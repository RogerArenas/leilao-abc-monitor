from __future__ import annotations

from hashlib import sha1
from typing import Any

from .geo import cidade_para_interface
from .scoring import calcular_score, explicar_score, estimar_qualidade_localizacao, sugerir_estrategia

def montar_imovel(
    titulo: str,
    cidade: str,
    lance: float,
    fonte: str,
    url: str,
    avaliado: float | None = None,
    area: int = 0,
    quartos: int = 0,
    data_leilao: str = "Consulte o site",
    praca: str = "?",
    ocupado: bool | None = None,
    bairro: str = "",
    matricula: str = "",
) -> dict[str, Any]:
    if avaliado is None:
        avaliado = lance * 1.3

    desagio = round(((avaliado - lance) / avaliado) * 100) if avaliado > 0 else 0
    comissao = round(lance * 0.05)
    itbi = round(lance * 0.03)
    cartorio = 3_500
    reforma = round(area * 400) if area > 0 else 15_000

    investimento_total = round(lance + comissao + itbi + cartorio + reforma)
    lucro_potencial = round(avaliado - investimento_total)
    roi_potencial = round((lucro_potencial / investimento_total) * 100, 1) if investimento_total else 0

    imovel = {
        "titulo": titulo.strip() or f"Apartamento em {cidade_para_interface(cidade)}",
        "cidade": cidade_para_interface(cidade),
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
        "custo_total": investimento_total,
        "valor_mercado_estimado": round(avaliado),
        "lucro_potencial": lucro_potencial,
        "roi_potencial": roi_potencial,
        "qualidade_localizacao": estimar_qualidade_localizacao(cidade, bairro),
        "estrategia_sugerida": sugerir_estrategia(area, quartos, roi_potencial, ocupado),
    }
    imovel["score"] = calcular_score(imovel)
    imovel["score_motivos"] = explicar_score(imovel)
    imovel["id"] = gerar_id_imovel(imovel)
    imovel["novo"] = True
    imovel["visto_antes"] = False
    imovel["mudanca"] = ""
    return imovel

def gerar_id_imovel(imovel: dict[str, Any]) -> str:
    base = "|".join(
        [
            str(imovel.get("fonte", "")).lower(),
            str(imovel.get("url", "")).split("?")[0].lower(),
            str(imovel.get("cidade", "")).lower(),
            str(imovel.get("titulo", "")).lower(),
        ]
    )
    return sha1(base.encode("utf-8")).hexdigest()[:16]

