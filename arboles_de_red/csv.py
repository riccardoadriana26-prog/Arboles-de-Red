"""Procesadores CSV que conservan la topología y los datos de la entrada."""

from abc import abstractmethod

from .algoritmo import Entrada
from .grafo import Arista, Grafo
from .parametros import EstimacionesPERT, ParametrosCPM, ParametrosPERT
from .procesamiento import ProcesadorGrafo
from .validacion_csv import ValidacionCSV


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
        validacion = ValidacionCSV(contenido, ("origen", "destino", "peso"), ("dirigida",))
        for registro in validacion.filas:
            origen_valido = validacion.identificador(registro, "origen")
            destino_valido = validacion.identificador(registro, "destino")
            fila = registro.valores
            if origen_valido and destino_valido and fila["origen"] == fila["destino"]:
                validacion.agregar(registro.linea, "destino", "No se admiten lazos.")
            validacion.numero(registro, "peso")
            if fila.get("dirigida", "false") not in ("true", "false"):
                validacion.agregar(registro.linea, "dirigida", "La dirección debe ser true o false.")
        validacion.comprobar()
        vertices: dict[str, None] = {}
        aristas: list[Arista] = []
        for registro in validacion.filas:
            fila = registro.valores
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
        validacion = ValidacionCSV(contenido, ("actividad", "duracion", "predecesoras"))
        validacion.actividades()
        for fila in validacion.filas:
            validacion.numero(fila, "duracion", no_negativo=True)
        validacion.comprobar()
        filas = [fila.valores for fila in validacion.filas]
        grafo = _grafo_actividades(filas)
        parametros = ParametrosCPM(
            {fila["actividad"]: float(fila["duracion"]) for fila in filas}
        )
        return Entrada(grafo, parametros)


class ProcesadorPERTCSV(ProcesadorCSV[ParametrosPERT]):
    """Lee actividades PERT y conserva las tres estimaciones sin resolverlas."""

    def preparar_entrada(self, contenido: str) -> Entrada[ParametrosPERT]:
        validacion = ValidacionCSV(
            contenido, ("actividad", "optimista", "mas_probable", "pesimista", "predecesoras")
        )
        validacion.actividades()
        for fila in validacion.filas:
            optimista = validacion.numero(fila, "optimista", no_negativo=True)
            probable = validacion.numero(fila, "mas_probable", no_negativo=True)
            pesimista = validacion.numero(fila, "pesimista", no_negativo=True)
            if optimista is not None and probable is not None and optimista > probable:
                validacion.agregar(
                    fila.linea, "mas_probable", "Debe cumplirse optimista <= mas_probable."
                )
            if probable is not None and pesimista is not None and probable > pesimista:
                validacion.agregar(
                    fila.linea, "pesimista", "Debe cumplirse mas_probable <= pesimista."
                )
        validacion.comprobar()
        filas = [fila.valores for fila in validacion.filas]
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
