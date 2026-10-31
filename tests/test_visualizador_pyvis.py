"""Pruebas del adaptador visual PyVis para entradas reales del proyecto."""

from itertools import combinations
from dataclasses import replace
import re
import unittest

try:
    import networkx  # noqa: F401
    import streamlit  # noqa: F401
    import pyvis  # noqa: F401

    from arboles_de_red.algoritmo import Entrada
    from arboles_de_red.csv import (
        ProcesadorCPMCSV,
        ProcesadorConexionesCSV,
        ProcesadorPERTCSV,
    )
    from arboles_de_red.grafo import Arista, Grafo
    from arboles_de_red.visualizador_pyvis import VisualizadorPyVis

    DEPENDENCIAS_VISUALIZACION = True
except ModuleNotFoundError:
    DEPENDENCIAS_VISUALIZACION = False


@unittest.skipUnless(
    DEPENDENCIAS_VISUALIZACION,
    "Instalá el grupo opcional poc-streamlit-estatica para estas pruebas.",
)
class VisualizadorPyVisTests(unittest.TestCase):
    def setUp(self):
        self.visualizador = VisualizadorPyVis()

    def test_html_personaliza_solo_controles_nativos_sin_cambiar_scripts_ni_red(self):
        entrada = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", 1, True),)), None)
        posiciones = {"A": (10.0, 20.0), "B": (30.0, 40.0)}
        red = self.visualizador.construir_red(entrada, "Conexiones", posiciones=posiciones)
        original = red.generate_html()
        datos_originales = repr((red.nodes, red.edges, red.options))
        html = self.visualizador.generar_html(red)
        marca = '<style id="estilo-navegacion-pyvis">'
        self.assertEqual(html.count(marca), 1)
        inicio = html.index(marca) + len(marca)
        css = html[inicio:html.index("</style>", inicio)]
        self.assertTrue(all(selector.strip().startswith("#mynetwork .vis-navigation .vis-button")
                            for selector in re.findall(r"([^{}]+)\{", css)))
        for clase in ("vis-up", "vis-down", "vis-left", "vis-right", "vis-zoomIn",
                      "vis-zoomOut", "vis-zoomExtends"):
            self.assertIn(f".vis-button.{clase}::before", css)
        self.assertIn(".vis-button:hover", css)
        self.assertIn(".vis-button:active", css)
        self.assertTrue(red.options["interaction"]["navigationButtons"])
        self.assertFalse(red.options["physics"]["enabled"])
        self.assertEqual(repr((red.nodes, red.edges, red.options)), datos_originales)
        self.assertEqual(re.findall(r"<script\b[^>]*>.*?</script>", html, re.DOTALL),
                         re.findall(r"<script\b[^>]*>.*?</script>", original, re.DOTALL))

    def test_conexiones_con_pesos_cero_negativo_direcciones_y_paralelas(self):
        entrada = ProcesadorConexionesCSV().preparar_entrada(
            "origen,destino,peso,dirigida\n"
            "A,B,0,true\n"
            "A,B,-2,false\n"
            "B,C,1,true\n"
        )
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual(len(red.nodes), 3)
        self.assertEqual(len(red.edges), 3)
        self.assertEqual([edge["id"] for edge in red.edges], ["arista-0", "arista-1", "arista-2"])
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[1]["arrows"], "")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("peso 0.0", red.edges[0]["title"])
        self.assertIn("peso -2.0", red.edges[1]["title"])
        self.assertIn("dirigida", red.edges[0]["title"])
        self.assertIn("no dirigida", red.edges[1]["title"])

    def test_vertices_aislados_y_peso_none_se_conservan(self):
        grafo = Grafo(
            ("A", "B", "aislado"),
            (Arista(0, "A", "B", None, True),),
        )
        entrada = Entrada(grafo, None)
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual({node["id"] for node in red.nodes}, {"A", "B", "aislado"})
        self.assertEqual(len(red.edges), 1)
        self.assertIn("sin peso", red.edges[0]["title"])
        self.assertNotIn("peso 0", red.edges[0]["title"])

    def test_cpm_asocia_duracion_y_precedencias_sin_peso(self):
        entrada = ProcesadorCPMCSV().preparar_entrada(
            "actividad,duracion,predecesoras\nA,2,\nB,3,A\nSolo,5,\n"
        )
        red = self.visualizador.construir_red(entrada, "CPM")
        nodos = {node["id"]: node for node in red.nodes}

        self.assertEqual(len(red.nodes), 3)
        self.assertIn("Duración: 2", nodos["A"]["label"])
        self.assertIn("Duración: 2", nodos["A"]["title"])
        self.assertEqual(len(red.edges), 1)
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("sin peso", red.edges[0]["title"])

    def test_pert_muestra_tripleta_original_y_precedencia_sin_peso(self):
        entrada = ProcesadorPERTCSV().preparar_entrada(
            "actividad,optimista,mas_probable,pesimista,predecesoras\n"
            "A,1,2,4,\nB,2,3,8,A\n"
        )
        red = self.visualizador.construir_red(entrada, "PERT")
        nodos = {node["id"]: node for node in red.nodes}

        self.assertIn("O: 1 | M: 2 | P: 4", nodos["A"]["label"])
        self.assertIn("Optimista: 1", nodos["A"]["title"])
        self.assertIn("Más probable: 2", nodos["A"]["title"])
        self.assertIn("Pesimista: 4", nodos["A"]["title"])
        self.assertEqual(len(red.edges), 1)
        self.assertEqual(red.edges[0]["arrows"], "to")
        self.assertEqual(red.edges[0]["label"], "")
        self.assertIn("sin peso", red.edges[0]["title"])

    def test_escala_200_nodos_890_aristas_posiciones_fijas_sin_fisica(self):
        vertices = tuple(f"V{indice}" for indice in range(200))
        pares = combinations(vertices, 2)
        aristas = tuple(
            Arista(identificador, origen, destino, 1.0, False)
            for identificador, (origen, destino) in zip(range(890), pares)
        )
        entrada = Entrada(Grafo(vertices, aristas), None)

        posiciones_1 = self.visualizador.calcular_posiciones(entrada.grafo)
        posiciones_2 = self.visualizador.calcular_posiciones(entrada.grafo)
        red = self.visualizador.construir_red(entrada, "Conexiones")

        self.assertEqual(len(posiciones_1), 200)
        self.assertEqual(posiciones_1, posiciones_2)
        self.assertEqual(len(red.nodes), 200)
        self.assertEqual(len(red.edges), 890)
        self.assertTrue(all(node["fixed"] is True for node in red.nodes))
        self.assertFalse(red.options["physics"]["enabled"])

    def test_cpm_pert_resaltan_precedencia_actual_con_prioridad_sobre_critica(self):
        from arboles_de_red.reconstruccion import ReconstruccionEjecucion
        from arboles_de_red.seleccion import SelectorAlgoritmos

        casos = (
            ("cpm", "CPM", ProcesadorCPMCSV(), "actividad,duracion,predecesoras\nA,2,\nB,3,A\n"),
            ("pert", "PERT", ProcesadorPERTCSV(),
             "actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,2,3,\nB,2,3,4,A\n"),
        )
        for algoritmo, formato, procesador, csv in casos:
            with self.subTest(algoritmo=algoritmo):
                entrada = procesador.preparar_entrada(csv)
                seleccion = SelectorAlgoritmos().seleccionar(algoritmo, entrada)
                resultado = seleccion.ejecutar()
                rec = ReconstruccionEjecucion(entrada, resultado, algoritmo)
                paso = next(p for p in resultado.pasos if getattr(p.detalle, "fase", None) == "adelante"
                            and p.detalle.actividad == "B")
                estado = rec.estado_en(paso.numero)
                self.assertEqual(estado.aristas_destacadas, (0,))
                normal = self.visualizador.construir_red(entrada, formato).edges[0]
                actual = self.visualizador.construir_red(entrada, formato, estado=estado).edges[0]
                self.assertEqual(actual["id"], "arista-0")
                self.assertEqual(actual["arrows"], "to")
                self.assertGreater(actual["width"], normal["width"])
                self.assertNotEqual(actual["color"], normal["color"])
                final = rec.estado_en(len(resultado.pasos))
                critica = self.visualizador.construir_red(
                    entrada, formato, estado=replace(final, aristas_destacadas=()),
                ).edges[0]
                actual_y_critica = self.visualizador.construir_red(entrada, formato, estado=final).edges[0]
                self.assertEqual(critica["color"]["color"], "#dc3545")
                self.assertEqual(actual_y_critica["color"], actual["color"])
                self.assertGreater(actual_y_critica["width"], critica["width"])
                self.assertEqual(len(entrada.grafo.aristas), 1)

    def test_cpm_pert_comparten_formato_por_fase_sin_redondear_datos_internos(self):
        from arboles_de_red.formato_visual import formatear_numero
        from arboles_de_red.parametros import EstimacionesPERT, ParametrosCPM, ParametrosPERT
        from arboles_de_red.presentacion_pasos import resumir_paso
        from arboles_de_red.reconstruccion import ReconstruccionEjecucion
        from arboles_de_red.seleccion import SelectorAlgoritmos

        grafo = Grafo(("101", "202"), (Arista(700, "101", "202", None, True),))
        casos = (
            ("cpm", ParametrosCPM({"101": 4.333333333333333, "202": 6.0}), "CPM"),
            ("pert", ParametrosPERT({"101": EstimacionesPERT(1, 4, 9),
                                     "202": EstimacionesPERT(6, 6, 6)}), "PERT"),
        )
        for algoritmo, parametros, formato in casos:
            with self.subTest(algoritmo=algoritmo):
                entrada = Entrada(grafo, parametros)
                seleccion = SelectorAlgoritmos().seleccionar(algoritmo, entrada)
                resultado = seleccion.ejecutar()
                reconstruccion = ReconstruccionEjecucion(seleccion.entrada, resultado, algoritmo)
                estados = tuple(reconstruccion.estado_en(i) for i in range(len(resultado.pasos) + 1))
                original = repr((entrada, resultado, estados))
                posiciones = {"101": (0.0, 0.0), "202": (100.0, 100.0)}

                for estado in estados:
                    campos = dict(resumir_paso(entrada, estado))
                    red = self.visualizador.construir_red(entrada, formato, posiciones=posiciones, estado=estado)
                    nodos = {n["id"]: n for n in red.nodes}
                    self.assertEqual(set(nodos), {"101", "202"})
                    self.assertEqual(red.edges[0]["id"], "arista-700")
                    self.assertEqual(red.edges[0]["label"], "")
                    plan = estado.estado.planificacion if algoritmo == "pert" else estado.estado
                    for actividad, valores in plan.valores_por_actividad.items():
                        for nombre, valor in (("IC", valores.ic), ("TC", valores.tc), ("IL", valores.il),
                                              ("TL", valores.tl), ("Holgura", valores.holgura)):
                            if valor is None:
                                self.assertNotIn(f"{nombre}:", nodos[actividad]["title"])
                                if campos.get("Actividad") == actividad:
                                    self.assertNotIn(nombre, campos)
                            else:
                                texto = formatear_numero(valor)
                                self.assertIn(f"{nombre}: {texto}", nodos[actividad]["title"].splitlines())
                                self.assertIn(f"{nombre}={texto}", nodos[actividad]["label"].splitlines()[-1].split(" | "))
                                if campos.get("Actividad") == actividad:
                                    self.assertEqual(campos[nombre], texto)

                red_final = self.visualizador.construir_red(entrada, formato, posiciones=posiciones, estado=estados[-1])
                self.assertIn("TC=10.33", red_final.nodes[1]["label"])
                plan_final = estados[-1].estado.planificacion if algoritmo == "pert" else estados[-1].estado
                self.assertEqual(plan_final.valores_por_actividad["202"].tc,
                                 resultado.solucion.actividades["202"].tc)
                self.assertNotEqual(plan_final.valores_por_actividad["202"].tc, 10.33)
                if algoritmo == "pert":
                    estimacion = dict(resumir_paso(entrada, estados[1]))
                    self.assertEqual(estimacion["Tiempo esperado"], "4.33")
                    self.assertEqual(estimacion["Varianza"], "1.78")
                    self.assertEqual(resultado.pasos[0].detalle.tiempo_esperado, 4.333333333333333)
                    self.assertEqual(resultado.pasos[0].detalle.varianza, 1.7777777777777777)
                    self.assertEqual(plan_final.valores_por_actividad["202"].tc, 10.333333333333334)
                    self.assertEqual(estados[-1].estado.varianzas["101"], 1.7777777777777777)
                    self.assertIn("Var: 1.78", red_final.nodes[0]["label"])
                    self.assertIn("Tiempo esperado: 4.33", red_final.nodes[0]["title"])
                else:
                    self.assertEqual(entrada.parametros.duraciones["101"], 4.333333333333333)
                    self.assertIn("Duración: 4.33", red_final.nodes[0]["label"])
                self.assertEqual(repr((entrada, resultado, estados)), original)


if __name__ == "__main__":
    unittest.main()
