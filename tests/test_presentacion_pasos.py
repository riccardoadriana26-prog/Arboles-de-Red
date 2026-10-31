"""Resúmenes legibles a partir de ejecuciones y entradas reales, sin interfaz."""

import unittest

from arboles_de_red.algoritmo import Entrada
from arboles_de_red.csv import ProcesadorCPMCSV, ProcesadorPERTCSV
from arboles_de_red.grafo import Arista, Grafo
from arboles_de_red.pert import DetalleEstimacionPERT
from arboles_de_red.presentacion_pasos import resumir_paso
from arboles_de_red.reconstruccion import ReconstruccionEjecucion
from arboles_de_red.seleccion import SelectorAlgoritmos


def conexiones(filas, dirigida=False):
    vertices = tuple(dict.fromkeys(
        vertice for origen, destino, _ in filas for vertice in (origen, destino)
    ))
    return Entrada(Grafo(vertices, tuple(
        Arista(i, u, v, peso, dirigida) for i, (u, v, peso) in enumerate(filas)
    )), None)


class PresentacionPasosTests(unittest.TestCase):
    def ejecutar(self, algoritmo, entrada, opciones=None):
        seleccion = SelectorAlgoritmos().seleccionar(algoritmo, entrada, opciones)
        self.assertTrue(seleccion.puede_ejecutarse, seleccion.motivo)
        resultado = seleccion.ejecutar()
        reconstruccion = ReconstruccionEjecucion(seleccion.entrada, resultado, algoritmo)
        return seleccion.entrada, resultado, reconstruccion

    def mst(self):
        return conexiones([
            ("A", "B", 1), ("B", "C", 2), ("A", "C", 3), ("C", "D", 4),
            ("B", "D", 5), ("D", "E", 6), ("C", "E", 7), ("E", "F", 8),
            ("D", "F", 9), ("A", "F", 12),
        ])

    def test_prim_resuelve_frontera_y_elegida_del_caso_manual(self):
        entrada, _, rec = self.ejecutar("prim", self.mst())
        resumen = dict(resumir_paso(entrada, rec.estado_en(2)))
        self.assertEqual(resumen["Arista elegida"], "#0 A — B · peso 1")
        self.assertEqual(resumen["Aristas evaluadas"],
                         "#0 A — B · peso 1; #2 A — C · peso 3; #9 A — F · peso 12")
        self.assertEqual(resumen["Peso acumulado"], "1")
        self.assertNotIn("rechazada", str(resumen).lower())
        self.assertEqual(dict(resumir_paso(entrada, rec.estado_en(0))),
                         {"Estado": "Inicial, sin eventos aplicados"})

    def test_kruskal_distingue_aceptacion_y_rechazo_por_ciclo(self):
        entrada, _, rec = self.ejecutar("kruskal", self.mst())
        aceptada = dict(resumir_paso(entrada, rec.estado_en(2)))
        self.assertEqual(aceptada["Decisión"], "Aceptada e incorporada al árbol")
        rechazada = dict(resumir_paso(entrada, rec.estado_en(4)))
        self.assertEqual(rechazada["Arista evaluada"], "#2 A — C · peso 3")
        self.assertEqual(rechazada["Decisión"], "Rechazada: formaría un ciclo")
        self.assertEqual(rechazada["Peso acumulado"], "3")

    def test_paralelas_conservan_id_y_pesos_cero_y_negativo(self):
        entrada, _, rec = self.ejecutar("prim", conexiones([
            ("A", "B", 0), ("A", "B", -2), ("B", "C", 1),
        ]))
        resumen = dict(resumir_paso(entrada, rec.estado_en(2)))
        self.assertEqual(resumen["Aristas evaluadas"], "#0 A — B · peso 0; #1 A — B · peso -2")
        self.assertEqual(resumen["Arista elegida"], "#1 A — B · peso -2")

    def test_dijkstra_muestra_mejora_predecesores_conservacion_y_fijacion(self):
        entrada, resultado, rec = self.ejecutar("dijkstra", conexiones([
            ("A", "B", 8), ("A", "C", 2), ("A", "D", 10),
            ("C", "B", 2), ("C", "D", 9), ("B", "D", 1),
        ], True), {"origen": "A"})
        mejora = next(p for p in resultado.pasos if p.detalle.accion == "relajar"
                      and p.detalle.predecesor_anterior is not None)
        resumen = dict(resumir_paso(entrada, rec.estado_en(mejora.numero)))
        self.assertEqual(resumen["Acción"], "Mejora de distancia")
        self.assertEqual(resumen["Vértice"], "B")
        self.assertEqual(resumen["Distancia anterior"], "8")
        self.assertEqual(resumen["Distancia nueva"], "4")
        self.assertEqual(resumen["Predecesor anterior"], "A mediante #0 A → B · peso 8")
        self.assertEqual(resumen["Predecesor nuevo"], "C mediante #3 C → B · peso 2")
        for accion, nombre in (("conservar", "Conservación de distancia"),
                               ("fijar", "Fijación del vértice permanente")):
            paso = next(p for p in resultado.pasos if p.detalle.accion == accion)
            campos = dict(resumir_paso(entrada, rec.estado_en(paso.numero)))
            self.assertEqual(campos["Acción"], nombre)
            if accion == "conservar":
                self.assertEqual(campos["Predecesor anterior"], campos["Predecesor nuevo"])
                self.assertEqual(campos["Distancia anterior"], campos["Distancia nueva"])

    def test_flujo_identifica_residual_inverso_y_paralelas_originales(self):
        carga = conexiones([
            ("S", "A", 1), ("S", "B", 1), ("A", "C", 1), ("A", "D", 0.5),
            ("B", "C", 1), ("C", "T", 1), ("D", "T", 1), ("A", "D", 0.5),
        ], True)
        entrada, _, rec = self.ejecutar("flujo_maximo", carga, {"fuente": "S", "sumidero": "T"})
        resumen = dict(resumir_paso(entrada, rec.estado_en(3)))
        self.assertEqual(resumen["Camino de aumento"], "S → B → C → A → D → T")
        self.assertIn("C → A: residual inverso de #2 A → C · peso 1", resumen["Tramos del camino"])
        self.assertIn("#3 A → D · peso 0.5", resumen["Aristas originales utilizadas"])
        siguiente = dict(resumir_paso(entrada, rec.estado_en(4)))
        self.assertIn("#7 A → D · peso 0.5", siguiente["Aristas originales utilizadas"])
        self.assertEqual(resumen["Cuello de botella"], "0.5")
        self.assertEqual(resumen["Incremento de flujo"], "0.5")
        self.assertEqual(resumen["Flujo acumulado"], "1.5")
        self.assertEqual(len(entrada.grafo.aristas), 8)

    def test_cpm_omite_valores_aun_no_calculados_y_muestra_cero(self):
        carga = ProcesadorCPMCSV().preparar_entrada("actividad,duracion,predecesoras\nA,2,\nB,3,A\n")
        entrada, resultado, rec = self.ejecutar("cpm", carga)
        adelante = dict(resumir_paso(entrada, rec.estado_en(1)))
        self.assertEqual(adelante, {"Fase": "Hacia adelante", "Actividad": "A", "IC": "0", "TC": "2"})
        atras = dict(resumir_paso(entrada, rec.estado_en(3)))
        self.assertEqual(atras["Fase"], "Hacia atrás")
        self.assertEqual(atras["Holgura"], "0")
        self.assertEqual(set(atras), {"Fase", "Actividad", "IC", "TC", "IL", "TL", "Holgura"})
        final = dict(resumir_paso(entrada, rec.estado_en(len(resultado.pasos))))
        self.assertEqual(final["Duración del proyecto"], "5")

    def test_pert_muestra_estimaciones_originales_y_luego_planificacion(self):
        carga = ProcesadorPERTCSV().preparar_entrada(
            "actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,2,9,\nB,2,3,4,A\n")
        entrada, resultado, rec = self.ejecutar("pert", carga)
        estimacion = dict(resumir_paso(entrada, rec.estado_en(1)))
        self.assertEqual(estimacion["Optimista"], "1")
        self.assertEqual(estimacion["Más probable"], "2")
        self.assertEqual(estimacion["Pesimista"], "9")
        self.assertEqual(estimacion["Tiempo esperado"], "3")
        self.assertEqual(estimacion["Varianza"], "1.78")
        self.assertEqual(resultado.pasos[0].detalle.varianza, 1.7777777777777777)
        numero = next(p.numero for p in resultado.pasos if not isinstance(p.detalle, DetalleEstimacionPERT))
        plan = dict(resumir_paso(entrada, rec.estado_en(numero)))
        self.assertEqual(plan, {"Fase": "Hacia adelante", "Actividad": "A", "IC": "0", "TC": "3"})


if __name__ == "__main__":
    unittest.main()
