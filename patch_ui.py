import re

with open("static/index.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1. Funcoes de formatacao contabil e conversao numerica
funcoes_js = """
    function formatarMoeda(el) {
      let v = el.value.replace(/\\D/g, '');
      if (!v) { el.value = ''; return; }
      let num = (parseInt(v, 10) / 100).toFixed(2);
      let partes = num.split('.');
      partes[0] = partes[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');
      el.value = partes.join(',');
    }

    function getCustoNumerico() {
      const el = document.getElementById('inCusto');
      if (!el || !el.value) return 0;
      let v = el.value.replace(/\\./g, '').replace(',', '.').replace(/[^\\d.]/g, '');
      return parseFloat(v) || 0;
    }
"""

if "function formatarMoeda" not in html:
    html = html.replace("<script>", "<script>\n" + funcoes_js, 1)

# 2. Altera o campo inCusto para aceitar mascara contabil
html = re.sub(
    r'<input\s+id="inCusto"[^>]*>',
    '<input id="inCusto" type="text" inputmode="numeric" placeholder="0,00" oninput="formatarMoeda(this); atualizarConversao()">',
    html
)

# 3. Faz o sistema ler o valor formatado corretamente
html = html.replace("parseFloat(document.getElementById('inCusto').value)", "getCustoNumerico()")

# 4. Corrige a funcao do WhatsApp para transmitir sem falhas
nova_funcao_wpp = """function enviarWhatsAppDireto() {
      if (typeof dossieWhats !== 'undefined' && dossieWhats) {
        window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(dossieWhats), '_blank');
        return;
      }
      if (!dadosUltimoRelatorio) return alert('Realize uma auditoria primeiro.');
      const r = dadosUltimoRelatorio;
      const c = r.classico || {};
      const p = r.premium || {};
      const st = r.status === 'A' ? '🟢 OPORTUNIDADE' : (r.status === 'E' ? '🔴 PREJUÍZO' : '🟡 MARGEM CRÍTICA');
      const custoVal = Number(r.custo_base || r.custo || 0).toFixed(2);
      const precoVal = Number(r.menor_preco || 0).toFixed(2);
      const msg = `*🤖 SMART MELI ULTRA | AUDITORIA HUD*\\n\\n` +
                  `📦 *Produto:* ${r.titulo_encontrado || r.titulo || ''}\\n` +
                  `🎯 *Menor Preço ML:* R$ ${precoVal}\\n` +
                  `💵 *Seu Custo Base:* R$ ${custoVal}\\n\\n` +
                  `📊 *VIABILIDADE DE VENDA:*\\n` +
                  `⚡ *ML Clássico:* Lucro R$ ${Number(c.lucro || 0).toFixed(2)} | Margem ${Number(c.margem || 0).toFixed(1)}%\\n` +
                  `💎 *ML Premium:* Lucro R$ ${Number(p.lucro || 0).toFixed(2)} | Margem ${Number(p.margem || 0).toFixed(1)}%\\n\\n` +
                  `🚦 *Status:* ${st}\\n` +
                  `🔗 *Link do Concorrente:* ${r.link || ''}\\n\\n` +
                  `_Auditado via Smart Meli Ultra Core_`;
      window.open('https://api.whatsapp.com/send?text=' + encodeURIComponent(msg), '_blank');
    }"""

html = re.sub(
    r'function enviarWhatsAppDireto\(\)\s*\{[\s\S]*?window\.open\([^)]+\);\s*\}',
    nova_funcao_wpp,
    html
)

with open("static/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("[OK] static/index.html atualizado com sucesso!")
