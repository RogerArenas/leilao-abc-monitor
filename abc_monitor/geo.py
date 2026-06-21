from __future__ import annotations

def normalizar_cidade(cidade: str) -> str:
    mapa = {
        "Santo André": "Santo Andre",
        "São Bernardo do Campo": "Sao Bernardo do Campo",
        "Mauá": "Maua",
        "São Caetano do Sul": "Sao Caetano do Sul",
    }
    return mapa.get(cidade, cidade)

def cidade_para_interface(cidade: str) -> str:
    mapa = {
        "Santo Andre": "Santo André",
        "Sao Bernardo do Campo": "São Bernardo do Campo",
        "Maua": "Mauá",
        "Sao Caetano do Sul": "São Caetano do Sul",
    }
    return mapa.get(cidade, cidade)

def slug_cidade(cidade: str) -> str:
    return {
        "Santo Andre": "santo-andre",
        "Sao Bernardo do Campo": "sao-bernardo-do-campo",
        "Maua": "maua",
        "Sao Caetano do Sul": "sao-caetano-do-sul",
    }[normalizar_cidade(cidade)]

def caixa_cidade(cidade: str) -> str:
    return {
        "Santo Andre": "SANTO+ANDRE",
        "Sao Bernardo do Campo": "SAO+BERNARDO+DO+CAMPO",
        "Maua": "MAUA",
        "Sao Caetano do Sul": "SAO+CAETANO+DO+SUL",
    }[normalizar_cidade(cidade)]

