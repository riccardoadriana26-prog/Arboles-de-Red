"""Contrato de presentación del grafo y de los resultados de una resolución."""

from abc import ABC, abstractmethod

from .algoritmo import Resultado
from .grafo import Grafo


class Visualizador[SolucionT, DetalleT](ABC):
    """Presenta datos del modelo sin leer archivos, procesarlos ni resolverlos."""

    @abstractmethod
    def mostrar_grafo(self, grafo: Grafo) -> None:
        """Presenta el grafo original, antes de ejecutar un algoritmo."""

    @abstractmethod
    def mostrar_resultado(
        self, grafo: Grafo, resultado: Resultado[SolucionT, DetalleT]
    ) -> None:
        """Presenta la solución y sus pasos en el contexto del grafo original.

        Recibe el resultado ya calculado; no ejecuta el algoritmo. La tecnología
        de presentación y los controles de recorrido se definirán en sus issues.
        """
