"""Modelo y contratos de lectura, procesamiento, resolución y visualización."""

from .algoritmo import (
    Algoritmo,
    AlgoritmoNoAplicableError,
    CondicionesAplicacion,
    Entrada,
    Paso,
    Resultado,
)
from .aplicabilidad import (
    CondicionesArbolExpansion,
    CondicionesCPM,
    CondicionesDijkstra,
    CondicionesFlujoMaximo,
    CondicionesPERT,
)
from .csv import (
    ProcesadorConexionesCSV,
    ProcesadorCPMCSV,
    ProcesadorCSV,
    ProcesadorPERTCSV,
)
from .catedra import crear_registro_catedra, crear_registro_predeterminado
from ._numeros import ErrorCalculoNumerico
from .arbol_expansion import DetalleArbolExpansion, Kruskal, Prim, SolucionArbolExpansion
from .cpm import CPM, DetalleCPM, RutasCriticas, SolucionCPM, TiemposActividad
from .dijkstra import DetalleDijkstra, Dijkstra, SolucionDijkstra
from .flujo_maximo import (
    ActualizacionResidual,
    DetalleFlujoMaximo,
    FordFulkerson,
    SolucionFlujoMaximo,
    TramoAumento,
)
from .grafo import Arista, Grafo
from .lectura import LectorArchivo, LectorTexto
from .parametros import (
    EstimacionesPERT,
    ParametrosCPM,
    ParametrosDijkstra,
    ParametrosFlujoMaximo,
    ParametrosPERT,
)
from .procesamiento import ProcesadorGrafo
from .pert import DetalleEstimacionPERT, DetallePERT, PERT, SolucionPERT, VariabilidadRutaPERT
from .registro import (
    EjecucionPreparada,
    ErrorPreparacionEntrada,
    RegistroAlgoritmo,
    RegistroAlgoritmos,
)
from .validacion_csv import DiagnosticoCSV, ErrorValidacionCSV
from .seleccion import OpcionAlgoritmo, SeleccionAlgoritmo, SelectorAlgoritmos
from .visualizacion import Visualizador

__all__ = [
    "ActualizacionResidual",
    "Algoritmo",
    "AlgoritmoNoAplicableError",
    "Arista",
    "CondicionesAplicacion",
    "CondicionesArbolExpansion",
    "CondicionesCPM",
    "CondicionesDijkstra",
    "CondicionesFlujoMaximo",
    "CondicionesPERT",
    "CPM",
    "DetalleArbolExpansion",
    "DetalleCPM",
    "DetalleDijkstra",
    "DetalleEstimacionPERT",
    "DetalleFlujoMaximo",
    "DetallePERT",
    "DiagnosticoCSV",
    "Dijkstra",
    "Entrada",
    "EjecucionPreparada",
    "ErrorValidacionCSV",
    "ErrorPreparacionEntrada",
    "ErrorCalculoNumerico",
    "EstimacionesPERT",
    "Grafo",
    "FordFulkerson",
    "Kruskal",
    "LectorArchivo",
    "LectorTexto",
    "OpcionAlgoritmo",
    "ParametrosCPM",
    "ParametrosDijkstra",
    "ParametrosFlujoMaximo",
    "ParametrosPERT",
    "Paso",
    "PERT",
    "Prim",
    "ProcesadorConexionesCSV",
    "ProcesadorCPMCSV",
    "ProcesadorCSV",
    "ProcesadorGrafo",
    "ProcesadorPERTCSV",
    "Resultado",
    "RegistroAlgoritmo",
    "RegistroAlgoritmos",
    "RutasCriticas",
    "SeleccionAlgoritmo",
    "SelectorAlgoritmos",
    "SolucionArbolExpansion",
    "SolucionCPM",
    "SolucionDijkstra",
    "SolucionFlujoMaximo",
    "SolucionPERT",
    "TiemposActividad",
    "TramoAumento",
    "VariabilidadRutaPERT",
    "Visualizador",
    "crear_registro_catedra",
    "crear_registro_predeterminado",
]
