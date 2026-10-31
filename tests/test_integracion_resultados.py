"""Integración real de las tres vistas sobre una única ejecución guardada."""

import json
from pathlib import Path
import re
from unittest.mock import patch

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("pyvis")
from streamlit.testing.v1 import AppTest

from arboles_de_red.algoritmo import Resultado
from arboles_de_red.arbol_expansion import Prim
from arboles_de_red.csv import ProcesadorConexionesCSV
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.reconstruccion import ReconstruccionEjecucion
from arboles_de_red.visualizador_pyvis import VisualizadorPyVis


RAIZ = Path(__file__).resolve().parents[1]
DIRIGIDO = b"origen,destino,peso,dirigida\nA,B,1,true\nA,C,5,true\nB,D,2,true\nC,D,1,true\nX,Y,1,true\n"


def widget(app, etiqueta):
    return next(w for w in app.selectbox if w.label == etiqueta)


def cargar(formato="Conexiones", contenido=None):
    app = AppTest.from_file(str(RAIZ / "poc_streamlit_estatica.py")).run(timeout=30)
    widget(app, "Formato").set_value(formato).run(timeout=30)
    contenido = contenido or (RAIZ / "ejemplos/conexiones_mst.csv").read_bytes()
    app.file_uploader[0].upload("red.csv", contenido, "text/csv").run(timeout=30)
    assert not app.exception
    return app


def iniciar(app):
    next(b for b in app.button if b.label == "Iniciar").click().run(timeout=30)
    assert not app.exception
    assert "hu07_resultado" in app.session_state


def vista(app, nombre):
    app.radio[0].set_value(nombre).run(timeout=30)
    assert not app.exception
    assert not app.error


def datos_red(app, variable):
    html = app.get("iframe")[0].proto.srcdoc
    return json.loads(re.search(rf"{variable} = new vis.DataSet\((\[.*?\])\);", html).group(1))


def texto(app):
    return "\n".join(m.value for m in app.markdown)


def test_tres_vistas_no_reprocesan_no_resuelven_y_conservan_paso_y_posiciones():
    app = cargar()
    iniciar(app)
    assert app.radio[0].options == ["Datos originales", "Recorrido", "Resultado"]
    app.slider[0].set_value(2).run(timeout=30)
    original = repr((app.session_state["hu07_entrada"], app.session_state["hu07_resultado"]))
    posiciones = dict(app.session_state["hu07_posiciones_ejecucion"])
    with patch.object(Prim, "_resolver", side_effect=AssertionError("reejecución")), \
         patch.object(ProcesadorConexionesCSV, "preparar_entrada", side_effect=AssertionError("reprocesamiento")), \
         patch.object(VisualizadorPyVis, "calcular_posiciones", side_effect=AssertionError("layout")):
        for nombre in ("Datos originales", "Resultado", "Recorrido", "Resultado", "Recorrido"):
            vista(app, nombre)
            nodos = datos_red(app, "nodes")
            assert {n["id"]: (n["x"], n["y"]) for n in nodos} == posiciones
            assert all(n["fixed"] for n in nodos)
            if nombre == "Datos originales":
                assert all("Solución final" not in n["title"] for n in nodos)
                assert all("Elegida en este paso" not in a["title"] for a in datos_red(app, "edges"))
            if nombre == "Recorrido":
                assert app.slider[0].value == 2
                assert next(m for m in app.metric if m.label == "Paso").value.startswith("2 /")
                assert any(s.value.startswith("Paso 2 ") for s in app.subheader)
        assert repr((app.session_state["hu07_entrada"], app.session_state["hu07_resultado"])) == original


