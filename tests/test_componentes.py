"""Integración de contratos con dobles, sin lector CSV ni interfaz gráfica."""

import unittest
from pathlib import Path

from arboles_de_red import (
    Arista,
    Entrada,
    Grafo,
    LectorArchivo,
    ProcesadorGrafo,
    Resultado,
    Visualizador,
)
from test_algoritmo import (
    AlgoritmoEjemplo,
    DetalleEjemplo,
    ParametrosEjemplo,
    SolucionEjemplo,
)


class LectorEnMemoria(LectorArchivo):
    def __init__(self, contenido: str) -> None:
        self.contenido = contenido
        self.rutas: list[str | Path] = []

    def leer(self, ruta: str | Path) -> str:
        self.rutas.append(ruta)
        return self.contenido


class ProcesadorEnMemoria(ProcesadorGrafo):
    def __init__(self, grafo: Grafo) -> None:
        self.grafo = grafo
        self.contenidos: list[str] = []

    def procesar(self, contenido: str) -> Grafo:
        self.contenidos.append(contenido)
        return self.grafo


class VisualizadorEnMemoria(Visualizador[SolucionEjemplo, DetalleEjemplo]):
    def __init__(self) -> None:
        self.grafos: list[Grafo] = []
        self.resultados: list[tuple[Grafo, Resultado[SolucionEjemplo, DetalleEjemplo]]] = []

    def mostrar_grafo(self, grafo: Grafo) -> None:
        self.grafos.append(grafo)

    def mostrar_resultado(
        self, grafo: Grafo, resultado: Resultado[SolucionEjemplo, DetalleEjemplo]
    ) -> None:
        self.resultados.append((grafo, resultado))


class ContratosComponentesTests(unittest.TestCase):
    def test_los_contratos_exigen_implementaciones_concretas(self):
        for contrato in (LectorArchivo, ProcesadorGrafo, Visualizador):
            with self.subTest(contrato=contrato.__name__), self.assertRaises(TypeError):
                contrato()

        class VisualizadorIncompleto(Visualizador):
            def mostrar_grafo(self, grafo: Grafo) -> None:
                pass

        with self.assertRaises(TypeError):
            VisualizadorIncompleto()

    def test_las_etapas_intercambian_datos_sin_ejecutarse_entre_si(self):
        grafo = Grafo(("A", "B"), (Arista(7, "A", "B", 8, True),))
        lector: LectorArchivo = LectorEnMemoria("texto sin interpretar")
        procesador: ProcesadorGrafo = ProcesadorEnMemoria(grafo)
        algoritmo = AlgoritmoEjemplo()
        visualizador: Visualizador[SolucionEjemplo, DetalleEjemplo] = (
            VisualizadorEnMemoria()
        )
        ruta = Path("grafo.csv")

        contenido = lector.leer(ruta)

        self.assertEqual(contenido, "texto sin interpretar")
        self.assertEqual(lector.rutas, [ruta])
        self.assertEqual(procesador.contenidos, [])

        cargado = procesador.procesar(contenido)

        self.assertEqual(procesador.contenidos, [contenido])
        self.assertIs(cargado, grafo)
        self.assertEqual(algoritmo.resoluciones, 0)
        self.assertEqual(visualizador.grafos, [])

        visualizador.mostrar_grafo(cargado)
        self.assertIs(visualizador.grafos[0], grafo)
        self.assertEqual(algoritmo.resoluciones, 0)

        resultado = algoritmo.ejecutar(Entrada(cargado, ParametrosEjemplo("A")))

        self.assertEqual(algoritmo.resoluciones, 1)
        self.assertEqual(visualizador.resultados, [])
        self.assertEqual(resultado.solucion.peso_total, 8.0)

        visualizador.mostrar_resultado(cargado, resultado)

        self.assertIs(visualizador.resultados[0][0], grafo)
        self.assertIs(visualizador.resultados[0][1], resultado)
        self.assertEqual(algoritmo.resoluciones, 1)
        self.assertEqual(lector.rutas, [ruta])
        self.assertEqual(procesador.contenidos, [contenido])


if __name__ == "__main__":
    unittest.main()
