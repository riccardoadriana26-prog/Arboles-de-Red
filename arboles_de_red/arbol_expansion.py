"""Prim y Kruskal implementados sobre las aristas del modelo común."""

from dataclasses import dataclass

from ._numeros import sumar
from .algoritmo import Algoritmo, Entrada, Paso, Resultado
from .aplicabilidad import CondicionesArbolExpansion
from .grafo import Arista


@dataclass(frozen=True, slots=True)
class SolucionArbolExpansion:
    aristas: tuple[Arista, ...]
    peso_total: float


@dataclass(frozen=True, slots=True)
class DetalleArbolExpansion:
    arista: int | None
    aceptada: bool
    aristas_arbol: tuple[int, ...]
    peso_acumulado: float


def _peso(arista: Arista) -> float:
    # Las condiciones compartidas ya comprobaron que ninguna arista carece de peso.
    assert arista.peso is not None
    return arista.peso


class Prim(Algoritmo[None, SolucionArbolExpansion, DetalleArbolExpansion]):
    def __init__(self) -> None:
        super().__init__(CondicionesArbolExpansion())

    def _resolver(self, entrada: Entrada[None]) -> Resultado[SolucionArbolExpansion, DetalleArbolExpansion]:
        grafo = entrada.grafo
        visitados = {grafo.vertices[0]}
        elegidas: list[Arista] = []
        pasos = [Paso(1, "Se inicia Prim en el primer vértice cargado.",
                      (grafo.vertices[0],), (), DetalleArbolExpansion(None, True, (), 0.0))]
        while len(visitados) < len(grafo.vertices):
            # Frontera: exactamente uno de los extremos pertenece al árbol.
            candidatas = (a for a in grafo.aristas
                          if (a.origen in visitados) != (a.destino in visitados))
            arista = min(candidatas, key=lambda a: (_peso(a), a.identificador))
            elegidas.append(arista)
            visitados.update((arista.origen, arista.destino))
            ids = tuple(a.identificador for a in elegidas)
            peso = sumar(_peso(a) for a in elegidas)
            pasos.append(Paso(len(pasos) + 1, "Se incorpora la arista de menor peso de la frontera.",
                              (arista.origen, arista.destino), (arista.identificador,),
                              DetalleArbolExpansion(arista.identificador, True, ids, peso)))
        return Resultado(SolucionArbolExpansion(tuple(elegidas), sumar(_peso(a) for a in elegidas)), tuple(pasos))


class Kruskal(Algoritmo[None, SolucionArbolExpansion, DetalleArbolExpansion]):
    def __init__(self) -> None:
        super().__init__(CondicionesArbolExpansion())

    def _resolver(self, entrada: Entrada[None]) -> Resultado[SolucionArbolExpansion, DetalleArbolExpansion]:
        grafo = entrada.grafo
        padres = {v: v for v in grafo.vertices}
        rangos = dict.fromkeys(grafo.vertices, 0)

        def raiz(vertice: str) -> str:
            while padres[vertice] != vertice:
                padres[vertice] = padres[padres[vertice]]
                vertice = padres[vertice]
            return vertice

        elegidas: list[Arista] = []
        pasos = [Paso(1, "Se inicia un componente por vértice y se ordenan las aristas por peso.",
                      grafo.vertices, (), DetalleArbolExpansion(None, True, (), 0.0))]
        for arista in sorted(grafo.aristas, key=lambda a: (_peso(a), a.identificador)):
            if len(elegidas) == len(grafo.vertices) - 1:
                break
            origen, destino = raiz(arista.origen), raiz(arista.destino)
            aceptada = origen != destino
            if aceptada:
                if rangos[origen] < rangos[destino]:
                    origen, destino = destino, origen
                padres[destino] = origen
                if rangos[origen] == rangos[destino]:
                    rangos[origen] += 1
                elegidas.append(arista)
            pasos.append(Paso(
                len(pasos) + 1,
                "Se unen dos componentes." if aceptada else "Se rechaza la arista porque formaría un ciclo.",
                (arista.origen, arista.destino), (arista.identificador,),
                DetalleArbolExpansion(arista.identificador, aceptada,
                                     tuple(a.identificador for a in elegidas), sumar(_peso(a) for a in elegidas)),
            ))
        return Resultado(SolucionArbolExpansion(tuple(elegidas), sumar(_peso(a) for a in elegidas)), tuple(pasos))
