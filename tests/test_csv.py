"""Carga de CSV mediante las interfaces públicas de lectura y procesamiento."""

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from tempfile import TemporaryDirectory

from arboles_de_red import (
    Arista,
    Entrada,
    EstimacionesPERT,
    Grafo,
    LectorTexto,
    ParametrosCPM,
    ParametrosPERT,
    ProcesadorConexionesCSV,
    ProcesadorCPMCSV,
    ProcesadorGrafo,
    ProcesadorPERTCSV,
)
from test_algoritmo import AlgoritmoEjemplo, ParametrosEjemplo
from test_componentes import VisualizadorEnMemoria


class LecturaCSVTests(unittest.TestCase):
    def test_lee_utf8_con_o_sin_bom_sin_interpretar_el_contenido(self):
        contenido = "actividad,duracion,predecesoras\nDiseño,3,\n"
        with TemporaryDirectory(dir=Path(__file__).parent) as carpeta:
            ruta = Path(carpeta) / "red.csv"
            for codificacion in ("utf-8", "utf-8-sig"):
                for argumento in (ruta, str(ruta)):
                    with self.subTest(codificacion=codificacion, ruta=argumento):
                        ruta.write_text(contenido, encoding=codificacion)
                        self.assertEqual(LectorTexto().leer(argumento), contenido)


class ConexionesCSVTests(unittest.TestCase):
    def test_carga_grafos_de_diez_y_doscientos_vertices(self):
        for cantidad in (10, 200):
            with self.subTest(vertices=cantidad):
                contenido = "origen,destino,peso\n" + "".join(
                    f"N{indice},N{indice + 1},1\n"
                    for indice in range(cantidad - 1)
                )
                grafo = ProcesadorConexionesCSV().procesar(contenido)

                self.assertEqual(len(grafo.vertices), cantidad)
                self.assertEqual(len(grafo.aristas), cantidad - 1)
                self.assertEqual(grafo.vertices[0], "N0")
                self.assertEqual(grafo.vertices[-1], f"N{cantidad - 1}")

    def test_formato_de_tres_columnas_carga_conexiones_no_dirigidas(self):
        grafo = ProcesadorConexionesCSV().procesar("origen,destino,peso\nA,B,1.5\n")

        self.assertEqual(grafo.aristas, (Arista(0, "A", "B", 1.5, False),))

    def test_conserva_pesos_direccion_y_aristas_paralelas(self):
        contenido = (
            "origen,destino,peso,dirigida\n"
            "A,B,8,true\n"
            "A,B,8,true\n"
            "B,C,-2.5,false\n"
            "D,E,0,false\n"
        )
        procesador = ProcesadorConexionesCSV()

        entrada = procesador.preparar_entrada(contenido)

        self.assertEqual(
            entrada.grafo,
            Grafo(
                ("A", "B", "C", "D", "E"),
                (
                    Arista(0, "A", "B", 8, True),
                    Arista(1, "A", "B", 8, True),
                    Arista(2, "B", "C", -2.5, False),
                    Arista(3, "D", "E", 0, False),
                ),
            ),
        )
        self.assertIsNone(entrada.parametros)
        self.assertEqual(procesador.procesar(contenido), entrada.grafo)


class ActividadesCSVTests(unittest.TestCase):
    def test_una_actividad_sin_predecesoras_es_una_red_valida(self):
        casos = (
            (ProcesadorCPMCSV(), "actividad,duracion,predecesoras\nA,2,\n"),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,mas_probable,pesimista,predecesoras\nA,1,2,3,\n",
            ),
        )
        for procesador, contenido in casos:
            with self.subTest(procesador=type(procesador).__name__):
                entrada = procesador.preparar_entrada(contenido)
                self.assertEqual(entrada.grafo, Grafo(("A",), ()))

    def test_recargar_crea_entradas_nuevas_y_no_modifica_la_carga_anterior(self):
        procesador = ProcesadorCPMCSV()
        contenido = "actividad,duracion,predecesoras\nA,2,\nB,3,A\n"
        primera = procesador.preparar_entrada(contenido)
        repetida = procesador.preparar_entrada(contenido)
        segunda = procesador.preparar_entrada("actividad,duracion,predecesoras\nC,5,\n")

        self.assertIsNot(primera, repetida)
        self.assertIsNot(primera.grafo, repetida.grafo)
        self.assertIsNot(primera.parametros, repetida.parametros)
        self.assertEqual(primera.grafo.vertices, ("A", "B"))
        self.assertEqual(primera.parametros.duraciones, {"A": 2.0, "B": 3.0})
        self.assertEqual(segunda.grafo.vertices, ("C",))
        with self.assertRaises(FrozenInstanceError):
            primera.grafo = segunda.grafo
        with self.assertRaises(FrozenInstanceError):
            primera.grafo.vertices = ("C",)
        with self.assertRaises(FrozenInstanceError):
            primera.parametros.duraciones = {}
        with self.assertRaises(TypeError):
            primera.parametros.duraciones["A"] = 99.0

    def test_estimaciones_y_colecciones_no_pueden_modificarse_desde_fuera(self):
        duraciones = {"A": 2.0}
        estimaciones = {"A": EstimacionesPERT(1.0, 2.0, 9.0)}
        cpm = ParametrosCPM(duraciones)
        pert = ParametrosPERT(estimaciones)

        duraciones["A"] = 99.0
        estimaciones.clear()

        self.assertEqual(cpm.duraciones, {"A": 2.0})
        self.assertEqual(pert.estimaciones, {"A": EstimacionesPERT(1.0, 2.0, 9.0)})
        with self.assertRaises(TypeError):
            pert.estimaciones["A"] = EstimacionesPERT(4.0, 5.0, 6.0)
        with self.assertRaises(FrozenInstanceError):
            pert.estimaciones["A"].optimista = 99.0

    def test_pert_conserva_las_tres_estimaciones_originales_por_actividad(self):
        contenido = (
            "actividad,optimista,mas_probable,pesimista,predecesoras\n"
            "A,1,2,9,\n"
            "B,0,0,0,\n"
            "C,2.5,4,8,A;B\n"
            "Independiente,1,3,5,\n"
        )
        procesador = ProcesadorPERTCSV()

        entrada = procesador.preparar_entrada(contenido)

        self.assertEqual(entrada.grafo.vertices, ("A", "B", "C", "Independiente"))
        self.assertEqual(
            entrada.grafo.aristas,
            (Arista(0, "A", "C", None, True), Arista(1, "B", "C", None, True)),
        )
        self.assertIsInstance(entrada.parametros, ParametrosPERT)
        self.assertEqual(
            entrada.parametros.estimaciones,
            {
                "A": EstimacionesPERT(1.0, 2.0, 9.0),
                "B": EstimacionesPERT(0.0, 0.0, 0.0),
                "C": EstimacionesPERT(2.5, 4.0, 8.0),
                "Independiente": EstimacionesPERT(1.0, 3.0, 5.0),
            },
        )
        self.assertEqual(procesador.procesar(contenido), entrada.grafo)


