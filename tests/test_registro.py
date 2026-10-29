"""Selección y ejecución a través del registro público de algoritmos."""

import unittest
from dataclasses import FrozenInstanceError, dataclass
from pathlib import Path
from typing import assert_type

from arboles_de_red import (
    Algoritmo,
    AlgoritmoNoAplicableError,
    Arista,
    CondicionesAplicacion,
    CondicionesArbolExpansion,
    CondicionesCPM,
    CondicionesDijkstra,
    CondicionesFlujoMaximo,
    CondicionesPERT,
    Entrada,
    EjecucionPreparada,
    ErrorPreparacionEntrada,
    EstimacionesPERT,
    Grafo,
    LectorTexto,
    ParametrosCPM,
    ParametrosDijkstra,
    ParametrosFlujoMaximo,
    ParametrosPERT,
    Paso,
    ProcesadorCPMCSV,
    ProcesadorPERTCSV,
    RegistroAlgoritmo,
    RegistroAlgoritmos,
    Resultado,
    crear_registro_catedra,
)
from test_algoritmo import AlgoritmoEjemplo, DetalleEjemplo, ParametrosEjemplo, SolucionEjemplo


@dataclass(frozen=True)
class SolucionDePrueba:
    algoritmo: str
    parametros: object
    numero_ejecucion: int


@dataclass(frozen=True)
class DetalleDePrueba:
    algoritmo: str


class AlgoritmoDePrueba[ParametrosT](Algoritmo[ParametrosT, SolucionDePrueba, DetalleDePrueba]):
    """Devuelve su identidad y entrada para verificar el recorrido del registro."""

    def __init__(self, identificador: str, condiciones: CondicionesAplicacion[ParametrosT]):
        super().__init__(condiciones)
        self.identificador = identificador
        self.resoluciones = 0

    def _resolver(self, entrada: Entrada[ParametrosT]) -> Resultado[SolucionDePrueba, DetalleDePrueba]:
        self.resoluciones += 1
        return Resultado(
            SolucionDePrueba(self.identificador, entrada.parametros, self.resoluciones),
            (Paso(1, "Resolución de prueba", (), (), DetalleDePrueba(self.identificador)),),
        )


def registro_catedra_de_prueba() -> RegistroAlgoritmos:
    return crear_registro_catedra(
        prim=lambda: AlgoritmoDePrueba("prim", CondicionesArbolExpansion()),
        kruskal=lambda: AlgoritmoDePrueba("kruskal", CondicionesArbolExpansion()),
        dijkstra=lambda: AlgoritmoDePrueba("dijkstra", CondicionesDijkstra()),
        flujo_maximo=lambda: AlgoritmoDePrueba("flujo_maximo", CondicionesFlujoMaximo()),
        cpm=lambda: AlgoritmoDePrueba("cpm", CondicionesCPM()),
        pert=lambda: AlgoritmoDePrueba("pert", CondicionesPERT()),
    )


