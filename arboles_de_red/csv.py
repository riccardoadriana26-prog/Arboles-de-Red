"""Procesadores CSV que conservan la topología y los datos de la entrada."""

from abc import abstractmethod
from csv import DictReader
from io import StringIO

from .algoritmo import Entrada
from .grafo import Arista, Grafo
from .parametros import EstimacionesPERT, ParametrosCPM, ParametrosPERT
from .procesamiento import ProcesadorGrafo


class ProcesadorCSV[ParametrosT](ProcesadorGrafo):
    """Permite obtener el grafo solo o junto con sus parámetros de carga."""

    def procesar(self, contenido: str) -> Grafo:
        return self.preparar_entrada(contenido).grafo

    @abstractmethod
    def preparar_entrada(self, contenido: str) -> Entrada[ParametrosT]:
        """Construye una entrada nueva sin leer archivos ni ejecutar algoritmos."""


class ProcesadorConexionesCSV(ProcesadorCSV[None]):
    """Lee conexiones ponderadas; los parámetros de ejecución se eligen aparte."""

    def preparar_entrada(self, contenido: str) -> Entrada[None]:
        vertices: dict[str, None] = {}
        aristas: list[Arista] = []
        for fila in DictReader(StringIO(contenido)):
            origen = fila["origen"]
            destino = fila["destino"]
            dirigida = {"true": True, "false": False}[fila.get("dirigida", "false")]
            vertices[origen] = None
            vertices[destino] = None
            aristas.append(
                Arista(len(aristas), origen, destino, float(fila["peso"]), dirigida)
            )
        return Entrada(Grafo(tuple(vertices), tuple(aristas)), None)


def _grafo_actividades(filas: list[dict[str, str]]) -> Grafo:
    vertices = tuple(fila["actividad"] for fila in filas)
    aristas: list[Arista] = []
    for fila in filas:
        for predecesora in fila["predecesoras"].split(";"):
            if predecesora.strip():
                aristas.append(
                    Arista(
                        len(aristas), predecesora.strip(), fila["actividad"], None, True
                    )
                )
    return Grafo(vertices, tuple(aristas))


class ProcesadorCPMCSV(ProcesadorCSV[ParametrosCPM]):
    """Lee actividades CPM, sus duraciones y sus predecesoras inmediatas."""

    def preparar_entrada(self, contenido: str) -> Entrada[ParametrosCPM]:
        filas = list(DictReader(StringIO(contenido)))
        grafo = _grafo_actividades(filas)
        parametros = ParametrosCPM(
            {fila["actividad"]: float(fila["duracion"]) for fila in filas}
        )
        return Entrada(grafo, parametros)


class ProcesadorPERTCSV(ProcesadorCSV[ParametrosPERT]):
    """Lee actividades PERT y conserva las tres estimaciones sin resolverlas."""

    def preparar_entrada(self, contenido: str) -> Entrada[ParametrosPERT]:
        filas = list(DictReader(StringIO(contenido)))
        grafo = _grafo_actividades(filas)
        parametros = ParametrosPERT(
            {
                fila["actividad"]: EstimacionesPERT(
                    float(fila["optimista"]),
                    float(fila["mas_probable"]),
                    float(fila["pesimista"]),
                )
                for fila in filas
            }
        )
        return Entrada(grafo, parametros)
