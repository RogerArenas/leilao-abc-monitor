"""
ABC Leilões Monitor
===================
Estratégia gratuita em duas camadas:

  CAMADA 1 — Caixa Econômica Federal (CSV público oficial)
    URL: https://venda.caixa.gov.br/Downloads/imovel_download.asp
    - Sem Cloudflare, sem JS, download direto
    - Maior volume de leilões do Brasil
    - Funciona 100% no GitHub Actions

  CAMADA 2 — Serper.dev (Google Search API, 2500 buscas/mês grátis)
    - Busca nos demais portais (Zuk, Leilão Imóvel, Mega, Sold, WebLeilões)
    - Extrai preços e links dos snippets do Google
    - Sem Cloudflare: é uma API REST simples
    - Cadastro grátis em https://serper.dev

  FALLBACK — Links de conferência manual
    - Sempre gerados para cada portal e cidade

Configuração mínima: só a CAMADA 1 já traz resultados reais da Caixa.
SERPER_API_KEY é opcional (mas gratuita).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import smtplib
import time
import urllib.parse
import urllib.request
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import sha1
from pathlib import Path
from typing import Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BASE_DIR = Path(__file__).resolve().parent
log = logging.getLogger("leilao")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# ── ENV ───────────────────────────────────────────────────────────────────────

def carregar_env(caminho: Path = BASE_DIR / ".env") -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

carregar_env()

CONFIG = {
    "filtros": {
        "lance_min": int(os.getenv("LANCE_MIN", "70000")),
        "lance_max": int(os.getenv("LANCE_MAX", "160000")),
        "tipo": "apartamento",
        "cidades": ["Santo André", "São Bernardo do Campo", "Mauá", "São Caetano do Sul"],
        "quartos_min": int(os.getenv("QUARTOS_MIN", "2")),
    },
    "serper": {
        "api_key": os.getenv("SERPER_API_KEY", ""),
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
        "assunto": "ABC Leilões - Novos apartamentos hoje",
    },
    "alertas": {
        "somente_novos": os.getenv("ALERTAR_SOMENTE_NOVOS", "false").lower() == "true",
        "score_minimo": int(os.getenv("ALERTAR_SCORE_MINIMO", "0")),
        "max_itens": int(os.getenv("ALERTAR_MAX_ITENS", "5")),
    },
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

CIDADES_NORM = {
    "SANTO ANDRE": "Santo André",
    "SANTO ANDRÉ": "Santo André",
    "SAO BERNARDO DO CAMPO": "São Bernardo do Campo",
    "SÃO BERNARDO DO CAMPO": "São Bernardo do Campo",
    "MAUA": "Mauá",
    "MAUÁ": "Mauá",
    "SAO CAETANO DO SUL": "São Caetano do Sul",
    "SÃO CAETANO DO SUL": "São Caetano do Sul",
}

def normalizar_cidade(cidade: str) -> str | None:
    """Retorna nome formatado ou None se não for uma das 4 cidades alvo."""
    upper = cidade.strip().upper()
    # Remover acentos para comparação
    import unicodedata
    sem_acento = unicodedata.normalize("NFD", upper).encode("ascii", "ignore").decode("ascii")
    for k, v in CIDADES_NORM.items():
        k_sem = unicodedata.normalize("NFD", k).encode("ascii", "ignore").decode("ascii")
        if sem_acento == k_sem:
            return v
    return None

def extrair_reais(texto: str) -> float | None:
    """Extrai primeiro valor monetário entre 50k e 800k do texto.

    Suporta todos os formatos encontrados na prática:
      - CSV Caixa:    "98500,00"  ou  "98.500,00"
      - Display:      "R$ 98.500,00"  ou  "R$98500"
      - Número limpo: "98500"
    """
    if not texto:
        return None

    candidatos: list[float] = []

    # 1) Com prefixo R$ (display)
    for m in re.findall(r"R\$\s*([\d.,]+)", texto):
        try:
            n = float(m.replace(".", "").replace(",", "."))
            if 50_000 <= n <= 800_000:
                candidatos.append(n)
        except ValueError:
            pass

    # 2) Número com separador de milhar por ponto: "98.500" ou "98.500,00"
    for m in re.findall(r"\b(\d{2,3}\.\d{3}(?:,\d{2})?)\b", texto):
        try:
            n = float(m.replace(".", "").replace(",", "."))
            if 50_000 <= n <= 800_000:
                candidatos.append(n)
        except ValueError:
            pass

    # 3) Número CSV bruto com vírgula decimal: "98500,00"
    for m in re.findall(r"\b(\d{5,6}),(\d{2})\b", texto):
        try:
            n = float(f"{m[0]}.{m[1]}")
            if 50_000 <= n <= 800_000:
                candidatos.append(n)
        except ValueError:
            pass

    # 4) Inteiro puro: "98500"
    for m in re.findall(r"\b(\d{5,6})\b", texto):
        try:
            n = float(m)
            if 50_000 <= n <= 800_000:
                candidatos.append(n)
        except ValueError:
            pass

    return min(candidatos) if candidatos else None

def extrair_area(texto: str) -> int:
    m = re.search(r"(\d{2,3})\s*m[²2]?", texto, re.IGNORECASE)
    return int(m.group(1)) if m else 0

def extrair_quartos(texto: str) -> int:
    m = re.search(r"(\d+)\s*(?:quarto|dorm|suite|dorms?\.?)", texto, re.IGNORECASE)
    return int(m.group(1)) if m else 0

def extrair_praca(texto: str) -> str:
    if re.search(r"2[aª]\s*pra[çc]a|segunda\s*pra[çc]a", texto, re.IGNORECASE):
        return "2"
    if re.search(r"1[aª]\s*pra[çc]a|primeira\s*pra[çc]a", texto, re.IGNORECASE):
        return "1"
    if re.search(r"venda\s*direta|venda\s*online|licitacao|licitação", texto, re.IGNORECASE):
        return "1"
    return "?"

def extrair_ocupado(texto: str) -> bool | None:
    if re.search(r"desocupado|livre|vazio|devolv", texto, re.IGNORECASE):
        return False
    if re.search(r"\bocupado\b|ocupação|posse|inquilino|imissao|imissão", texto, re.IGNORECASE):
        return True
    return None

def formatar_reais(valor: float) -> str:
    return f"R$ {round(valor):,}".replace(",", ".")

def esta_na_faixa(valor: float | None, filtros: dict) -> bool:
    return bool(valor and filtros["lance_min"] <= valor <= filtros["lance_max"])

def gerar_id(imovel: dict) -> str:
    base = "|".join([
        str(imovel.get("fonte", "")).lower(),
        str(imovel.get("url", "")).split("?")[0].lower(),
        str(imovel.get("cidade", "")).lower(),
        str(imovel.get("lance", 0)),
    ])
    return sha1(base.encode()).hexdigest()[:16]

def estimar_localizacao(cidade: str, bairro: str = "") -> int:
    base = {
        "Santo André": 78, "São Bernardo do Campo": 76,
        "São Caetano do Sul": 86, "Mauá": 66,
    }.get(cidade, 65)
    bons = ("centro", "paraiso", "vila bastos", "boa vista", "santo antonio", "baeta")
    if bairro and any(b in bairro.lower() for b in bons):
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
        return "Locação compacta"
    return "Analisar edital e mercado"

def calcular_score(im: dict) -> int:
    p = 100
    if im.get("ocupado") is True: p -= 30
    if im.get("praca") == "2": p -= 10
    if im.get("debito_iptu", 0) > 0: p -= 15
    if im.get("debito_cond", 0) > 0: p -= 10
    if im.get("desagio", 0) >= 35: p += 10
    if im.get("desagio", 0) < 20: p -= 10
    if not im.get("area"): p -= 3
    if not im.get("quartos"): p -= 3
    return max(0, min(100, p))

def explicar_score(im: dict) -> list[str]:
    r = []
    if im.get("ocupado") is True: r.append("ocupado exige plano de posse")
    elif im.get("ocupado") is False: r.append("desocupado tende a ser mais simples")
    else: r.append("ocupacao precisa ser confirmada")
    if im.get("desagio", 0) >= 35: r.append("desagio forte")
    elif im.get("desagio", 0) < 20: r.append("desagio baixo")
    if im.get("debito_iptu", 0) or im.get("debito_cond", 0): r.append("ha debitos informados")
    if not im.get("area") or not im.get("quartos"): r.append("dados incompletos no edital")
    return r

def montar_imovel(titulo, cidade, lance, fonte, url, avaliado=None, area=0, quartos=0,
                  data_leilao="Consulte o site", praca="?", ocupado=None,
                  bairro="", matricula="") -> dict:
    if avaliado is None or avaliado <= lance:
        avaliado = lance * 1.35
    desagio = round(((avaliado - lance) / avaliado) * 100) if avaliado > 0 else 0
    comissao = round(lance * 0.05)
    itbi = round(lance * 0.03)
    cartorio = 3_500
    reforma = round(area * 400) if area > 0 else 15_000
    investimento = round(lance + comissao + itbi + cartorio + reforma)
    lucro = round(avaliado - investimento)
    roi = round((lucro / investimento) * 100, 1) if investimento else 0

    im = {
        "titulo": titulo.strip() or f"Apartamento em {cidade}",
        "cidade": cidade,
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
        "custo_total": investimento,
        "valor_mercado_estimado": round(avaliado),
        "lucro_potencial": lucro,
        "roi_potencial": roi,
        "qualidade_localizacao": estimar_localizacao(cidade, bairro),
        "estrategia_sugerida": sugerir_estrategia(area, quartos, roi, ocupado),
        "novo": True,
        "visto_antes": False,
        "mudanca": "",
    }
    im["score"] = calcular_score(im)
    im["score_motivos"] = explicar_score(im)
    im["id"] = gerar_id(im)
    return im

# ── HTTP ──────────────────────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 30, encoding: str = "utf-8") -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    if HAS_REQUESTS:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        r.encoding = encoding
        return r.text
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode(encoding, errors="ignore")

# ── CAMADA 1: CAIXA CSV ───────────────────────────────────────────────────────

URL_CAIXA_CSV = "https://venda.caixa.gov.br/Downloads/imovel_download.asp"
# URL alternativa com mais detalhes (quartos, área, praça)
URL_CAIXA_CSV_DETALHE = "https://venda.caixa.gov.br/Downloads/imovel_download_detalhe.asp"

def _parse_csv_caixa(conteudo: str, filtros: dict) -> list[dict]:
    """Parseia o CSV da Caixa e retorna imóveis dentro dos filtros."""
    imoveis: list[dict] = []
    vistos: set[str] = set()

    try:
        leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    except Exception as e:
        log.warning("[Caixa CSV] Erro ao criar DictReader: %s", e)
        return []

    cabecalhos_ok = False
    for row in leitor:
        # Normalizar chaves
        row = {k.strip().lower().replace(" ", "_"): (v or "").strip() for k, v in row.items()}

        if not cabecalhos_ok:
            log.info("[Caixa CSV] Colunas: %s", list(row.keys()))
            cabecalhos_ok = True

        # Filtrar por UF
        uf = row.get("uf", row.get("estado", "")).upper().strip()
        if uf and uf != "SP":
            continue

        # Cidade
        cidade_raw = row.get("cidade", row.get("municipio", "")).strip()
        cidade = normalizar_cidade(cidade_raw)
        if cidade is None:
            continue

        # Tipo — apenas apartamento
        desc = row.get("descricao", row.get("tipo", row.get("tipo_imovel", ""))).lower()
        if not re.search(r"apto|apart", desc):
            continue

        # Lance — campo correto: "preco" no CSV simples, "valor_minimo" no detalhe
        lance_raw = (
            row.get("preco", "")
            or row.get("valor_minimo", "")
            or row.get("lance_minimo", "")
            or row.get("preco_minimo", "")
            or ""
        )
        lance = extrair_reais(lance_raw) or extrair_reais(lance_raw.replace(",", ".").replace(".", "", lance_raw.count(".") - 1))
        if lance is None:
            # Tentar extrair número direto (formato: 98500,00)
            try:
                lance = float(lance_raw.replace(".", "").replace(",", "."))
            except Exception:
                lance = None
        if not esta_na_faixa(lance, filtros):
            continue

        # Avaliação
        aval_raw = (
            row.get("valor_avaliacao", "")
            or row.get("avaliacao", "")
            or row.get("preco_avaliacao", "")
            or ""
        )
        avaliado: float | None = None
        try:
            avaliado = float(aval_raw.replace(".", "").replace(",", ".")) if aval_raw else None
        except ValueError:
            avaliado = extrair_reais(aval_raw)

        # Campos extras do CSV detalhe
        area_raw = row.get("area_total", row.get("area_privativa", row.get("area", "")))
        quartos_raw = row.get("quartos", row.get("dormitorios", row.get("dorms", desc)))
        area = extrair_area(area_raw) if area_raw else extrair_area(desc)
        quartos = 0
        if quartos_raw and quartos_raw != desc:
            try:
                quartos = int(quartos_raw)
            except ValueError:
                quartos = extrair_quartos(quartos_raw)
        if not quartos:
            quartos = extrair_quartos(desc)

        # Filtro de quartos mínimos
        qmin = filtros.get("quartos_min", 0)
        if qmin and quartos and quartos < qmin:
            continue

        # Ocupação e praça
        ocupado = extrair_ocupado(desc + " " + row.get("modalidade", ""))
        praca = extrair_praca(row.get("modalidade", "") + " " + desc)

        # URL
        matricula = row.get("matricula", row.get("num_imovel", row.get("numero_imovel", "")))
        link = row.get("link_acesso", row.get("link", row.get("url", "")))
        if not link:
            if matricula:
                link = f"https://venda.caixa.gov.br/imoveis/{matricula}"
            else:
                cidade_url = urllib.parse.quote(cidade_raw.upper())
                link = f"https://venda.caixa.gov.br/imoveis?estado=SP&cidade={cidade_url}&tipo=2"

        # Bairro e endereço
        bairro = row.get("bairro", "")
        titulo_base = f"Apto {cidade}{' — ' + bairro if bairro else ''}"

        # Deduplicar
        chave = matricula or f"{cidade}|{round(lance or 0)}"
        if chave in vistos:
            continue
        vistos.add(chave)

        imoveis.append(montar_imovel(
            titulo=titulo_base,
            cidade=cidade,
            lance=lance or 0,
            avaliado=avaliado,
            fonte="Caixa",
            url=link,
            area=area,
            quartos=quartos,
            data_leilao=row.get("data_leilao", row.get("data", "Consulte o site")),
            praca=praca,
            ocupado=ocupado,
            bairro=bairro,
            matricula=matricula,
        ))

    return imoveis


def buscar_caixa(filtros: dict) -> list[dict]:
    """Tenta CSV detalhado e CSV simples da Caixa. Sem JS, sem Cloudflare."""
    for url, nome in [
        (URL_CAIXA_CSV_DETALHE, "CSV detalhe"),
        (URL_CAIXA_CSV, "CSV simples"),
    ]:
        try:
            log.info("[Caixa] Baixando %s...", nome)
            conteudo = http_get(url, encoding="latin-1")
            log.info("[Caixa] Download OK — %d KB", len(conteudo) // 1024)
            imoveis = _parse_csv_caixa(conteudo, filtros)
            log.info("[Caixa] %d apartamento(s) encontrado(s) na faixa e cidades", len(imoveis))
            if imoveis:
                return imoveis
        except Exception as e:
            log.warning("[Caixa] %s falhou: %s", nome, e)

    log.warning("[Caixa] Ambos os CSVs falharam.")
    return []


# ── CAMADA 2: SERPER.DEV (Google Search API gratuita) ─────────────────────────

SERPER_URL = "https://google.serper.dev/search"

QUERIES_SERPER = [
    'apartamento leilão "Santo André" OR "São Bernardo" OR "Mauá" OR "São Caetano" lance',
    'site:leilaoimovel.com.br apartamento "santo-andre" OR "sao-bernardo" OR "maua" OR "sao-caetano"',
    'site:megaleiloes.com.br apartamento SP "santo andre" OR "sao bernardo" OR "maua"',
    'site:portalzuk.com.br apartamento ABC paulista leilão',
    'site:webleiloes.com.br apartamento "santo andre" OR "sao bernardo" leilão lance',
    'site:sold.com.br leilão apartamento ABC paulista',
    'leilão apartamento ABC paulista R$ lance mínimo 2025',
]

def buscar_serper(filtros: dict) -> list[dict]:
    """Busca via Serper.dev (Google Search API). 2500 buscas/mês grátis."""
    api_key = CONFIG["serper"].get("api_key", "")
    if not api_key or len(api_key) < 10:
        log.info("[Serper] SERPER_API_KEY não configurada — pulando.")
        return []

    if not HAS_REQUESTS:
        log.warning("[Serper] requests não instalado.")
        return []

    imoveis: list[dict] = []
    vistos: set[str] = set()

    for query in QUERIES_SERPER:
        try:
            log.info("[Serper] Query: %s", query[:60])
            resp = requests.post(
                SERPER_URL,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "gl": "br", "hl": "pt-br", "num": 10},
                timeout=15,
            )
            if resp.status_code != 200:
                log.warning("[Serper] HTTP %s na query: %s", resp.status_code, query[:40])
                continue

            data = resp.json()
            results = data.get("organic", [])
            log.info("[Serper] %d resultados orgânicos", len(results))

            for r in results:
                titulo = r.get("title", "")
                link = r.get("link", "")
                snippet = r.get("snippet", "")
                texto = titulo + " " + snippet

                # Precisa ter link real de portal de leilão
                portais_validos = (
                    "leilaoimovel.com.br", "megaleiloes.com.br", "portalzuk.com.br",
                    "webleiloes.com.br", "sold.com.br", "venda.caixa.gov.br",
                    "superbid.net", "bb.com.br", "leiloes.bb.com.br",
                    "zuk.com.br", "lance.com.br", "d1lance.com.br",
                )
                if not any(p in link for p in portais_validos):
                    continue

                # Detectar cidade
                cidade = None
                for c in filtros["cidades"]:
                    if c.lower() in texto.lower() or any(
                        p.lower() in texto.lower() for p in c.split()
                    ):
                        cidade = c
                        break
                if not cidade:
                    continue

                # Precisa conter palavras-chave de apartamento
                if not re.search(r"apto|apart|dormit|quarto|m²|m2", texto, re.IGNORECASE):
                    continue

                # Extrair lance
                lance = extrair_reais(texto)
                if not esta_na_faixa(lance, filtros):
                    continue

                # Deduplicar por URL
                if link in vistos:
                    continue
                vistos.add(link)

                # Identificar fonte pelo domínio
                fonte = "Web"
                for nome, dominio in [
                    ("Leilão Imóvel", "leilaoimovel.com.br"),
                    ("Mega Leilões", "megaleiloes.com.br"),
                    ("Portal Zuk", "portalzuk.com.br"),
                    ("WebLeilões", "webleiloes.com.br"),
                    ("Sold", "sold.com.br"),
                    ("Caixa", "caixa.gov.br"),
                    ("Banco do Brasil", "bb.com.br"),
                    ("Superbid", "superbid.net"),
                ]:
                    if dominio in link:
                        fonte = nome
                        break

                area = extrair_area(texto)
                quartos = extrair_quartos(texto)
                qmin = filtros.get("quartos_min", 0)
                if qmin and quartos and quartos < qmin:
                    continue

                im = montar_imovel(
                    titulo=titulo[:100],
                    cidade=cidade,
                    lance=lance,
                    fonte=fonte,
                    url=link,
                    area=area,
                    quartos=quartos,
                    praca=extrair_praca(texto),
                    ocupado=extrair_ocupado(texto),
                )
                imoveis.append(im)
                log.info("[Serper] ✓ %s — R$ %s — %s", cidade, formatar_reais(lance), link[:60])

            time.sleep(0.5)  # rate limit gentil

        except Exception as e:
            log.warning("[Serper] Erro na query '%s': %s", query[:40], e)

    log.info("[Serper] Total: %d imóvel(is) encontrado(s)", len(imoveis))
    return imoveis


# ── LINKS DE CONFERÊNCIA MANUAL ───────────────────────────────────────────────

def gerar_links_consulta(filtros: dict) -> list[dict]:
    links = []
    slug_map = {
        "Santo André": "santo-andre",
        "São Bernardo do Campo": "sao-bernardo-do-campo",
        "Mauá": "maua",
        "São Caetano do Sul": "sao-caetano-do-sul",
    }
    caixa_map = {
        "Santo André": "SANTO+ANDRE",
        "São Bernardo do Campo": "SAO+BERNARDO+DO+CAMPO",
        "Mauá": "MAUA",
        "São Caetano do Sul": "SAO+CAETANO+DO+SUL",
    }
    lmin, lmax = filtros["lance_min"], filtros["lance_max"]

    for cidade in filtros["cidades"]:
        slug = slug_map.get(cidade, cidade.lower().replace(" ", "-"))
        caixa = caixa_map.get(cidade, urllib.parse.quote(cidade.upper()))

        for nome, url in [
            ("Caixa", f"https://venda.caixa.gov.br/imoveis?estado=SP&cidade={caixa}&tipo=2&vlMin={lmin}&vlMax={lmax}"),
            ("Leilão Imóvel", f"https://www.leilaoimovel.com.br/leilao-de-imovel/{slug}-sp"),
            ("Mega Leilões", f"https://www.megaleiloes.com.br/imoveis/apartamentos/sp/{slug}"),
            ("Portal Zuk", f"https://www.portalzuk.com.br/leilao-de-imoveis/c/todos-imoveis/sp/grande-sao-paulo/{slug}"),
            ("WebLeilões", "https://www.webleiloes.com.br/"),
            ("Sold", "https://www.sold.com.br/leiloes-de-imoveis"),
        ]:
            links.append({
                "titulo": f"Conferir apartamentos em {cidade} — {nome}",
                "cidade": cidade, "fonte": nome, "url": url,
                "lance": 0, "avaliado": 0, "desagio": 0,
                "ocupado": None, "debito_iptu": 0, "debito_cond": 0,
                "area": 0, "quartos": 0, "data_leilao": "Consulte o site",
                "praca": "?", "custo_total": 0, "tipo": "consulta",
            })
    return links


# ── HISTÓRICO ─────────────────────────────────────────────────────────────────

def carregar_historico() -> list[dict]:
    hoje = f"historico_{date.today().isoformat()}.json"
    for arq in sorted(BASE_DIR.glob("historico_*.json"), reverse=True):
        if arq.name == hoje:
            continue
        try:
            dados = json.loads(arq.read_text(encoding="utf-8"))
            if isinstance(dados, list):
                return dados
        except Exception:
            continue
    return []

def anotar_historico(imoveis: list[dict]) -> dict:
    anteriores = {
        (i.get("id") or gerar_id(i)): i
        for i in carregar_historico()
        if i.get("lance", 0) > 0
    }
    novos = alterados = confirmados = 0
    for im in imoveis:
        if im.get("lance", 0) <= 0:
            continue
        confirmados += 1
        id_ = im.get("id") or gerar_id(im)
        im["id"] = id_
        ant = anteriores.get(id_)
        im["visto_antes"] = ant is not None
        im["novo"] = ant is None
        if ant is None:
            novos += 1
        else:
            la, la2 = int(ant.get("lance", 0)), int(im.get("lance", 0))
            if la and la2 and la != la2:
                alterados += 1
                delta = la2 - la
                im["mudanca"] = f"Lance {'+'if delta>0 else ''}{formatar_reais(abs(delta))} desde a última coleta"
    return {"confirmados": confirmados, "novos": novos, "alterados": alterados}

def salvar_historico(imoveis: list[dict]) -> None:
    arq = BASE_DIR / f"historico_{date.today().isoformat()}.json"
    arq.write_text(json.dumps(imoveis, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Histórico salvo: %s", arq.name)


# ── ALERTAS ───────────────────────────────────────────────────────────────────

def dica_do_dia(reais: list[dict]) -> str:
    if not reais:
        return "Sem preço confirmado hoje. Use os links para conferir os portais manualmente."
    if any(i.get("ocupado") is True for i in reais):
        return "Imóvel ocupado pode exigir imissão na posse — coloque custo jurídico e prazo na conta."
    if any(i.get("desagio", 0) >= 35 for i in reais):
        return "Deságio alto é atrativo, mas cheque edital, matrícula e débitos antes de qualquer lance."
    return "Compare o custo total (lance + comissão + ITBI + cartório + reforma), não só o lance."

def filtrar_alertas(reais: list[dict], config: dict) -> list[dict]:
    al = config.get("alertas", {})
    score_min = int(al.get("score_minimo", 0))
    so_novos = bool(al.get("somente_novos", False))
    itens = [i for i in reais if calcular_score(i) >= score_min]
    if so_novos:
        itens = [i for i in itens if i.get("novo")]
    return sorted(itens, key=calcular_score, reverse=True)

def enviar_whatsapp(imoveis: list[dict], config: dict) -> None:
    if not config["whatsapp"]["ativo"]:
        return
    numero = config["whatsapp"]["numero"]
    apikey = config["whatsapp"]["apikey"]
    if "APIKEY" in apikey or "XXXXXXXX" in numero:
        log.warning("Configure WA_NUMERO e WA_APIKEY no .env ou GitHub Secrets.")
        return

    reais = [i for i in imoveis if i.get("lance", 0) > 0]
    alertas = filtrar_alertas(reais, config)
    links = [i for i in imoveis if i.get("lance", 0) == 0]
    hoje = date.today().strftime("%d/%m/%Y")
    max_itens = int(config.get("alertas", {}).get("max_itens", 5))

    linhas = [
        f"*ABC Leilões — {hoje}*",
        f"📊 {len(reais)} com preço confirmado | {sum(1 for i in reais if i.get('novo'))} novo(s)",
        f"💡 {dica_do_dia(reais)}",
    ]
    if alertas:
        linhas.append("\n🏠 Melhores oportunidades:")
        for n, im in enumerate(alertas[:max_itens], 1):
            sc = calcular_score(im)
            tag = "NOVO ✦" if im.get("novo") else "recorrente"
            linhas.append(
                f"{n}. [{tag}] {im['titulo']}\n"
                f"📍 {im['cidade']}\n"
                f"💰 {formatar_reais(im['lance'])} | -{im.get('desagio',0)}% deságio\n"
                f"🎯 Score {sc}/100 | {im['fonte']}\n"
                f"🔗 {im['url']}"
            )
    else:
        linhas.append("\nNenhum imóvel passou pelos filtros hoje.")

    if links and len(reais) == 0:
        linhas.append("\n🔍 Conferência manual recomendada:")
        vistos: set = set()
        for l in links[:6]:
            k = f"{l['fonte']}|{l['cidade']}"
            if k in vistos:
                continue
            vistos.add(k)
            linhas.append(f"• {l['fonte']} ({l['cidade']}): {l['url']}")

    mensagem = "\n".join(linhas)
    url = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={urllib.parse.quote(numero)}"
        f"&text={urllib.parse.quote(mensagem)}"
        f"&apikey={urllib.parse.quote(apikey)}"
    )
    try:
        log.info("Enviando WhatsApp...")
        if HAS_REQUESTS:
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                log.warning("WhatsApp HTTP %s", r.status_code)
        else:
            urllib.request.urlopen(url, timeout=15)
        log.info("WhatsApp enviado.")
    except Exception as e:
        log.error("Erro WhatsApp: %s", e)

def enviar_email(imoveis: list[dict], config: dict, filtros: dict) -> None:
    if not config["email"]["ativo"]:
        return
    rem = config["email"]["remetente"]
    senha = config["email"]["senha_app"]
    dest = config["email"]["destinatario"]
    if rem == "seuemail@gmail.com" or len(senha.replace(" ", "")) < 16:
        log.warning("Configure EMAIL_REMETENTE e EMAIL_SENHA.")
        return

    reais = [i for i in imoveis if i.get("lance", 0) > 0]
    alertas = filtrar_alertas(reais, config)
    links = [i for i in imoveis if i.get("lance", 0) == 0]
    hoje = date.today().strftime("%d/%m/%Y")

    rows = "".join(f"""
        <tr>
          <td><strong>{i['titulo']}</strong><br>
              <small>{'✦ NOVO' if i.get('novo') else 'recorrente'} · {i['cidade']} · {i['fonte']}</small>
              {f"<br><small style='color:green'>{i['mudanca']}</small>" if i.get('mudanca') else ''}
          </td>
          <td>{formatar_reais(i['lance'])}</td>
          <td>{i.get('desagio', 0)}%</td>
          <td>{calcular_score(i)}/100</td>
          <td>{i.get('data_leilao', '—')}</td>
          <td><a href="{i['url']}">Ver edital ↗</a></td>
        </tr>""" for i in alertas) or '<tr><td colspan="6">Nenhum imóvel com preço confirmado hoje.</td></tr>'

    vistos2: set = set()
    links_html = ""
    for l in links:
        k = f"{l['fonte']}|{l['cidade']}"
        if k in vistos2:
            continue
        vistos2.add(k)
        links_html += f'<li><a href="{l["url"]}">{l["fonte"]} — {l["cidade"]}</a></li>'

    html = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>
body{{font-family:Arial,sans-serif;background:#f6f7fb;color:#172033;margin:0;padding:20px}}
.box{{max-width:760px;margin:0 auto;background:#fff;padding:28px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
h1{{font-size:20px;color:#1a2744;margin-bottom:4px}}
p{{font-size:13px;color:#475569;margin:8px 0}}
table{{width:100%;border-collapse:collapse;margin-top:16px;font-size:13px}}
th,td{{border-bottom:1px solid #e5e7eb;padding:10px 12px;text-align:left}}
th{{background:#f8f9fc;font-size:11px;text-transform:uppercase;color:#6b7280;font-weight:700}}
a{{color:#1d4ed8}}
.dica{{background:#fef3c7;border:1px solid #fde68a;border-radius:8px;padding:12px;margin:12px 0;font-size:13px;color:#78350f}}
</style></head><body><div class="box">
<h1>🏠 ABC Leilões — {hoje}</h1>
<p>Filtro: apartamentos {formatar_reais(filtros['lance_min'])} – {formatar_reais(filtros['lance_max'])} · {filtros.get('quartos_min',1)}+ quartos · ABC Paulista</p>
<p><strong>Resumo:</strong> {len(reais)} com preço confirmado · {sum(1 for i in reais if i.get('novo'))} novo(s) · {len(alertas)} no alerta</p>
<div class="dica">💡 {dica_do_dia(reais)}</div>
<table>
<thead><tr><th>Imóvel</th><th>Lance</th><th>Deságio</th><th>Score</th><th>Data</th><th>Link</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 style="font-size:15px;margin-top:24px">🔍 Conferência manual</h2>
<ul style="font-size:13px">{links_html}</ul>
<p style="font-size:11px;color:#94a3b8;margin-top:20px;border-top:1px solid #e5e7eb;padding-top:12px">
Leia o edital · Consulte IPTU · Verifique matrícula · Confirme ocupação · Calcule custo total · Defina seu lance máximo.</p>
</div></body></html>"""

    try:
        log.info("Enviando e-mail...")
        msg = MIMEMultipart("alternative")
        msg["Subject"] = config["email"]["assunto"]
        msg["From"] = rem
        msg["To"] = dest
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(rem, senha)
            s.sendmail(rem, dest, msg.as_string())
        log.info("E-mail enviado.")
    except Exception as e:
        log.error("Erro e-mail: %s", e)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def salvar_dados_json(imoveis: list[dict], filtros: dict, stats: dict) -> None:
    reais = [i for i in imoveis if i.get("lance", 0) > 0]
    links = [i for i in imoveis if i.get("lance", 0) == 0]
    dados = {
        "atualizado": date.today().strftime("%d/%m/%Y"),
        "total": len(reais),
        "total_novos": stats.get("novos", 0),
        "total_links_consulta": len(links),
        "filtros": filtros,
        "imoveis": reais,
        "links_consulta": links,
    }
    arq = BASE_DIR / "dados.json"
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("dados.json: %d imóveis + %d links de consulta", len(reais), len(links))

