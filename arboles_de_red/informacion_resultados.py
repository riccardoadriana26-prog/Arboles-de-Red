"""Información final tipada, sin interfaz, pasos ni fórmulas de los algoritmos."""

from dataclasses import dataclass
from itertools import islice
from typing import Literal

from ._numeros import ErrorCalculoNumerico
from .algoritmo import Entrada, Resultado
from .pert import VariabilidadRutaPERT
from .proyeccion_resultados import (
    IdentificadorAlgoritmo, ProyeccionArbol, ProyeccionDijkstra, ProyeccionFlujo,
    ProyeccionCPM, ProyeccionPERT, proyectar_resultado,
)


MAXIMO_RUTAS = 10


@dataclass(frozen=True, slots=True)
class InformacionGeneral:
    vertices_originales: int
    aristas_originales: int


@dataclass(frozen=True, slots=True)
class InformacionArbol:
    algoritmo: Literal["prim", "kruskal"]
    general: InformacionGeneral
    aristas_arbol: int
    peso_total: float


@dataclass(frozen=True, slots=True)
class InformacionDijkstra:
    algoritmo: Literal["dijkstra"]
    general: InformacionGeneral
    origen: str
    destino: str | None
    ruta: tuple[str, ...] | None
    costo: float | None
    condicion: Literal["sin_consulta", "alcanzable", "inalcanzable"]


@dataclass(frozen=True, slots=True)
class FilaFlujo:
    identificador: int
    origen: str
    destino: str
    dirigida: bool
    capacidad_original: float
    flujo: float


@dataclass(frozen=True, slots=True)
class InformacionFlujo:
    algoritmo: Literal["flujo_maximo"]
    general: InformacionGeneral
    flujo_maximo: float
    arcos: tuple[FilaFlujo, ...]


@dataclass(frozen=True, slots=True)
class FilaActividadCPM:
    actividad: str
    ic: float
    tc: float
    il: float
    tl: float
    holgura: float


@dataclass(frozen=True, slots=True)
class RutasMostradas:
    cantidad_total: int
    rutas: tuple[tuple[str, ...], ...]
    hay_mas: bool


@dataclass(frozen=True, slots=True)
class InformacionCPM:
    algoritmo: Literal["cpm"]
    general: InformacionGeneral
    duracion_proyecto: float
    rutas_criticas: RutasMostradas
    actividades: tuple[FilaActividadCPM, ...]


@dataclass(frozen=True, slots=True)
class FilaActividadPERT:
    actividad: str
    optimista: float
    mas_probable: float
    pesimista: float
    tiempo_esperado: float
    varianza: float
    ic: float
    tc: float
    il: float
    tl: float
    holgura: float


@dataclass(frozen=True, slots=True)
class ErrorVariabilidadPERT:
    ruta: tuple[str, ...]
    mensaje: str
    tipo: Literal["ErrorCalculoNumerico"] = "ErrorCalculoNumerico"


@dataclass(frozen=True, slots=True)
class VariabilidadCompleta:
    valores: tuple[VariabilidadRutaPERT, ...]


@dataclass(frozen=True, slots=True)
class VariabilidadInterrumpida:
    valores: tuple[VariabilidadRutaPERT, ...]
    error: ErrorVariabilidadPERT
    rutas_no_evaluadas: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class InformacionPERT:
    algoritmo: Literal["pert"]
    general: InformacionGeneral
    duracion_esperada: float
    rutas_criticas: RutasMostradas
    actividades: tuple[FilaActividadPERT, ...]
    variabilidad: VariabilidadCompleta | VariabilidadInterrumpida


type InformacionResultado = (
    InformacionArbol | InformacionDijkstra | InformacionFlujo | InformacionCPM | InformacionPERT
)


def _rutas(solucion, limite: int) -> RutasMostradas:
    red = solucion.rutas_criticas
    rutas = tuple(islice(red, limite))
    return RutasMostradas(red.cantidad, rutas, red.cantidad > len(rutas))


