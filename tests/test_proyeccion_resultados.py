"""Resultados finales del núcleo, sin navegación ni dependencias visuales."""

from dataclasses import FrozenInstanceError, replace
import unittest
from unittest.mock import patch

from arboles_de_red.algoritmo import Entrada, Resultado
from arboles_de_red.arbol_expansion import Prim, Kruskal
from arboles_de_red.cpm import CPM, RutasCriticas
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.flujo_maximo import FordFulkerson
from arboles_de_red.grafo import Arista, Grafo
from arboles_de_red.parametros import (
    EstimacionesPERT, ParametrosCPM, ParametrosDijkstra,
    ParametrosFlujoMaximo, ParametrosPERT,
)
from arboles_de_red.pert import PERT
from arboles_de_red.proyeccion_resultados import (
    ErrorProyeccion, ProyeccionArbol, ProyeccionCPM, ProyeccionDijkstra,
    ProyeccionFlujo, ProyeccionPERT, proyectar_resultado,
)


def red(vertices, filas, dirigida=False):
    return Grafo(tuple(vertices), tuple(Arista(i, u, v, peso, dirigida) for i, u, v, peso in filas))


class ProyeccionResultadosTests(unittest.TestCase):
    def mst(self):
        return Entrada(red("ABCD", [
            (17, "A", "B", 3), (23, "A", "B", 1), (31, "B", "C", 2),
            (47, "A", "C", 5), (59, "C", "D", 4),
        ]), None)

    def dijkstra(self, destino=None):
        return Entrada(red("ABCDX", [
            (10, "A", "B", 5), (11, "A", "B", 1), (25, "B", "D", 2),
            (31, "A", "C", 2), (40, "C", "D", 10),
        ], True), ParametrosDijkstra("A", destino))

    def flujo(self):
        return Entrada(red("SAT", [
            (10, "S", "A", 1), (11, "S", "A", 2), (12, "A", "S", 1),
            (20, "A", "T", 2), (21, "S", "T", 0), (22, "T", "S", 1),
        ], True), ParametrosFlujoMaximo("S", "T"))

    def cpm(self):
        return Entrada(red(("A", "B", "C", "D", "Solo"), [
            (70, "A", "C", None), (71, "A", "C", None),
            (80, "B", "C", None), (90, "C", "D", None), (99, "A", "D", None),
        ], True), ParametrosCPM({"A": 2, "B": 2, "C": 3, "D": 1, "Solo": 1}))

    def pert(self):
        return Entrada(red("ABC", [
            (70, "A", "C", None), (71, "A", "C", None), (80, "B", "C", None),
        ], True), ParametrosPERT({
            "A": EstimacionesPERT(1, 4, 9), "B": EstimacionesPERT(1, 4, 9),
            "C": EstimacionesPERT(6, 6, 6),
        }))

    def test_prim_proyecta_ids_del_arbol_y_distingue_paralelas(self):
        entrada = self.mst()
        resultado = Prim().ejecutar(entrada)
        proyeccion = proyectar_resultado(entrada, resultado, "prim")
        self.assertIsInstance(proyeccion, ProyeccionArbol)
        self.assertEqual(proyeccion.algoritmo, "prim")
        self.assertEqual(proyeccion.aristas, tuple(a.identificador for a in resultado.solucion.aristas))
        self.assertEqual(proyeccion.aristas, (23, 31, 59))
        self.assertNotIn(17, proyeccion.aristas)
        self.assertEqual(proyeccion.vertices, frozenset("ABCD"))
        self.assertEqual(proyeccion.peso_total, 7)
        self.assertFalse(hasattr(proyeccion, "aristas_evaluadas"))
        self.assertFalse(hasattr(proyeccion, "arista_elegida"))

    def test_kruskal_proyecta_ids_del_arbol_sin_rechazos_del_recorrido(self):
        entrada = self.mst()
        resultado = Kruskal().ejecutar(entrada)
        proyeccion = proyectar_resultado(entrada, resultado, "kruskal")
        self.assertEqual(proyeccion.algoritmo, "kruskal")
        self.assertEqual(proyeccion.aristas, tuple(a.identificador for a in resultado.solucion.aristas))
        self.assertEqual(proyeccion.aristas, (23, 31, 59))
        self.assertFalse(hasattr(proyeccion, "aristas_rechazadas_ciclo"))
        self.assertEqual(proyeccion.peso_total, resultado.solucion.peso_total)

    def test_arbol_unico_vertice_sin_aristas(self):
        entrada = Entrada(Grafo(("101",), ()), None)
        for nombre, clase in (("prim", Prim), ("kruskal", Kruskal)):
            with self.subTest(algoritmo=nombre):
                p = proyectar_resultado(entrada, clase().ejecutar(entrada), nombre)
                self.assertEqual((p.vertices, p.aristas, p.peso_total), (frozenset({"101"}), (), 0))

    def test_dijkstra_solo_ruta_final_y_arista_paralela_correcta(self):
        entrada = self.dijkstra("D")
        resultado = Dijkstra().ejecutar(entrada)
        p = proyectar_resultado(entrada, resultado, "dijkstra")
        self.assertIsInstance(p, ProyeccionDijkstra)
        self.assertEqual((p.origen, p.destino_ejecucion, p.destino), ("A", "D", "D"))
        self.assertEqual((p.ruta, p.aristas_ruta, p.costo), (("A", "B", "D"), (11, 25), 3))
        self.assertIn("C", p.predecesores)
        self.assertNotIn(31, p.aristas_ruta)
        self.assertNotIn(10, p.aristas_ruta)

    def test_dijkstra_sin_destino_consulta_posterior_no_resuelve(self):
        entrada = self.dijkstra()
        resultado = Dijkstra().ejecutar(entrada)
        with patch.object(Dijkstra, "_resolver", side_effect=AssertionError("No debe resolver")):
            p = proyectar_resultado(entrada, resultado, "dijkstra")
            self.assertEqual((p.destino, p.ruta, p.aristas_ruta, p.costo), (None, None, None, None))
            consultada = p.consultar_destino("D")
            self.assertEqual((consultada.ruta, consultada.aristas_ruta, consultada.costo),
                             (("A", "B", "D"), (11, 25), 3))
            self.assertIsNone(consultada.destino_ejecucion)
            self.assertIsNone(p.destino)
            self.assertEqual(p.consultar_destino("C").aristas_ruta, (31,))
            self.assertEqual(proyectar_resultado(entrada, resultado, "dijkstra", destino="D"), consultada)

    def test_dijkstra_destino_inalcanzable_no_es_ausencia_de_consulta(self):
        entrada = self.dijkstra("X")
        p = proyectar_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")
        self.assertEqual(p.destino, "X")
        self.assertEqual((p.ruta, p.aristas_ruta, p.costo), (None, None, None))
        self.assertEqual(p.distancias["X"], float("inf"))
        self.assertIn("X", p.inalcanzables)
        self.assertEqual(p.consultar_destino("X"), p)
        with self.assertRaisesRegex(ErrorProyeccion, "no existe"):
            p.consultar_destino("Inexistente")

    def test_dijkstra_origen_igual_destino(self):
        entrada = self.dijkstra("A")
        p = proyectar_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")
        self.assertEqual((p.ruta, p.aristas_ruta, p.costo), (("A",), (), 0))
        self.assertEqual(p.consultar_destino("A"), p)

    def test_dijkstra_respeta_arista_no_dirigida_recorrida_al_reves(self):
        entrada = Entrada(red("AB", [(94, "B", "A", 9.5)]), ParametrosDijkstra("A", "B"))
        p = proyectar_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")
        self.assertEqual((p.ruta, p.aristas_ruta, p.costo), (("A", "B"), (94,), 9.5))

    def test_flujo_capacidades_flujos_ceros_paralelas_y_antiparalelas_por_id(self):
        entrada = self.flujo()
        resultado = FordFulkerson().ejecutar(entrada)
        p = proyectar_resultado(entrada, resultado, "flujo_maximo")
        self.assertIsInstance(p, ProyeccionFlujo)
        self.assertEqual(set(p.arcos), {10, 11, 12, 20, 21, 22})
        self.assertEqual(p.flujo_maximo, 2)
        for a in entrada.grafo.aristas:
            arco = p.arcos[a.identificador]
            self.assertEqual((arco.identificador, arco.origen, arco.destino, arco.capacidad_original),
                             (a.identificador, a.origen, a.destino, a.peso))
            self.assertEqual(arco.flujo, resultado.solucion.flujo_por_arco[a.identificador])
        self.assertEqual((p.arcos[10].flujo, p.arcos[11].flujo), (1, 1))
        self.assertEqual((p.arcos[12].flujo, p.arcos[12].capacidad_original), (0, 1))
        self.assertEqual((p.arcos[21].flujo, p.arcos[21].capacidad_original), (0, 0))
        self.assertEqual(p.aristas_corte, resultado.solucion.aristas_corte)
        self.assertEqual(p.capacidad_corte, resultado.solucion.capacidad_corte)
        self.assertEqual(p.lado_fuente, frozenset(resultado.solucion.lado_fuente))
        self.assertEqual(p.lado_sumidero, frozenset(resultado.solucion.lado_sumidero))
        self.assertFalse(hasattr(p, "capacidades_residuales"))

    def test_flujo_maximo_cero_conserva_todos_los_arcos(self):
        entrada = Entrada(red("SAT", [(3, "S", "A", 0), (8, "A", "T", 3)], True),
                          ParametrosFlujoMaximo("S", "T"))
        p = proyectar_resultado(entrada, FordFulkerson().ejecutar(entrada), "flujo_maximo")
        self.assertEqual(p.flujo_maximo, 0)
        self.assertEqual(set(p.arcos), {3, 8})
        self.assertTrue(all(a.flujo == 0 for a in p.arcos.values()))

    def test_cpm_red_critica_valores_finales_y_precedencias_paralelas(self):
        entrada = self.cpm()
        resultado = CPM().ejecutar(entrada)
        with patch.object(RutasCriticas, "__iter__", side_effect=AssertionError("No enumerar rutas")):
            p = proyectar_resultado(entrada, resultado, "cpm")
        self.assertIsInstance(p, ProyeccionCPM)
        self.assertEqual(p.actividades, resultado.solucion.actividades)
        self.assertEqual(p.duracion_proyecto, 6)
        self.assertEqual(p.actividades_criticas, frozenset("ABCD"))
        self.assertEqual(p.aristas_criticas, (70, 71, 80, 90))
        self.assertNotIn(99, p.aristas_criticas)  # Une actividades críticas, pero no es relación crítica.
        self.assertEqual(set(p.actividades), set(entrada.grafo.vertices))
        self.assertTrue(all(a.peso is None and a.dirigida for a in entrada.grafo.aristas))

    def test_cpm_criticidad_no_se_redecide_desde_holguras_publicadas(self):
        entrada = self.cpm()
        solucion = CPM().ejecutar(entrada).solucion
        # La red crítica calculada sigue siendo la autoridad, incluso si se
        # suministran copias de valores publicados con otras holguras.
        copia = replace(solucion, actividades={v: replace(t, holgura=123.456)
                                               for v, t in solucion.actividades.items()})
        p = proyectar_resultado(entrada, Resultado(copia, ()), "cpm")
        self.assertEqual(p.actividades_criticas, frozenset(solucion.rutas_criticas.sucesoras))
        self.assertEqual(p.aristas_criticas, (70, 71, 80, 90))

    def test_cpm_multiples_rutas_exponenciales_sin_materializarlas(self):
        vertices = tuple(f"V{i}" for i in range(40))
        pares = [(vertices[i], vertices[j]) for i in range(38)
                 for j in range((i // 2 + 1) * 2, (i // 2 + 1) * 2 + 2)]
        entrada = Entrada(red(vertices, [(100 + i, u, v, None) for i, (u, v) in enumerate(pares)], True),
                          ParametrosCPM(dict.fromkeys(vertices, 1)))
        resultado = CPM().ejecutar(entrada)
        self.assertEqual(resultado.solucion.rutas_criticas.cantidad, 2 ** 20)
        with patch.object(RutasCriticas, "__iter__", side_effect=AssertionError("No enumerar rutas")):
            p = proyectar_resultado(entrada, resultado, "cpm")
        self.assertEqual(p.actividades_criticas, frozenset(vertices))
        self.assertEqual(p.aristas_criticas, tuple(a.identificador for a in entrada.grafo.aristas))

    def test_cpm_actividad_independiente_unica_critica(self):
        entrada = Entrada(Grafo(("101",), ()), ParametrosCPM({"101": 0}))
        p = proyectar_resultado(entrada, CPM().ejecutar(entrada), "cpm")
        self.assertEqual(p.actividades_criticas, frozenset({"101"}))
        self.assertEqual(p.aristas_criticas, ())

    def test_pert_conserva_estimaciones_planificacion_criticidad_y_precision(self):
        entrada = self.pert()
        resultado = PERT().ejecutar(entrada)
        with patch.object(RutasCriticas, "__iter__", side_effect=AssertionError("No enumerar rutas")):
            p = proyectar_resultado(entrada, resultado, "pert")
        self.assertIsInstance(p, ProyeccionPERT)
        self.assertEqual(p.estimaciones, resultado.solucion.estimaciones)
        self.assertEqual(p.actividades, resultado.solucion.planificacion.actividades)
        self.assertEqual(p.tiempos_esperados["A"], 4.333333333333333)
        self.assertEqual(p.varianzas["A"], 1.7777777777777777)
        self.assertEqual(p.duracion_esperada, 10.333333333333334)
        self.assertEqual((p.estimaciones["A"].optimista, p.estimaciones["A"].mas_probable,
                          p.estimaciones["A"].pesimista), (1, 4, 9))
        self.assertEqual(p.actividades_criticas, frozenset("ABC"))
        self.assertEqual(p.aristas_criticas, (70, 71, 80))

    def test_seis_algoritmos_sin_pasos_sin_resolver_y_sin_mutar_entrada(self):
        casos = (("prim", Prim, self.mst()), ("kruskal", Kruskal, self.mst()),
                 ("dijkstra", Dijkstra, self.dijkstra("D")), ("flujo_maximo", FordFulkerson, self.flujo()),
                 ("cpm", CPM, self.cpm()), ("pert", PERT, self.pert()))
        for nombre, clase, entrada in casos:
            with self.subTest(algoritmo=nombre):
                resultado = clase().ejecutar(entrada)
                original = repr((entrada, resultado))
                with patch.object(clase, "_resolver", side_effect=AssertionError("No debe resolver")):
                    normal = proyectar_resultado(entrada, resultado, nombre)
                    vacio = proyectar_resultado(entrada, Resultado(resultado.solucion, ()), nombre)
                self.assertEqual(normal, vacio)
                self.assertEqual(repr((entrada, resultado)), original)
                with self.assertRaises(FrozenInstanceError):
                    normal.algoritmo = "otro"

    def test_mapas_y_valores_anidados_son_inmutables_y_no_aliasan_mapas_mutables(self):
        entrada = self.pert()
        p = proyectar_resultado(entrada, PERT().ejecutar(entrada), "pert")
        for nombre in ("actividades", "estimaciones", "tiempos_esperados", "varianzas"):
            with self.subTest(mapa=nombre):
                mapa = getattr(p, nombre)
                with self.assertRaises(TypeError):
                    mapa["A"] = None
                externo = dict(mapa)
                copia = replace(p, **{nombre: externo})
                externo.clear()
                self.assertEqual(getattr(copia, nombre), mapa)
        with self.assertRaises(FrozenInstanceError):
            p.actividades["A"].ic = 42
        with self.assertRaises(FrozenInstanceError):
            p.estimaciones["A"].optimista = 42
        carga_f = self.flujo()
        flujo = proyectar_resultado(carga_f, FordFulkerson().ejecutar(carga_f), "flujo_maximo")
        with self.assertRaises(TypeError):
            flujo.arcos[10] = None
        with self.assertRaises(FrozenInstanceError):
            flujo.arcos[10].flujo = 42
        carga_d = self.dijkstra()
        dijkstra = proyectar_resultado(carga_d, Dijkstra().ejecutar(carga_d), "dijkstra")
        with self.assertRaises(TypeError):
            dijkstra.predecesores["B"] = ("C", 40)
        with self.assertRaises(TypeError):
            dijkstra.distancias["B"] = 42

    def test_regresion_dijkstra_origen_y_destino_original_incompatibles(self):
        entrada = self.dijkstra("D")
        resultado = Dijkstra().ejecutar(entrada)
        for parametros, mensaje in ((ParametrosDijkstra("C", "D"), "origen"),
                                    (ParametrosDijkstra("A", "C"), "destino")):
            with self.subTest(parametros=parametros), self.assertRaisesRegex(ErrorProyeccion, mensaje):
                proyectar_resultado(replace(entrada, parametros=parametros), resultado, "dijkstra")

    def test_regresion_dijkstra_id_existente_extremos_o_direccion_incompatibles(self):
        entrada = Entrada(red("ABC", [(0, "A", "B", 1), (1, "A", "C", 2)], True),
                          ParametrosDijkstra("A", "B"))
        resultado = Dijkstra().ejecutar(entrada)
        for nueva in (Arista(0, "A", "C", 1, True), Arista(0, "B", "A", 1, True)):
            with self.subTest(arista=nueva), self.assertRaises(ErrorProyeccion):
                carga = replace(entrada, grafo=Grafo(entrada.grafo.vertices, (nueva, entrada.grafo.aristas[1])))
                proyectar_resultado(carga, resultado, "dijkstra")

    def test_regresion_flujo_capacidad_ajena_exceso_negativo_y_no_finito(self):
        entrada = Entrada(red("ST", [(0, "S", "T", 2)], True), ParametrosFlujoMaximo("S", "T"))
        resultado = FordFulkerson().ejecutar(entrada)
        ajena = replace(entrada, grafo=red("ST", [(0, "S", "T", 1)], True))
        with self.assertRaisesRegex(ErrorProyeccion, "excede.*capacidad"):
            proyectar_resultado(ajena, resultado, "flujo_maximo")
        for valor in (3, -1, float("nan"), float("inf")):
            with self.subTest(flujo=valor), self.assertRaises(ErrorProyeccion):
                solucion = replace(resultado.solucion, flujo_por_arco={0: valor})
                proyectar_resultado(entrada, Resultado(solucion, ()), "flujo_maximo")

    def test_flujo_tolerancia_no_modifica_valores_y_terminales_se_validan(self):
        entrada = Entrada(red("ST", [(0, "S", "T", 2)], True), ParametrosFlujoMaximo("S", "T"))
        resultado = FordFulkerson().ejecutar(entrada)
        for valor in (-1e-13, 2 + 1e-13):
            with self.subTest(flujo=valor):
                solucion = replace(resultado.solucion, flujo_por_arco={0: valor})
                p = proyectar_resultado(entrada, Resultado(solucion, ()), "flujo_maximo")
                self.assertEqual(p.arcos[0].flujo, valor)
        with self.assertRaisesRegex(ErrorProyeccion, "fuente|sumidero"):
            proyectar_resultado(replace(entrada, parametros=ParametrosFlujoMaximo("T", "S")),
                               resultado, "flujo_maximo")

    def test_regresion_pert_estimaciones_originales_incompatibles(self):
        entrada = self.pert()
        resultado = PERT().ejecutar(entrada)
        otras = dict(entrada.parametros.estimaciones)
        otras["A"] = EstimacionesPERT(2, 5, 10)
        with self.assertRaisesRegex(ErrorProyeccion, "estimaciones.*originales"):
            proyectar_resultado(replace(entrada, parametros=ParametrosPERT(otras)), resultado, "pert")

    def test_cpm_valida_actividades_pero_no_infiere_duraciones_no_publicadas(self):
        entrada = Entrada(red("AB", [(0, "A", "B", None)], True), ParametrosCPM({"A": 1, "B": 1}))
        resultado = CPM().ejecutar(entrada)
        self.assertFalse(hasattr(resultado.solucion, "duraciones"))
        # Limitación explícita del contrato: no inferir duraciones desde TC-IC.
        ajena = replace(entrada, parametros=ParametrosCPM({"A": 100, "B": 100}))
        self.assertEqual(proyectar_resultado(ajena, resultado, "cpm").actividades,
                         resultado.solucion.actividades)
        with self.assertRaisesRegex(ErrorProyeccion, "parámetros.*identificadores"):
            proyectar_resultado(replace(entrada, parametros=ParametrosCPM({"A": 1})), resultado, "cpm")

    def test_regresion_arbol_compara_datos_originales_y_tipo_de_solucion(self):
        entrada = self.mst()
        resultado = Prim().ejecutar(entrada)
        arista = resultado.solucion.aristas[0]
        for cambios in ({"peso": 99}, {"dirigida": True}, {"destino": "D"}):
            with self.subTest(cambios=cambios), self.assertRaisesRegex(ErrorProyeccion, "original"):
                solucion = replace(resultado.solucion, aristas=(replace(arista, **cambios),))
                proyectar_resultado(entrada, Resultado(solucion, ()), "prim")
        for algoritmo in ("dijkstra", "flujo_maximo", "cpm", "pert"):
            with self.subTest(algoritmo=algoritmo), self.assertRaisesRegex(ErrorProyeccion, "incompatible"):
                proyectar_resultado(entrada, resultado, algoritmo)

    def test_rechaza_algoritmo_tipo_destino_o_ids_incompatibles(self):
        entrada = self.mst()
        resultado = Prim().ejecutar(entrada)
        for algoritmo in ("desconocido", "dijkstra"):
            with self.assertRaises(ErrorProyeccion):
                proyectar_resultado(entrada, resultado, algoritmo)
        with self.assertRaises(ErrorProyeccion):
            proyectar_resultado(entrada, resultado, "prim", destino="A")
        ajena = replace(resultado.solucion.aristas[0], identificador=9999)
        invalido = Resultado(replace(resultado.solucion, aristas=(ajena,)), ())
        with self.assertRaisesRegex(ErrorProyeccion, "inexistente"):
            proyectar_resultado(entrada, invalido, "prim")


if __name__ == "__main__":
    unittest.main()
