"""HU-09 en la vista Resultado real de Streamlit; no certifica apariencia visual."""

from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("pyvis")

from arboles_de_red._numeros import ErrorCalculoNumerico
from arboles_de_red.arbol_expansion import Prim, Kruskal
from arboles_de_red.cpm import RutasCriticas
from arboles_de_red.csv import ProcesadorConexionesCSV
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.pert import SolucionPERT
from arboles_de_red.visualizador_pyvis import VisualizadorPyVis
from tests.test_integracion_resultados import cargar, iniciar, vista, widget, texto, datos_red, DIRIGIDO


def filas(app, indice=0):
    return app.dataframe[indice].value.to_dict("records")


def comprobar_orden_resultado(app, detalles=()):
    """Comprueba el orden en el árbol, no solamente texto presente en la página."""
    elementos = list(app.main)
    def ubicacion(tipo, valor=None):
        indices = [i for i, e in enumerate(elementos)
                   if e.type == tipo and (valor is None or e.value == valor)]
        assert len(indices) == 1, (tipo, valor, indices)
        return indices[0]
    resultado = ubicacion("subheader", "Resultado final")
    informacion = ubicacion("subheader", "Información del resultado")
    iframe = ubicacion("iframe")
    assert resultado < informacion < iframe
    grafo = app.session_state["hu07_entrada"].grafo
    for etiqueta, cantidad in (("Vértices del grafo original", len(grafo.vertices)),
                               ("Aristas del grafo original", len(grafo.aristas))):
        indice = ubicacion("markdown", f"**{etiqueta}:** {cantidad}")
        assert informacion < indice < iframe
    for etiqueta in ("Algoritmo", "Aristas del árbol", "Peso total", "Origen", "Destino consultado",
                     "Ruta", "Costo", "Flujo máximo", "Duración total", "Duración esperada",
                     "Cantidad de rutas críticas"):
        indices = [i for i, e in enumerate(elementos)
                   if e.type == "markdown" and e.value.startswith(f"**{etiqueta}:**")]
        assert len(indices) <= 1
        assert all(informacion < i < iframe for i in indices)
    obligatorias = {
        "prim": ("Algoritmo", "Aristas del árbol", "Peso total"),
        "kruskal": ("Algoritmo", "Aristas del árbol", "Peso total"),
        "dijkstra": ("Algoritmo", "Origen", "Destino consultado", "Ruta"),
        "flujo_maximo": ("Algoritmo", "Flujo máximo"),
        "cpm": ("Algoritmo", "Duración total", "Cantidad de rutas críticas"),
        "pert": ("Algoritmo", "Duración esperada", "Cantidad de rutas críticas"),
    }
    for etiqueta in obligatorias[app.session_state["hu07_algoritmo"]]:
        assert sum(e.type == "markdown" and e.value.startswith(f"**{etiqueta}:**")
                   for e in elementos) == 1
    for titulo in detalles:
        assert ubicacion("markdown", f"#### {titulo}") > iframe
    posteriores = [e for e in elementos[iframe + 1:]
                   if e.type in ("subheader", "markdown", "dataframe", "warning")]
    if not detalles:
        assert not posteriores  # Prim/Kruskal/Dijkstra no requieren un bloque vacío.
    else:
        assert app.dataframe
        tablas = [i for i, e in enumerate(elementos) if e.type == "dataframe"]
        assert len(tablas) == len(app.dataframe)
        assert all(i > iframe for i in tablas)
        assert all(i > iframe for i, e in enumerate(elementos)
                   if e.type == "markdown" and e.value.startswith("Ruta "))


@pytest.mark.parametrize("algoritmo", ["prim", "kruskal"])
def test_arbol_metricas_unicas_y_grafo_con_regresiones_de_navegacion(algoritmo):
    app = cargar()
    widget(app, "Algoritmo").set_value(algoritmo).run(timeout=30)
    iniciar(app)
    app.slider[0].set_value(2).run(timeout=30)
    nodos_originales = datos_red(app, "nodes")
    with patch.object(Prim, "_resolver", side_effect=AssertionError("No resolver")), \
         patch.object(Kruskal, "_resolver", side_effect=AssertionError("No resolver")), \
         patch.object(ProcesadorConexionesCSV, "preparar_entrada", side_effect=AssertionError("No procesar")), \
         patch.object(VisualizadorPyVis, "calcular_posiciones", side_effect=AssertionError("No layout")):
        for nombre in ("Resultado", "Datos originales", "Recorrido", "Resultado"):
            vista(app, nombre)
            assert [(n["id"], n["x"], n["y"]) for n in datos_red(app, "nodes")] == [
                (n["id"], n["x"], n["y"]) for n in nodos_originales]
            if nombre == "Recorrido":
                assert app.slider[0].value == 2
    assert texto(app).count("**Peso total:** 21") == 1
    assert texto(app).count("**Aristas del árbol:** 5") == 1
    for etiqueta, valor in (("Vértices", "6"), ("Conexiones / precedencias", "10")):
        metricas = [m for m in app.metric if m.label == etiqueta]
        assert len(metricas) == 1
        assert metricas[0].value == valor
    assert len(app.get("iframe")) == 1
    comprobar_orden_resultado(app)


