"""Casos de uso de la API: carga, selección, rechazo, repetición e independencia."""

import csv
import io
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, fields
from itertools import permutations
from pathlib import Path
from tempfile import TemporaryDirectory

from arboles_de_red import (
    AlgoritmoNoAplicableError, Arista, CondicionesDijkstra, CPM, Dijkstra, Entrada, ErrorPreparacionEntrada,
    ErrorValidacionCSV, EstimacionesPERT, FordFulkerson, Grafo, Kruskal, LectorTexto,
    PERT, ParametrosCPM, ParametrosDijkstra, ParametrosFlujoMaximo, ParametrosPERT,
    Prim, ProcesadorCPMCSV, ProcesadorConexionesCSV, ProcesadorPERTCSV, SelectorAlgoritmos,
)


def casos_validos():
    red = Grafo(tuple("ABC"), (Arista(10, "A", "B", 1, False), Arista(20, "B", "C", 2, False)))
    flujo = Grafo(("S", "T"), (Arista(70, "S", "T", .1, True), Arista(90, "S", "T", .2, True)))
    aon = Grafo(tuple("ABC"), (Arista(4, "A", "C", None, True), Arista(8, "B", "C", None, True)))
    return (
        (Prim(), Entrada(red, None)), (Kruskal(), Entrada(red, None)),
        (Dijkstra(), Entrada(red, ParametrosDijkstra("A", "C"))),
        (FordFulkerson(), Entrada(flujo, ParametrosFlujoMaximo("S", "T"))),
        (CPM(), Entrada(aon, ParametrosCPM({"A": 2, "B": 2, "C": 0}))),
        (PERT(), Entrada(aon, ParametrosPERT({"A": EstimacionesPERT(0, 2, 4),
                                            "B": EstimacionesPERT(2, 2, 2), "C": EstimacionesPERT(0, 0, 0)}))),
    )