def _variabilidad(solucion, rutas: RutasMostradas) -> VariabilidadCompleta | VariabilidadInterrumpida:
    valores = []
    consulta = solucion.variabilidad_rutas()
    for indice, ruta in enumerate(rutas.rutas):
        try:
            valor = next(consulta)
        except ErrorCalculoNumerico as error:
            # El generador del núcleo se cierra al fallar. No se reintenta ni se
            # inventan métricas para las rutas posteriores: quedan identificadas.
            return VariabilidadInterrumpida(
                tuple(valores), ErrorVariabilidadPERT(ruta, str(error)), rutas.rutas[indice + 1:],
            )
        except StopIteration as error:
            raise ValueError("La consulta de variabilidad PERT omite una ruta crítica mostrada.") from error
        if valor.actividades != ruta:
            raise ValueError("La variabilidad PERT no corresponde a la ruta crítica mostrada.")
        valores.append(valor)
    return VariabilidadCompleta(tuple(valores))


def obtener_informacion_resultado(
    entrada: Entrada[object], resultado: Resultado[object, object],
    algoritmo: IdentificadorAlgoritmo, *, destino: str | None = None, limite_rutas: int = MAXIMO_RUTAS,
) -> InformacionResultado:
    """Consulta la solución final sin consumir pasos ni ejecutar resolutores.

    ``limite_rutas`` es un entero entre 1 y 10 inclusive (no admite bool).
    Limita rutas y variabilidades por igual, sin enumerar una ruta adicional.
    La variabilidad procede de la API del núcleo; un error numérico conserva
    los resultados previos y declara explícitamente las rutas no evaluadas.
    CPM no publica duraciones originales: subsiste la limitación de HU-08 para
    comprobar su correspondencia sin inferirlas desde tiempos derivados.
    """
    if isinstance(limite_rutas, bool) or not isinstance(limite_rutas, int) or not 1 <= limite_rutas <= MAXIMO_RUTAS:
        raise ValueError("limite_rutas debe ser un entero entre 1 y 10.")
    p = proyectar_resultado(entrada, resultado, algoritmo, destino=destino)
    general = InformacionGeneral(len(entrada.grafo.vertices), len(entrada.grafo.aristas))
    if isinstance(p, ProyeccionArbol):
        return InformacionArbol(p.algoritmo, general, len(p.aristas), p.peso_total)
    if isinstance(p, ProyeccionDijkstra):
        condicion = "sin_consulta" if p.destino is None else "inalcanzable" if p.ruta is None else "alcanzable"
        return InformacionDijkstra(p.algoritmo, general, p.origen, p.destino, p.ruta, p.costo, condicion)
    if isinstance(p, ProyeccionFlujo):
        filas = tuple(FilaFlujo(a.identificador, a.origen, a.destino, a.dirigida,
                               p.arcos[a.identificador].capacidad_original, p.arcos[a.identificador].flujo)
                      for a in entrada.grafo.aristas)
        return InformacionFlujo(p.algoritmo, general, p.flujo_maximo, filas)
    rutas = _rutas(resultado.solucion, limite_rutas)
    if isinstance(p, ProyeccionCPM):
        filas = tuple(FilaActividadCPM(v, t.ic, t.tc, t.il, t.tl, t.holgura)
                      for v in entrada.grafo.vertices for t in (p.actividades[v],))
        return InformacionCPM(p.algoritmo, general, p.duracion_proyecto, rutas, filas)
    if isinstance(p, ProyeccionPERT):
        filas = tuple(FilaActividadPERT(v, e.optimista, e.mas_probable, e.pesimista,
                                       p.tiempos_esperados[v], p.varianzas[v],
                                       t.ic, t.tc, t.il, t.tl, t.holgura)
                      for v in entrada.grafo.vertices
                      for e, t in ((p.estimaciones[v], p.actividades[v]),))
        return InformacionPERT(p.algoritmo, general, p.duracion_esperada, rutas, filas,
                               _variabilidad(resultado.solucion, rutas))
    raise TypeError(f"Proyección no admitida: {type(p).__name__}.")
