"""Pruebas de los estados reconstruidos desde eventos, sin reejecutar algoritmos."""

import unittest
from dataclasses import replace
from math import inf
from unittest.mock import patch

from arboles_de_red import (
    Arista, Entrada, EstimacionesPERT, Grafo, ParametrosCPM,
    ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT,
)
from arboles_de_red.arbol_expansion import Kruskal, Prim
from arboles_de_red.cpm import CPM
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.flujo_maximo import FordFulkerson
from arboles_de_red.pert import PERT
from arboles_de_red.reconstruccion import (
    ErrorReconstruccion, EstadoDijkstra, EstadoExpansion, EstadoFlujoResidual,
    EstadoPlanificacion, ReconstruccionEjecucion,
)


def construir(vertices, conexiones, dirigida=False):
    return Grafo(tuple(vertices), tuple(
        Arista(*conexion, dirigida) for conexion in conexiones
    ))


class ReconstruccionTests(unittest.TestCase):
    def reconstruir(self, identificador, entrada, algoritmo, **kwargs):
        resultado = algoritmo().ejecutar(entrada)
        return resultado, ReconstruccionEjecucion(entrada, resultado, identificador, **kwargs)

    def test_prim_conserva_arbol_y_frontera_sin_rechazos_ficticios(self):
        grafo = Grafo(("A", "B", "C", "D"), (
            Arista(17, "A", "B", 1, False), Arista(23, "B", "C", 2, False),
            Arista(31, "A", "C", 4, False), Arista(47, "C", "D", 3, False),
            Arista(59, "B", "D", 7, False),
        ))
        entrada = Entrada(grafo, None)
        resultado, rec = self.reconstruir("Prim", entrada, Prim)
        inicial = rec.estado_en(0).estado
        self.assertIsInstance(inicial, EstadoExpansion)
        self.assertEqual(inicial.aristas_arbol, ())
        self.assertEqual(inicial.vertices_arbol, ("A",))
        for numero, paso in enumerate(resultado.pasos, start=1):
            estado = rec.estado_en(numero).estado
            self.assertEqual(estado.aristas_arbol, paso.detalle.aristas_arbol)
            self.assertEqual(estado.aristas_evaluadas, paso.detalle.aristas_evaluadas)
            self.assertEqual(estado.arista_elegida, paso.detalle.arista)
            self.assertEqual(estado.aristas_rechazadas_ciclo, ())
        self.assertNotIn(23, rec.estado_en(2).estado.aristas_evaluadas)
        self.assertIn(23, rec.estado_en(3).estado.aristas_evaluadas)
        self.assertEqual(rec.estado_en(len(resultado.pasos)).estado.aristas_arbol,
                         tuple(a.identificador for a in resultado.solucion.aristas))

    def test_kruskal_reconstruye_rechazos_y_componentes(self):
        grafo = construir("ABCD", [(0, "A", "B", 1), (1, "B", "C", 2),
                                    (2, "A", "C", 3), (3, "C", "D", 4)])
        resultado, rec = self.reconstruir("Kruskal", Entrada(grafo, None), Kruskal)
        estados = [rec.estado_en(i).estado for i in range(len(resultado.pasos) + 1)]
        self.assertEqual(estados[0].componentes, (("A",), ("B",), ("C",), ("D",)))
        self.assertEqual(estados[4].aristas_evaluadas, (2,))
        self.assertEqual(estados[4].aristas_rechazadas_ciclo, (2,))
        self.assertEqual(estados[-1].aristas_arbol, (0, 1, 3))
        self.assertEqual(estados[-1].componentes, (("A", "B", "C", "D"),))

    def test_dijkstra_reconstruye_distancias_predecesores_y_permanentes(self):
        grafo = Grafo(tuple("ABCD"), (
            Arista(11, "A", "B", 5, True), Arista(12, "A", "C", 1, True),
            Arista(13, "C", "B", 1, True), Arista(14, "A", "D", 10, True),
            Arista(15, "C", "D", 20, True), Arista(16, "B", "D", 2, True),
        ))
        entrada = Entrada(grafo, ParametrosDijkstra("A"))
        resultado, rec = self.reconstruir("Dijkstra", entrada, Dijkstra)
        self.assertEqual(rec.estado_en(0).estado.distancias, {"A": 0.0, "B": inf, "C": inf, "D": inf})
        for i, paso in enumerate(resultado.pasos, start=1):
            estado = rec.estado_en(i).estado
            self.assertIsInstance(estado, EstadoDijkstra)
            detalle = paso.detalle
            self.assertEqual(estado.accion, detalle.accion)
            if detalle.accion == "conservar":
                self.assertEqual(estado.distancias[detalle.vertice], detalle.distancia_anterior)
                self.assertEqual(estado.predecesores.get(detalle.vertice), detalle.predecesor_anterior)
        estado_final = rec.estado_en(len(resultado.pasos)).estado
        self.assertEqual(estado_final.distancias, resultado.solucion.distancias)
        self.assertEqual(estado_final.predecesores, resultado.solucion.predecesores)
        self.assertEqual(estado_final.permanentes, ("A", "C", "B", "D"))

    def test_dijkstra_reconstruye_mejora_exacta_con_distancias_float_iguales(self):
        entrada = Entrada(construir("ABC", [
            (0, "A", "B", 10000000000000000), (1, "A", "C", 1),
            (2, "C", "B", 9999999999999998),
        ], True), ParametrosDijkstra("A"))
        resultado, rec = self.reconstruir("dijkstra", entrada, Dijkstra)
        mejora = next(p for p in resultado.pasos if p.detalle.arista == 2)
        self.assertEqual(mejora.detalle.accion, "relajar")
        self.assertEqual(mejora.detalle.distancia_anterior, 1e16)
        self.assertEqual(mejora.detalle.distancia_nueva, 1e16)
        estados = [rec.estado_en(i) for i in range(len(resultado.pasos) + 1)]
        self.assertEqual(estados[mejora.numero].estado.predecesores["B"], ("C", 2))
        self.assertEqual(estados[-1].estado.distancias, resultado.solucion.distancias)
        self.assertEqual(estados[-1].estado.predecesores, resultado.solucion.predecesores)
        self.assertEqual(rec.estado_en(mejora.numero), estados[mejora.numero])

    def test_dijkstra_no_admite_falsa_mejora_exactamente_empatada(self):
        entrada = Entrada(construir("ABC", [
            (0, "A", "B", 2), (1, "A", "C", 1), (2, "C", "B", 1),
        ], True), ParametrosDijkstra("A"))
        resultado = Dijkstra().ejecutar(entrada)
        paso = next(p for p in resultado.pasos if p.detalle.arista == 2)
        self.assertEqual(paso.detalle.accion, "conservar")
        detalle = replace(paso.detalle, accion="relajar", predecesor_nuevo=("C", 2))
        pasos = tuple(replace(p, detalle=detalle) if p.numero == paso.numero else p for p in resultado.pasos)
        rec = ReconstruccionEjecucion(entrada, replace(resultado, pasos=pasos), "dijkstra")
        with self.assertRaisesRegex(ErrorReconstruccion, "no mejora"):
            rec.estado_en(paso.numero)

    def test_pert_reconstruye_estimaciones_grandes_sin_overflow_auxiliar(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosPERT({
            "A": EstimacionesPERT(1e308, 1e308, 1e308),
        }))
        resultado, rec = self.reconstruir("pert", entrada, PERT)
        original = repr((entrada, resultado))
        estados = [rec.estado_en(i) for i in range(len(resultado.pasos) + 1)]
        self.assertEqual(estados[1].estado.tiempos_esperados["A"], 1e308)
        self.assertEqual(estados[1].estado.varianzas["A"], 0)
        self.assertEqual(estados[-1].estado.planificacion.duracion_proyecto, 1e308)
        self.assertEqual(estados[-1].estado.planificacion.valores_por_actividad["A"].tc, 1e308)
        self.assertEqual(repr((entrada, resultado)), original)

    def test_ford_fulkerson_reproduce_arcos_inversos_y_paralelos(self):
        # El primer caso fuerza el uso de C->A como residual inverso.
        grafo = construir("SABCDT", [
            (0, "S", "A", 1), (1, "S", "B", 1), (2, "A", "C", 1),
            (3, "A", "D", 1), (4, "B", "C", 1), (5, "C", "T", 1),
            (6, "D", "T", 1), (7, "B", "C", 0),
        ], True)
        entrada = Entrada(grafo, ParametrosFlujoMaximo("S", "T"))
        resultado, rec = self.reconstruir("FlujoMaximo", entrada, FordFulkerson)
        self.assertEqual(rec.estado_en(0).estado.flujo_por_arco[2], 0)
        estados = [rec.estado_en(i).estado for i in range(len(resultado.pasos) + 1)]
        self.assertTrue(any(t.inverso for p in resultado.pasos for t in p.detalle.camino))
        for i, paso in enumerate(resultado.pasos, start=1):
            estado = estados[i]
            self.assertIsInstance(estado, EstadoFlujoResidual)
            self.assertEqual(estado.flujo_por_arco, dict(paso.detalle.flujo_por_arco))
            for cambio in paso.detalle.actualizaciones:
                self.assertIn((cambio.arista, cambio.inverso), estado.capacidades_residuales)
        self.assertEqual(estados[-1].flujo_acumulado, resultado.solucion.flujo_maximo)
        self.assertIn((2, True), estados[-1].capacidades_residuales)
        self.assertEqual(len(grafo.aristas), 8)  # IDs paralelos siguen siendo distintos.

    def test_cpm_reconstruye_valores_por_fase_y_criticas(self):
        vertices = ("A", "B", "C", "D")
        grafo = Grafo(vertices, (Arista(21, "A", "C", None, True), Arista(22, "B", "C", None, True)))
        entrada = Entrada(grafo, ParametrosCPM({"A": 2, "B": 3, "C": 4, "D": 7}))
        resultado, rec = self.reconstruir("CPM", entrada, CPM)
        mitad = rec.estado_en(2).estado
        self.assertIsInstance(mitad, EstadoPlanificacion)
        self.assertEqual((mitad.valores_por_actividad["A"].ic, mitad.valores_por_actividad["A"].tc), (0, 2))
        self.assertIsNone(mitad.valores_por_actividad["A"].holgura)
        final = rec.estado_en(len(resultado.pasos)).estado
        self.assertEqual(final.duracion_proyecto, resultado.solucion.duracion_proyecto)
        self.assertEqual(final.actividades_criticas, resultado.pasos[-1].vertices_destacados)
        self.assertEqual(final.valores_por_actividad["C"].holgura, resultado.solucion.actividades["C"].holgura)

    def test_pert_acumula_estimaciones_y_luego_planificacion(self):
        vertices = ("A", "B", "C")
        grafo = Grafo(vertices, (Arista(40, "A", "C", None, True), Arista(41, "B", "C", None, True)))
        estimaciones = {"A": EstimacionesPERT(1, 2, 3), "B": EstimacionesPERT(2, 4, 6),
                        "C": EstimacionesPERT(3, 3, 9)}
        entrada = Entrada(grafo, ParametrosPERT(estimaciones))
        resultado, rec = self.reconstruir("PERT", entrada, PERT)
        estado_inicial = rec.estado_en(0).estado
        self.assertEqual(estado_inicial.estimaciones, estimaciones)
        self.assertEqual(dict(estado_inicial.tiempos_esperados), {})
        estado_estimacion = rec.estado_en(3).estado
        self.assertEqual(len(estado_estimacion.tiempos_esperados), 3)
        self.assertEqual(estado_estimacion.tiempos_esperados["A"], 2)
        self.assertEqual(estado_estimacion.fase, "estimacion")
        primer_plan = rec.estado_en(4).estado
        self.assertEqual(primer_plan.fase, "planificacion_adelante")
        self.assertEqual(primer_plan.planificacion.valores_por_actividad["A"].tc, 2)
        final = rec.estado_en(len(resultado.pasos)).estado
        self.assertEqual(final.planificacion.duracion_proyecto, resultado.solucion.duracion_esperada)
        self.assertEqual(final.planificacion.actividades_criticas, resultado.pasos[-1].vertices_destacados)

    def test_navegacion_no_monotonica_inmutable_y_no_reinvoca_resolvedores(self):
        grafo = construir("ABCDE", [(i, u, v, 1) for i, (u, v) in enumerate(
            (("A", "B"), ("B", "C"), ("C", "D"), ("D", "E")))])
        entrada = Entrada(grafo, None)
        resultado = Prim().ejecutar(entrada)
        # Acepta el identificador público del registro además del nombre visible.
        rec = ReconstruccionEjecucion(entrada, resultado, "prim", intervalo_checkpoint=2)
        with patch.object(Prim, "_resolver", side_effect=AssertionError("no debe reejecutar")):
            octavo = rec.estado_en(4)
            tercero = rec.estado_en(2)
            octavo_repetido = rec.estado_en(4)
            self.assertEqual(octavo, octavo_repetido)
            self.assertNotEqual(octavo, tercero)
            self.assertEqual(rec.estado_en(0).numero, 0)
            self.assertEqual(rec.estado_en(3).numero, 3)

    def test_navegar_no_invoca_resolutores_de_ninguno_de_los_seis_algoritmos(self):
        undirected = construir("ABC", [(0, "A", "B", 1), (1, "B", "C", 2), (2, "A", "C", 4)])
        directed = construir("ABC", [(0, "A", "B", 2), (1, "B", "C", 1), (2, "A", "C", 4)], True)
        aon = Grafo(("A", "B", "C"), (Arista(0, "A", "C", None, True),))
        casos = (
            ("Prim", Prim, Entrada(undirected, None)),
            ("Kruskal", Kruskal, Entrada(undirected, None)),
            ("Dijkstra", Dijkstra, Entrada(directed, ParametrosDijkstra("A", "C"))),
            ("FlujoMaximo", FordFulkerson, Entrada(directed, ParametrosFlujoMaximo("A", "C"))),
            ("CPM", CPM, Entrada(aon, ParametrosCPM({"A": 1, "B": 2, "C": 3}))),
            ("PERT", PERT, Entrada(aon, ParametrosPERT({
                "A": EstimacionesPERT(1, 1, 1), "B": EstimacionesPERT(2, 2, 2),
                "C": EstimacionesPERT(3, 3, 3),
            }))),
        )
        for nombre, clase, entrada in casos:
            with self.subTest(algoritmo=nombre):
                resultado = clase().ejecutar(entrada)
                rec = ReconstruccionEjecucion(entrada, resultado, nombre)
                with patch.object(clase, "_resolver", side_effect=AssertionError("resolutor invocado durante navegación")):
                    rec.estado_en(0)
                    rec.estado_en(len(resultado.pasos) // 2)
                    rec.estado_en(len(resultado.pasos))

    def test_checkpoint_mayor_a_64_y_validaciones_de_eventos(self):
        vertices = tuple(f"V{i}" for i in range(70))
        grafo = Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], 1, False) for i in range(69)))
        entrada = Entrada(grafo, None)
        resultado = Prim().ejecutar(entrada)
        rec = ReconstruccionEjecucion(entrada, resultado, "Prim")
        self.assertEqual(rec.estado_en(65).numero, 65)
        self.assertIn(64, rec._checkpoints)
        with self.assertRaises(IndexError):
            rec.estado_en(len(resultado.pasos) + 1)
        pasos_rotos = (resultado.pasos[0],) + tuple(
            type(p)(p.numero + 1, p.descripcion, p.vertices_destacados, p.aristas_destacadas, p.detalle)
            for p in resultado.pasos[1:]
        )
        with self.assertRaisesRegex(ErrorReconstruccion, "Numeración discontinua"):
            ReconstruccionEjecucion(entrada, type(resultado)(resultado.solucion, pasos_rotos), "Prim")

    def test_inconsistencia_residual_se_rechaza(self):
        grafo = construir("SAT", [(0, "S", "A", 1), (1, "A", "T", 1)], True)
        entrada = Entrada(grafo, ParametrosFlujoMaximo("S", "T"))
        resultado = FordFulkerson().ejecutar(entrada)
        paso = resultado.pasos[1]
        cambio = paso.detalle.actualizaciones[0]
        cambios = (type(cambio)(cambio.arista, cambio.origen, cambio.destino, cambio.inverso,
                                cambio.antes + 1, cambio.despues),) + paso.detalle.actualizaciones[1:]
        detalle = type(paso.detalle)(paso.detalle.camino, paso.detalle.cuello_botella,
                                     paso.detalle.flujo_acumulado, cambios, paso.detalle.flujo_por_arco)
        pasos = (resultado.pasos[0], type(paso)(paso.numero, paso.descripcion, paso.vertices_destacados,
                                                paso.aristas_destacadas, detalle), *resultado.pasos[2:])
        resultado_malo = type(resultado)(resultado.solucion, pasos)
        rec = ReconstruccionEjecucion(entrada, resultado_malo, "FlujoMaximo")
        with self.assertRaisesRegex(ErrorReconstruccion, "Residual anterior inconsistente"):
            rec.estado_en(2)


if __name__ == "__main__":
    unittest.main()
