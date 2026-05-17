"""
=============================================================
  ABC LEILÃO MONITOR — Ferramenta pessoal de alertas
  Apartamentos 70-160k | Santo André · SBC · Mauá · S.Caetano
=============================================================
  Roda todo dia via GitHub Actions (gratuito)
  Envia resumo por WhatsApp (CallMeBot) e E-mail (Gmail)
=============================================================
"""

import os
import json
import time
import logging
import smtplib
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# ─────────────────────────────────────────
#  CONFIGURAÇÕES — edite aqui
# ─────────────────────────────────────────
CONFIG = {
    # Seus filtros de busca
    "filtros": {
        "lance_min": 70_000,
        "lance_max": 160_000,
        "tipo": "apartamento",
        "cidades": ["Santo André", "São Bernardo do Campo", "Mauá", "São Caetano do Sul"],
        "quartos_min": 2,
    },

    # WhatsApp via CallMeBot (gratuito)
    # Instruções: wa.me/+5511999999999?text=I+allow+callmebot+to+send+me+messages
    # Depois acesse: https://www.callmebot.com/blog/free-api-whatsapp-messages/
    "whatsapp": {
        "ativo": True,
        "numero": os.getenv("WA_NUMERO", "+55119XXXXXXXX"),   # ex: +5511999999999
        "apikey": os.getenv("WA_APIKEY", "SUA_APIKEY_AQUI"),  # gerada no CallMeBot
    },

    # E-mail via Gmail SMTP
    "email": {
        "ativo": True,
        "remetente": os.getenv("EMAIL_REMETENTE", "seuemail@gmail.com"),
        "senha_app": os.getenv("EMAIL_SENHA", "xxxx xxxx xxxx xxxx"),  # Senha de App do Gmail
        "destinatario": os.getenv("EMAIL_DEST", "seuemail@gmail.com"),
        "assunto": "🏠 ABC Leilões — Novos apartamentos hoje",
    },
}

# ─────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("leilao")


# ══════════════════════════════════════════════════════════
#  MÓDULO DE BUSCA — cada plataforma tem sua função
# ══════════════════════════════════════════════════════════

def buscar_caixa(filtros):
    """
    Busca imóveis no site da Caixa Econômica Federal.
    URL base: https://venda.caixa.gov.br/imoveis
    A Caixa disponibiliza listagem pública sem autenticação.
    """
    imoveis = []
    cidades_caixa = {
        "Santo André": "SANTO+ANDRE",
        "São Bernardo do Campo": "SAO+BERNARDO+DO+CAMPO",
        "Mauá": "MAUA",
        "São Caetano do Sul": "SAO+CAETANO+DO+SUL",
    }

    for cidade_pt, cidade_enc in cidades_caixa.items():
        if cidade_pt not in filtros["cidades"]:
            continue

        url = (
            f"https://venda.caixa.gov.br/imoveis"
            f"?estado=SP&cidade={cidade_enc}"
            f"&bairro=&categ=&tipo=2"       # tipo=2 → apartamento
            f"&vlMin={filtros['lance_min']}"
            f"&vlMax={filtros['lance_max']}"
            f"&submit=Pesquisar"
        )

        try:
            log.info(f"[Caixa] Buscando em {cidade_pt}...")
            if HAS_REQUESTS:
                resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
                html = resp.text
            else:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    html = r.read().decode("utf-8", errors="ignore")

            if HAS_BS4:
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".item-imovel, .imovel-card, [class*='imovel']")
                for card in cards[:10]:
                    try:
                        titulo = card.select_one("h2, h3, .titulo, .descricao")
                        preco_el = card.select_one(".preco, .valor, [class*='preco'], [class*='valor']")
                        link_el = card.select_one("a[href]")

                        titulo_txt = titulo.get_text(strip=True) if titulo else f"Apartamento em {cidade_pt}"
                        preco_txt = preco_el.get_text(strip=True) if preco_el else ""
                        link = link_el["href"] if link_el else url

                        preco_num = extrair_numero(preco_txt)
                        if preco_num and filtros["lance_min"] <= preco_num <= filtros["lance_max"]:
                            imoveis.append(montar_imovel(
                                titulo=titulo_txt,
                                cidade=cidade_pt,
                                lance=preco_num,
                                fonte="Caixa",
                                url=link if link.startswith("http") else "https://venda.caixa.gov.br" + link,
                            ))
                    except Exception:
                        continue
            else:
                # Sem BeautifulSoup, monta link direto para o usuário acessar
                imoveis.append({
                    "titulo": f"Ver apartamentos Caixa em {cidade_pt}",
                    "cidade": cidade_pt,
                    "lance": 0,
                    "avaliado": 0,
                    "desagio": 0,
                    "fonte": "Caixa",
                    "url": url,
                    "ocupado": None,
                    "debito_iptu": 0,
                    "debito_cond": 0,
                    "area": 0,
                    "quartos": 0,
                    "data_leilao": "Consulte o site",
                    "praca": "?",
                    "custo_total": 0,
                })

            time.sleep(2)  # respeitar o servidor

        except Exception as e:
            log.warning(f"[Caixa] Erro em {cidade_pt}: {e}")

    return imoveis


