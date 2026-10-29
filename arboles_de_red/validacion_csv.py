"""Validación de CSV con diagnósticos de origen antes de construir el modelo."""

from collections import Counter
from collections.abc import Iterable
from csv import Error as ErrorCSV, reader
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import StringIO
from math import isfinite


@dataclass(frozen=True, slots=True)
class DiagnosticoCSV:
    """Error de contenido localizado en una línea y, cuando corresponde, columna."""

    linea: int
    columna: str | None
    mensaje: str

    def __str__(self) -> str:
        ubicacion = f"Línea {self.linea}"
        if self.columna is not None:
            ubicacion += f", columna '{self.columna}'"
        return f"{ubicacion}: {self.mensaje}"


class ErrorValidacionCSV(ValueError):
    """La carga falló; contiene todos los diagnósticos que se pudieron reunir."""

    def __init__(self, errores: Iterable[DiagnosticoCSV]) -> None:
        self.errores = tuple(errores)
        super().__init__("\n".join(str(error) for error in self.errores))


@dataclass(frozen=True, slots=True)
class FilaCSV:
    linea: int
    valores: dict[str, str]


class ValidacionCSV:
    """Recoge problemas de estructura y contenido sin publicar un modelo parcial."""

    def __init__(
        self,
        contenido: str,
        obligatorias: tuple[str, ...],
        opcionales: tuple[str, ...] = (),
    ) -> None:
        self.errores: list[DiagnosticoCSV] = []
        lector = reader(StringIO(contenido, newline=""), strict=True)
        try:
            encabezado = next(lector, [])
        except ErrorCSV as error:
            raise ErrorValidacionCSV(
                (DiagnosticoCSV(1, None, f"CSV mal formado: {error}."),)
            ) from error
        for columna in obligatorias:
            if columna not in encabezado:
                self.agregar(1, columna, "Falta la columna obligatoria.")
        for columna, cantidad in Counter(encabezado).items():
            if cantidad > 1:
                self.agregar(1, columna, "La columna está repetida.")
            if columna not in obligatorias + opcionales:
                self.agregar(1, columna, "La columna no está admitida en esta estructura.")
        self.comprobar()
        self.filas: list[FilaCSV] = []
        while True:
            linea = lector.line_num + 1
            try:
                celdas = next(lector, None)
            except ErrorCSV as error:
                self.agregar(linea, None, f"CSV mal formado: {error}.")
                break
            if celdas is None:
                break
            if not celdas:
                continue
            if len(celdas) != len(encabezado):
                self.agregar(
                    linea, None,
                    f"La fila tiene {len(celdas)} campos; se esperaban {len(encabezado)}.",
                )
                continue
            self.filas.append(FilaCSV(linea, dict(zip(encabezado, celdas))))
        if not self.filas and not self.errores:
            self.agregar(1, None, "El archivo no contiene conexiones ni actividades.")

    def agregar(self, linea: int, columna: str | None, mensaje: str) -> None:
        self.errores.append(DiagnosticoCSV(linea, columna, mensaje))

    def identificador(self, fila: FilaCSV, columna: str) -> bool:
        if not fila.valores[columna].isalnum():
            self.agregar(fila.linea, columna, "El identificador debe ser alfanumérico y no vacío.")
            return False
        return True

    def numero(
        self, fila: FilaCSV, columna: str, *, no_negativo: bool = False
    ) -> Decimal | None:
        try:
            valor = Decimal(fila.valores[columna])
            if not valor.is_finite() or not isfinite(float(valor)):
                raise ValueError("El valor no se puede representar como float finito.")
        except (InvalidOperation, ValueError, OverflowError):
            self.agregar(fila.linea, columna, "El valor debe ser un número real finito.")
            return None
        if no_negativo and valor < 0:
            self.agregar(fila.linea, columna, "El valor no puede ser negativo.")
            return None
        if float(valor) == 0 and valor != 0:
            self.agregar(fila.linea, columna, "El valor no nulo es demasiado pequeño para representarse como float.")
            # Conservar el decimal para poder diagnosticar también su orden en PERT.
        return valor

    def actividades(self) -> None:
        declaradas: dict[str, int] = {}
        for fila in self.filas:
            if self.identificador(fila, "actividad"):
                actividad = fila.valores["actividad"]
                if actividad in declaradas:
                    self.agregar(
                        fila.linea, "actividad",
                        f"La actividad está repetida; se declaró en la línea {declaradas[actividad]}.",
                    )
                else:
                    declaradas[actividad] = fila.linea
        for fila in self.filas:
            texto = fila.valores["predecesoras"]
            if not texto.strip():
                continue
            for elemento in texto.split(";"):
                predecesora = elemento.strip()
                if not predecesora.isalnum():
                    self.agregar(
                        fila.linea, "predecesoras",
                        "Cada predecesora debe ser un identificador alfanumérico no vacío.",
                    )
                elif predecesora == fila.valores["actividad"]:
                    self.agregar(
                        fila.linea, "predecesoras",
                        "Una actividad no puede ser su propia predecesora (lazo).",
                    )
                elif predecesora not in declaradas:
                    self.agregar(
                        fila.linea, "predecesoras",
                        f"La predecesora '{predecesora}' no existe.",
                    )

    def comprobar(self) -> None:
        if self.errores:
            raise ErrorValidacionCSV(self.errores)