class UsoCoreTests(unittest.TestCase):
    def test_matriz_de_compatibilidad_antes_de_ejecutar(self):
        vertices = ("A", "B")
        casos = (
            (Entrada(Grafo(vertices, (Arista(0, "A", "B", 2, False),)), None), (True, True, True, False, None, None)),
            (Entrada(Grafo(vertices, (Arista(0, "A", "B", 2, True),)), None), (False, False, True, True, None, None)),
            (Entrada(Grafo(vertices, (Arista(0, "A", "B", -2, False),)), None), (True, True, False, False, None, None)),
            (Entrada(Grafo(vertices, (Arista(0, "A", "B", None, True),)), ParametrosCPM({"A": 0, "B": 2})),
             (False, False, False, False, True, None)),
            (Entrada(Grafo(vertices, (Arista(0, "A", "B", None, True),)),
                     ParametrosPERT(dict.fromkeys(vertices, EstimacionesPERT(0, 0, 0)))),
             (False, False, False, False, None, True)),
            (Entrada(Grafo(vertices, ()), None), (False, False, True, True, None, None)),
            (Entrada(Grafo((), ()), None), (False, False, False, False, None, None)),
        )
        selector = SelectorAlgoritmos()
        ids = ("prim", "kruskal", "dijkstra", "flujo_maximo", "cpm", "pert")
        for numero, (carga, aplicables) in enumerate(casos):
            for identificador, esperado in zip(ids, aplicables):
                with self.subTest(carga=numero, algoritmo=identificador):
                    opciones = {"origen": "A", "destino": "B"} if identificador == "dijkstra" else (
                        {"fuente": "A", "sumidero": "B"} if identificador == "flujo_maximo" else {})
                    if esperado is None:
                        with self.assertRaises(ErrorPreparacionEntrada):
                            selector.seleccionar(identificador, carga, opciones)
                        continue
                    seleccion = selector.seleccionar(identificador, carga, opciones)
                    self.assertEqual(seleccion.identificador, identificador)
                    self.assertEqual(seleccion.puede_ejecutarse, esperado)
                    self.assertEqual(seleccion.motivo is None, esperado)
                    if esperado:
                        self.assertTrue(seleccion.ejecutar().pasos)
                    else:
                        with self.assertRaises(AlgoritmoNoAplicableError) as captura:
                            seleccion.ejecutar()
                        self.assertEqual(captura.exception.motivo, seleccion.motivo)

    def test_archivo_utf8_bom_saltos_de_linea_y_errores_de_lectura(self):
        with TemporaryDirectory(prefix="arboles-pruebas-") as carpeta:
            raiz = Path(carpeta).resolve()
            ruta = raiz / "conexiones.csv"
            for codificacion in ("utf-8", "utf-8-sig"):
                for salto in ("\n", "\r\n", "\r"):
                    with self.subTest(codificacion=codificacion, salto=repr(salto)):
                        ruta.write_bytes(("origen,destino,peso" + salto + "A,B,2" + salto).encode(codificacion))
                        contenido = LectorTexto().leer(ruta)
                        carga = ProcesadorConexionesCSV().preparar_entrada(contenido)
                        self.assertEqual(SelectorAlgoritmos().seleccionar("prim", carga).ejecutar().solucion.peso_total, 2)
            ruta.write_bytes(b"\xff\xfe\x80")
            with self.assertRaises(UnicodeDecodeError):
                LectorTexto().leer(ruta)
            with self.assertRaises(FileNotFoundError):
                LectorTexto().leer(raiz / "inexistente.csv")
            with self.assertRaises((PermissionError, IsADirectoryError)):
                LectorTexto().leer(raiz)

    def test_todas_las_permutaciones_de_columnas_con_y_sin_comillas(self):
        formatos = (
            (ProcesadorConexionesCSV(), {"origen": "A", "destino": "B", "peso": "2", "dirigida": "true"}),
            (ProcesadorCPMCSV(), {"actividad": "A", "duracion": "2", "predecesoras": ""}),
            (ProcesadorPERTCSV(), {"actividad": "A", "optimista": "1", "mas_probable": "2", "pesimista": "3", "predecesoras": ""}),
        )
        for procesador, datos in formatos:
            referencia = None
            for columnas in permutations(datos):
                for comillas in (csv.QUOTE_MINIMAL, csv.QUOTE_ALL):
                    with self.subTest(formato=type(procesador).__name__, columnas=columnas, comillas=comillas):
                        salida = io.StringIO(newline="")
                        escritor = csv.writer(salida, quoting=comillas, lineterminator="\r\n")
                        escritor.writerow(columnas)
                        escritor.writerow([datos[c] for c in columnas])
                        carga = procesador.preparar_entrada(salida.getvalue())
                        if referencia is None:
                            referencia = carga
                        self.assertEqual(carga, referencia)

    def test_error_de_carga_o_seleccion_no_destruye_una_ejecucion_anterior(self):
        procesador = ProcesadorConexionesCSV()
        texto = "origen,destino,peso\nA,B,2\n"
        carga = procesador.preparar_entrada(texto)
        selector = SelectorAlgoritmos()
        seleccion = selector.seleccionar("prim", carga)
        resultado = seleccion.ejecutar()
        for contenido in ("", "origen,destino,peso\nA,B,nan\n", "origen,destino,peso\nA,A,1\n"):
            with self.subTest(contenido=contenido):
                with self.assertRaises(ErrorValidacionCSV):
                    procesador.preparar_entrada(contenido)
                self.assertEqual(seleccion.ejecutar(), resultado)
        for identificador, opciones in (("dijkstra", {}), ("prim", {"origen": "A"}), ("cpm", {})):
            with self.subTest(algoritmo=identificador):
                with self.assertRaises(ErrorPreparacionEntrada):
                    selector.seleccionar(identificador, carga, opciones)
                self.assertEqual(seleccion.ejecutar(), resultado)
        self.assertEqual(procesador.preparar_entrada(texto), carga)
        self.assertEqual(seleccion.ejecutar(), resultado)

    def test_120_ejecuciones_concurrentes_comparten_instancia_sin_compartir_estado(self):
        casos = casos_validos()
        esperados = [algoritmo.ejecutar(entrada) for algoritmo, entrada in casos]

        def resolver(indice):
            algoritmo, entrada = casos[indice % len(casos)]
            return indice % len(casos), algoritmo.ejecutar(entrada)

        with ThreadPoolExecutor(max_workers=8) as ejecutor:
            for indice, resultado in ejecutor.map(resolver, range(120)):
                self.assertEqual(resultado, esperados[indice])
                self.assertIsNot(resultado, esperados[indice])

    def test_todas_las_soluciones_y_detalles_son_inmutables(self):
        for algoritmo, entrada in casos_validos():
            with self.subTest(algoritmo=type(algoritmo).__name__):
                resultado = algoritmo.ejecutar(entrada)
                for objeto in (resultado, resultado.solucion, resultado.pasos[0], resultado.pasos[0].detalle):
                    for campo in fields(objeto):
                        with self.assertRaises((FrozenInstanceError, AttributeError)):
                            setattr(objeto, campo.name, getattr(objeto, campo.name))
                for nombre in ("distancias", "predecesores", "flujo_por_arco", "actividades",
                               "estimaciones", "tiempos_esperados", "varianzas"):
                    mapa = getattr(resultado.solucion, nombre, None)
                    if mapa is not None:
                        with self.assertRaises(TypeError):
                            mapa["Nueva"] = 0
                if isinstance(algoritmo, (CPM, PERT)):
                    rutas = resultado.solucion.rutas_criticas
                    primer_iterador, segundo_iterador = iter(rutas), iter(rutas)
                    self.assertEqual(next(primer_iterador), next(segundo_iterador))
                    self.assertEqual(tuple(primer_iterador), tuple(segundo_iterador))
                    with self.assertRaises(TypeError):
                        rutas.sucesoras["Nueva"] = ()

    def test_el_modelo_rechaza_tipos_ambiguos_e_identificadores_invalidos(self):
        for identificador in (True, -1, 1.5, "0"):
            with self.subTest(identificador=identificador), self.assertRaises((TypeError, ValueError)):
                Arista(identificador, "A", "B", 1, True)
        for vertice in (None, 1, "", "A B", "A-B", "\x00"):
            with self.subTest(vertice=vertice), self.assertRaises((TypeError, ValueError)):
                Grafo((vertice,), ())
        with self.assertRaises(TypeError):
            Grafo(("A", "B"), (object(),))

    def test_consulta_de_inalcanzables_rechaza_parametros_invalidos_con_el_mismo_motivo(self):
        entrada = Entrada(Grafo(("A",), ()), ParametrosDijkstra("Inexistente"))
        condiciones = CondicionesDijkstra()
        with self.assertRaises(AlgoritmoNoAplicableError) as captura:
            condiciones.vertices_inalcanzables(entrada)
        self.assertEqual(captura.exception.motivo, condiciones.motivo_inaplicabilidad(entrada))

    def test_el_modelo_rechaza_pesos_fuera_del_rango_float(self):
        with self.assertRaises(ValueError):
            Arista(0, "A", "B", 10 ** 400, True)


if __name__ == "__main__":
    unittest.main()
