import re

print(">>> Iniciando atualizacao do SmartML Ultra HUD...")

# -------------------------------------------------------------
# 1. ATUALIZAR src/scraper.py (Garantir suporte à imagem e candidatos)
# -------------------------------------------------------------
scraper_code = '''import os, logging, urllib.parse
import urllib.request, json

log = logging.getLogger("smartml.scraper")

def buscar_menor_preco_ml(termo, custo_base=0.0):
    try:
        tunnel_url = os.getenv("LOCAL_SCRAPER_URL", "https://ltd-developer-wed-drives.trycloudflare.com").rstrip("/")
        termo_encoded = urllib.parse.quote(termo)
        url_chamada = f"{tunnel_url}/buscar?termo={termo_encoded}&custo={custo_base}"

        req = urllib.request.Request(url_chamada, headers={"User-Agent": "SmartML-Cloud/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if not data.get("sucesso"):
            return {"sucesso": False, "mensagem": data.get("mensagem", "Nenhum concorrente encontrado.")}

        candidatos = data.get("candidatos", [])
        if candidatos:
            melhor = candidatos[0]
            return {
                "sucesso": True,
                "menor_preco": melhor["preco"],
                "link": melhor["link"],
                "titulo_encontrado": melhor["titulo"],
                "imagem": melhor.get("imagem", "")
            }

        if "menor_preco" in data:
            return data

        return {"sucesso": False, "mensagem": "Nenhum anúncio qualificado encontrado."}

    except Exception as e:
        log.error(f"Erro ao consultar radar local: {e}")
        return {"sucesso": False, "mensagem": f"Erro no radar de concorrencia: {str(e)}"}
'''
with open("src/scraper.py", "w", encoding="utf-8") as f:
    f.write(scraper_code)
print("[OK] src/scraper.py atualizado!")

