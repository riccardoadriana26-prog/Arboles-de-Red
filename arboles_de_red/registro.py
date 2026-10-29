"""Registro extensible que coordina preparación y ejecución sin conocer algoritmos."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .algoritmo import Algoritmo, Entrada, Resultado


class ErrorPreparacionEntrada(ValueError):
    """La carga o las opciones no aportan los datos de la entrada seleccionada."""


class EjecucionPreparada[SolucionT, DetalleT](ABC):
    """Entrada y operaciones de una selección con tipos propios de resultado."""

    __slots__ = ()

    @property
    @abstractmethod
    def entrada(self) -> Entrada[object]: ...

    @abstractmethod
    def es_aplicable(self) -> bool: ...

    @abstractmethod
    def motivo_inaplicabilidad(self) -> str | None: ...

    @abstractmethod
    def ejecutar(self) -> Resultado[SolucionT, DetalleT]: ...


@dataclass(frozen=True, slots=True)
class _EjecucionPreparada[ParametrosT, SolucionT, DetalleT](EjecucionPreparada[SolucionT, DetalleT]):
    entrada: Entrada[ParametrosT] = field()
    _crear_algoritmo: Callable[[], Algoritmo[ParametrosT, SolucionT, DetalleT]]

    def es_aplicable(self) -> bool:
        return self._crear_algoritmo().es_aplicable(self.entrada)

    def motivo_inaplicabilidad(self) -> str | None:
        return self._crear_algoritmo().motivo_inaplicabilidad(self.entrada)

    def ejecutar(self) -> Resultado[SolucionT, DetalleT]:
        return self._crear_algoritmo().ejecutar(self.entrada)


class _RegistroPublico(ABC):
    """Vista del catálogo heterogéneo; los tipos propios permanecen en cada registro."""

    __slots__ = ()

    @property
    @abstractmethod
    def identificador(self) -> str: ...

    @property
    @abstractmethod
    def nombre(self) -> str: ...

    @abstractmethod
    def preparar(
        self, carga: Entrada[object], opciones: Mapping[str, str] | None = None
    ) -> EjecucionPreparada[object, object]: ...


@dataclass(frozen=True, slots=True)
class RegistroAlgoritmo[ParametrosT, SolucionT, DetalleT](_RegistroPublico):
    """Une la fábrica y la preparación de parámetros de una implementación."""

    identificador: str = field()
    nombre: str = field()
    crear_algoritmo: Callable[[], Algoritmo[ParametrosT, SolucionT, DetalleT]]
    preparar_parametros: Callable[[Entrada[object], Mapping[str, str]], ParametrosT]

    def preparar(
        self, carga: Entrada[object], opciones: Mapping[str, str] | None = None
    ) -> EjecucionPreparada[SolucionT, DetalleT]:
        parametros = self.preparar_parametros(carga, MappingProxyType(dict(opciones or {})))
        return _EjecucionPreparada(Entrada(carga.grafo, parametros), self.crear_algoritmo)


class RegistroAlgoritmos:
    """Selecciona por identificador sin reemplazar ni ejecutar otras opciones."""

    def __init__(self) -> None:
        self._registros: dict[str, _RegistroPublico] = {}

    @property
    def identificadores(self) -> tuple[str, ...]:
        return tuple(self._registros)

    def registrar[ParametrosT, SolucionT, DetalleT](
        self, registro: RegistroAlgoritmo[ParametrosT, SolucionT, DetalleT]
    ) -> None:
        if registro.identificador in self._registros:
            raise ValueError(f"El algoritmo '{registro.identificador}' ya está registrado.")
        self._registros[registro.identificador] = registro

    def seleccionar(self, identificador: str) -> _RegistroPublico:
        return self._registros[identificador]
