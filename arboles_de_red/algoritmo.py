"""Contrato común para ejecutar algoritmos sobre un :class:`Grafo`."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .grafo import Grafo


class AlgoritmoNoAplicableError(ValueError):
    """La entrada no satisface las condiciones del algoritmo seleccionado."""

    def __init__(self, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(motivo)


@dataclass(frozen=True, slots=True)
class Entrada[ParametrosT]:
    """Grafo y parámetros propios del algoritmo para una ejecución."""

    grafo: Grafo
    parametros: ParametrosT


@dataclass(frozen=True, slots=True)
class Paso[DetalleT]:
    """Decisión ordenada y referencias que puede destacar la visualización."""

    numero: int
    descripcion: str
    vertices_destacados: tuple[str, ...]
    aristas_destacadas: tuple[int, ...]
    detalle: DetalleT

    def __post_init__(self) -> None:
        object.__setattr__(self, "vertices_destacados", tuple(self.vertices_destacados))
        object.__setattr__(self, "aristas_destacadas", tuple(self.aristas_destacadas))


@dataclass(frozen=True, slots=True)
class Resultado[SolucionT, DetalleT]:
    """Solución propia del algoritmo y secuencia completa de sus pasos."""

    solucion: SolucionT
    pasos: tuple[Paso[DetalleT], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "pasos", tuple(self.pasos))


class Algoritmo[ParametrosT, SolucionT, DetalleT](ABC):
    """Base que impide resolver una entrada no aplicable.

    Cada implementación define sus condiciones y la resolución. Para informar
    una incompatibilidad, ``_motivo_inaplicabilidad`` devuelve un motivo; para
    una entrada válida devuelve ``None``. La aplicación usa ``es_aplicable``
    antes de iniciar y ``ejecutar`` cuando el usuario decide continuar.
    """

    def es_aplicable(self, entrada: Entrada[ParametrosT]) -> bool:
        return self._motivo_inaplicabilidad(entrada) is None

    def ejecutar(self, entrada: Entrada[ParametrosT]) -> Resultado[SolucionT, DetalleT]:
        motivo = self._motivo_inaplicabilidad(entrada)
        if motivo is not None:
            raise AlgoritmoNoAplicableError(motivo)
        return self._resolver(entrada)

    @abstractmethod
    def _motivo_inaplicabilidad(self, entrada: Entrada[ParametrosT]) -> str | None:
        """Devuelve ``None`` si la entrada cumple todas las condiciones."""

    @abstractmethod
    def _resolver(self, entrada: Entrada[ParametrosT]) -> Resultado[SolucionT, DetalleT]:
        """Calcula la solución y todos sus pasos en orden de ejecución."""
