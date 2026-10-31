"""Información de soluciones reales, con enumeración acotada y sin interfaz."""

from dataclasses import FrozenInstanceError, replace
from math import sqrt
from unittest.mock import patch

import pytest

from arboles_de_red._numeros import ErrorCalculoNumerico
from arboles_de_red.algoritmo import Entrada, Resultado
from arboles_de_red.arbol_expansion import Prim, Kruskal
from arboles_de_red.cpm import CPM, RutasCriticas
from arboles_de_red.dijkstra import Dijkstra
from arboles_de_red.flujo_maximo import FordFulkerson
from arboles_de_red.grafo import Arista, Grafo
from arboles_de_red.informacion_resultados import (
    obtener_informacion_resultado, VariabilidadCompleta, VariabilidadInterrumpida,
)
from arboles_de_red.parametros import (
    ParametrosCPM, ParametrosPERT, EstimacionesPERT, ParametrosDijkstra, ParametrosFlujoMaximo,
)
from arboles_de_red.pert import PERT, SolucionPERT


def conexiones(vertices="ABCD", dirigida=False):
    return Grafo(tuple(vertices), tuple(Arista(i, u, v, w, dirigida) for i, u, v, w in (
        (10, "A", "B", 5), (11, "A", "B", 0), (20, "B", "C", 2),
        (30, "A", "C", 4), (40, "C", "D", 1), (50, "D", "A", 0),
    )))


