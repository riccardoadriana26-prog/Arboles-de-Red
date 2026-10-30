"""POC de posiciones estables con Streamlit, NetworkX y PyVis."""

from itertools import combinations

import networkx as nx
import streamlit as st
from pyvis.network import Network

from arboles_de_red.grafo import Arista, Grafo


CANTIDAD_VERTICES = 200
CANTIDAD_ARISTAS = 890
SEMILLA_LAYOUT = 42
ESCALA_POSICIONES = 1000


def construir_grafo_prueba() -> Grafo:
    """Construye un grafo conexo no dirigido, reproducible, de 200/890."""
    vertices = tuple(f"V{i}" for i in range(CANTIDAD_VERTICES))

    # La cadena garantiza conectividad. Luego se agregan pares en orden
    # determinista hasta completar las 890 aristas.
    pares = [(vertices[i], vertices[i + 1]) for i in range(CANTIDAD_VERTICES - 1)]
    pares_existentes = set(pares)
    for origen, destino in combinations(vertices, 2):
        if (origen, destino) in pares_existentes:
            continue
        pares.append((origen, destino))
        pares_existentes.add((origen, destino))
        if len(pares) == CANTIDAD_ARISTAS:
            break

    aristas = tuple(
        Arista(identificador, origen, destino, 1.0, False)
        for identificador, (origen, destino) in enumerate(pares)
    )
    return Grafo(vertices, aristas)


def calcular_posiciones(grafo: Grafo) -> dict[str, tuple[float, float]]:
    """Calcula posiciones fijas; la dirección no afecta el layout físico."""
    topologia = nx.Graph()
    topologia.add_nodes_from(grafo.vertices)
    topologia.add_edges_from((arista.origen, arista.destino) for arista in grafo.aristas)

    posiciones_crudas = nx.spring_layout(topologia, seed=SEMILLA_LAYOUT)
    return {
        vertice: (
            float(coordenadas[0]) * ESCALA_POSICIONES,
            float(coordenadas[1]) * ESCALA_POSICIONES,
        )
        for vertice, coordenadas in posiciones_crudas.items()
    }


def crear_visualizacion(
    grafo: Grafo,
    posiciones: dict[str, tuple[float, float]],
    arista_seleccionada: int | None = None,
) -> Network:
    """Adapta el modelo al formato PyVis sin descartar aristas."""
    visualizacion = Network(
        height="700px",
        width="100%",
        # Se habilita el modo dirigido del contenedor para poder configurar
        # flechas individualmente y conservar también las aristas no dirigidas.
        directed=True,
        cdn_resources="in_line",
    )

    for vertice in grafo.vertices:
        x, y = posiciones[vertice]
        visualizacion.add_node(
            vertice,
            label=vertice,
            title=f"Vértice {vertice}",
            x=x,
            y=y,
            fixed=True,
        )

    for arista in grafo.aristas:
        detalle_peso = "sin peso" if arista.peso is None else f"peso {arista.peso}"
        seleccionada = arista.identificador == arista_seleccionada
        visualizacion.add_edge(
            arista.origen,
            arista.destino,
            id=f"arista-{arista.identificador}",
            label="",
            title=(
                f"Arista {arista.identificador}: {arista.origen} — {arista.destino}; "
                f"{detalle_peso}"
            ),
            arrows="to" if arista.dirigida else "",
            color={
                "color": "#e76f00" if seleccionada else "#8492a6",
                "opacity": 1.0 if seleccionada else 0.35,
            },
            width=2.5 if seleccionada else 0.8,
        )

    visualizacion.set_options(
        """
        {
          "physics": {"enabled": false},
          "interaction": {
            "hover": true,
            "navigationButtons": true,
            "dragNodes": false,
            "dragView": true,
            "zoomView": true
          },
          "edges": {"smooth": {"enabled": false}}
        }
        """
    )
    return visualizacion


st.set_page_config(page_title="POC estática de grafos", layout="wide")
st.title("POC: posiciones estables con NetworkX + PyVis")
st.caption(
    "NetworkX calcula una distribución reproducible en Python. "
    "PyVis recibe coordenadas fijas y mantiene desactivada su física."
)

grafo = construir_grafo_prueba()
posiciones = calcular_posiciones(grafo)

aristas_por_id = {arista.identificador: arista for arista in grafo.aristas}
arista_seleccionada = st.selectbox(
    "Arista a consultar",
    options=tuple(aristas_por_id),
    format_func=lambda identificador: (
        f"{identificador}: {aristas_por_id[identificador].origen} — "
        f"{aristas_por_id[identificador].destino}"
    ),
)
visualizacion = crear_visualizacion(grafo, posiciones, arista_seleccionada)

columna_nodos, columna_aristas, columna_semilla = st.columns(3)
columna_nodos.metric("Vértices", len(grafo.vertices))
columna_aristas.metric("Aristas", len(grafo.aristas))
columna_semilla.metric("Semilla de distribución", SEMILLA_LAYOUT)

arista = aristas_por_id[arista_seleccionada]
st.subheader("Conexión seleccionada")
columna_id, columna_origen, columna_destino, columna_direccion, columna_peso = st.columns(5)
columna_id.metric("Identificador", arista.identificador)
columna_origen.metric("Origen", arista.origen)
columna_destino.metric("Destino", arista.destino)
columna_direccion.metric(
    "Dirección", "Dirigida" if arista.dirigida else "No dirigida"
)
columna_peso.metric(
    "Peso", "Sin peso" if arista.peso is None else str(arista.peso)
)

st.iframe(visualizacion.generate_html(), height=730, tab_index=0)
