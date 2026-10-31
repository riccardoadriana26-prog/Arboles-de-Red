"""Redes de solución final desde proyecciones, sin eventos del recorrido."""

import unittest
from dataclasses import replace
from unittest.mock import patch

from arboles_de_red.algoritmo import Entrada, Resultado
from arboles_de_red.arbol_expansion import Prim, Kruskal
from arboles_de_red.cpm import CPM
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.flujo_maximo import FordFulkerson
from arboles_de_red.grafo import Arista, Grafo
from arboles_de_red.parametros import (
    EstimacionesPERT, ParametrosCPM, ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT,
)
from arboles_de_red.pert import PERT
from arboles_de_red.proyeccion_resultados import proyectar_resultado

try:
    from arboles_de_red.visualizador_pyvis import VisualizadorPyVis
    DEPENDENCIAS_VISUALES = True
except ModuleNotFoundError:
    DEPENDENCIAS_VISUALES = False


def grafo(vertices, aristas, dirigida=False):
    return Grafo(tuple(vertices), tuple(Arista(i, u, v, peso, dirigida) for i, u, v, peso in aristas))


@unittest.skipUnless(DEPENDENCIAS_VISUALES, "Requiere el grupo opcional poc-streamlit-estatica.")
class VisualizadorResultadosTests(unittest.TestCase):
    def setUp(self):
        self.visualizador = VisualizadorPyVis()

    def construir(self, entrada, proyeccion, formato):
        posiciones = {v: (i * 10.25, i * -7.5) for i, v in enumerate(entrada.grafo.vertices)}
        original = repr((entrada, proyeccion, posiciones))
        with patch.object(self.visualizador, "calcular_posiciones", side_effect=AssertionError("No recalcular layout")):
            red = self.visualizador.construir_red_resultado(entrada, formato, proyeccion, posiciones)
        self.assertEqual(repr((entrada, proyeccion, posiciones)), original)
        self.assertEqual({n["id"] for n in red.nodes}, set(entrada.grafo.vertices))
        self.assertEqual({a["id"] for a in red.edges}, {f"arista-{a.identificador}" for a in entrada.grafo.aristas})
        self.assertEqual(len(red.edges), len(entrada.grafo.aristas))
        nodos = {n["id"]: n for n in red.nodes}
        aristas = {a["id"]: a for a in red.edges}
        for v, posicion in posiciones.items():
            self.assertEqual((nodos[v]["x"], nodos[v]["y"]), posicion)
            self.assertTrue(nodos[v]["fixed"])
        for a in entrada.grafo.aristas:
            visual = aristas[f"arista-{a.identificador}"]
            self.assertEqual((visual["from"], visual["to"]), (a.origen, a.destino))
            self.assertEqual(visual["arrows"], "to" if a.dirigida else "")
            self.assertEqual(visual["label"], "")
        self.assertFalse(red.options["physics"]["enabled"])
        self.assertTrue(red.options["interaction"]["navigationButtons"])
        self.assertTrue(red.options["interaction"]["zoomView"])
        self.assertTrue(red.options["interaction"]["dragView"])
        self.assertIn('<style id="estilo-navegacion-pyvis">', self.visualizador.generar_html(red))
        titulos = "\n".join(elemento["title"] for elemento in red.nodes + red.edges).lower()
        for termino in ("evaluada", "rechazada", "frontera", "elegida en este paso", "evento actual", "residual"):
            self.assertNotIn(termino, titulos)
        return nodos, aristas

    def ids_resaltados(self, aristas):
        return {identificador for identificador, datos in aristas.items() if datos["width"] > 1}

    def nodos_resaltados(self, nodos):
        return {v for v, datos in nodos.items() if datos["font"]["color"] == "#ffffff"}

    def test_prim_kruskal_resaltan_solo_arbol_y_conservan_paralelas(self):
        entrada = Entrada(grafo("ABCD", [
            (11, "A", "B", 1), (12, "A", "B", 3), (23, "B", "C", 2),
            (34, "C", "D", 4), (41, "A", "D", 9),
        ]), None)
        for nombre, clase in (("prim", Prim), ("kruskal", Kruskal)):
            with self.subTest(algoritmo=nombre):
                p = proyectar_resultado(entrada, clase().ejecutar(entrada), nombre)
                nodos, aristas = self.construir(entrada, p, "Conexiones")
                self.assertEqual(self.ids_resaltados(aristas), {"arista-11", "arista-23", "arista-34"})
                self.assertEqual(self.nodos_resaltados(nodos), set("ABCD"))
                self.assertLess(aristas["arista-12"]["color"]["opacity"], aristas["arista-11"]["color"]["opacity"])
                self.assertIn("Peso total del árbol: 7", nodos["A"]["title"])

    def dijkstra(self):
        entrada = Entrada(grafo("ABCDX", [
            (10, "A", "B", 5), (11, "A", "B", 1), (25, "B", "D", 2),
            (31, "A", "C", 2), (40, "C", "D", 10),
        ], True), ParametrosDijkstra("A"))
        return entrada, proyectar_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")

    def test_dijkstra_solo_ruta_consultada_no_todas_las_ramas_predecesoras(self):
        entrada, base = self.dijkstra()
        p = base.consultar_destino("D")
        nodos, aristas = self.construir(entrada, p, "Conexiones")
        self.assertEqual(self.ids_resaltados(aristas), {"arista-11", "arista-25"})
        self.assertEqual(self.nodos_resaltados(nodos), set("ABD"))
        self.assertIn("Origen", nodos["A"]["label"])
        self.assertIn("Destino", nodos["D"]["label"])
        self.assertNotEqual(nodos["A"]["color"], nodos["D"]["color"])
        self.assertIn("Costo final de la ruta: 3", nodos["D"]["title"])
        self.assertIn("C", p.predecesores)

    def test_dijkstra_origen_igual_destino(self):
        entrada, p = self.dijkstra()
        nodos, aristas = self.construir(entrada, p.consultar_destino("A"), "Conexiones")
        self.assertEqual(self.ids_resaltados(aristas), set())
        self.assertEqual(self.nodos_resaltados(nodos), {"A"})
        self.assertIn("Origen y Destino", nodos["A"]["label"])
        self.assertIn("Costo final de la ruta: 0", nodos["A"]["title"])

    def test_dijkstra_inalcanzable_o_sin_consulta_no_fabrican_ruta(self):
        entrada, base = self.dijkstra()
        for p in (base, base.consultar_destino("X")):
            with self.subTest(destino=p.destino):
                nodos, aristas = self.construir(entrada, p, "Conexiones")
                self.assertEqual(self.ids_resaltados(aristas), set())
                self.assertEqual(self.nodos_resaltados(nodos), set())
                self.assertIn("Origen", nodos["A"]["label"])
                if p.destino is not None:
                    self.assertIn("Destino", nodos["X"]["label"])
                    self.assertIn("inalcanzable", nodos["X"]["title"])

    def test_flujo_capacidad_flujo_por_id_ceros_paralelas_antiparalelas_sin_residuales(self):
        entrada = Entrada(grafo("SAT", [
            (10, "S", "A", 1), (11, "S", "A", 2), (12, "A", "S", 1),
            (20, "A", "T", 2), (21, "S", "T", 0), (22, "T", "S", 1),
        ], True), ParametrosFlujoMaximo("S", "T"))
        p = proyectar_resultado(entrada, FordFulkerson().ejecutar(entrada), "flujo_maximo")
        nodos, aristas = self.construir(entrada, p, "Conexiones")
        self.assertEqual(self.ids_resaltados(aristas), {f"arista-{i}" for i, a in p.arcos.items() if a.flujo > 0})
        self.assertIn("Flujo final: 1 / 2", aristas["arista-11"]["title"])
        self.assertIn("Capacidad original: 2", aristas["arista-11"]["title"])
        self.assertIn("Flujo final: 0 / 0", aristas["arista-21"]["title"])
        self.assertIn("Flujo final: 0 / 1", aristas["arista-12"]["title"])
        self.assertIn("Flujo máximo: 2", nodos["S"]["title"])

    def test_flujo_maximo_cero_no_oculta_arcos(self):
        entrada = Entrada(grafo("SAT", [(0, "S", "A", 0), (9, "A", "T", 3)], True),
                          ParametrosFlujoMaximo("S", "T"))
        p = proyectar_resultado(entrada, FordFulkerson().ejecutar(entrada), "flujo_maximo")
        _, aristas = self.construir(entrada, p, "Conexiones")
        self.assertEqual(self.ids_resaltados(aristas), set())
        self.assertEqual(len(aristas), 2)

    def test_cpm_criticas_y_no_criticas_siguen_aon_con_valores_finales(self):
        entrada = Entrada(grafo(("A", "B", "C", "D", "Solo"), [
            (70, "A", "C", None), (71, "A", "C", None), (80, "B", "C", None),
            (90, "C", "D", None), (99, "A", "D", None),
        ], True), ParametrosCPM({"A": 2, "B": 2, "C": 3, "D": 1, "Solo": 1}))
        p = proyectar_resultado(entrada, CPM().ejecutar(entrada), "cpm")
        nodos, aristas = self.construir(entrada, p, "CPM")
        self.assertEqual(self.nodos_resaltados(nodos), set(p.actividades_criticas))
        self.assertEqual(self.ids_resaltados(aristas), {f"arista-{i}" for i in p.aristas_criticas})
        self.assertNotIn("arista-99", self.ids_resaltados(aristas))
        self.assertIn("IC=2 | TC=5 | IL=2 | TL=5 | Holgura=0", nodos["C"]["label"])
        self.assertIn("Duración del proyecto: 6", nodos["C"]["title"])
        self.assertIn("Duración: 1", nodos["Solo"]["title"])
        self.assertTrue(all("sin peso" in a["title"] for a in aristas.values()))

    def test_pert_estimaciones_y_planificacion_formateadas_sin_cambiar_precision(self):
        entrada = Entrada(grafo(("A", "B", "C", "Solo"), [
            (70, "A", "C", None), (71, "A", "C", None), (80, "B", "C", None),
        ], True), ParametrosPERT({
            "A": EstimacionesPERT(1, 4, 9), "B": EstimacionesPERT(1, 4, 9),
            "C": EstimacionesPERT(6, 6, 6), "Solo": EstimacionesPERT(1, 1, 1),
        }))
        p = proyectar_resultado(entrada, PERT().ejecutar(entrada), "pert")
        nodos, aristas = self.construir(entrada, p, "PERT")
        self.assertEqual(self.nodos_resaltados(nodos), set(p.actividades_criticas))
        self.assertEqual(self.ids_resaltados(aristas), {f"arista-{i}" for i in p.aristas_criticas})
        self.assertIn("O: 1 | M: 4 | P: 9", nodos["A"]["label"])
        self.assertIn("E: 4.33 | Var: 1.78", nodos["A"]["label"])
        self.assertIn("Varianza: 1.78", nodos["A"]["title"])
        self.assertIn("TC=10.33", nodos["C"]["label"])
        self.assertIn("TL: 10.33", nodos["C"]["title"])
        self.assertIn("Duración esperada: 10.33", nodos["C"]["title"])
        self.assertEqual(p.varianzas["A"], 1.7777777777777777)
        self.assertEqual(p.tiempos_esperados["A"], 4.333333333333333)
        self.assertEqual(p.actividades["C"].tc, 10.333333333333334)

    def test_regresion_algoritmo_runtime_incompatible_en_todas_las_variantes(self):
        from tests.test_proyeccion_resultados import ProyeccionResultadosTests
        cargas = ProyeccionResultadosTests()
        for algoritmo, clase, entrada, formato in (
            ("prim", Prim, cargas.mst(), "Conexiones"),
            ("dijkstra", Dijkstra, cargas.dijkstra("D"), "Conexiones"),
            ("flujo_maximo", FordFulkerson, cargas.flujo(), "Conexiones"),
            ("cpm", CPM, cargas.cpm(), "CPM"),
            ("pert", PERT, cargas.pert(), "PERT"),
        ):
            with self.subTest(algoritmo=algoritmo):
                p = proyectar_resultado(entrada, clase().ejecutar(entrada), algoritmo)
                incorrecto = "cpm" if algoritmo == "prim" else "prim"
                with self.assertRaisesRegex(ValueError, "algoritmo incompatible"):
                    self.visualizador.construir_red_resultado(entrada, formato, replace(p, algoritmo=incorrecto))

    def test_regresion_dijkstra_arista_existente_no_corresponde_al_tramo(self):
        entrada = Entrada(grafo("ABC", [(0, "A", "B", 1), (1, "A", "C", 2)], True),
                          ParametrosDijkstra("A", "B"))
        p = proyectar_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")
        for nueva in (Arista(0, "A", "C", 1, True), Arista(0, "B", "A", 1, True)):
            with self.subTest(arista=nueva), self.assertRaisesRegex(ValueError, "#0.*tramo"):
                ajena = replace(entrada, grafo=Grafo(entrada.grafo.vertices, (nueva, entrada.grafo.aristas[1])))
                self.visualizador.construir_red_resultado(ajena, "Conexiones", p)
        for cambios in ({"aristas_ruta": ()}, {"ruta": ("A", "C")}, {"costo": None}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                self.visualizador.construir_red_resultado(entrada, "Conexiones", replace(p, **cambios))

    def test_regresion_flujo_capacidad_extremos_id_y_direccion(self):
        entrada = Entrada(grafo("ST", [(0, "S", "T", 2)], True), ParametrosFlujoMaximo("S", "T"))
        p = proyectar_resultado(entrada, FordFulkerson().ejecutar(entrada), "flujo_maximo")
        ajena = replace(entrada, grafo=grafo("ST", [(0, "S", "T", 1)], True))
        with self.assertRaisesRegex(ValueError, "capacidad proyectada"):
            self.visualizador.construir_red_resultado(ajena, "Conexiones", p)
        for cambios in ({"capacidad_original": 1}, {"origen": "T"}, {"identificador": 99}, {"flujo": 3}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                alterada = replace(p, arcos={0: replace(p.arcos[0], **cambios)})
                self.visualizador.construir_red_resultado(entrada, "Conexiones", alterada)
        no_dirigida = replace(entrada, grafo=grafo("ST", [(0, "S", "T", 2)], False))
        with self.assertRaisesRegex(ValueError, "dirigida"):
            self.visualizador.construir_red_resultado(no_dirigida, "Conexiones", p)

    def test_regresion_planificacion_precedencias_criticas_y_metadatos_pert(self):
        g = grafo("ABC", [(0, "A", "B", None), (1, "A", "C", None)], True)
        for formato, clase, parametros in (
            ("CPM", CPM, ParametrosCPM({"A": 1, "B": 3, "C": 1})),
            ("PERT", PERT, ParametrosPERT({v: EstimacionesPERT(t, t, t) for v, t in
                                          {"A": 1, "B": 3, "C": 1}.items()})),
        ):
            with self.subTest(formato=formato):
                entrada = Entrada(g, parametros)
                p = proyectar_resultado(entrada, clase().ejecutar(entrada), formato.lower())
                for ids in ((1,), (999,)):
                    with self.assertRaises(ValueError):
                        self.visualizador.construir_red_resultado(entrada, formato, replace(p, aristas_criticas=ids))
                if formato == "PERT":
                    otras = dict(p.estimaciones)
                    otras["A"] = EstimacionesPERT(2, 2, 2)
                    with self.assertRaisesRegex(ValueError, "estimaciones.*originales"):
                        self.visualizador.construir_red_resultado(entrada, formato, replace(p, estimaciones=otras))
                    with self.assertRaisesRegex(ValueError, "varianzas"):
                        self.visualizador.construir_red_resultado(entrada, formato, replace(p, varianzas={}))

    def test_resultado_sin_pasos_no_construye_estados_ni_reinvoca_resolutor(self):
        entrada = Entrada(grafo("AB", [(7, "A", "B", 1)]), None)
        resultado = Prim().ejecutar(entrada)
        p = proyectar_resultado(entrada, Resultado(resultado.solucion, ()), "prim")
        with patch.object(Prim, "_resolver", side_effect=AssertionError("No resolver")), \
             patch("arboles_de_red.visualizador_pyvis.EstadoVisualPaso", side_effect=AssertionError("No crear paso")):
            self.construir(entrada, p, "Conexiones")


if __name__ == "__main__":
    unittest.main()
