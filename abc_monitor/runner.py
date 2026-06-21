from __future__ import annotations

import time
from typing import Any

from salvar_json import salvar_dados_json

from .config import CONFIG, log
from .history import anotar_historico, salvar_log
from .notifications import enviar_email, enviar_whatsapp
from .sources import buscar_caixa, buscar_links_consulta


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
    salvar_dados_json(todos_imoveis, filtros=filtros)
    enviar_whatsapp(todos_imoveis, CONFIG)
    time.sleep(1)
    enviar_email(todos_imoveis, CONFIG, filtros)

    log.info("Monitoramento concluido.")
