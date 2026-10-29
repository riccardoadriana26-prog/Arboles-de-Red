"""Condiciones propias de los algoritmos de redes, sin calcular sus soluciones."""

from collections.abc import Mapping
from decimal import Decimal
from math import isfinite
from numbers import Real
from operator import ge

from .algoritmo import AlgoritmoNoAplicableError, CondicionesAplicacion, Entrada
from .grafo import Grafo
from .parametros import (
    EstimacionesPERT,
    ParametrosCPM,
    ParametrosDijkstra,
    ParametrosFlujoMaximo,
    ParametrosPERT,
)


def _alcanzables(grafo: Grafo, origen: str) -> set[str]:
    adyacentes: dict[str, list[str]] = {vertice: [] for vertice in grafo.vertices}
    for arista in grafo.aristas:
        adyacentes[arista.origen].append(arista.destino)
        if not arista.dirigida:
            adyacentes[arista.destino].append(arista.origen)
    visitados = {origen}
    pendientes = [origen]
    while pendientes:
        for vecino in adyacentes[pendientes.pop()]:
            if vecino not in visitados:
                visitados.add(vecino)
                pendientes.append(vecino)
    return visitados


def _motivo_pesos_no_negativos(grafo: Grafo) -> str | None:
    for arista in grafo.aristas:
        if arista.peso is None:
            return f"Falta el peso o capacidad de la arista {arista.identificador}."
        if arista.peso < 0:
            return f"El peso o capacidad de la arista {arista.identificador} es negativo."
    return None


def _motivo_red_aon(grafo: Grafo) -> str | None:
    if not grafo.vertices:
        return "El grafo de actividades está vacío."
    if any(not arista.dirigida for arista in grafo.aristas):
        return "La red AON debe ser dirigida."
    grados = dict.fromkeys(grafo.vertices, 0)
    sucesoras: dict[str, list[str]] = {v: [] for v in grafo.vertices}
    for arista in grafo.aristas:
        grados[arista.destino] += 1
        sucesoras[arista.origen].append(arista.destino)
    pendientes = [v for v in grafo.vertices if grados[v] == 0]
    procesadas = 0
    while pendientes:
        actividad = pendientes.pop()
        procesadas += 1
        for sucesora in sucesoras[actividad]:
            grados[sucesora] -= 1
            if grados[sucesora] == 0:
                pendientes.append(sucesora)
    if procesadas != len(grafo.vertices):
        return "La red AON contiene ciclos."
    return None


def _motivo_datos_actividades(grafo: Grafo, datos: Mapping[str, object]) -> str | None:
    faltantes = [v for v in grafo.vertices if v not in datos]
    if faltantes:
        return f"Faltan datos por actividad para: {', '.join(faltantes)}."
    vertices = set(grafo.vertices)
    extras = [str(v) for v in datos if v not in vertices]
    if extras:
        return f"Hay datos de actividades inexistentes: {', '.join(extras)}."
    return None


def _es_tiempo_valido(valor: object) -> bool:
    if isinstance(valor, bool) or not isinstance(valor, (Real, Decimal)):
        return False
    try:
        return isfinite(float(valor)) and bool(ge(valor, 0))
    except (OverflowError, ValueError):
        return False


class CondicionesArbolExpansion(CondicionesAplicacion[None]):
    """Condiciones compartidas por Prim y Kruskal."""

    def motivo_inaplicabilidad(self, entrada: Entrada[None]) -> str | None:
        grafo = entrada.grafo
        if not grafo.vertices:
            return "El grafo está vacío."
        for arista in grafo.aristas:
            if arista.dirigida:
                return f"La arista {arista.identificador} es dirigida; se requiere un grafo no dirigido."
            if arista.peso is None:
                return f"Falta el peso de la arista {arista.identificador}."
        alcanzables = _alcanzables(grafo, grafo.vertices[0])
        if len(alcanzables) != len(grafo.vertices):
            ausentes = ", ".join(v for v in grafo.vertices if v not in alcanzables)
            return f"El grafo debe ser conexo; no se alcanzan los vértices: {ausentes}."
        return None


