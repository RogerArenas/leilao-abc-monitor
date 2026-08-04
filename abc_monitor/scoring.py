from __future__ import annotations

from typing import Any

from .geo import normalizar_cidade

def estimar_qualidade_localizacao(cidade: str, bairro: str = "") -> int:
    cidade_norm = normalizar_cidade(cidade)
    base = {
        "Santo André": 78,
        "São Bernardo do Campo": 76,
        "São Caetano do Sul": 86,
        "Mauá": 66,
    }.get(cidade_norm, 65)
    bairros_fortes = ("centro", "paraiso", "vila bastos", "boa vista", "santo antonio", "baeta")
    if bairro and any(b in bairro.lower() for b in bairros_fortes):
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
        return "Locacao compacta"
    return "Analisar edital e mercado"

def formatar_reais(valor: float) -> str:
    return f"R$ {valor:,.0f}".replace(",", ".")

def calcular_score(imovel: dict[str, Any]) -> int:
    pontos = 100
    if imovel.get("ocupado") is True:
        pontos -= 30
    if imovel.get("praca") == "2":
        pontos -= 10
    if imovel.get("debito_iptu", 0) > 0:
        pontos -= 15
    if imovel.get("debito_cond", 0) > 0:
        pontos -= 10
    if imovel.get("desagio", 0) >= 35:
        pontos += 10
    if imovel.get("desagio", 0) < 20:
        pontos -= 10
    if not imovel.get("area"):
        pontos -= 3
    if not imovel.get("quartos"):
        pontos -= 3
    return max(0, min(100, pontos))

def explicar_score(imovel: dict[str, Any]) -> list[str]:
    razoes: list[str] = []
    if imovel.get("ocupado") is True:
        razoes.append("ocupado exige plano de posse")
    elif imovel.get("ocupado") is False:
        razoes.append("desocupado tende a ser mais simples")
    else:
        razoes.append("ocupacao precisa ser confirmada")

    if imovel.get("desagio", 0) >= 35:
        razoes.append("desagio forte")
    elif imovel.get("desagio", 0) < 20:
        razoes.append("desagio baixo")

    if imovel.get("debito_iptu", 0) or imovel.get("debito_cond", 0):
        razoes.append("ha debitos informados")
    if not imovel.get("area") or not imovel.get("quartos"):
        razoes.append("dados incompletos")
    return razoes

def dica_do_dia(imoveis_reais: list[dict[str, Any]]) -> str:
    if not imoveis_reais:
        return "Quando nao houver preco confirmado, use os links por cidade e procure venda direta ou edital com ocupacao clara."
    if any(i.get("ocupado") is True for i in imoveis_reais):
        return "Imovel ocupado pode exigir acao de imissao na posse; coloque prazo e custo juridico na conta."
    if any(i.get("desagio", 0) >= 35 for i in imoveis_reais):
        return "Desagio alto chama atencao, mas so vira oportunidade depois de checar edital, matricula e debitos."
    return "Compare o lance com o custo total, nao apenas com o valor de avaliacao."

def filtrar_para_alerta(
    imoveis_reais: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    alertas = config.get("alertas", {})
    score_minimo = int(alertas.get("score_minimo", 0))
    somente_novos = bool(alertas.get("somente_novos", False))

    itens = [i for i in imoveis_reais if calcular_score(i) >= score_minimo]
    if somente_novos:
        itens = [i for i in itens if i.get("novo")]
    return sorted(itens, key=calcular_score, reverse=True)

def emoji_status(imovel: dict[str, Any]) -> str:
    if imovel.get("ocupado") is True:
        return "ATENCAO"
    if imovel.get("ocupado") is False:
        return "OK"
    return "VERIFICAR"

