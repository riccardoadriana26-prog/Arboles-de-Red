"""Interfaz para cargar, ejecutar y recorrer algoritmos sobre grafos reales."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from hashlib import sha256
import json
from math import isfinite
from collections.abc import Mapping

import streamlit as st

from arboles_de_red.csv import (
    ProcesadorCPMCSV,
    ProcesadorConexionesCSV,
    ProcesadorPERTCSV,
)
from arboles_de_red.reconstruccion import (
    ErrorReconstruccion, EstadoPERT, EstadoPlanificacion, ReconstruccionEjecucion,
)
from arboles_de_red.formato_visual import formatear_numero
from arboles_de_red.presentacion_pasos import resumir_paso
from arboles_de_red.proyeccion_resultados import (
    ProyeccionArbol, ProyeccionCPM, ProyeccionDijkstra, ProyeccionFlujo,
    ProyeccionPERT, proyectar_resultado,
)
from arboles_de_red.seleccion import SelectorAlgoritmos
from arboles_de_red.registro import ErrorPreparacionEntrada
from arboles_de_red.validacion_csv import ErrorValidacionCSV
from arboles_de_red.visualizador_pyvis import FormatoGrafo, VisualizadorPyVis


_CLAVES_EJECUCION = (
    "hu07_entrada", "hu07_resultado", "hu07_reconstruccion", "hu07_algoritmo",
    "hu07_parametros", "hu07_posiciones_ejecucion", "hu07_ejecucion_key",
    "hu08_proyeccion", "hu08_vista", "hu08_destino",
)
_ALGORITMOS_POR_FORMATO = {
    "Conexiones": ("prim", "kruskal", "dijkstra", "flujo_maximo"),
    "CPM": ("cpm",),
    "PERT": ("pert",),
}
_PROCESADORES = {
    "Conexiones": ProcesadorConexionesCSV,
    "CPM": ProcesadorCPMCSV,
    "PERT": ProcesadorPERTCSV,
}


def clave_ejecucion(formato: str, contenido: bytes, algoritmo: str, parametros: Mapping[str, str]) -> str:
    """Identifica inequívocamente una ejecución y sus datos de entrada."""
    material = {
        "formato": formato,
        "archivo_sha256": sha256(contenido).hexdigest(),
        "algoritmo": algoritmo,
        "parametros": sorted(parametros.items()),
    }
    return sha256(json.dumps(material, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def invalidar_ejecucion_si_cambia(session_state, nueva_clave: str) -> bool:
    """Elimina datos anteriores si cambió archivo, formato, algoritmo u opciones."""
    anterior = session_state.get("hu07_ejecucion_key")
    if anterior is None or anterior == nueva_clave:
        return False
    for clave in _CLAVES_EJECUCION:
        session_state.pop(clave, None)
    clave_slider = session_state.pop("hu07_slider_key", None)
    if clave_slider:
        session_state.pop(clave_slider, None)
    return True


def invalidar_si_cambia_la_carga(session_state, clave_carga: str) -> bool:
    """Invalida antes de parsear, incluso si el archivo nuevo no valida."""
    anterior = session_state.get("hu07_clave_carga")
    if anterior is not None and anterior != clave_carga:
        session_state.pop("hu08_entrada_original", None)
        session_state.pop("hu08_entrada_clave", None)
        for clave in _CLAVES_EJECUCION:
            session_state.pop(clave, None)
        clave_slider = session_state.pop("hu07_slider_key", None)
        if clave_slider:
            session_state.pop(clave_slider, None)
        cambio = True
    else:
        cambio = False
    session_state["hu07_clave_carga"] = clave_carga
    return cambio


def _serializable(valor, compactar_numeros=False):
    """Crea una copia de presentación; conserva IDs enteros y los objetos originales."""
    if is_dataclass(valor) and not isinstance(valor, type):
        return {campo.name: _serializable(getattr(valor, campo.name), compactar_numeros)
                for campo in fields(valor)}
    if isinstance(valor, Mapping):
        return {str(clave): _serializable(item, compactar_numeros) for clave, item in valor.items()}
    if isinstance(valor, (tuple, list)):
        return [_serializable(item, compactar_numeros) for item in valor]
    if compactar_numeros and isinstance(valor, float):
        return formatear_numero(valor)
    if isinstance(valor, float) and not isfinite(valor):
        return "∞" if valor > 0 else "−∞" if valor < 0 else "No es número"
    return valor


def _opciones_algoritmo(formato: FormatoGrafo, selector: SelectorAlgoritmos):
    permitidos = set(_ALGORITMOS_POR_FORMATO[formato])
    return tuple(opcion for opcion in selector.opciones if opcion.identificador in permitidos)


def _claves_widget_ejecucion(clave: str) -> tuple[str, str]:
    corto = clave[:16]
    return f"hu07_paso_{corto}", f"hu07_inicio_{corto}"


def _mover_paso(clave_slider: str, desplazamiento: int, cantidad: int) -> None:
    """Actualiza el índice compartido antes de que Streamlit redibuje los controles."""
    actual = int(st.session_state.get(clave_slider, 0))
    st.session_state[clave_slider] = min(cantidad, max(0, actual + desplazamiento))


def _mostrar_estado(estado_visual, entrada):
    paso = estado_visual.paso
    compactar = isinstance(estado_visual.estado, (EstadoPlanificacion, EstadoPERT))
    st.subheader(f"Paso {estado_visual.numero} · {estado_visual.fase}")
    if paso is None:
        st.write("Estado inicial; todavía no se aplicó ningún evento.")
    else:
        st.write(paso.descripcion)
        for etiqueta, valor in resumir_paso(entrada, estado_visual):
            st.markdown(f"**{etiqueta}:** {valor}")
        with st.expander("Detalle tipado del evento", expanded=False):
            st.json(_serializable(paso.detalle, compactar_numeros=compactar))
    with st.expander("Estado acumulado", expanded=False):
        st.json(_serializable(estado_visual.estado, compactar_numeros=compactar))


def resumen_resultado(proyeccion, resultado) -> tuple[tuple[str, str], ...]:
    """Describe la solución final sin consultar sus pasos ni enumerar rutas críticas."""
    nombres = {"prim": "Prim", "kruskal": "Kruskal", "dijkstra": "Dijkstra",
               "flujo_maximo": "Ford–Fulkerson", "cpm": "CPM", "pert": "PERT"}
    campos = [("Algoritmo", nombres[proyeccion.algoritmo])]
    if isinstance(proyeccion, ProyeccionArbol):
        campos.extend((("Aristas del árbol", str(len(proyeccion.aristas))),
                       ("Peso total", formatear_numero(proyeccion.peso_total))))
    elif isinstance(proyeccion, ProyeccionDijkstra):
        campos.extend((("Origen", proyeccion.origen),
                       ("Destino consultado", proyeccion.destino or "Sin seleccionar")))
        if proyeccion.destino is None:
            campos.append(("Ruta", "Seleccioná un destino para consultar la ruta final"))
        elif proyeccion.ruta is None:
            campos.append(("Ruta", "Destino inalcanzable desde el origen"))
        else:
            campos.extend((("Ruta", " → ".join(proyeccion.ruta)),
                           ("Costo", formatear_numero(proyeccion.costo))))
    elif isinstance(proyeccion, ProyeccionFlujo):
        campos.extend((("Flujo máximo", formatear_numero(proyeccion.flujo_maximo)),
                       ("Capacidad del corte mínimo", formatear_numero(proyeccion.capacidad_corte))))
    elif isinstance(proyeccion, (ProyeccionCPM, ProyeccionPERT)):
        duracion = (proyeccion.duracion_proyecto if isinstance(proyeccion, ProyeccionCPM)
                    else proyeccion.duracion_esperada)
        campos.extend((("Duración total" if isinstance(proyeccion, ProyeccionCPM) else "Duración esperada",
                        formatear_numero(duracion)),
                       ("Actividades críticas", str(len(proyeccion.actividades_criticas))),
                       ("Cantidad de rutas críticas", str(resultado.solucion.rutas_criticas.cantidad))))
    return tuple(campos)


def main():
    st.set_page_config(page_title="Visualizador de grafos", layout="wide")
    st.title("Visualización y recorrido de algoritmos")
    st.caption("Cargá una red para inspeccionarla y, cuando quieras, iniciar un algoritmo.")

    formato: FormatoGrafo = st.selectbox("Formato", ("Conexiones", "CPM", "PERT"), key="hu07_formato")
    archivo = st.file_uploader("Archivo CSV", type=("csv",), key="hu07_archivo")
    if archivo is None:
        invalidar_si_cambia_la_carga(st.session_state, f"{formato}:sin-archivo")
        st.info("Seleccioná un archivo CSV compatible para cargar la red y comenzar la visualización.")
        return

    contenido_bytes = archivo.getvalue()
    clave_visual = f"{formato}:{sha256(contenido_bytes).hexdigest()}"
    invalidar_si_cambia_la_carga(st.session_state, clave_visual)
    if st.session_state.get("hu08_entrada_clave") != clave_visual:
        try:
            contenido = contenido_bytes.decode("utf-8-sig")
            entrada_original = _PROCESADORES[formato]().preparar_entrada(contenido)
        except UnicodeDecodeError:
            st.error("El archivo debe estar codificado como UTF-8.")
            return
        except ErrorValidacionCSV as error:
            st.error(str(error))
            return
        st.session_state["hu08_entrada_original"] = entrada_original
        st.session_state["hu08_entrada_clave"] = clave_visual
    entrada_original = st.session_state["hu08_entrada_original"]

    grafo = entrada_original.grafo
    st.caption(f"Archivo: {archivo.name}")
    col_nodos, col_aristas = st.columns(2)
    col_nodos.metric("Vértices", len(grafo.vertices))
    col_aristas.metric("Conexiones / precedencias", len(grafo.aristas))

    visualizador = VisualizadorPyVis()
    if st.session_state.get("hu07_clave_visual") != clave_visual:
        st.session_state["hu07_clave_visual"] = clave_visual
        st.session_state["hu07_posiciones"] = visualizador.calcular_posiciones(grafo)
    posiciones = st.session_state["hu07_posiciones"]

    if grafo.aristas:
        aristas_por_id = {arista.identificador: arista for arista in grafo.aristas}
        arista_seleccionada = st.selectbox(
            "Consultar una conexión",
            tuple(aristas_por_id),
            format_func=lambda identificador: (
                f"#{identificador}: {aristas_por_id[identificador].origen} "
                f"{'→' if aristas_por_id[identificador].dirigida else '—'} "
                f"{aristas_por_id[identificador].destino}; "
                + ("sin peso" if aristas_por_id[identificador].peso is None
                   else f"peso {aristas_por_id[identificador].peso}")
            ),
            key=f"hu07_arista_{clave_visual[-12:]}",
        )
        seleccionada = aristas_por_id[arista_seleccionada]
        campos = st.columns(5)
        campos[0].metric("Identificador", seleccionada.identificador)
        campos[1].metric("Origen", seleccionada.origen)
        campos[2].metric("Destino", seleccionada.destino)
        campos[3].metric("Dirección", "Dirigida" if seleccionada.dirigida else "No dirigida")
        campos[4].metric("Peso", "Sin peso" if seleccionada.peso is None else str(seleccionada.peso))
    else:
        arista_seleccionada = None
        st.info("El archivo contiene vértices, pero no conexiones ni precedencias.")

    selector = SelectorAlgoritmos()
    opciones_algoritmo = _opciones_algoritmo(formato, selector)
    algoritmo_id = st.selectbox(
        "Algoritmo", tuple(opcion.identificador for opcion in opciones_algoritmo),
        format_func=lambda identificador: next(o.nombre for o in opciones_algoritmo if o.identificador == identificador),
        key=f"hu07_algoritmo_{clave_visual[-12:]}",
    )
    opciones: dict[str, str] = {}
    parametros_validos = True
    vertices = tuple(grafo.vertices)
    clave_widget = clave_visual[-12:]

    if algoritmo_id == "dijkstra":
        origen = st.selectbox("Origen de Dijkstra", vertices, index=None, placeholder="Elegí el origen",
                              key=f"hu07_origen_{clave_widget}")
        destino = st.selectbox("Destino (opcional)", ("Sin destino específico",) + vertices,
                               key=f"hu07_destino_{clave_widget}")
        if origen is None:
            parametros_validos = False
        else:
            opciones["origen"] = origen
        if destino != "Sin destino específico":
            opciones["destino"] = destino
    elif algoritmo_id == "flujo_maximo":
        fuente = st.selectbox("Fuente del flujo", vertices, index=None, placeholder="Elegí la fuente",
                              key=f"hu07_fuente_{clave_widget}")
        sumidero = st.selectbox("Sumidero del flujo", vertices, index=None, placeholder="Elegí el sumidero",
                                key=f"hu07_sumidero_{clave_widget}")
        if fuente is None or sumidero is None or fuente == sumidero:
            parametros_validos = False
            if fuente is not None and fuente == sumidero:
                st.warning("La fuente y el sumidero deben ser vértices distintos.")
        else:
            opciones.update(fuente=fuente, sumidero=sumidero)

    clave = clave_ejecucion(formato, contenido_bytes, algoritmo_id, opciones)
    invalidar_ejecucion_si_cambia(st.session_state, clave)
    slider_key, inicio_key = _claves_widget_ejecucion(clave)
    st.session_state["hu07_slider_key"] = slider_key

    if st.button("Iniciar", disabled=not parametros_validos, key=inicio_key):
        try:
            seleccion = selector.seleccionar(algoritmo_id, entrada_original, opciones)
            if not seleccion.puede_ejecutarse:
                st.error(seleccion.motivo or "La entrada no es aplicable al algoritmo seleccionado.")
            else:
                with st.spinner("Ejecutando algoritmo una vez y preparando los pasos…"):
                    entrada_ejecucion = seleccion.entrada
                    resultado = seleccion.ejecutar()
                    reconstruccion = ReconstruccionEjecucion(
                        entrada_ejecucion, resultado, seleccion.identificador,
                    )
                st.session_state.update({
                    "hu07_entrada": entrada_ejecucion,
                    "hu07_resultado": resultado,
                    "hu07_reconstruccion": reconstruccion,
                    "hu07_algoritmo": seleccion.identificador,
                    "hu07_parametros": dict(opciones),
                    "hu07_posiciones_ejecucion": posiciones,
                    "hu07_ejecucion_key": clave,
                    slider_key: 0,
                    "hu08_vista": "Recorrido",
                })
                st.session_state.pop("hu08_proyeccion", None)
                st.session_state.pop("hu08_destino", None)
        except (ErrorPreparacionEntrada, ErrorReconstruccion, ValueError) as error:
            st.error(str(error))

    if st.session_state.get("hu07_ejecucion_key") != clave:
        visualizador.mostrar_grafo(entrada_original, formato, arista_seleccionada, posiciones)
        return

    reconstruccion = st.session_state["hu07_reconstruccion"]
    cantidad = reconstruccion.cantidad_pasos
    # Desvincula la clave del ciclo de limpieza de widgets cuando el slider se
    # oculta al cambiar de vista; el índice sigue teniendo una sola fuente.
    st.session_state[slider_key] = st.session_state.get(slider_key, 0)
    if "hu08_destino" in st.session_state:
        st.session_state["hu08_destino"] = st.session_state["hu08_destino"]
    vista = st.radio("Vista", ("Datos originales", "Recorrido", "Resultado"),
                     horizontal=True, key="hu08_vista")
    if vista == "Datos originales":
        visualizador.mostrar_grafo(entrada_original, formato, arista_seleccionada, posiciones)
        return
    if vista == "Resultado":
        try:
            resultado = st.session_state["hu07_resultado"]
            if "hu08_proyeccion" not in st.session_state:
                st.session_state["hu08_proyeccion"] = proyectar_resultado(
                    st.session_state["hu07_entrada"], resultado, st.session_state["hu07_algoritmo"],
                )
            proyeccion = st.session_state["hu08_proyeccion"]
            if isinstance(proyeccion, ProyeccionDijkstra) and proyeccion.destino_ejecucion is None:
                destino_consulta = st.selectbox("Destino del resultado", vertices, index=None,
                                                placeholder="Elegí un destino", key="hu08_destino")
                if destino_consulta is not None:
                    proyeccion = proyeccion.consultar_destino(destino_consulta)
            st.subheader("Resultado final")
            for etiqueta, valor in resumen_resultado(proyeccion, resultado):
                st.markdown(f"**{etiqueta}:** {valor}")
            red = visualizador.construir_red_resultado(
                st.session_state["hu07_entrada"], formato, proyeccion,
                st.session_state["hu07_posiciones_ejecucion"],
            )
            st.iframe(visualizador.generar_html(red), height=730, tab_index=0)
        except ValueError as error:
            st.error(str(error))
        return

    actual = min(max(int(st.session_state.get(slider_key, 0)), 0), cantidad)
    col_anterior, col_numero, col_siguiente = st.columns((1, 2, 1))
    col_anterior.button(
        "Anterior", disabled=actual <= 0, key=f"hu07_anterior_{clave[:12]}",
        on_click=_mover_paso, args=(slider_key, -1, cantidad),
    )
    col_numero.metric("Paso", f"{actual} / {cantidad}")
    col_siguiente.button(
        "Siguiente", disabled=actual >= cantidad, key=f"hu07_siguiente_{clave[:12]}",
        on_click=_mover_paso, args=(slider_key, 1, cantidad),
    )
    if cantidad:
        actual = st.slider("Seleccionar paso", min_value=0, max_value=cantidad, step=1,
                           key=slider_key, help="0 muestra el estado inicial antes del primer evento.")
    else:
        st.info("La ejecución no contiene pasos registrados.")

    try:
        estado_visual = reconstruccion.estado_en(actual)
    except (ErrorReconstruccion, IndexError) as error:
        st.error(str(error))
        return
    _mostrar_estado(estado_visual, st.session_state["hu07_entrada"])
    visualizador.mostrar_grafo(
        st.session_state["hu07_entrada"], formato, arista_seleccionada,
        st.session_state["hu07_posiciones_ejecucion"], estado_visual,
    )


if __name__ == "__main__":
    main()
