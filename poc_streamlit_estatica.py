"""Interfaz para visualizar CSV reales de Conexiones, CPM o PERT."""

import streamlit as st

from arboles_de_red.csv import (
    ProcesadorCPMCSV,
    ProcesadorConexionesCSV,
    ProcesadorPERTCSV,
)
from arboles_de_red.validacion_csv import ErrorValidacionCSV
from arboles_de_red.visualizador_pyvis import FormatoGrafo, VisualizadorPyVis


st.set_page_config(page_title="Visualizador de grafos", layout="wide")
st.title("Visualización del grafo original")
st.caption("Cargá un CSV para inspeccionar sus datos antes de ejecutar un algoritmo.")

formato: FormatoGrafo = st.selectbox("Formato", ("Conexiones", "CPM", "PERT"))
archivo = st.file_uploader("Archivo CSV", type=("csv",))

if archivo is None:
    st.info("Seleccioná un CSV de Conexiones, CPM o PERT para visualizarlo.")
    st.stop()

try:
    contenido = archivo.getvalue().decode("utf-8-sig")
except UnicodeDecodeError:
    st.error("El archivo debe estar codificado como UTF-8.")
    st.stop()

procesadores = {
    "Conexiones": ProcesadorConexionesCSV,
    "CPM": ProcesadorCPMCSV,
    "PERT": ProcesadorPERTCSV,
}
try:
    entrada = procesadores[formato]().preparar_entrada(contenido)
except ErrorValidacionCSV as error:
    st.error(str(error))
    st.stop()

grafo = entrada.grafo
st.caption(f"Archivo: {archivo.name}")
col_nodos, col_aristas = st.columns(2)
col_nodos.metric("Vértices", len(grafo.vertices))
col_aristas.metric("Conexiones / precedencias", len(grafo.aristas))

if grafo.aristas:
    aristas_por_id = {arista.identificador: arista for arista in grafo.aristas}
    arista_seleccionada = st.selectbox(
        "Consultar una conexión",
        tuple(aristas_por_id),
        format_func=lambda identificador: (
            f"#{identificador}: {aristas_por_id[identificador].origen} "
            f"{'→' if aristas_por_id[identificador].dirigida else '—'} "
            f"{aristas_por_id[identificador].destino}; "
            + (
                "sin peso"
                if aristas_por_id[identificador].peso is None
                else f"peso {aristas_por_id[identificador].peso}"
            )
        ),
    )
    seleccionada = aristas_por_id[arista_seleccionada]
    campos = st.columns(5)
    campos[0].metric("Identificador", seleccionada.identificador)
    campos[1].metric("Origen", seleccionada.origen)
    campos[2].metric("Destino", seleccionada.destino)
    campos[3].metric(
        "Dirección", "Dirigida" if seleccionada.dirigida else "No dirigida"
    )
    campos[4].metric(
        "Peso", "Sin peso" if seleccionada.peso is None else str(seleccionada.peso)
    )
else:
    arista_seleccionada = None
    st.info("El archivo contiene vértices, pero no conexiones ni precedencias.")

VisualizadorPyVis().mostrar_grafo(entrada, formato, arista_seleccionada)
