"""PERT conserva las estimaciones y planifica la AON con sus tiempos esperados."""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from fractions import Fraction
from math import sqrt
from types import MappingProxyType

from ._numeros import como_float, sumar
from .algoritmo import Algoritmo, Entrada, Paso, Resultado
from .aplicabilidad import CondicionesPERT
from .cpm import DetalleCPM, RutasCriticas, SolucionCPM, TiemposActividad, _planificar
from .parametros import EstimacionesPERT, ParametrosPERT


@dataclass(frozen=True, slots=True)
class VariabilidadRutaPERT:
    actividades: tuple[str, ...]
    duracion_esperada: float
    varianza: float
    desviacion_estandar: float


@dataclass(frozen=True, slots=True)
class SolucionPERT:
    estimaciones: Mapping[str, EstimacionesPERT]
    tiempos_esperados: Mapping[str, float]
    varianzas: Mapping[str, float]
    planificacion: SolucionCPM

    def __post_init__(self) -> None:
        object.__setattr__(self, "estimaciones", MappingProxyType(dict(self.estimaciones)))
        object.__setattr__(self, "tiempos_esperados", MappingProxyType(dict(self.tiempos_esperados)))
        object.__setattr__(self, "varianzas", MappingProxyType(dict(self.varianzas)))

    @property
    def duracion_esperada(self) -> float:
        return self.planificacion.duracion_proyecto

    @property
    def actividades(self) -> Mapping[str, TiemposActividad]:
        return self.planificacion.actividades

    @property
    def rutas_criticas(self) -> RutasCriticas:
        return self.planificacion.rutas_criticas

    def variabilidad_rutas(self) -> Iterator[VariabilidadRutaPERT]:
        """Suma varianzas por ruta bajo la hipótesis PERT de actividades independientes.

        No elige una ruta ni presenta su varianza como la del máximo aleatorio
        de varias rutas. La enumeración es a demanda, igual que la red crítica.
        """
        for ruta in self.rutas_criticas:
            varianza = sumar(self.varianzas[v] for v in ruta)
            yield VariabilidadRutaPERT(ruta, self.duracion_esperada, varianza, sqrt(varianza))


@dataclass(frozen=True, slots=True)
class DetalleEstimacionPERT:
    actividad: str
    estimaciones: EstimacionesPERT
    tiempo_esperado: float
    varianza: float


type DetallePERT = DetalleEstimacionPERT | DetalleCPM


class PERT(Algoritmo[ParametrosPERT, SolucionPERT, DetallePERT]):
    def __init__(self) -> None:
        super().__init__(CondicionesPERT())

    def _resolver(self, entrada: Entrada[ParametrosPERT]) -> Resultado[SolucionPERT, DetallePERT]:
        esperados: dict[str, Fraction] = {}
        varianzas: dict[str, float] = {}
        pasos: list[Paso[DetallePERT]] = []
        for actividad in entrada.grafo.vertices:
            estimaciones = entrada.parametros.estimaciones[actividad]
            a = Fraction(str(estimaciones.optimista))
            m = Fraction(str(estimaciones.mas_probable))
            b = Fraction(str(estimaciones.pesimista))
            esperados[actividad] = (a + 4 * m + b) / 6
            varianzas[actividad] = como_float(((b - a) / 6) ** 2)
            pasos.append(Paso(len(pasos) + 1, "Se calcula el tiempo esperado (a + 4m + b) / 6 y la varianza ((b - a) / 6)².",
                              (actividad,), (), DetalleEstimacionPERT(
                                  actividad, estimaciones, como_float(esperados[actividad]), varianzas[actividad])))
        planificacion = _planificar(entrada.grafo, esperados)
        for paso in planificacion.pasos:
            pasos.append(Paso(len(pasos) + 1, paso.descripcion, paso.vertices_destacados,
                              paso.aristas_destacadas, paso.detalle))
        solucion = SolucionPERT(entrada.parametros.estimaciones,
                               {v: como_float(t) for v, t in esperados.items()}, varianzas, planificacion.solucion)
        return Resultado(solucion, tuple(pasos))
