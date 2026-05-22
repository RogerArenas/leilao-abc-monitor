"""
ABC Leilao Monitor

Coleta oportunidades quando a fonte permite leitura publica e sempre gera
links de conferencia manual para os portais relevantes. O objetivo e ser util
sem prometer scraping fragil em sites que mudam ou bloqueiam automacao.
"""

from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from hashlib import sha1
from typing import Any

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


BASE_DIR = Path(__file__).resolve().parent


def carregar_env(caminho: Path = BASE_DIR / ".env") -> None:
    """Carrega variaveis de um .env simples sem sobrescrever o ambiente."""
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(chave, valor)


carregar_env()


CONFIG = {
    "filtros": {
        "lance_min": int(os.getenv("LANCE_MIN", "70000")),
        "lance_max": int(os.getenv("LANCE_MAX", "160000")),
        "tipo": "apartamento",
        "cidades": [
            "Santo Andre",
            "Sao Bernardo do Campo",
            "Maua",
            "Sao Caetano do Sul",
        ],
        "quartos_min": int(os.getenv("QUARTOS_MIN", "2")),
    },
    "whatsapp": {
        "ativo": os.getenv("WA_ATIVO", "true").lower() == "true",
        "numero": os.getenv("WA_NUMERO", "+55119XXXXXXXX"),
        "apikey": os.getenv("WA_APIKEY", "SUA_APIKEY_AQUI"),
    },
    "email": {
        "ativo": os.getenv("EMAIL_ATIVO", "true").lower() == "true",
        "remetente": os.getenv("EMAIL_REMETENTE", "seuemail@gmail.com"),
        "senha_app": os.getenv("EMAIL_SENHA", "xxxx xxxx xxxx xxxx"),
        "destinatario": os.getenv("EMAIL_DEST", "seuemail@gmail.com"),
        "assunto": "ABC Leiloes - Novos apartamentos hoje",
    },
    "alertas": {
        "somente_novos": os.getenv("ALERTAR_SOMENTE_NOVOS", "false").lower() == "true",
        "score_minimo": int(os.getenv("ALERTAR_SCORE_MINIMO", "0")),
        "max_itens": int(os.getenv("ALERTAR_MAX_ITENS", "5")),
    },
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("leilao")


@dataclass(frozen=True)
class FonteBusca:
    nome: str
    url: str
    cidade: str = ""
    tipo: str = "consulta"


def normalizar_cidade(cidade: str) -> str:
    mapa = {
        "Santo André": "Santo Andre",
        "São Bernardo do Campo": "Sao Bernardo do Campo",
        "Mauá": "Maua",
        "São Caetano do Sul": "Sao Caetano do Sul",
    }
    return mapa.get(cidade, cidade)


def cidade_para_interface(cidade: str) -> str:
    mapa = {
        "Santo Andre": "Santo André",
        "Sao Bernardo do Campo": "São Bernardo do Campo",
        "Maua": "Mauá",
        "Sao Caetano do Sul": "São Caetano do Sul",
    }
    return mapa.get(cidade, cidade)


def slug_cidade(cidade: str) -> str:
    return {
        "Santo Andre": "santo-andre",
        "Sao Bernardo do Campo": "sao-bernardo-do-campo",
        "Maua": "maua",
        "Sao Caetano do Sul": "sao-caetano-do-sul",
    }[normalizar_cidade(cidade)]


def caixa_cidade(cidade: str) -> str:
    return {
        "Santo Andre": "SANTO+ANDRE",
        "Sao Bernardo do Campo": "SAO+BERNARDO+DO+CAMPO",
        "Maua": "MAUA",
        "Sao Caetano do Sul": "SAO+CAETANO+DO+SUL",
    }[normalizar_cidade(cidade)]


def http_get(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
        )
    }
    if HAS_REQUESTS:
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.text

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resposta:
        return resposta.read().decode("utf-8", errors="ignore")


