"""Adaptación de entradas del proyecto a una visualización PyVis estática."""

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Literal

import networkx as nx
from pyvis.network import Network

from .algoritmo import Entrada
from .grafo import Grafo
from .parametros import EstimacionesPERT, ParametrosCPM, ParametrosPERT


FormatoGrafo = Literal["Conexiones", "CPM", "PERT"]
SEMILLA_LAYOUT = 42
ESCALA_POSICIONES = 1000


@dataclass(frozen=True, slots=True)
class AtributosVertice:
    etiqueta: str
    detalle: str


def atributos_vertices_entrada(
    entrada: Entrada[object], formato: FormatoGrafo
) -> Mapping[str, AtributosVertice]:
    """Proyecta los parámetros originales CPM/PERT sobre sus actividades."""
    if formato == "Conexiones":
        return {
            vertice: AtributosVertice(vertice, f"Vértice {vertice}")
            for vertice in entrada.grafo.vertices
        }

    if formato == "CPM":
        if not isinstance(entrada.parametros, ParametrosCPM):
            raise TypeError("El formato CPM requiere una Entrada con ParametrosCPM.")
        duraciones = entrada.parametros.duraciones
        if set(duraciones) != set(entrada.grafo.vertices):
            raise ValueError("Las duraciones CPM deben corresponder a todos los vértices.")
        return {
            actividad: AtributosVertice(
                f"{actividad}\nDuración: {duraciones[actividad]}",
                f"Actividad {actividad}\nDuración: {duraciones[actividad]}",
            )
            for actividad in entrada.grafo.vertices
        }

    if formato == "PERT":
        if not isinstance(entrada.parametros, ParametrosPERT):
            raise TypeError("El formato PERT requiere una Entrada con ParametrosPERT.")
        estimaciones = entrada.parametros.estimaciones
        if set(estimaciones) != set(entrada.grafo.vertices):
            raise ValueError("Las estimaciones PERT deben corresponder a todos los vértices.")
        return {
            actividad: _atributos_pert(actividad, estimaciones[actividad])
            for actividad in entrada.grafo.vertices
        }

    raise ValueError(f"Formato desconocido: {formato}")


def _atributos_pert(actividad: str, estimaciones: EstimacionesPERT) -> AtributosVertice:
    optimista = estimaciones.optimista
    probable = estimaciones.mas_probable
    pesimista = estimaciones.pesimista
    return AtributosVertice(
        f"{actividad}\nO: {optimista} | M: {probable} | P: {pesimista}",
        (
            f"Actividad {actividad}\n"
            f"Optimista: {optimista}\n"
            f"Más probable: {probable}\n"
            f"Pesimista: {pesimista}"
        ),
    )


class VisualizadorPyVis:
    """Construye una red PyVis desde una Entrada; no carga archivos ni resuelve."""

    def __init__(self, semilla: int = SEMILLA_LAYOUT, escala: int = ESCALA_POSICIONES):
        self.semilla = semilla
        self.escala = escala

    def calcular_posiciones(self, grafo: Grafo) -> dict[str, tuple[float, float]]:
        """Calcula coordenadas deterministas sin alterar el modelo original."""
        topologia = nx.Graph()
        topologia.add_nodes_from(grafo.vertices)
        topologia.add_edges_from(
            (arista.origen, arista.destino) for arista in grafo.aristas
        )
        posiciones = nx.spring_layout(topologia, seed=self.semilla)
        return {
            vertice: (
                float(coordenadas[0]) * self.escala,
                float(coordenadas[1]) * self.escala,
            )
            for vertice, coordenadas in posiciones.items()
        }

    def construir_red(
        self,
        entrada: Entrada[object],
        formato: FormatoGrafo,
        arista_seleccionada: int | None = None,
    ) -> Network:
        grafo = entrada.grafo
        atributos = atributos_vertices_entrada(entrada, formato)
        posiciones = self.calcular_posiciones(grafo)
        red = Network(
            height="700px",
            width="100%",
            # Permite asignar flechas individualmente en grafos de dirección mixta.
            directed=True,
            cdn_resources="in_line",
        )

        for vertice in grafo.vertices:
            x, y = posiciones[vertice]
            datos = atributos[vertice]
            red.add_node(
                vertice,
                label=datos.etiqueta,
                title=datos.detalle,
                x=x,
                y=y,
                fixed=True,
            )

        for arista in grafo.aristas:
            seleccionada = arista.identificador == arista_seleccionada
            if formato == "Conexiones":
                direccion = "dirigida" if arista.dirigida else "no dirigida"
                peso = "sin peso" if arista.peso is None else f"peso {arista.peso}"
                titulo = (
                    f"Arista {arista.identificador}: {arista.origen} → {arista.destino}; "
                    f"{direccion}; {peso}"
                )
            else:
                titulo = (
                    f"Precedencia {arista.identificador}: "
                    f"{arista.origen} → {arista.destino}; sin peso"
                )

            red.add_edge(
                arista.origen,
                arista.destino,
                id=f"arista-{arista.identificador}",
                label="",
                title=titulo,
                arrows="to" if arista.dirigida else "",
                color={
                    "color": "#e76f00" if seleccionada else "#8492a6",
                    "opacity": 1.0 if seleccionada else 0.35,
                },
                width=2.5 if seleccionada else 0.8,
            )

        red.set_options(
            json.dumps(
                {
                    "physics": {"enabled": False},
                    "layout": {"randomSeed": self.semilla},
                    "interaction": {
                        "hover": True,
                        "navigationButtons": True,
                        "dragNodes": False,
                        "dragView": True,
                        "zoomView": True,
                    },
                    "edges": {"smooth": {"enabled": False}},
                }
            )
        )
        return red

    def mostrar_grafo(
        self,
        entrada: Entrada[object],
        formato: FormatoGrafo,
        arista_seleccionada: int | None = None,
    ) -> None:
        """Muestra el grafo original en Streamlit, sin ejecutar algoritmos."""
        import streamlit as st

        red = self.construir_red(entrada, formato, arista_seleccionada)
        st.iframe(red.generate_html(), height=730, tab_index=0)