def buscar_sold(filtros):
    """
    Sold Leilões — https://www.sold.com.br
    Plataforma com imóveis de bancos e particulares.
    """
    imoveis = []
    for cidade in filtros["cidades"]:
        url = (
            f"https://www.sold.com.br/imoveis"
            f"?tipo=apartamento&estado=SP"
            f"&cidade={urllib.parse.quote(cidade)}"
            f"&preco_min={filtros['lance_min']}"
            f"&preco_max={filtros['lance_max']}"
        )
        imoveis.append({
            "titulo": f"🔍 Ver apartamentos Sold em {cidade}",
            "cidade": cidade,
            "lance": 0,
            "avaliado": 0,
            "desagio": 0,
            "fonte": "Sold",
            "url": url,
            "ocupado": None,
            "debito_iptu": 0,
            "debito_cond": 0,
            "area": 0,
            "quartos": 0,
            "data_leilao": "Consulte o site",
            "praca": "?",
            "custo_total": 0,
        })
    return imoveis


def buscar_zuk(filtros):
    """Zuk Leilões — https://www.zuk.com.br"""
    imoveis = []
    for cidade in filtros["cidades"]:
        url = (
            f"https://www.zuk.com.br/busca"
            f"?tipo=apartamento&uf=SP"
            f"&cidade={urllib.parse.quote(cidade)}"
            f"&lance_min={filtros['lance_min']}"
            f"&lance_max={filtros['lance_max']}"
        )
        imoveis.append({
            "titulo": f"🔍 Ver apartamentos Zuk em {cidade}",
            "cidade": cidade,
            "lance": 0,
            "avaliado": 0,
            "desagio": 0,
            "fonte": "Zuk",
            "url": url,
            "ocupado": None,
            "debito_iptu": 0,
            "debito_cond": 0,
            "area": 0,
            "quartos": 0,
            "data_leilao": "Consulte o site",
            "praca": "?",
            "custo_total": 0,
        })
    return imoveis


def buscar_superbid(filtros):
    """Superbid — https://www.superbid.net"""
    imoveis = []
    for cidade in filtros["cidades"]:
        url = (
            f"https://www.superbid.net/busca"
            f"?q=apartamento&estado=SP"
            f"&cidade={urllib.parse.quote(cidade)}"
            f"&preco_de={filtros['lance_min']}"
            f"&preco_ate={filtros['lance_max']}"
        )
        imoveis.append({
            "titulo": f"🔍 Ver apartamentos Superbid em {cidade}",
            "cidade": cidade,
            "lance": 0,
            "avaliado": 0,
            "desagio": 0,
            "fonte": "Superbid",
            "url": url,
            "ocupado": None,
            "debito_iptu": 0,
            "debito_cond": 0,
            "area": 0,
            "quartos": 0,
            "data_leilao": "Consulte o site",
            "praca": "?",
            "custo_total": 0,
        })
    return imoveis


