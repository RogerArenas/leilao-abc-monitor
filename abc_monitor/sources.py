from __future__ import annotations

import csv
import io
import time
import urllib.parse
import urllib.request
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

from .config import log
from .geo import caixa_cidade, cidade_para_interface, normalizar_cidade, slug_cidade
from .models import FonteBusca
from .parsing import esta_na_faixa, extrair_area, extrair_numero, extrair_quartos
from .properties import montar_imovel

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

def buscar_caixa_csv(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Usa o endpoint CSV público da Caixa — sem JS, sem scraping frágil.
    URL: https://venda.caixa.gov.br/Downloads/imovel_download.asp
    Retorna CSV com todos os imóveis disponíveis em SP.
    """
    import io
    import csv

    URL_CSV = "https://venda.caixa.gov.br/Downloads/imovel_download.asp"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://venda.caixa.gov.br/imoveis",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    cidades_busca = {normalizar_cidade(c).lower() for c in filtros["cidades"]}
    imoveis: list[dict[str, Any]] = []
    vistos: set[str] = set()

    try:
        log.info("[Caixa CSV] Baixando arquivo CSV oficial...")
        if HAS_REQUESTS:
            resp = requests.get(URL_CSV, headers=HEADERS, timeout=30)
            resp.encoding = "latin-1"
            conteudo = resp.text
        else:
            req = urllib.request.Request(URL_CSV, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                conteudo = r.read().decode("latin-1", errors="ignore")

        leitor = csv.DictReader(
            io.StringIO(conteudo),
            delimiter=";",
        )

        for row in leitor:
            # Normalizar chaves (CSV da Caixa tem cabeçalhos variados)
            row = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}

            # Filtrar por estado SP
            uf = row.get("uf", row.get("estado", "")).upper()
            if uf and uf != "SP":
                continue

            # Cidade
            cidade_csv = row.get("cidade", row.get("municipio", "")).strip()
            cidade_norm = normalizar_cidade(cidade_csv)
            if cidades_busca and cidade_norm.lower() not in cidades_busca:
                continue

            # Tipo — apartamento
            tipo_csv = row.get("tipo", row.get("tipo_imovel", "")).lower()
            if "apto" not in tipo_csv and "apartamento" not in tipo_csv:
                continue

            # Lance / valor
            # LANCE: prioridade correta — campo de entrada, nunca valor_avaliacao
            lance_txt = (
                row.get("preco", "")
                or row.get("valor_minimo", "")
                or row.get("lance_minimo", "")
                or row.get("preco_minimo", "")
                or row.get("lance_minimo", "")
                or ""
            )
            lance = extrair_numero(lance_txt)
            if not esta_na_faixa(lance, filtros):
                continue

            # AVALIADO: agora sim, campo de valor de mercado
            avaliado_txt = (
                row.get("valor_avaliacao", "")
                or row.get("preco_avaliacao", "")
                or row.get("avaliacao", "")
            )
            avaliado = extrair_numero(avaliado_txt) or (lance * 1.3 if lance else 0)

            # Endereço
            bairro = row.get("bairro", "")
            endereco = row.get("endereco", row.get("logradouro", ""))

            # Link do edital
            matricula = row.get("matricula", row.get("num_imovel", ""))
            url_edital = (
                f"https://venda.caixa.gov.br/imoveis/{matricula}"
                if matricula
                else f"https://venda.caixa.gov.br/imoveis?estado=SP&cidade={urllib.parse.quote(cidade_norm)}&tipo=2"
            )

            # Deduplicar
            chave = matricula or f"{cidade_norm}|{lance}|{bairro}"
            if chave in vistos:
                continue
            vistos.add(chave)

            area_txt = row.get("area_total", row.get("area_privativa", row.get("area", "")))
            quartos_txt = row.get("quartos", row.get("dormitorios", ""))

            imoveis.append(montar_imovel(
                titulo=f"Apto {cidade_para_interface(cidade_norm)}" + (f" — {bairro}" if bairro else ""),
                cidade=cidade_para_interface(cidade_norm),
                lance=lance or 0,
                avaliado=avaliado,
                fonte="Caixa",
                url=url_edital,
                area=extrair_area(area_txt) if area_txt else 0,
                quartos=extrair_quartos(quartos_txt) if quartos_txt else 0,
                bairro=bairro,
                matricula=matricula,
                ocupado=None,
            ))

        log.info("[Caixa CSV] %d imóveis encontrados na faixa e cidades", len(imoveis))

    except Exception as exc:
        log.warning("[Caixa CSV] Falha no CSV: %s — usando links de consulta", exc)

    return imoveis

def parse_caixa_cards(html: str, cidade: str, filtros: dict[str, Any], url_base: str) -> list[dict[str, Any]]:
    """Fallback HTML — mantido caso CSV falhe."""
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
    """Tenta CSV oficial primeiro; cai no parser HTML se falhar."""
    imoveis = buscar_caixa_csv(filtros)
    if imoveis:
        return imoveis
    # Fallback: parser HTML cidade por cidade
    log.info("[Caixa] CSV vazio ou falhou — tentando HTML por cidade")
    resultado: list[dict[str, Any]] = []
    for cidade in filtros["cidades"]:
        cidade_norm = normalizar_cidade(cidade)
        url = montar_url_caixa(cidade_norm, filtros)
        try:
            log.info("[Caixa HTML] Buscando em %s", cidade_para_interface(cidade_norm))
            html = http_get(url)
            encontrados = parse_caixa_cards(html, cidade_norm, filtros, url)
            log.info("[Caixa HTML] %s item(ns)", len(encontrados))
            resultado.extend(encontrados)
            time.sleep(1)
        except Exception as exc:
            log.warning("[Caixa HTML] Falha em %s: %s", cidade_para_interface(cidade_norm), exc)
    return resultado

def buscar_links_consulta(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    return [montar_link_consulta(fonte) for fonte in montar_fontes_consulta(filtros)]

