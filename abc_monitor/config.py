from __future__ import annotations

import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def carregar_env(caminho: Path = BASE_DIR / ".env") -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


carregar_env()

# ── Regiões e cidades de São Paulo ─────────────────────────────────────────
REGIOES: dict[str, list[str]] = {
    "ABC Paulista": [
        "Santo André", "São Bernardo do Campo", "Mauá",
        "São Caetano do Sul", "Diadema", "Ribeirão Pires",
    ],
    "Capital": ["São Paulo"],
    "Grande SP": [
        "Guarulhos", "Osasco", "Mogi das Cruzes", "Suzano",
        "Itaquaquecetuba", "Carapicuíba", "Barueri", "Cotia",
        "Taboão da Serra", "Francisco Morato", "Ferraz de Vasconcelos",
        "Poá", "Arujá", "Santo André",
    ],
    "Baixada Santista": [
        "Santos", "São Vicente", "Guarujá", "Praia Grande",
        "Cubatão", "Bertioga",
    ],
    "Vale do Paraíba": [
        "São José dos Campos", "Taubaté", "Jacareí",
        "Pindamonhangaba", "Guaratinguetá",
    ],
    "Interior SP": [
        "Campinas", "Sorocaba", "Ribeirão Preto", "São José do Rio Preto",
        "Bauru", "Piracicaba", "Araçatuba", "Franca",
        "Presidente Prudente", "Marília", "Araraquara", "São Carlos",
        "Limeira", "Americana", "Jundiaí", "Botucatu",
    ],
}

# Lista plana de todas as cidades (sem duplicatas, ordem alfabética)
_todas = sorted({c for r in REGIOES.values() for c in r})

# Fonte de qualidade de localização por cidade (0–100)
QUALIDADE_LOCALIZACAO: dict[str, int] = {
    # ABC
    "São Caetano do Sul": 88, "Santo André": 76,
    "São Bernardo do Campo": 75, "Diadema": 68,
    "Mauá": 65, "Ribeirão Pires": 63,
    # Capital
    "São Paulo": 82,
    # Grande SP
    "Guarulhos": 70, "Osasco": 70, "Barueri": 72, "Cotia": 68,
    "Mogi das Cruzes": 66, "Suzano": 62, "Itaquaquecetuba": 58,
    "Carapicuíba": 63, "Taboão da Serra": 64, "Ferraz de Vasconcelos": 60,
    "Francisco Morato": 55, "Poá": 60, "Arujá": 62,
    # Baixada
    "Santos": 74, "São Vicente": 67, "Guarujá": 70,
    "Praia Grande": 68, "Cubatão": 58, "Bertioga": 65,
    # Vale
    "São José dos Campos": 75, "Taubaté": 68, "Jacareí": 65,
    "Pindamonhangaba": 62, "Guaratinguetá": 60,
    # Interior
    "Campinas": 77, "Sorocaba": 72, "Ribeirão Preto": 74,
    "São José do Rio Preto": 72, "Bauru": 69, "Piracicaba": 70,
    "Araçatuba": 66, "Franca": 66, "Presidente Prudente": 65,
    "Marília": 64, "Araraquara": 68, "São Carlos": 70,
    "Limeira": 67, "Americana": 68, "Jundiaí": 73, "Botucatu": 65,
}

CONFIG = {
    "filtros": {
        "lance_min":   int(os.getenv("LANCE_MIN",   "70000")),
        "lance_max":   int(os.getenv("LANCE_MAX",   "500000")),
        "tipo":        "apartamento",
        # Vazio = todo SP; informar lista para restringir
        "cidades":     [c.strip() for c in os.getenv("CIDADES", "").split(",") if c.strip()],
        "quartos_min": int(os.getenv("QUARTOS_MIN", "1")),
    },
    "whatsapp": {
        "ativo":  os.getenv("WA_ATIVO",  "true").lower() == "true",
        "numero": os.getenv("WA_NUMERO", "+55119XXXXXXXX"),
        "apikey": os.getenv("WA_APIKEY", "SUA_APIKEY_AQUI"),
    },
    "email": {
        "ativo":      os.getenv("EMAIL_ATIVO",    "true").lower() == "true",
        "remetente":  os.getenv("EMAIL_REMETENTE","seuemail@gmail.com"),
        "senha_app":  os.getenv("EMAIL_SENHA",    "xxxx xxxx xxxx xxxx"),
        "destinatario":os.getenv("EMAIL_DEST",    "seuemail@gmail.com"),
        "assunto":    "Monitor SP Leilões — Novos imóveis hoje",
    },
    "alertas": {
        "somente_novos": os.getenv("ALERTAR_SOMENTE_NOVOS", "true").lower() == "true",
        "score_minimo":  int(os.getenv("ALERTAR_SCORE_MINIMO", "0")),
        "max_itens":     int(os.getenv("ALERTAR_MAX_ITENS", "5")),
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("leilao")
