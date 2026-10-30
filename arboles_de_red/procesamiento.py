"""Contrato para validar e interpretar texto y construir el modelo común."""

from abc import ABC, abstractmethod

from .grafo import Grafo
from arboles_de_red.aplicabilidad import (
    CondicionesCPM,
    CondicionesArbolExpansion,
    CondicionesDijkstra,
    CondicionesFlujoMaximo,
    CondicionesPERT,
)
from arboles_de_red.parametros import Entrada, Resultado

from .cpm import CPM
from .arbol_expansion import Prim, Kruskal
from .dijkstra import Dijkstra
from .flujo_maximo import FordFulkerson
from .pert import PERT

class ProcesadorGrafo(ABC):
    """Construye un grafo desde texto, sin acceder a archivos ni ejecutar algoritmos."""

    @abstractmethod
    def procesar(self, contenido: str) -> Grafo:
        """Valida e interpreta el contenido y devuelve un grafo si es válido.

        Las reglas del formato y los errores de validación corresponden a la
        implementación concreta. Las condiciones de aplicación de cada
        algoritmo se comprueban al resolver, mediante el contrato Algoritmo.
        """



def ejecutar_algoritmo_seleccionado(entrada_original: Entrada, nombre_algoritmo: str):
    # 1. Seleccionar el conjunto de condiciones específico del algoritmo
    if nombre_algoritmo == "CPM":
        condiciones = CondicionesCPM()
    elif nombre_algoritmo in ("ArbolExpansion", "Prim", "Kruskal"):
        condiciones = CondicionesArbolExpansion()
    elif nombre_algoritmo == "Dijkstra":
        condiciones = CondicionesDijkstra()
    elif nombre_algoritmo == "FlujoMaximo":
        condiciones = CondicionesFlujoMaximo()
    elif nombre_algoritmo == "PERT":
        condiciones = CondicionesPERT()
    else:
        raise ValueError(f"Algoritmo desconocido: {nombre_algoritmo}")

    # 2. Cada ejecución valida sus propias condiciones de manera independiente
    if not condiciones.es_aplicable(entrada_original):
        # 3. Se informa si los datos no bastan, SIN sustituir ni modificar la carga original
        motivo = condiciones.motivo_inaplicabilidad(entrada_original)
        print(f"Aviso de compatibilidad: Los datos cargados no bastan para {nombre_algoritmo}. Motivo: {motivo}")
        return None  # Conserva la entrada original intacta

    # 4. Si es aplicable, se procede con la resolución usando las clases correctas
    if nombre_algoritmo == "CPM":
        return CPM().resolver(entrada_original)
    elif nombre_algoritmo == "ArbolExpansion" or nombre_algoritmo == "Prim":
        return Prim().resolver(entrada_original)  # O Kruskal(), según prefieras por defecto
    elif nombre_algoritmo == "Kruskal":
        return Kruskal().resolver(entrada_original)
    elif nombre_algoritmo == "Dijkstra":
        return Dijkstra().resolver(entrada_original)
    elif nombre_algoritmo == "FlujoMaximo":
        return FordFulkerson().resolver(entrada_original)
    elif nombre_algoritmo == "PERT":
        return PERT().resolver(entrada_original)