class EjemplosCSVTests(unittest.TestCase):
    def test_el_grafo_cargado_se_puede_visualizar_y_usar_en_una_ejecucion(self):
        ruta = Path(__file__).resolve().parents[1] / "ejemplos" / "conexiones.csv"
        procesador: ProcesadorGrafo = ProcesadorConexionesCSV()
        visualizador = VisualizadorEnMemoria()
        grafo = procesador.procesar(LectorTexto().leer(ruta))

        visualizador.mostrar_grafo(grafo)
        resultado = AlgoritmoEjemplo().ejecutar(Entrada(grafo, ParametrosEjemplo("A")))
        visualizador.mostrar_resultado(grafo, resultado)

        self.assertEqual(resultado.solucion.peso_total, 8.0)
        self.assertEqual(resultado.pasos[0].vertices_destacados, ("A", "B"))
        self.assertIs(visualizador.grafos[0], grafo)
        self.assertIs(visualizador.resultados[0][1], resultado)

    def test_los_archivos_documentados_preparan_entradas_con_datos_completos(self):
        carpeta = Path(__file__).resolve().parents[1] / "ejemplos"
        lector = LectorTexto()

        conexiones = ProcesadorConexionesCSV().preparar_entrada(
            lector.leer(carpeta / "conexiones.csv")
        )
        cpm = ProcesadorCPMCSV().preparar_entrada(lector.leer(carpeta / "cpm.csv"))
        pert = ProcesadorPERTCSV().preparar_entrada(lector.leer(carpeta / "pert.csv"))

        self.assertEqual(conexiones.grafo.vertices, ("A", "B", "C"))
        self.assertEqual(
            conexiones.grafo.aristas,
            (
                Arista(0, "A", "B", 8, False),
                Arista(1, "A", "C", 3.5, True),
                Arista(2, "A", "B", 8, False),
            ),
        )
        self.assertEqual(cpm.grafo.vertices, ("A", "B", "C", "Independiente"))
        self.assertEqual(cpm.parametros.duraciones["C"], 4.5)
        self.assertEqual(pert.grafo, cpm.grafo)
        self.assertEqual(pert.parametros.estimaciones["C"], EstimacionesPERT(2, 4, 8))


class PrecedenciasCSVTests(unittest.TestCase):
    def test_cpm_asocia_duraciones_a_actividades_y_conserva_precedencias(self):
        contenido = (
            "actividad,duracion,predecesoras\n"
            "C,4.5,A;B\n"
            "A,2,\n"
            "B,3,A\n"
            "Independiente,0,\n"
        )
        procesador = ProcesadorCPMCSV()

        entrada = procesador.preparar_entrada(contenido)

        self.assertEqual(entrada.grafo.vertices, ("C", "A", "B", "Independiente"))
        self.assertEqual(
            entrada.grafo.aristas,
            (
                Arista(0, "A", "C", None, True),
                Arista(1, "B", "C", None, True),
                Arista(2, "A", "B", None, True),
            ),
        )
        self.assertIsInstance(entrada.parametros, ParametrosCPM)
        self.assertEqual(
            entrada.parametros.duraciones,
            {"C": 4.5, "A": 2.0, "B": 3.0, "Independiente": 0.0},
        )
        self.assertEqual(procesador.procesar(contenido), entrada.grafo)


if __name__ == "__main__":
    unittest.main()
