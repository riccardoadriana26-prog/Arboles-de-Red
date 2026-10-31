"""Integración entre selección, reconstrucción y proyección PyVis de estados."""

import unittest
from pathlib import Path
from unittest.mock import patch

from arboles_de_red import (
    Arista, Entrada, EstimacionesPERT, Grafo, ParametrosCPM,
    ParametrosPERT, SelectorAlgoritmos,
)
from arboles_de_red.reconstruccion import (
    EstadoDijkstra, EstadoExpansion, EstadoFlujoResidual, EstadoPERT,
    EstadoPlanificacion, ReconstruccionEjecucion,
)
try:
    from streamlit.testing.v1 import AppTest
    from arboles_de_red.arbol_expansion import Prim
    from arboles_de_red.visualizador_pyvis import VisualizadorPyVis
    from poc_streamlit_estatica import (
        _mover_paso,
        _serializable,
        clave_ejecucion,
        invalidar_ejecucion_si_cambia,
    )
    DEPENDENCIAS_UI_DISPONIBLES = True
except ModuleNotFoundError:
    DEPENDENCIAS_UI_DISPONIBLES = False


def red(vertices, conexiones, dirigida):
    return Grafo(tuple(vertices), tuple(Arista(i, u, v, w, dirigida) for i, (u, v, w) in enumerate(conexiones)))


