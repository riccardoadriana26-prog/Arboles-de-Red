"""Adaptación de entradas del proyecto a una visualización PyVis estática."""

from collections.abc import Mapping
from dataclasses import dataclass
import json
from typing import Literal

import networkx as nx
from pyvis.network import Network

from .algoritmo import Entrada
from .grafo import Grafo
from .formato_visual import formatear_numero
from .parametros import EstimacionesPERT, ParametrosCPM, ParametrosPERT
from .reconstruccion import (
    EstadoDijkstra,
    EstadoExpansion,
    EstadoFlujoResidual,
    EstadoPERT,
    EstadoPlanificacion,
    EstadoVisualPaso,
)


FormatoGrafo = Literal["Conexiones", "CPM", "PERT"]
SEMILLA_LAYOUT = 42
ESCALA_POSICIONES = 1000

# El ID pertenece a la plantilla incluida por PyVis. La especificidad del ID
# permite anular los PNG y sombras de vis-network sin afectar el lienzo.
_CSS_NAVEGACION = """
#mynetwork .vis-navigation .vis-button {
    background: #17191d;
    border: 1px solid #454b55;
    border-radius: 50%;
    box-sizing: border-box;
    color: #f1f3f5;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    font: 500 22px/1 "Segoe UI Symbol", Arial, sans-serif;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    transition: background-color 120ms ease, border-color 120ms ease,
                box-shadow 120ms ease, transform 120ms ease;
}
#mynetwork .vis-navigation .vis-button::before {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 1em;
    height: 1em;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    pointer-events: none;
}
#mynetwork .vis-navigation .vis-button.vis-up::before { content: "↑"; }
#mynetwork .vis-navigation .vis-button.vis-down::before { content: "↓"; }
#mynetwork .vis-navigation .vis-button.vis-left::before { content: "←"; }
#mynetwork .vis-navigation .vis-button.vis-right::before { content: "→"; }
#mynetwork .vis-navigation .vis-button.vis-zoomIn::before { content: "+"; }
#mynetwork .vis-navigation .vis-button.vis-zoomOut::before { content: "−"; }
#mynetwork .vis-navigation .vis-button.vis-zoomExtends::before { content: "⤢"; }
#mynetwork .vis-navigation .vis-button:hover {
    background-color: #2c3139;
    border-color: #8793a2;
    box-shadow: 0 0 0 2px rgba(241, 243, 245, 0.15);
}
#mynetwork .vis-navigation .vis-button:active {
    background-color: #414a57;
    border-color: #bec8d5;
    box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.5);
    transform: scale(0.95);
}
"""


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
                f"{actividad}\nDuración: {formatear_numero(duraciones[actividad])}",
                f"Actividad {actividad}\nDuración: {formatear_numero(duraciones[actividad])}",
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
    optimista = formatear_numero(estimaciones.optimista)
    probable = formatear_numero(estimaciones.mas_probable)
    pesimista = formatear_numero(estimaciones.pesimista)
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
        posiciones: Mapping[str, tuple[float, float]] | None = None,
        estado: EstadoVisualPaso | None = None,
    ) -> Network:
        grafo = entrada.grafo
        atributos = atributos_vertices_entrada(entrada, formato)
        posiciones = self.calcular_posiciones(grafo) if posiciones is None else dict(posiciones)
        if set(posiciones) != set(grafo.vertices):
            raise ValueError("Las posiciones deben corresponder exactamente a los vértices del grafo.")
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
            etiqueta, titulo = self._atributos_vertice_estado(vertice, datos, estado)
            color_nodo = self._color_vertice(vertice, estado)
            red.add_node(
                vertice,
                label=etiqueta,
                title=titulo,
                x=x,
                y=y,
                fixed=True,
                color=color_nodo,
            )

        for arista in grafo.aristas:
            titulo = self._titulo_arista(arista, formato, estado)
            color, ancho = self._estilo_arista(arista.identificador, arista_seleccionada, estado)

            red.add_edge(
                arista.origen,
                arista.destino,
                id=f"arista-{arista.identificador}",
                label="",
                title=titulo,
                arrows="to" if arista.dirigida else "",
                color={"color": color, "opacity": 0.95 if ancho > 1 else 0.45},
                width=ancho,
            )

        if estado is not None and isinstance(estado.estado, EstadoFlujoResidual):
            self._agregar_arcos_inversos(red, entrada, estado.estado)

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

    def _atributos_vertice_estado(self, vertice, datos, estado):
        if estado is None:
            return datos.etiqueta, datos.detalle
        payload = estado.estado
        detalle = payload.planificacion if isinstance(payload, EstadoPERT) else payload
        lineas = [datos.detalle]
        etiqueta = datos.etiqueta
        if isinstance(payload, EstadoDijkstra):
            distancia = self._numero(payload.distancias[vertice])
            predecesor = payload.predecesores.get(vertice)
            texto_predecesor = "ninguno" if predecesor is None else f"{predecesor[0]} (arista #{predecesor[1]})"
            etiqueta += f"\nd: {distancia}"
            lineas.extend((f"Distancia: {distancia}", f"Predecesor: {texto_predecesor}"))
        elif isinstance(payload, EstadoFlujoResidual):
            if vertice in payload.lado_fuente:
                lineas.append("Lado fuente del corte mínimo")
        if isinstance(payload, EstadoPERT):
            if vertice in payload.tiempos_esperados:
                esperado = formatear_numero(payload.tiempos_esperados[vertice])
                varianza = formatear_numero(payload.varianzas[vertice])
                etiqueta += f"\nE: {esperado} | Var: {varianza}"
                lineas.extend((f"Tiempo esperado: {esperado}", f"Varianza: {varianza}"))
        if isinstance(detalle, EstadoPlanificacion):
            valores = detalle.valores_por_actividad[vertice]
            pares = (("IC", valores.ic), ("TC", valores.tc), ("IL", valores.il),
                     ("TL", valores.tl), ("Holgura", valores.holgura))
            calculados = [f"{nombre}: {formatear_numero(valor)}" for nombre, valor in pares if valor is not None]
            if calculados:
                etiqueta += "\n" + " | ".join(f"{nombre}={formatear_numero(valor)}" for nombre, valor in pares if valor is not None)
                lineas.extend(calculados)
        return etiqueta, "\n".join(lineas)

    @staticmethod
    def _numero(valor):
        if valor == float("inf"):
            return "∞"
        if valor == float("-inf"):
            return "−∞"
        return str(valor)

    @staticmethod
    def _color_vertice(vertice, estado):
        if estado is None:
            return "#97c2fc"
        payload = estado.estado
        if isinstance(payload, EstadoExpansion):
            if vertice in payload.vertices_arbol:
                return "#79c99e"
        if isinstance(payload, EstadoDijkstra):
            if vertice == payload.vertice_actual:
                return "#ffca58"
            if vertice in payload.permanentes:
                return "#79c99e"
        if isinstance(payload, EstadoPERT):
            if vertice in payload.planificacion.actividades_criticas:
                return "#ff9b85"
        if isinstance(payload, EstadoPlanificacion) and vertice in payload.actividades_criticas:
            return "#ff9b85"
        if vertice in estado.vertices_destacados:
            return "#ffca58"
        return "#97c2fc"

    def _titulo_arista(self, arista, formato, estado):
        identificador = arista.identificador
        if formato == "Conexiones":
            direccion = "dirigida" if arista.dirigida else "no dirigida"
            peso = "sin peso" if arista.peso is None else f"peso {arista.peso}"
            lineas = [f"Arista {identificador}: {arista.origen} → {arista.destino}; {direccion}; {peso}"]
        else:
            lineas = [f"Precedencia {identificador}: {arista.origen} → {arista.destino}; sin peso"]
        if estado is not None:
            payload = estado.estado
            if isinstance(payload, EstadoDijkstra):
                predecesores = [v for v, par in payload.predecesores.items() if par[1] == identificador]
                if predecesores:
                    lineas.append(f"Arista predecesora de: {', '.join(predecesores)}")
                if payload.arista_actual == identificador:
                    lineas.append(f"Acción actual: {payload.accion}; d({payload.vertice_actual})={self._numero(payload.distancia_nueva)}")
            elif isinstance(payload, EstadoExpansion):
                if identificador in payload.aristas_arbol:
                    lineas.append("Aceptada e incorporada al árbol")
                if identificador in payload.aristas_evaluadas:
                    lineas.append("Evaluada en la ronda actual" if payload.algoritmo == "Prim" else "Evaluada en este paso")
                if identificador in payload.aristas_rechazadas_ciclo:
                    lineas.append("Rechazada por ciclo")
                if identificador == payload.arista_elegida and (
                    payload.algoritmo == "Prim" or identificador not in payload.aristas_rechazadas_ciclo
                ):
                    lineas.append("Elegida en este paso")
            elif isinstance(payload, EstadoFlujoResidual):
                flujo = payload.flujo_por_arco[identificador]
                residual = payload.capacidades_residuales[(identificador, False)]
                lineas.extend((f"Flujo: {flujo}", f"Residual directo: {residual}"))
            elif isinstance(payload, EstadoPERT):
                if identificador in payload.planificacion.aristas_criticas:
                    lineas.append("Precedencia crítica")
            elif isinstance(payload, EstadoPlanificacion) and identificador in payload.aristas_criticas:
                lineas.append("Precedencia crítica")
        return "\n".join(lineas)

    @staticmethod
    def _estilo_arista(identificador, seleccionada, estado):
        color, ancho = ("#e76f00", 2.5) if identificador == seleccionada else ("#8492a6", 0.8)
        if estado is None:
            return color, ancho
        payload = estado.estado
        if isinstance(payload, EstadoExpansion):
            if identificador in payload.aristas_arbol:
                color, ancho = "#198754", 3.0
            if identificador in payload.aristas_evaluadas:
                color, ancho = "#f0a202", 2.2
            if identificador in payload.aristas_rechazadas_ciclo:
                color, ancho = "#dc3545", 2.2
            if identificador == payload.arista_elegida and (
                payload.algoritmo == "Prim" or identificador not in payload.aristas_rechazadas_ciclo
            ):
                color, ancho = "#00a86b", 4.0
        elif isinstance(payload, EstadoDijkstra):
            if any(par[1] == identificador for par in payload.predecesores.values()):
                color, ancho = "#2a9d8f", 2.6
            if payload.arista_actual == identificador:
                color, ancho = "#e76f00", 3.5
        elif isinstance(payload, EstadoFlujoResidual):
            tramos = [t for t in payload.camino if t.arista == identificador]
            if tramos:
                color, ancho = ("#9b2226", 4.0) if any(t.inverso for t in tramos) else ("#198754", 4.0)
        else:
            criticas = payload.planificacion.aristas_criticas if isinstance(payload, EstadoPERT) else payload.aristas_criticas
            if identificador in criticas:
                color, ancho = "#dc3545", 3.0
            # Prioridad: precedencia del evento actual > crítica > normal.
            if identificador in estado.aristas_destacadas:
                color, ancho = "#e76f00", 3.5
        return color, ancho

    @staticmethod
    def _agregar_arcos_inversos(red, entrada, estado):
        aristas = {a.identificador: a for a in entrada.grafo.aristas}
        tramo_inverso = {t.arista for t in estado.camino if t.inverso}
        for identificador, arista in aristas.items():
            capacidad = estado.capacidades_residuales[(identificador, True)]
            activo = identificador in tramo_inverso
            if capacidad <= 0 and not activo:
                continue
            situacion = "Utilizado en el camino actual" if activo else "Disponible después del paso"
            if activo and capacidad <= 0:
                situacion += "; agotado después del aumento"
            red.add_edge(
                arista.destino, arista.origen,
                id=f"residual-inverso-{identificador}",
                label="",
                title=(f"Arco residual inverso de arista original #{identificador}: "
                       f"{arista.destino} → {arista.origen}; capacidad residual {capacidad}; "
                       f"flujo original {estado.flujo_por_arco[identificador]}; {situacion}"),
                arrows="to",
                dashes=True,
                color={"color": "#9b2226" if activo else "#7b2cbf", "opacity": 0.9},
                width=3.5 if activo else 1.4,
            )

    def generar_html(self, red: Network) -> str:
        """Añade exclusivamente CSS para los controles nativos al documento PyVis."""
        html = red.generate_html()
        if "</head>" not in html:
            raise ValueError("El HTML de PyVis no contiene el cierre de head para los estilos de navegación.")
        estilo = f'<style id="estilo-navegacion-pyvis">{_CSS_NAVEGACION}</style>'
        return html.replace("</head>", f"{estilo}\n</head>", 1)

    def mostrar_grafo(
        self,
        entrada: Entrada[object],
        formato: FormatoGrafo,
        arista_seleccionada: int | None = None,
        posiciones: Mapping[str, tuple[float, float]] | None = None,
        estado: EstadoVisualPaso | None = None,
    ) -> None:
        """Muestra el grafo original en Streamlit, sin ejecutar algoritmos."""
        import streamlit as st

        red = self.construir_red(entrada, formato, arista_seleccionada, posiciones, estado)
        st.iframe(self.generar_html(red), height=730, tab_index=0)
