"""Proyecciones finales inmutables; no consumen pasos ni ejecutan algoritmos.

``proyectar_resultado`` recibe los identificadores públicos del registro:
prim, kruskal, dijkstra, flujo_maximo, cpm y pert. Los valores numéricos se
conservan sin formato ni redondeo; esa tarea corresponde a la presentación.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import inf, isclose, isfinite
from types import MappingProxyType
from typing import Literal

from .algoritmo import Entrada, Resultado
from .arbol_expansion import SolucionArbolExpansion
from .cpm import SolucionCPM, TiemposActividad
from .dijkstra import SolucionDijkstra
from .flujo_maximo import SolucionFlujoMaximo
from .grafo import Arista, Grafo
from .parametros import (
    EstimacionesPERT, ParametrosCPM, ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT,
)
from .pert import SolucionPERT


type IdentificadorAlgoritmo = Literal["prim", "kruskal", "dijkstra", "flujo_maximo", "cpm", "pert"]


class ErrorProyeccion(ValueError):
    """La solución o sus referencias no corresponden al contexto recibido."""


@dataclass(frozen=True, slots=True)
class ProyeccionArbol:
    algoritmo: Literal["prim", "kruskal"]
    vertices: frozenset[str]
    aristas: tuple[int, ...]
    peso_total: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "vertices", frozenset(self.vertices))
        object.__setattr__(self, "aristas", tuple(self.aristas))


@dataclass(frozen=True, slots=True)
class ProyeccionDijkstra:
    algoritmo: Literal["dijkstra"]
    origen: str
    destino_ejecucion: str | None
    destino: str | None
    ruta: tuple[str, ...] | None
    aristas_ruta: tuple[int, ...] | None
    costo: float | None
    distancias: Mapping[str, float]
    predecesores: Mapping[str, tuple[str, int]]
    inalcanzables: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "distancias", MappingProxyType(dict(self.distancias)))
        object.__setattr__(self, "predecesores", MappingProxyType({v: tuple(p) for v, p in self.predecesores.items()}))
        object.__setattr__(self, "inalcanzables", tuple(self.inalcanzables))
        if self.ruta is not None:
            object.__setattr__(self, "ruta", tuple(self.ruta))
        if self.aristas_ruta is not None:
            object.__setattr__(self, "aristas_ruta", tuple(self.aristas_ruta))

    def consultar_destino(self, destino: str) -> ProyeccionDijkstra:
        """Proyecta otra ruta desde los mapas finales, sin alterar la consulta anterior."""
        if destino not in self.distancias:
            raise ErrorProyeccion(f"El destino {destino!r} no existe en la solución de Dijkstra.")
        if self.distancias[destino] == inf:
            return replace(self, destino=destino, ruta=None, aristas_ruta=None, costo=None)
        vertices = [destino]
        aristas: list[int] = []
        vistos = {destino}
        while vertices[-1] != self.origen:
            actual = vertices[-1]
            if actual not in self.predecesores:
                raise ErrorProyeccion(f"Falta el predecesor final de {actual!r}.")
            anterior, identificador = self.predecesores[actual]
            if anterior in vistos:
                raise ErrorProyeccion("La cadena final de predecesores contiene un ciclo.")
            vistos.add(anterior)
            vertices.append(anterior)
            aristas.append(identificador)
        return replace(self, destino=destino, ruta=tuple(reversed(vertices)),
                       aristas_ruta=tuple(reversed(aristas)), costo=self.distancias[destino])


@dataclass(frozen=True, slots=True)
class ArcoFlujoFinal:
    identificador: int
    origen: str
    destino: str
    capacidad_original: float
    flujo: float


@dataclass(frozen=True, slots=True)
class ProyeccionFlujo:
    algoritmo: Literal["flujo_maximo"]
    vertices: frozenset[str]
    arcos: Mapping[int, ArcoFlujoFinal]
    flujo_maximo: float
    lado_fuente: frozenset[str]
    lado_sumidero: frozenset[str]
    aristas_corte: tuple[int, ...]
    capacidad_corte: float

    def __post_init__(self) -> None:
        for nombre in ("vertices", "lado_fuente", "lado_sumidero"):
            object.__setattr__(self, nombre, frozenset(getattr(self, nombre)))
        object.__setattr__(self, "arcos", MappingProxyType(dict(self.arcos)))
        object.__setattr__(self, "aristas_corte", tuple(self.aristas_corte))


@dataclass(frozen=True, slots=True)
class ProyeccionCPM:
    algoritmo: Literal["cpm"]
    actividades: Mapping[str, TiemposActividad]
    duracion_proyecto: float
    actividades_criticas: frozenset[str]
    aristas_criticas: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actividades", MappingProxyType(dict(self.actividades)))
        object.__setattr__(self, "actividades_criticas", frozenset(self.actividades_criticas))
        object.__setattr__(self, "aristas_criticas", tuple(self.aristas_criticas))


@dataclass(frozen=True, slots=True)
class ProyeccionPERT:
    algoritmo: Literal["pert"]
    actividades: Mapping[str, TiemposActividad]
    estimaciones: Mapping[str, EstimacionesPERT]
    tiempos_esperados: Mapping[str, float]
    varianzas: Mapping[str, float]
    duracion_esperada: float
    actividades_criticas: frozenset[str]
    aristas_criticas: tuple[int, ...]

    def __post_init__(self) -> None:
        for nombre in ("actividades", "estimaciones", "tiempos_esperados", "varianzas"):
            object.__setattr__(self, nombre, MappingProxyType(dict(getattr(self, nombre))))
        object.__setattr__(self, "actividades_criticas", frozenset(self.actividades_criticas))
        object.__setattr__(self, "aristas_criticas", tuple(self.aristas_criticas))


type ProyeccionResultado = ProyeccionArbol | ProyeccionDijkstra | ProyeccionFlujo | ProyeccionCPM | ProyeccionPERT


def _claves_originales(datos: Mapping, originales: set, nombre: str) -> None:
    if set(datos) != originales:
        raise ErrorProyeccion(f"{nombre} no cubre exactamente los identificadores originales.")


def _arista_original(aristas: Mapping[int, Arista], identificador: int) -> Arista:
    if identificador not in aristas:
        raise ErrorProyeccion(f"La solución refiere una arista inexistente: {identificador!r}.")
    return aristas[identificador]


def _criticidad(grafo: Grafo, solucion: SolucionCPM) -> tuple[frozenset[str], tuple[int, ...]]:
    _claves_originales(solucion.actividades, set(grafo.vertices), "La planificación")
    sucesoras = solucion.rutas_criticas.sucesoras
    criticas = frozenset(sucesoras)
    relaciones = {(u, v) for u, destinos in sucesoras.items() for v in destinos}
    if not criticas <= set(grafo.vertices) or any(v not in criticas for _, v in relaciones):
        raise ErrorProyeccion("La red crítica refiere actividades inexistentes o no críticas.")
    if not relaciones <= {(a.origen, a.destino) for a in grafo.aristas}:
        raise ErrorProyeccion("La red crítica refiere precedencias ausentes del grafo original.")
    # Recupera todos los IDs originales, también los de precedencias paralelas.
    return criticas, tuple(a.identificador for a in grafo.aristas if (a.origen, a.destino) in relaciones)


def _proyectar_resultado(
    entrada: Entrada[object], resultado: Resultado[object, object],
    algoritmo: IdentificadorAlgoritmo, *, destino: str | None = None,
) -> ProyeccionResultado:
    """Adapta exclusivamente ``resultado.solucion`` en el contexto del grafo original.

    Prim y Kruskal necesitan el identificador explícito porque comparten tipo de
    solución. ``destino`` es una consulta visual opcional exclusiva de Dijkstra.
    """
    if destino is not None and algoritmo != "dijkstra":
        raise ErrorProyeccion("La consulta de destino solo corresponde a Dijkstra.")
    solucion, grafo = resultado.solucion, entrada.grafo
    aristas = {a.identificador: a for a in grafo.aristas}
    vertices = set(grafo.vertices)
    if algoritmo in ("prim", "kruskal") and isinstance(solucion, SolucionArbolExpansion):
        ids = tuple(a.identificador for a in solucion.aristas)
        for a in solucion.aristas:
            if _arista_original(aristas, a.identificador) != a:
                raise ErrorProyeccion(f"La arista {a.identificador} no coincide con la original.")
        if len(set(ids)) != len(ids):
            raise ErrorProyeccion("El árbol final contiene IDs repetidos.")
        return ProyeccionArbol(algoritmo, frozenset(vertices), ids, solucion.peso_total)
    if algoritmo == "dijkstra" and isinstance(solucion, SolucionDijkstra):
        _claves_originales(solucion.distancias, vertices, "Las distancias")
        if solucion.origen not in vertices or (solucion.destino is not None and solucion.destino not in vertices):
            raise ErrorProyeccion("Los terminales de Dijkstra no pertenecen al grafo original.")
        for v, (u, identificador) in solucion.predecesores.items():
            a = _arista_original(aristas, identificador)
            if v not in vertices or u not in vertices or not (
                (a.origen, a.destino) == (u, v) or (not a.dirigida and (a.destino, a.origen) == (u, v))
            ):
                raise ErrorProyeccion(f"Predecesor final incoherente para {v!r}.")
        if solucion.ruta is not None:
            if (solucion.aristas_ruta is None or len(solucion.aristas_ruta) != len(solucion.ruta) - 1
                    or not solucion.ruta or solucion.ruta[0] != solucion.origen
                    or solucion.ruta[-1] != solucion.destino):
                raise ErrorProyeccion("La ruta final de Dijkstra es inconsistente.")
            for u, v, identificador in zip(solucion.ruta, solucion.ruta[1:], solucion.aristas_ruta):
                a = _arista_original(aristas, identificador)
                if not ((a.origen, a.destino) == (u, v) or (not a.dirigida and (a.destino, a.origen) == (u, v))):
                    raise ErrorProyeccion("La ruta final no respeta las conexiones originales.")
        proyeccion = ProyeccionDijkstra(
            "dijkstra", solucion.origen, solucion.destino, solucion.destino,
            solucion.ruta, solucion.aristas_ruta, solucion.costo,
            solucion.distancias, solucion.predecesores, solucion.inalcanzables,
        )
        return proyeccion.consultar_destino(destino) if destino is not None else proyeccion
    if algoritmo == "flujo_maximo" and isinstance(solucion, SolucionFlujoMaximo):
        _claves_originales(solucion.flujo_por_arco, set(aristas), "Los flujos")
        arcos = {}
        for a in grafo.aristas:
            if a.peso is None:
                raise ErrorProyeccion(f"La arista {a.identificador} carece de capacidad original.")
            arcos[a.identificador] = ArcoFlujoFinal(a.identificador, a.origen, a.destino,
                                                 a.peso, solucion.flujo_por_arco[a.identificador])
        for identificador in solucion.aristas_corte:
            _arista_original(aristas, identificador)
        if not (set(solucion.lado_fuente) | set(solucion.lado_sumidero)) <= vertices:
            raise ErrorProyeccion("El corte refiere vértices inexistentes.")
        return ProyeccionFlujo("flujo_maximo", frozenset(vertices), arcos, solucion.flujo_maximo,
                              frozenset(solucion.lado_fuente), frozenset(solucion.lado_sumidero),
                              solucion.aristas_corte, solucion.capacidad_corte)
    if algoritmo == "cpm" and isinstance(solucion, SolucionCPM):
        criticas, ids = _criticidad(grafo, solucion)
        return ProyeccionCPM("cpm", solucion.actividades, solucion.duracion_proyecto, criticas, ids)
    if algoritmo == "pert" and isinstance(solucion, SolucionPERT):
        criticas, ids = _criticidad(grafo, solucion.planificacion)
        for nombre in ("estimaciones", "tiempos_esperados", "varianzas"):
            _claves_originales(getattr(solucion, nombre), vertices, nombre)
        return ProyeccionPERT("pert", solucion.actividades, solucion.estimaciones,
                              solucion.tiempos_esperados, solucion.varianzas,
                              solucion.duracion_esperada, criticas, ids)
    raise ErrorProyeccion(f"Solución {type(solucion).__name__} incompatible con el algoritmo {algoritmo!r}.")


def _validar_tramo(aristas, identificador, origen, destino):
    arista = _arista_original(aristas, identificador)
    if not ((arista.origen, arista.destino) == (origen, destino) or
            (not arista.dirigida and (arista.destino, arista.origen) == (origen, destino))):
        raise ErrorProyeccion(f"La arista #{identificador} no corresponde al tramo {origen} → {destino}.")


def _validar_flujo(arista, flujo):
    capacidad = arista.peso
    if not arista.dirigida or capacidad is None or not isfinite(capacidad) or capacidad < 0:
        raise ErrorProyeccion(f"La arista #{arista.identificador} requiere una capacidad dirigida válida.")
    if not isfinite(flujo) or (flujo < 0 and not isclose(flujo, 0, abs_tol=1e-12)):
        raise ErrorProyeccion(f"El flujo de la arista #{arista.identificador} es inválido o negativo.")
    if flujo > capacidad and not isclose(flujo, capacidad, rel_tol=1e-12, abs_tol=1e-12):
        raise ErrorProyeccion(f"El flujo de la arista #{arista.identificador} excede su capacidad original.")


def validar_proyeccion(entrada: Entrada[object], proyeccion: ProyeccionResultado) -> None:
    """Valida referencias y metadatos verificables, sin recalcular soluciones.

    CPM no publica duraciones originales: no se infieren desde TC-IC, cuya
    resta puede perder precisión. Árboles solo conservan IDs en la proyección.
    """
    tipos = {ProyeccionArbol: ("prim", "kruskal"), ProyeccionDijkstra: ("dijkstra",),
             ProyeccionFlujo: ("flujo_maximo",), ProyeccionCPM: ("cpm",), ProyeccionPERT: ("pert",)}
    permitidos = tipos.get(type(proyeccion), ())
    if not permitidos or proyeccion.algoritmo not in permitidos:
        raise ErrorProyeccion(f"Proyección {type(proyeccion).__name__} declara algoritmo incompatible: "
                              f"{getattr(proyeccion, 'algoritmo', None)!r}.")
    vertices = set(entrada.grafo.vertices)
    aristas = {a.identificador: a for a in entrada.grafo.aristas}
    parametros = entrada.parametros
    if isinstance(proyeccion, ProyeccionArbol):
        if proyeccion.vertices != vertices or len(set(proyeccion.aristas)) != len(proyeccion.aristas):
            raise ErrorProyeccion("Los vértices o IDs del árbol no corresponden a la entrada.")
        for identificador in proyeccion.aristas:
            if _arista_original(aristas, identificador).dirigida:
                raise ErrorProyeccion(f"La arista #{identificador} del árbol debe ser no dirigida.")
    elif isinstance(proyeccion, ProyeccionDijkstra):
        if not isinstance(parametros, ParametrosDijkstra):
            raise ErrorProyeccion("Dijkstra requiere ParametrosDijkstra en la entrada.")
        if proyeccion.origen != parametros.origen or proyeccion.origen not in vertices:
            raise ErrorProyeccion("La solución Dijkstra es incompatible con el origen de la entrada.")
        if proyeccion.destino_ejecucion != parametros.destino:
            raise ErrorProyeccion("La solución Dijkstra es incompatible con el destino original de la entrada.")
        _claves_originales(proyeccion.distancias, vertices, "Las distancias")
        if not set(proyeccion.inalcanzables) <= vertices:
            raise ErrorProyeccion("Dijkstra refiere vértices inalcanzables inexistentes.")
        for v, (u, identificador) in proyeccion.predecesores.items():
            if u not in vertices or v not in vertices:
                raise ErrorProyeccion("El predecesor refiere un vértice inexistente.")
            _validar_tramo(aristas, identificador, u, v)
        if proyeccion.destino is not None and proyeccion.destino not in vertices:
            raise ErrorProyeccion("El destino consultado no pertenece al grafo original.")
        if proyeccion.ruta is None:
            if proyeccion.aristas_ruta is not None or proyeccion.costo is not None:
                raise ErrorProyeccion("Dijkstra sin ruta no puede contener aristas o costo de ruta.")
            if proyeccion.destino is not None and proyeccion.distancias[proyeccion.destino] != inf:
                raise ErrorProyeccion("Dijkstra omite la ruta de un destino alcanzable.")
        else:
            ruta, ids = proyeccion.ruta, proyeccion.aristas_ruta
            if (not ruta or ids is None or len(ids) != len(ruta) - 1 or
                    ruta[0] != proyeccion.origen or ruta[-1] != proyeccion.destino or
                    not set(ruta) <= vertices or proyeccion.costo is None):
                raise ErrorProyeccion("La ruta final de Dijkstra es inconsistente.")
            for u, v, identificador in zip(ruta, ruta[1:], ids):
                _validar_tramo(aristas, identificador, u, v)
    elif isinstance(proyeccion, ProyeccionFlujo):
        if not isinstance(parametros, ParametrosFlujoMaximo):
            raise ErrorProyeccion("Flujo máximo requiere ParametrosFlujoMaximo en la entrada.")
        if (proyeccion.vertices != vertices or parametros.fuente not in vertices or
                parametros.sumidero not in vertices or parametros.fuente == parametros.sumidero):
            raise ErrorProyeccion("Los vértices o terminales del flujo no corresponden a la entrada.")
        fuente, sumidero = proyeccion.lado_fuente, proyeccion.lado_sumidero
        if (fuente & sumidero or fuente | sumidero != vertices or
                parametros.fuente not in fuente or parametros.sumidero not in sumidero):
            raise ErrorProyeccion("El corte del flujo es incompatible con la fuente o el sumidero originales.")
        _claves_originales(proyeccion.arcos, set(aristas), "Los arcos finales")
        for identificador, arco in proyeccion.arcos.items():
            original = _arista_original(aristas, identificador)
            if (arco.identificador, arco.origen, arco.destino) != (identificador, original.origen, original.destino):
                raise ErrorProyeccion(f"El arco final #{identificador} no corresponde a sus extremos originales.")
            if arco.capacidad_original != original.peso:
                raise ErrorProyeccion(f"La capacidad proyectada de #{identificador} no coincide con el grafo original.")
            _validar_flujo(original, arco.flujo)
        for identificador in proyeccion.aristas_corte:
            _arista_original(aristas, identificador)
    else:
        esperado = ParametrosCPM if isinstance(proyeccion, ProyeccionCPM) else ParametrosPERT
        if not isinstance(parametros, esperado):
            raise ErrorProyeccion(f"{proyeccion.algoritmo.upper()} requiere {esperado.__name__} en la entrada.")
        _claves_originales(proyeccion.actividades, vertices, "Las actividades finales")
        originales = parametros.duraciones if isinstance(parametros, ParametrosCPM) else parametros.estimaciones
        _claves_originales(originales, vertices, "Los parámetros de actividades")
        if not proyeccion.actividades_criticas <= vertices:
            raise ErrorProyeccion("La proyección refiere actividades críticas inexistentes.")
        for identificador in proyeccion.aristas_criticas:
            a = _arista_original(aristas, identificador)
            if not a.dirigida or a.peso is not None or not {a.origen, a.destino} <= proyeccion.actividades_criticas:
                raise ErrorProyeccion(f"La precedencia crítica #{identificador} no vincula actividades críticas válidas.")
        if isinstance(proyeccion, ProyeccionPERT):
            for nombre in ("estimaciones", "tiempos_esperados", "varianzas"):
                _claves_originales(getattr(proyeccion, nombre), vertices, nombre)
            if proyeccion.estimaciones != parametros.estimaciones:
                raise ErrorProyeccion("Las estimaciones PERT no coinciden con las originales de la entrada.")


def proyectar_resultado(
    entrada: Entrada[object], resultado: Resultado[object, object],
    algoritmo: IdentificadorAlgoritmo, *, destino: str | None = None,
) -> ProyeccionResultado:
    """Proyecta la solución y valida su contexto verificable, sin consumir pasos."""
    proyeccion = _proyectar_resultado(entrada, resultado, algoritmo, destino=destino)
    validar_proyeccion(entrada, proyeccion)
    return proyeccion
