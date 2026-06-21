from __future__ import annotations

import smtplib
import urllib.parse
import urllib.request
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .config import log
from .scoring import calcular_score, dica_do_dia, emoji_status, explicar_score, filtrar_para_alerta, formatar_reais

def enviar_whatsapp(imoveis: list[dict[str, Any]], config: dict[str, Any]) -> None:
    if not config["whatsapp"]["ativo"]:
        log.info("WhatsApp desativado.")
        return

    numero = config["whatsapp"]["numero"]
    apikey = config["whatsapp"]["apikey"]
    if "APIKEY" in apikey or "XXXXXXXX" in numero:
        log.warning("Configure WA_NUMERO e WA_APIKEY no .env ou GitHub Secrets.")
        return

    hoje = date.today().strftime("%d/%m/%Y")
    imoveis_reais = [i for i in imoveis if i.get("lance", 0) > 0]
    imoveis_alerta = filtrar_para_alerta(imoveis_reais, config)
    links = [i for i in imoveis if i.get("lance", 0) == 0]
    novos = sum(1 for i in imoveis_reais if i.get("novo"))
    max_itens = int(config.get("alertas", {}).get("max_itens", 5))

    linhas = [
        f"*ABC Leiloes - {hoje}*",
        "",
        f"Resumo: {len(imoveis_reais)} com preco confirmado | {novos} novo(s) | {len(links)} links para conferencia.",
        f"Dica: {dica_do_dia(imoveis_reais)}",
    ]
    if imoveis_alerta:
        linhas.append("\nMelhores oportunidades:")
        for indice, imovel in enumerate(imoveis_alerta[:max_itens], 1):
            score = calcular_score(imovel)
            razoes = "; ".join(explicar_score(imovel)[:3])
            etiqueta = "NOVO" if imovel.get("novo") else "recorrente"
            mudanca = f" | {imovel['mudanca']}" if imovel.get("mudanca") else ""
            linhas.append(
                "\n".join(
                    [
                        f"{indice}. [{etiqueta}] {imovel['titulo']}",
                        f"Cidade: {imovel['cidade']}",
                        f"Lance: {formatar_reais(imovel['lance'])} | Desagio: {imovel['desagio']}%",
                        f"Score: {score}/100 | {emoji_status(imovel)} | {razoes}{mudanca}",
                        imovel["url"],
                    ]
                )
            )
    else:
        linhas.append("\nNenhum imovel passou pelos filtros de alerta de hoje.")

    if links:
        linhas.append("\nConferir manualmente:")
        fontes_vistas: set[str] = set()
        for link in links:
            chave = f"{link['fonte']}|{link['cidade']}"
            if chave in fontes_vistas:
                continue
            fontes_vistas.add(chave)
            linhas.append(f"- {link['fonte']} ({link['cidade']}): {link['url']}")

    linhas.append("\nChecklist minimo: edital, matricula, IPTU, condominio, ocupacao e lance maximo.")
    mensagem = "\n".join(linhas)
    url = (
        "https://api.callmebot.com/whatsapp.php"
        f"?phone={urllib.parse.quote(numero)}"
        f"&text={urllib.parse.quote(mensagem)}"
        f"&apikey={urllib.parse.quote(apikey)}"
    )

    try:
        log.info("Enviando WhatsApp...")
        if HAS_REQUESTS:
            resp = requests.get(url, timeout=15)
            if resp.status_code != 200:
                log.warning("WhatsApp retornou %s: %s", resp.status_code, resp.text[:200])
        else:
            with urllib.request.urlopen(url, timeout=15):
                pass
        log.info("WhatsApp enviado.")
    except Exception as exc:
        log.error("Erro ao enviar WhatsApp: %s", exc)