def test_dijkstra_consultas_sin_ejecutar_ni_mostrar_costo_ficticio():
    app = cargar(contenido=DIRIGIDO)
    widget(app, "Algoritmo").set_value("dijkstra").run(timeout=30)
    widget(app, "Origen de Dijkstra").set_value("A").run(timeout=30)
    iniciar(app)
    with patch.object(Dijkstra, "_resolver", side_effect=AssertionError("No resolver")):
        vista(app, "Resultado")
        assert "Seleccioná un destino" in texto(app)
        for destino, esperado, costo in (("D", "A → B → D", "3"), ("A", "A", "0"),
                                         ("X", "Destino inalcanzable", None)):
            widget(app, "Destino del resultado").set_value(destino).run(timeout=30)
            assert not app.exception
            assert f"**Destino consultado:** {destino}" in texto(app)
            assert esperado in texto(app)
            assert ("**Costo:**" in texto(app)) == (costo is not None)
            if costo is not None:
                assert f"**Costo:** {costo}" in texto(app)
            comprobar_orden_resultado(app)
    assert not app.dataframe


def test_flujo_tabla_todos_los_arcos_capacidad_flujo_ceros_y_paralelas():
    csv = b"origen,destino,peso,dirigida\nS,A,1,true\nS,A,2,true\nA,S,1,true\nA,T,2,true\nS,T,0,true\n"
    app = cargar(contenido=csv)
    widget(app, "Algoritmo").set_value("flujo_maximo").run(timeout=30)
    widget(app, "Fuente del flujo").set_value("S").run(timeout=30)
    widget(app, "Sumidero del flujo").set_value("T").run(timeout=30)
    iniciar(app)
    vista(app, "Resultado")
    tabla = filas(app)
    assert len(tabla) == 5
    assert list(tabla[0]) == ["ID", "Origen", "Destino", "Dirección", "Capacidad", "Flujo"]
    assert [f["ID"] for f in tabla] == [0, 1, 2, 3, 4]
    assert tabla[0]["Origen"] == tabla[1]["Origen"] == tabla[2]["Destino"] == "S"
    assert tabla[1]["Capacidad"] == "2"
    assert tabla[4]["Capacidad"] == tabla[4]["Flujo"] == "0"
    assert tabla[2]["Flujo"] == "0"
    assert all(f["Dirección"] == "Dirigida" for f in tabla)
    assert "**Flujo máximo:** 2" in texto(app)
    assert len(datos_red(app, "edges")) == 5
    comprobar_orden_resultado(app, ("Flujos por arco",))
    widget(app, "Algoritmo").set_value("dijkstra").run(timeout=30)
    assert not app.radio and not app.dataframe
    assert "hu07_resultado" not in app.session_state


@pytest.mark.parametrize("formato,csv", [
    ("CPM", b"actividad,duracion,predecesoras\nA,3,\nB,3,\nC,0,A;B\n"),
    ("PERT", b"actividad,optimista,mas_probable,pesimista,predecesoras\nA,0,3,6,\nB,3,3,3,\nC,0,0,0,A;B\n"),
])
def test_planificacion_tablas_rutas_y_variabilidad_por_ruta(formato, csv):
    app = cargar(formato, csv)
    iniciar(app)
    vista(app, "Resultado")
    assert "**Cantidad de rutas críticas:** 2" in texto(app)
    assert "Ruta 1: A → C" in texto(app)
    assert "Ruta 2: B → C" in texto(app)
    tabla = filas(app)
    for fila in tabla:
        assert all(c in fila for c in ("Actividad", "IC", "TC", "IL", "TL", "Holgura"))
    assert tabla[0]["TC"] == tabla[0]["TL"] == "3"
    assert tabla[0]["Holgura"] == "0"
    assert len(datos_red(app, "nodes")) == 3
    if formato == "PERT":
        comprobar_orden_resultado(app, ("Rutas críticas", "Actividades", "Variabilidad de rutas críticas"))
        assert "**Duración esperada:** 3" in texto(app)
        assert all(c in tabla[0] for c in ("Optimista", "Más probable", "Pesimista", "Tiempo esperado", "Varianza"))
        assert tabla[0]["Tiempo esperado"] == "3"
        assert tabla[0]["Varianza"] == "1"
        variabilidad = filas(app, 1)
        assert [(f["Ruta"], f["Varianza"], f["Desviación estándar"]) for f in variabilidad] == [
            ("A → C", "1", "1"), ("B → C", "0", "0")]
        assert "varianza global" not in texto(app).lower()
    else:
        comprobar_orden_resultado(app, ("Rutas críticas", "Actividades"))
        assert "**Duración total:** 3" in texto(app)


