"""El formato compacto devuelve texto y conserva los valores de cálculo."""

import unittest

from arboles_de_red.formato_visual import formatear_numero


class FormatoVisualTests(unittest.TestCase):
    def test_dos_decimales_sin_ceros_finales(self):
        for valor, esperado in (
            (3.0, "3"), (1.7777777777777777, "1.78"),
            (4.333333333333333, "4.33"), (10.333333333333334, "10.33"),
            (0.1111111111111111, "0.11"), (9.5, "9.5"), (0.0, "0"),
            (-0.0, "0"), (-0.001, "0"), (-1.7777777777777777, "-1.78"),
        ):
            with self.subTest(valor=valor):
                original = valor.hex()
                self.assertEqual(formatear_numero(valor), esperado)
                self.assertEqual(valor.hex(), original)


if __name__ == "__main__":
    unittest.main()
