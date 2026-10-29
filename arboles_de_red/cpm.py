"""Planificación AON mediante orden de precedencia y dos pasadas propias."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction
from types import MappingProxyType

from ._numeros import como_float
from .algoritmo import Algoritmo, Entrada, Paso, Resultado
from .aplicabilidad import CondicionesCPM
from .grafo import Grafo
from .parametros import ParametrosCPM


@dataclass(frozen=True, slots=True)
class TiemposActividad:
    ic: float
    tc: float
    il: float
    tl: float
    holgura: float


@dataclass(frozen=True, slots=True)
class RutasCriticas:
    """Red de caminos críticos; se enumeran a demanda porque pueden ser exponenciales."""

    inicios: tuple[str, ...]
    sucesoras: Mapping[str, tuple[str, ...]]
    cantidad: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "sucesoras", MappingProxyType({v: tuple(ss) for v, ss in self.sucesoras.items()}))

    def __iter__(self) -> Iterator[tuple[str, ...]]:
        # Pila explícita: también admite cadenas de más de mil actividades.
        for inicio in self.inicios:
            ruta = [inicio]
            pila = [iter(self.sucesoras[inicio])]
            if not self.sucesoras[inicio]:
                yield tuple(ruta)
            while pila:
                siguiente = next(pila[-1], None)
                if siguiente is None:
                    pila.pop()
                    ruta.pop()
                else:
                    ruta.append(siguiente)
                    pila.append(iter(self.sucesoras[siguiente]))
                    if not self.sucesoras[siguiente]:
                        yield tuple(ruta)


@dataclass(frozen=True, slots=True)
class SolucionCPM:
    actividades: Mapping[str, TiemposActividad]
    duracion_proyecto: float
    rutas_criticas: RutasCriticas
    orden_topologico: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actividades", MappingProxyType(dict(self.actividades)))


@dataclass(frozen=True, slots=True)
class DetalleCPM:
    fase: str
    actividad: str | None
    ic: float | None
    tc: float | None
    il: float | None
    tl: float | None
    holgura: float | None
    relacionadas: tuple[str, ...]


def _planificar(
    grafo: Grafo, duraciones: Mapping[str, Fraction],
) -> Resultado[SolucionCPM, DetalleCPM]:
    # Se cuentan relaciones entre actividades una sola vez aunque haya arcos paralelos.
    sucesoras: dict[str, dict[str, None]] = {v: {} for v in grafo.vertices}
    predecesoras: dict[str, dict[str, None]] = {v: {} for v in grafo.vertices}
    for arista in grafo.aristas:
        sucesoras[arista.origen][arista.destino] = None
        predecesoras[arista.destino][arista.origen] = None
    grados = {v: len(predecesoras[v]) for v in grafo.vertices}
    orden = [v for v in grafo.vertices if grados[v] == 0]
    indice = 0
    while indice < len(orden):
        actual = orden[indice]
        indice += 1
        for sucesora in sucesoras[actual]:
            grados[sucesora] -= 1
            if grados[sucesora] == 0:
                orden.append(sucesora)
    # El contrato de aplicabilidad ya rechazó ciclos; no se calcula un resultado parcial.
    assert len(orden) == len(grafo.vertices)
    ic: dict[str, Fraction] = {}
    tc: dict[str, Fraction] = {}
    il: dict[str, Fraction] = {}
    tl: dict[str, Fraction] = {}
    holguras: dict[str, Fraction] = {}
    pasos: list[Paso[DetalleCPM]] = []
    for actual in orden:
        ic[actual] = max((tc[p] for p in predecesoras[actual]), default=Fraction(0))
        tc[actual] = ic[actual] + duraciones[actual]
        aristas = tuple(a.identificador for a in grafo.aristas if a.destino == actual)
        pasos.append(Paso(len(pasos) + 1, "Pasada hacia adelante: IC = máximo TC de predecesoras; TC = IC + duración.",
                          (actual,), aristas,
                          DetalleCPM("adelante", actual, como_float(ic[actual]), como_float(tc[actual]),
                                     None, None, None, tuple(predecesoras[actual]))))
    duracion = max(tc.values())
    for actual in reversed(orden):
        tl[actual] = min((il[s] for s in sucesoras[actual]), default=duracion)
        il[actual] = tl[actual] - duraciones[actual]
        holguras[actual] = il[actual] - ic[actual]
        aristas = tuple(a.identificador for a in grafo.aristas if a.origen == actual)
        pasos.append(Paso(len(pasos) + 1, "Pasada hacia atrás: TL = mínimo IL de sucesoras; IL = TL - duración.",
                          (actual,), aristas,
                          DetalleCPM("atras", actual, como_float(ic[actual]), como_float(tc[actual]),
                                     como_float(il[actual]), como_float(tl[actual]), como_float(holguras[actual]),
                                     tuple(sucesoras[actual]))))
    criticas = {v for v in orden if holguras[v] == 0}
    enlaces = {v: tuple(s for s in sucesoras[v] if s in criticas and tc[v] == ic[s])
               for v in orden if v in criticas}
    inicios = tuple(v for v in orden if v in criticas and not predecesoras[v])
    cantidades: dict[str, int] = {}
    for v in reversed(orden):
        if v in criticas:
            cantidades[v] = sum(cantidades[s] for s in enlaces[v]) if enlaces[v] else 1
    rutas = RutasCriticas(inicios, enlaces, sum(cantidades[v] for v in inicios))
    actividades = {v: TiemposActividad(como_float(ic[v]), como_float(tc[v]), como_float(il[v]),
                                       como_float(tl[v]), como_float(holguras[v])) for v in grafo.vertices}
    aristas_criticas = tuple(a.identificador for a in grafo.aristas
                            if a.origen in criticas and a.destino in enlaces[a.origen])
    pasos.append(Paso(len(pasos) + 1, "Las actividades de holgura cero y precedencias ajustadas forman las rutas críticas.",
                      tuple(v for v in grafo.vertices if v in criticas), aristas_criticas,
                      DetalleCPM("finalizar", None, None, como_float(duracion), None, None, None, ())))
    return Resultado(SolucionCPM(actividades, como_float(duracion), rutas, tuple(orden)), tuple(pasos))


class CPM(Algoritmo[ParametrosCPM, SolucionCPM, DetalleCPM]):
    def __init__(self) -> None:
        super().__init__(CondicionesCPM())

    def _resolver(self, entrada: Entrada[ParametrosCPM]) -> Resultado[SolucionCPM, DetalleCPM]:
        # Aritmética racional evita inventar holguras por errores de suma decimal.
        duraciones = {v: Fraction(str(t)) for v, t in entrada.parametros.duraciones.items()}
        return _planificar(entrada.grafo, duraciones)
