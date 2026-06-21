from __future__ import annotations

import re
from typing import Any

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

