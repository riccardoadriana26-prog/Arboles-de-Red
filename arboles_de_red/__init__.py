"""Modelo y contrato compartidos para los algoritmos de redes."""

from .algoritmo import Algoritmo, AlgoritmoNoAplicableError, Entrada, Paso, Resultado
from .grafo import Arista, Grafo

__all__ = [
    "Algoritmo",
    "AlgoritmoNoAplicableError",
    "Arista",
    "Entrada",
    "Grafo",
    "Paso",
    "Resultado",
]
