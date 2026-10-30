"""Pruebas del adaptador visual PyVis para entradas reales del proyecto."""

from itertools import combinations
import unittest

try:
    import networkx  # noqa: F401
    import streamlit  # noqa: F401
    import pyvis  # noqa: F401

    from arboles_de_red.algoritmo import Entrada
    from arboles_de_red.csv import (
        ProcesadorCPMCSV,
        ProcesadorConexionesCSV,
        ProcesadorPERTCSV,
    )
    from arboles_de_red.grafo import Arista, Grafo
    from arboles_de_red.visualizador_pyvis import VisualizadorPyVis

    DEPENDENCIAS_VISUALIZACION = True
except ModuleNotFoundError:
    DEPENDENCIAS_VISUALIZACION = False


@unittest.skipUnless(
    DEPENDENCIAS_VISUALIZACION,
    "Instalá el grupo opcional poc-streamlit-estatica para estas pruebas.",
)
class VisualizadorPyVisTests(unittest.TestCase):
    def setUp(self):
        self.visualizador = VisualizadorPyVis()

    def test_conexiones_con_pesos_cero_negativo_direcciones_y_paralelas(self):
        entrada = ProcesadorConexionesCSV().preparar_entrada(
            "origen,destino,peso,dirigida\n"
            "A,B,0,true\n"
            "A,B,-2,false\n"
            "B,C,1,true\n"
        )
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual(len(red.nodes), 3)
        self.assertEqual(len(red.edges), 3)
        self.assertEqual([edge["id"] for edge in red.edges], ["arista-0", "arista-1", "arista-2"])
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[1]["arrows"], "")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("peso 0.0", red.edges[0]["title"])
        self.assertIn("peso -2.0", red.edges[1]["title"])
        self.assertIn("dirigida", red.edges[0]["title"])
        self.assertIn("no dirigida", red.edges[1]["title"])

    def test_vertices_aislados_y_peso_none_se_conservan(self):
        grafo = Grafo(
            ("A", "B", "aislado"),
            (Arista(0, "A", "B", None, True),),
        )
        entrada = Entrada(grafo, None)
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual({node["id"] for node in red.nodes}, {"A", "B", "aislado"})
        self.assertEqual(len(red.edges), 1)
        self.assertIn("sin peso", red.edges[0]["title"])
        self.assertNotIn("peso 0", red.edges[0]["title"])

    def test_cpm_asocia_duracion_y_precedencias_sin_peso(self):
        entrada = ProcesadorCPMCSV().preparar_entrada(
            "actividad,duracion,predecesoras\nA,2,\nB,3,A\nSolo,5,\n"
        )
        red = self.visualizador.construir_red(entrada, "CPM")
        nodos = {node["id"]: node for node in red.nodes}

        self.assertEqual(len(red.nodes), 3)
        self.assertIn("Duración: 2.0", nodos["A"]["label"])
        self.assertIn("Duración: 2.0", nodos["A"]["title"])
        self.assertEqual(len(red.edges), 1)
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("sin peso", red.edges[0]["title"])

    def test_pert_muestra_tripleta_original_y_precedencia_sin_peso(self):
        entrada = ProcesadorPERTCSV().preparar_entrada(
            "actividad,optimista,mas_probable,pesimista,predecesoras\n"
            "A,1,2,4,\nB,2,3,8,A\n"
        )
        red = self.visualizador.construir_red(entrada, "PERT")
        nodos = {node["id"]: node for node in red.nodes}

        self.assertIn("O: 1.0 | M: 2.0 | P: 4.0", nodos["A"]["label"])
        self.assertIn("Optimista: 1.0", nodos["A"]["title"])
        self.assertIn("Más probable: 2.0", nodos["A"]["title"])
        self.assertIn("Pesimista: 4.0", nodos["A"]["title"])
        self.assertEqual(len(red.edges), 1)
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("sin peso", red.edges[0]["title"])

    def test_escala_200_nodos_890_aristas_posiciones_fijas_sin_fisica(self):
        vertices = tuple(f"V{indice}" for indice in range(200))
        pares = combinations(vertices, 2)
        aristas = tuple(
            Arista(identificador, origen, destino, 1.0, False)
            for identificador, (origen, destino) in zip(range(890), pares)
        )
        entrada = Entrada(Grafo(vertices, aristas), None)

        posiciones_1 = self.visualizador.calcular_posiciones(entrada.grafo)
        posiciones_2 = self.visualizador.calcular_posiciones(entrada.grafo)
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual(len(posiciones_1), 200)
        self.assertEqual(posiciones_1, posiciones_2)
        self.assertEqual(len(red.nodes), 200)
        self.assertEqual(len(red.edges), 890)
        self.assertTrue(all(node["fixed"] is True for node in red.nodes))
        self.assertFalse(red.options["physics"]["enabled"])


if __name__ == "__main__":
    unittest.main()