def buscar_banco_brasil(filtros):
    """Banco do Brasil — https://leiloes.bb.com.br"""
    imoveis = []
    for cidade in filtros["cidades"]:
        url = (
            f"https://leiloes.bb.com.br/imoveis"
            f"?estado=SP&cidade={urllib.parse.quote(cidade)}"
            f"&tipo=apartamento"
            f"&valor_de={filtros['lance_min']}"
            f"&valor_ate={filtros['lance_max']}"
        )
        imoveis.append({
            "titulo": f"🔍 Ver apartamentos BB em {cidade}",
            "cidade": cidade,
            "lance": 0,
            "avaliado": 0,
            "desagio": 0,
            "fonte": "Banco do Brasil",
            "url": url,
            "ocupado": None,
            "debito_iptu": 0,
            "debito_cond": 0,
            "area": 0,
            "quartos": 0,
            "data_leilao": "Consulte o site",
            "praca": "?",
            "custo_total": 0,
        })
    return imoveis


# ══════════════════════════════════════════════════════════
#  UTILITÁRIOS
# ══════════════════════════════════════════════════════════

def extrair_numero(texto):
    """Extrai valor numérico de strings como 'R$ 98.500,00'"""
    import re
    txt = texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
    nums = re.findall(r"\d+(?:\.\d+)?", txt)
    if nums:
        return float(nums[0])
    return None


def montar_imovel(titulo, cidade, lance, fonte, url,
                  avaliado=None, area=0, quartos=0,
                  data_leilao="Consulte o site", praca="?", ocupado=None):
    """Monta dicionário padrão de imóvel com cálculos automáticos"""
    if avaliado is None:
        avaliado = lance * 1.3  # estimativa quando não disponível

    desagio = round(((avaliado - lance) / avaliado) * 100) if avaliado > 0 else 0

    # Cálculo de custo real total
    comissao = round(lance * 0.05)
    itbi = round(lance * 0.03)
    cartorio = 3_500
    reforma = round(area * 400) if area > 0 else 15_000
    custo_total = lance + comissao + itbi + cartorio + reforma

    return {
        "titulo": titulo,
        "cidade": cidade,
        "lance": lance,
        "avaliado": round(avaliado),
        "desagio": desagio,
        "fonte": fonte,
        "url": url,
        "ocupado": ocupado,
        "debito_iptu": 0,
        "debito_cond": 0,
        "area": area,
        "quartos": quartos,
        "data_leilao": data_leilao,
        "praca": praca,
        "custo_total": custo_total,
    }


def formatar_reais(valor):
    """Formata número como moeda brasileira"""
    return f"R$ {valor:,.0f}".replace(",", ".")


def emoji_status(im):
    if im.get("ocupado") is True:
        return "⚠️"
    if im.get("ocupado") is False:
        return "✅"
    return "🔍"


# ══════════════════════════════════════════════════════════
#  WHATSAPP — CallMeBot (100% gratuito)
# ══════════════════════════════════════════════════════════

