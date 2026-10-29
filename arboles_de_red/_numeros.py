"""Errores numéricos explícitos para no confundir desbordes con resultados válidos."""

from collections.abc import Iterable
from math import fsum, isfinite
from numbers import Rational


class ErrorCalculoNumerico(ArithmeticError):
    """Un resultado excede el rango de los números utilizados por la aplicación."""


def finito(valor: float) -> float:
    if not isfinite(valor):
        raise ErrorCalculoNumerico("El resultado excede el rango numérico finito.")
    return valor


def como_float(valor: Rational) -> float:
    try:
        convertido = finito(float(valor))
    except OverflowError as error:
        raise ErrorCalculoNumerico("El resultado excede el rango numérico finito.") from error
    if convertido == 0 and valor != 0:
        raise ErrorCalculoNumerico("El resultado no nulo es demasiado pequeño para representarse como float.")
    return convertido


def sumar(valores: Iterable[float]) -> float:
    try:
        return finito(fsum(valores))
    except OverflowError as error:
        raise ErrorCalculoNumerico("La suma excede el rango numérico finito.") from error
