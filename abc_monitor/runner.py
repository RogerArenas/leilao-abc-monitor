from __future__ import annotations

import os
import time
from typing import Any

from salvar_json import salvar_dados_json

from .config import CONFIG, log
from .geocoding import geocodificar, locais_proximos
from .history import anotar_historico, salvar_log
from .mercado import valor_mercado
from .notifications import enviar_email, enviar_whatsapp
from .sources import buscar_caixa, buscar_links_consulta


def enriquecer_imovel(im: dict[str, Any], serper_key: str | None) -> dict[str, Any]:
    """Adiciona geocoding, locais próximos e valor de mercado ao imóvel."""
    cidade  = im.get("cidade", "")
    area    = im.get("area")
    quartos = im.get("quartos")
    endereco = im.get("endereco") or im.get("bairro") or ""

    # ── 1. Geocoding ─────────────────────────────────────────────────────────
    if not im.get("lat"):
        coords = geocodificar(endereco, cidade)
        if coords:
            im["lat"], im["lng"] = coords
            log.debug("  Geocoded %s → %.4f, %.4f", cidade, im["lat"], im["lng"])
        time.sleep(1.1)   # Nominatim: máx 1 req/s

    # ── 2. Locais próximos ───────────────────────────────────────────────────
    if im.get("lat") and not im.get("locais_proximos"):
        try:
            im["locais_proximos"] = locais_proximos(im["lat"], im["lng"])
        except Exception as e:
            log.debug("  Locais próximos falhou: %s", e)
            im["locais_proximos"] = {}

    # ── 3. Valor de mercado ───────────────────────────────────────────────────
    if not im.get("valor_mercado"):
        vm = valor_mercado(cidade, area, quartos, serper_key)
        if vm and vm.get("estimado", 0) > 0:
            im["valor_mercado"] = vm
            # Recalcular deságio real vs mercado
            lance = im.get("lance", 0)
            if lance and vm["estimado"] > 0:
                im["desagio_real"] = round(((vm["estimado"] - lance) / vm["estimado"]) * 100, 1)

    return im


def coletar_imoveis(filtros: dict[str, Any]) -> list[dict[str, Any]]:
    imoveis = buscar_caixa(filtros)
    links   = buscar_links_consulta(filtros)
    return imoveis + links


def main() -> None:
    log.info("=" * 55)
    log.info("SP Leilões Monitor — iniciando")
    log.info("=" * 55)

    filtros    = CONFIG["filtros"]
    serper_key = os.getenv("SERPER_API_KEY", "")

    todos_imoveis = coletar_imoveis(filtros)
    resumo_historico = anotar_historico(todos_imoveis)
    imoveis_reais = [i for i in todos_imoveis if i.get("lance", 0) > 0]

    # Enriquecer: geocoding + locais + mercado (apenas imóveis reais)
    total = len(imoveis_reais)
    log.info("Enriquecendo %d imóveis (geocoding, locais, mercado)...", total)
    for n, im in enumerate(imoveis_reais, 1):
        log.info("  [%d/%d] %s — %s", n, total, im.get("cidade"), im.get("titulo","")[:40])
        enriquecer_imovel(im, serper_key)

    links    = [i for i in todos_imoveis if i.get("lance", 0) == 0]
    filtros_out = {**filtros, "total": len(imoveis_reais), "total_novos": resumo_historico.get("novos", 0)}

    salvar_dados_json(imoveis_reais, filtros_out)

    alertas_conf = CONFIG["alertas"]
    imoveis_alerta = [
        i for i in imoveis_reais
        if (not alertas_conf["somente_novos"] or i.get("novo"))
        and i.get("_sc", 0) >= alertas_conf["score_minimo"]
    ][: alertas_conf["max_itens"]]

    if imoveis_alerta and (CONFIG["whatsapp"]["ativo"] or CONFIG["email"]["ativo"]):
        if CONFIG["whatsapp"]["ativo"]:
            enviar_whatsapp(imoveis_alerta, CONFIG["whatsapp"], resumo_historico)
        if CONFIG["email"]["ativo"]:
            enviar_email(imoveis_alerta, CONFIG["email"], resumo_historico)

    salvar_log(resumo_historico)
    log.info("Concluído. %d imóveis salvos.", len(imoveis_reais))