def enviar_whatsapp(imoveis, config):
    """
    Envia mensagem WhatsApp via CallMeBot.
    Ativação: salve o número +34 644 44 44 49 e mande:
      'I allow callmebot to send me messages'
    Depois acesse callmebot.com para pegar sua API Key.
    """
    if not config["whatsapp"]["ativo"]:
        log.info("WhatsApp desativado nas configurações.")
        return

    numero = config["whatsapp"]["numero"]
    apikey = config["whatsapp"]["apikey"]

    if "APIKEY" in apikey or "XXXXXXXX" in numero:
        log.warning("Configure WA_NUMERO e WA_APIKEY no .env ou GitHub Secrets!")
        return

    hoje = date.today().strftime("%d/%m/%Y")
    imoveis_reais = [i for i in imoveis if i["lance"] > 0]
    links = [i for i in imoveis if i["lance"] == 0]

    linhas = [f"🏠 *ABC Leilões — {hoje}*\n"]

    if imoveis_reais:
        linhas.append(f"📌 *{len(imoveis_reais)} apartamento(s) na faixa 70–160k:*\n")
        for i, im in enumerate(imoveis_reais[:5], 1):
            linhas.append(
                f"{i}️⃣ *{im['titulo']}*\n"
                f"📍 {im['cidade']}\n"
                f"💰 Lance: {formatar_reais(im['lance'])} | Deságio: {im['desagio']}%\n"
                f"{emoji_status(im)} {'Ocupado' if im.get('ocupado') else 'Ver edital'}\n"
                f"🔗 {im['url']}\n"
            )

    if links:
        linhas.append("🔎 *Busque também nestes sites:*")
        fontes_vistas = set()
        for im in links:
            if im["fonte"] not in fontes_vistas:
                linhas.append(f"• {im['fonte']}: {im['url']}")
                fontes_vistas.add(im["fonte"])

    linhas.append("\n💡 Lembre-se: leia o edital completo antes de dar o lance!")

    mensagem = "\n".join(linhas)

    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={urllib.parse.quote(numero)}"
        f"&text={urllib.parse.quote(mensagem)}"
        f"&apikey={apikey}"
    )

    try:
        log.info("Enviando WhatsApp...")
        if HAS_REQUESTS:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                log.info("✅ WhatsApp enviado!")
            else:
                log.warning(f"WhatsApp retornou {resp.status_code}: {resp.text[:200]}")
        else:
            with urllib.request.urlopen(url, timeout=15) as r:
                log.info(f"✅ WhatsApp enviado! Status: {r.status}")
    except Exception as e:
        log.error(f"Erro ao enviar WhatsApp: {e}")


# ══════════════════════════════════════════════════════════
#  E-MAIL — Gmail SMTP
# ══════════════════════════════════════════════════════════