class RegistroAlgoritmosTests(unittest.TestCase):
    def test_el_registro_generico_conserva_los_tipos_estaticos(self) -> None:
        def crear() -> Algoritmo[ParametrosDijkstra, SolucionDePrueba, DetalleDePrueba]:
            return AlgoritmoDePrueba("dijkstra", CondicionesDijkstra())

        opcion = RegistroAlgoritmo(
            "dijkstra", "Dijkstra", crear,
            lambda carga, opciones: ParametrosDijkstra(opciones["origen"]),
        )
        ejecucion = opcion.preparar(Entrada(Grafo(("A",), ()), None), {"origen": "A"})
        assert_type(ejecucion, EjecucionPreparada[SolucionDePrueba, DetalleDePrueba])
        resultado = ejecucion.ejecutar()
        assert_type(resultado, Resultado[SolucionDePrueba, DetalleDePrueba])
        self.assertEqual(resultado.solucion.algoritmo, "dijkstra")

    def test_ampliar_el_registro_conserva_las_selecciones_y_entradas_anteriores(self):
        grafo = Grafo(("A", "B"), (Arista(7, "A", "B", 8, True),))
        original = RegistroAlgoritmo(
            "original", "Original", AlgoritmoEjemplo,
            lambda carga, opciones: ParametrosEjemplo(opciones["origen"]),
        )
        registro = RegistroAlgoritmos()
        registro.registrar(original)
        seleccion = registro.seleccionar("original")
        identificadores = registro.identificadores
        opciones = {"origen": "A"}
        preparada = seleccion.preparar(Entrada(grafo, None), opciones)

        registro.registrar(RegistroAlgoritmo(
            "otro", "Otra opción", AlgoritmoEjemplo,
            lambda carga, opciones: ParametrosEjemplo("B"),
        ))
        opciones["origen"] = "B"

        self.assertIs(registro.seleccionar("original"), seleccion)
        self.assertEqual(identificadores, ("original",))
        self.assertEqual(registro.identificadores, ("original", "otro"))
        self.assertEqual(preparada.entrada.parametros, ParametrosEjemplo("A"))
        self.assertEqual(preparada.ejecutar().solucion.peso_total, 8)
        with self.assertRaises(FrozenInstanceError):
            original.nombre = "Reemplazo"
        with self.assertRaises(FrozenInstanceError):
            preparada.entrada = Entrada(Grafo((), ()), None)

    def test_rechaza_identificadores_repetidos_sin_sustituir_el_registro_original(self):
        original = RegistroAlgoritmo(
            "ejemplo", "Original", AlgoritmoEjemplo,
            lambda carga, opciones: ParametrosEjemplo("A"),
        )
        reemplazo = RegistroAlgoritmo(
            "ejemplo", "Reemplazo", AlgoritmoEjemplo,
            lambda carga, opciones: ParametrosEjemplo("B"),
        )
        registro = RegistroAlgoritmos()
        registro.registrar(original)

        with self.assertRaisesRegex(ValueError, "registrado"):
            registro.registrar(reemplazo)

        self.assertIs(registro.seleccionar("ejemplo"), original)
        self.assertEqual(registro.identificadores, ("ejemplo",))
        with self.assertRaises(KeyError):
            registro.seleccionar("desconocido")

    def test_registra_prepara_y_ejecuta_con_los_tipos_propios_del_algoritmo(self):
        grafo = Grafo(("A", "B"), (Arista(7, "A", "B", 8, True),))
        registro = RegistroAlgoritmos()
        registro.registrar(
            RegistroAlgoritmo(
                "ejemplo", "Algoritmo de ejemplo", AlgoritmoEjemplo,
                lambda carga, opciones: ParametrosEjemplo(opciones["origen"]),
            )
        )

        opcion = registro.seleccionar("ejemplo")
        ejecucion = opcion.preparar(Entrada(grafo, None), {"origen": "A"})

        self.assertEqual(registro.identificadores, ("ejemplo",))
        self.assertEqual(opcion.nombre, "Algoritmo de ejemplo")
        self.assertIs(ejecucion.entrada.grafo, grafo)
        self.assertEqual(ejecucion.entrada.parametros, ParametrosEjemplo("A"))
        self.assertTrue(ejecucion.es_aplicable())
        self.assertIsNone(ejecucion.motivo_inaplicabilidad())
        resultado = ejecucion.ejecutar()
        self.assertIsInstance(resultado.solucion, SolucionEjemplo)
        self.assertEqual(resultado.solucion.peso_total, 8)
        self.assertEqual(resultado.pasos[0].detalle, DetalleEjemplo(7))


