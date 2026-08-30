"""
SmartML Ultra - Price Discovery Engine v3 (ProviderChain + Fuzzy Matcher + Sniper)
Integração da Arquitetura Avançada (Bypass de 403 e Validação Semântica)
"""
from __future__ import annotations
import json
import logging
import os
import re
import statistics
import time
import unicodedata
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Sequence, Dict

log = logging.getLogger("smartml.scraper")

API = "https://api.mercadolibre.com"
FRONT = "https://lista.mercadolivre.com.br"
TIMEOUT = 10

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"

# ---------------------------------------------------------------- normalização
_ACCESSORY_TERMS = {
    "capa", "case", "capinha", "pelicula", "película", "carregador", "cabo",
    "fone", "suporte", "adaptador", "protetor", "vidro", "bateria", "tela",
    "display", "carcaca", "carcaça", "kit", "caneta", "bumper", "skin",
    "adesivo", "chip", "gabinete", "flex", "conector", "placa", "aro",
}
_SUSPECT_TITLE_TERMS = {"somente", "apenas", "leia", "sucata", "defeito", "peças", "pecas"}
_STOPWORDS = {"de", "da", "do", "com", "para", "e", "o", "a", "novo", "nova", "lacrado", "gb"}

def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

def norm(text: str) -> str:
    text = strip_accents(text or "").lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

# ---------------------------------------------------------------- query model
_STORAGE_RE = re.compile(r"\b(\d{2,4})\s*(gb|tb)\b")
_COLORS = {
    "preto", "branco", "azul", "verde", "vermelho", "roxo", "rosa", "dourado",
    "prata", "cinza", "grafite", "titanio", "laranja", "amarelo", "bege", "creme",
}
_MODEL_HINTS = ("pro", "max", "plus", "mini", "ultra", "air", "lite", "fe", "se")

@dataclass(frozen=True)
class ProductQuery:
    raw: str
    macro: str
    storage: str | None
    color: str | None
    required: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> "ProductQuery":
        flat = norm(raw)
        m = _STORAGE_RE.search(flat)
        storage = f"{m.group(1)}{m.group(2)}" if m else None
        flat_wo_storage = _STORAGE_RE.sub(" ", flat)
        toks = [t for t in flat_wo_storage.split() if t not in _STOPWORDS]
        color = next((t for t in toks if t in _COLORS), None)
        macro_tokens = [t for t in toks if t != color]
        macro = " ".join(macro_tokens).strip()
        required = tuple(t for t in macro_tokens if t.isdigit() or t in _MODEL_HINTS or len(t) > 2)
        return cls(raw=raw, macro=macro or flat, storage=storage, color=color, required=required)

    def relaxations(self) -> list[str]:
        out, seen = [], set()
        candidates = [
            self.macro,
            " ".join(self.macro.split()[:4]),
            " ".join(self.macro.split()[:3]),
            " ".join(self.macro.split()[:2]),
        ]
        for c in candidates:
            c = c.strip()
            if c and c not in seen:
                seen.add(c)
                out.append(c)
        return out

# ---------------------------------------------------------------- auth
class MLAuth:
    def __init__(self):
        self.client_id = "6903491647062278"
        self.client_secret = "qm1v0B0xZNhoMB0qtSH6T6wk814L5n4e"
        self._token: str | None = None
        self._exp: float = 0.0

    def token(self) -> str | None:
        if self._token and time.time() < self._exp - 300:
            return self._token
        try:
            payload = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret}).encode("utf-8")
            req = urllib.request.Request(f"{API}/oauth/token", data=payload, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
                self._token = data["access_token"]
                self._exp = time.time() + int(data.get("expires_in", 21600))
                return self._token
        except Exception:
            return None

# ---------------------------------------------------------------- resultado
@dataclass
class Offer:
    id: str
    title: str
    price: float
    permalink: str
    source: str = ""
    score: float = 0.0

# ---------------------------------------------------------------- matcher
class Matcher:
    def __init__(self, query: ProductQuery, custo_compra: float, min_score: float = 0.62):
        self.q = query
        self.min_score = min_score
        self.custo_compra = custo_compra

    def score(self, title: str) -> float:
        t = norm(title)
        tset = set(t.split())
        if bool(tset & _SUSPECT_TITLE_TERMS) or bool(tset & _ACCESSORY_TERMS):
            return 0.0
        req = [r for r in self.q.required]
        if req:
            coverage = sum(1 for r in req if r in tset) / len(req)
            if coverage < 0.75: return 0.0
        else:
            coverage = 1.0
        ratio = SequenceMatcher(None, self.q.macro, t).ratio()
        bonus = 0.0
        if self.q.storage: bonus += 0.15 if self.q.storage in t.replace(" ", "") else -0.20
        if self.q.color and self.q.color in tset: bonus += 0.10
        return max(0.0, min(1.0, 0.55 * coverage + 0.45 * ratio + bonus))

    def filter(self, offers: Iterable[Offer]) -> list[Offer]:
        kept = []
        for o in offers:
            o.score = self.score(o.title)
            # Trava financeira embutida na validação semântica
            if o.score >= self.min_score and o.price > (self.custo_compra * 0.25):
                kept.append(o)
        return sorted(kept, key=lambda x: (-x.score, x.price))

# ---------------------------------------------------------------- providers
class Provider:
    name = "base"
    def __init__(self, auth: MLAuth):
        self.auth = auth

    def get_json(self, url: str, authed: bool = True) -> dict:
        h = {"User-Agent": "SmartMLEngine/2.0", "Accept": "application/json"}
        if authed and self.auth.token():
            h["Authorization"] = f"Bearer {self.auth.token()}"
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))