def gerar_html_email(imoveis, filtros):
    """Gera e-mail HTML bonito com tabela de imóveis"""
    hoje = date.today().strftime("%d/%m/%Y")
    imoveis_reais = [i for i in imoveis if i["lance"] > 0]
    links_busca = [i for i in imoveis if i["lance"] == 0]

    # Remover fontes duplicadas nos links
    fontes_unicas = {}
    for im in links_busca:
        if im["fonte"] not in fontes_unicas:
            fontes_unicas[im["fonte"]] = im["url"]

    rows_imoveis = ""
    for im in imoveis_reais:
        cor_ocupado = "#ef4444" if im.get("ocupado") else "#10b981"
        txt_ocupado = "⚠️ Ocupado" if im.get("ocupado") else "✅ Livre"
        desagio_cor = "#10b981" if im["desagio"] >= 30 else "#f59e0b"

        rows_imoveis += f"""
        <tr style="border-bottom:1px solid #e5e7eb">
          <td style="padding:12px 10px;font-size:14px">
            <strong>{im['titulo']}</strong><br>
            <span style="color:#6b7280;font-size:12px">📍 {im['cidade']} · {im['fonte']}</span>
          </td>
          <td style="padding:12px 10px;text-align:center;font-weight:600;color:#1d4ed8;font-size:14px">
            {formatar_reais(im['lance'])}
          </td>
          <td style="padding:12px 10px;text-align:center;font-weight:600;color:{desagio_cor}">
            -{im['desagio']}%
          </td>
          <td style="padding:12px 10px;text-align:center;font-size:13px;color:{cor_ocupado}">
            {txt_ocupado}
          </td>
          <td style="padding:12px 10px;text-align:center;font-size:13px">
            {im['data_leilao']}
          </td>
          <td style="padding:12px 10px;text-align:center">
            <a href="{im['url']}" style="background:#1d4ed8;color:#fff;padding:6px 14px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600">Ver edital</a>
          </td>
        </tr>"""

    links_html = ""
    for fonte, url in fontes_unicas.items():
        links_html += f"""
        <a href="{url}" style="display:inline-block;margin:4px 6px;background:#f3f4f6;border:1px solid #d1d5db;
           border-radius:8px;padding:8px 16px;text-decoration:none;color:#374151;font-size:13px;font-weight:500">
          🔗 {fonte}
        </a>"""

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f9fafb;font-family:'Segoe UI',sans-serif">
<div style="max-width:680px;margin:0 auto;padding:24px 16px">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a5f,#1d4ed8);border-radius:16px;padding:32px 28px;margin-bottom:20px;color:#fff">
    <div style="font-size:28px;margin-bottom:8px">🏠 ABC Leilões</div>
    <div style="font-size:16px;opacity:.85">Relatório diário — {hoje}</div>
    <div style="margin-top:16px;background:rgba(255,255,255,.12);border-radius:10px;padding:12px 16px;font-size:13px">
      Filtros ativos: Apartamentos · {formatar_reais(filtros['lance_min'])} – {formatar_reais(filtros['lance_max'])} · ABC + São Caetano
    </div>
  </div>

  <!-- Resumo -->
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:20px">
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:24px;font-weight:700;color:#1d4ed8">{len(imoveis_reais)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">Imóveis encontrados</div>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:24px;font-weight:700;color:#10b981">{len(fontes_unicas) + (1 if imoveis_reais else 0)}</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">Plataformas verificadas</div>
    </div>
    <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;text-align:center">
      <div style="font-size:24px;font-weight:700;color:#f59e0b">{max((i['desagio'] for i in imoveis_reais), default=0)}%</div>
      <div style="font-size:12px;color:#6b7280;margin-top:4px">Maior deságio</div>
    </div>
  </div>

  <!-- Tabela de imóveis -->
  {"" if not imoveis_reais else f'''
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;margin-bottom:20px;overflow:hidden">
    <div style="padding:16px 20px;border-bottom:1px solid #e5e7eb">
      <strong>📋 Apartamentos na faixa de preço</strong>
    </div>
    <div style="overflow-x:auto">
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="background:#f9fafb">
          <th style="padding:10px 10px;text-align:left;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Imóvel</th>
          <th style="padding:10px 10px;text-align:center;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Lance</th>
          <th style="padding:10px 10px;text-align:center;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Deságio</th>
          <th style="padding:10px 10px;text-align:center;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Situação</th>
          <th style="padding:10px 10px;text-align:center;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Data</th>
          <th style="padding:10px 10px;text-align:center;font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase">Link</th>
        </tr>
      </thead>
      <tbody>{rows_imoveis}</tbody>
    </table>
    </div>
  </div>'''}

  <!-- Links de busca -->
  <div style="background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin-bottom:20px">
    <div style="font-weight:600;margin-bottom:12px">🔎 Buscar agora nas plataformas</div>
    <div style="font-size:13px;color:#6b7280;margin-bottom:12px">Clique nos links abaixo para ver todos os apartamentos disponíveis hoje com os seus filtros:</div>
    {links_html}
  </div>

  <!-- Checklist rápido -->
  <div style="background:#fef3c7;border:1px solid #fcd34d;border-radius:12px;padding:20px;margin-bottom:20px">
    <div style="font-weight:600;color:#92400e;margin-bottom:10px">📋 Antes de dar um lance — cheque isso:</div>
    <ul style="margin:0;padding-left:18px;color:#78350f;font-size:13px;line-height:2">
      <li>Leia o <strong>edital completo</strong> no site do leiloeiro</li>
      <li>Verifique <strong>IPTU atrasado</strong> no portal da prefeitura</li>
      <li>Ligue para o síndico/administradora para saber o <strong>débito de condomínio</strong></li>
      <li>Consulte a <strong>matrícula do imóvel</strong> no Cartório de Registro de Imóveis</li>
      <li>Verifique se o imóvel está <strong>ocupado</strong> e qual o prazo de desocupação</li>
      <li>Defina seu <strong>lance máximo</strong> antes do leilão e não passe dele</li>
    </ul>
  </div>

  <!-- Footer -->
  <div style="text-align:center;color:#9ca3af;font-size:12px;padding:16px">
    Monitoramento automático pessoal · ABC Leilões<br>
    Este e-mail é para uso pessoal e não constitui assessoria jurídica ou financeira.
  </div>

