"""Contrato de lectura de archivos, independiente del formato del grafo."""

from abc import ABC, abstractmethod
from pathlib import Path


class LectorArchivo(ABC):
    """Obtiene texto sin interpretar ni validar su contenido como grafo."""

    @abstractmethod
    def leer(self, ruta: str | Path) -> str:
        """Devuelve el texto del archivo indicado por la ruta.

        La implementación concreta se encarga del acceso al archivo y de su
        decodificación. La interpretación del contenido pertenece al procesador.
        """