class CatalogProductsProvider(Provider):
    name = "catalog"
    def search(self, term: str) -> list[Offer]:
        try:
            data = self.get_json(f"{API}/products/search?status=active&site_id=MLB&q={urllib.parse.quote(term)}&limit=10")
            offers = []
            for prod in (data.get("results") or [])[:5]:
                pid = prod.get("id")
                if not pid: continue
                try:
                    bb_data = self.get_json(f"{API}/products/{pid}")
                    price = float((bb_data.get("buy_box_winner") or {}).get("price") or 0)
                    if price > 0:
                        offers.append(Offer(id=pid, title=prod.get("name", ""), price=price, permalink=prod.get("permalink", ""), source=self.name))
                except Exception: pass
            return offers
        except Exception as e:
            raise PermissionError from e

class SiteSearchProvider(Provider):
    name = "site_search"
    def search(self, term: str) -> list[Offer]:
        try:
            data = self.get_json(f"{API}/sites/MLB/search?q={urllib.parse.quote(term)}&limit=40&condition=new")
            return [Offer(id=i.get("id",""), title=i.get("title",""), price=float(i.get("price") or 0), permalink=i.get("permalink",""), source=self.name) for i in (data.get("results") or [])]
        except Exception as e:
            raise PermissionError from e

class PublicFrontProvider(Provider):
    name = "public_front"
    _RE_STATE = re.compile(r'"price"\s*:\s*([0-9.]+).{0,400}?"title"\s*:\s*"([^"]{10,200})"', re.S)
    def search(self, term: str) -> list[Offer]:
        slug = norm(term).replace(" ", "-")
        req = urllib.request.Request(f"{FRONT}/{slug}_ITEM*CONDITION_2230284", headers={"User-Agent": UA, "Accept": "text/html"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                html = r.read().decode("utf-8")
                offers = []
                seen = set()
                for price, title in self._RE_STATE.findall(html):
                    title = json.loads(f'"{title}"') if "\\u" in title else title
                    if (title.lower(), price) in seen: continue
                    seen.add((title.lower(), price))
                    offers.append(Offer(id="", title=title, price=float(price), permalink=f"{FRONT}/{slug}", source=self.name))
                return offers
        except Exception as e:
            raise PermissionError from e

# ---------------------------------------------------------------- orquestrador e fachada
_auth = MLAuth()

def buscar_menor_preco_ml(termo_busca: str, custo_compra: float = 0.0) -> Dict:
    termo_base = str(termo_busca).strip()
    
    # 1. MODO SNIPER ABSOLUTO (Mantido para preservar a UI do AppSheet)
    match_item = re.search(r'MLB[-_]?(\d+)', termo_base, re.IGNORECASE)
    if "mercadolivre.com.br" in termo_base or match_item:
        mlb_id = f"MLB{match_item.group(1)}" if match_item else ""
        if mlb_id:
            try:
                h = {"User-Agent": "SmartMLEngine/2.0", "Accept": "application/json"}
                req = urllib.request.Request(f"{API}/items/{mlb_id}", headers=h)
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    item = json.loads(r.read().decode('utf-8'))
                    return {
                        "encontrado": True, "menor_preco": float(item.get('price', 0.0)),
                        "link": item.get('permalink', '').split('?')[0], "titulo_encontrado": item.get('title', ''),
                        "auditoria_ia": "🎯 Anúncio Exato (Modo Sniper)"
                    }
            except Exception: pass
        match_slug = re.search(r'mercadolivre\.com\.br/([^/]+)', termo_base)
        if match_slug:
            termo_base = match_slug.group(1).replace("-", " ")

    # 2. PROVIDER CHAIN & FUZZY MATCHER (Arquitetura P25)
    q = ProductQuery.parse(termo_base)
    matcher = Matcher(q, custo_compra)
    providers = [CatalogProductsProvider(_auth), SiteSearchProvider(_auth), PublicFrontProvider(_auth)]
    
    best_offers = []
    used_provider = ""

    for provider in providers:
        for term in q.relaxations():
            try:
                raw_offers = provider.search(term)
                hits = matcher.filter(raw_offers)
                if len(hits) >= 3:
                    best_offers, used_provider = hits, provider.name
                    break
                if len(hits) > len(best_offers):
                    best_offers, used_provider = hits, provider.name
            except PermissionError:
                break # Pula para o próximo provedor se tomar 403
        if len(best_offers) >= 3:
            break

    if best_offers:
        prices = [o.price for o in best_offers]
        # P25 de Quartil Imune a Anúncio Isca
        if len(prices) < 4:
            ref_price = statistics.median(prices)
        else:
            q1, q3 = statistics.quantiles(prices, n=4)[0], statistics.quantiles(prices, n=4)[2]
            iqr = q3 - q1
            clean = [p for p in prices if q1 - 1.5 * iqr <= p <= q3 + 1.5 * iqr] or prices
            ref_price = statistics.quantiles(clean, n=4)[0] if len(clean) >= 4 else statistics.median(clean)

        return {
            "encontrado": True,
            "menor_preco": round(ref_price, 2),
            "link": best_offers[0].permalink,
            "titulo_encontrado": best_offers[0].title,
            "auditoria_ia": f"⚡ Provedor: {used_provider.upper()} | Precisão P25 | Amostra: {len(prices)}"
        }

    return {
        "encontrado": False,
        "mensagem": "❌ RESTRIÇÃO DA API OU PRODUTO INEXISTENTE.<br><br>Cole o <b>LINK EXATO</b> para análise forçada."
    }