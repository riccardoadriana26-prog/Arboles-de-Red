"""Ejecuciones completas de 200 nodos y límites del formato numérico de resultados."""

import unittest
from dataclasses import FrozenInstanceError

from arboles_de_red import (
    Arista, Entrada, ErrorCalculoNumerico, EstimacionesPERT, Grafo, ParametrosCPM,
    ParametrosPERT, SelectorAlgoritmos,
)


class IntegracionResolucionTests(unittest.TestCase):
    def test_los_seis_algoritmos_con_200_vertices_conservan_la_carga_y_los_pasos(self):
        vertices = tuple(f"V{i}" for i in range(200))
        conexiones = tuple(Arista(i, vertices[i], vertices[i + 1], 1, False) for i in range(199))
        ponderada = Entrada(Grafo(vertices, conexiones), None)
        red_flujo = Entrada(Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], 2, True) for i in range(199))), None)
        aon = Grafo(vertices, tuple(Arista(i, vertices[i], vertices[i + 1], None, True) for i in range(199)))
        cpm = Entrada(aon, ParametrosCPM(dict.fromkeys(vertices, 1)))
        pert = Entrada(aon, ParametrosPERT(dict.fromkeys(vertices, EstimacionesPERT(1, 2, 3))))
        selector = SelectorAlgoritmos()
        casos = (("prim", ponderada, {}), ("kruskal", ponderada, {}),
                 ("dijkstra", ponderada, {"origen": "V0", "destino": "V199"}),
                 ("flujo_maximo", red_flujo, {"fuente": "V0", "sumidero": "V199"}),
                 ("cpm", cpm, {}), ("pert", pert, {}))
        for identificador, carga, opciones in casos:
            with self.subTest(algoritmo=identificador):
                grafo_antes = (carga.grafo.vertices, carga.grafo.aristas)
                seleccion = selector.seleccionar(identificador, carga, opciones)
                self.assertTrue(seleccion.puede_ejecutarse)
                resultado = seleccion.ejecutar()
                copia = seleccion.ejecutar()
                self.assertEqual(resultado, copia)
                self.assertIsNot(resultado, copia)
                self.assertEqual((carga.grafo.vertices, carga.grafo.aristas), grafo_antes)
                self.assertEqual([p.numero for p in resultado.pasos], list(range(1, len(resultado.pasos) + 1)))
                ids = {a.identificador for a in carga.grafo.aristas}
                for paso in resultado.pasos:
                    self.assertTrue(set(paso.vertices_destacados) <= set(vertices))
                    self.assertTrue(set(paso.aristas_destacadas) <= ids)
                with self.assertRaises(FrozenInstanceError):
                    resultado.pasos[0].numero = 0
                if identificador in ("prim", "kruskal"):
                    self.assertEqual(resultado.solucion.peso_total, 199)
                elif identificador == "dijkstra":
                    self.assertEqual(resultado.solucion.costo, 199)
                    self.assertEqual(resultado.solucion.ruta, vertices)
                elif identificador == "flujo_maximo":
                    self.assertEqual(resultado.solucion.flujo_maximo, 2)
                elif identificador == "cpm":
                    self.assertEqual(resultado.solucion.duracion_proyecto, 200)
                    self.assertEqual(tuple(resultado.solucion.rutas_criticas), (vertices,))
                else:
                    self.assertEqual(resultado.solucion.duracion_esperada, 400)
                    ruta, = resultado.solucion.variabilidad_rutas()
                    self.assertAlmostEqual(ruta.varianza, 200 / 9)

    def test_desborde_no_se_presenta_como_solucion_valida_o_inalcanzable(self):
        vertices = ("A", "B", "C")
        red = Entrada(Grafo(vertices, (Arista(0, "A", "B", 1e308, False),
                                      Arista(1, "B", "C", 1e308, False))), None)
        selector = SelectorAlgoritmos()
        for identificador, opciones in (("prim", {}), ("kruskal", {}), ("dijkstra", {"origen": "A", "destino": "C"})):
            with self.subTest(algoritmo=identificador), self.assertRaises(ErrorCalculoNumerico):
                selector.seleccionar(identificador, red, opciones).ejecutar()
        aon = Entrada(Grafo(vertices, (Arista(0, "A", "B", None, True), Arista(1, "B", "C", None, True))),
                      ParametrosCPM(dict.fromkeys(vertices, 1e308)))
        with self.assertRaises(ErrorCalculoNumerico):
            selector.seleccionar("cpm", aon).ejecutar()


if __name__ == "__main__":
    unittest.main()
