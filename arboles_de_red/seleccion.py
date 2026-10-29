"""API de selección para la futura interfaz, sin depender de su tecnología."""

from collections.abc import Mapping
from dataclasses import dataclass

from .algoritmo import Entrada, Resultado
from .catedra import crear_registro_predeterminado
from .registro import EjecucionPreparada, RegistroAlgoritmos


@dataclass(frozen=True, slots=True)
class OpcionAlgoritmo:
    identificador: str
    nombre: str


@dataclass(frozen=True, slots=True)
class SeleccionAlgoritmo:
    identificador: str
    nombre: str
    ejecucion: EjecucionPreparada[object, object]
    motivo: str | None

    @property
    def puede_ejecutarse(self) -> bool:
        return self.motivo is None

    @property
    def entrada(self) -> Entrada[object]:
        return self.ejecucion.entrada

    def ejecutar(self) -> Resultado[object, object]:
        """El contrato vuelve a validar la entrada antes de calcular la solución."""
        return self.ejecucion.ejecutar()


class SelectorAlgoritmos:
    """Lista opciones y prepara una elección explícita con su compatibilidad.

    Los errores de preparación se propagan como ErrorPreparacionEntrada;
    una entrada preparada incompatible devuelve una selección con su motivo.
    No resuelve durante la selección ni mantiene una selección global mutable.
    """

    def __init__(self, registro: RegistroAlgoritmos | None = None) -> None:
        self._registro = crear_registro_predeterminado() if registro is None else registro

    @property
    def opciones(self) -> tuple[OpcionAlgoritmo, ...]:
        return tuple(OpcionAlgoritmo(i, self._registro.seleccionar(i).nombre)
                     for i in self._registro.identificadores)

    def seleccionar(
        self, identificador: str, carga: Entrada[object], opciones: Mapping[str, str] | None = None,
    ) -> SeleccionAlgoritmo:
        registro = self._registro.seleccionar(identificador)
        ejecucion = registro.preparar(carga, opciones)
        motivo = ejecucion.motivo_inaplicabilidad()
        return SeleccionAlgoritmo(registro.identificador, registro.nombre, ejecucion, motivo)
