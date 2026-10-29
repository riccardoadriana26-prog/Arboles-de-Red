"""API de aplicación sobre CSV reales, registro extensible y resolutores reales."""

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from arboles_de_red import (
    Algoritmo, AlgoritmoNoAplicableError, Arista, CondicionesArbolExpansion, Entrada,
    ErrorPreparacionEntrada, Grafo, LectorTexto, ParametrosDijkstra, ParametrosFlujoMaximo,
    Paso, ProcesadorConexionesCSV, ProcesadorCPMCSV, ProcesadorPERTCSV,
    RegistroAlgoritmo, RegistroAlgoritmos, Resultado, SelectorAlgoritmos,
    crear_registro_predeterminado,
)


class SeleccionTests(unittest.TestCase):
    def test_lista_y_ejecuta_los_seis_algoritmos_reales_desde_csv(self):
        selector = SelectorAlgoritmos()
        ids = tuple(o.identificador for o in selector.opciones)
        self.assertEqual(ids, ("prim", "kruskal", "dijkstra", "flujo_maximo", "cpm", "pert"))
        carpeta = Path(__file__).resolve().parents[1] / "ejemplos"
        cpm = ProcesadorCPMCSV().preparar_entrada(LectorTexto().leer(carpeta / "cpm.csv"))
        pert = ProcesadorPERTCSV().preparar_entrada(LectorTexto().leer(carpeta / "pert.csv"))
        no_dirigida = ProcesadorConexionesCSV().preparar_entrada("origen,destino,peso\nA,B,2\nB,C,3\nA,C,8\n")
        dirigida = ProcesadorConexionesCSV().preparar_entrada("origen,destino,peso,dirigida\nS,A,4,true\nA,T,3,true\nS,T,2,true\n")
        casos = (("prim", no_dirigida, {}), ("kruskal", no_dirigida, {}),
                 ("dijkstra", dirigida, {"origen": "S", "destino": "T"}),
                 ("flujo_maximo", dirigida, {"fuente": "S", "sumidero": "T"}),
                 ("cpm", cpm, {}), ("pert", pert, {}))
        for identificador, carga, opciones in casos:
            with self.subTest(algoritmo=identificador):
                seleccion = selector.seleccionar(identificador, carga, opciones)
                self.assertTrue(seleccion.puede_ejecutarse)
                self.assertIsNone(seleccion.motivo)
                self.assertEqual(seleccion.identificador, identificador)
                self.assertIs(seleccion.entrada.grafo, carga.grafo)
                if identificador in ("cpm", "pert"):
                    self.assertIs(seleccion.entrada.parametros, carga.parametros)
                resultado = seleccion.ejecutar()
                self.assertIsInstance(resultado.pasos, tuple)
                self.assertTrue(resultado.pasos)
                self.assertEqual([p.numero for p in resultado.pasos], list(range(1, len(resultado.pasos) + 1)))
                self.assertEqual(resultado, seleccion.ejecutar())
                if identificador in ("prim", "kruskal"):
                    self.assertEqual(resultado.solucion.peso_total, 5)
                elif identificador == "dijkstra":
                    self.assertEqual(seleccion.entrada.parametros, ParametrosDijkstra("S", "T"))
                    self.assertEqual(resultado.solucion.ruta, ("S", "T"))
                    self.assertEqual(resultado.solucion.costo, 2)
                elif identificador == "flujo_maximo":
                    self.assertEqual(seleccion.entrada.parametros, ParametrosFlujoMaximo("S", "T"))
                    self.assertEqual(resultado.solucion.flujo_maximo, 5)
                elif identificador == "cpm":
                    self.assertEqual(resultado.solucion.duracion_proyecto, 9.5)
                else:
                    self.assertAlmostEqual(resultado.solucion.duracion_esperada, 31 / 3)

    def test_informa_incompatibilidad_sin_elegir_otro_algoritmo(self):
        carga = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", 1, True),)), None)
        selector = SelectorAlgoritmos()
        seleccion = selector.seleccionar("prim", carga)
        self.assertEqual(seleccion.identificador, "prim")
        self.assertFalse(seleccion.puede_ejecutarse)
        self.assertIn("dirigida", seleccion.motivo)
        with self.assertRaises(AlgoritmoNoAplicableError) as captura:
            seleccion.ejecutar()
        self.assertEqual(captura.exception.motivo, seleccion.motivo)
        valida = selector.seleccionar("dijkstra", carga, {"origen": "A", "destino": "B"})
        self.assertTrue(valida.puede_ejecutarse)
        self.assertEqual(valida.ejecutar().solucion.costo, 1)
        self.assertFalse(seleccion.puede_ejecutarse)
        with self.assertRaises(FrozenInstanceError):
            seleccion.motivo = None

    def test_informa_parametros_faltantes_y_terminales_inexistentes(self):
        carga = Entrada(Grafo(("A",), ()), None)
        selector = SelectorAlgoritmos()
        for identificador, opciones in (("dijkstra", {}), ("flujo_maximo", {"fuente": "A"}),
                                        ("cpm", {}), ("pert", {})):
            with self.subTest(algoritmo=identificador), self.assertRaises(ErrorPreparacionEntrada):
                selector.seleccionar(identificador, carga, opciones)
        seleccion = selector.seleccionar("dijkstra", carga, {"origen": "A", "destino": "B"})
        self.assertFalse(seleccion.puede_ejecutarse)
        self.assertIn("destino", seleccion.motivo)
        with self.assertRaises(KeyError):
            selector.seleccionar("inexistente", carga)
        seleccion = selector.seleccionar("dijkstra", carga, {"origen": "A"})
        self.assertEqual(seleccion.ejecutar().solucion.ruta_hasta("A"), ("A",))

    def test_seleccion_no_resuelve_y_admite_nuevos_registros_sin_cambios(self):
        llamadas = []

        class OtroAlgoritmo(Algoritmo[None, int, str]):
            def __init__(self):
                super().__init__(CondicionesArbolExpansion())

            def _resolver(self, entrada):
                llamadas.append("resolver")
                return Resultado(42, (Paso(1, "Respuesta propia", (), (), "detalle"),))

        registro = crear_registro_predeterminado()
        registro.registrar(RegistroAlgoritmo("otro", "Otra opción", OtroAlgoritmo, lambda carga, opciones: None))
        selector = SelectorAlgoritmos(registro)
        carga = Entrada(Grafo(("A",), ()), None)
        seleccion = selector.seleccionar("otro", carga)
        self.assertEqual(llamadas, [])
        self.assertIn("otro", tuple(o.identificador for o in selector.opciones))
        self.assertEqual(seleccion.ejecutar().solucion, 42)
        self.assertEqual(llamadas, ["resolver"])
        self.assertEqual(SelectorAlgoritmos(RegistroAlgoritmos()).opciones, ())


if __name__ == "__main__":
    unittest.main()
