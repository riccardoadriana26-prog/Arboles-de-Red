"""Escala, transformaciones que conservan soluciones y certificados de los pasos."""

import unittest
from decimal import Decimal
from fractions import Fraction
from itertools import combinations
from math import inf
from random import Random

from arboles_de_red import (
    Arista, CPM, Dijkstra, Entrada, EstimacionesPERT, FordFulkerson, Grafo, Kruskal,
    PERT, ParametrosCPM, ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT, Prim,
)


class PropiedadesCoreTests(unittest.TestCase):
    def test_prim_kruskal_y_dijkstra_en_grafo_completo_de_200_vertices(self):
        vertices = tuple(f"V{i}" for i in range(200))
        grafo = Grafo(vertices, tuple(Arista(i, u, v, 1, False) for i, (u, v) in enumerate(combinations(vertices, 2))))
        self.assertEqual(len(grafo.aristas), 19900)
        for algoritmo in (Prim(), Kruskal()):
            with self.subTest(algoritmo=type(algoritmo).__name__):
                solucion = algoritmo.ejecutar(Entrada(grafo, None)).solucion
                self.assertEqual(solucion.peso_total, 199)
                self.assertEqual(len(solucion.aristas), 199)
        solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra("V0", "V199"))).solucion
        self.assertEqual(solucion.costo, 1)
        self.assertEqual(solucion.ruta, ("V0", "V199"))

    def test_flujo_en_red_de_200_vertices_9999_arcos_y_99_aumentos(self):
        izquierda = tuple(f"A{i}" for i in range(99))
        derecha = tuple(f"B{i}" for i in range(99))
        extremos = [("S", v) for v in izquierda] + [(u, v) for u in izquierda for v in derecha] + [(v, "T") for v in derecha]
        grafo = Grafo(("S",) + izquierda + derecha + ("T",),
                      tuple(Arista(i, u, v, 1, True) for i, (u, v) in enumerate(extremos)))
        self.assertEqual(len(grafo.aristas), 9999)
        resultado = FordFulkerson().ejecutar(Entrada(grafo, ParametrosFlujoMaximo("S", "T")))
        self.assertEqual(resultado.solucion.flujo_maximo, 99)
        self.assertEqual(resultado.solucion.capacidad_corte, 99)
        self.assertEqual(sum(bool(p.detalle.camino) for p in resultado.pasos), 99)

    def test_cpm_y_pert_en_dag_completo_de_200_actividades(self):
        vertices = tuple(f"V{i}" for i in range(200))
        grafo = Grafo(tuple(reversed(vertices)), tuple(Arista(i, u, v, None, True)
                                                      for i, (u, v) in enumerate(combinations(vertices, 2))))
        for algoritmo, parametros, duracion in (
            (CPM(), ParametrosCPM(dict.fromkeys(vertices, 1)), 200),
            (PERT(), ParametrosPERT(dict.fromkeys(vertices, EstimacionesPERT(1, 2, 3))), 400),
        ):
            with self.subTest(algoritmo=type(algoritmo).__name__):
                solucion = algoritmo.ejecutar(Entrada(grafo, parametros)).solucion
                plan = solucion if isinstance(algoritmo, CPM) else solucion.planificacion
                self.assertEqual(plan.duracion_proyecto, duracion)
                self.assertEqual(tuple(plan.rutas_criticas), (vertices,))

    def test_los_seis_resolutores_en_cadenas_de_1500_vertices_sin_recursion(self):
        vertices = tuple(f"V{i}" for i in range(1500))
        conexion = Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], 1, False) for i in range(1499)))
        for algoritmo in (Prim(), Kruskal()):
            with self.subTest(algoritmo=type(algoritmo).__name__):
                self.assertEqual(algoritmo.ejecutar(Entrada(conexion, None)).solucion.peso_total, 1499)
        camino = Dijkstra().ejecutar(Entrada(conexion, ParametrosDijkstra("V0", "V1499"))).solucion
        self.assertEqual(camino.ruta, vertices)
        self.assertEqual(camino.costo, 1499)
        flujo = Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], 1, True) for i in range(1499)))
        self.assertEqual(FordFulkerson().ejecutar(Entrada(flujo, ParametrosFlujoMaximo("V0", "V1499"))).solucion.flujo_maximo, 1)
        aon = Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], None, True) for i in range(1499)))
        cpm = CPM().ejecutar(Entrada(aon, ParametrosCPM(dict.fromkeys(vertices, 1)))).solucion
        self.assertEqual(cpm.duracion_proyecto, 1500)
        self.assertEqual(next(iter(cpm.rutas_criticas)), vertices)
        pert = PERT().ejecutar(Entrada(aon, ParametrosPERT(dict.fromkeys(vertices, EstimacionesPERT(1, 1, 1))))).solucion
        self.assertEqual(pert.duracion_esperada, 1500)
        self.assertEqual(next(pert.variabilidad_rutas()).varianza, 0)

    def test_escalar_pesos_y_cambiar_nombres_conserva_las_soluciones(self):
        nombres = {"A": "Edificio1", "B": "Nodo2", "C": "Servidor3", "D": "Terminal4"}
        conexiones = (("A", "B", 2), ("A", "C", 6), ("B", "C", 1), ("C", "D", 3), ("B", "D", 8))
        base = Grafo(tuple(nombres), tuple(Arista(i, u, v, w, False) for i, (u, v, w) in enumerate(conexiones)))
        escalado = Grafo(tuple(reversed(tuple(nombres.values()))),
                         tuple(Arista(a.identificador, nombres[a.destino], nombres[a.origen], 7 * a.peso, False) for a in base.aristas))
        for algoritmo in (Prim(), Kruskal()):
            self.assertEqual(algoritmo.ejecutar(Entrada(escalado, None)).solucion.peso_total,
                             7 * algoritmo.ejecutar(Entrada(base, None)).solucion.peso_total)
        antes = Dijkstra().ejecutar(Entrada(base, ParametrosDijkstra("A", "D"))).solucion
        despues = Dijkstra().ejecutar(Entrada(escalado, ParametrosDijkstra(nombres["A"], nombres["D"]))).solucion
        self.assertEqual(despues.costo, 7 * antes.costo)
        self.assertEqual(despues.ruta, tuple(nombres[v] for v in antes.ruta))

    def test_flujo_escalar_capacidades_y_arcos_paralelos_conservan_el_valor(self):
        base = Grafo(tuple("SAT"), (Arista(10, "S", "A", 3, True), Arista(20, "A", "T", 3, True)))
        paralelo = Grafo(tuple("SAT"), (Arista(1, "S", "A", 1, True), Arista(5, "S", "A", 2, True),
                                       Arista(9, "A", "T", 3, True), Arista(100, "A", "S", 8, True),
                                       Arista(1000, "T", "A", 5, True)))
        parametros = ParametrosFlujoMaximo("S", "T")
        esperado = FordFulkerson().ejecutar(Entrada(base, parametros)).solucion.flujo_maximo
        self.assertEqual(FordFulkerson().ejecutar(Entrada(paralelo, parametros)).solucion.flujo_maximo, esperado)
        escalado = Grafo(base.vertices, tuple(Arista(a.identificador, a.origen, a.destino, 7 * a.peso, True) for a in base.aristas))
        self.assertEqual(FordFulkerson().ejecutar(Entrada(escalado, parametros)).solucion.flujo_maximo, 7 * esperado)

    def test_cpm_y_pert_escalan_tiempos_y_varianzas_con_distintas_potencias(self):
        grafo = Grafo(tuple("ABC"), (Arista(0, "A", "C", None, True), Arista(1, "B", "C", None, True)))
        duraciones = {"A": 2, "B": 1, "C": 3}
        cpm = CPM().ejecutar(Entrada(grafo, ParametrosCPM(duraciones))).solucion
        otro = CPM().ejecutar(Entrada(grafo, ParametrosCPM({v: 3 * t for v, t in duraciones.items()}))).solucion
        self.assertEqual(otro.duracion_proyecto, 3 * cpm.duracion_proyecto)
        self.assertEqual(tuple(otro.rutas_criticas), tuple(cpm.rutas_criticas))
        estimaciones = {v: EstimacionesPERT(0, t, 2 * t) for v, t in duraciones.items()}
        pert = PERT().ejecutar(Entrada(grafo, ParametrosPERT(estimaciones))).solucion
        otro = PERT().ejecutar(Entrada(grafo, ParametrosPERT({v: EstimacionesPERT(0, 3 * t, 6 * t) for v, t in duraciones.items()}))).solucion
        self.assertEqual(otro.duracion_esperada, 3 * pert.duracion_esperada)
        self.assertAlmostEqual(next(otro.variabilidad_rutas()).varianza, 9 * next(pert.variabilidad_rutas()).varianza)

    def test_precedencias_redundantes_y_duraciones_cero(self):
        aristas = (Arista(0, "A", "B", None, True), Arista(1, "B", "C", None, True))
        base = Grafo(tuple("ABC"), aristas)
        redundante = Grafo(tuple("ABC"), aristas + (Arista(2, "A", "C", None, True),))
        datos = ParametrosCPM({"A": 1, "B": 0, "C": 1})
        primero = CPM().ejecutar(Entrada(base, datos)).solucion
        segundo = CPM().ejecutar(Entrada(redundante, datos)).solucion
        self.assertEqual(primero.actividades, segundo.actividades)
        self.assertEqual(set(segundo.rutas_criticas), {("A", "B", "C"), ("A", "C")})

    def test_parametros_decimal_y_fraccion_y_copias_de_mapas(self):
        grafo = Grafo(tuple("ABC"), (Arista(0, "A", "B", None, True), Arista(1, "B", "C", None, True)))
        datos = {"A": Fraction(1, 3), "B": Decimal("0.1"), "C": 2}
        parametros = ParametrosCPM(datos)
        datos["A"] = 99
        solucion = CPM().ejecutar(Entrada(grafo, parametros)).solucion
        self.assertEqual(solucion.duracion_proyecto, float(Fraction(73, 30)))
        estimaciones = {v: EstimacionesPERT(Fraction(1, 3), Fraction(1, 3), Fraction(1, 3)) for v in grafo.vertices}
        parametros_pert = ParametrosPERT(estimaciones)
        estimaciones["A"] = EstimacionesPERT(99, 99, 99)
        solucion = PERT().ejecutar(Entrada(grafo, parametros_pert)).solucion
        self.assertEqual(solucion.duracion_esperada, 1)

    def test_los_pasos_de_dijkstra_reconstruyen_sus_distancias(self):
        azar = Random(813)
        for numero in range(40):
            with self.subTest(red=numero):
                aristas = tuple(Arista(i, u, v, azar.randint(0, 5), bool(azar.randrange(2)))
                                 for i, (u, v) in enumerate(combinations("ABCDE", 2)) if azar.random() < .7)
                grafo = Grafo(tuple("ABCDE"), aristas)
                resultado = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra("A")))
                distancias = dict.fromkeys(grafo.vertices, inf)
                distancias["A"] = 0
                permanentes = []
                for paso in resultado.pasos:
                    d = paso.detalle
                    if d.accion == "fijar":
                        pendientes = [distancias[v] for v in grafo.vertices if v not in permanentes]
                        self.assertEqual(d.distancia_nueva, min(pendientes))
                        permanentes.append(d.vertice)
                    elif d.accion in ("relajar", "conservar"):
                        self.assertEqual(d.distancia_anterior, distancias[d.vertice])
                        if d.accion == "relajar":
                            self.assertLess(d.distancia_nueva, d.distancia_anterior)
                        else:
                            self.assertEqual(d.distancia_nueva, d.distancia_anterior)
                        distancias[d.vertice] = d.distancia_nueva
                    self.assertEqual(d.permanentes, tuple(permanentes))
                self.assertEqual(distancias, resultado.solucion.distancias)


if __name__ == "__main__":
    unittest.main()
