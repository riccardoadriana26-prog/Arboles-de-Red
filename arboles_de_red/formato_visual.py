"""Formato numérico de presentación; nunca reemplaza los valores del modelo."""


def formatear_numero(valor: float) -> str:
    """Muestra como máximo dos decimales sin ceros finales ni cero negativo."""
    if valor == float("inf"):
        return "∞"
    if valor == float("-inf"):
        return "−∞"
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return "0" if texto == "-0" else texto
