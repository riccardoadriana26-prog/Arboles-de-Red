"""Regresiones de redondeo, rango numérico y cálculos intermedios extremos."""

import unittest
from decimal import Decimal
from math import inf, nan

from arboles_de_red import (
    Arista, CPM, Dijkstra, Entrada, ErrorCalculoNumerico, ErrorValidacionCSV,
    EstimacionesPERT, FordFulkerson, Grafo, PERT, ParametrosCPM,
    ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT,
    ProcesadorCPMCSV, ProcesadorConexionesCSV, ProcesadorPERTCSV,
)
from arboles_de_red._numeros import finito, sumar


class PrecisionTests(unittest.TestCase):
    def test_dijkstra_no_elige_una_ruta_mas_cara_por_redondear_la_suma(self):
        grafo = Grafo(tuple("ABC"), (
            Arista(0, "A", "B", .1, True), Arista(1, "B", "C", .2, True),
            Arista(2, "A", "C", .30000000000000004, True),
        ))
        solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra("A", "C"))).solucion
        self.assertEqual(solucion.ruta, ("A", "B", "C"))
        self.assertEqual(solucion.costo, .3)

    def test_dijkstra_conserva_la_primera_ruta_en_un_empate_decimal(self):
        grafo = Grafo(tuple("ABCD"), (
            Arista(0, "A", "B", .1, True), Arista(1, "B", "D", .2, True),
            Arista(2, "A", "C", .3, True), Arista(3, "C", "D", 0, True),
        ))
        solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra("A", "D"))).solucion
        self.assertEqual(solucion.ruta, ("A", "B", "D"))
        self.assertEqual(solucion.costo, .3)

    def test_dijkstra_no_falla_por_un_candidato_descartado_fuera_de_rango(self):
        grafo = Grafo(tuple("ABC"), (
            Arista(0, "A", "B", 1e308, True), Arista(1, "B", "C", 1e308, True),
            Arista(2, "A", "C", 1.5e308, True),
        ))
        solucion = Dijkstra().ejecutar(Entrada(grafo, ParametrosDijkstra("A", "C"))).solucion
        self.assertEqual(solucion.ruta, ("A", "C"))
        self.assertEqual(solucion.costo, 1.5e308)

    def test_cpm_no_convierte_una_duracion_positiva_en_cero_por_subdesborde(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosCPM({"A": Decimal("1e-400")}))
        with self.assertRaises(ErrorCalculoNumerico):
            CPM().ejecutar(entrada)

    def test_pert_no_convierte_una_varianza_positiva_en_cero_por_subdesborde(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosPERT({"A": EstimacionesPERT(0, 3e-200, 6e-200)}))
        with self.assertRaises(ErrorCalculoNumerico):
            PERT().ejecutar(entrada)

    def test_carga_y_modelo_rechazan_no_ceros_que_se_normalizarian_a_cero(self):
        for peso in (Decimal("1e-400"), Decimal("-1e-400")):
            with self.subTest(peso=peso), self.assertRaises(ValueError):
                Arista(0, "A", "B", peso, True)
        casos = (
            (ProcesadorConexionesCSV(), "origen,destino,peso\nA,B,1e-400\n", "peso"),
            (ProcesadorCPMCSV(), "actividad,duracion,predecesoras\nA,1e-400,\n", "duracion"),
            (ProcesadorPERTCSV(), "actividad,optimista,mas_probable,pesimista,predecesoras\nA,0,1e-400,1,\n", "mas_probable"),
        )
        for procesador, texto, columna in casos:
            with self.subTest(procesador=type(procesador).__name__):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    procesador.preparar_entrada(texto)
                self.assertIn((2, columna), {(e.linea, e.columna) for e in captura.exception.errores})

    def test_pert_estimaciones_grandes_iguales_sin_desborde_intermedio(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosPERT({"A": EstimacionesPERT(1e308, 1e308, 1e308)}))
        solucion = PERT().ejecutar(entrada).solucion
        self.assertEqual(solucion.duracion_esperada, 1e308)
        self.assertEqual(next(solucion.variabilidad_rutas()).varianza, 0)

    def test_pert_informa_desborde_de_varianza(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosPERT({"A": EstimacionesPERT(0, 1e200, 2e200)}))
        with self.assertRaises(ErrorCalculoNumerico):
            PERT().ejecutar(entrada)

    def test_pert_informa_desborde_de_la_suma_de_varianzas_al_recorrer_la_ruta(self):
        grafo = Grafo(("A", "B"), (Arista(0, "A", "B", None, True),))
        entrada = Entrada(grafo, ParametrosPERT(dict.fromkeys(grafo.vertices, EstimacionesPERT(0, 3e154, 6e154))))
        solucion = PERT().ejecutar(entrada).solucion
        self.assertTrue(all(v == 1e308 for v in solucion.varianzas.values()))
        with self.assertRaises(ErrorCalculoNumerico):
            tuple(solucion.variabilidad_rutas())

    def test_flujo_informa_desborde_del_total(self):
        grafo = Grafo(("S", "T"), (Arista(0, "S", "T", 1e308, True), Arista(1, "S", "T", 1e308, True)))
        with self.assertRaises(ErrorCalculoNumerico):
            FordFulkerson().ejecutar(Entrada(grafo, ParametrosFlujoMaximo("S", "T")))

    def test_capacidad_subnormal_representable_conserva_su_flujo(self):
        grafo = Grafo(("S", "T"), (Arista(0, "S", "T", 5e-324, True),))
        solucion = FordFulkerson().ejecutar(Entrada(grafo, ParametrosFlujoMaximo("S", "T"))).solucion
        self.assertEqual(solucion.flujo_maximo, 5e-324)
        self.assertEqual(solucion.flujo_por_arco[0], 5e-324)

    def test_errores_de_calculo_no_devuelven_nan_ni_inf(self):
        for valor in (inf, -inf, nan):
            with self.subTest(valor=valor), self.assertRaises(ErrorCalculoNumerico):
                finito(valor)
        with self.assertRaises(ErrorCalculoNumerico):
            sumar((1e308, 1e308))


if __name__ == "__main__":
    unittest.main()
