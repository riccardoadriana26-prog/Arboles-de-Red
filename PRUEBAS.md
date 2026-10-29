# Pruebas del núcleo de selección y resolución

Ejecución final del 29 de octubre de 2026, con Python 3.14.0 en Windows y
coverage 7.17.0: **133 métodos, 32.145 subcasos, cero fallos, cero errores y
cero omitidos**. De esos subcasos, 31.574 corresponden a los dominios exhaustivos
de la tabla siguiente. Tiempo observado con cobertura: 22,645 segundos.
Cobertura del paquete: **969/969 líneas ejecutables y 294/294 ramas medidas
(100 % en ambas métricas)**. Los hashes del código y las pruebas se registran
en [resultado.json](informes/pruebas-core/resultado.json); el detalle está en
[ejecucion.txt](informes/pruebas-core/ejecucion.txt) y
[cobertura.txt](informes/pruebas-core/cobertura.txt).
La herramienta excluye 28 líneas mediante sus reglas predeterminadas; las
ubicaciones exactas también figuran en `cobertura.json`.

El núcleo incluye carga y validación de datos, preparación de entradas,
comprobación de compatibilidad, selección explícita y resolución de los seis
algoritmos. Estas pruebas recorren las interfaces públicas y contrastan sus
resultados con enumeraciones independientes. No se incluyen pantallas ni
controles gráficos todavía no implementados.

## Enumeración exhaustiva dentro de dominios finitos

| Área | Dominio completo enumerado | Escenarios |
| --- | --- | ---: |
| Prim y Kruskal | Cuatro vértices, seis conexiones posibles. Cada conexión está ausente o tiene peso -1, 0 o 2. Se verifican ambos algoritmos y se rechazan los grafos desconectados. | 4.096 |
| Dijkstra dirigido | Tres vértices, seis arcos posibles, cada uno ausente o con peso 0, 1 o 2. Cada grafo se resuelve desde los tres orígenes. | 12.288 |
| Dijkstra mixto | Tres vértices; cada par puede no tener conexión, ser no dirigido con peso 0 o 2, o dirigido con peso 1 en cualquiera de los sentidos. Se consultan los seis pares origen/destino. | 750 |
| Ford–Fulkerson | Todos los grafos dirigidos de tres vértices con arcos ausentes o capacidades 0, 1 o 2, y todos los de cuatro vértices con arcos ausentes o capacidad 1. Se comprueba cada aumento. | 8.192 |
| CPM | Las 64 combinaciones de precedencias compatibles con un orden de cuatro actividades, con las 81 combinaciones de duraciones 0, 1 y 2. Incluye cargas en orden inverso. | 5.184 |
| PERT | Ocho redes AON sobre tres actividades y 125 combinaciones de tripletas: (0,0,0), (1,1,1), (0,1,2), (0,0,6) y (0,2,6). Incluye igual duración esperada con distinta varianza. | 1.000 |
| Ciclos AON | Las 64 topologías dirigidas sobre tres actividades. Se contrasta la compatibilidad CPM y PERT con la existencia de algún orden válido. | 64 |
| **Total** | Cada fila cuenta escenarios; un escenario puede comprobar varios algoritmos, destinos, pasos e invariantes. | **31.574** |

Los oráculos de `tests/oraculos.py` no invocan los resolutores del programa:

- Árbol mínimo: enumeran todos los subconjuntos de V-1 aristas y comparan sus costos cuando conectan todos los vértices.
- Caminos mínimos: enumeran caminos simples y comparan sus costos por destino.
- Flujo máximo: enumeran todos los cortes fuente/sumidero. También comprueban conservación, capacidades y reproducen las actualizaciones residuales de los pasos.
- CPM/PERT: enumeran caminos completos de la AON para obtener duración, rutas críticas y los cinco tiempos de cada actividad, sin usar las dos pasadas del programa como oráculo.

## Casos de uso y límites adicionales

