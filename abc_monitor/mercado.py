"""
Estimativa de valor de mercado via duas estratégias:
  1. Tabela estática (sempre disponível, sem API)
  2. Serper.dev buscando OLX/ZAP (quando API key configurada)
"""
from __future__ import annotations
import logging
import os
import re
import time
from typing import Any

log = logging.getLogger("leilao.mercado")

# Preço médio por m² por cidade (Fipe Zap / pesquisa de mercado 2025)
PRECO_M2: dict[str, int] = {
    "São Paulo":                7500, "São Caetano do Sul":       6200,
    "Santo André":              4800, "São Bernardo do Campo":    4500,
    "Santos":                   5500, "Guarujá":                  4800,
    "São José dos Campos":      4500, "Campinas":                 4800,
    "Jundiaí":                  5000, "Sorocaba":                 3800,
    "Ribeirão Preto":           4200, "São José do Rio Preto":    3900,
    "Osasco":                   4200, "Guarulhos":                4000,
    "Barueri":                  5200, "Cotia":                    4500,
    "Mogi das Cruzes":          3800, "Suzano":                   3200,
    "Diadema":                  3600, "Mauá":                     3400,
    "Ribeirão Pires":           3200, "São Vicente":              3800,
    "Praia Grande":             4200, "Bertioga":                 5000,
    "Carapicuíba":              3600, "Taboão da Serra":          3800,
    "Bauru":                    3300, "Piracicaba":               3600,
    "Americana":                3700, "Limeira":                  3400,
    "Araraquara":               3500, "São Carlos":               3600,
    "Marília":                  3200, "Presidente Prudente":      3000,
    "Araçatuba":                3100, "Franca":                   3200,
    "Taubaté":                  3600, "Jacareí":                  3400,
    "Botucatu":                 3200,
}
_DEFAULT_M2 = 3500


def estimar_por_tabela(cidade: str, area: int | None, quartos: int | None) -> dict[str, Any] | None:
    """Estimativa baseada em tabela de preço/m² por cidade."""
    preco_m2 = PRECO_M2.get(cidade, _DEFAULT_M2)
    if not area or area < 20:
        # Sem área: estimar por quartos
        area_est = {1: 45, 2: 65, 3: 85, 4: 110}.get(quartos or 2, 65)
    else:
        area_est = area

    vm = preco_m2 * area_est
    margem = int(vm * 0.12)   # ±12%
    return {
        "min":        vm - margem,
        "max":        vm + margem,
        "estimado":   vm,
        "preco_m2":   preco_m2,
        "area_usada": area_est,
        "fonte":      "tabela_local",
    }


def _extrair_preco_texto(txt: str) -> int | None:
    """Extrai o primeiro preço entre 50k e 5M de um trecho de texto."""
    for m in re.finditer(r"R\$\s*([\d.,]+)", txt):
        try:
            n = float(m.group(1).replace(".", "").replace(",", "."))
            if 50_000 <= n <= 5_000_000:
                return int(n)
        except ValueError:
            pass
    return None


def buscar_via_serper(cidade: str, area: int | None, quartos: int | None, api_key: str) -> dict[str, Any] | None:
    """Busca preços reais em OLX/ZAP via Serper.dev."""
    try:
        import requests
    except ImportError:
        return None

    q_str = f"apartamento {quartos or 2} quartos" + (f" {area}m2" if area and area > 20 else "")
    queries = [
        f"site:olx.com.br {q_str} {cidade} venda",
        f"site:zapimoveis.com.br {q_str} {cidade} venda",
        f"site:vivareal.com.br {q_str} {cidade} venda",
    ]
    precos: list[int] = []
    for q in queries:
        try:
            r = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": q, "gl": "br", "hl": "pt-br", "num": 5},
                timeout=8,
            )
            if r.status_code != 200:
                continue
            for res in r.json().get("organic", []):
                snippet = res.get("snippet", "") + " " + res.get("title", "")
                p = _extrair_preco_texto(snippet)
                if p:
                    precos.append(p)
            time.sleep(0.3)
        except Exception as e:
            log.debug("Serper falhou em %s: %s", q, e)

    if len(precos) < 2:
        return None

    precos.sort()
    p10 = precos[max(0, len(precos)//10)]
    p90 = precos[min(len(precos)-1, (9*len(precos))//10)]
    med = int(sum(precos) / len(precos))
    return {
        "min":      p10,
        "max":      p90,
        "estimado": med,
        "preco_m2": (med // area) if area and area > 20 else None,
        "amostras": len(precos),
        "fonte":    "serper_olx_zap",
    }


def valor_mercado(cidade: str, area: int | None, quartos: int | None,
                  serper_key: str | None = None) -> dict[str, Any]:
    """
    Retorna estimativa de valor de mercado.
    Tenta Serper (dados reais) se key disponível, senão usa tabela local.
    """
    if serper_key and len(serper_key) > 8:
        dados = buscar_via_serper(cidade, area, quartos, serper_key)
        if dados:
            return dados
    # Fallback: tabela local (sempre funciona)
    return estimar_por_tabela(cidade, area, quartos) or {
        "min": 0, "max": 0, "estimado": 0, "fonte": "sem_dados"
    }