# -------------------------------------------------------------
# 2. ATUALIZAR src/main.py (Repassar a imagem no payload final)
# -------------------------------------------------------------
with open("src/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

if '"imagem":' not in main_code:
    main_code = main_code.replace(
        '"link": link,',
        '"link": link,\n            "imagem": resultado_scraper.get("imagem", ""),'
    )
    with open("src/main.py", "w", encoding="utf-8") as f:
        f.write(main_code)
    print("[OK] src/main.py atualizado com campo de imagem!")
else:
    print("[SKIP] src/main.py ja possui campo de imagem.")

# -------------------------------------------------------------
# 3. ATUALIZAR static/index.html (HUD Cockpit + Câmera Preservada)
# -------------------------------------------------------------
with open("static/index.html", "r", encoding="utf-8", errors="ignore") as f:
    html = f.read()

# Injetar CSS do Cockpit HUD antes de </style>
css_hud = '''
    /* BOTOES DE MOEDA */
    .curr-btn {
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.2);
      color: #94a3b8;
      border-radius: 6px;
      padding: 3px 12px;
      font-size: 11px;
      font-weight: 800;
      cursor: pointer;
      transition: all 0.2s;
    }
    .curr-btn.active {
      background: #FFE600;
      color: #000000;
      border-color: #FFE600;
      font-weight: 900;
    }

    /* PAINEL COCKPIT HUD */
    .hud-panel {
      display: none;
      background: #090f1d;
      border: 1px solid #00E5FF;
      border-radius: 14px;
      padding: 16px;
      margin-top: 14px;
      box-shadow: 0 0 25px rgba(0, 229, 255, 0.15);
      animation: fadeIn 0.25s ease-out;
    }
    .hud-panel.status-A { border-color: #00FF88; box-shadow: 0 0 25px rgba(0, 255, 136, 0.2); }
    .hud-panel.status-D { border-color: #FFE600; box-shadow: 0 0 25px rgba(255, 230, 0, 0.2); }
    .hud-panel.status-E { border-color: #ef4444; box-shadow: 0 0 25px rgba(239, 68, 68, 0.25); }

    .hud-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 8px;
      border-bottom: 1px dashed rgba(255,255,255,0.15);
      margin-bottom: 12px;
    }
    .hud-tag { font-size: 10px; font-weight: 900; letter-spacing: 0.5px; text-transform: uppercase; }
    .badge-status { padding: 4px 8px; border-radius: 4px; font-weight: 900; font-size: 10px; }

    /* CARD DO PRODUTO AUDITADO */
    .hud-product-card {
      display: flex;
      gap: 12px;
      background: rgba(255,255,255,0.03);
      padding: 10px;
      border-radius: 10px;
      margin-bottom: 12px;
      align-items: center;
      border: 1px solid rgba(255,255,255,0.06);
    }
    .hud-thumb {
      width: 70px;
      height: 70px;
      object-fit: contain;
      background: #ffffff;
      border-radius: 8px;
      padding: 2px;
      flex-shrink: 0;
    }
    .hud-pdetails { flex: 1; min-width: 0; }
    .hud-title {
      font-size: 12px;
      font-weight: 700;
      color: #f8fafc;
      line-height: 1.3;
      margin-bottom: 4px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .hud-price { font-size: 15px; font-weight: 900; color: #FFE600; }
    .hud-link { font-size: 10px; color: #00E5FF; text-decoration: none; font-weight: 800; display: inline-block; margin-top: 3px; }
    .hud-link:hover { text-decoration: underline; }

    /* GRADE DUAL: CLASSICO VS PREMIUM */
    .viab-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 14px;
    }
    .viab-box {
      background: rgba(15, 23, 42, 0.75);
      border-radius: 10px;
      padding: 10px 8px;
      border: 1px solid rgba(0, 229, 255, 0.25);
      text-align: center;
    }
    .viab-box.prem { border-color: rgba(255, 230, 0, 0.35); background: rgba(30, 41, 59, 0.6); }
    .viab-lbl { font-size: 9px; font-weight: 800; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px; }
    .viab-lucro { font-size: 14px; font-weight: 900; margin: 3px 0; }
    .viab-margem { font-size: 11px; font-weight: 800; }

    .btn-send-wpp {
      width: 100%;
      background: linear-gradient(90deg, #25D366 0%, #128C7E 100%);
      color: #ffffff;
      border: none;
      font-weight: 900;
      padding: 12px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 11px;
      text-transform: uppercase;
      box-shadow: 0 4px 12px rgba(37, 211, 102, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      margin-bottom: 8px;
    }
'''
if ".curr-btn" not in html:
    html = html.replace("</style>", css_hud + "\n</style>")

# Atualizar Subtítulo
html = re.sub(
    r'<div class=[\'"]subtitle[\'"]>.*?</div>',
    '<div class="subtitle">Análise de alta performance</div>',
    html,
    flags=re.IGNORECASE
)

# Atualizar Rótulo SKU/EAN
html = re.sub(
    r'<label>\s*PRODUTO\s*/\s*SKU.*?</label>',
    '<label>PRODUTO / SKU / EAN</label>',
    html,
    flags=re.IGNORECASE
)

# Atualizar Bloco de Custo com Seletor R$ / US$
bloco_custo_regex = r'<label>\s*CUSTO\s*BASE.*?</label>\s*<div[^>]*>\s*<input id=[\'"]inCusto[\'"][^>]*>\s*</div>'
novo_bloco_custo = '''<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <label id="lblCusto" style="margin: 0;">CUSTO (R$)</label>
        <div style="display: flex; gap: 4px;">
          <button type="button" id="btnBRL" class="curr-btn active" onclick="setMoeda('BRL')">R$</button>
          <button type="button" id="btnUSD" class="curr-btn" onclick="setMoeda('USD')">US$</button>
        </div>
      </div>
      <div style="margin-bottom: 4px;">
        <input id="inCusto" type="number" step="0.01" placeholder="Ex: 50,00" oninput="atualizarConversao()">
      </div>
      <div id="previewConversao" style="display: none; font-size: 11px; color: #FFE600; font-weight: 700; margin-bottom: 8px;"></div>'''
html = re.sub(bloco_custo_regex, novo_bloco_custo, html, flags=re.IGNORECASE | re.DOTALL)

# Atualizar Botão de Ação Principal
html = re.sub(
    r'<button class=[\'"]btn-calc[\'"][^>]*>.*?</button>',
    '<button class="btn-calc" id="btnAcao" onclick="executarCalculo()">ANALISAR VIABILIDADE ⚡</button>',
    html,
    flags=re.IGNORECASE
)

# Atualizar Bloco de Botão Novo / Ação
bloco_resultado_antigo = r'<div id=[\'"]resBox[\'"][^>]*>.*?</div>\s*<button id=[\'"]btnCopiar[\'"].*?</button>\s*<div class=[\'"]action-row[\'"][^>]*>\s*<button class=[\'"]btn-action[\'"][^>]*>.*?</button>\s*</div>'
novo_bloco_resultado = '''<div class="action-row" id="areaBotoes" style="margin-top: 10px;">
        <button type="button" class="btn-action" onclick="novoCalculo()">+ NOVA ANÁLISE</button>
      </div>

      <!-- PAINEL COCKPIT HUD -->
      <div id="hudPainel" class="hud-panel">
        <div class="hud-header">
          <span class="hud-tag" style="color: #00E5FF;">⚡ RADAR AUDITORIA</span>
          <span id="hudStatusBadge" class="badge-status">VIÁVEL</span>
        </div>

        <div class="hud-product-card">
          <img id="hudImg" class="hud-thumb" src="" alt="Produto">
          <div class="hud-pdetails">
            <div id="hudTitulo" class="hud-title">Título do Concorrente</div>
            <div class="hud-price" id="hudPreco">R$ 0,00</div>
            <a id="hudLink" class="hud-link" href="#" target="_blank">🔗 INSPECIONAR ANÚNCIO NO ML</a>
          </div>
        </div>

        <div class="viab-grid">
          <div class="viab-box" id="cardClassico">
            <div class="viab-lbl" style="color: #00E5FF;">ML CLÁSSICO</div>
            <div class="viab-lbl">LUCRO LÍQUIDO</div>
            <div class="viab-lucro" id="hudLucroC">R$ 0,00</div>
            <div class="viab-margem" id="hudMargemC">Margem: 0%</div>
          </div>
          <div class="viab-box prem" id="cardPremium">
            <div class="viab-lbl" style="color: #FFE600;">ML PREMIUM</div>
            <div class="viab-lbl">LUCRO LÍQUIDO</div>
            <div class="viab-lucro" id="hudLucroP">R$ 0,00</div>
            <div class="viab-margem" id="hudMargemP">Margem: 0%</div>
          </div>
        </div>

        <button type="button" class="btn-send-wpp" onclick="enviarWhatsAppDireto()">
          📲 TRANSMITIR VIA WHATSAPP
        </button>
        <button type="button" class="copy-btn" id="btnCopiar" style="display: block; margin-top: 0;" onclick="copiarWhatsApp()">
          📋 COPIAR RELATÓRIO TÉCNICO
        </button>
      </div>'''
html = re.sub(bloco_resultado_antigo, novo_bloco_resultado, html, flags=re.IGNORECASE | re.DOTALL)

# Injetar Funções JavaScript de Moeda e HUD
js_novas_funcoes = '''
    let moedaAtual = 'BRL';
    const COTACAO_USD = 5.60;
    let dadosUltimoRelatorio = null;

    function setMoeda(m) {
      moedaAtual = m;
      document.getElementById('btnBRL').classList.toggle('active', m === 'BRL');
      document.getElementById('btnUSD').classList.toggle('active', m === 'USD');
      document.getElementById('lblCusto').innerText = m === 'BRL' ? 'CUSTO (R$)' : 'CUSTO (US$)';
      document.getElementById('inCusto').placeholder = m === 'BRL' ? 'Ex: 50,00' : 'Ex: 15.00';
      atualizarConversao();
    }

    function atualizarConversao() {
      const val = parseFloat(document.getElementById('inCusto').value);
      const prev = document.getElementById('previewConversao');
      if (moedaAtual === 'USD' && !isNaN(val) && val > 0) {
        const brl = (val * COTACAO_USD).toFixed(2);
        prev.innerText = '≈ R$ ' + brl + ' (Câmbio: US$ 1 = R$ ' + COTACAO_USD.toFixed(2) + ')';
        prev.style.display = 'block';
      } else {
        prev.style.display = 'none';
      }
    }

    function enviarWhatsAppDireto() {
      if (!dadosUltimoRelatorio) return alert('Realize uma auditoria primeiro.');
      const r = dadosUltimoRelatorio;
      const c = r.classico;
      const p = r.premium;
      const st = r.status === 'A' ? '🟢 OPORTUNIDADE' : (r.status === 'E' ? '🔴 PREJUÍZO' : '🟡 MARGEM CRÍTICA');
      const msg = `*🤖 SMART MELI ULTRA | AUDITORIA HUD*\\n\\n` +
                  `📦 *Produto:* ${r.titulo_encontrado || r.titulo}\\n` +
                  `🎯 *Menor Preço ML:* R$ ${r.menor_preco.toFixed(2)}\\n` +
                  `💵 *Seu Custo Base:* R$ ${r.custo_base.toFixed(2)} (${moedaAtual})\\n\\n` +
                  `📊 *VIABILIDADE DE VENDA:*\\n` +
                  `⚡ *ML Clássico (11.5%):* Lucro R$ ${c.lucro.toFixed(2)} | Margem ${c.margem.toFixed(1)}%\\n` +
                  `💎 *ML Premium (16.5%):* Lucro R$ ${p.lucro.toFixed(2)} | Margem ${p.margem.toFixed(1)}%\\n\\n` +
                  `🚦 *Status:* ${st}\\n` +
                  `🔗 *Link do Concorrente:* ${r.link}\\n\\n` +
                  `_Auditado via Smart Meli Ultra Core_`;
      window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(msg), '_blank');
    }
'''

if "let moedaAtual" not in html:
    html = re.sub(
        r'(<script[^>]*>)',
        r'\1' + js_novas_funcoes,
        html,
        count=1,
        flags=re.IGNORECASE
    )

# Atualizar o fetch do executarCalculo para enviar a moeda
html = re.sub(
    r'body:\s*JSON\.stringify\(\{\s*titulo:\s*prod,\s*custo:\s*custo\s*\}\)',
    'body: JSON.stringify({ titulo: prod, custo: custo, moeda: moedaAtual, cotacao: COTACAO_USD })',
    html
)

# Atualizar renderizacao no executarCalculo para preencher o HUD Cockpit
js_render_hud = '''
          dadosUltimoRelatorio = res;
          btn.innerText = 'ANALISAR VIABILIDADE ⚡';
          btn.disabled = false;

          const hud = document.getElementById('hudPainel');
          const stBadge = document.getElementById('hudStatusBadge');

          if (!res.sucesso) {
            hud.className = 'hud-panel status-E';
            hud.style.display = 'block';
            stBadge.innerText = '🔴 NÃO LOCALIZADO';
            stBadge.style.background = 'rgba(239,68,68,0.2)';
            stBadge.style.color = '#ef4444';
            document.getElementById('hudTitulo').innerText = res.mensagem || 'Concorrência não encontrada.';
            document.getElementById('hudPreco').innerText = '---';
            document.getElementById('hudImg').src = 'https://http2.mlstatic.com/frontend-assets/ui-navigation/5.18.9/mercadolibre/logo__small.png';
            document.getElementById('hudLink').style.display = 'none';
            return;
          }

          hud.className = 'hud-panel status-' + res.status;
          stBadge.innerText = res.status === 'A' ? '🟢 OPORTUNIDADE' : (res.status === 'E' ? '🔴 PREJUÍZO' : '🟡 MARGEM CRÍTICA');
          stBadge.style.background = res.status === 'A' ? 'rgba(0,255,136,0.15)' : (res.status === 'E' ? 'rgba(239,68,68,0.15)' : 'rgba(255,230,0,0.15)');
          stBadge.style.color = res.status === 'A' ? '#00FF88' : (res.status === 'E' ? '#ef4444' : '#FFE600');

          document.getElementById('hudTitulo').innerText = res.titulo_encontrado || res.titulo;
          document.getElementById('hudPreco').innerText = 'R$ ' + res.menor_preco.toFixed(2);
          document.getElementById('hudImg').src = res.imagem || 'https://http2.mlstatic.com/frontend-assets/ui-navigation/5.18.9/mercadolibre/logo__small.png';

          const lk = document.getElementById('hudLink');
          if (res.link) { lk.href = res.link; lk.style.display = 'inline-block'; } else { lk.style.display = 'none'; }

          // Classico
          const c = res.classico;
          document.getElementById('hudLucroC').innerText = 'R$ ' + c.lucro.toFixed(2);
          document.getElementById('hudLucroC').style.color = c.lucro >= 0 ? '#00FF88' : '#ef4444';
          document.getElementById('hudMargemC').innerText = 'Margem: ' + c.margem.toFixed(1) + '%';
          document.getElementById('hudMargemC').style.color = c.margem >= 15 ? '#00FF88' : (c.margem > 0 ? '#FFE600' : '#ef4444');

          // Premium
          const p = res.premium;
          document.getElementById('hudLucroP').innerText = 'R$ ' + p.lucro.toFixed(2);
          document.getElementById('hudLucroP').style.color = p.lucro >= 0 ? '#FFE600' : '#ef4444';
          document.getElementById('hudMargemP').innerText = 'Margem: ' + p.margem.toFixed(1) + '%';
          document.getElementById('hudMargemP').style.color = p.margem >= 15 ? '#00FF88' : (p.margem > 0 ? '#FFE600' : '#ef4444');

          dossieWhats = `*🤖 SMART MELI ULTRA | AUDITORIA*\\n\\n` +
                        `📦 *Produto:* ${res.titulo_encontrado || res.titulo}\\n` +
                        `🎯 *Menor Preço ML:* R$ ${res.menor_preco.toFixed(2)}\\n` +
                        `💵 *Seu Custo Base:* R$ ${res.custo_base.toFixed(2)}\\n\\n` +
                        `⚡ *ML Clássico (11.5%):* Lucro R$ ${c.lucro.toFixed(2)} (${c.margem.toFixed(1)}%)\\n` +
                        `💎 *ML Premium (16.5%):* Lucro R$ ${p.lucro.toFixed(2)} (${p.margem.toFixed(1)}%)\\n\\n` +
                        `🔗 *Link:* ${res.link}`;

          hud.style.display = 'block';
          return;
'''

html = re.sub(
    r'btn\.disabled = false;\s*const resBox = document\.getElementById\([\'"]resBox[\'"]\);.*?dossieWhats = `.*?;',
    js_render_hud,
    html,
    flags=re.DOTALL
)

# Atualizar funcao novoCalculo para limpar o HUD
html = re.sub(
    r'function novoCalculo\(\)\s*\{.*?\}',
    '''function novoCalculo() {
      document.getElementById('inProd').value = '';
      document.getElementById('inCusto').value = '';
      const hud = document.getElementById('hudPainel');
      if (hud) hud.style.display = 'none';
      setMoeda('BRL');
      document.getElementById('inProd').focus();
    }''',
    html,
    flags=re.DOTALL
)

with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("[OK] static/index.html atualizado com Cockpit HUD e camera intacta!")
