"""Estimaciones originales, planificación esperada y variabilidad de cada ruta crítica."""

import unittest
from itertools import islice
from math import sqrt

from arboles_de_red import Arista, Entrada, EstimacionesPERT, Grafo, ParametrosPERT
from arboles_de_red.algoritmo import AlgoritmoNoAplicableError
from arboles_de_red.pert import PERT


def entrada_pert(estimaciones, precedencias):
    return Entrada(Grafo(tuple(estimaciones), tuple(Arista(i, u, v, None, True)
                                                   for i, (u, v) in enumerate(precedencias))),
                   ParametrosPERT({v: EstimacionesPERT(*ts) for v, ts in estimaciones.items()}))


class PERTTests(unittest.TestCase):
    def test_ejemplo_catedra_sin_redondeos_intermedios(self):
        entrada = entrada_pert({"A": (3, 5, 7), "B": (5, 7, 10), "C": (2, 4, 6),
                               "D": (4, 6, 9), "E": (2, 3, 4)},
                              [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")])
        resultado = PERT().ejecutar(entrada)
        solucion = resultado.solucion
        self.assertAlmostEqual(solucion.duracion_esperada, 64 / 3)
        self.assertEqual(tuple(solucion.rutas_criticas), (("A", "B", "D", "E"),))
        variabilidad, = solucion.variabilidad_rutas()
        self.assertAlmostEqual(variabilidad.varianza, 35 / 18)
        self.assertAlmostEqual(variabilidad.desviacion_estandar, sqrt(35 / 18))
        self.assertEqual(solucion.estimaciones, entrada.parametros.estimaciones)
        self.assertEqual(solucion.tiempos_esperados["C"], 4)
        self.assertAlmostEqual(solucion.varianzas["C"], 4 / 9)
        self.assertAlmostEqual(solucion.actividades["C"].holgura, 19 / 6)
        self.assertEqual([p.numero for p in resultado.pasos], list(range(1, len(resultado.pasos) + 1)))
        self.assertEqual(len(resultado.pasos), 16)

    def test_rutas_empatadas_con_varianzas_distintas_sin_elegir_una(self):
        entrada = entrada_pert({"A": (0, 3, 6), "B": (3, 3, 3), "C": (0, 0, 0)}, [("A", "C"), ("B", "C")])
        solucion = PERT().ejecutar(entrada).solucion
        rutas = {r.actividades: r for r in solucion.variabilidad_rutas()}
        self.assertEqual(solucion.duracion_esperada, 3)
        self.assertEqual(solucion.rutas_criticas.cantidad, 2)
        self.assertEqual(rutas[("A", "C")].varianza, 1)
        self.assertEqual(rutas[("A", "C")].desviacion_estandar, 1)
        self.assertEqual(rutas[("B", "C")].varianza, 0)
        self.assertEqual(rutas[("B", "C")].desviacion_estandar, 0)
        with self.assertRaises(TypeError):
            solucion.estimaciones["A"] = EstimacionesPERT(1, 1, 1)
        with self.assertRaises(TypeError):
            solucion.varianzas["A"] = 99

    def test_actividad_unica_sin_incertidumbre(self):
        entrada = entrada_pert({"A": (2, 2, 2)}, [])
        algoritmo = PERT()
        resultado = algoritmo.ejecutar(entrada)
        ruta, = resultado.solucion.variabilidad_rutas()
        self.assertEqual((ruta.actividades, ruta.duracion_esperada, ruta.varianza), (("A",), 2, 0))
        self.assertEqual(resultado, algoritmo.ejecutar(entrada))

    def test_variabilidad_de_200_actividades_se_enumera_a_demanda(self):
        datos = {f"V{i}": (0, 1, 2) for i in range(200)}
        enlaces = [(f"V{i}", f"V{j}") for i in range(198) for j in range((i // 2 + 1) * 2, (i // 2 + 1) * 2 + 2)]
        solucion = PERT().ejecutar(entrada_pert(datos, enlaces)).solucion
        self.assertEqual(solucion.rutas_criticas.cantidad, 2 ** 100)
        for ruta in islice(solucion.variabilidad_rutas(), 2):
            self.assertEqual(ruta.duracion_esperada, 100)
            self.assertAlmostEqual(ruta.varianza, 100 / 9)

    def test_rechaza_estimaciones_desordenadas(self):
        with self.assertRaises(AlgoritmoNoAplicableError):
            PERT().ejecutar(entrada_pert({"A": (3, 1, 4)}, []))


if __name__ == "__main__":
    unittest.main()