def test_cpm_ruta_unica_y_tabla_de_ejemplo():
    app = cargar("CPM", b"actividad,duracion,predecesoras\nA,2,\nB,3,A\n")
    iniciar(app)
    vista(app, "Resultado")
    assert "Ruta 1: A → B" in texto(app)
    assert "**Duración total:** 5" in texto(app)
    assert filas(app)[1] == {"Actividad": "B", "IC": "2", "TC": "5", "IL": "2", "TL": "5", "Holgura": "0"}


def test_cpm_2_elevado_100_rutas_muestra_solo_diez():
    lineas = ["actividad,duracion,predecesoras"]
    for i in range(200):
        predecesoras = "" if i < 2 else f"V{(i // 2 - 1) * 2};V{(i // 2 - 1) * 2 + 1}"
        lineas.append(f"V{i},1,{predecesoras}")
    app = cargar("CPM", "\n".join(lineas).encode())
    iniciar(app)
    original = RutasCriticas.__iter__
    def limitado(self):
        for indice, ruta in enumerate(original(self)):
            assert indice < 10, "Enumeración ilimitada desde la interfaz"
            yield ruta
    with patch.object(RutasCriticas, "__iter__", limitado):
        vista(app, "Resultado")
    assert sum(m.value.startswith("Ruta ") for m in app.markdown) == 10
    assert any(c.value == f"Mostrando 10 de {2 ** 100} rutas críticas." for c in app.caption)
    assert len(filas(app)) == 200


def test_pert_precision_solo_visual_en_tablas():
    app = cargar("PERT", b"actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,4,9,\nB,6,6,6,A\n")
    iniciar(app)
    resultado = app.session_state["hu07_resultado"]
    antes = repr(resultado)
    vista(app, "Resultado")
    tabla = filas(app)
    assert tabla[0]["Tiempo esperado"] == "4.33"
    assert tabla[0]["Varianza"] == "1.78"
    assert tabla[1]["TC"] == tabla[1]["TL"] == "10.33"
    assert filas(app, 1)[0]["Varianza"] == "1.78"
    assert resultado.solucion.varianzas["A"] == 1.7777777777777777
    assert resultado.solucion.tiempos_esperados["A"] == 4.333333333333333
    assert repr(resultado) == antes


def test_error_real_de_variabilidad_no_oculta_grafo_ni_actividades():
    app = cargar("PERT", b"actividad,optimista,mas_probable,pesimista,predecesoras\nA,0,3e154,6e154,\nB,0,3e154,6e154,A\n")
    iniciar(app)
    vista(app, "Resultado")
    assert "**Duración esperada:**" in texto(app)
    assert "Ruta 1: A → B" in texto(app)
    assert len(filas(app)) == 2
    assert any("A → B" in w.value for w in app.warning)
    assert len(app.dataframe) == 1  # No se inventa una fila de variabilidad.
    assert len(app.get("iframe")) == 1
    assert "hu07_resultado" in app.session_state


def test_error_intermedio_muestra_prefijo_y_rutas_posteriores_no_evaluadas():
    app = cargar("PERT", b"actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,1,1,\nB,1,1,1,\nC,1,1,1,\n")
    iniciar(app)
    primero = next(app.session_state["hu07_resultado"].solucion.variabilidad_rutas())
    def interrumpida(self):
        yield primero
        raise ErrorCalculoNumerico("Desborde controlado")
    with patch.object(SolucionPERT, "variabilidad_rutas", interrumpida):
        vista(app, "Resultado")
    assert len(filas(app)) == 3
    assert len(filas(app, 1)) == 1
    assert filas(app, 1)[0]["Ruta"] == "A"
    advertencias = "\n".join(w.value for w in app.warning)
    assert "ruta B" in advertencias and "Desborde controlado" in advertencias
    assert "generador se interrumpió: C" in advertencias
    assert len(app.get("iframe")) == 1
    app.file_uploader[0].set_value(("invalido.csv", b"actividad\nX\n", "text/csv")).run(timeout=30)
    assert not app.exception
    assert not app.radio and not app.dataframe and not app.warning
    assert "hu07_resultado" not in app.session_state
