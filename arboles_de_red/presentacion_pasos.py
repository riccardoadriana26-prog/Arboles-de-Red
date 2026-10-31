"""Resúmenes de decisiones sin dependencias de interfaz ni ejecución de algoritmos."""

from .algoritmo import Entrada
from .arbol_expansion import DetalleArbolExpansion
from .cpm import DetalleCPM
from .dijkstra import DetalleDijkstra
from .flujo_maximo import DetalleFlujoMaximo
from .formato_visual import formatear_numero
from .pert import DetalleEstimacionPERT
from .reconstruccion import EstadoPERT, EstadoVisualPaso


def _numero(valor: float | None) -> str:
    if valor is None:
        return "No disponible"
    if valor == float("inf"):
        return "∞"
    if valor == float("-inf"):
        return "−∞"
    texto = str(valor)
    return texto[:-2] if texto.endswith(".0") else texto


def resumir_paso(entrada: Entrada, estado: EstadoVisualPaso) -> tuple[tuple[str, str], ...]:
    """Devuelve campos legibles del evento, resolviendo IDs contra la entrada real."""
    if estado.paso is None:
        return (("Estado", "Inicial, sin eventos aplicados"),)
    aristas = {arista.identificador: arista for arista in entrada.grafo.aristas}

    def conexion(identificador: int) -> str:
        arista = aristas[identificador]
        direccion = "→" if arista.dirigida else "—"
        peso = "Sin peso" if arista.peso is None else f"peso {_numero(arista.peso)}"
        return f"#{identificador} {arista.origen} {direccion} {arista.destino} · {peso}"

    def conexiones(identificadores) -> str:
        return "; ".join(conexion(i) for i in identificadores) or "Ninguna"

    def predecesor(valor) -> str:
        return "Sin predecesor" if valor is None else f"{valor[0]} mediante {conexion(valor[1])}"

    detalle = estado.paso.detalle
    campos: list[tuple[str, str]] = []
    if isinstance(detalle, DetalleArbolExpansion):
        if estado.estado.algoritmo == "Prim":
            if detalle.arista is not None:
                campos.append(("Arista elegida", conexion(detalle.arista)))
            campos.append(("Aristas evaluadas", conexiones(detalle.aristas_evaluadas)))
        elif detalle.arista is not None:
            campos.extend((("Arista evaluada", conexion(detalle.arista)),
                           ("Decisión", "Aceptada e incorporada al árbol" if detalle.aceptada
                            else "Rechazada: formaría un ciclo")))
        campos.extend((("Peso acumulado", _numero(detalle.peso_acumulado)),
                       ("Aristas aceptadas acumuladas", conexiones(detalle.aristas_arbol))))
    elif isinstance(detalle, DetalleDijkstra):
        acciones = {"iniciar": "Inicialización", "fijar": "Fijación del vértice permanente",
                    "relajar": "Mejora de distancia", "conservar": "Conservación de distancia",
                    "finalizar": "Finalización"}
        campos.extend((("Acción", acciones[detalle.accion]), ("Vértice", detalle.vertice)))
        if detalle.arista is not None:
            campos.append(("Arista utilizada", conexion(detalle.arista)))
        campos.extend((("Distancia anterior", _numero(detalle.distancia_anterior)),
                       ("Distancia nueva", _numero(detalle.distancia_nueva)),
                       ("Predecesor anterior", predecesor(detalle.predecesor_anterior)),
                       ("Predecesor nuevo", predecesor(detalle.predecesor_nuevo))))
    elif isinstance(detalle, DetalleFlujoMaximo):
        if detalle.camino:
            camino = (detalle.camino[0].origen,) + tuple(t.destino for t in detalle.camino)
            campos.append(("Camino de aumento", " → ".join(camino)))
            tramos = []
            for tramo in detalle.camino:
                if tramo.inverso:
                    tramos.append(f"{tramo.origen} → {tramo.destino}: residual inverso de {conexion(tramo.arista)}")
                else:
                    tramos.append(conexion(tramo.arista))
            campos.extend((("Tramos del camino", "; ".join(tramos)),
                           ("Aristas originales utilizadas", conexiones(dict.fromkeys(t.arista for t in detalle.camino))),
                           ("Cuello de botella", _numero(detalle.cuello_botella)),
                           ("Incremento de flujo", _numero(estado.estado.incremento_flujo))))
        campos.append(("Flujo acumulado", _numero(detalle.flujo_acumulado)))
    elif isinstance(detalle, DetalleEstimacionPERT):
        estimaciones = entrada.parametros.estimaciones[detalle.actividad]
        campos.extend((("Fase", "Estimación PERT"), ("Actividad", detalle.actividad),
                       ("Optimista", formatear_numero(estimaciones.optimista)),
                       ("Más probable", formatear_numero(estimaciones.mas_probable)),
                       ("Pesimista", formatear_numero(estimaciones.pesimista)),
                       ("Tiempo esperado", formatear_numero(detalle.tiempo_esperado)),
                       ("Varianza", formatear_numero(detalle.varianza))))
    elif isinstance(detalle, DetalleCPM):
        fases = {"adelante": "Hacia adelante", "atras": "Hacia atrás", "finalizar": "Finalización"}
        campos.append(("Fase", fases[detalle.fase]))
        if detalle.actividad is not None:
            campos.append(("Actividad", detalle.actividad))
            for etiqueta, valor in (("IC", detalle.ic), ("TC", detalle.tc), ("IL", detalle.il),
                                    ("TL", detalle.tl), ("Holgura", detalle.holgura)):
                if valor is not None:
                    campos.append((etiqueta, formatear_numero(valor)))
        else:
            plan = estado.estado.planificacion if isinstance(estado.estado, EstadoPERT) else estado.estado
            if plan.duracion_proyecto is not None:
                campos.append(("Duración del proyecto", formatear_numero(plan.duracion_proyecto)))
            campos.append(("Actividades críticas", ", ".join(plan.actividades_criticas) or "Ninguna"))
    else:
        raise TypeError(f"Detalle de evento sin presentación: {type(detalle).__name__}.")
    return tuple(campos)
