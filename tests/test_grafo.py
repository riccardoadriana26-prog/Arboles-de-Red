import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from math import inf, nan

from arboles_de_red import Arista, Grafo


class AristaTests(unittest.TestCase):
    def test_direccion_y_peso_pertenecen_a_cada_arista(self):
        directa = Arista(0, "A1", "B2", 8, True)
        sin_direccion = Arista(1, "B2", "C3", -2.5, False)
        grafo = Grafo(("A1", "B2", "C3"), (directa, sin_direccion))

        self.assertEqual(grafo.aristas[0].peso, 8.0)
        self.assertEqual(grafo.aristas[1].peso, -2.5)
        self.assertTrue(grafo.aristas[0].dirigida)
        self.assertFalse(grafo.aristas[1].dirigida)

    def test_aristas_paralelas_identicas_se_conservan(self):
        primera = Arista(0, "A", "B", 5, True)
        segunda = Arista(1, "A", "B", 5, True)
        grafo = Grafo(("A", "B"), (primera, segunda))

        self.assertEqual(len(grafo.aristas), 2)
        self.assertNotEqual(grafo.aristas[0], grafo.aristas[1])

    def test_rechaza_pesos_no_reales_o_no_finitos(self):
        for peso in ("5", True, nan, inf, -inf, complex(1, 2), Decimal("NaN")):
            with self.subTest(peso=peso), self.assertRaises((TypeError, ValueError)):
                Arista(0, "A", "B", peso, True)

    def test_acepta_decimales_finitos_convertidos_a_float(self):
        self.assertEqual(Arista(0, "A", "B", Decimal("0.5"), True).peso, 0.5)

    def test_rechaza_lazos_e_identificadores_no_alfanumericos(self):
        with self.assertRaises(ValueError):
            Arista(0, "A", "A", 1, True)
        with self.assertRaises(ValueError):
            Arista(0, "A-B", "C", 1, True)

    def test_rechaza_direccion_ambigua(self):
        with self.assertRaises(TypeError):
            Arista(0, "A", "B", 1, "sí")


class GrafoTests(unittest.TestCase):
    def test_acepta_componentes_desconectados_sin_aislados(self):
        grafo = Grafo(
            ("A", "B", "C", "D"),
            (Arista(0, "A", "B", 1, False), Arista(1, "C", "D", 2, False)),
        )
        self.assertEqual(len(grafo.vertices), 4)

    def test_admite_actividades_aisladas_y_precedencias_sin_peso(self):
        grafo = Grafo(("A", "B", "C"), (Arista(0, "A", "B", None, True),))
        self.assertEqual(grafo.vertices, ("A", "B", "C"))
        self.assertIsNone(grafo.aristas[0].peso)
        self.assertEqual(Grafo(("Unica",), ()).vertices, ("Unica",))

    def test_rechaza_identificadores_de_vertice_repetidos(self):
        with self.assertRaisesRegex(ValueError, "únicos"):
            Grafo(("A", "A", "B"), (Arista(0, "A", "B", 1, True),))

    def test_rechaza_aristas_con_extremos_ausentes_o_id_repetido(self):
        with self.assertRaisesRegex(ValueError, "existir"):
            Grafo(("A", "B"), (Arista(0, "A", "C", 1, True),))
        with self.assertRaisesRegex(ValueError, "únicos"):
            Grafo(
                ("A", "B"),
                (Arista(0, "A", "B", 1, True), Arista(0, "A", "B", 2, True)),
            )

    def test_copia_las_colecciones_y_no_permite_modificaciones(self):
        vertices = ["A", "B"]
        aristas = [Arista(0, "A", "B", 1, True)]
        grafo = Grafo(vertices, aristas)
        vertices.append("C")
        aristas.append(Arista(1, "A", "B", 2, True))

        self.assertEqual(grafo.vertices, ("A", "B"))
        self.assertEqual(len(grafo.aristas), 1)
        with self.assertRaises(FrozenInstanceError):
            grafo.vertices = ("A",)
        with self.assertRaises(FrozenInstanceError):
            grafo.aristas[0].peso = 3

    def test_grafo_vacio_es_representable_para_validacion_en_csv(self):
        self.assertEqual(Grafo((), ()).vertices, ())


if __name__ == "__main__":
    unittest.main()
