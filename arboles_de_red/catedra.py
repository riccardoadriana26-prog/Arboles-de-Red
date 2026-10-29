"""Composición de los seis registros de la consigna y sus parámetros tipados."""

from collections.abc import Callable, Mapping

from .algoritmo import Algoritmo, Entrada
from .arbol_expansion import Kruskal, Prim
from .cpm import CPM
from .dijkstra import Dijkstra
from .flujo_maximo import FordFulkerson
from .pert import PERT
from .parametros import (
    ParametrosCPM,
    ParametrosDijkstra,
    ParametrosFlujoMaximo,
    ParametrosPERT,
)
from .registro import ErrorPreparacionEntrada, RegistroAlgoritmo, RegistroAlgoritmos


def _opciones_permitidas(opciones: Mapping[str, str], permitidas: tuple[str, ...]) -> None:
    extras = [campo for campo in opciones if campo not in permitidas]
    if extras:
        raise ErrorPreparacionEntrada(f"No se admiten estos parámetros: {', '.join(extras)}.")


def _opcion_obligatoria(opciones: Mapping[str, str], nombre: str) -> str:
    valor = opciones.get(nombre)
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorPreparacionEntrada(f"Falta el parámetro '{nombre}' o no es texto no vacío.")
    return valor


def _sin_parametros(carga: Entrada[object], opciones: Mapping[str, str]) -> None:
    _opciones_permitidas(opciones, ())
    return None


def _parametros_dijkstra(
    carga: Entrada[object], opciones: Mapping[str, str]
) -> ParametrosDijkstra:
    _opciones_permitidas(opciones, ("origen", "destino"))
    origen = _opcion_obligatoria(opciones, "origen")
    destino = _opcion_obligatoria(opciones, "destino") if "destino" in opciones else None
    return ParametrosDijkstra(origen, destino)


def _parametros_flujo(
    carga: Entrada[object], opciones: Mapping[str, str]
) -> ParametrosFlujoMaximo:
    _opciones_permitidas(opciones, ("fuente", "sumidero"))
    return ParametrosFlujoMaximo(
        _opcion_obligatoria(opciones, "fuente"), _opcion_obligatoria(opciones, "sumidero")
    )


def _parametros_carga[ParametrosT](
    carga: Entrada[object], opciones: Mapping[str, str], tipo: type[ParametrosT], nombre: str
) -> ParametrosT:
    _opciones_permitidas(opciones, ())
    if not isinstance(carga.parametros, tipo):
        raise ErrorPreparacionEntrada(f"La carga no contiene los datos de actividades de {nombre}.")
    return carga.parametros


def crear_registro_catedra[
    PrimSolucionT, PrimDetalleT, KruskalSolucionT, KruskalDetalleT,
    DijkstraSolucionT, DijkstraDetalleT, FlujoSolucionT, FlujoDetalleT,
    CPMSolucionT, CPMDetalleT, PERTSolucionT, PERTDetalleT,
](
    *,
    prim: Callable[[], Algoritmo[None, PrimSolucionT, PrimDetalleT]],
    kruskal: Callable[[], Algoritmo[None, KruskalSolucionT, KruskalDetalleT]],
    dijkstra: Callable[[], Algoritmo[ParametrosDijkstra, DijkstraSolucionT, DijkstraDetalleT]],
    flujo_maximo: Callable[[], Algoritmo[ParametrosFlujoMaximo, FlujoSolucionT, FlujoDetalleT]],
    cpm: Callable[[], Algoritmo[ParametrosCPM, CPMSolucionT, CPMDetalleT]],
    pert: Callable[[], Algoritmo[ParametrosPERT, PERTSolucionT, PERTDetalleT]],
) -> RegistroAlgoritmos:
    """Conecta fábricas de implementaciones; cada fábrica debe crear una instancia nueva."""
    registro = RegistroAlgoritmos()
    registro.registrar(RegistroAlgoritmo("prim", "Prim", prim, _sin_parametros))
    registro.registrar(RegistroAlgoritmo("kruskal", "Kruskal", kruskal, _sin_parametros))
    registro.registrar(RegistroAlgoritmo("dijkstra", "Dijkstra", dijkstra, _parametros_dijkstra))
    registro.registrar(RegistroAlgoritmo(
        "flujo_maximo", "Flujo Máximo (Ford–Fulkerson)", flujo_maximo, _parametros_flujo,
    ))
    registro.registrar(RegistroAlgoritmo(
        "cpm", "CPM", cpm,
        lambda carga, opciones: _parametros_carga(carga, opciones, ParametrosCPM, "CPM"),
    ))
    registro.registrar(RegistroAlgoritmo(
        "pert", "PERT", pert,
        lambda carga, opciones: _parametros_carga(carga, opciones, ParametrosPERT, "PERT"),
    ))
    return registro


def crear_registro_predeterminado() -> RegistroAlgoritmos:
    """Catálogo de la aplicación con las seis implementaciones reales del issue #6."""
    return crear_registro_catedra(
        prim=Prim, kruskal=Kruskal, dijkstra=Dijkstra,
        flujo_maximo=FordFulkerson, cpm=CPM, pert=PERT,
    )
