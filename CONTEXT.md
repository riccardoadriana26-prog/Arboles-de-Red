# Grafos de red

Vocabulario común para los grafos que cargará la aplicación y utilizarán los algoritmos de redes.

## Lenguaje

**Grafo**:
Conjunto de vértices y aristas sobre el que se puede evaluar la aplicación de un algoritmo de redes. Puede contener aristas dirigidas y no dirigidas, incluso en un mismo grafo.

**Vértice**:
Elemento del grafo identificado por un valor alfanumérico. Puede ser una actividad AON sin precedencias, incluso aislada.

**Arista**:
Conexión entre dos vértices que puede ser dirigida o no dirigida. Puede tener un peso real finito; una precedencia AON utiliza None para expresar ausencia de peso. Una arista no puede unir un vértice consigo mismo.

**Aristas paralelas**:
Aristas individuales que conectan el mismo par de vértices. Pueden compartir dirección y peso sin convertirse en una sola arista.

**Peso**:
Valor numérico real y finito asociado a una arista; puede ser positivo, negativo o cero.

**Entrada de algoritmo**:
Grafo y parámetros tipados propios del algoritmo que se utilizarán en una ejecución.

**Registro de algoritmos**:
Catálogo de algoritmos disponibles para seleccionar, cada uno con una identidad y unos requisitos de entrada propios. Incorporar una opción conserva las elecciones anteriores.

**Ejecución preparada**:
Selección de un algoritmo con su entrada específica, lista para consultar su compatibilidad y resolver. Conserva la carga original y los parámetros propios de esa elección.

**Actividad AON**:
Trabajo representado por un vértice de la red CPM o PERT. Tiene una duración en CPM o tres estimaciones en PERT, y puede existir sin precedencias.

**Predecesora inmediata**:
Actividad que debe terminar antes de que otra pueda comenzar, expresada por una arista dirigida sin peso desde la predecesora hacia la sucesora. Una actividad puede tener varias predecesoras inmediatas o ninguna.

**Duración CPM**:
Tiempo de una actividad, asociado a su identificador y no a las aristas de precedencia.

**Estimaciones PERT**:
Tripleta de tiempos optimista, más probable y pesimista de una actividad. Se conserva completa para calcular el tiempo esperado y la varianza durante la resolución.

**Condiciones de aplicación**:
Requisitos específicos del algoritmo que se verifican antes de resolver una entrada.

**Vértice inalcanzable**:
Vértice al que no se puede llegar desde el origen respetando la dirección de cada conexión. Su presencia se informa en Dijkstra y no implica por sí sola que el algoritmo no sea aplicable.

**Paso de ejecución**:
Decisión ordenada con descripción, referencias a vértices y aristas destacados, y un detalle propio del algoritmo.

**Resultado de algoritmo**:
Solución tipada propia del algoritmo y secuencia completa e inmutable de pasos. La solución contiene las métricas que correspondan, como el peso total.

## Decisiones acordadas