def main() -> None:
    filtros = CONFIG["filtros"]
    log.info("=== ABC Leilões Monitor ===")
    log.info(
        "Filtros: %s | %s – %s | %d+ quartos",
        ", ".join(filtros["cidades"]),
        formatar_reais(filtros["lance_min"]),
        formatar_reais(filtros["lance_max"]),
        filtros.get("quartos_min", 1),
    )

    imoveis_reais: list[dict] = []

    # CAMADA 1: Caixa CSV (gratuito, sem API key)
    imoveis_reais.extend(buscar_caixa(filtros))

    # CAMADA 2: Serper.dev (gratuito com API key)
    serper = buscar_serper(filtros)
    # Deduplicar com o que já veio da Caixa
    ids_existentes = {i.get("id") for i in imoveis_reais}
    imoveis_reais.extend(i for i in serper if i.get("id") not in ids_existentes)

    log.info("Total coletado: %d imóvel(is) com preço confirmado", len(imoveis_reais))

    # Links de conferência manual
    links = gerar_links_consulta(filtros)

    # Histórico (novo/recorrente/mudança de lance)
    stats = anotar_historico(imoveis_reais)
    log.info(
        "Histórico: %d confirmados · %d novos · %d com lance alterado",
        stats["confirmados"], stats["novos"], stats["alterados"],
    )

    # Salvar
    salvar_historico(imoveis_reais)
    salvar_dados_json(imoveis_reais + links, filtros, stats)

    # Alertas
    enviar_whatsapp(imoveis_reais + links, CONFIG)
    enviar_email(imoveis_reais + links, CONFIG, filtros)

    log.info("Concluído.")

if __name__ == "__main__":
    main()
