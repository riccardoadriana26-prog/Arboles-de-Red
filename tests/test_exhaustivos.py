"""Enumeración exhaustiva de dominios pequeños y finitos, con oráculos independientes."""

import unittest
from fractions import Fraction
from itertools import combinations, permutations, product
from math import inf, sqrt

from arboles_de_red import (
    Arista, CPM, Dijkstra, Entrada, EstimacionesPERT, FordFulkerson, Grafo,
    Kruskal, PERT, ParametrosCPM, ParametrosDijkstra, ParametrosFlujoMaximo,
    ParametrosPERT, Prim,
)
from oraculos import arbol_minimo, caminos_simples, corte_minimo, planificacion, racional


def red(vertices, extremos, estados, dirigida):
    # Identificadores no consecutivos: una solución no puede usarlos como índices.
    return Grafo(tuple(vertices), tuple(Arista(10 + 3 * i, u, v, peso, dirigida)
                                        for i, ((u, v), peso) in enumerate(zip(extremos, estados))
                                        if peso is not None))


class ExhaustivosTests(unittest.TestCase):
    def test_4096_grafos_ponderados_de_cuatro_vertices_prim_y_kruskal(self):
        extremos = tuple(combinations("ABCD", 2))
        for numero, estados in enumerate(product((None, -1, 0, 2), repeat=6)):
            with self.subTest(grafo=numero):
                grafo = red("ABCD", extremos, estados, False)
                esperado = arbol_minimo(grafo)
                for algoritmo in (Prim(), Kruskal()):
                    entrada = Entrada(grafo, None)
                    self.assertEqual(algoritmo.es_aplicable(entrada), esperado is not None)
                    if esperado is None:
                        continue
                    resultado = algoritmo.ejecutar(entrada)
                    self.assertEqual(resultado.solucion.peso_total, float(esperado))
                    self.assertEqual(len(resultado.solucion.aristas), 3)
                    elegidas = Grafo(grafo.vertices, resultado.solucion.aristas)
                    self.assertIsNotNone(arbol_minimo(elegidas))
                    self.assertTrue(all(a in grafo.aristas for a in elegidas.aristas))
                    ids = tuple(a.identificador for a in elegidas.aristas)
                    self.assertEqual(resultado.pasos[-1].detalle.aristas_arbol, ids)

    def test_4096_grafos_dirigidos_dijkstra_desde_cada_origen(self):
        extremos = tuple(permutations("ABC", 2))
        for numero, estados in enumerate(product((None, 0, 1, 2), repeat=6)):
            grafo = red("ABC", extremos, estados, True)
            for origen in grafo.vertices:
                with self.subTest(grafo=numero, origen=origen):
                    esperado = caminos_simples(grafo, origen)
                    solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra(origen))).solucion
                    self.assertEqual(dict(solucion.distancias), {v: inf if d is None else float(d) for v, d in esperado.items()})
                    self.assertEqual(solucion.inalcanzables, tuple(v for v, d in esperado.items() if d is None))
                    aristas = {a.identificador: a for a in grafo.aristas}
                    for destino in grafo.vertices:
                        ruta = solucion.ruta_hasta(destino)
                        if esperado[destino] is None:
                            self.assertIsNone(ruta)
                            continue
                        self.assertEqual((ruta[0], ruta[-1]), (origen, destino))
                        self.assertEqual(len(set(ruta)), len(ruta))
                        costo = Fraction(0)
                        for u, v in zip(ruta, ruta[1:]):
                            anterior, identificador = solucion.predecesores[v]
                            a = aristas[identificador]
                            self.assertEqual((anterior, a.origen, a.destino), (u, u, v))
                            costo += racional(a.peso)
                        self.assertEqual(costo, esperado[destino])

    def test_125_redes_mixtas_dijkstra_en_ambas_direcciones(self):
        variantes = (None, (0, False, False), (2, False, False), (1, True, False), (1, True, True))
        for numero, estados in enumerate(product(variantes, repeat=3)):
            aristas = []
            for i, ((u, v), estado) in enumerate(zip(combinations("ABC", 2), estados)):
                if estado is not None:
                    peso, dirigida, invertir = estado
                    aristas.append(Arista(i, v if invertir else u, u if invertir else v, peso, dirigida))
            grafo = Grafo(tuple("ABC"), tuple(aristas))
            for origen, destino in permutations(grafo.vertices, 2):
                with self.subTest(grafo=numero, origen=origen, destino=destino):
                    esperado = caminos_simples(grafo, origen)[destino]
                    solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra(origen, destino))).solucion
                    self.assertEqual(solucion.costo, None if esperado is None else float(esperado))
                    if esperado is None:
                        self.assertIsNone(solucion.aristas_ruta)
                    else:
                        self.assertEqual(len(solucion.aristas_ruta), len(solucion.ruta) - 1)

    def verificar_flujo_y_pasos(self, grafo, resultado, fuente, sumidero):
        solucion = resultado.solucion
        self.assertEqual(solucion.flujo_maximo, float(corte_minimo(grafo, fuente, sumidero)))
        self.assertEqual(solucion.capacidad_corte, solucion.flujo_maximo)
        self.assertIn(fuente, solucion.lado_fuente)
        self.assertIn(sumidero, solucion.lado_sumidero)
        self.assertEqual(set(solucion.lado_fuente) | set(solucion.lado_sumidero), set(grafo.vertices))
        self.assertFalse(set(solucion.lado_fuente) & set(solucion.lado_sumidero))
        aristas = {a.identificador: a for a in grafo.aristas}
        flujos = dict.fromkeys(aristas, Fraction(0))
        residuales = {(a.identificador, False): racional(a.peso) for a in grafo.aristas}
        residuales.update({(a.identificador, True): Fraction(0) for a in grafo.aristas})
        acumulado = Fraction(0)
        for paso in resultado.pasos:
            detalle = paso.detalle
            if detalle.camino:
                self.assertEqual(detalle.camino[0].origen, fuente)
                self.assertEqual(detalle.camino[-1].destino, sumidero)
                for anterior, siguiente in zip(detalle.camino, detalle.camino[1:]):
                    self.assertEqual(anterior.destino, siguiente.origen)
                cuello = min(residuales[t.arista, t.inverso] for t in detalle.camino)
                self.assertEqual(detalle.cuello_botella, float(cuello))
                self.assertGreater(cuello, 0)
                acumulado += cuello
                for tramo in detalle.camino:
                    a = aristas[tramo.arista]
                    extremos = (a.destino, a.origen) if tramo.inverso else (a.origen, a.destino)
                    self.assertEqual((tramo.origen, tramo.destino), extremos)
                    flujos[tramo.arista] += -cuello if tramo.inverso else cuello
                self.assertEqual(len(detalle.actualizaciones), 2 * len(detalle.camino))
                for cambio in detalle.actualizaciones:
                    clave = cambio.arista, cambio.inverso
                    self.assertEqual(cambio.antes, float(residuales[clave]))
                    residuales[clave] += cuello if clave not in {(t.arista, t.inverso) for t in detalle.camino} else -cuello
                    self.assertEqual(cambio.despues, float(residuales[clave]))
                    self.assertGreaterEqual(cambio.despues, 0)
            self.assertEqual(detalle.flujo_acumulado, float(acumulado))
            self.assertEqual(dict(detalle.flujo_por_arco), {i: float(f) for i, f in flujos.items()})
            balance = dict.fromkeys(grafo.vertices, Fraction(0))
            for i, f in flujos.items():
                a = aristas[i]
                self.assertTrue(0 <= f <= racional(a.peso))
                balance[a.origen] -= f
                balance[a.destino] += f
            self.assertEqual(balance[fuente], -acumulado)
            self.assertEqual(balance[sumidero], acumulado)
            self.assertTrue(all(b == 0 for v, b in balance.items() if v not in (fuente, sumidero)))
        self.assertEqual(dict(solucion.flujo_por_arco), {i: float(f) for i, f in flujos.items()})

    def test_4096_redes_de_tres_vertices_con_capacidades_cero_uno_dos(self):
        extremos = tuple(permutations("SAT", 2))
        for numero, estados in enumerate(product((None, 0, 1, 2), repeat=6)):
            with self.subTest(red=numero):
                grafo = red("SAT", extremos, estados, True)
                resultado = FordFulkerson().ejecutar(Entrada(grafo, ParametrosFlujoMaximo("S", "T")))
                self.verificar_flujo_y_pasos(grafo, resultado, "S", "T")

    def test_4096_redes_de_cuatro_vertices_con_todos_los_arcos_posibles(self):
        extremos = tuple(permutations("SABT", 2))
        for numero, estados in enumerate(product((None, 1), repeat=12)):
            with self.subTest(red=numero):
                grafo = red("SABT", extremos, estados, True)
                resultado = FordFulkerson().ejecutar(Entrada(grafo, ParametrosFlujoMaximo("S", "T")))
                self.verificar_flujo_y_pasos(grafo, resultado, "S", "T")

    def verificar_planificacion(self, grafo, duraciones, solucion):
        duracion, rutas, tiempos = planificacion(grafo, duraciones)
        self.assertEqual(solucion.duracion_proyecto, float(duracion))
        self.assertEqual(set(solucion.rutas_criticas), rutas)
        self.assertEqual(solucion.rutas_criticas.cantidad, len(rutas))
        for v, valores in tiempos.items():
            t = solucion.actividades[v]
            self.assertEqual((t.ic, t.tc, t.il, t.tl, t.holgura), tuple(float(x) for x in valores))

    def test_5184_planificaciones_con_ceros_y_todas_las_precedencias_ordenadas(self):
        extremos = tuple(combinations("ABCD", 2))
        for mascara in range(64):
            aristas = tuple(Arista(i, u, v, None, True) for i, (u, v) in enumerate(extremos) if mascara & (1 << i))
            grafo = Grafo(tuple("ABCD" if mascara % 2 else "DCBA"), aristas)
            for duraciones in product((0, 1, 2), repeat=4):
                with self.subTest(red=mascara, duraciones=duraciones):
                    datos = dict(zip("ABCD", duraciones))
                    resultado = CPM().ejecutar(Entrada(grafo, ParametrosCPM(datos)))
                    self.verificar_planificacion(grafo, {v: racional(t) for v, t in datos.items()}, resultado.solucion)

    def test_1000_redes_pert_con_distintas_estimaciones_y_empates(self):
        extremos = tuple(combinations("ABC", 2))
        tripletas = ((0, 0, 0), (1, 1, 1), (0, 1, 2), (0, 0, 6), (0, 2, 6))
        for mascara in range(8):
            grafo = Grafo(tuple("CBA"), tuple(Arista(i, u, v, None, True)
                                             for i, (u, v) in enumerate(extremos) if mascara & (1 << i)))
            for valores in product(tripletas, repeat=3):
                with self.subTest(red=mascara, tripletas=valores):
                    estimaciones = {v: EstimacionesPERT(*ts) for v, ts in zip("ABC", valores)}
                    esperados = {v: (racional(a) + 4 * racional(m) + racional(b)) / 6 for v, (a, m, b) in zip("ABC", valores)}
                    varianzas = {v: ((racional(b) - racional(a)) / 6) ** 2 for v, (a, m, b) in zip("ABC", valores)}
                    solucion = PERT().ejecutar(Entrada(grafo, ParametrosPERT(estimaciones))).solucion
                    self.verificar_planificacion(grafo, esperados, solucion.planificacion)
                    self.assertEqual(solucion.estimaciones, estimaciones)
                    self.assertEqual(dict(solucion.tiempos_esperados), {v: float(t) for v, t in esperados.items()})
                    for ruta in solucion.variabilidad_rutas():
                        varianza = sum(varianzas[v] for v in ruta.actividades)
                        self.assertAlmostEqual(ruta.varianza, float(varianza))
                        self.assertAlmostEqual(ruta.desviacion_estandar, sqrt(float(varianza)))

    def test_ciclos_en_las_64_topologias_dirigidas_de_tres_actividades(self):
        extremos = tuple(permutations("ABC", 2))
        for mascara in range(64):
            with self.subTest(red=mascara):
                grafo = Grafo(tuple("ABC"), tuple(Arista(i, u, v, None, True)
                                                 for i, (u, v) in enumerate(extremos) if mascara & (1 << i)))
                ordenable = any(all(orden.index(a.origen) < orden.index(a.destino) for a in grafo.aristas)
                                for orden in permutations(grafo.vertices))
                cpm = Entrada(grafo, ParametrosCPM(dict.fromkeys(grafo.vertices, 1)))
                pert = Entrada(grafo, ParametrosPERT(dict.fromkeys(grafo.vertices, EstimacionesPERT(1, 1, 1))))
                self.assertEqual(CPM().es_aplicable(cpm), ordenable)
                self.assertEqual(PERT().es_aplicable(pert), ordenable)


if __name__ == "__main__":
    unittest.main()