class CondicionesDijkstra(CondicionesAplicacion[ParametrosDijkstra]):
    """Admite redes mixtas y desconectadas con pesos no negativos."""

    def vertices_inalcanzables(self, entrada: Entrada[ParametrosDijkstra]) -> tuple[str, ...]:
        """Informa inaccesibles en orden del grafo; no calcula distancias ni rutas."""
        motivo = self.motivo_inaplicabilidad(entrada)
        if motivo is not None:
            raise AlgoritmoNoAplicableError(motivo)
        alcanzables = _alcanzables(entrada.grafo, entrada.parametros.origen)
        return tuple(v for v in entrada.grafo.vertices if v not in alcanzables)

    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosDijkstra]) -> str | None:
        grafo = entrada.grafo
        if not grafo.vertices:
            return "El grafo está vacío."
        parametros = entrada.parametros
        if not isinstance(parametros, ParametrosDijkstra):
            return "Faltan los parámetros de Dijkstra."
        if parametros.origen not in grafo.vertices:
            return "El origen no existe en el grafo."
        if parametros.destino is not None and parametros.destino not in grafo.vertices:
            return "El destino no existe en el grafo."
        return _motivo_pesos_no_negativos(grafo)


class CondicionesFlujoMaximo(CondicionesAplicacion[ParametrosFlujoMaximo]):
    """Comprueba capacidades y terminales, sin imponer conectividad ni flujo positivo."""

    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosFlujoMaximo]) -> str | None:
        grafo = entrada.grafo
        if not grafo.vertices:
            return "El grafo está vacío."
        parametros = entrada.parametros
        if not isinstance(parametros, ParametrosFlujoMaximo):
            return "Faltan los parámetros de Flujo Máximo."
        if parametros.fuente not in grafo.vertices:
            return "La fuente no existe en el grafo."
        if parametros.sumidero not in grafo.vertices:
            return "El sumidero no existe en el grafo."
        if parametros.fuente == parametros.sumidero:
            return "La fuente y el sumidero deben ser distintos."
        if any(not arista.dirigida for arista in grafo.aristas):
            return "Flujo Máximo requiere una red dirigida."
        return _motivo_pesos_no_negativos(grafo)


class CondicionesCPM(CondicionesAplicacion[ParametrosCPM]):
    """Comprueba una duración por actividad en una red AON."""

    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosCPM]) -> str | None:
        motivo = _motivo_red_aon(entrada.grafo)
        if motivo is not None:
            return motivo
        if not isinstance(entrada.parametros, ParametrosCPM):
            return "Faltan los parámetros de CPM, con duraciones por actividad."
        duraciones = entrada.parametros.duraciones
        motivo = _motivo_datos_actividades(entrada.grafo, duraciones)
        if motivo is not None:
            return motivo
        for actividad, duracion in duraciones.items():
            if not _es_tiempo_valido(duracion):
                return f"La duración de la actividad {actividad} debe ser real finita y no negativa."
        return None


class CondicionesPERT(CondicionesAplicacion[ParametrosPERT]):
    """Comprueba tripletas de estimaciones por vértice, sin usar pesos de arista."""

    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosPERT]) -> str | None:
        motivo = _motivo_red_aon(entrada.grafo)
        if motivo is not None:
            return motivo
        if not isinstance(entrada.parametros, ParametrosPERT):
            return "Faltan los parámetros de PERT, con estimaciones por actividad."
        estimaciones = entrada.parametros.estimaciones
        motivo = _motivo_datos_actividades(entrada.grafo, estimaciones)
        if motivo is not None:
            return motivo
        for actividad, tripleta in estimaciones.items():
            if not isinstance(tripleta, EstimacionesPERT):
                return f"Falta una tripleta completa de estimaciones para la actividad {actividad}."
            valores = (tripleta.optimista, tripleta.mas_probable, tripleta.pesimista)
            if not all(_es_tiempo_valido(valor) for valor in valores):
                return f"Las estimaciones de la actividad {actividad} deben ser reales finitas y no negativas."
            if not tripleta.optimista <= tripleta.mas_probable <= tripleta.pesimista:
                return f"La actividad {actividad} debe cumplir optimista <= mas_probable <= pesimista."
        return None
