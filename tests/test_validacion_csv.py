"""Diagnósticos observables desde las interfaces públicas de procesamiento CSV."""

import unittest

from arboles_de_red import (
    ErrorValidacionCSV,
    ProcesadorConexionesCSV,
    ProcesadorCPMCSV,
    ProcesadorPERTCSV,
)


class EncabezadoCSVTests(unittest.TestCase):
    def test_cada_estructura_exige_sus_columnas_y_rechaza_columnas_ajenas(self):
        casos = (
            (ProcesadorConexionesCSV(), "origen,destino,duracion\n", {"peso", "duracion"}),
            (
                ProcesadorCPMCSV(),
                "actividad,actividad,peso,predecesoras\n",
                {"actividad", "duracion", "peso"},
            ),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,optimista,predecesoras,tiempo_esperado\n",
                {"optimista", "mas_probable", "pesimista", "tiempo_esperado"},
            ),
        )
        for procesador, contenido, columnas in casos:
            with self.subTest(procesador=type(procesador).__name__):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    procesador.preparar_entrada(contenido)
                self.assertEqual({error.columna for error in captura.exception.errores}, columnas)

    def test_reune_columnas_faltantes_repetidas_y_no_admitidas(self):
        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorConexionesCSV().procesar("origen,origen,extra\nA,B,1\n")

        errores = captura.exception.errores
        self.assertIsInstance(errores, tuple)
        self.assertEqual(
            {(error.linea, error.columna) for error in errores},
            {(1, "destino"), (1, "peso"), (1, "origen"), (1, "extra")},
        )
        self.assertTrue(all(error.mensaje for error in errores))
        self.assertIn("Línea 1", str(captura.exception))


class EstructuraCSVTests(unittest.TestCase):
    def test_las_lineas_se_conservan_con_campos_entre_comillas_y_saltos_de_linea(self):
        contenido = 'origen,destino,peso\r\n"A\r\nX",B,1\r\nC,D,nan\r\n'

        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorConexionesCSV().procesar(contenido)

        self.assertEqual(
            [(error.linea, error.columna) for error in captura.exception.errores],
            [(2, "origen"), (4, "peso")],
        )

    def test_un_error_de_sintaxis_no_oculta_los_errores_de_filas_anteriores(self):
        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorConexionesCSV().procesar(
                'origen,destino,peso\nA,B,nan\n"C,D,1'
            )

        self.assertEqual(
            {(error.linea, error.columna) for error in captura.exception.errores},
            {(2, "peso"), (3, None)},
        )

    def test_un_encabezado_mal_formado_tambien_tiene_diagnostico(self):
        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorCPMCSV().procesar('"actividad,duracion,predecesoras')

        self.assertEqual(captura.exception.errores[0].linea, 1)
        self.assertIn("CSV mal formado", str(captura.exception))

    def test_las_comillas_mal_formadas_producen_un_diagnostico(self):
        for fila in ('"A,B,1', '"A"x,B,1'):
            with self.subTest(fila=fila):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    ProcesadorConexionesCSV().procesar("origen,destino,peso\n" + fila)
                self.assertEqual(captura.exception.errores[0].linea, 2)
                self.assertIn("CSV mal formado", captura.exception.errores[0].mensaje)

    def test_rechaza_archivos_sin_conexiones_ni_actividades(self):
        formatos = (
            (ProcesadorConexionesCSV(), "origen,destino,peso"),
            (ProcesadorCPMCSV(), "actividad,duracion,predecesoras"),
            (ProcesadorPERTCSV(), "actividad,optimista,mas_probable,pesimista,predecesoras"),
        )
        for procesador, encabezado in formatos:
            for contenido in ("", "\n\n", encabezado + "\n\n"):
                with self.subTest(procesador=type(procesador).__name__, contenido=contenido):
                    with self.assertRaises(ErrorValidacionCSV):
                        procesador.preparar_entrada(contenido)

    def test_informa_filas_incompletas_y_sobrantes_con_su_linea_fisica(self):
        contenido = "origen,destino,peso\n\nA,B\nB,C,2,extra\nC,D,3\n"

        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorConexionesCSV().preparar_entrada(contenido)

        self.assertEqual([error.linea for error in captura.exception.errores], [3, 4])
        self.assertTrue(all(error.columna is None for error in captura.exception.errores))


class ValoresConexionesCSVTests(unittest.TestCase):
    def test_reune_errores_de_valores_y_estructura_sin_devolver_un_grafo_parcial(self):
        contenido = (
            "origen,destino,peso,dirigida\n"
            "A,B,2,true\n"
            "A!,B,nan,si\n"
            "C,C,inf,false\n"
            "D,E,1\n"
            ",,texto,\n"
        )

        with self.assertRaises(ErrorValidacionCSV) as captura:
            ProcesadorConexionesCSV().preparar_entrada(contenido)

        self.assertEqual(
            {(error.linea, error.columna) for error in captura.exception.errores},
            {
                (3, "origen"), (3, "peso"), (3, "dirigida"),
                (4, "destino"), (4, "peso"), (5, None),
                (6, "origen"), (6, "destino"), (6, "peso"), (6, "dirigida"),
            },
        )


