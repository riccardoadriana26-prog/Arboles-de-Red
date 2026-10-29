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


class CondicionesAplicacion[ParametrosT](ABC):
    """Condiciones reutilizables del algoritmo, independientes de su resolución."""

    def es_aplicable(self, entrada: Entrada[ParametrosT]) -> bool:
        return self.motivo_inaplicabilidad(entrada) is None

    @abstractmethod
    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosT]) -> str | None:
        """Devuelve el motivo de rechazo o ``None`` cuando la entrada es compatible."""


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

    Recibe condiciones reutilizables y cada implementación define la resolución.
    También admite implementaciones que definen ``_motivo_inaplicabilidad``.
    La aplicación consulta ``es_aplicable`` y ``motivo_inaplicabilidad`` antes
    de iniciar; ``ejecutar`` vuelve a verificar las condiciones antes de resolver.
    """

    def __init__(self, condiciones: CondicionesAplicacion[ParametrosT] | None = None) -> None:
        self._condiciones = condiciones

    def es_aplicable(self, entrada: Entrada[ParametrosT]) -> bool:
        return self.motivo_inaplicabilidad(entrada) is None

    def motivo_inaplicabilidad(self, entrada: Entrada[ParametrosT]) -> str | None:
        """Permite consultar el motivo antes de ejecutar; ``None`` indica que aplica."""
        return self._motivo_inaplicabilidad(entrada)

    def ejecutar(self, entrada: Entrada[ParametrosT]) -> Resultado[SolucionT, DetalleT]:
        motivo = self.motivo_inaplicabilidad(entrada)
        if motivo is not None:
            raise AlgoritmoNoAplicableError(motivo)
        return self._resolver(entrada)

    def _motivo_inaplicabilidad(self, entrada: Entrada[ParametrosT]) -> str | None:
        """Usa las condiciones recibidas; permite conservar implementaciones propias."""
        if self._condiciones is None:
            return "No se definieron las condiciones de aplicación del algoritmo."
        return self._condiciones.motivo_inaplicabilidad(entrada)

    @abstractmethod
    def _resolver(self, entrada: Entrada[ParametrosT]) -> Resultado[SolucionT, DetalleT]:
        """Calcula la solución y todos sus pasos en orden de ejecución."""
