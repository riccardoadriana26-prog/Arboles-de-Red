"""Contrato para validar e interpretar texto y construir el modelo común."""

from abc import ABC, abstractmethod

from .grafo import Grafo


class ProcesadorGrafo(ABC):
    """Construye un grafo desde texto, sin acceder a archivos ni ejecutar algoritmos."""

    @abstractmethod
    def procesar(self, contenido: str) -> Grafo:
        """Valida e interpreta el contenido y devuelve un grafo si es válido.

        Las reglas del formato y los errores de validación corresponden a la
        implementación concreta. Las condiciones de aplicación de cada
        algoritmo se comprueban al resolver, mediante el contrato Algoritmo.
        """
