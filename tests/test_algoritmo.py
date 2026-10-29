"""Ejemplo mínimo de implementación del contrato común."""

import unittest
from dataclasses import FrozenInstanceError, dataclass

from arboles_de_red import (
    Algoritmo,
    AlgoritmoNoAplicableError,
    Arista,
    Entrada,
    Grafo,
    Paso,
    Resultado,
)


@dataclass(frozen=True)
class ParametrosEjemplo:
    origen: str


@dataclass(frozen=True)
class DetalleEjemplo:
    arista_elegida: int


@dataclass(frozen=True)
class SolucionEjemplo:
    arista_elegida: int
    peso_total: float


class AlgoritmoEjemplo(Algoritmo[ParametrosEjemplo, SolucionEjemplo, DetalleEjemplo]):
    """Elige la primera arista que sale del origen para probar el contrato."""

    def __init__(self) -> None:
        self.resoluciones = 0

    def _motivo_inaplicabilidad(
        self, entrada: Entrada[ParametrosEjemplo]
    ) -> str | None:
        if entrada.parametros.origen not in entrada.grafo.vertices:
            return "El origen no existe en el grafo."
        if not any(
            arista.origen == entrada.parametros.origen
            for arista in entrada.grafo.aristas
        ):
            return "El origen no tiene aristas salientes."
        return None

    def _resolver(
        self, entrada: Entrada[ParametrosEjemplo]
    ) -> Resultado[SolucionEjemplo, DetalleEjemplo]:
        self.resoluciones += 1
        arista = next(
            arista
            for arista in entrada.grafo.aristas
            if arista.origen == entrada.parametros.origen
        )
        return Resultado(
            solucion=SolucionEjemplo(arista.identificador, arista.peso),
            pasos=(
                Paso(
                    numero=1,
                    descripcion="Se eligió la primera arista saliente.",
                    vertices_destacados=(arista.origen, arista.destino),
                    aristas_destacadas=(arista.identificador,),
                    detalle=DetalleEjemplo(arista.identificador),
                ),
            ),
        )


class ContratoAlgoritmoTests(unittest.TestCase):
    def test_el_motivo_es_consultable_sin_resolver(self):
        valida = Entrada(self.grafo, ParametrosEjemplo("A"))
        invalida = Entrada(self.grafo, ParametrosEjemplo("C"))

        self.assertIsNone(self.algoritmo.motivo_inaplicabilidad(valida))
        self.assertEqual(
            self.algoritmo.motivo_inaplicabilidad(invalida),
            "El origen no existe en el grafo.",
        )
        self.assertEqual(self.algoritmo.resoluciones, 0)

    def setUp(self) -> None:
        self.grafo = Grafo(("A", "B"), (Arista(7, "A", "B", 8, True),))
        self.algoritmo = AlgoritmoEjemplo()

    def test_entrada_aplicable_produce_solucion_tipada_y_pasos(self):
        entrada = Entrada(self.grafo, ParametrosEjemplo("A"))

        self.assertTrue(self.algoritmo.es_aplicable(entrada))
        resultado = self.algoritmo.ejecutar(entrada)

        self.assertIsInstance(resultado.solucion, SolucionEjemplo)
        self.assertEqual(resultado.solucion.peso_total, 8.0)
        self.assertIsInstance(resultado.pasos, tuple)
        self.assertEqual(resultado.pasos[0].numero, 1)
        self.assertEqual(resultado.pasos[0].vertices_destacados, ("A", "B"))
        self.assertEqual(resultado.pasos[0].aristas_destacadas, (7,))
        self.assertEqual(resultado.pasos[0].detalle, DetalleEjemplo(7))
        self.assertEqual(self.algoritmo.resoluciones, 1)

    def test_entrada_no_aplicable_informa_motivo_y_no_resuelve(self):
        entrada = Entrada(self.grafo, ParametrosEjemplo("C"))

        self.assertFalse(self.algoritmo.es_aplicable(entrada))
        with self.assertRaisesRegex(
            AlgoritmoNoAplicableError, "El origen no existe"
        ) as error:
            self.algoritmo.ejecutar(entrada)

        self.assertEqual(error.exception.motivo, "El origen no existe en el grafo.")
        self.assertEqual(self.algoritmo.resoluciones, 0)

    def test_otra_condicion_de_aplicacion_tambien_se_valida(self):
        entrada = Entrada(self.grafo, ParametrosEjemplo("B"))

        self.assertFalse(self.algoritmo.es_aplicable(entrada))
        with self.assertRaisesRegex(AlgoritmoNoAplicableError, "salientes"):
            self.algoritmo.ejecutar(entrada)

    def test_entrada_y_secuencia_de_pasos_son_inmutables(self):
        entrada = Entrada(self.grafo, ParametrosEjemplo("A"))
        vertices = ["A", "B"]
        aristas = [7]
        paso = Paso(1, "Se elige la arista", vertices, aristas, DetalleEjemplo(7))
        segundo_paso = Paso(2, "Se termina", (), (), DetalleEjemplo(7))
        pasos = [paso, segundo_paso]
        resultado = Resultado(SolucionEjemplo(7, 8.0), pasos)
        vertices.append("C")
        aristas.append(8)
        pasos.reverse()

        self.assertEqual(paso.vertices_destacados, ("A", "B"))
        self.assertEqual(paso.aristas_destacadas, (7,))
        self.assertEqual(resultado.pasos, (paso, segundo_paso))
        with self.assertRaises(FrozenInstanceError):
            entrada.grafo = Grafo((), ())
        with self.assertRaises(FrozenInstanceError):
            paso.numero = 2
        with self.assertRaises(FrozenInstanceError):
            resultado.pasos = ()


if __name__ == "__main__":
    unittest.main()