class RegistroCatedraTests(unittest.TestCase):
    def test_cada_ejecucion_tiene_su_instancia_y_no_se_sustituye_un_algoritmo_incompatible(self):
        registro = registro_catedra_de_prueba()
        carga = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", 2, True),)), None)
        preparada = registro.seleccionar("dijkstra").preparar(carga, {"origen": "A"})

        primero = preparada.ejecutar()
        segundo = preparada.ejecutar()

        self.assertEqual(primero.solucion.numero_ejecucion, 1)
        self.assertEqual(segundo.solucion.numero_ejecucion, 1)
        self.assertIsNot(primero, segundo)
        self.assertTrue(preparada.es_aplicable())
        incompatible = registro.seleccionar("prim").preparar(carga)
        self.assertFalse(incompatible.es_aplicable())
        motivo = incompatible.motivo_inaplicabilidad()
        with self.assertRaises(AlgoritmoNoAplicableError) as captura:
            incompatible.ejecutar()
        self.assertEqual(captura.exception.motivo, motivo)
        self.assertIn("dirigida", motivo)

    def test_informa_parametros_ausentes_y_no_inventa_datos_de_actividades(self):
        registro = registro_catedra_de_prueba()
        carga = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", 2, True),)), None)
        casos = (
            ("dijkstra", {}, "origen"),
            ("dijkstra", {"origen": ""}, "origen"),
            ("dijkstra", {"origen": "A", "destino": ""}, "destino"),
            ("flujo_maximo", {"fuente": "A"}, "sumidero"),
            ("flujo_maximo", {"sumidero": "B"}, "fuente"),
            ("cpm", {}, "CPM"),
            ("pert", {}, "PERT"),
            ("prim", {"origen": "A"}, "origen"),
            ("dijkstra", {"origen": "A", "extra": "B"}, "extra"),
        )
        for identificador, opciones, fragmento in casos:
            with self.subTest(algoritmo=identificador, opciones=opciones):
                with self.assertRaisesRegex(ErrorPreparacionEntrada, fragmento):
                    registro.seleccionar(identificador).preparar(carga, opciones)
        pert = Entrada(Grafo(("A",), ()), ParametrosPERT({"A": EstimacionesPERT(1, 2, 3)}))
        with self.assertRaisesRegex(ErrorPreparacionEntrada, "CPM"):
            registro.seleccionar("cpm").preparar(pert)
        cpm = Entrada(pert.grafo, ParametrosCPM({"A": 2}))
        with self.assertRaisesRegex(ErrorPreparacionEntrada, "PERT"):
            registro.seleccionar("pert").preparar(cpm)

    def test_los_seis_registros_preparan_sus_parametros_y_conservan_solucion_y_pasos(self):
        registro = registro_catedra_de_prueba()
        carpeta = Path(__file__).resolve().parents[1] / "ejemplos"
        cpm = ProcesadorCPMCSV().preparar_entrada(LectorTexto().leer(carpeta / "cpm.csv"))
        pert = ProcesadorPERTCSV().preparar_entrada(LectorTexto().leer(carpeta / "pert.csv"))
        no_dirigida = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", -2, False),)), None)
        dirigida = Entrada(Grafo(("A", "B"), (Arista(0, "A", "B", 2, True),)), None)
        casos = (
            ("prim", no_dirigida, {}, None),
            ("kruskal", no_dirigida, {}, None),
            ("dijkstra", dirigida, {"origen": "A", "destino": "B"}, ParametrosDijkstra("A", "B")),
            ("flujo_maximo", dirigida, {"fuente": "A", "sumidero": "B"}, ParametrosFlujoMaximo("A", "B")),
            ("cpm", cpm, {}, ParametrosCPM({"A": 2, "B": 3, "C": 4.5, "Independiente": 1})),
            ("pert", pert, {}, ParametrosPERT({
                "A": EstimacionesPERT(1, 2, 9), "B": EstimacionesPERT(2, 3, 4),
                "C": EstimacionesPERT(2, 4, 8), "Independiente": EstimacionesPERT(1, 1, 1),
            })),
        )

        self.assertEqual(registro.identificadores, ("prim", "kruskal", "dijkstra", "flujo_maximo", "cpm", "pert"))
        for identificador, carga, opciones, esperados in casos:
            with self.subTest(algoritmo=identificador):
                ejecucion = registro.seleccionar(identificador).preparar(carga, opciones)
                self.assertIs(ejecucion.entrada.grafo, carga.grafo)
                self.assertEqual(ejecucion.entrada.parametros, esperados)
                self.assertTrue(ejecucion.es_aplicable())
                self.assertIsNone(ejecucion.motivo_inaplicabilidad())
                resultado = ejecucion.ejecutar()
                self.assertEqual(resultado.solucion.algoritmo, identificador)
                self.assertEqual(resultado.solucion.parametros, esperados)
                self.assertEqual(resultado.pasos[0].detalle, DetalleDePrueba(identificador))


if __name__ == "__main__":
    unittest.main()
