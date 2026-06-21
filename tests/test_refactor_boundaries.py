import unittest
from unittest.mock import patch

from abc_monitor.notifications import enviar_email, enviar_whatsapp
from abc_monitor.sources import buscar_caixa


class RefactorBoundariesTest(unittest.TestCase):
    def test_buscar_caixa_usa_fallback_html_quando_csv_vazio(self):
        filtros = {
            "lance_min": 70000,
            "lance_max": 160000,
            "cidades": ["Maua"],
        }

        with (
            patch("abc_monitor.sources.buscar_caixa_csv", return_value=[]),
            patch("abc_monitor.sources.http_get", return_value="<html></html>") as http_get,
            patch("abc_monitor.sources.parse_caixa_cards", return_value=[{"lance": 90000}]),
        ):
            resultado = buscar_caixa(filtros)

        self.assertEqual(resultado, [{"lance": 90000}])
        http_get.assert_called_once()

    def test_notificacoes_sem_credenciais_nao_chamam_rede(self):
        config = {
            "whatsapp": {
                "ativo": True,
                "numero": "+55119XXXXXXXX",
                "apikey": "SUA_APIKEY_AQUI",
            },
            "email": {
                "ativo": True,
                "remetente": "seuemail@gmail.com",
                "senha_app": "curta",
                "destinatario": "destino@example.com",
                "assunto": "Teste",
            },
            "alertas": {},
        }

        with (
            patch("abc_monitor.notifications.urllib.request.urlopen") as urlopen,
            patch("abc_monitor.notifications.smtplib.SMTP_SSL") as smtp_ssl,
        ):
            enviar_whatsapp([], config)
            enviar_email([], config, {"lance_min": 70000, "lance_max": 160000})

        urlopen.assert_not_called()
        smtp_ssl.assert_not_called()


if __name__ == "__main__":
    unittest.main()
