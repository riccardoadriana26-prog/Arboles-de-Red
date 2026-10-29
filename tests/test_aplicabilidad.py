"""Condiciones por algoritmo, consultadas antes de la resolución."""

import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

from arboles_de_red import (
    Algoritmo,
    AlgoritmoNoAplicableError,
    Arista,
    CondicionesAplicacion,
    CondicionesArbolExpansion,
    CondicionesCPM,
    CondicionesDijkstra,
    CondicionesFlujoMaximo,
    CondicionesPERT,
    Entrada,
    EstimacionesPERT,
    Grafo,
    LectorTexto,
    ParametrosDijkstra,
    ParametrosCPM,
    ParametrosFlujoMaximo,
    ParametrosPERT,
    ProcesadorCPMCSV,
    ProcesadorPERTCSV,
    Resultado,
)


class ResolucionDePrueba[ParametrosT](Algoritmo[ParametrosT, str, None]):
    """Resolución mínima para comprobar que el contrato aplica las condiciones."""

    def __init__(self, condiciones: CondicionesAplicacion[ParametrosT] | None = None):
        super().__init__(condiciones)
        self.resoluciones = 0

    def _resolver(self, entrada: Entrada[ParametrosT]) -> Resultado[str, None]:
        self.resoluciones += 1
        return Resultado("resuelta", ())


class ArbolExpansionTests(unittest.TestCase):
    def test_rechaza_grafos_vacios_dirigidos_sin_pesos_o_desconectados(self):
        casos = (
            (Grafo((), ()), "vacío"),
            (Grafo(("A", "B"), (Arista(0, "A", "B", 1, True),)), "dirigida"),
            (Grafo(("A", "B"), (Arista(0, "A", "B", None, False),)), "peso"),
            (
                Grafo(("A", "B", "Aislado"), (Arista(0, "A", "B", 1, False),)),
                "conexo",
            ),
        )
        condiciones = CondicionesArbolExpansion()
        for grafo, fragmento in casos:
            with self.subTest(grafo=grafo):
                entrada = Entrada(grafo, None)
                self.assertIs(condiciones.es_aplicable(entrada), False)
                self.assertIn(fragmento, condiciones.motivo_inaplicabilidad(entrada))

    def test_prim_y_kruskal_admiten_pesos_negativos_y_aristas_paralelas(self):
        grafo = Grafo(
            ("A", "B", "C"),
            (
                Arista(0, "A", "B", -2, False),
                Arista(1, "A", "B", -2, False),
                Arista(2, "B", "C", 0, False),
            ),
        )
        condiciones = CondicionesArbolExpansion()

        self.assertIs(condiciones.es_aplicable(Entrada(grafo, None)), True)
        self.assertIsNone(condiciones.motivo_inaplicabilidad(Entrada(grafo, None)))
        self.assertEqual(len(grafo.aristas), 3)