class ActividadesCSVTests(unittest.TestCase):
    def test_el_redondeo_no_oculta_duraciones_negativas_ni_estimaciones_desordenadas(self):
        casos = (
            (
                ProcesadorCPMCSV(),
                "actividad,duracion,predecesoras\nA,-1e-400,\n",
                {"duracion"},
            ),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,mas_probable,pesimista,predecesoras\nA,1e-400,0,1,\n",
                {"optimista", "mas_probable"},
            ),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,mas_probable,pesimista,predecesoras\n"
                "A,0,1.0000000000000000000001,1,\n",
                {"pesimista"},
            ),
        )
        for procesador, contenido, columnas in casos:
            with self.subTest(procesador=type(procesador).__name__, columnas=columnas):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    procesador.preparar_entrada(contenido)
                self.assertEqual(
                    {(error.linea, error.columna) for error in captura.exception.errores},
                    {(2, columna) for columna in columnas},
                )

    def test_pert_exige_tripletas_completas_finitas_no_negativas_y_ordenadas(self):
        casos = (
            ("-1", "2", "3", {"optimista"}),
            ("1", "-1", "3", {"mas_probable"}),
            ("1", "2", "-1", {"pesimista"}),
            ("3", "2", "1", {"mas_probable", "pesimista"}),
            ("nan", "2", "inf", {"optimista", "pesimista"}),
            ("", "texto", "1e309", {"optimista", "mas_probable", "pesimista"}),
        )
        for optimista, probable, pesimista, columnas in casos:
            with self.subTest(estimaciones=(optimista, probable, pesimista)):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    ProcesadorPERTCSV().procesar(
                        "actividad,optimista,mas_probable,pesimista,predecesoras\n"
                        f"A,{optimista},{probable},{pesimista},\n"
                    )
                self.assertEqual(
                    {error.columna for error in captura.exception.errores}, columnas
                )
                self.assertTrue(all(error.linea == 2 for error in captura.exception.errores))

    def test_cpm_exige_duracion_finita_no_negativa_y_reune_otros_errores(self):
        for duracion in ("", "-1", "nan", "inf", "-inf", "1e309", "texto"):
            with self.subTest(duracion=duracion):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    ProcesadorCPMCSV().procesar(
                        "actividad,duracion,predecesoras\n"
                        f"A,{duracion},Desconocida\n"
                    )
                self.assertEqual(
                    {(error.linea, error.columna) for error in captura.exception.errores},
                    {(2, "duracion"), (2, "predecesoras")},
                )

    def test_reune_identificadores_duplicados_y_predecesoras_invalidas_en_aon(self):
        casos = (
            (
                ProcesadorCPMCSV(),
                "actividad,duracion,predecesoras\n"
                "A,2,\nB,3,A;X\nA,1,\nInvalida!,2,\nC,2,C\nD,1,A;;B\n",
            ),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,mas_probable,pesimista,predecesoras\n"
                "A,1,2,3,\nB,1,2,3,A;X\nA,1,2,3,\nInvalida!,1,2,3,\n"
                "C,1,2,3,C\nD,1,2,3,A;;B\n",
            ),
        )
        for procesador, contenido in casos:
            with self.subTest(procesador=type(procesador).__name__):
                with self.assertRaises(ErrorValidacionCSV) as captura:
                    procesador.preparar_entrada(contenido)
                self.assertEqual(
                    {(error.linea, error.columna) for error in captura.exception.errores},
                    {(3, "predecesoras"), (4, "actividad"), (5, "actividad"),
                     (6, "predecesoras"), (7, "predecesoras")},
                )

class IntegridadCargaCSVTests(unittest.TestCase):
    def test_una_carga_invalida_no_modifica_la_anterior_y_permite_volver_a_cargar(self):
        casos = (
            (ProcesadorConexionesCSV(), "origen,destino,peso\nA,B,-2\n", "A,B,nan\n"),
            (ProcesadorCPMCSV(), "actividad,duracion,predecesoras\nA,0,\n", "A,-1,\n"),
            (
                ProcesadorPERTCSV(),
                "actividad,optimista,mas_probable,pesimista,predecesoras\nA,0,0,0,\n",
                "A,3,2,1,\n",
            ),
        )
        for procesador, contenido_valido, fila_invalida in casos:
            with self.subTest(procesador=type(procesador).__name__):
                anterior = procesador.preparar_entrada(contenido_valido)
                vertices = anterior.grafo.vertices
                aristas = anterior.grafo.aristas
                parametros = anterior.parametros
                invalido = contenido_valido.splitlines()[0] + "\n" + fila_invalida

                for cargar in (procesador.procesar, procesador.preparar_entrada):
                    with self.assertRaises(ErrorValidacionCSV):
                        cargar(invalido)

                self.assertIs(anterior.grafo.vertices, vertices)
                self.assertIs(anterior.grafo.aristas, aristas)
                self.assertIs(anterior.parametros, parametros)
                siguiente = procesador.preparar_entrada(contenido_valido)
                self.assertEqual(anterior, siguiente)
                self.assertIsNot(anterior.grafo, siguiente.grafo)

    def test_los_ciclos_y_la_desconexion_no_son_errores_del_csv(self):
        conexiones = ProcesadorConexionesCSV().procesar(
            "origen,destino,peso\nA,B,-2\nC,D,0\n"
        )
        cpm = ProcesadorCPMCSV().procesar(
            "actividad,duracion,predecesoras\nA,0,B\nB,1,A\nIndependiente,0,\n"
        )
        pert = ProcesadorPERTCSV().procesar(
            "actividad,optimista,mas_probable,pesimista,predecesoras\n"
            "A,0,0,0,B\nB,1,1,1,A\nIndependiente,0,0,0,\n"
        )

        self.assertEqual(conexiones.vertices, ("A", "B", "C", "D"))
        self.assertEqual(cpm.vertices, ("A", "B", "Independiente"))
        self.assertEqual(cpm, pert)


if __name__ == "__main__":
    unittest.main()
