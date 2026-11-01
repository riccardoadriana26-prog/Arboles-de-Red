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
    ProyeccionDijkstra, proyectar_resultado,
)
from arboles_de_red.informacion_resultados import (
    InformacionArbol, InformacionDijkstra, InformacionFlujo, InformacionCPM,
    InformacionPERT, InformacionResultado, VariabilidadInterrumpida,
    obtener_informacion_resultado,
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

# --- EJEMPLOS PRECARGADOS CUBRIENDO TODOS LOS CRITERIOS DE LA CÁTEDRA ---
_EJEMPLOS_CATEDRA = {
    "Conexiones": {
        "Red ponderada estándar (Prim, Kruskal, Dijkstra, Flujo Máximo)": (
            "origen,destino,peso\n"
            "A,B,4\n"
            "A,C,2\n"
            "B,C,1\n"
            "B,D,5\n"
            "C,D,8\n"
        ),
        "Caso de validación de condiciones (Aristas negativas para Dijkstra)": (
            "origen,destino,peso\n"
            "A,B,2\n"
            "B,C,-3\n"
            "A,C,5\n"
        )
    },
    "CPM": {
        "CPM (Caso Servidores - Estructura AON directa)": (
            "actividad,duracion,predecesoras\n"
            "A,3,\n"   
            "B,5,A\n"
            "C,2,A\n"
            "D,4,B;C\n"
        )
    },
    "PERT": {
        "PERT (Caso Servidores - Estimaciones probabilísticas con predecesoras)": (
            "actividad,optimista,mas_probable,pesimista,predecesoras\n"
            "A,2,3,4,-\n"
            "B,4,5,6,A\n"
            "C,1,2,3,A\n"
            "D,3,4,5,B;C\n"
        )
    }
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


def resumen_resultado(informacion: InformacionResultado, proyeccion) -> tuple[tuple[str, str], ...]:
    """Reutiliza HU-09 y conserva los datos adicionales del resumen HU-08."""
    nombres = {"prim": "Prim", "kruskal": "Kruskal", "dijkstra": "Dijkstra",
               "flujo_maximo": "Ford–Fulkerson", "cpm": "CPM", "pert": "PERT"}
    campos = [("Algoritmo", nombres[informacion.algoritmo])]
    if isinstance(informacion, InformacionArbol):
        campos.extend((("Aristas del árbol", str(informacion.aristas_arbol)),
                       ("Peso total", formatear_numero(informacion.peso_total))))
    elif isinstance(informacion, InformacionDijkstra):
        campos.extend((("Origen", informacion.origen),
                       ("Destino consultado", informacion.destino or "Sin seleccionar")))
        if informacion.condicion == "sin_consulta":
            campos.append(("Ruta", "Seleccioná un destino para consultar la ruta final"))
        elif informacion.condicion == "inalcanzable":
            campos.append(("Ruta", "Destino inalcanzable desde el origen"))
        else:
            campos.extend((("Ruta", " → ".join(informacion.ruta)),
                           ("Costo", formatear_numero(informacion.costo))))
    elif isinstance(informacion, InformacionFlujo):
        campos.extend((("Flujo máximo", formatear_numero(informacion.flujo_maximo)),
                       ("Capacidad del corte mínimo", formatear_numero(proyeccion.capacidad_corte))))
    elif isinstance(informacion, (InformacionCPM, InformacionPERT)):
        duracion = (informacion.duracion_proyecto if isinstance(informacion, InformacionCPM)
                    else informacion.duracion_esperada)
        campos.extend((("Duración total" if isinstance(informacion, InformacionCPM) else "Duración esperada",
                        formatear_numero(duracion)),
                       ("Actividades críticas", str(len(proyeccion.actividades_criticas))),
                       ("Cantidad de rutas críticas", str(informacion.rutas_criticas.cantidad_total))))
    return tuple(campos)


def _mostrar_detalles_resultado(informacion: InformacionResultado) -> None:
    """Presenta los detalles posteriores al grafo, sin repetir el resumen común."""
    if isinstance(informacion, (InformacionArbol, InformacionDijkstra)):
        return  # Su información ya está completa en el resumen principal.
    if isinstance(informacion, InformacionFlujo):
        st.markdown("#### Flujos por arco")
        st.dataframe([
            {"ID": a.identificador, "Origen": a.origen, "Destino": a.destino,
             "Dirección": "Dirigida" if a.dirigida else "No dirigida",
             "Capacidad": formatear_numero(a.capacidad_original), "Flujo": formatear_numero(a.flujo)}
            for a in informacion.arcos
        ], hide_index=True)
        return

    st.markdown("#### Rutas críticas")
    muestra = informacion.rutas_criticas
    for indice, ruta in enumerate(muestra.rutas, 1):
        st.write(f"Ruta {indice}: {' → '.join(ruta)}")
    if muestra.hay_mas:
        st.caption(f"Mostrando {len(muestra.rutas)} de {muestra.cantidad_total} rutas críticas.")

    st.markdown("#### Actividades")
    columnas = []
    if isinstance(informacion, InformacionPERT):
        columnas.extend((("Optimista", "optimista"), ("Más probable", "mas_probable"),
                         ("Pesimista", "pesimista"), ("Tiempo esperado", "tiempo_esperado"),
                         ("Varianza", "varianza")))
    columnas.extend((("IC", "ic"), ("TC", "tc"), ("IL", "il"), ("TL", "tl"), ("Holgura", "holgura")))
    # Los textos son copias para la tabla. La información tipada conserva floats.
    st.dataframe([
        {"Actividad": fila.actividad,
         **{titulo: formatear_numero(getattr(fila, atributo)) for titulo, atributo in columnas}}
        for fila in informacion.actividades
    ], hide_index=True)

    if isinstance(informacion, InformacionPERT):
        st.markdown("#### Variabilidad de rutas críticas")
        if muestra.cantidad_total == 1:
            st.caption("Variabilidad de la única ruta crítica del proyecto.")
        else:
            st.caption("Las métricas corresponden a cada ruta crítica, bajo la hipótesis de actividades independientes.")
        variabilidad = informacion.variabilidad
        if variabilidad.valores:
            st.dataframe([
                {"Ruta": " → ".join(v.actividades),
                 "Duración esperada": formatear_numero(v.duracion_esperada),
                 "Varianza": formatear_numero(v.varianza),
                 "Desviación estándar": formatear_numero(v.desviacion_estandar)}
                for v in variabilidad.valores
            ], hide_index=True)
        if isinstance(variabilidad, VariabilidadInterrumpida):
            st.warning(f"No se pudo evaluar la variabilidad de la ruta {' → '.join(variabilidad.error.ruta)}: "
                       f"{variabilidad.error.mensaje}")
            if variabilidad.rutas_no_evaluadas:
                st.warning("Las rutas posteriores de la muestra no pudieron evaluarse porque el generador "
                           "se interrumpió: " + "; ".join(" → ".join(r) for r in variabilidad.rutas_no_evaluadas))


def main():
    st.set_page_config(page_title="Visualizador de grafos", layout="wide")
    st.title("Visualización y recorrido de algoritmos")
    st.caption("Cargá una red para inspeccionarla y, cuando quieras, iniciar un algoritmo.")

    formato: FormatoGrafo = st.selectbox("Formato", ("Conexiones", "CPM", "PERT"), key="hu07_formato")
    
    # --- SELECTOR DE ORIGEN DE DATOS ---
    origen_modo = st.radio(
        "Origen de los datos:",
        ("Ejemplo precargado de cátedra", "Subir archivo CSV"),
        horizontal=True
    )

    contenido_bytes = None
    nombre_fuente = ""

    if origen_modo == "Ejemplo precargado de cátedra":
        opciones_ejemplos = list(_EJEMPLOS_CATEDRA[formato].keys())
        ejemplo_elegido = st.selectbox("Seleccioná el caso de prueba:", opciones_ejemplos)
        csv_texto = _EJEMPLOS_CATEDRA[formato][ejemplo_elegido]
        contenido_bytes = csv_texto.encode("utf-8")
        nombre_fuente = f"Ejemplo cátedra: {ejemplo_elegido}"
    else:
        archivo = st.file_uploader("Archivo CSV", type=("csv",), key="hu07_archivo")
        if archivo is None:
            invalidar_si_cambia_la_carga(st.session_state, f"{formato}:sin-archivo")
            st.info("Seleccioná un archivo CSV compatible para cargar la red y comenzar la visualización.")
            return
        contenido_bytes = archivo.getvalue()
        nombre_fuente = f"Archivo: {archivo.name}"

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
    st.caption(nombre_fuente)
    col_nodos, col_aristas = st.columns(2)
    indicador_vertices = col_nodos.empty()
    indicador_aristas = col_aristas.empty()
    indicador_vertices.metric("Vértices", len(grafo.vertices))
    indicador_aristas.metric("Conexiones / precedencias", len(grafo.aristas))

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
        st.info("El contenido no contiene aristas ni precedencias.")

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
            informacion = obtener_informacion_resultado(
                st.session_state["hu07_entrada"], resultado, st.session_state["hu07_algoritmo"],
                destino=proyeccion.destino if isinstance(proyeccion, ProyeccionDijkstra) else None,
            )
            indicador_vertices.metric("Vértices", informacion.general.vertices_originales)
            indicador_aristas.metric("Conexiones / precedencias", informacion.general.aristas_originales)
            st.subheader("Resultado final")
            st.subheader("Información del resultado")
            st.markdown(f"**Vértices del grafo original:** {informacion.general.vertices_originales}")
            st.markdown(f"**Aristas del grafo original:** {informacion.general.aristas_originales}")
            for etiqueta, valor in resumen_resultado(informacion, proyeccion):
                st.markdown(f"**{etiqueta}:** {valor}")
            red = visualizador.construir_red_resultado(
                st.session_state["hu07_entrada"], formato, proyeccion,
                st.session_state["hu07_posiciones_ejecucion"],
            )
            st.iframe(visualizador.generar_html(red), height=730, tab_index=0)
            _mostrar_detalles_resultado(informacion)
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
        st.info("The execution contains no recorded steps.")

    try:
        estado_visual = reconstruccion.estado_en(actual)
    except (ErrorReconstruccion, IndexError) as error:
        st.error(str(error))
        return
    _mostrar_estado(estado_visual, st.session_state["hu07_entrada"])
    visualizador.mostrar_grafo(
        st.session_state["hu07_entrada"], formato, arista_seleccionada,
        st.session_state["hu07_posiciones_graduacion" if False else "hu07_posiciones_ejecucion"], estado_visual,
    )


if __name__ == "__main__":
    main()