def montar_url_caixa(cidade: str, filtros: dict[str, Any]) -> str:
    return (
        "https://venda.caixa.gov.br/imoveis"
        f"?estado=SP&cidade={caixa_cidade(cidade)}"
        "&bairro=&categ=&tipo=2"
        f"&vlMin={filtros['lance_min']}"
        f"&vlMax={filtros['lance_max']}"
        "&submit=Pesquisar"
    )


def montar_fontes_consulta(filtros: dict[str, Any]) -> list[FonteBusca]:
    fontes: list[FonteBusca] = []
    for cidade in filtros["cidades"]:
        cidade_norm = normalizar_cidade(cidade)
        cidade_ui = cidade_para_interface(cidade_norm)
        cidade_url = urllib.parse.quote(cidade_ui)
        slug = slug_cidade(cidade_norm)

        fontes.extend(
            [
                FonteBusca("Caixa", montar_url_caixa(cidade_norm, filtros), cidade_ui),
                FonteBusca(
                    "Sold",
                    "https://www.sold.com.br/leiloes-de-imoveis",
                    cidade_ui,
                ),
                FonteBusca(
                    "Portal Zuk",
                    f"https://www.portalzuk.com.br/leilao-de-imoveis/u/todos-imoveis/sp?search={cidade_url}",
                    cidade_ui,
                ),
                FonteBusca(
                    "Superbid",
                    "https://www.superbid.net/categorias/imoveis",
                    cidade_ui,
                ),
                FonteBusca(
                    "Leilao Imovel",
                    f"https://www.leilaoimovel.com.br/leilao-de-imovel/{slug}-sp",
                    cidade_ui,
                ),
                FonteBusca(
                    "Mega Leiloes",
                    f"https://www.megaleiloes.com.br/imoveis/apartamentos/sp/{slug}",
                    cidade_ui,
                ),
            ]
        )
    return fontes


def extrair_numero(texto: str | None) -> float | None:
    """Extrai valores em formato brasileiro, como R$ 98.500,00."""
    if not texto:
        return None

    candidatos = re.findall(r"\d[\d.,]*", texto)
    for candidato in candidatos:
        valor = candidato.replace(".", "").replace(",", ".")
        try:
            numero = float(valor)
        except ValueError:
            continue
        if numero >= 1_000:
            return numero
    return None


def extrair_area(texto: str) -> int:
    achou = re.search(r"(\d{2,3})\s*m", texto, flags=re.IGNORECASE)
    return int(achou.group(1)) if achou else 0


def extrair_quartos(texto: str) -> int:
    achou = re.search(r"(\d+)\s*(?:quarto|dorm)", texto, flags=re.IGNORECASE)
    return int(achou.group(1)) if achou else 0


def esta_na_faixa(valor: float | None, filtros: dict[str, Any]) -> bool:
    return bool(valor and filtros["lance_min"] <= valor <= filtros["lance_max"])


def montar_imovel(
    titulo: str,
    cidade: str,
    lance: float,
    fonte: str,
    url: str,
    avaliado: float | None = None,
    area: int = 0,
    quartos: int = 0,
    data_leilao: str = "Consulte o site",
    praca: str = "?",
    ocupado: bool | None = None,
    bairro: str = "",
    matricula: str = "",
) -> dict[str, Any]:
    if avaliado is None:
        avaliado = lance * 1.3

    desagio = round(((avaliado - lance) / avaliado) * 100) if avaliado > 0 else 0
    comissao = round(lance * 0.05)
    itbi = round(lance * 0.03)
    cartorio = 3_500
    reforma = round(area * 400) if area > 0 else 15_000

    investimento_total = round(lance + comissao + itbi + cartorio + reforma)
    lucro_potencial = round(avaliado - investimento_total)
    roi_potencial = round((lucro_potencial / investimento_total) * 100, 1) if investimento_total else 0

    imovel = {
        "titulo": titulo.strip() or f"Apartamento em {cidade_para_interface(cidade)}",
        "cidade": cidade_para_interface(cidade),
        "bairro": bairro,
        "lance": round(lance),
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
        "matricula": matricula,
        "custo_total": investimento_total,
        "valor_mercado_estimado": round(avaliado),
        "lucro_potencial": lucro_potencial,
        "roi_potencial": roi_potencial,
        "qualidade_localizacao": estimar_qualidade_localizacao(cidade, bairro),
        "estrategia_sugerida": sugerir_estrategia(area, quartos, roi_potencial, ocupado),
    }
    imovel["score"] = calcular_score(imovel)
    imovel["score_motivos"] = explicar_score(imovel)
    imovel["id"] = gerar_id_imovel(imovel)
    imovel["novo"] = True
    imovel["visto_antes"] = False
    imovel["mudanca"] = ""
    return imovel