| Grupo | Cobertura funcional |
| --- | --- |
| Lectura | UTF-8 con y sin BOM, LF/CRLF/CR, archivo inexistente, contenido de codificación inválida y ruta de directorio. |
| CSV | Todas las permutaciones de columnas de los tres formatos con y sin comillas; encabezados faltantes, repetidos o ajenos, archivos vacíos, sintaxis inválida, filas sobrantes o incompletas, referencias inexistentes, duplicados y diagnósticos con línea y columna. |
| Selección | Catálogo de seis opciones, parámetros obligatorios y opcionales, datos CPM/PERT reutilizados, incompatibilidad con motivo, identificador desconocido, extensibilidad y ausencia de selección automática de otro algoritmo. |
| Modelo | Lazos, tipos ambiguos, identificadores inválidos o repetidos, extremos ausentes, aristas paralelas, pesos ausentes, no reales, infinitos y fuera de rango. |
| Árboles | Grafo de un vértice, desconexión, pesos negativos y cero, empates estables, ciclos y conexiones paralelas con identificadores no consecutivos. |
| Dijkstra | Grafo dirigido, no dirigido o mixto; destino opcional, origen igual a destino, inaccesibles, ciclos y aristas de peso cero, empates decimales, ruta y aristas originales. Los pasos reconstruyen las distancias. |
| Flujo | Flujo cero, terminales inválidos, capacidades cero y decimales, paralelas y antiparalelas, arcos hacia la fuente y desde el sumidero, uso de arcos inversos, corte mínimo y reconstrucción de cada aumento. |
| CPM/PERT | Actividad única, duraciones cero, actividades independientes, múltiples componentes, comienzos y finales, precedencias paralelas o redundantes, carga desordenada, rechazo de ciclos, parámetros Decimal/Fraction y múltiples rutas críticas. |
| Integridad | Rechazos sin alterar cargas anteriores, mapas copiados e inmutables, soluciones y detalles inmutables, repetición e intercalación de iteradores de rutas independientes. |
| Concurrencia | 120 resoluciones en ocho hilos compartiendo instancias de los seis algoritmos, comparadas con resultados secuenciales y sin compartir objetos de resultado. No es una prueba de carga del sistema operativo. |
| Transformaciones | Renombrar vértices, invertir extremos de aristas no dirigidas, escalar pesos/capacidades/tiempos, dividir capacidad en paralelas y verificar que las métricas cambian como corresponde. |
| Escala | Los seis resolutores sobre cadenas de 1.500 vértices; grafos completos y DAG completos de 200 vértices y 19.900 aristas; flujo en 200 vértices y 9.999 arcos con 99 aumentos. |
| Número de rutas | Redes CPM/PERT de 200 actividades con 2^100 rutas críticas, contadas de forma compacta y recorridas de manera acotada. |
| Rango numérico | Desbordes de pesos, distancias, duración, flujo y varianza; valores no nulos que no caben en float; capacidades subnormales representables y estimaciones PERT grandes cuya media sí cabe en rango. |

## Fallos encontrados y correcciones

1. **Comparaciones decimales de Dijkstra.** Una ruta de pesos 0,1 y 0,2 podía perder frente a una arista de peso 0,30000000000000004; también se alteraba la regla de conservar la primera ruta de igual costo. Las comparaciones y sumas ahora usan racionales a partir de la representación decimal de los pesos normalizados.
2. **Desborde de un candidato descartado.** Dijkstra abortaba al evaluar 1e308 + 1e308 aunque ya conociera para ese vértice una ruta de 1,5e308. La comparación exacta permite descartarlo sin convertirlo a float.
3. **Conversión silenciosa a cero.** Un valor positivo como 1e-400 podía convertirse a cero al cargarlo o publicar un resultado, incluida la varianza de PERT. CSV y modelo lo rechazan en la entrada; los cálculos informan `ErrorCalculoNumerico`. Los subnormales que sí pueden representarse continúan admitidos.

El cambio de validación conserva los decimales originales para informar además
errores de orden en las tripletas PERT. Por eso un optimista positivo fuera de
rango y mayor que el tiempo más probable puede producir ambos diagnósticos.
La suma de varianzas por ruta se evalúa a demanda: si esa suma desborda, el
error se comunica al recorrer `variabilidad_rutas()`.

## Ejecución reproducible

Desde la raíz del repositorio, con Python 3.14:

```sh
py -3.14 -m unittest discover -s tests -v
py -3.14 scripts/ejecutar_pruebas.py --salida informes/pruebas-core
```

La primera instrucción ejecuta las pruebas con la biblioteca estándar. La
segunda agrega un log, contador de subcasos, tiempos observados y hashes SHA-256
del código y las pruebas. Para medir líneas y ramas:

```sh
py -3.14 -m pip install coverage==7.17.0
py -3.14 scripts/ejecutar_pruebas.py --cobertura --salida informes/pruebas-core
```

`coverage` es una herramienta de desarrollo; no participa en los algoritmos.
`informes/pruebas-core/resultado.json` registra la ejecución, y `cobertura.json`
expone las líneas y ramas medidas. Los tiempos con instrumentación no deben
interpretarse como un benchmark de rendimiento.

La revisión estática con Pyright conserva cuatro diagnósticos previos de
sobrescritura de propiedades y tipos genéricos en `registro.py`, ya presentes
en el commit de base efd2811. No aparecen diagnósticos nuevos en el paquete.

## Límites de la evidencia

La enumeración es exhaustiva únicamente en los dominios descritos. Las entradas
de tamaño arbitrario, los valores reales posibles y todas las intercalaciones
de hilos no pueden enumerarse en una suite finita. La cobertura de líneas y
ramas mide ejecución del código, no demuestra por sí sola la corrección.

No se prueban una interfaz gráfica ni los controles de los issues pendientes.
La memoria para los pasos aumenta con su cantidad y detalle, especialmente las
instantáneas del flujo por arco; las redes densas probadas no garantizan una
cota de memoria para cualquier entrada. Enumerar todas las rutas críticas
puede tener costo exponencial, aunque contarlas y guardar su red sea compacto.
