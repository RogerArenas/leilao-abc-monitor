from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FonteBusca:
    nome: str
    url: str
    cidade: str = ""
    tipo: str = "consulta"