def estimar_qualidade_localizacao(cidade: str, bairro: str = "") -> int:
    cidade_norm = normalizar_cidade(cidade)
    base = {
        "Santo Andre": 78,
        "Sao Bernardo do Campo": 76,
        "Sao Caetano do Sul": 86,
        "Maua": 66,
    }.get(cidade_norm, 65)
    bairros_fortes = ("centro", "paraiso", "vila bastos", "boa vista", "santo antonio", "baeta")
    if bairro and any(b in bairro.lower() for b in bairros_fortes):
        base += 6
    return max(0, min(100, base))


def sugerir_estrategia(area: int, quartos: int, roi: float, ocupado: bool | None) -> str:
    if ocupado is True:
        return "Aguardar/regularizar posse"
    if roi >= 18 and area >= 45:
        return "Revenda com margem"
    if quartos >= 2 and area >= 50:
        return "Moradia ou aluguel tradicional"
    if area and area <= 45:
        return "Locacao compacta"
    return "Analisar edital e mercado"


def montar_link_consulta(fonte: FonteBusca) -> dict[str, Any]:
    return {
        "titulo": f"Conferir apartamentos em {fonte.cidade} - {fonte.nome}",
        "cidade": fonte.cidade,
        "lance": 0,
        "avaliado": 0,
        "desagio": 0,
        "fonte": fonte.nome,
        "url": fonte.url,
        "ocupado": None,
        "debito_iptu": 0,
        "debito_cond": 0,
        "area": 0,
        "quartos": 0,
        "data_leilao": "Consulte o site",
        "praca": "?",
        "custo_total": 0,
        "tipo": fonte.tipo,
    }


def parse_caixa_cards(html: str, cidade: str, filtros: dict[str, Any], url_base: str) -> list[dict[str, Any]]:
    if not HAS_BS4:
        return []

    soup = BeautifulSoup(html, "html.parser")
    candidatos = soup.select(
        ".item-imovel, .imovel-card, .resultado-busca, .card, li, tr, [class*='imovel']"
    )
    imoveis: list[dict[str, Any]] = []
    vistos: set[tuple[str, int]] = set()

    for card in candidatos:
        texto = " ".join(card.get_text(" ", strip=True).split())
        if not texto or "apartamento" not in texto.lower():
            continue

        lance = extrair_numero(texto)
        if not esta_na_faixa(lance, filtros):
            continue

        link_el = card.select_one("a[href]")
        link = link_el["href"] if link_el else url_base
        if link.startswith("/"):
            link = "https://venda.caixa.gov.br" + link

        titulo_el = card.select_one("h2, h3, h4, .titulo, .descricao")
        titulo = titulo_el.get_text(" ", strip=True) if titulo_el else texto[:110]
        chave = (link, round(lance or 0))
        if chave in vistos:
            continue
        vistos.add(chave)

        imoveis.append(
            montar_imovel(
                titulo=titulo,
                cidade=cidade,
                lance=lance or 0,
                fonte="Caixa",
                url=link,
                area=extrair_area(texto),
                quartos=extrair_quartos(texto),
                ocupado=None if "ocupado" not in texto.lower() else True,
            )
        )

    return imoveis


