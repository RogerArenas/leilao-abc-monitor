"""
Gera o dados.json consumido pelo index.html e pelo GitHub Pages.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def salvar_dados_json(
    imoveis: list[dict[str, Any]],
    filtros: dict[str, Any] | None = None,
    caminho: str | Path = "dados.json",
) -> dict[str, Any]:
    imoveis_reais = [im for im in imoveis if im.get("lance", 0) > 0]
    links_consulta = [im for im in imoveis if im.get("lance", 0) <= 0]
    novos = [im for im in imoveis_reais if im.get("novo")]

    payload = {
        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": len(imoveis_reais),
        "total_novos": len(novos),
        "total_links_consulta": len(links_consulta),
        "filtros": filtros or {},
        "imoveis": imoveis_reais,
        "links_consulta": links_consulta,
    }

    destino = Path(caminho)
    destino.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    print(
        "[OK] dados.json salvo com "
        f"{len(imoveis_reais)} imoveis, {len(novos)} novos e "
        f"{len(links_consulta)} links de consulta."
    )
    return payload
