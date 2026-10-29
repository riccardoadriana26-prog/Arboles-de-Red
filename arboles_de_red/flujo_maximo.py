"""Ford–Fulkerson con búsqueda propia en anchura de caminos de aumento."""

from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from ._numeros import como_float
from .algoritmo import Algoritmo, Entrada, Paso, Resultado
from .aplicabilidad import CondicionesFlujoMaximo
from .parametros import ParametrosFlujoMaximo


@dataclass(frozen=True, slots=True)
class SolucionFlujoMaximo:
    flujo_maximo: float
    flujo_por_arco: Mapping[int, float]
    lado_fuente: tuple[str, ...]
    lado_sumidero: tuple[str, ...]
    aristas_corte: tuple[int, ...]
    capacidad_corte: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "flujo_por_arco", MappingProxyType(dict(self.flujo_por_arco)))


@dataclass(frozen=True, slots=True)
class ActualizacionResidual:
    arista: int
    origen: str
    destino: str
    inverso: bool
    antes: float
    despues: float


@dataclass(frozen=True, slots=True)
class TramoAumento:
    arista: int
    origen: str
    destino: str
    inverso: bool


@dataclass(frozen=True, slots=True)
class DetalleFlujoMaximo:
    camino: tuple[TramoAumento, ...]
    cuello_botella: float
    flujo_acumulado: float
    actualizaciones: tuple[ActualizacionResidual, ...]
    flujo_por_arco: tuple[tuple[int, float], ...]


@dataclass(slots=True)
class _ArcoResidual:
    destino: str
    pareja: int
    capacidad: Fraction
    arista: int
    inverso: bool


class FordFulkerson(Algoritmo[ParametrosFlujoMaximo, SolucionFlujoMaximo, DetalleFlujoMaximo]):
    def __init__(self) -> None:
        super().__init__(CondicionesFlujoMaximo())

    def _resolver(self, entrada: Entrada[ParametrosFlujoMaximo]) -> Resultado[SolucionFlujoMaximo, DetalleFlujoMaximo]:
        grafo, parametros = entrada.grafo, entrada.parametros
        red: dict[str, list[_ArcoResidual]] = {v: [] for v in grafo.vertices}
        flujos = {a.identificador: Fraction(0) for a in grafo.aristas}
        for arista in grafo.aristas:
            assert arista.peso is not None
            ida = _ArcoResidual(arista.destino, len(red[arista.destino]),
                                Fraction(str(arista.peso)), arista.identificador, False)
            vuelta = _ArcoResidual(arista.origen, len(red[arista.origen]),
                                   Fraction(0), arista.identificador, True)
            red[arista.origen].append(ida)
            red[arista.destino].append(vuelta)

        def instantanea() -> tuple[tuple[int, float], ...]:
            return tuple((identificador, como_float(flujo)) for identificador, flujo in flujos.items())

        total = Fraction(0)
        pasos = [Paso(1, "Se inicia el flujo en cero y se construyen los arcos residuales directos e inversos.",
                      (parametros.fuente, parametros.sumidero), (),
                      DetalleFlujoMaximo((), 0.0, 0.0, (), instantanea()))]
        while True:
            # Búsqueda en anchura implementada aquí: ningún resolvedor externo.
            padres: dict[str, tuple[str, int]] = {}
            visitados = {parametros.fuente}
            cola = [parametros.fuente]
            indice = 0
            while indice < len(cola) and parametros.sumidero not in visitados:
                actual = cola[indice]
                indice += 1
                for posicion, arco in enumerate(red[actual]):
                    if arco.capacidad > 0 and arco.destino not in visitados:
                        visitados.add(arco.destino)
                        padres[arco.destino] = (actual, posicion)
                        cola.append(arco.destino)
            if parametros.sumidero not in visitados:
                break
            camino: list[tuple[str, int]] = []
            actual = parametros.sumidero
            while actual != parametros.fuente:
                anterior, posicion = padres[actual]
                camino.append((anterior, posicion))
                actual = anterior
            camino.reverse()
            cuello = min(red[origen][posicion].capacidad for origen, posicion in camino)
            tramos = []
            actualizaciones = []
            for origen, posicion in camino:
                arco = red[origen][posicion]
                pareja = red[arco.destino][arco.pareja]
                tramos.append(TramoAumento(arco.arista, origen, arco.destino, arco.inverso))
                antes, antes_pareja = arco.capacidad, pareja.capacidad
                arco.capacidad -= cuello
                pareja.capacidad += cuello
                flujos[arco.arista] += -cuello if arco.inverso else cuello
                actualizaciones.extend((
                    ActualizacionResidual(arco.arista, origen, arco.destino, arco.inverso,
                                          como_float(antes), como_float(arco.capacidad)),
                    ActualizacionResidual(pareja.arista, arco.destino, origen, pareja.inverso,
                                          como_float(antes_pareja), como_float(pareja.capacidad)),
                ))
            total += cuello
            pasos.append(Paso(len(pasos) + 1, "Se aumenta el flujo por el cuello de botella y se actualiza la red residual.",
                              (parametros.fuente,) + tuple(t.destino for t in tramos),
                              tuple(t.arista for t in tramos),
                              DetalleFlujoMaximo(tuple(tramos), como_float(cuello), como_float(total),
                                                 tuple(actualizaciones), instantanea())))
        corte = tuple(a for a in grafo.aristas if a.origen in visitados and a.destino not in visitados)
        capacidad_corte = sum((Fraction(str(a.peso)) for a in corte), Fraction(0))
        fuente = tuple(v for v in grafo.vertices if v in visitados)
        sumidero = tuple(v for v in grafo.vertices if v not in visitados)
        pasos.append(Paso(len(pasos) + 1, "No existe un camino residual de aumento; se alcanza el corte mínimo.",
                          fuente, tuple(a.identificador for a in corte),
                          DetalleFlujoMaximo((), 0.0, como_float(total), (), instantanea())))
        return Resultado(SolucionFlujoMaximo(como_float(total), dict(instantanea()), fuente, sumidero,
                                            tuple(a.identificador for a in corte), como_float(capacidad_corte)), tuple(pasos))