class DijkstraTests(unittest.TestCase):
    def test_informa_inalcanzables_respetando_la_direccion_de_cada_arista(self):
        grafo = Grafo(
            ("A", "B", "C", "D", "Aislado"),
            (
                Arista(0, "A", "B", 1, False),
                Arista(1, "A", "B", 1, False),
                Arista(2, "B", "C", 0, True),
                Arista(3, "D", "C", 1, True),
            ),
        )
        condiciones = CondicionesDijkstra()

        self.assertEqual(
            condiciones.vertices_inalcanzables(Entrada(grafo, ParametrosDijkstra("B"))),
            ("D", "Aislado"),
        )
        self.assertEqual(
            condiciones.vertices_inalcanzables(Entrada(grafo, ParametrosDijkstra("C"))),
            ("A", "B", "D", "Aislado"),
        )

    def test_verifica_origen_destino_y_pesos_sin_exigir_conectividad(self):
        grafo = Grafo(
            ("A", "B", "C", "Aislado"),
            (Arista(0, "A", "B", 0, False), Arista(1, "B", "C", 3, True)),
        )
        casos = (
            (Entrada(grafo, ParametrosDijkstra("A")), None),
            (Entrada(grafo, ParametrosDijkstra("A", "C")), None),
            (Entrada(grafo, ParametrosDijkstra("A", "Aislado")), None),
            (Entrada(grafo, ParametrosDijkstra("Ausente")), "origen"),
            (Entrada(grafo, ParametrosDijkstra("A", "Ausente")), "destino"),
            (Entrada(grafo, None), "parámetros"),
            (Entrada(Grafo((), ()), ParametrosDijkstra("A")), "vacío"),
            (
                Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", None, True),)), ParametrosDijkstra("A")),
                "peso",
            ),
            (
                Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", -1, True),)), ParametrosDijkstra("A")),
                "negativo",
            ),
        )
        condiciones = CondicionesDijkstra()
        for entrada, fragmento in casos:
            with self.subTest(entrada=entrada):
                self.assertIs(condiciones.es_aplicable(entrada), fragmento is None)
                motivo = condiciones.motivo_inaplicabilidad(entrada)
                if fragmento is None:
                    self.assertIsNone(motivo)
                else:
                    self.assertIn(fragmento, motivo)


class FlujoMaximoTests(unittest.TestCase):
    def test_exige_capacidades_y_terminales_validos_en_una_red_dirigida(self):
        dirigida = Grafo(
            ("S", "T", "Aislado"),
            (Arista(0, "S", "T", 0, True), Arista(1, "S", "T", 5, True)),
        )
        casos = (
            (Entrada(dirigida, ParametrosFlujoMaximo("S", "T")), None),
            (Entrada(dirigida, ParametrosFlujoMaximo("S", "Aislado")), None),
            (Entrada(dirigida, ParametrosFlujoMaximo("X", "T")), "fuente"),
            (Entrada(dirigida, ParametrosFlujoMaximo("S", "X")), "sumidero"),
            (Entrada(dirigida, ParametrosFlujoMaximo("S", "S")), "distintos"),
            (Entrada(dirigida, None), "parámetros"),
            (Entrada(Grafo((), ()), ParametrosFlujoMaximo("S", "T")), "vacío"),
            (
                Entrada(Grafo(("S", "T"), (Arista(0, "S", "T", 1, False),)), ParametrosFlujoMaximo("S", "T")),
                "dirigida",
            ),
            (
                Entrada(Grafo(("S", "T"), (Arista(0, "S", "T", None, True),)), ParametrosFlujoMaximo("S", "T")),
                "capacidad",
            ),
            (
                Entrada(Grafo(("S", "T"), (Arista(0, "S", "T", -1, True),)), ParametrosFlujoMaximo("S", "T")),
                "negativo",
            ),
        )
        condiciones = CondicionesFlujoMaximo()
        for entrada, fragmento in casos:
            with self.subTest(entrada=entrada):
                self.assertIs(condiciones.es_aplicable(entrada), fragmento is None)
                motivo = condiciones.motivo_inaplicabilidad(entrada)
                if fragmento is None:
                    self.assertIsNone(motivo)
                else:
                    self.assertIn(fragmento, motivo)
        self.assertEqual(len(dirigida.aristas), 2)