def buscar_caixa(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    imoveis: list[dict[str, Any]] = []
    for cidade in filtros["cidades"]:
        cidade_norm = normalizar_cidade(cidade)
        url = montar_url_caixa(cidade_norm, filtros)
        try:
            log.info("[Caixa] Buscando em %s", cidade_para_interface(cidade_norm))
            html = http_get(url)
            encontrados = parse_caixa_cards(html, cidade_norm, filtros, url)
            log.info("[Caixa] %s item(ns) com preco confirmado", len(encontrados))
            imoveis.extend(encontrados)
            time.sleep(1)
        except Exception as exc:
            log.warning("[Caixa] Falha em %s: %s", cidade_para_interface(cidade_norm), exc)
    return imoveis


def buscar_links_consulta(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    return [montar_link_consulta(fonte) for fonte in montar_fontes_consulta(filtros)]


def gerar_id_imovel(imovel: dict[str, Any]) -> str:
    base = "|".join(
        [
            str(imovel.get("fonte", "")).lower(),
            str(imovel.get("url", "")).split("?")[0].lower(),
            str(imovel.get("cidade", "")).lower(),
            str(imovel.get("titulo", "")).lower(),
        ]
    )
    return sha1(base.encode("utf-8")).hexdigest()[:16]


def carregar_historico_anterior() -> list[dict[str, Any]]:
    hoje = f"historico_{date.today().isoformat()}.json"
    arquivos = sorted(BASE_DIR.glob("historico_*.json"), reverse=True)
    for arquivo in arquivos:
        if arquivo.name == hoje:
            continue
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(dados, list):
            return dados
    return []


def anotar_historico(
    imoveis: list[dict[str, Any]],
    historico_anterior: list[dict[str, Any]] | None = None,
) -> dict[str, int]:
    historico_anterior = historico_anterior if historico_anterior is not None else carregar_historico_anterior()
    anteriores: dict[str, dict[str, Any]] = {}

    for item in historico_anterior:
        if item.get("lance", 0) <= 0:
            continue
        item_id = item.get("id") or gerar_id_imovel(item)
        anteriores[item_id] = item

    novos = 0
    alterados = 0
    confirmados = 0

    for item in imoveis:
        if item.get("lance", 0) <= 0:
            continue
        confirmados += 1
        item_id = item.get("id") or gerar_id_imovel(item)
        item["id"] = item_id
        anterior = anteriores.get(item_id)
        item["visto_antes"] = anterior is not None
        item["novo"] = anterior is None
        item["mudanca"] = ""

        if anterior is None:
            novos += 1
            continue

        lance_anterior = int(anterior.get("lance", 0) or 0)
        lance_atual = int(item.get("lance", 0) or 0)
        if lance_anterior and lance_atual and lance_anterior != lance_atual:
            alterados += 1
            delta = lance_atual - lance_anterior
            sinal = "+" if delta > 0 else "-"
            item["mudanca"] = f"Lance {sinal}{formatar_reais(abs(delta))} desde a ultima coleta"

    return {
        "confirmados": confirmados,
        "novos": novos,
        "recorrentes": confirmados - novos,
        "alterados": alterados,
    }


def formatar_reais(valor: float) -> str:
    return f"R$ {valor:,.0f}".replace(",", ".")


def calcular_score(imovel: dict[str, Any]) -> int:
    pontos = 100
    if imovel.get("ocupado") is True:
        pontos -= 30
    if imovel.get("praca") == "2":
        pontos -= 10
    if imovel.get("debito_iptu", 0) > 0:
        pontos -= 15
    if imovel.get("debito_cond", 0) > 0:
        pontos -= 10
    if imovel.get("desagio", 0) >= 35:
        pontos += 10
    if imovel.get("desagio", 0) < 20:
        pontos -= 10
    if not imovel.get("area"):
        pontos -= 3
    if not imovel.get("quartos"):
        pontos -= 3
    return max(0, min(100, pontos))


def explicar_score(imovel: dict[str, Any]) -> list[str]:
    razoes: list[str] = []
    if imovel.get("ocupado") is True:
        razoes.append("ocupado exige plano de posse")
    elif imovel.get("ocupado") is False:
        razoes.append("desocupado tende a ser mais simples")
    else:
        razoes.append("ocupacao precisa ser confirmada")

    if imovel.get("desagio", 0) >= 35:
        razoes.append("desagio forte")
    elif imovel.get("desagio", 0) < 20:
        razoes.append("desagio baixo")

    if imovel.get("debito_iptu", 0) or imovel.get("debito_cond", 0):
        razoes.append("ha debitos informados")
    if not imovel.get("area") or not imovel.get("quartos"):
        razoes.append("dados incompletos")
    return razoes


def dica_do_dia(imoveis_reais: list[dict[str, Any]]) -> str:
    if not imoveis_reais:
        return "Quando nao houver preco confirmado, use os links por cidade e procure venda direta ou edital com ocupacao clara."
    if any(i.get("ocupado") is True for i in imoveis_reais):
        return "Imovel ocupado pode exigir acao de imissao na posse; coloque prazo e custo juridico na conta."
    if any(i.get("desagio", 0) >= 35 for i in imoveis_reais):
        return "Desagio alto chama atencao, mas so vira oportunidade depois de checar edital, matricula e debitos."
    return "Compare o lance com o custo total, nao apenas com o valor de avaliacao."


def filtrar_para_alerta(
    imoveis_reais: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    alertas = config.get("alertas", {})
    score_minimo = int(alertas.get("score_minimo", 0))
    somente_novos = bool(alertas.get("somente_novos", False))

    itens = [i for i in imoveis_reais if calcular_score(i) >= score_minimo]
    if somente_novos:
        itens = [i for i in itens if i.get("novo")]
    return sorted(itens, key=calcular_score, reverse=True)


def emoji_status(imovel: dict[str, Any]) -> str:
    if imovel.get("ocupado") is True:
        return "ATENCAO"
    if imovel.get("ocupado") is False:
        return "OK"
    return "VERIFICAR"


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


def salvar_log(imoveis: list[dict[str, Any]]) -> Path:
    arquivo = BASE_DIR / f"historico_{date.today().isoformat()}.json"
    arquivo.write_text(json.dumps(imoveis, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Historico salvo em %s", arquivo.name)
    return arquivo


def coletar_imoveis(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    imoveis = buscar_caixa(filtros)
    links = buscar_links_consulta(filtros)
    return imoveis + links


def main() -> None:
    log.info("=" * 55)
    log.info("ABC Leilao Monitor - iniciando")
    log.info("=" * 55)

    filtros = CONFIG["filtros"]
    todos_imoveis = coletar_imoveis(filtros)
    resumo_historico = anotar_historico(todos_imoveis)
    imoveis_reais = [i for i in todos_imoveis if i.get("lance", 0) > 0]
    links = [i for i in todos_imoveis if i.get("lance", 0) == 0]

    log.info(
        "Total: %s item(ns), %s com preco confirmado, %s novo(s), %s links de conferencia",
        len(todos_imoveis),
        len(imoveis_reais),
        resumo_historico["novos"],
        len(links),
    )

    salvar_log(todos_imoveis)

    from salvar_json import salvar_dados_json

    salvar_dados_json(todos_imoveis, filtros=filtros)
    enviar_whatsapp(todos_imoveis, CONFIG)
    time.sleep(1)
    enviar_email(todos_imoveis, CONFIG, filtros)

    log.info("Monitoramento concluido.")


if __name__ == "__main__":
    main()