@unittest.skipUnless(DEPENDENCIAS_UI_DISPONIBLES, "La integración requiere el grupo opcional de visualización.")
class IntegracionVisualizacionTests(unittest.TestCase):
    def setUp(self):
        self.selector = SelectorAlgoritmos()
        self.visualizador = VisualizadorPyVis()

    def _ejecutar(self, nombre, entrada, opciones=None):
        seleccion = self.selector.seleccionar(nombre, entrada, opciones)
        self.assertTrue(seleccion.puede_ejecutarse, seleccion.motivo)
        resultado = seleccion.ejecutar()
        reconstruccion = ReconstruccionEjecucion(seleccion.entrada, resultado, seleccion.identificador)
        return seleccion.entrada, resultado, reconstruccion

    def test_selector_prepara_y_ejecuta_los_seis_algoritmos(self):
        conexa = Entrada(red("ABC", [("A", "B", 2), ("B", "C", 1), ("A", "C", 4)], False), None)
        dirigida = Entrada(red("ABC", [("A", "B", 2), ("B", "C", 1), ("A", "C", 4)], True), None)
        aon = Grafo(("A", "B", "C"), (Arista(0, "A", "C", None, True),))
        cpm = Entrada(aon, ParametrosCPM({"A": 1, "B": 2, "C": 3}))
        pert = Entrada(aon, ParametrosPERT({v: EstimacionesPERT(1, 2, 3) for v in aon.vertices}))
        casos = (
            ("prim", conexa, {}, "Conexiones"),
            ("kruskal", conexa, {}, "Conexiones"),
            ("dijkstra", dirigida, {"origen": "A", "destino": "C"}, "Conexiones"),
            ("flujo_maximo", dirigida, {"fuente": "A", "sumidero": "C"}, "Conexiones"),
            ("cpm", cpm, {}, "CPM"),
            ("pert", pert, {}, "PERT"),
        )
        for nombre, carga, opciones, formato in casos:
            with self.subTest(algoritmo=nombre):
                entrada, resultado, reconstruccion = self._ejecutar(nombre, carga, opciones)
                self.assertIs(entrada.grafo, carga.grafo)
                self.assertGreater(len(resultado.pasos), 0)
                self.assertEqual(reconstruccion.estado_en(0).numero, 0)
                self.assertEqual(reconstruccion.estado_en(len(resultado.pasos)).numero, len(resultado.pasos))
                estado = reconstruccion.estado_en(len(resultado.pasos) // 2).estado
                red_pyvis = self.visualizador.construir_red(entrada, formato, estado=reconstruccion.estado_en(len(resultado.pasos) // 2))
                self.assertEqual({n["id"] for n in red_pyvis.nodes}, set(carga.grafo.vertices))
                self.assertGreaterEqual(len(red_pyvis.edges), len(carga.grafo.aristas))
                self.assertIsInstance(estado, (EstadoExpansion, EstadoDijkstra, EstadoFlujoResidual,
                                               EstadoPlanificacion, EstadoPERT))

    def test_parametros_obligatorios_no_reciben_valores_inventados(self):
        entrada = Entrada(red("ABC", [("A", "B", 1), ("B", "C", 1)], True), None)
        with self.assertRaises(ValueError):
            self.selector.seleccionar("dijkstra", entrada, {})
        with self.assertRaises(ValueError):
            self.selector.seleccionar("flujo_maximo", entrada, {"fuente": "A"})

    def test_posiciones_se_reutilizan_sin_recalcular_layout(self):
        entrada = Entrada(red("ABC", [("A", "B", 1), ("B", "C", 1)], False), None)
        posiciones = self.visualizador.calcular_posiciones(entrada.grafo)
        self.visualizador.calcular_posiciones = lambda grafo: self.fail("se recalculó el layout")
        red_pyvis = self.visualizador.construir_red(entrada, "Conexiones", posiciones=posiciones)
        nodos = {n["id"]: n for n in red_pyvis.nodes}
        self.assertEqual((nodos["A"]["x"], nodos["A"]["y"]), posiciones["A"])
        self.assertTrue(all(n["fixed"] for n in red_pyvis.nodes))
        self.assertFalse(red_pyvis.options["physics"]["enabled"])

    def test_ford_visualiza_inversos_con_id_origen_sin_modificar_grafo(self):
        carga = Entrada(red("SABCDT", [
            ("S", "A", 1), ("S", "B", 1), ("A", "C", 1), ("A", "D", 1),
            ("B", "C", 1), ("C", "T", 1), ("D", "T", 1),
        ], True), None)
        # Completa los parámetros en el selector, igual que haría la interfaz.
        entrada, resultado, reconstruccion = self._ejecutar(
            "flujo_maximo", carga, {"fuente": "S", "sumidero": "T"},
        )
        antes = (entrada.grafo.vertices, entrada.grafo.aristas)
        numero = next(i for i, paso in enumerate(resultado.pasos, 1)
                      if any(tramo.inverso for tramo in paso.detalle.camino))
        estado = reconstruccion.estado_en(numero)
        red_pyvis = self.visualizador.construir_red(
            entrada, "Conexiones", posiciones=self.visualizador.calcular_posiciones(entrada.grafo), estado=estado,
        )
        inversos = [a for a in red_pyvis.edges if str(a["id"]).startswith("residual-inverso-")]
        self.assertTrue(any("Arco residual inverso de arista original" in a["title"] for a in inversos))
        self.assertTrue(any(t.inverso for t in estado.estado.camino))
        self.assertEqual(estado.estado.capacidades_residuales[(2, True)], 0)
        utilizado = next(a for a in inversos if a["id"] == "residual-inverso-2")
        self.assertEqual((utilizado["from"], utilizado["to"]), ("C", "A"))
        self.assertIn("agotado", utilizado["title"])
        final = reconstruccion.estado_en(len(resultado.pasos))
        red_final = self.visualizador.construir_red(entrada, "Conexiones", estado=final)
        self.assertFalse(any(a["id"] == "residual-inverso-2" for a in red_final.edges))
        self.assertEqual((entrada.grafo.vertices, entrada.grafo.aristas), antes)

    def test_nodos_y_aristas_reflejan_decisiones_de_expansion_y_dijkstra(self):
        carga = Entrada(red("ABC", [("A", "B", 1), ("B", "C", 2), ("A", "C", 4)], False), None)
        entrada, resultado, reconstruccion = self._ejecutar("prim", carga)
        numero = next(i for i, paso in enumerate(resultado.pasos, 1) if paso.detalle.arista is not None)
        estado = reconstruccion.estado_en(numero)
        red_pyvis = self.visualizador.construir_red(entrada, "Conexiones", estado=estado)
        arista_id = estado.estado.arista_elegida
        visual_arista = next(a for a in red_pyvis.edges if a["id"] == f"arista-{arista_id}")
        self.assertIn("Elegida en este paso", visual_arista["title"])
        self.assertGreater(visual_arista["width"], 1)

        dirigida = Entrada(red("ABC", [("A", "B", 5), ("A", "C", 1), ("C", "B", 1)], True), None)
        entrada_d, resultado_d, rec_d = self._ejecutar("dijkstra", dirigida, {"origen": "A"})
        numero_d = next(i for i, p in enumerate(resultado_d.pasos, 1) if p.detalle.accion == "relajar")
        estado_d = rec_d.estado_en(numero_d)
        red_d = self.visualizador.construir_red(entrada_d, "Conexiones", estado=estado_d)
        nodo = next(n for n in red_d.nodes if n["id"] == estado_d.estado.vertice_actual)
        self.assertIn("Distancia:", nodo["title"])
        self.assertIn("Predecesor:", nodo["title"])

        ciclica = Entrada(red("ABCD", [("A", "B", 1), ("B", "C", 2),
                                        ("A", "C", 3), ("C", "D", 4)], False), None)
        entrada_k, resultado_k, rec_k = self._ejecutar("kruskal", ciclica)
        numero_rechazo = next(i for i, p in enumerate(resultado_k.pasos, 1) if p.detalle.aceptada is False)
        estado_k = rec_k.estado_en(numero_rechazo)
        red_k = self.visualizador.construir_red(entrada_k, "Conexiones", estado=estado_k)
        rechazada = next(a for a in red_k.edges if a["id"] == f"arista-{estado_k.estado.arista_elegida}")
        self.assertEqual(rechazada["color"]["color"], "#dc3545")
        self.assertIn("Rechazada por ciclo", rechazada["title"])
        self.assertNotIn("Elegida en este paso", rechazada["title"])

    def test_cpm_y_pert_renderizan_las_etapas_y_valores_por_actividad(self):
        aon = Grafo(("A", "B", "C"), (
            Arista(0, "A", "C", None, True),
            Arista(1, "B", "C", None, True),
        ))
        entrada_cpm, resultado_cpm, reconstruccion_cpm = self._ejecutar(
            "cpm", Entrada(aon, ParametrosCPM({"A": 2, "B": 1, "C": 3})),
        )
        paso_final_cpm = reconstruccion_cpm.estado_en(len(resultado_cpm.pasos))
        red_cpm = self.visualizador.construir_red(entrada_cpm, "CPM", estado=paso_final_cpm)
        nodo_cpm = {n["id"]: n for n in red_cpm.nodes}["C"]
        self.assertIn("IC=2", nodo_cpm["label"])
        self.assertIn("TC=5", nodo_cpm["label"])
        self.assertIn("IL=2", nodo_cpm["label"])
        self.assertIn("TL=5", nodo_cpm["label"])
        self.assertIn("Holgura=0", nodo_cpm["label"])
        self.assertEqual(len(red_cpm.edges), 2)
        self.assertTrue(all(edge["arrows"] == "to" for edge in red_cpm.edges))
        self.assertTrue(all("sin peso" in edge["title"] for edge in red_cpm.edges))

        estimaciones = {
            "A": EstimacionesPERT(1, 2, 4),
            "B": EstimacionesPERT(1, 1, 1),
            "C": EstimacionesPERT(2, 3, 4),
        }
        entrada_pert, resultado_pert, reconstruccion_pert = self._ejecutar(
            "pert", Entrada(aon, ParametrosPERT(estimaciones)),
        )
        paso_estimacion = next(
            indice for indice, paso in enumerate(resultado_pert.pasos, 1)
            if paso.detalle.__class__.__name__ == "DetalleEstimacionPERT"
        )
        estado_estimacion = reconstruccion_pert.estado_en(paso_estimacion)
        red_estimacion = self.visualizador.construir_red(
            entrada_pert, "PERT", estado=estado_estimacion,
        )
        nodos_estimacion = {n["id"]: n for n in red_estimacion.nodes}
        self.assertIn("Tiempo esperado: 2.17", nodos_estimacion["A"]["title"])
        self.assertIn("Varianza:", nodos_estimacion["A"]["title"])
        self.assertNotIn("Tiempo esperado:", nodos_estimacion["B"]["title"])

        estado_final_pert = reconstruccion_pert.estado_en(len(resultado_pert.pasos))
        red_pert = self.visualizador.construir_red(entrada_pert, "PERT", estado=estado_final_pert)
        nodo_pert = {n["id"]: n for n in red_pert.nodes}["A"]
        self.assertIn("O: 1 | M: 2 | P: 4", nodo_pert["label"])
        self.assertIn("E: 2.17", nodo_pert["label"])
        self.assertIn("IC=0", nodo_pert["label"])
        self.assertEqual(len(red_pert.edges), 2)
        self.assertTrue(all(edge["arrows"] == "to" for edge in red_pert.edges))
        self.assertTrue(all("sin peso" in edge["title"] for edge in red_pert.edges))

    def test_clave_e_invalidacion_consideran_archivo_formato_algoritmo_y_opciones(self):
        base = clave_ejecucion("Conexiones", b"origen,destino\nA,B", "dijkstra", {"origen": "A"})
        variantes = (
            clave_ejecucion("CPM", b"origen,destino\nA,B", "dijkstra", {"origen": "A"}),
            clave_ejecucion("Conexiones", b"origen,destino\nA,C", "dijkstra", {"origen": "A"}),
            clave_ejecucion("Conexiones", b"origen,destino\nA,B", "prim", {}),
            clave_ejecucion("Conexiones", b"origen,destino\nA,B", "dijkstra", {"origen": "B"}),
        )
        self.assertEqual(len({base, *variantes}), 5)
        for variante in variantes:
            estado = {"hu07_ejecucion_key": base, "hu07_resultado": object(), "hu07_reconstruccion": object()}
            self.assertTrue(invalidar_ejecucion_si_cambia(estado, variante))
            self.assertNotIn("hu07_resultado", estado)
            self.assertNotIn("hu07_reconstruccion", estado)
            self.assertFalse(invalidar_ejecucion_si_cambia(estado, variante))

    def test_callback_de_navegacion_respeta_limites(self):
        estado = {"paso": 0}
        with patch("poc_streamlit_estatica.st.session_state", estado):
            _mover_paso("paso", -1, 6)
            self.assertEqual(estado["paso"], 0)
            estado["paso"] = 6
            _mover_paso("paso", 1, 6)
            self.assertEqual(estado["paso"], 6)

    def test_interfaz_ejecuta_una_vez_y_navega_con_estado_de_sesion(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "poc_streamlit_estatica.py")).run(timeout=30)
        csv = "origen,destino,peso,dirigida\nA,B,1,false\nB,C,2,false\nC,D,3,false\nD,E,4,false\nE,F,5,false\n"
        app.file_uploader[0].upload("red.csv", csv.encode("utf-8"), "text/csv").run(timeout=30)

        def comprobar(indice, consulta):
            self.assertFalse(app.exception)
            cantidad = app.session_state["hu07_reconstruccion"].cantidad_pasos
            indicador = next(m for m in app.metric if m.label == "Paso")
            self.assertEqual(indicador.value, f"{indice} / {cantidad}")
            self.assertEqual(app.slider[0].value, indice)
            self.assertIn('<style id="estilo-navegacion-pyvis">', app.get("iframe")[0].proto.srcdoc)
            self.assertEqual(app.session_state[app.session_state["hu07_slider_key"]], indice)
            self.assertTrue(any(s.value.startswith(f"Paso {indice} ") for s in app.subheader))
            if indice == 2:
                self.assertTrue(any(m.value == "**Arista elegida:** #0 A — B · peso 1"
                                    for m in app.markdown))
            self.assertEqual(consulta.call_args.args[1], indice)
            self.assertEqual(app.button[1].disabled, indice == 0)
            self.assertEqual(app.button[2].disabled, indice == cantidad)

        with patch.object(ReconstruccionEjecucion, "estado_en", autospec=True,
                          side_effect=ReconstruccionEjecucion.estado_en) as consulta:
            app.button[0].click().run(timeout=30)
            comprobar(0, consulta)
            self.assertIn("hu07_resultado", app.session_state)

            with patch.object(Prim, "_resolver", side_effect=AssertionError("navegar reejecutó Prim")):
                app.button[2].click().run(timeout=30)
                comprobar(1, consulta)
                app.button[2].click().run(timeout=30)
                comprobar(2, consulta)
                app.button[1].click().run(timeout=30)
                comprobar(1, consulta)
                app.slider[0].set_value(4).run(timeout=30)
                comprobar(4, consulta)
                cantidad = app.session_state["hu07_reconstruccion"].cantidad_pasos
                app.slider[0].set_value(cantidad).run(timeout=30)
                comprobar(cantidad, consulta)
                app.slider[0].set_value(0).run(timeout=30)
                comprobar(0, consulta)

    def test_copia_json_compacta_conserva_ids_y_valores_originales(self):
        datos = {"actividad": "101", "arista": 700, "tc": 10.333333333333334,
                 "pendiente": None, "critica": True}
        original = dict(datos)
        copia = _serializable(datos, compactar_numeros=True)
        self.assertEqual(copia, {"actividad": "101", "arista": 700, "tc": "10.33",
                                "pendiente": None, "critica": True})
        self.assertEqual(datos, original)
        self.assertEqual(_serializable(datos)["tc"], 10.333333333333334)

    def test_interfaz_cpm_pert_formatea_resumen_json_y_html_sin_alterar_precision(self):
        for formato, csv, indices in (
            ("PERT", b"actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,4,9,\nB,6,6,6,A\n", (1, 4, 5)),
            ("CPM", b"actividad,duracion,predecesoras\nA,4.333333333333333,\nB,6,A\n", (1, 2, 3)),
        ):
            with self.subTest(formato=formato):
                app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "poc_streamlit_estatica.py")).run(timeout=30)
                app.selectbox[0].set_value(formato).run(timeout=30)
                app.file_uploader[0].upload("precision.csv", csv, "text/csv").run(timeout=30)
                app.button[0].click().run(timeout=30)
                resultado = app.session_state["hu07_resultado"]
                reconstruccion = app.session_state["hu07_reconstruccion"]
                original = repr((app.session_state["hu07_entrada"], resultado))
                for indice in indices:
                    app.slider[0].set_value(indice).run(timeout=30)
                    self.assertFalse(app.exception)
                    resumen = "\n".join(m.value for m in app.markdown)
                    html = app.get("iframe")[0].proto.srcdoc
                    json_visible = "\n".join(j.value for j in app.json)
                    for numero in ("1.7777777777777777", "4.333333333333333", "10.333333333333334"):
                        self.assertNotIn(numero, resumen)
                        self.assertNotIn(numero, html)
                        self.assertNotIn(numero, json_visible)
                    if indice == 1:
                        self.assertIn("4.33", resumen)
                        self.assertIn("4.33", html)
                        if formato == "PERT":
                            self.assertIn("**Varianza:** 1.78", resumen)
                            self.assertIn("Var: 1.78", html)
                            self.assertIn("Varianza: 1.78", html)
                            self.assertIn('"varianza": "1.78"', json_visible)
                            self.assertEqual(resultado.pasos[0].detalle.varianza, 1.7777777777777777)
                            self.assertEqual(resultado.pasos[0].detalle.tiempo_esperado, 4.333333333333333)
                    else:
                        self.assertIn("10.33", resumen)
                        self.assertIn("10.33", html)
                    if formato == "PERT" and indice == 4:
                        self.assertIn("**TC:** 10.33", resumen)
                        self.assertIn("TC=10.33", html)
                        self.assertEqual(reconstruccion.estado_en(indice).estado.planificacion.valores_por_actividad["B"].tc,
                                         10.333333333333334)
                    if formato == "PERT" and indice == 5:
                        self.assertIn("**TL:** 10.33", resumen)
                        self.assertIn("TL=10.33", html)
                    self.assertEqual(repr((app.session_state["hu07_entrada"], resultado)), original)

    def test_interfaz_invalida_resultado_al_cambiar_formato_o_csv_invalido(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "poc_streamlit_estatica.py")).run(timeout=30)
        csv_valido = "origen,destino,peso,dirigida" + chr(10) + "A,B,1,false" + chr(10) + "B,C,2,false" + chr(10)
        app.file_uploader[0].upload("red.csv", csv_valido.encode("utf-8"), "text/csv").run(timeout=30)
        app.button[0].click().run(timeout=30)
        self.assertFalse(app.exception)
        self.assertIn("hu07_resultado", app.session_state)

        # Un formato nuevo invalida primero la ejecución y después informa el error de CSV.
        app.selectbox[0].set_value("CPM").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotIn("hu07_resultado", app.session_state)
        self.assertNotIn("hu07_reconstruccion", app.session_state)
        self.assertTrue(any("columna" in error.value.lower() for error in app.error))

        # Aun si se vuelve al formato anterior, el resultado descartado no reaparece.
        app.selectbox[0].set_value("Conexiones").run(timeout=30)
        self.assertNotIn("hu07_resultado", app.session_state)

        # Reejecuta con datos válidos y reemplaza el archivo por uno que no valida.
        app.button[0].click().run(timeout=30)
        self.assertIn("hu07_resultado", app.session_state)
        csv_invalido = b"origen,destino\nA,B\n"
        app.file_uploader[0].set_value(("invalido.csv", csv_invalido, "text/csv")).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertNotIn("hu07_resultado", app.session_state)
        self.assertNotIn("hu07_reconstruccion", app.session_state)
        self.assertTrue(any("peso" in error.value.lower() for error in app.error))


if __name__ == "__main__":
    unittest.main()
