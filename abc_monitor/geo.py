from __future__ import annotations

# Forma canônica de cada cidade (com acento correto)
_NORM: dict[str, str] = {
    "Santo Andre":             "Santo André",
    "SANTO ANDRE":             "Santo André",
    "Santo André":             "Santo André",
    "Sao Bernardo do Campo":   "São Bernardo do Campo",
    "SAO BERNARDO DO CAMPO":   "São Bernardo do Campo",
    "São Bernardo do Campo":   "São Bernardo do Campo",
    "Maua":                    "Mauá",
    "MAUA":                    "Mauá",
    "Mauá":                    "Mauá",
    "Sao Caetano do Sul":      "São Caetano do Sul",
    "SAO CAETANO DO SUL":      "São Caetano do Sul",
    "São Caetano do Sul":      "São Caetano do Sul",
    "Diadema":                 "Diadema",
    "Ribeirao Pires":          "Ribeirão Pires",
    "RIBEIRAO PIRES":          "Ribeirão Pires",
}

_SLUGS: dict[str, str] = {
    "Santo André":             "santo-andre",
    "São Bernardo do Campo":   "sao-bernardo-do-campo",
    "Mauá":                    "maua",
    "São Caetano do Sul":      "sao-caetano-do-sul",
    "Diadema":                 "diadema",
    "Ribeirão Pires":          "ribeirao-pires",
}

_CAIXA_QUERY: dict[str, str] = {
    "Santo André":             "SANTO+ANDRE",
    "São Bernardo do Campo":   "SAO+BERNARDO+DO+CAMPO",
    "Mauá":                    "MAUA",
    "São Caetano do Sul":      "SAO+CAETANO+DO+SUL",
    "Diadema":                 "DIADEMA",
    "Ribeirão Pires":          "RIBEIRAO+PIRES",
}


def normalizar_cidade(cidade: str) -> str:
    """Retorna o nome canônico com acento. Entrada pode ser com ou sem acento."""
    return _NORM.get(cidade.strip(), cidade.strip())


def slug_cidade(cidade: str) -> str:
    """Retorna o slug URL da cidade normalizada."""
    return _SLUGS.get(normalizar_cidade(cidade), cidade.lower().replace(" ", "-"))


def cidade_para_caixa(cidade: str) -> str:
    """Nome da cidade no formato query da Caixa Econômica."""
    return _CAIXA_QUERY.get(normalizar_cidade(cidade), cidade.upper().replace(" ", "+"))


# ── Aliases para compatibilidade retroativa ──────────────────────────────────
def caixa_cidade(cidade: str) -> str:
    """Alias de cidade_para_caixa — mantido para compatibilidade."""
    return cidade_para_caixa(cidade)


def cidade_para_interface(cidade: str) -> str:
    """Alias de normalizar_cidade — retorna nome com acento para exibição."""
    return normalizar_cidade(cidade)