class CPMTests(unittest.TestCase):
    def test_rechaza_datos_ausentes_duraciones_invalidas_y_redes_no_aon(self):
        aislada = Grafo(("A",), ())
        ciclo = Grafo(
            ("A", "B"),
            (Arista(0, "A", "B", None, True), Arista(1, "B", "A", None, True)),
        )
        casos = (
            (Entrada(Grafo((), ()), ParametrosCPM({})), "vacío"),
            (Entrada(aislada, None), "parámetros"),
            (Entrada(aislada, ParametrosCPM({})), "A"),
            (Entrada(aislada, ParametrosCPM({"A": 1, "Extra": 2})), "Extra"),
            (Entrada(aislada, ParametrosCPM({0: 1})), "actividad"),
            (Entrada(ciclo, ParametrosCPM({"A": 1, "B": 2})), "ciclos"),
            (
                Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", None, False),)), ParametrosCPM({"A": 1, "B": 2})),
                "dirigida",
            ),
        )
        condiciones = CondicionesCPM()
        for entrada, fragmento in casos:
            with self.subTest(entrada=entrada):
                self.assertFalse(condiciones.es_aplicable(entrada))
                self.assertIn(fragmento, condiciones.motivo_inaplicabilidad(entrada))
        for duracion in (None, "2", True, -1, float("nan"), float("inf"), float("-inf")):
            with self.subTest(duracion=duracion):
                entrada = Entrada(aislada, ParametrosCPM({"A": duracion}))
                self.assertFalse(condiciones.es_aplicable(entrada))
                self.assertIn("duración", condiciones.motivo_inaplicabilidad(entrada))

    def test_actividades_independientes_y_precedencias_paralelas_no_exigen_pesos(self):
        grafo = Grafo(
            ("A", "B", "C", "Independiente"),
            (
                Arista(0, "A", "C", None, True),
                Arista(1, "A", "C", None, True),
                Arista(2, "B", "C", None, True),
            ),
        )
        entrada = Entrada(grafo, ParametrosCPM({"A": 0, "B": 2, "C": 3, "Independiente": 1}))
        condiciones = CondicionesCPM()

        self.assertIs(condiciones.es_aplicable(entrada), True)
        self.assertIsNone(condiciones.motivo_inaplicabilidad(entrada))
        self.assertTrue(condiciones.es_aplicable(Entrada(Grafo(("A",), ()), ParametrosCPM({"A": 0}))))
        self.assertEqual(len(grafo.aristas), 3)


class PERTTests(unittest.TestCase):
    def test_verifica_estimaciones_por_actividad_y_topologia_aon(self):
        aislada = Grafo(("A",), ())
        valida = EstimacionesPERT(0, 0, 0)
        casos = (
            (Entrada(aislada, ParametrosPERT({"A": valida})), None),
            (Entrada(Grafo((), ()), ParametrosPERT({})), "vacío"),
            (Entrada(aislada, None), "parámetros"),
            (Entrada(aislada, ParametrosCPM({"A": 1})), "parámetros"),
            (Entrada(aislada, ParametrosPERT({})), "actividad"),
            (Entrada(aislada, ParametrosPERT({0: valida})), "actividad"),
            (Entrada(aislada, ParametrosPERT({"A": valida, "Extra": valida})), "Extra"),
            (Entrada(aislada, ParametrosPERT({"A": (1, 2, 3)})), "tripleta"),
            (
                Entrada(
                    Grafo(("A", "B"), (Arista(0, "A", "B", None, False),)),
                    ParametrosPERT({"A": valida, "B": valida}),
                ),
                "dirigida",
            ),
            (
                Entrada(
                    Grafo(("A", "B"), (Arista(0, "A", "B", None, True), Arista(1, "B", "A", None, True))),
                    ParametrosPERT({"A": valida, "B": valida}),
                ),
                "ciclos",
            ),
        )
        condiciones = CondicionesPERT()
        for entrada, fragmento in casos:
            with self.subTest(entrada=entrada):
                self.assertIs(condiciones.es_aplicable(entrada), fragmento is None)
                motivo = condiciones.motivo_inaplicabilidad(entrada)
                if fragmento is None:
                    self.assertIsNone(motivo)
                else:
                    self.assertIn(fragmento, motivo)
        invalidas = (
            EstimacionesPERT(-1, 2, 3), EstimacionesPERT(1, 0, 3),
            EstimacionesPERT(1, 3, 2), EstimacionesPERT(1, 2, float("nan")),
            EstimacionesPERT(1, float("inf"), 3), EstimacionesPERT(1, 2, None),
            EstimacionesPERT(True, 2, 3), EstimacionesPERT("1", 2, 3),
        )
        for estimaciones in invalidas:
            with self.subTest(estimaciones=estimaciones):
                entrada = Entrada(aislada, ParametrosPERT({"A": estimaciones}))
                self.assertFalse(condiciones.es_aplicable(entrada))
                self.assertIn("A", condiciones.motivo_inaplicabilidad(entrada))


