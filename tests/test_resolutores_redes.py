"""Resultados conocidos e invariantes, contrastados con enumeración exhaustiva pequeña."""

import unittest
from dataclasses import FrozenInstanceError
from itertools import combinations
from math import inf
from random import Random

from arboles_de_red import Arista, Entrada, Grafo, ParametrosDijkstra, ParametrosFlujoMaximo
from arboles_de_red.algoritmo import AlgoritmoNoAplicableError
from arboles_de_red.arbol_expansion import Kruskal, Prim
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.flujo_maximo import FordFulkerson


def grafo(vertices, conexiones, dirigida=False):
    return Grafo(tuple(vertices), tuple(Arista(i, u, v, peso, dirigida)
                                       for i, (u, v, peso) in enumerate(conexiones)))


class ArbolExpansionTests(unittest.TestCase):
    def test_ejemplo_catedra_y_arbol_de_un_solo_vertice(self):
        red = grafo("ABCDEFG", [
            ("A", "B", 30), ("A", "D", 50), ("B", "C", 15), ("B", "D", 20),
            ("C", "F", 10), ("D", "E", 25), ("E", "G", 30), ("F", "G", 15),
        ])
        for algoritmo in (Prim(), Kruskal()):
            with self.subTest(algoritmo=type(algoritmo).__name__):
                resultado = algoritmo.ejecutar(Entrada(red, None))
                self.assertEqual(resultado.solucion.peso_total, 115)
                self.assertEqual(len(resultado.solucion.aristas), 6)
                self.assertEqual([p.numero for p in resultado.pasos], list(range(1, len(resultado.pasos) + 1)))
                unico = algoritmo.ejecutar(Entrada(grafo("A", []), None))
                self.assertEqual(unico.solucion.aristas, ())
                self.assertEqual(unico.solucion.peso_total, 0)

    def test_pesos_negativos_paralelas_y_empates_estables(self):
        red = grafo("ABC", [("A", "B", 0), ("B", "A", -2), ("B", "C", -2), ("A", "C", -2)])
        for algoritmo in (Prim(), Kruskal()):
            resultado = algoritmo.ejecutar(Entrada(red, None))
            self.assertEqual(tuple(a.identificador for a in resultado.solucion.aristas), (1, 2))
            self.assertEqual(resultado.solucion.peso_total, -4)
            self.assertEqual(resultado, algoritmo.ejecutar(Entrada(red, None)))
            with self.assertRaises(FrozenInstanceError):
                resultado.solucion.peso_total = 42
        ciclico = Kruskal().ejecutar(Entrada(grafo("ABCD", [
            ("A", "B", 1), ("B", "C", 2), ("A", "C", 3), ("C", "D", 4),
        ]), None))
        self.assertTrue(any(not p.detalle.aceptada for p in ciclico.pasos))

    def test_contraste_con_todos_los_subconjuntos_de_aristas(self):
        azar = Random(431)
        for _ in range(20):
            conexiones = [(u, v, azar.randint(-5, 6)) for u, v in zip("ABCD", "BCDE")]
            conexiones += [(u, v, azar.randint(-5, 6)) for u, v in combinations("ABCDE", 2) if azar.random() < .4]
            red = grafo("ABCDE", conexiones)
            costos = []
            for aristas in combinations(red.aristas, 4):
                vistos = {"A"}
                for _ in range(4):
                    for a in aristas:
                        if a.origen in vistos or a.destino in vistos:
                            vistos.update((a.origen, a.destino))
                if len(vistos) == 5:
                    costos.append(sum(a.peso for a in aristas))
            for algoritmo in (Prim(), Kruskal()):
                self.assertEqual(algoritmo.ejecutar(Entrada(red, None)).solucion.peso_total, min(costos))

    def test_rechaza_antes_de_resolver(self):
        for red in (grafo("AB", []), grafo("AB", [("A", "B", 1)], True)):
            for algoritmo in (Prim(), Kruskal()):
                with self.assertRaises(AlgoritmoNoAplicableError):
                    algoritmo.ejecutar(Entrada(red, None))


