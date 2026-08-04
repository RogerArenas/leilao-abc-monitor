from __future__ import annotations

import logging
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def carregar_env(caminho: Path = BASE_DIR / ".env") -> None:
    """Carrega variaveis de um .env simples sem sobrescrever o ambiente."""
    if not caminho.exists():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave = chave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(chave, valor)


carregar_env()


CONFIG = {
    "filtros": {
        "lance_min": int(os.getenv("LANCE_MIN", "70000")),
        "lance_max": int(os.getenv("LANCE_MAX", "160000")),
        "tipo": "apartamento",
        "cidades": [
            "Santo André",
            "São Bernardo do Campo",
            "Mauá",
            "São Caetano do Sul",
        ],
        "quartos_min": int(os.getenv("QUARTOS_MIN", "2")),
    },
    "whatsapp": {
        "ativo": os.getenv("WA_ATIVO", "true").lower() == "true",
        "numero": os.getenv("WA_NUMERO", "+55119XXXXXXXX"),
        "apikey": os.getenv("WA_APIKEY", "SUA_APIKEY_AQUI"),
    },
    "email": {
        "ativo": os.getenv("EMAIL_ATIVO", "true").lower() == "true",
        "remetente": os.getenv("EMAIL_REMETENTE", "seuemail@gmail.com"),
        "senha_app": os.getenv("EMAIL_SENHA", "xxxx xxxx xxxx xxxx"),
        "destinatario": os.getenv("EMAIL_DEST", "seuemail@gmail.com"),
        "assunto": "ABC Leiloes - Novos apartamentos hoje",
    },
    "alertas": {
        "somente_novos": os.getenv("ALERTAR_SOMENTE_NOVOS", "false").lower() == "true",
        "score_minimo": int(os.getenv("ALERTAR_SCORE_MINIMO", "0")),
        "max_itens": int(os.getenv("ALERTAR_MAX_ITENS", "5")),
    },
}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("leilao")
