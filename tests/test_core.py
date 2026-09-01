import base64
import unittest

import core


class CoreTests(unittest.TestCase):
    def test_normaliza_acentos_e_caixa(self):
        self.assertEqual(core.normalizar_texto_busca("Olá, ACADÊMICO"), "ola, academico")

    def test_decodifica_base64_urlsafe_sem_padding(self):
        encoded = base64.urlsafe_b64encode("mensagem".encode()).decode().rstrip("=")
        self.assertEqual(core.decode_b64_urlsafe(encoded), "mensagem")

    def test_gera_labels_intermediarios(self):
        self.assertEqual(
            core.labels_intermediarios(["Compras/Amazon/Pedidos"]),
            ["Compras", "Compras/Amazon", "Compras/Amazon/Pedidos"],
        )

    def test_slug_para_cli(self):
        self.assertEqual(core.slug("Mercado Livre"), "mercado-livre")

    def test_detecta_operacao_de_lixeira(self):
        self.assertTrue(core.operacao_usa_lixeira(["TRASH"]))
        self.assertFalse(core.operacao_usa_lixeira(["INBOX"]))


if __name__ == "__main__":
    unittest.main()