| Decisión | Referencia en el código |
| --- | --- |
| El grafo es la entrada común, independiente de los algoritmos. La dirección se define en cada arista; un mismo grafo puede combinar aristas dirigidas y no dirigidas. | [`Grafo`](./arboles_de_red/grafo.py), [`Arista`](./arboles_de_red/grafo.py), [API pública](./arboles_de_red/__init__.py) |
| Los vértices tienen identificadores alfanuméricos únicos. Se admiten vértices aislados para representar actividades independientes; no se admiten lazos. | [Validación de vértices y lazos](./arboles_de_red/grafo.py), [validación del grafo](./arboles_de_red/grafo.py) |
| Se conservan las aristas paralelas como entidades individuales, incluso si sus extremos, dirección y peso coinciden. Cada una tiene un identificador entero único dentro del grafo. Flujo Máximo podrá usar ambas; la selección de aristas para una solución corresponde al algoritmo. | [`Arista`](./arboles_de_red/grafo.py), [unicidad en `Grafo`](./arboles_de_red/grafo.py), [prueba de paralelas](./tests/test_grafo.py) |
| El peso es opcional: None representa una precedencia sin peso y se distingue de cero. Los enteros y reales finitos se normalizan a `float`, por lo que `8` y `8.0` representan el mismo peso. Se aceptan valores negativos y cero; se rechazan texto, `NaN` e infinitos. | [Validación del peso](./arboles_de_red/grafo.py), [pruebas de pesos](./tests/test_grafo.py) |
| El modelo es inmutable. Cargar otro CSV dará lugar a otro `Grafo`, no a una modificación del existente. | [`dataclass` inmutables y conversión a tuplas](./arboles_de_red/grafo.py), [prueba de inmutabilidad](./tests/test_grafo.py) |
| Un grafo puede tener componentes desconectados. Cada algoritmo verificará sus propias condiciones de aplicación antes de ejecutarse, según el [issue #3](https://github.com/camilamercad/arboles-de-red/issues/3). | [`Grafo`](./arboles_de_red/grafo.py), [prueba de desconexión](./tests/test_grafo.py) |
| El modelo puede representar un grafo vacío. La validación del CSV lo rechaza según el [issue #2](https://github.com/camilamercad/arboles-de-red/issues/2); una red AON de una sola actividad es válida. | [Prueba del grafo vacío](./tests/test_grafo.py), [validación CSV](./tests/test_validacion_csv.py) |
| La versión mínima es Python 3.14. Pueden incorporarse dependencias externas, pero la lógica de los algoritmos se implementará en el proyecto. Este modelo utiliza la biblioteca estándar. | [Configuración del proyecto](./pyproject.toml#L5), [modelo](./arboles_de_red/grafo.py) |
| Todos los algoritmos comparten una clase base genérica y reciben `Entrada` con `Grafo` y parámetros propios tipados. También son tipados la solución y el detalle de los pasos. | [`Algoritmo` y `Entrada`](./arboles_de_red/algoritmo.py), [ejemplo de implementación](./tests/test_algoritmo.py) |
| `es_aplicable` devuelve solamente `bool`; `motivo_inaplicabilidad` permite consultar el motivo o `None`. `ejecutar` verifica nuevamente las condiciones antes de resolver y, si falla, lanza `AlgoritmoNoAplicableError` con el motivo. Las condiciones pueden reutilizarse independientemente de la resolución. | [Comprobación y ejecución](./arboles_de_red/algoritmo.py), [condiciones por algoritmo](./arboles_de_red/aplicabilidad.py), [pruebas de rechazo](./tests/test_aplicabilidad.py) |
| El resultado contiene la solución propia del algoritmo y una secuencia completa e inmutable de pasos. Cada paso lleva número, descripción, identificadores de vértices y aristas destacados, y detalle tipado propio. | [`Resultado` y `Paso`](./arboles_de_red/algoritmo.py), [pruebas de inmutabilidad](./tests/test_algoritmo.py) |
| Los conteos de vértices y aristas salen del `Grafo`. Las métricas como peso total se exponen, cuando corresponda, desde la solución tipada del algoritmo. | [`Grafo`](./arboles_de_red/grafo.py), [solución del ejemplo](./tests/test_algoritmo.py) |
| Los seis algoritmos tienen resolución propia y reutilizan el contrato y las condiciones comunes. No utilizan librerías de grafos ni resolutores externos. | [Prim/Kruskal](./arboles_de_red/arbol_expansion.py), [Dijkstra](./arboles_de_red/dijkstra.py), [Ford–Fulkerson](./arboles_de_red/flujo_maximo.py), [CPM](./arboles_de_red/cpm.py), [PERT](./arboles_de_red/pert.py) |
| El issue #16 comprende contratos y estructura modular. La lectura obtiene texto de un archivo; el procesamiento valida e interpreta ese texto y construye un `Grafo`; la resolución usa `Algoritmo`; la visualización recibe el grafo y el resultado ya calculado. | [`LectorArchivo`](./arboles_de_red/lectura.py), [`ProcesadorGrafo`](./arboles_de_red/procesamiento.py), [`Algoritmo`](./arboles_de_red/algoritmo.py), [`Visualizador`](./arboles_de_red/visualizacion.py) |
| Las nuevas interfaces son clases base abstractas, como `Algoritmo`. Cada componente tiene su propio módulo y se comunica mediante texto, `Grafo`, `Entrada` y `Resultado`. Los algoritmos no dependen de la interfaz gráfica. | [API pública](./arboles_de_red/__init__.py), [integración con dobles](./tests/test_componentes.py) |
| El lector CSV y la visualización concretos quedan para sus respectivos issues. La codificación de archivos, los detalles del formato CSV y sus errores, y la tecnología de interfaz no se definen en el issue #16. | [Alcance del issue #16](./README.md#separación-de-responsabilidades-issue-16) |

Estas decisiones concretan los [issues #14](https://github.com/camilamercad/arboles-de-red/issues/14), [#15](https://github.com/camilamercad/arboles-de-red/issues/15) y [#16](https://github.com/camilamercad/arboles-de-red/issues/16). La carga de CSV se incorpora en el [issue #1](https://github.com/camilamercad/arboles-de-red/issues/1), con formatos de conexiones, CPM y PERT documentados en el README. Las resoluciones de los seis algoritmos y la API de selección se implementan en los issues #6 y #5. La visualización concreta sigue pendiente.

## Corrección del modelo #14 para redes AON

La bibliografía de CPM (diapositivas 3 y 9) y PERT (diapositivas 8 y 10) de la cátedra representa actividades en vértices y precedencias en aristas dirigidas. La duración o las tres estimaciones corresponden a cada actividad y se asocian a su identificador mediante los parámetros tipados de Entrada.

Se reemplazan las decisiones anteriores de prohibir vértices aislados y exigir peso en toda arista. El modelo admite una actividad sin conexiones y precedencias con peso=None; mantiene la inmutabilidad, la identidad individual de aristas paralelas y la validación de pesos reales finitos cuando están presentes. Véanse [modelo](./arboles_de_red/grafo.py), [pruebas](./tests/test_grafo.py) y [ejemplo de uso](./README.md#modelo-común-de-grafos-issue-14).

El modelo no decide si una red cumple las condiciones de un algoritmo. La carga de actividades se incorpora en el issue #1 y la validación del contenido en el issue #2. El issue #3 incorpora las condiciones de aplicación, incluidos los ciclos y la conectividad, sin resolver los algoritmos del issue #6.

El issue #17 incorpora el catálogo y la preparación de entradas de los seis algoritmos. Las implementaciones de resolución del issue #6 se conectan mediante el contrato común, conservando sus condiciones, soluciones y pasos propios.

## Resolución #6 y selección #5

Los algoritmos se implementan desde cero y no dependen de la interfaz gráfica.
Prim/Kruskal conservan las aristas originales; Dijkstra conserva las rutas y
distancias; Ford–Fulkerson mantiene un par residual propio por arista, incluso
para conexiones paralelas y antiparalelas. Sus pasos identifican arcos inversos
y ambas actualizaciones residuales. CPM y PERT usan actividades en vértices,
precedencias dirigidas y dos pasadas sobre un orden topológico.

Se preservan todas las rutas críticas en una red compacta con un contador y
enumeración a demanda. Para PERT, por decisión acordada, se expone la varianza
y la desviación estándar de cada ruta crítica sin elegir una automáticamente.
La suma de varianzas por ruta supone actividades independientes. La consulta
probabilística contra una fecha objetivo corresponde al #9; no se incorpora
crashing de CPM en el #6.

El #5 se implementa, según lo acordado, como una API para la futura interfaz
gráfica. `SelectorAlgoritmos` usa el registro del #17, lista las opciones y
devuelve una `SeleccionAlgoritmo` con entrada, compatibilidad y motivo.
No ejecuta al seleccionar ni cambia de algoritmo ante una incompatibilidad.
`crear_registro_predeterminado` conecta las seis clases concretas y conserva
la alternativa de inyectar un catálogo extensible. Cada ejecución vuelve a
comprobar las condiciones y crea su propio estado.

Las soluciones y pasos son inmutables y no alteran la carga. Los controles de
recorrido reproducirán la secuencia completa después de calcularla. El README
documenta los campos concretos, los empates y los errores numéricos. Las pruebas
contrastan los ejemplos de la cátedra y redes pequeñas con enumeración exhaustiva,
incluyen arcos inversos y realizan ejecuciones completas con 200 vértices.

## Ampliación de pruebas y precisión numérica

El alcance reproducible se documenta en [PRUEBAS.md](./PRUEBAS.md), con
enumeración de dominios pequeños, oráculos independientes, validación de pasos,
casos densos, cadenas largas y ejecuciones concurrentes. La evidencia incluye
hashes del código y las pruebas ejecutadas.

Las regresiones detectaron que las sumas float podían alterar rutas y empates
de Dijkstra. Sus comparaciones usan ahora racionales, como las de planificación
y flujo. También se evita convertir candidatos descartados fuera de rango.
Los números no nulos que se convertirían en cero se rechazan en CSV y modelo;
cuando ese límite se alcanza al calcular se informa `ErrorCalculoNumerico`.
