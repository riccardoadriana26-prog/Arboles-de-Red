"""Dijkstra por selección del mínimo temporal y relajación de sus conexiones."""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import inf
from types import MappingProxyType

from ._numeros import como_float
from .algoritmo import Algoritmo, Entrada, Paso, Resultado
from .aplicabilidad import CondicionesDijkstra
from .grafo import Arista
from .parametros import ParametrosDijkstra


@dataclass(frozen=True, slots=True)
class SolucionDijkstra:
    origen: str
    destino: str | None
    ruta: tuple[str, ...] | None
    aristas_ruta: tuple[int, ...] | None
    costo: float | None
    distancias: Mapping[str, float]
    predecesores: Mapping[str, tuple[str, int]]
    inalcanzables: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "distancias", MappingProxyType(dict(self.distancias)))
        object.__setattr__(self, "predecesores", MappingProxyType(dict(self.predecesores)))

    def ruta_hasta(self, destino: str) -> tuple[str, ...] | None:
        """Consulta cualquier destino después de resolver desde el origen."""
        if self.distancias[destino] == inf:
            return None
        ruta = [destino]
        while ruta[-1] != self.origen:
            ruta.append(self.predecesores[ruta[-1]][0])
        return tuple(reversed(ruta))


@dataclass(frozen=True, slots=True)
class DetalleDijkstra:
    accion: str
    vertice: str
    arista: int | None
    distancia_anterior: float | None
    distancia_nueva: float
    permanentes: tuple[str, ...]
    predecesor_anterior: tuple[str, int] | None
    predecesor_nuevo: tuple[str, int] | None


class Dijkstra(Algoritmo[ParametrosDijkstra, SolucionDijkstra, DetalleDijkstra]):
    def __init__(self) -> None:
        super().__init__(CondicionesDijkstra())

    def _resolver(self, entrada: Entrada[ParametrosDijkstra]) -> Resultado[SolucionDijkstra, DetalleDijkstra]:
        grafo, parametros = entrada.grafo, entrada.parametros
        vecinos: dict[str, list[tuple[str, Arista]]] = {v: [] for v in grafo.vertices}
        for arista in grafo.aristas:
            vecinos[arista.origen].append((arista.destino, arista))
            if not arista.dirigida:
                vecinos[arista.destino].append((arista.origen, arista))
        # Comparar sumas exactas de los pesos decimales normalizados. Convertir
        # recién al publicar un dato evita falsos empates y desbordes de rutas descartadas.
        distancias: dict[str, Fraction | None] = dict.fromkeys(grafo.vertices)
        distancias[parametros.origen] = Fraction(0)

        def distancia_publica(vertice: str) -> float:
            distancia = distancias[vertice]
            return inf if distancia is None else como_float(distancia)
        predecesores: dict[str, tuple[str, int]] = {}
        permanentes: list[str] = []
        fijados: set[str] = set()
        pasos = [Paso(1, "Se asigna cero al origen e infinito a los demás vértices.",
                      (parametros.origen,), (), DetalleDijkstra(
                          "iniciar", parametros.origen, None, None, 0.0, (), None, None
                      ))]
        while len(fijados) < len(grafo.vertices):
            actual = min((v for v in grafo.vertices if v not in fijados),
                         key=lambda v: (distancias[v] is None, distancias[v] or Fraction(0)))
            distancia_actual = distancias[actual]
            if distancia_actual is None:
                break
            fijados.add(actual)
            permanentes.append(actual)
            predecesor_actual = predecesores.get(actual)
            pasos.append(Paso(len(pasos) + 1, "Se fija el vértice temporal de menor distancia.",
                              (actual,), (), DetalleDijkstra("fijar", actual, None, None,
                                                           distancia_publica(actual), tuple(permanentes),
                                                           predecesor_actual, predecesor_actual)))
            for vecino, arista in vecinos[actual]:
                if vecino in fijados:
                    continue
                assert arista.peso is not None
                candidato = distancia_actual + Fraction(str(arista.peso))
                anterior = distancias[vecino]
                predecesor_anterior = predecesores.get(vecino)
                mejora = anterior is None or candidato < anterior
                if mejora:
                    distancias[vecino] = candidato
                    predecesores[vecino] = (actual, arista.identificador)
                predecesor_nuevo = predecesores.get(vecino)
                pasos.append(Paso(
                    len(pasos) + 1,
                    "Se mejora la distancia temporal." if mejora else "Se conserva la distancia conocida.",
                    (actual, vecino), (arista.identificador,),
                    DetalleDijkstra("relajar" if mejora else "conservar", vecino, arista.identificador,
                                    inf if anterior is None else como_float(anterior),
                                    distancia_publica(vecino), tuple(permanentes),
                                    predecesor_anterior, predecesor_nuevo),
                ))
        inalcanzables = tuple(v for v in grafo.vertices if distancias[v] is None)
        ruta: tuple[str, ...] | None = None
        ids: tuple[int, ...] | None = None
        costo = None
        if parametros.destino is not None and distancias[parametros.destino] is not None:
            vertices = [parametros.destino]
            aristas = []
            while vertices[-1] != parametros.origen:
                anterior, identificador = predecesores[vertices[-1]]
                vertices.append(anterior)
                aristas.append(identificador)
            ruta, ids = tuple(reversed(vertices)), tuple(reversed(aristas))
            costo = distancia_publica(parametros.destino)
        descripcion = "Finaliza Dijkstra."
        if parametros.destino in inalcanzables:
            descripcion = "El destino es inalcanzable desde el origen."
        terminal = parametros.destino if parametros.destino is not None else parametros.origen
        predecesor_terminal = predecesores.get(terminal)
        pasos.append(Paso(len(pasos) + 1, descripcion, ruta or (), ids or (),
                          DetalleDijkstra("finalizar", terminal, None, None,
                                          distancia_publica(terminal), tuple(permanentes),
                                          predecesor_terminal, predecesor_terminal)))
        return Resultado(SolucionDijkstra(parametros.origen, parametros.destino, ruta, ids, costo,
                                         {v: distancia_publica(v) for v in grafo.vertices},
                                         predecesores, inalcanzables), tuple(pasos))