def aon(pert=False, exponencial=False):
    if exponencial:
        vertices = tuple(f"V{i}" for i in range(200))
        enlaces = [(vertices[i], vertices[j]) for i in range(198)
                   for j in range((i // 2 + 1) * 2, (i // 2 + 1) * 2 + 2)]
    else:
        vertices, enlaces = ("A", "B", "C"), [("A", "C"), ("B", "C")]
    grafo = Grafo(vertices, tuple(Arista(i, u, v, None, True) for i, (u, v) in enumerate(enlaces)))
    if pert:
        datos = dict.fromkeys(vertices, EstimacionesPERT(0, 1, 2)) if exponencial else {
            "A": EstimacionesPERT(0, 3, 6), "B": EstimacionesPERT(3, 3, 3), "C": EstimacionesPERT(0, 0, 0),
        }
        return Entrada(grafo, ParametrosPERT(datos))
    return Entrada(grafo, ParametrosCPM(dict.fromkeys(vertices, 1)))


@pytest.mark.parametrize("nombre,clase", [("prim", Prim), ("kruskal", Kruskal)])
def test_arbol_conteos_originales_peso_directo_sin_sumar(nombre, clase):
    entrada = Entrada(conexiones(), None)
    resultado = clase().ejecutar(entrada)
    # El contrato publica el peso: esta capa no debe decidirlo ni sumarlo otra vez.
    resultado = Resultado(replace(resultado.solucion, peso_total=1.7777777777777777), ())
    info = obtener_informacion_resultado(entrada, resultado, nombre)
    assert (info.general.vertices_originales, info.general.aristas_originales) == (4, 6)
    assert info.aristas_arbol == 3
    assert info.peso_total == 1.7777777777777777


@pytest.mark.parametrize("destino,condicion,ruta,costo", [
    (None, "sin_consulta", None, None), ("C", "alcanzable", ("A", "B", "C"), 2),
    ("A", "alcanzable", ("A",), 0), ("X", "inalcanzable", None, None),
])
def test_dijkstra_consulta_posterior_sin_resolver(destino, condicion, ruta, costo):
    entrada = Entrada(conexiones("ABCDX", True), ParametrosDijkstra("A"))
    resultado = Dijkstra().ejecutar(entrada)
    with patch.object(Dijkstra, "_resolver", side_effect=AssertionError("No resolver")):
        info = obtener_informacion_resultado(entrada, Resultado(resultado.solucion, ()), "dijkstra", destino=destino)
    assert (info.origen, info.destino, info.condicion, info.ruta, info.costo) == ("A", destino, condicion, ruta, costo)
    assert info.general.vertices_originales == 5
    assert not hasattr(info, "peso_total")


def test_dijkstra_con_destino_original():
    entrada = Entrada(conexiones(dirigida=True), ParametrosDijkstra("A", "C"))
    info = obtener_informacion_resultado(entrada, Dijkstra().ejecutar(entrada), "dijkstra")
    assert (info.destino, info.ruta, info.costo) == ("C", ("A", "B", "C"), 2)


def test_flujo_preserva_todos_los_ids_ceros_paralelas_y_antiparalelas():
    g = Grafo(("S", "A", "T"), tuple(Arista(i, u, v, w, True) for i, u, v, w in (
        (1, "S", "A", 1), (2, "S", "A", 2), (3, "A", "S", 1),
        (4, "A", "T", 2), (5, "S", "T", 0),
    )))
    entrada = Entrada(g, ParametrosFlujoMaximo("S", "T"))
    resultado = FordFulkerson().ejecutar(entrada)
    info = obtener_informacion_resultado(entrada, resultado, "flujo_maximo")
    assert info.flujo_maximo == 2
    assert info.general.aristas_originales == 5
    for fila, original in zip(info.arcos, g.aristas):
        assert (fila.identificador, fila.origen, fila.destino, fila.dirigida, fila.capacidad_original) == (
            original.identificador, original.origen, original.destino, True, original.peso)
        assert fila.flujo == resultado.solucion.flujo_por_arco[original.identificador]
    assert info.arcos[-1].capacidad_original == info.arcos[-1].flujo == 0
    assert info.arcos[2].flujo == 0


@pytest.mark.parametrize("pert,clase,nombre", [(False, CPM, "cpm"), (True, PERT, "pert")])
def test_planificacion_valores_finales_y_multiples_rutas(pert, clase, nombre):
    entrada = aon(pert)
    resultado = clase().ejecutar(entrada)
    info = obtener_informacion_resultado(entrada, resultado, nombre)
    assert info.rutas_criticas.cantidad_total == 2
    assert info.rutas_criticas.rutas == (("A", "C"), ("B", "C"))
    assert not info.rutas_criticas.hay_mas
    for fila in info.actividades:
        t = resultado.solucion.actividades[fila.actividad]
        assert (fila.ic, fila.tc, fila.il, fila.tl, fila.holgura) == (t.ic, t.tc, t.il, t.tl, t.holgura)
    if pert:
        assert info.duracion_esperada == 3
        assert isinstance(info.variabilidad, VariabilidadCompleta)
        assert [(v.varianza, v.desviacion_estandar) for v in info.variabilidad.valores] == [(1, 1), (0, 0)]
        for fila in info.actividades:
            e = resultado.solucion.estimaciones[fila.actividad]
            assert (fila.optimista, fila.mas_probable, fila.pesimista) == (e.optimista, e.mas_probable, e.pesimista)
            assert fila.tiempo_esperado == resultado.solucion.tiempos_esperados[fila.actividad]
            assert fila.varianza == resultado.solucion.varianzas[fila.actividad]
    else:
        assert info.duracion_proyecto == 2


@pytest.mark.parametrize("nombre,clase", [("prim", Prim), ("kruskal", Kruskal), ("cpm", CPM), ("pert", PERT)])
def test_un_solo_vertice(nombre, clase):
    parametros = (ParametrosCPM({"A": 0}) if nombre == "cpm" else
                  ParametrosPERT({"A": EstimacionesPERT(2, 2, 2)}) if nombre == "pert" else None)
    entrada = Entrada(Grafo(("A",), ()), parametros)
    info = obtener_informacion_resultado(entrada, clase().ejecutar(entrada), nombre)
    assert (info.general.vertices_originales, info.general.aristas_originales) == (1, 0)
    if nombre in ("cpm", "pert"):
        assert info.rutas_criticas.rutas == (("A",),)


@pytest.mark.parametrize("pert,clase,nombre", [(False, CPM, "cpm"), (True, PERT, "pert")])
def test_2_elevado_100_rutas_consume_solo_el_limite(pert, clase, nombre):
    entrada = aon(pert, True)
    resultado = clase().ejecutar(entrada)
    iterar = RutasCriticas.__iter__
    consumidas = []
    def limitado(self):
        for indice, ruta in enumerate(iterar(self)):
            assert indice < 10, "Se enumeró más allá del límite"
            consumidas.append(ruta)
            yield ruta
    with patch.object(RutasCriticas, "__iter__", limitado):
        info = obtener_informacion_resultado(entrada, resultado, nombre)
    assert info.rutas_criticas.cantidad_total == 2 ** 100
    assert len(info.rutas_criticas.rutas) == 10
    assert info.rutas_criticas.hay_mas
    assert len(consumidas) == (20 if pert else 10)  # Dos consultas acotadas: rutas y variabilidad.
    if pert:
        assert len(info.variabilidad.valores) == 10


def test_limite_menor_y_precision_pert_sin_redondeo():
    entrada = Entrada(Grafo(("A", "B"), (Arista(7, "A", "B", None, True),)),
                      ParametrosPERT({"A": EstimacionesPERT(1, 4, 9), "B": EstimacionesPERT(6, 6, 6)}))
    resultado = PERT().ejecutar(entrada)
    info = obtener_informacion_resultado(entrada, resultado, "pert", limite_rutas=1)
    assert info.actividades[0].tiempo_esperado == 4.333333333333333
    assert info.actividades[0].varianza == 1.7777777777777777
    assert info.duracion_esperada == 10.333333333333334
    v = info.variabilidad.valores[0]
    assert v.varianza == resultado.solucion.varianzas["A"]
    assert v.desviacion_estandar == sqrt(v.varianza)
    entrada = aon()
    info = obtener_informacion_resultado(entrada, CPM().ejecutar(entrada), "cpm", limite_rutas=1)
    assert len(info.rutas_criticas.rutas) == 1
    assert info.rutas_criticas.cantidad_total == 2 and info.rutas_criticas.hay_mas


def test_error_numerico_real_conserva_informacion_pert():
    entrada = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", None, True),)),
                      ParametrosPERT(dict.fromkeys(("A", "B"), EstimacionesPERT(0, 3e154, 6e154))))
    resultado = PERT().ejecutar(entrada)
    info = obtener_informacion_resultado(entrada, resultado, "pert")
    assert info.duracion_esperada == resultado.solucion.duracion_esperada
    assert len(info.actividades) == 2
    assert info.rutas_criticas.rutas == (("A", "B"),)
    assert isinstance(info.variabilidad, VariabilidadInterrumpida)
    assert info.variabilidad.error.ruta == ("A", "B")
    assert info.variabilidad.error.tipo == "ErrorCalculoNumerico"
    assert info.variabilidad.error.mensaje
    assert info.variabilidad.valores == ()


def test_error_intermedio_conserva_prefijo_y_declara_pendientes():
    entrada = Entrada(Grafo(("A", "B", "C"), ()), ParametrosPERT(dict.fromkeys("ABC", EstimacionesPERT(1, 1, 1))))
    resultado = PERT().ejecutar(entrada)
    primero = next(resultado.solucion.variabilidad_rutas())
    def interrumpida(self):
        yield primero
        raise ErrorCalculoNumerico("Desborde de prueba")
    with patch.object(SolucionPERT, "variabilidad_rutas", interrumpida):
        info = obtener_informacion_resultado(entrada, resultado, "pert")
    assert info.variabilidad.valores == (primero,)
    assert info.variabilidad.error.ruta == ("B",)
    assert info.variabilidad.rutas_no_evaluadas == (("C",),)
    assert len(info.rutas_criticas.rutas) == len(info.actividades) == 3


def test_filas_y_colecciones_de_informacion_son_inmutables():
    entrada = aon(True)
    info = obtener_informacion_resultado(entrada, PERT().ejecutar(entrada), "pert")
    assert isinstance(info.actividades, tuple)
    assert isinstance(info.rutas_criticas.rutas, tuple)
    assert all(isinstance(ruta, tuple) for ruta in info.rutas_criticas.rutas)
    with pytest.raises(FrozenInstanceError):
        info.actividades[0].varianza = 99
    with pytest.raises(FrozenInstanceError):
        info.variabilidad.valores[0].varianza = 99
    with pytest.raises(FrozenInstanceError):
        info.rutas_criticas.hay_mas = True


@pytest.mark.parametrize("limite", [0, -1, 11, 10**100, True, False, None, 1.5, "10"])
def test_limite_invalido(limite):
    with pytest.raises(ValueError, match="limite_rutas"):
        obtener_informacion_resultado(None, None, "cpm", limite_rutas=limite)


def test_validaciones_reutilizadas_y_objetos_no_mutados():
    entrada = Entrada(conexiones(dirigida=True), ParametrosDijkstra("A"))
    resultado = Dijkstra().ejecutar(entrada)
    antes = repr((entrada, resultado))
    with pytest.raises(ValueError):
        obtener_informacion_resultado(entrada, resultado, "prim")
    with pytest.raises(ValueError):
        obtener_informacion_resultado(entrada, resultado, "dijkstra", destino="Inexistente")
    info = obtener_informacion_resultado(entrada, resultado, "dijkstra", destino="C")
    assert info == obtener_informacion_resultado(entrada, Resultado(resultado.solucion, ()), "dijkstra", destino="C")
    assert repr((entrada, resultado)) == antes
    with pytest.raises(FrozenInstanceError):
        info.costo = 99


@pytest.mark.parametrize("nombre,clase", [("prim", Prim), ("kruskal", Kruskal), ("dijkstra", Dijkstra),
                                         ("flujo_maximo", FordFulkerson), ("cpm", CPM), ("pert", PERT)])
def test_seis_algoritmos_independientes_de_pasos_sin_reejecucion(nombre, clase):
    entrada = (aon(nombre == "pert") if nombre in ("cpm", "pert") else
               Entrada(conexiones(dirigida=nombre in ("dijkstra", "flujo_maximo")),
                       ParametrosDijkstra("A") if nombre == "dijkstra" else
                       ParametrosFlujoMaximo("A", "C") if nombre == "flujo_maximo" else None))
    resultado = clase().ejecutar(entrada)
    antes = repr((entrada, resultado))
    with patch.object(clase, "_resolver", side_effect=AssertionError("No reejecutar")):
        info = obtener_informacion_resultado(entrada, resultado, nombre)
        assert info == obtener_informacion_resultado(entrada, Resultado(resultado.solucion, ()), nombre)
    assert repr((entrada, resultado)) == antes
    with pytest.raises(FrozenInstanceError):
        info.general.vertices_originales = 0
