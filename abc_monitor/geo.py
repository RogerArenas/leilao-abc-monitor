from __future__ import annotations

_NORM = {
    "Santo Andre": "Santo André", "SANTO ANDRE": "Santo André", "Santo André": "Santo André",
    "Sao Bernardo do Campo": "São Bernardo do Campo", "SAO BERNARDO DO CAMPO": "São Bernardo do Campo", "São Bernardo do Campo": "São Bernardo do Campo",
    "Maua": "Mauá", "MAUA": "Mauá", "Mauá": "Mauá",
    "Sao Caetano do Sul": "São Caetano do Sul", "SAO CAETANO DO SUL": "São Caetano do Sul", "São Caetano do Sul": "São Caetano do Sul",
    "Diadema": "Diadema",
    "Ribeirao Pires": "Ribeirão Pires", "RIBEIRAO PIRES": "Ribeirão Pires", "Ribeirão Pires": "Ribeirão Pires",
    "Sao Paulo": "São Paulo", "SAO PAULO": "São Paulo", "São Paulo": "São Paulo",
    "Guarulhos": "Guarulhos", "Osasco": "Osasco",
    "Mogi das Cruzes": "Mogi das Cruzes", "MOGI DAS CRUZES": "Mogi das Cruzes",
    "Suzano": "Suzano", "Itaquaquecetuba": "Itaquaquecetuba",
    "Carapicuiba": "Carapicuíba", "CARAPICUIBA": "Carapicuíba", "Carapicuíba": "Carapicuíba",
    "Barueri": "Barueri", "Cotia": "Cotia",
    "Taboao da Serra": "Taboão da Serra", "TABOAO DA SERRA": "Taboão da Serra", "Taboão da Serra": "Taboão da Serra",
    "Francisco Morato": "Francisco Morato",
    "Ferraz de Vasconcelos": "Ferraz de Vasconcelos", "FERRAZ DE VASCONCELOS": "Ferraz de Vasconcelos",
    "Poa": "Poá", "POA": "Poá", "Poá": "Poá",
    "Aruja": "Arujá", "ARUJA": "Arujá", "Arujá": "Arujá",
    "Santos": "Santos",
    "Sao Vicente": "São Vicente", "SAO VICENTE": "São Vicente", "São Vicente": "São Vicente",
    "Guaruja": "Guarujá", "GUARUJA": "Guarujá", "Guarujá": "Guarujá",
    "Praia Grande": "Praia Grande",
    "Cubatao": "Cubatão", "CUBATAO": "Cubatão", "Cubatão": "Cubatão",
    "Bertioga": "Bertioga",
    "Sao Jose dos Campos": "São José dos Campos", "SAO JOSE DOS CAMPOS": "São José dos Campos", "São José dos Campos": "São José dos Campos",
    "Taubate": "Taubaté", "TAUBATE": "Taubaté", "Taubaté": "Taubaté",
    "Jacarei": "Jacareí", "JACAREI": "Jacareí", "Jacareí": "Jacareí",
    "Pindamonhangaba": "Pindamonhangaba",
    "Guaratingueta": "Guaratinguetá", "GUARATINGUETA": "Guaratinguetá", "Guaratinguetá": "Guaratinguetá",
    "Campinas": "Campinas", "Sorocaba": "Sorocaba",
    "Ribeirao Preto": "Ribeirão Preto", "RIBEIRAO PRETO": "Ribeirão Preto", "Ribeirão Preto": "Ribeirão Preto",
    "Sao Jose do Rio Preto": "São José do Rio Preto", "SAO JOSE DO RIO PRETO": "São José do Rio Preto", "São José do Rio Preto": "São José do Rio Preto",
    "Bauru": "Bauru", "Piracicaba": "Piracicaba",
    "Aracatuba": "Araçatuba", "ARACATUBA": "Araçatuba", "Araçatuba": "Araçatuba",
    "Franca": "Franca",
    "Presidente Prudente": "Presidente Prudente", "PRESIDENTE PRUDENTE": "Presidente Prudente",
    "Marilia": "Marília", "MARILIA": "Marília", "Marília": "Marília",
    "Araraquara": "Araraquara",
    "Sao Carlos": "São Carlos", "SAO CARLOS": "São Carlos", "São Carlos": "São Carlos",
    "Limeira": "Limeira", "Americana": "Americana",
    "Jundiai": "Jundiaí", "JUNDIAI": "Jundiaí", "Jundiaí": "Jundiaí",
    "Botucatu": "Botucatu",
}

_SLUGS = {
    "Santo André": "santo-andre", "São Bernardo do Campo": "sao-bernardo-do-campo",
    "Mauá": "maua", "São Caetano do Sul": "sao-caetano-do-sul",
    "Diadema": "diadema", "Ribeirão Pires": "ribeirao-pires",
    "São Paulo": "sao-paulo", "Guarulhos": "guarulhos", "Osasco": "osasco",
    "Mogi das Cruzes": "mogi-das-cruzes", "Suzano": "suzano",
    "Itaquaquecetuba": "itaquaquecetuba", "Carapicuíba": "carapicuiba",
    "Barueri": "barueri", "Cotia": "cotia", "Taboão da Serra": "taboao-da-serra",
    "Francisco Morato": "francisco-morato", "Ferraz de Vasconcelos": "ferraz-de-vasconcelos",
    "Poá": "poa", "Arujá": "aruja",
    "Santos": "santos", "São Vicente": "sao-vicente", "Guarujá": "guaruja",
    "Praia Grande": "praia-grande", "Cubatão": "cubatao", "Bertioga": "bertioga",
    "São José dos Campos": "sao-jose-dos-campos", "Taubaté": "taubate",
    "Jacareí": "jacarei", "Pindamonhangaba": "pindamonhangaba", "Guaratinguetá": "guaratingueta",
    "Campinas": "campinas", "Sorocaba": "sorocaba", "Ribeirão Preto": "ribeirao-preto",
    "São José do Rio Preto": "sao-jose-do-rio-preto", "Bauru": "bauru",
    "Piracicaba": "piracicaba", "Araçatuba": "aracatuba", "Franca": "franca",
    "Presidente Prudente": "presidente-prudente", "Marília": "marilia",
    "Araraquara": "araraquara", "São Carlos": "sao-carlos",
    "Limeira": "limeira", "Americana": "americana", "Jundiaí": "jundiai",
    "Botucatu": "botucatu",
}

_CAIXA = {c: s.upper().replace("-", "+") for c, s in _SLUGS.items()}


def normalizar_cidade(cidade: str) -> str:
    return _NORM.get(cidade.strip(), cidade.strip())

def slug_cidade(cidade: str) -> str:
    return _SLUGS.get(normalizar_cidade(cidade), cidade.lower().replace(" ", "-"))

def cidade_para_caixa(cidade: str) -> str:
    return _CAIXA.get(normalizar_cidade(cidade), cidade.upper().replace(" ", "+"))

def caixa_cidade(cidade: str) -> str:
    return cidade_para_caixa(cidade)

def cidade_para_interface(cidade: str) -> str:
    return normalizar_cidade(cidade)