@pytest.mark.parametrize("algoritmo,formato,archivo,parametros,campo", [
    ("prim", "Conexiones", "conexiones_mst.csv", {}, "Peso total"),
    ("kruskal", "Conexiones", "conexiones_mst.csv", {}, "Peso total"),
    ("dijkstra", "Conexiones", "conexiones_dijkstra.csv", {"Origen de Dijkstra": "A", "Destino (opcional)": "F"}, "Costo"),
    ("flujo_maximo", "Conexiones", "conexiones_flujo.csv", {"Fuente del flujo": "S", "Sumidero del flujo": "T"}, "Flujo máximo"),
    ("cpm", "CPM", "cpm.csv", {}, "Duración total"),
    ("pert", "PERT", "pert.csv", {}, "Duración esperada"),
])
def test_resultado_real_de_los_seis_algoritmos(algoritmo, formato, archivo, parametros, campo):
    app = cargar(formato, (RAIZ / "ejemplos" / archivo).read_bytes())
    widget(app, "Algoritmo").set_value(algoritmo).run(timeout=30)
    for etiqueta, valor in parametros.items():
        widget(app, etiqueta).set_value(valor).run(timeout=30)
    iniciar(app)
    with patch.object(ReconstruccionEjecucion, "estado_en", side_effect=AssertionError("dependencia del recorrido")):
        vista(app, "Resultado")
    assert f"**{campo}:**" in texto(app)
    p = app.session_state["hu08_proyeccion"]
    aristas = datos_red(app, "edges")
    assert len(aristas) == len(app.session_state["hu07_entrada"].grafo.aristas)
    assert not any(str(a["id"]).startswith("residual-inverso") for a in aristas)
    if algoritmo in ("prim", "kruskal", "dijkstra", "cpm", "pert"):
        esperadas = (set(p.aristas) if algoritmo in ("prim", "kruskal") else
                     set(p.aristas_ruta) if algoritmo == "dijkstra" else set(p.aristas_criticas))
        assert {a["id"] for a in aristas if a["width"] == 3} == {f"arista-{i}" for i in esperadas}
    else:
        assert all("Capacidad original:" in a["title"] and "Flujo final:" in a["title"] for a in aristas)
    if algoritmo == "dijkstra":
        assert not any(w.label == "Destino del resultado" for w in app.selectbox)


def test_dijkstra_consulta_destinos_sin_reejecutar_incluye_inalcanzable_y_trivial():
    app = cargar(contenido=DIRIGIDO)
    widget(app, "Algoritmo").set_value("dijkstra").run(timeout=30)
    widget(app, "Origen de Dijkstra").set_value("A").run(timeout=30)
    iniciar(app)
    with patch.object(Dijkstra, "_resolver", side_effect=AssertionError("reejecución")):
        vista(app, "Resultado")
        for destino, ruta, costo in (("D", "A → B → D", "3"), ("C", "A → C", "5"),
                                     ("X", "Destino inalcanzable", None), ("A", "A", "0")):
            widget(app, "Destino del resultado").set_value(destino).run(timeout=30)
            assert not app.exception
            assert ruta in texto(app)
            if costo is None:
                assert "**Costo:**" not in texto(app)
            else:
                assert f"**Costo:** {costo}" in texto(app)
        vista(app, "Recorrido")
        vista(app, "Resultado")
        assert widget(app, "Destino del resultado").value == "A"
        assert app.session_state["hu08_proyeccion"].destino is None


def test_resultado_sin_pasos_no_fabrica_eventos():
    resolver = Prim._resolver
    def sin_pasos(self, entrada):
        return Resultado(resolver(self, entrada).solucion, ())
    app = cargar()
    with patch.object(Prim, "_resolver", sin_pasos):
        iniciar(app)
    assert not app.slider
    assert app.session_state["hu07_resultado"].pasos == ()
    vista(app, "Resultado")
    assert "**Peso total:**" in texto(app)


@pytest.mark.parametrize("cambio", ["archivo", "invalido", "formato", "algoritmo", "origen", "destino", "fuente", "sumidero"])
def test_invalida_tambien_presentacion_hu08(cambio):
    flujo = cambio in ("fuente", "sumidero")
    dijkstra = cambio in ("origen", "destino")
    app = cargar(contenido=DIRIGIDO if flujo or dijkstra else None)
    if flujo or dijkstra:
        widget(app, "Algoritmo").set_value("flujo_maximo" if flujo else "dijkstra").run(timeout=30)
        widget(app, "Fuente del flujo" if flujo else "Origen de Dijkstra").set_value("A").run(timeout=30)
        if flujo:
            widget(app, "Sumidero del flujo").set_value("D").run(timeout=30)
    iniciar(app)
    vista(app, "Resultado")
    assert "hu08_proyeccion" in app.session_state
    if cambio in ("archivo", "invalido"):
        contenido = DIRIGIDO if cambio == "archivo" else b"origen,destino\nA,B\n"
        app.file_uploader[0].set_value(("nuevo.csv", contenido, "text/csv")).run(timeout=30)
    else:
        etiqueta, valor = {"formato": ("Formato", "CPM"), "algoritmo": ("Algoritmo", "kruskal"),
                           "origen": ("Origen de Dijkstra", "B"), "destino": ("Destino (opcional)", "D"),
                           "fuente": ("Fuente del flujo", "B"), "sumidero": ("Sumidero del flujo", "C")}[cambio]
        widget(app, etiqueta).set_value(valor).run(timeout=30)
    assert not app.exception
    assert "hu07_resultado" not in app.session_state
    assert "hu08_proyeccion" not in app.session_state
    assert "hu08_destino" not in app.session_state
    assert not app.radio
