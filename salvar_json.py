"""
Salva os imóveis coletados em dados.json para o site GitHub Pages consumir.
Este arquivo é importado pelo leilao_monitor.py principal.
"""

import json
from datetime import datetime


def salvar_dados_json(imoveis):
    """
    Gera o dados.json que o index.html lê.
    Inclui apenas imóveis com lance > 0 (dados reais).
    """
    imoveis_reais = [im for im in imoveis if im.get('lance', 0) > 0]

    payload = {
        "atualizado": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": len(imoveis_reais),
        "imoveis": imoveis_reais,
    }

    with open("dados.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    print(f"[OK] dados.json salvo com {len(imoveis_reais)} imóveis.")
    return payload
