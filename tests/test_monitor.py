import json
import tempfile
import unittest
from pathlib import Path

from leilao_monitor import (
    CONFIG,
    anotar_historico,
    calcular_score,
    dica_do_dia,
    extrair_numero,
    explicar_score,
    filtrar_para_alerta,
    montar_fontes_consulta,
    montar_imovel,
)
from salvar_json import salvar_dados_json


class MonitorTest(unittest.TestCase):
    def test_extrair_numero_formato_brasileiro(self):
        self.assertEqual(extrair_numero("Lance minimo R$ 98.500,00"), 98500)
        self.assertEqual(extrair_numero("Valor: 120000"), 120000)
        self.assertIsNone(extrair_numero("sem valor informado"))

    def test_montar_imovel_calcula_desagio_e_custo(self):
        imovel = montar_imovel(
            titulo="Apartamento teste",
            cidade="Santo Andre",
            lance=100000,
            avaliado=150000,
            fonte="Caixa",
            url="https://example.com",
            area=50,
        )

        self.assertEqual(imovel["cidade"], "Santo André")
        self.assertEqual(imovel["desagio"], 33)
        self.assertEqual(imovel["custo_total"], 131500)
        self.assertIn("score", imovel)
        self.assertIn("score_motivos", imovel)
        self.assertEqual(imovel["valor_mercado_estimado"], 150000)
        self.assertEqual(imovel["lucro_potencial"], 18500)
        self.assertAlmostEqual(imovel["roi_potencial"], 14.1)
        self.assertIn("estrategia_sugerida", imovel)

    def test_score_e_dica_do_dia(self):
        imovel = montar_imovel(
            titulo="Apartamento ocupado",
            cidade="Santo Andre",
            lance=100000,
            avaliado=160000,
            fonte="Caixa",
            url="https://example.com",
            ocupado=True,
        )

        self.assertLess(calcular_score(imovel), 80)
        self.assertTrue(any("ocupado" in r for r in explicar_score(imovel)))
        self.assertIn("imissao na posse", dica_do_dia([imovel]))

    def test_fontes_consulta_por_cidade(self):
        fontes = montar_fontes_consulta(CONFIG["filtros"])

        self.assertGreaterEqual(len(fontes), 20)
        self.assertTrue(any(f.nome == "Caixa" for f in fontes))
        self.assertTrue(any("santo-andre" in f.url for f in fontes))

    def test_salvar_dados_json_separa_imoveis_e_links(self):
        imovel = montar_imovel(
            titulo="Apartamento teste",
            cidade="Maua",
            lance=90000,
            fonte="Caixa",
            url="https://example.com/1",
        )
        link = {
            "titulo": "Consulta",
            "cidade": "Mauá",
            "lance": 0,
            "fonte": "Sold",
            "url": "https://example.com/2",
        }

        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "dados.json"
            payload = salvar_dados_json([imovel, link], caminho=destino)
            gravado = json.loads(destino.read_text(encoding="utf-8"))

        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["total_links_consulta"], 1)
        self.assertEqual(len(gravado["imoveis"]), 1)
        self.assertEqual(len(gravado["links_consulta"]), 1)
        self.assertEqual(gravado["total_novos"], 1)

    def test_historico_marca_novos_e_recorrentes(self):
        antigo = montar_imovel(
            titulo="Apartamento antigo",
            cidade="Maua",
            lance=90000,
            fonte="Caixa",
            url="https://example.com/antigo",
        )
        recorrente = montar_imovel(
            titulo="Apartamento antigo",
            cidade="Maua",
            lance=88000,
            fonte="Caixa",
            url="https://example.com/antigo",
        )
        novo = montar_imovel(
            titulo="Apartamento novo",
            cidade="Maua",
            lance=100000,
            fonte="Caixa",
            url="https://example.com/novo",
        )

        resumo = anotar_historico([recorrente, novo], [antigo])

        self.assertEqual(resumo["novos"], 1)
        self.assertFalse(recorrente["novo"])
        self.assertTrue(novo["novo"])
        self.assertIn("Lance", recorrente["mudanca"])

    def test_filtrar_para_alerta_respeita_novos_e_score(self):
        novo = montar_imovel(
            titulo="Novo bom",
            cidade="Santo Andre",
            lance=100000,
            avaliado=170000,
            fonte="Caixa",
            url="https://example.com/novo",
        )
        antigo = montar_imovel(
            titulo="Antigo",
            cidade="Santo Andre",
            lance=100000,
            avaliado=170000,
            fonte="Caixa",
            url="https://example.com/antigo",
        )
        antigo["novo"] = False

        filtrados = filtrar_para_alerta(
            [novo, antigo],
            {"alertas": {"somente_novos": True, "score_minimo": 50}},
        )

        self.assertEqual(filtrados, [novo])


if __name__ == "__main__":
    unittest.main()