</div>
</body>
</html>"""
    return html


def enviar_email(imoveis, config, filtros):
    """Envia e-mail HTML via Gmail SMTP"""
    if not config["email"]["ativo"]:
        log.info("E-mail desativado nas configurações.")
        return

    remetente = config["email"]["remetente"]
    senha = config["email"]["senha_app"]
    destinatario = config["email"]["destinatario"]

    if "gmail.com" not in remetente or len(senha) < 10:
        log.warning("Configure EMAIL_REMETENTE e EMAIL_SENHA nas variáveis de ambiente!")
        return

    try:
        log.info("Enviando e-mail...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = config["email"]["assunto"]
        msg["From"] = remetente
        msg["To"] = destinatario

        html_content = gerar_html_email(imoveis, filtros)
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())

        log.info("✅ E-mail enviado com sucesso!")
    except Exception as e:
        log.error(f"Erro ao enviar e-mail: {e}")


# ══════════════════════════════════════════════════════════
#  SALVAR LOG LOCAL
# ══════════════════════════════════════════════════════════

def salvar_log(imoveis):
    """Salva os imóveis encontrados em JSON para histórico"""
    hoje = date.today().isoformat()
    arquivo = f"historico_{hoje}.json"
    with open(arquivo, "w", encoding="utf-8") as f:
        json.dump(imoveis, f, ensure_ascii=False, indent=2, default=str)
    log.info(f"Log salvo em {arquivo}")


# ══════════════════════════════════════════════════════════
#  MAIN — Orquestração principal
# ══════════════════════════════════════════════════════════

def main():
    log.info("=" * 55)
    log.info("  ABC LEILÃO MONITOR — Iniciando busca")
    log.info("=" * 55)

    filtros = CONFIG["filtros"]
    todos_imoveis = []

    # Busca em cada plataforma
    log.info("Buscando na Caixa Econômica Federal...")
    todos_imoveis += buscar_caixa(filtros)

    log.info("Buscando na Sold...")
    todos_imoveis += buscar_sold(filtros)

    log.info("Buscando na Zuk...")
    todos_imoveis += buscar_zuk(filtros)

    log.info("Buscando na Superbid...")
    todos_imoveis += buscar_superbid(filtros)

    log.info("Buscando no Banco do Brasil...")
    todos_imoveis += buscar_banco_brasil(filtros)

    imoveis_reais = [i for i in todos_imoveis if i["lance"] > 0]
    log.info(f"Total: {len(todos_imoveis)} resultados · {len(imoveis_reais)} com preço confirmado")

    # Salvar histórico local
    salvar_log(todos_imoveis)

    # Salvar dados.json para o site GitHub Pages
    try:
        from salvar_json import salvar_dados_json
        salvar_dados_json(todos_imoveis)
    except Exception as e:
        log.warning(f"Erro ao salvar dados.json: {e}")

    # Enviar alertas
    enviar_whatsapp(todos_imoveis, CONFIG)
    time.sleep(3)
    enviar_email(todos_imoveis, CONFIG, filtros)

    log.info("=" * 55)
    log.info("  Monitoramento concluído!")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
