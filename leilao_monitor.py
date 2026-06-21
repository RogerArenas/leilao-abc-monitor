"""Compatibilidade e entrypoint do ABC Leilao Monitor."""

from __future__ import annotations

from abc_monitor.config import BASE_DIR, CONFIG, carregar_env, log
from abc_monitor.geo import caixa_cidade, cidade_para_interface, normalizar_cidade, slug_cidade
from abc_monitor.history import anotar_historico, carregar_historico_anterior, salvar_log
from abc_monitor.models import FonteBusca
from abc_monitor.notifications import enviar_email, enviar_whatsapp, gerar_html_email
from abc_monitor.parsing import esta_na_faixa, extrair_area, extrair_numero, extrair_quartos
from abc_monitor.properties import gerar_id_imovel, montar_imovel
from abc_monitor.runner import coletar_imoveis, main
from abc_monitor.scoring import (
    calcular_score,
    dica_do_dia,
    emoji_status,
    explicar_score,
    filtrar_para_alerta,
    formatar_reais,
)
from abc_monitor.sources import (
    buscar_caixa,
    buscar_caixa_csv,
    buscar_links_consulta,
    http_get,
    montar_fontes_consulta,
    montar_link_consulta,
    montar_url_caixa,
    parse_caixa_cards,
)

__all__ = [
    "BASE_DIR",
    "CONFIG",
    "FonteBusca",
    "anotar_historico",
    "buscar_caixa",
    "buscar_caixa_csv",
    "buscar_links_consulta",
    "caixa_cidade",
    "calcular_score",
    "carregar_env",
    "carregar_historico_anterior",
    "cidade_para_interface",
    "coletar_imoveis",
    "dica_do_dia",
    "emoji_status",
    "enviar_email",
    "enviar_whatsapp",
    "esta_na_faixa",
    "explicar_score",
    "extrair_area",
    "extrair_numero",
    "extrair_quartos",
    "filtrar_para_alerta",
    "formatar_reais",
    "gerar_html_email",
    "gerar_id_imovel",
    "http_get",
    "log",
    "main",
    "montar_fontes_consulta",
    "montar_imovel",
    "montar_link_consulta",
    "montar_url_caixa",
    "normalizar_cidade",
    "parse_caixa_cards",
    "salvar_log",
    "slug_cidade",
]


if __name__ == "__main__":
    main()
