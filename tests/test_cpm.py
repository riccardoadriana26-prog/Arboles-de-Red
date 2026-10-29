"""Dos pasadas AON, actividades independientes y todas las rutas críticas."""

import unittest
from itertools import islice
from random import Random

from arboles_de_red import Arista, Entrada, Grafo, ParametrosCPM
from arboles_de_red.algoritmo import AlgoritmoNoAplicableError
from arboles_de_red.cpm import CPM


def entrada_cpm(duraciones, precedencias):
    red = Grafo(tuple(duraciones), tuple(Arista(i, u, v, None, True)
                                        for i, (u, v) in enumerate(precedencias)))
    return Entrada(red, ParametrosCPM(duraciones))


class CPMTests(unittest.TestCase):
    def test_ejemplo_catedra_tiempos_y_holguras(self):
        entrada = entrada_cpm({"A": 5, "B": 7, "C": 4, "D": 6, "E": 3},
                              [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")])
        resultado = CPM().ejecutar(entrada)
        solucion = resultado.solucion
        self.assertEqual(solucion.duracion_proyecto, 21)
        self.assertEqual(tuple(solucion.rutas_criticas), (("A", "B", "D", "E"),))
        esperado = {"A": (0, 5, 0, 5, 0), "B": (5, 12, 5, 12, 0),
                    "C": (5, 9, 8, 12, 3), "D": (12, 18, 12, 18, 0), "E": (18, 21, 18, 21, 0)}
        for v, valores in esperado.items():
            t = solucion.actividades[v]
            self.assertEqual((t.ic, t.tc, t.il, t.tl, t.holgura), valores)
        self.assertEqual([p.detalle.fase for p in resultado.pasos], ["adelante"] * 5 + ["atras"] * 5 + ["finalizar"])
        self.assertEqual([p.detalle.actividad for p in resultado.pasos[:5]], list(solucion.orden_topologico))
        with self.assertRaises(TypeError):
            solucion.actividades["A"] = solucion.actividades["B"]

    def test_actividad_unica_independientes_y_componentes_desconectados(self):
        unico = CPM().ejecutar(entrada_cpm({"A": 0}, [])).solucion
        self.assertEqual((unico.duracion_proyecto, tuple(unico.rutas_criticas)), (0, (("A",),)))
        independientes = CPM().ejecutar(entrada_cpm({"A": 5, "B": 3, "C": 5}, [])).solucion
        self.assertEqual(tuple(independientes.rutas_criticas), (("A",), ("C",)))
        self.assertEqual(independientes.actividades["B"].holgura, 2)
        desconectados = CPM().ejecutar(entrada_cpm({"A": 2, "B": 3, "C": 1, "D": 1}, [("A", "B"), ("C", "D")])).solucion
        self.assertEqual(desconectados.actividades["D"].tl, 5)
        self.assertEqual(tuple(desconectados.rutas_criticas), (("A", "B"),))

    def test_empates_decimales_paralelas_y_orden_de_carga_no_topologico(self):
        entrada = entrada_cpm({"D": 0, "B": .2, "A": .1, "C": .3},
                              [("A", "B"), ("A", "B"), ("B", "D"), ("C", "D")])
        solucion = CPM().ejecutar(entrada).solucion
        self.assertEqual(solucion.duracion_proyecto, .3)
        self.assertEqual(set(solucion.rutas_criticas), {("A", "B", "D"), ("C", "D")})
        self.assertEqual(solucion.rutas_criticas.cantidad, 2)
        self.assertTrue(all(t.holgura == 0 for t in solucion.actividades.values()))

    def test_200_actividades_con_exponencial_de_rutas_sin_materializarlas(self):
        duraciones = {f"V{i}": 1 for i in range(200)}
        enlaces = [(f"V{i}", f"V{j}") for i in range(198) for j in range((i // 2 + 1) * 2, (i // 2 + 1) * 2 + 2)]
        solucion = CPM().ejecutar(entrada_cpm(duraciones, enlaces)).solucion
        self.assertEqual(solucion.duracion_proyecto, 100)
        self.assertEqual(solucion.rutas_criticas.cantidad, 2 ** 100)
        primeras = tuple(islice(solucion.rutas_criticas, 2))
        self.assertEqual(len(primeras), 2)
        self.assertEqual(len(primeras[0]), 100)

    def test_contraste_con_todos_los_caminos_de_dags_pequenos(self):
        azar = Random(501)
        for _ in range(30):
            duraciones = {v: azar.randint(0, 6) for v in "ABCDEF"}
            enlaces = [(u, v) for i, u in enumerate(duraciones) for v in tuple(duraciones)[i + 1:] if azar.random() < .3]
            inicios = [v for v in duraciones if all(v != destino for _, destino in enlaces)]
            caminos = []
            pila = [((v,), duraciones[v]) for v in inicios]
            while pila:
                ruta, costo = pila.pop()
                sucesoras = [destino for origen, destino in enlaces if origen == ruta[-1]]
                if not sucesoras:
                    caminos.append((ruta, costo))
                for v in sucesoras:
                    pila.append((ruta + (v,), costo + duraciones[v]))
            mayor = max(costo for _, costo in caminos)
            solucion = CPM().ejecutar(entrada_cpm(duraciones, enlaces)).solucion
            self.assertEqual(solucion.duracion_proyecto, mayor)
            self.assertEqual(set(solucion.rutas_criticas), {ruta for ruta, costo in caminos if costo == mayor})
            self.assertEqual(solucion.rutas_criticas.cantidad, len(tuple(solucion.rutas_criticas)))

    def test_rechaza_ciclo_sin_devolver_resultado_parcial(self):
        with self.assertRaises(AlgoritmoNoAplicableError):
            CPM().ejecutar(entrada_cpm({"A": 1, "B": 1}, [("A", "B"), ("B", "A")]))


if __name__ == "__main__":
    unittest.main()
