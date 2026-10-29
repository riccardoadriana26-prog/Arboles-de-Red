"""Parámetros tipados e inmutables para los algoritmos de redes."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ParametrosDijkstra:
    """Origen y destino opcional de una consulta de caminos mínimos."""

    origen: str
    destino: str | None = None


@dataclass(frozen=True, slots=True)
class ParametrosFlujoMaximo:
    """Terminales de una red de capacidades para Ford–Fulkerson."""

    fuente: str
    sumidero: str


@dataclass(frozen=True, slots=True)
class ParametrosCPM:
    """Duración de cada actividad; las precedencias pertenecen al grafo."""

    duraciones: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "duraciones", MappingProxyType(dict(self.duraciones)))


@dataclass(frozen=True, slots=True)
class EstimacionesPERT:
    """Tripleta original de una actividad; no calcula tiempo esperado ni varianza."""

    optimista: float
    mas_probable: float
    pesimista: float


@dataclass(frozen=True, slots=True)
class ParametrosPERT:
    """Estimaciones PERT de cada actividad, sin asociarlas a las aristas."""

    estimaciones: Mapping[str, EstimacionesPERT]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "estimaciones", MappingProxyType(dict(self.estimaciones))
        )