class IntegracionAplicabilidadTests(unittest.TestCase):
    def test_sin_condiciones_definidas_no_se_ejecuta_la_resolucion(self):
        algoritmo = ResolucionDePrueba()
        entrada = Entrada(Grafo(("A",), ()), None)

        self.assertFalse(algoritmo.es_aplicable(entrada))
        with self.assertRaisesRegex(AlgoritmoNoAplicableError, "condiciones"):
            algoritmo.ejecutar(entrada)
        self.assertEqual(algoritmo.resoluciones, 0)

    def test_los_ejemplos_cpm_y_pert_se_verifican_desde_su_carga_csv(self):
        carpeta = Path(__file__).resolve().parents[1] / "ejemplos"
        cpm = ProcesadorCPMCSV().preparar_entrada(LectorTexto().leer(carpeta / "cpm.csv"))
        pert = ProcesadorPERTCSV().preparar_entrada(LectorTexto().leer(carpeta / "pert.csv"))

        self.assertTrue(CondicionesCPM().es_aplicable(cpm))
        self.assertTrue(CondicionesPERT().es_aplicable(pert))
        self.assertEqual(cpm.parametros.duraciones["C"], 4.5)
        self.assertEqual(pert.parametros.estimaciones["C"], EstimacionesPERT(2, 4, 8))
        self.assertEqual(cpm.grafo, pert.grafo)

    def test_el_signo_y_orden_de_los_tiempos_no_se_pierden_por_redondeo(self):
        grafo = Grafo(("A",), ())
        for valor in (Decimal("-1e-400"), Decimal("sNaN"), 10**400):
            with self.subTest(duracion=valor):
                self.assertFalse(CondicionesCPM().es_aplicable(Entrada(grafo, ParametrosCPM({"A": valor}))))
        entrada = Entrada(
            grafo,
            ParametrosPERT({"A": EstimacionesPERT(Decimal("1e-400"), 0, 1)}),
        )
        self.assertFalse(CondicionesPERT().es_aplicable(entrada))
        self.assertTrue(CondicionesCPM().es_aplicable(Entrada(grafo, ParametrosCPM({"A": Fraction(1, 3)}))))

    def test_una_cadena_grande_y_una_actividad_independiente_son_validas_en_aon(self):
        vertices = tuple(f"A{i}" for i in range(1500)) + ("Independiente",)
        grafo = Grafo(
            vertices,
            tuple(Arista(i, f"A{i}", f"A{i + 1}", None, True) for i in range(1499)),
        )
        cpm = Entrada(grafo, ParametrosCPM(dict.fromkeys(vertices, 1)))
        pert = Entrada(grafo, ParametrosPERT(dict.fromkeys(vertices, EstimacionesPERT(1, 1, 1))))

        self.assertTrue(CondicionesCPM().es_aplicable(cpm))
        self.assertTrue(CondicionesPERT().es_aplicable(pert))

    def test_ejecutar_recomprueba_las_condiciones_y_rechaza_antes_de_resolver(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosCPM({"A": 1}))
        incompleta = Entrada(entrada.grafo, ParametrosCPM({}))
        algoritmo = ResolucionDePrueba(CondicionesCPM())

        self.assertIs(algoritmo.es_aplicable(entrada), True)
        motivo = algoritmo.motivo_inaplicabilidad(incompleta)
        with self.assertRaises(AlgoritmoNoAplicableError) as captura:
            algoritmo.ejecutar(incompleta)
        self.assertEqual(captura.exception.motivo, motivo)
        self.assertEqual(algoritmo.resoluciones, 0)
        self.assertEqual(algoritmo.ejecutar(entrada).solucion, "resuelta")
        self.assertEqual(algoritmo.resoluciones, 1)


if __name__ == "__main__":
    unittest.main()
