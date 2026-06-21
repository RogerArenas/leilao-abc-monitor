from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from .config import BASE_DIR, log
from .properties import gerar_id_imovel
from .scoring import formatar_reais

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

def salvar_log(imoveis: list[dict[str, Any]]) -> Path:
    arquivo = BASE_DIR / f"historico_{date.today().isoformat()}.json"
    arquivo.write_text(json.dumps(imoveis, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Historico salvo em %s", arquivo.name)
    return arquivo