def gerar_html_email(
    imoveis: list[dict[str, Any]],
    filtros: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> str:
    hoje = date.today().strftime("%d/%m/%Y")
    imoveis_reais = [i for i in imoveis if i.get("lance", 0) > 0]
    imoveis_alerta = filtrar_para_alerta(imoveis_reais, config or {})
    links_busca = [i for i in imoveis if i.get("lance", 0) == 0]
    novos = sum(1 for i in imoveis_reais if i.get("novo"))

    rows = []
    for imovel in imoveis_alerta:
        score = calcular_score(imovel)
        razoes = "; ".join(explicar_score(imovel))
        etiqueta = "NOVO" if imovel.get("novo") else "recorrente"
        mudanca = f"<br><small>{imovel['mudanca']}</small>" if imovel.get("mudanca") else ""
        rows.append(
            f"""
            <tr>
              <td><strong>{imovel['titulo']}</strong><br><small>{etiqueta} - {imovel['cidade']} - {imovel['fonte']}</small>{mudanca}</td>
              <td>{formatar_reais(imovel['lance'])}</td>
              <td>{imovel['desagio']}%</td>
              <td>{score}/100<br><small>{razoes}</small></td>
              <td>{imovel['data_leilao']}</td>
              <td><a href="{imovel['url']}">Ver edital</a></td>
            </tr>
            """
        )

    links = []
    vistos: set[str] = set()
    for item in links_busca:
        chave = f"{item['fonte']}|{item['cidade']}"
        if chave in vistos:
            continue
        vistos.add(chave)
        links.append(f'<li><a href="{item["url"]}">{item["fonte"]} - {item["cidade"]}</a></li>')

    corpo = (
        "".join(rows)
        if rows
        else '<tr><td colspan="6">Nenhum imovel com preco confirmado na coleta automatica de hoje.</td></tr>'
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; background:#f6f7fb; color:#172033; }}
    .box {{ max-width: 760px; margin: 0 auto; background:#fff; padding:24px; border-radius:12px; }}
    table {{ width:100%; border-collapse: collapse; margin-top:16px; }}
    th, td {{ border-bottom:1px solid #e5e7eb; padding:10px; text-align:left; }}
    th {{ background:#f9fafb; font-size:12px; text-transform:uppercase; color:#6b7280; }}
    a {{ color:#1d4ed8; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>ABC Leiloes - {hoje}</h1>
    <p>Filtros: apartamentos de {formatar_reais(filtros['lance_min'])} a {formatar_reais(filtros['lance_max'])}.</p>
    <p><strong>Resumo:</strong> {len(imoveis_reais)} imoveis com preco confirmado, {novos} novo(s), {len(imoveis_alerta)} dentro do filtro de alerta e {len(links_busca)} links de conferencia.</p>
    <p><strong>Dica do dia:</strong> {dica_do_dia(imoveis_reais)}</p>
    <table>
      <thead><tr><th>Imovel</th><th>Lance</th><th>Desagio</th><th>Score</th><th>Data</th><th>Link</th></tr></thead>
      <tbody>{corpo}</tbody>
    </table>
    <h2>Conferencia manual recomendada</h2>
    <ul>{"".join(links)}</ul>
    <h2>Guia rapido</h2>
    <ul>
      <li><strong>Venda direta:</strong> preco mais previsivel, mas ainda depende de edital e debitos.</li>
      <li><strong>Venda online:</strong> disputa pela internet; confirme cadastro, caucao e horario final.</li>
      <li><strong>Licitacao aberta:</strong> proposta formal conforme criterio do edital.</li>
      <li><strong>2a praca:</strong> pode ter desconto maior, mas merece verificacao redobrada.</li>
    </ul>
    <p><strong>Checklist:</strong> leia o edital, consulte IPTU, confirme condominio, matricula, ocupacao e custo total.</p>
  </div>
</body>
</html>"""

def enviar_email(imoveis: list[dict[str, Any]], config: dict[str, Any], filtros: dict[str, Any]) -> None:
    if not config["email"]["ativo"]:
        log.info("E-mail desativado.")
        return

    remetente = config["email"]["remetente"]
    senha = config["email"]["senha_app"]
    destinatario = config["email"]["destinatario"]
    if remetente == "seuemail@gmail.com" or len(senha.replace(" ", "")) < 16:
        log.warning("Configure EMAIL_REMETENTE e EMAIL_SENHA no .env ou GitHub Secrets.")
        return

    try:
        log.info("Enviando e-mail...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = config["email"]["assunto"]
        msg["From"] = remetente
        msg["To"] = destinatario
        msg.attach(MIMEText(gerar_html_email(imoveis, filtros, config), "html", "utf-8"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(remetente, senha)
            server.sendmail(remetente, destinatario, msg.as_string())
        log.info("E-mail enviado.")
    except Exception as exc:
        log.error("Erro ao enviar e-mail: %s", exc)

