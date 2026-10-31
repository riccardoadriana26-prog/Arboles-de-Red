"""Reconstrucción pura de estados acumulados a partir de ``Resultado.pasos``.

Este módulo no ejecuta algoritmos ni depende de una interfaz. Los índices
visibles son prefijos: 0 es el estado inicial y N aplica los primeros N pasos.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import fsum, inf, isclose, isfinite
from types import MappingProxyType
from typing import TypeAlias

from .algoritmo import Entrada, Paso, Resultado
from .arbol_expansion import DetalleArbolExpansion
from .cpm import DetalleCPM
from .dijkstra import DetalleDijkstra
from .flujo_maximo import ActualizacionResidual, DetalleFlujoMaximo, TramoAumento
from .grafo import Arista
from .parametros import (
    EstimacionesPERT,
    ParametrosCPM,
    ParametrosDijkstra,
    ParametrosFlujoMaximo,
    ParametrosPERT,
)
from .pert import DetalleEstimacionPERT


class ErrorReconstruccion(ValueError):
    """La entrada o un evento no permite reconstruir un estado consistente."""


@dataclass(frozen=True, slots=True)
class ValoresActividad:
    """Valores CPM publicados hasta el paso consultado; ``None`` aún no calculado."""

    ic: float | None = None
    tc: float | None = None
    il: float | None = None
    tl: float | None = None
    holgura: float | None = None


@dataclass(frozen=True, slots=True)
class EstadoExpansion:
    aristas_arbol: tuple[int, ...]
    aristas_evaluadas: tuple[int, ...]
    aristas_evaluadas_acumuladas: tuple[int, ...]
    arista_elegida: int | None
    aristas_rechazadas_ciclo: tuple[int, ...]
    peso_acumulado: float
    vertices_arbol: tuple[str, ...]
    componentes: tuple[tuple[str, ...], ...]
    algoritmo: str


@dataclass(frozen=True, slots=True)
class EstadoDijkstra:
    distancias: Mapping[str, float]
    predecesores: Mapping[str, tuple[str, int]]
    permanentes: tuple[str, ...]
    accion: str
    vertice_actual: str | None
    arista_actual: int | None
    distancia_anterior: float | None
    distancia_nueva: float | None
    predecesor_anterior: tuple[str, int] | None
    predecesor_nuevo: tuple[str, int] | None


@dataclass(frozen=True, slots=True)
class EstadoFlujoResidual:
    capacidades_residuales: Mapping[tuple[int, bool], float]
    flujo_por_arco: Mapping[int, float]
    camino: tuple[TramoAumento, ...]
    cuello_botella: float
    incremento_flujo: float
    flujo_acumulado: float
    actualizaciones: tuple[ActualizacionResidual, ...]
    lado_fuente: tuple[str, ...]
    aristas_corte: tuple[int, ...]
    accion: str


@dataclass(frozen=True, slots=True)
class EstadoPlanificacion:
    valores_por_actividad: Mapping[str, ValoresActividad]
    duraciones: Mapping[str, float]
    fase: str
    actividad_actual: str | None
    actividades_criticas: tuple[str, ...]
    aristas_criticas: tuple[int, ...]
    duracion_proyecto: float | None


@dataclass(frozen=True, slots=True)
class EstadoPERT:
    estimaciones: Mapping[str, EstimacionesPERT]
    tiempos_esperados: Mapping[str, float]
    varianzas: Mapping[str, float]
    planificacion: EstadoPlanificacion
    fase: str
    actividad_actual: str | None


EstadoAlgoritmo: TypeAlias = (
    EstadoExpansion | EstadoDijkstra | EstadoFlujoResidual | EstadoPlanificacion | EstadoPERT
)


@dataclass(frozen=True, slots=True)
class EstadoEjecucion:
    """Contexto compartido; el grafo original se conserva una sola vez aquí."""

    entrada: Entrada[object]
    resultado: Resultado[object, object]
    algoritmo: str


@dataclass(frozen=True, slots=True)
class EstadoVisualPaso:
    """Estado visual inmutable después de aplicar el prefijo indicado."""

    numero: int
    fase: str
    paso: Paso[object] | None
    vertices_destacados: tuple[str, ...]
    aristas_destacadas: tuple[int, ...]
    estado: EstadoAlgoritmo


def _solo_lectura(valores: Mapping) -> Mapping:
    return MappingProxyType(dict(valores))


def _cercanos(a: float, b: float) -> bool:
    return isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def _componentes(vertices: tuple[str, ...], aristas: tuple[Arista, ...], ids: tuple[int, ...]) -> tuple[tuple[str, ...], ...]:
    adyacencia = {v: set() for v in vertices}
    por_id = {a.identificador: a for a in aristas}
    for identificador in ids:
        a = por_id[identificador]
        adyacencia[a.origen].add(a.destino)
        adyacencia[a.destino].add(a.origen)
    vistos: set[str] = set()
    salida = []
    for inicio in vertices:
        if inicio in vistos:
            continue
        componente = []
        pila = [inicio]
        vistos.add(inicio)
        while pila:
            actual = pila.pop()
            componente.append(actual)
            for vecino in adyacencia[actual]:
                if vecino not in vistos:
                    vistos.add(vecino)
                    pila.append(vecino)
        miembros = set(componente)
        salida.append(tuple(v for v in vertices if v in miembros))
    return tuple(salida)


def _plan_inicial(vertices: tuple[str, ...], duraciones: Mapping[str, float]) -> EstadoPlanificacion:
    return EstadoPlanificacion(
        _solo_lectura({v: ValoresActividad() for v in vertices}),
        _solo_lectura(duraciones), "inicial", None, (), (), None,
    )


def _aplicar_cpm(
    estado: EstadoPlanificacion, detalle: DetalleCPM, paso: Paso[object],
) -> EstadoPlanificacion:
    valores = dict(estado.valores_por_actividad)
    fase = detalle.fase
    if fase not in ("adelante", "atras", "finalizar"):
        raise ErrorReconstruccion(f"Fase CPM desconocida: {fase!r}.")
    if fase == "finalizar":
        if detalle.actividad is not None:
            raise ErrorReconstruccion("El detalle CPM de finalización no debe identificar una actividad.")
        return EstadoPlanificacion(
            _solo_lectura(valores), estado.duraciones, fase, None,
            paso.vertices_destacados, paso.aristas_destacadas, detalle.tc,
        )
    actividad = detalle.actividad
    if actividad not in valores:
        raise ErrorReconstruccion(f"CPM refiere actividad inexistente: {actividad!r}.")
    anterior = valores[actividad]
    valores[actividad] = ValoresActividad(
        detalle.ic if detalle.ic is not None else anterior.ic,
        detalle.tc if detalle.tc is not None else anterior.tc,
        detalle.il if detalle.il is not None else anterior.il,
        detalle.tl if detalle.tl is not None else anterior.tl,
        detalle.holgura if detalle.holgura is not None else anterior.holgura,
    )
    return EstadoPlanificacion(
        _solo_lectura(valores), estado.duraciones, fase, actividad,
        estado.actividades_criticas, estado.aristas_criticas, estado.duracion_proyecto,
    )


class ReconstruccionEjecucion:
    """Reconstruye prefijos de eventos con snapshots cada ``intervalo_checkpoint`` pasos.

    ``estado_en(0)`` devuelve el estado inicial; ``estado_en(N)`` aplica los
    primeros N eventos. Cada consulta parte de un checkpoint inmutable y
    reproduce hacia delante; nunca invierte eventos ni invoca un resolvedor.
    """

    ALGORITMOS = frozenset(("Prim", "Kruskal", "Dijkstra", "FlujoMaximo", "CPM", "PERT"))
    _ALIAS = {
        "prim": "Prim", "kruskal": "Kruskal", "dijkstra": "Dijkstra",
        "flujo_maximo": "FlujoMaximo", "cpm": "CPM", "pert": "PERT",
    }

    def __init__(
        self, entrada: Entrada[object], resultado: Resultado[object, object],
        algoritmo: str, intervalo_checkpoint: int = 64,
    ) -> None:
        algoritmo = self._ALIAS.get(algoritmo, algoritmo)
        if algoritmo not in self.ALGORITMOS:
            raise ErrorReconstruccion(f"Algoritmo no admitido: {algoritmo!r}.")
        if isinstance(intervalo_checkpoint, bool) or not isinstance(intervalo_checkpoint, int) or intervalo_checkpoint < 1:
            raise ValueError("intervalo_checkpoint debe ser un entero positivo.")
        self.contexto = EstadoEjecucion(entrada, resultado, algoritmo)
        self.intervalo_checkpoint = intervalo_checkpoint
        self._aristas = {a.identificador: a for a in entrada.grafo.aristas}
        self._vertices = frozenset(entrada.grafo.vertices)
        self._validar_entrada()
        self._validar_pasos()
        self._checkpoints: dict[int, EstadoAlgoritmo] = {0: self._inicial()}

    @property
    def cantidad_pasos(self) -> int:
        return len(self.contexto.resultado.pasos)

    def estado_en(self, numero: int) -> EstadoVisualPaso:
        """Devuelve el estado después de ``numero`` eventos, sin mutar consultas previas."""
        if isinstance(numero, bool) or not isinstance(numero, int) or not 0 <= numero <= self.cantidad_pasos:
            raise IndexError(f"El paso debe estar entre 0 y {self.cantidad_pasos}; recibido {numero!r}.")
        base = max(n for n in self._checkpoints if n <= numero)
        estado = self._checkpoints[base]
        for indice in range(base, numero):
            estado = self._aplicar(estado, self.contexto.resultado.pasos[indice])
            aplicado = indice + 1
            if aplicado % self.intervalo_checkpoint == 0:
                self._checkpoints[aplicado] = estado
        paso = None if numero == 0 else self.contexto.resultado.pasos[numero - 1]
        fase = "inicial" if paso is None else self._fase(estado)
        return EstadoVisualPaso(
            numero, fase, paso,
            () if paso is None else paso.vertices_destacados,
            () if paso is None else paso.aristas_destacadas,
            estado,
        )

    def _validar_entrada(self) -> None:
        algoritmo, entrada = self.contexto.algoritmo, self.contexto.entrada
        parametros = entrada.parametros
        if algoritmo in ("Prim", "Kruskal"):
            if parametros is not None:
                raise ErrorReconstruccion(f"{algoritmo} requiere parámetros None.")
            if any(a.dirigida or a.peso is None for a in entrada.grafo.aristas):
                raise ErrorReconstruccion(f"{algoritmo} requiere aristas no dirigidas y ponderadas.")
        elif algoritmo == "Dijkstra":
            if not isinstance(parametros, ParametrosDijkstra):
                raise ErrorReconstruccion("Dijkstra requiere ParametrosDijkstra.")
            if parametros.origen not in self._vertices or (parametros.destino is not None and parametros.destino not in self._vertices):
                raise ErrorReconstruccion("Los parámetros de Dijkstra refieren vértices inexistentes.")
        elif algoritmo == "FlujoMaximo":
            if not isinstance(parametros, ParametrosFlujoMaximo):
                raise ErrorReconstruccion("FlujoMaximo requiere ParametrosFlujoMaximo.")
            if parametros.fuente not in self._vertices or parametros.sumidero not in self._vertices:
                raise ErrorReconstruccion("Los parámetros de flujo refieren vértices inexistentes.")
            if any(a.peso is None for a in entrada.grafo.aristas):
                raise ErrorReconstruccion("FlujoMaximo necesita capacidad en cada arista original.")
        elif algoritmo == "CPM":
            if not isinstance(parametros, ParametrosCPM):
                raise ErrorReconstruccion("CPM requiere ParametrosCPM.")
            if set(parametros.duraciones) != self._vertices:
                raise ErrorReconstruccion("Las duraciones CPM deben cubrir exactamente los vértices del grafo.")
        elif not isinstance(parametros, ParametrosPERT) or set(parametros.estimaciones) != self._vertices:
            raise ErrorReconstruccion("PERT requiere estimaciones para todos los vértices del grafo.")

    def _validar_pasos(self) -> None:
        esperado = {
            "Prim": DetalleArbolExpansion, "Kruskal": DetalleArbolExpansion,
            "Dijkstra": DetalleDijkstra, "FlujoMaximo": DetalleFlujoMaximo,
            "CPM": DetalleCPM, "PERT": (DetalleEstimacionPERT, DetalleCPM),
        }[self.contexto.algoritmo]
        for indice, paso in enumerate(self.contexto.resultado.pasos, start=1):
            if paso.numero != indice:
                raise ErrorReconstruccion(f"Numeración discontinua: se esperaba paso {indice}, llegó {paso.numero}.")
            if not isinstance(paso.detalle, esperado):
                raise ErrorReconstruccion(
                    f"Paso {indice} de {self.contexto.algoritmo} tiene detalle incompatible: {type(paso.detalle).__name__}."
                )
            for vertice in paso.vertices_destacados:
                self._validar_vertice(vertice, f"paso {indice}")
            for identificador in paso.aristas_destacadas:
                self._validar_arista(identificador, f"paso {indice}")

    def _validar_vertice(self, vertice: str, origen: str) -> None:
        if vertice not in self._vertices:
            raise ErrorReconstruccion(f"{origen} refiere vértice inexistente {vertice!r}.")

    def _validar_arista(self, identificador: int, origen: str) -> Arista:
        try:
            return self._aristas[identificador]
        except KeyError as error:
            raise ErrorReconstruccion(f"{origen} refiere arista inexistente {identificador!r}.") from error

    def _costo_camino_dijkstra(self, vertice: str, predecesores: Mapping[str, tuple[str, int]]) -> Fraction:
        """Suma el camino ya registrado; no selecciona rutas ni ejecuta el resolutor."""
        origen = self.contexto.entrada.parametros.origen
        costo = Fraction(0)
        vistos: set[str] = set()
        while vertice != origen:
            if vertice in vistos or vertice not in predecesores:
                raise ErrorReconstruccion(f"Camino de predecesores Dijkstra inválido para {vertice!r}.")
            vistos.add(vertice)
            anterior, identificador = predecesores[vertice]
            arista = self._validar_arista(identificador, "camino de predecesores Dijkstra")
            extremos = (arista.origen, arista.destino)
            if arista.peso is None or not (
                extremos == (anterior, vertice) or (not arista.dirigida and extremos == (vertice, anterior))
            ):
                raise ErrorReconstruccion(f"Arista de predecesores Dijkstra incoherente: {identificador}.")
            costo += Fraction(str(arista.peso))
            vertice = anterior
        return costo

    def _inicial(self) -> EstadoAlgoritmo:
        algoritmo, entrada = self.contexto.algoritmo, self.contexto.entrada
        vertices = entrada.grafo.vertices
        if algoritmo in ("Prim", "Kruskal"):
            paso = self.contexto.resultado.pasos[0] if self.cantidad_pasos else None
            raiz = paso.vertices_destacados[0] if algoritmo == "Prim" and paso and paso.vertices_destacados else None
            componentes = tuple((v,) for v in vertices) if algoritmo == "Kruskal" else ()
            return EstadoExpansion((), (), (), None, (), 0.0, (raiz,) if raiz else (), componentes, algoritmo)
        if algoritmo == "Dijkstra":
            origen = entrada.parametros.origen
            return EstadoDijkstra(
                _solo_lectura({v: 0.0 if v == origen else inf for v in vertices}),
                _solo_lectura({}), (), "inicial", None, None, None, None, None, None,
            )
        if algoritmo == "FlujoMaximo":
            residuales = {}
            for a in entrada.grafo.aristas:
                assert a.peso is not None
                residuales[(a.identificador, False)] = a.peso
                residuales[(a.identificador, True)] = 0.0
            return EstadoFlujoResidual(
                _solo_lectura(residuales), _solo_lectura(dict.fromkeys(self._aristas, 0.0)),
                (), 0.0, 0.0, 0.0, (), (), (), "inicial",
            )
        if algoritmo == "CPM":
            return _plan_inicial(vertices, entrada.parametros.duraciones)
        plan = _plan_inicial(vertices, {})
        return EstadoPERT(
            _solo_lectura(entrada.parametros.estimaciones), _solo_lectura({}),
            _solo_lectura({}), plan, "inicial", None,
        )

    def _aplicar(self, estado: EstadoAlgoritmo, paso: Paso[object]) -> EstadoAlgoritmo:
        algoritmo, detalle = self.contexto.algoritmo, paso.detalle
        if algoritmo in ("Prim", "Kruskal"):
            assert isinstance(detalle, DetalleArbolExpansion)
            if detalle.arista is not None:
                arista = self._validar_arista(detalle.arista, f"detalle del paso {paso.numero}")
                self._validar_vertice(arista.origen, f"arista {arista.identificador}")
                self._validar_vertice(arista.destino, f"arista {arista.identificador}")
            for identificador in (*detalle.aristas_arbol, *detalle.aristas_evaluadas):
                self._validar_arista(identificador, f"detalle del paso {paso.numero}")
            if not isinstance(estado, EstadoExpansion):
                raise ErrorReconstruccion("Estado base incompatible con expansión.")
            if algoritmo == "Prim":
                if detalle.arista is not None and (detalle.aceptada is not True or detalle.arista not in detalle.aristas_arbol):
                    raise ErrorReconstruccion(f"Decisión Prim inconsistente en paso {paso.numero}.")
                if detalle.arista is None and detalle.aristas_arbol:
                    raise ErrorReconstruccion("El paso inicial Prim no puede contener aristas del árbol.")
                if tuple(detalle.aristas_arbol[:len(estado.aristas_arbol)]) != estado.aristas_arbol:
                    raise ErrorReconstruccion(f"El árbol de Prim no conserva el prefijo en paso {paso.numero}.")
                if estado.vertices_arbol and detalle.arista is not None:
                    dentro = set(estado.vertices_arbol)
                    frontera = tuple(
                        a.identificador for a in self.contexto.entrada.grafo.aristas
                        if (a.origen in dentro) != (a.destino in dentro)
                    )
                    if detalle.aristas_evaluadas != frontera:
                        raise ErrorReconstruccion(f"Frontera evaluada de Prim inconsistente en paso {paso.numero}.")
                    if detalle.arista is not None and detalle.arista not in frontera:
                        raise ErrorReconstruccion(f"Prim eligió una arista fuera de la frontera en paso {paso.numero}.")
                    candidatas = [self._aristas[i] for i in frontera]
                    elegida_esperada = min(candidatas, key=lambda a: (a.peso, a.identificador))
                    if detalle.arista != elegida_esperada.identificador:
                        raise ErrorReconstruccion(f"Prim no eligió la arista mínima de la frontera en paso {paso.numero}.")
                rechazadas = estado.aristas_rechazadas_ciclo
            else:
                if detalle.arista is not None and detalle.aceptada not in (True, False):
                    raise ErrorReconstruccion(f"Kruskal no indicó aceptación o rechazo en paso {paso.numero}.")
                if detalle.arista is not None and detalle.aristas_evaluadas != (detalle.arista,):
                    raise ErrorReconstruccion(f"Kruskal debe evaluar una arista por paso ({paso.numero}).")
                if detalle.aristas_arbol[:len(estado.aristas_arbol)] != estado.aristas_arbol:
                    raise ErrorReconstruccion(f"El árbol de Kruskal no conserva el prefijo en paso {paso.numero}.")
                if detalle.arista is not None:
                    componentes_previas = _componentes(
                        self.contexto.entrada.grafo.vertices,
                        self.contexto.entrada.grafo.aristas,
                        estado.aristas_arbol,
                    )
                    grupos = {v: i for i, grupo in enumerate(componentes_previas) for v in grupo}
                    arista_evaluada = self._aristas[detalle.arista]
                    forma_ciclo = grupos[arista_evaluada.origen] == grupos[arista_evaluada.destino]
                    if detalle.aceptada is forma_ciclo:
                        raise ErrorReconstruccion(f"Decisión de ciclo de Kruskal inconsistente en paso {paso.numero}.")
                    arbol_esperado = estado.aristas_arbol + ((detalle.arista,) if detalle.aceptada else ())
                    if detalle.aristas_arbol != arbol_esperado:
                        raise ErrorReconstruccion(f"Árbol posterior de Kruskal inconsistente en paso {paso.numero}.")
                if detalle.aceptada is False and detalle.arista is not None:
                    rechazadas = estado.aristas_rechazadas_ciclo + (detalle.arista,)
                else:
                    rechazadas = estado.aristas_rechazadas_ciclo
                if detalle.arista is not None and detalle.arista in estado.aristas_evaluadas_acumuladas:
                    raise ErrorReconstruccion(f"Kruskal vuelve a evaluar arista {detalle.arista}.")
            evaluadas = detalle.aristas_evaluadas
            acumuladas = estado.aristas_evaluadas_acumuladas + tuple(i for i in evaluadas if i not in estado.aristas_evaluadas_acumuladas)
            arbol = tuple(detalle.aristas_arbol)
            if len(set(arbol)) != len(arbol):
                raise ErrorReconstruccion(f"Aristas duplicadas en el árbol del paso {paso.numero}.")
            peso_arbol = fsum(self._aristas[i].peso for i in arbol)
            if not _cercanos(peso_arbol, detalle.peso_acumulado):
                raise ErrorReconstruccion(f"Peso acumulado de expansión inconsistente en paso {paso.numero}.")
            vertices_arbol = set()
            if algoritmo == "Prim" and estado.vertices_arbol:
                vertices_arbol.add(estado.vertices_arbol[0])
            for identificador in arbol:
                a = self._aristas[identificador]
                vertices_arbol.update((a.origen, a.destino))
            return EstadoExpansion(
                arbol, evaluadas, acumuladas, detalle.arista, rechazadas,
                detalle.peso_acumulado, tuple(v for v in self.contexto.entrada.grafo.vertices if v in vertices_arbol),
                _componentes(self.contexto.entrada.grafo.vertices, self.contexto.entrada.grafo.aristas, arbol), algoritmo,
            )
        if algoritmo == "Dijkstra":
            assert isinstance(detalle, DetalleDijkstra)
            if not isinstance(estado, EstadoDijkstra):
                raise ErrorReconstruccion("Estado base incompatible con Dijkstra.")
            self._validar_vertice(detalle.vertice, f"detalle Dijkstra paso {paso.numero}")
            if detalle.arista is not None:
                a = self._validar_arista(detalle.arista, f"detalle Dijkstra paso {paso.numero}")
                if detalle.accion in ("relajar", "conservar") and detalle.vertice not in (a.origen, a.destino):
                    raise ErrorReconstruccion(f"La arista {a.identificador} no incide en el vértice actualizado {detalle.vertice}.")
            distancias, predecesores = dict(estado.distancias), dict(estado.predecesores)
            permanentes = estado.permanentes
            if detalle.accion == "iniciar":
                if paso.numero != 1 or detalle.vertice != self.contexto.entrada.parametros.origen:
                    raise ErrorReconstruccion("Evento de inicio Dijkstra fuera de lugar o con origen incorrecto.")
                if detalle.distancia_nueva != 0 or detalle.distancia_anterior is not None or detalle.arista is not None:
                    raise ErrorReconstruccion("El evento de inicio Dijkstra debe fijar únicamente distancia cero al origen.")
            elif detalle.accion == "fijar":
                if detalle.vertice in permanentes:
                    raise ErrorReconstruccion(f"Dijkstra fija dos veces {detalle.vertice!r}.")
                if not _cercanos(distancias[detalle.vertice], detalle.distancia_nueva):
                    raise ErrorReconstruccion(f"Distancia fijada inconsistente para {detalle.vertice!r} en paso {paso.numero}.")
                if detalle.predecesor_nuevo != predecesores.get(detalle.vertice):
                    raise ErrorReconstruccion(f"Predecesor fijado inconsistente para {detalle.vertice!r} en paso {paso.numero}.")
                permanentes += (detalle.vertice,)
                if detalle.permanentes != permanentes:
                    raise ErrorReconstruccion(f"Lista de permanentes inconsistente en paso {paso.numero}.")
            elif detalle.accion in ("relajar", "conservar"):
                if detalle.arista is None:
                    raise ErrorReconstruccion(f"Relajación Dijkstra sin arista en paso {paso.numero}.")
                anterior = distancias[detalle.vertice]
                pred_anterior = predecesores.get(detalle.vertice)
                if not _cercanos(anterior, detalle.distancia_anterior) or pred_anterior != detalle.predecesor_anterior:
                    raise ErrorReconstruccion(f"Valores anteriores Dijkstra no coinciden en paso {paso.numero}.")
                origen_relajacion = paso.vertices_destacados[0] if paso.vertices_destacados else None
                a = self._aristas[detalle.arista]
                extremos_validos = (a.origen, a.destino) == (origen_relajacion, detalle.vertice)
                if not a.dirigida:
                    extremos_validos |= (a.destino, a.origen) == (origen_relajacion, detalle.vertice)
                if not extremos_validos or origen_relajacion not in distancias:
                    raise ErrorReconstruccion(f"Orientación de relajación Dijkstra inválida en paso {paso.numero}.")
                if a.peso is None:
                    raise ErrorReconstruccion(f"Arista Dijkstra {a.identificador} carece de peso.")
                candidato = distancias[origen_relajacion] + a.peso
                if detalle.accion == "relajar":
                    mejora = detalle.distancia_nueva < anterior
                    if detalle.distancia_nueva == anterior and isfinite(anterior) and pred_anterior is not None:
                        # Dos costos exactos distintos pueden publicar el mismo float.
                        candidato_exacto = self._costo_camino_dijkstra(origen_relajacion, predecesores) + Fraction(str(a.peso))
                        mejora = candidato_exacto < self._costo_camino_dijkstra(detalle.vertice, predecesores)
                    if detalle.vertice in permanentes or not mejora or not _cercanos(detalle.distancia_nueva, candidato):
                        raise ErrorReconstruccion(f"La relajación Dijkstra no mejora la distancia en paso {paso.numero}.")
                    if detalle.predecesor_nuevo != (origen_relajacion, detalle.arista):
                        raise ErrorReconstruccion(f"Predecesor nuevo Dijkstra incoherente en paso {paso.numero}.")
                    distancias[detalle.vertice] = detalle.distancia_nueva
                    predecesores[detalle.vertice] = detalle.predecesor_nuevo
                else:
                    if candidato < anterior and not _cercanos(candidato, anterior):
                        raise ErrorReconstruccion(f"Dijkstra conservó una distancia mejorable en paso {paso.numero}.")
                    if not _cercanos(detalle.distancia_nueva, anterior) or detalle.predecesor_nuevo != pred_anterior:
                        raise ErrorReconstruccion(f"Evento conservar Dijkstra altera estado en paso {paso.numero}.")
                if detalle.permanentes != permanentes:
                    raise ErrorReconstruccion(f"Permanentes Dijkstra inconsistentes en paso {paso.numero}.")
            elif detalle.accion == "finalizar":
                if detalle.permanentes != permanentes:
                    raise ErrorReconstruccion(f"Permanentes finales Dijkstra inconsistentes en paso {paso.numero}.")
                if not _cercanos(detalle.distancia_nueva, distancias[detalle.vertice]) or detalle.predecesor_nuevo != predecesores.get(detalle.vertice):
                    raise ErrorReconstruccion(f"Estado final Dijkstra inconsistente en paso {paso.numero}.")
            else:
                raise ErrorReconstruccion(f"Acción Dijkstra desconocida: {detalle.accion!r}.")
            return EstadoDijkstra(
                _solo_lectura(distancias), _solo_lectura(predecesores), permanentes,
                detalle.accion, detalle.vertice, detalle.arista, detalle.distancia_anterior,
                detalle.distancia_nueva, detalle.predecesor_anterior, detalle.predecesor_nuevo,
            )
        if algoritmo == "FlujoMaximo":
            assert isinstance(detalle, DetalleFlujoMaximo)
            if not isinstance(estado, EstadoFlujoResidual):
                raise ErrorReconstruccion("Estado base incompatible con Ford–Fulkerson.")
            residual = dict(estado.capacidades_residuales)
            flujos = dict(estado.flujo_por_arco)
            if paso.numero == 1:
                if detalle.camino or detalle.actualizaciones or detalle.cuello_botella != 0 or detalle.flujo_acumulado != 0:
                    raise ErrorReconstruccion("El primer evento de flujo debe ser la inicialización en cero.")
                accion = "inicializar"
                incremento = 0.0
            elif detalle.camino:
                if detalle.cuello_botella <= 0:
                    raise ErrorReconstruccion(f"Cuello de botella no positivo en paso {paso.numero}.")
                incremento = detalle.cuello_botella
                accion = "aumentar"
                for tramo in detalle.camino:
                    a = self._validar_arista(tramo.arista, f"camino de aumento paso {paso.numero}")
                    extremos = (a.destino, a.origen) if tramo.inverso else (a.origen, a.destino)
                    if (tramo.origen, tramo.destino) != extremos:
                        raise ErrorReconstruccion(f"Tramo residual no corresponde a arista {a.identificador}.")
                    clave = (tramo.arista, tramo.inverso)
                    if residual.get(clave, 0.0) + 1e-12 < incremento:
                        raise ErrorReconstruccion(f"Capacidad insuficiente en arco residual {clave}.")
                    flujos[tramo.arista] += -incremento if tramo.inverso else incremento
            else:
                if detalle.actualizaciones or detalle.cuello_botella != 0:
                    raise ErrorReconstruccion(f"Evento final de flujo contiene actualizaciones en paso {paso.numero}.")
                accion = "corte_minimo"
                incremento = 0.0
            for cambio in detalle.actualizaciones:
                a = self._validar_arista(cambio.arista, f"actualización residual paso {paso.numero}")
                extremos = (a.destino, a.origen) if cambio.inverso else (a.origen, a.destino)
                if (cambio.origen, cambio.destino) != extremos:
                    raise ErrorReconstruccion(f"Orientación residual incorrecta para arista {a.identificador}.")
                clave = (cambio.arista, cambio.inverso)
                actual = residual.get(clave)
                if actual is None or not _cercanos(actual, cambio.antes):
                    raise ErrorReconstruccion(
                        f"Residual anterior inconsistente para {clave} en paso {paso.numero}: esperado {actual}, recibido {cambio.antes}."
                    )
                if cambio.despues < -1e-12:
                    raise ErrorReconstruccion(f"Capacidad residual negativa para {clave} en paso {paso.numero}.")
                residual[clave] = cambio.despues
            if detalle.camino:
                esperadas = []
                for tramo in detalle.camino:
                    clave = (tramo.arista, tramo.inverso)
                    pareja = (tramo.arista, not tramo.inverso)
                    original = self._aristas[tramo.arista]
                    extremos = (original.destino, original.origen) if tramo.inverso else (original.origen, original.destino)
                    pareja_extremos = (extremos[1], extremos[0])
                    antes_seleccionado = estado.capacidades_residuales[clave]
                    antes_pareja = estado.capacidades_residuales[pareja]
                    esperadas.extend((
                        (clave, extremos, antes_seleccionado, antes_seleccionado - incremento),
                        (pareja, pareja_extremos, antes_pareja, antes_pareja + incremento),
                    ))
                recibidas = [((c.arista, c.inverso), (c.origen, c.destino)) for c in detalle.actualizaciones]
                if len(recibidas) != len(esperadas) or any(
                    (clave, extremos) != (recibida[0], recibida[1])
                    or not _cercanos(antes, detalle.actualizaciones[i].antes)
                    or not _cercanos(despues, detalle.actualizaciones[i].despues)
                    for i, ((clave, extremos, antes, despues), recibida) in enumerate(zip(esperadas, recibidas))
                ):
                    raise ErrorReconstruccion(f"Actualizaciones residuales no corresponden al camino en paso {paso.numero}.")
            if len(dict(detalle.flujo_por_arco)) != len(detalle.flujo_por_arco):
                raise ErrorReconstruccion(f"Flujos duplicados en detalle del paso {paso.numero}.")
            flujo_publicado = dict(detalle.flujo_por_arco)
            if set(flujo_publicado) != set(self._aristas):
                raise ErrorReconstruccion(f"El snapshot de flujo del paso {paso.numero} no cubre las aristas originales.")
            if any(not _cercanos(flujos[i], flujo_publicado[i]) for i in flujos):
                raise ErrorReconstruccion(f"El flujo publicado no coincide con el camino de aumento en paso {paso.numero}.")
            esperado_total = estado.flujo_acumulado + incremento
            if not _cercanos(esperado_total, detalle.flujo_acumulado):
                raise ErrorReconstruccion(f"Flujo acumulado inconsistente en paso {paso.numero}.")
            lado_fuente = paso.vertices_destacados if accion == "corte_minimo" else estado.lado_fuente
            aristas_corte = paso.aristas_destacadas if accion == "corte_minimo" else ()
            return EstadoFlujoResidual(
                _solo_lectura(residual), _solo_lectura(flujo_publicado), tuple(detalle.camino),
                detalle.cuello_botella, incremento, detalle.flujo_acumulado,
                tuple(detalle.actualizaciones), lado_fuente, aristas_corte, accion,
            )
        if algoritmo == "CPM":
            assert isinstance(detalle, DetalleCPM)
            if not isinstance(estado, EstadoPlanificacion):
                raise ErrorReconstruccion("Estado base incompatible con CPM.")
            for relacionada in detalle.relacionadas:
                self._validar_vertice(relacionada, f"detalle CPM paso {paso.numero}")
            if detalle.fase in ("adelante", "atras") and detalle.actividad is not None:
                duracion = estado.duraciones[detalle.actividad]
                if detalle.fase == "adelante" and detalle.ic is not None and detalle.tc is not None and not _cercanos(detalle.tc, detalle.ic + duracion):
                    raise ErrorReconstruccion(f"IC/TC CPM incoherentes para {detalle.actividad!r} en paso {paso.numero}.")
                if detalle.fase == "atras" and detalle.il is not None and detalle.tl is not None and not _cercanos(detalle.il, detalle.tl - duracion):
                    raise ErrorReconstruccion(f"IL/TL CPM incoherentes para {detalle.actividad!r} en paso {paso.numero}.")
                if detalle.fase == "atras" and detalle.holgura is not None and detalle.il is not None and detalle.ic is not None and not _cercanos(detalle.holgura, detalle.il - detalle.ic):
                    raise ErrorReconstruccion(f"Holgura CPM incoherente para {detalle.actividad!r} en paso {paso.numero}.")
            return _aplicar_cpm(estado, detalle, paso)
        assert isinstance(estado, EstadoPERT)
        if isinstance(detalle, DetalleEstimacionPERT):
            if detalle.actividad not in estado.estimaciones:
                raise ErrorReconstruccion(f"PERT refiere actividad inexistente {detalle.actividad!r}.")
            if detalle.estimaciones != estado.estimaciones[detalle.actividad]:
                raise ErrorReconstruccion(f"Las estimaciones PERT cambiaron en paso {paso.numero}.")
            original = detalle.estimaciones
            a, m, b = (Fraction(str(valor)) for valor in (
                original.optimista, original.mas_probable, original.pesimista,
            ))
            esperado = float((a + 4 * m + b) / 6)
            varianza = float(((b - a) / 6) ** 2)
            if not _cercanos(detalle.tiempo_esperado, esperado) or not _cercanos(detalle.varianza, varianza):
                raise ErrorReconstruccion(f"Cálculo de estimación PERT inconsistente en paso {paso.numero}.")
            esperadas = dict(estado.tiempos_esperados)
            varianzas = dict(estado.varianzas)
            esperadas[detalle.actividad] = detalle.tiempo_esperado
            varianzas[detalle.actividad] = detalle.varianza
            return EstadoPERT(
                estado.estimaciones, _solo_lectura(esperadas), _solo_lectura(varianzas),
                estado.planificacion, "estimacion", detalle.actividad,
            )
        if isinstance(detalle, DetalleCPM):
            plan = _aplicar_cpm(estado.planificacion, detalle, paso)
            return EstadoPERT(
                estado.estimaciones, estado.tiempos_esperados, estado.varianzas,
                plan, f"planificacion_{detalle.fase}", detalle.actividad,
            )
        raise ErrorReconstruccion(f"Detalle PERT no admitido en paso {paso.numero}.")

    @staticmethod
    def _fase(estado: EstadoAlgoritmo) -> str:
        if isinstance(estado, EstadoExpansion):
            return estado.algoritmo.lower()
        if isinstance(estado, (EstadoDijkstra, EstadoFlujoResidual)):
            return estado.accion
        if isinstance(estado, EstadoPlanificacion):
            return estado.fase
        return estado.fase
