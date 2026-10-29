"""Representación inmutable de grafos con dirección definida por arista."""

from dataclasses import dataclass
from decimal import Decimal
from math import isfinite
from numbers import Real


def _validar_vertice(identificador: str) -> None:
    if not isinstance(identificador, str):
        raise TypeError("El identificador de un vértice debe ser texto.")
    if not identificador or not identificador.isalnum():
        raise ValueError("El identificador de un vértice debe ser alfanumérico.")


@dataclass(frozen=True, slots=True)
class Arista:
    """Conexión individual; peso=None representa una precedencia sin peso."""

    identificador: int
    origen: str
    destino: str
    peso: float | None
    dirigida: bool

    def __post_init__(self) -> None:
        if isinstance(self.identificador, bool) or not isinstance(
            self.identificador, int
        ):
            raise TypeError("El identificador de una arista debe ser un entero.")
        if self.identificador < 0:
            raise ValueError("El identificador de una arista no puede ser negativo.")

        _validar_vertice(self.origen)
        _validar_vertice(self.destino)
        if self.origen == self.destino:
            raise ValueError("No se admiten lazos.")

        if self.peso is not None:
            if isinstance(self.peso, bool) or not isinstance(
                self.peso, (Real, Decimal)
            ):
                raise TypeError("El peso debe ser un número real.")
            try:
                peso = float(self.peso)
            except OverflowError as error:
                raise ValueError("El peso debe ser un número real finito.") from error
            if not isfinite(peso):
                raise ValueError("El peso debe ser un número real finito.")
            if peso == 0 and self.peso != 0:
                raise ValueError("El peso no nulo es demasiado pequeño para representarse como float.")
            object.__setattr__(self, "peso", peso)

        if not isinstance(self.dirigida, bool):
            raise TypeError("La dirección de la arista debe ser un booleano.")


@dataclass(frozen=True, slots=True)
class Grafo:
    """Instantánea de vértices y aristas, independiente del algoritmo.

    Un grafo vacío es representable; la validación del CSV lo rechazará.
    La conectividad y otras condiciones de aplicación pertenecen a cada algoritmo.
    """

    vertices: tuple[str, ...]
    aristas: tuple[Arista, ...]

    def __post_init__(self) -> None:
        vertices = tuple(self.vertices)
        aristas = tuple(self.aristas)

        for vertice in vertices:
            _validar_vertice(vertice)
        if len(set(vertices)) != len(vertices):
            raise ValueError("Los identificadores de vértices deben ser únicos.")

        identificadores: set[int] = set()
        conjunto_vertices = set(vertices)
        for arista in aristas:
            if not isinstance(arista, Arista):
                raise TypeError("Todas las aristas deben ser instancias de Arista.")
            if arista.identificador in identificadores:
                raise ValueError("Los identificadores de aristas deben ser únicos.")
            identificadores.add(arista.identificador)
            if (
                arista.origen not in conjunto_vertices
                or arista.destino not in conjunto_vertices
            ):
                raise ValueError("Los extremos de cada arista deben existir en el grafo.")

        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "aristas", aristas)