class DijkstraTests(unittest.TestCase):
    def test_ejemplo_catedra(self):
        red = grafo("ABCDEFG", [
            ("A", "B", 30), ("A", "D", 50), ("B", "C", 15), ("B", "D", 20),
            ("C", "F", 10), ("D", "E", 25), ("E", "G", 30), ("F", "G", 15),
        ])
        solucion = Dijkstra().ejecutar(Entrada(red, ParametrosDijkstra("A", "G"))).solucion
        self.assertEqual(solucion.ruta, ("A", "B", "C", "F", "G"))
        self.assertEqual(solucion.aristas_ruta, (0, 2, 4, 7))
        self.assertEqual(solucion.costo, 70)

    def test_red_mixta_paralelas_cero_inalcanzables_y_origen_igual_destino(self):
        red = Grafo(tuple("ABCDE"), (
            Arista(0, "A", "B", 5, True), Arista(1, "A", "B", 0, False),
            Arista(2, "B", "C", 0, True), Arista(3, "C", "A", 0, True),
            Arista(4, "D", "C", 1, True),
        ))
        algoritmo = Dijkstra()
        solucion = algoritmo.ejecutar(Entrada(red, ParametrosDijkstra("A", "D"))).solucion
        self.assertIsNone(solucion.ruta)
        self.assertIsNone(solucion.costo)
        self.assertEqual(solucion.inalcanzables, ("D", "E"))
        self.assertEqual(solucion.distancias["D"], inf)
        self.assertEqual(solucion.ruta_hasta("C"), ("A", "B", "C"))
        self.assertIsNone(solucion.ruta_hasta("E"))
        with self.assertRaises(TypeError):
            solucion.distancias["A"] = 20
        propio = algoritmo.ejecutar(Entrada(red, ParametrosDijkstra("A", "A"))).solucion
        self.assertEqual((propio.ruta, propio.aristas_ruta, propio.costo), (("A",), (), 0))
        sin_destino = algoritmo.ejecutar(Entrada(red, ParametrosDijkstra("B"))).solucion
        self.assertEqual(sin_destino.ruta_hasta("A"), ("B", "A"))

    def test_contraste_con_enumeracion_de_caminos_simples(self):
        azar = Random(98)
        for _ in range(25):
            aristas = [Arista(i, u, v, azar.randint(0, 9), bool(azar.randrange(2)))
                       for i, (u, v) in enumerate(combinations("ABCDE", 2)) if azar.random() < .5]
            red = Grafo(tuple("ABCDE"), tuple(aristas))
            costos = dict.fromkeys(red.vertices, inf)
            pendientes = [("A", frozenset("A"), 0)]
            while pendientes:
                actual, visitados, costo = pendientes.pop()
                costos[actual] = min(costos[actual], costo)
                for a in red.aristas:
                    vecino = a.destino if a.origen == actual else a.origen if not a.dirigida and a.destino == actual else None
                    if vecino is not None and vecino not in visitados:
                        pendientes.append((vecino, visitados | {vecino}, costo + a.peso))
            solucion = Dijkstra().ejecutar(Entrada(red, ParametrosDijkstra("A"))).solucion
            self.assertEqual(dict(solucion.distancias), costos)

    def test_rechaza_peso_negativo(self):
        with self.assertRaises(AlgoritmoNoAplicableError):
            Dijkstra().ejecutar(Entrada(grafo("AB", [("A", "B", -1)]), ParametrosDijkstra("A", "B")))


class FordFulkersonTests(unittest.TestCase):
    def verificar_flujo(self, red, solucion, fuente="S", sumidero="T"):
        balance = dict.fromkeys(red.vertices, 0.0)
        for a in red.aristas:
            flujo = solucion.flujo_por_arco[a.identificador]
            self.assertGreaterEqual(flujo, 0)
            self.assertLessEqual(flujo, a.peso)
            balance[a.origen] -= flujo
            balance[a.destino] += flujo
        for v in red.vertices:
            esperado = -solucion.flujo_maximo if v == fuente else solucion.flujo_maximo if v == sumidero else 0
            self.assertAlmostEqual(balance[v], esperado)
        self.assertAlmostEqual(solucion.flujo_maximo, solucion.capacidad_corte)

    def test_ejemplo_de_18_y_red_sin_camino(self):
        red = grafo("SABT", [("S", "A", 10), ("A", "T", 8), ("A", "B", 2), ("S", "B", 10), ("B", "T", 10)], True)
        solucion = FordFulkerson().ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T"))).solucion
        self.assertEqual(solucion.flujo_maximo, 18)
        self.verificar_flujo(red, solucion)
        red = grafo("SABT", [("S", "A", 0), ("B", "T", 3)], True)
        solucion = FordFulkerson().ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T"))).solucion
        self.assertEqual(solucion.flujo_maximo, 0)
        self.verificar_flujo(red, solucion)

    def test_el_camino_inverso_deshace_una_asignacion_anterior(self):
        red = grafo("SABCDT", [("S", "A", 1), ("S", "B", 1), ("A", "C", 1),
                               ("A", "D", 1), ("B", "C", 1), ("C", "T", 1), ("D", "T", 1)], True)
        resultado = FordFulkerson().ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T")))
        self.assertEqual(resultado.solucion.flujo_maximo, 2)
        self.assertEqual(resultado.solucion.flujo_por_arco[2], 0)
        inverso = [t for p in resultado.pasos for t in p.detalle.camino if t.inverso]
        self.assertEqual([(t.arista, t.origen, t.destino) for t in inverso], [(2, "C", "A")])
        self.assertTrue(any(a.inverso and a.despues < a.antes for p in resultado.pasos for a in p.detalle.actualizaciones))
        self.verificar_flujo(red, resultado.solucion)

    def test_paralelas_antiparalelas_y_capacidades_decimales(self):
        red = grafo("SAT", [("S", "A", .1), ("S", "A", .2), ("A", "S", .7), ("A", "T", .3)], True)
        algoritmo = FordFulkerson()
        resultado = algoritmo.ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T")))
        self.assertEqual(resultado.solucion.flujo_maximo, .3)
        self.assertEqual(dict(resultado.solucion.flujo_por_arco), {0: .1, 1: .2, 2: 0, 3: .3})
        self.verificar_flujo(red, resultado.solucion)
        self.assertEqual(resultado, algoritmo.ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T"))))
        with self.assertRaises(TypeError):
            resultado.solucion.flujo_por_arco[0] = 9

    def test_contraste_con_todos_los_cortes_de_redes_pequenas(self):
        azar = Random(74)
        for _ in range(35):
            conexiones = [(u, v, azar.randint(0, 8)) for u in "SABCT" for v in "SABCT"
                          if u != v and azar.random() < .25]
            conexiones += conexiones[:2]  # Preservar identidad de paralelas.
            red = grafo("SABCT", conexiones, True)
            cortes = []
            for mascara in range(8):
                lado = {"S"} | {v for i, v in enumerate("ABC") if mascara & (1 << i)}
                cortes.append(sum(a.peso for a in red.aristas if a.origen in lado and a.destino not in lado))
            solucion = FordFulkerson().ejecutar(Entrada(red, ParametrosFlujoMaximo("S", "T"))).solucion
            self.assertEqual(solucion.flujo_maximo, min(cortes))
            self.verificar_flujo(red, solucion)


if __name__ == "__main__":
    unittest.main()
