# arboles-de-red

## Desarrollo de una aplicación para algoritmos de redes 

### Objetivo 

 - Desarrollar una aplicación que permita cargar, representar y resolver grafos de diferentes tamaños, utilizando los algoritmos de redes trabajados durante la cátedra. 
 - La aplicación deberá permitir al usuario ingresar grafos de distintas dimensiones, desde grafos pequeños utilizados para verificar los resultados hasta grafos de mayor tamaño, con el objetivo de comprobar el funcionamiento de los algoritmos en diferentes escenarios.

### Requerimientos 

La aplicación deberá: 

 - Permitir la carga de grafos de diferentes tamaños. Por ejemplo, deberá ser posible trabajar tanto con un grafo de 10 nodos como con uno de 200 nodos.
 - Permitir ingresar la información necesaria para definir las conexiones del grafo y sus respectivos valores o pesos, cuando corresponda.
 - Representar adecuadamente el grafo y/o la información ingresada.
 - Implementar los algoritmos de redes trabajados durante la asignatura (Prim, Kruskal, Dijkstra, Flujo Máximo, CPM, PERT).
 - Mostrar de manera clara los resultados obtenidos por cada algoritmo.

### Modelo común de grafos (issue #14)

El paquete `arboles_de_red` expone `Grafo` y `Arista` para que los futuros
algoritmos reciban una misma representación, sin depender de la carga de CSV
ni de la interfaz. Requiere Python 3.14 o superior.

```python
from arboles_de_red import Arista, Grafo

grafo = Grafo(
    vertices=("A", "B", "C"),
    aristas=(
        Arista(0, "A", "B", 8, dirigida=False),
        Arista(1, "B", "C", 2.5, dirigida=True),
    ),
)
```

Cada arista tiene un identificador entero único dentro del grafo. Esto permite
conservar aristas paralelas aunque coincidan sus extremos, dirección y peso.
Los pesos presentes se almacenan como `float` finitos; se aceptan valores negativos y
cero. La dirección se define por arista, así que un grafo puede combinar
aristas dirigidas y no dirigidas.

El modelo es inmutable y rechaza lazos e identificadores de
vértice no alfanuméricos, extremos inexistentes e identificadores repetidos.
Acepta componentes desconectados: cada algoritmo decidirá si puede aplicarse
según el issue #3. Un grafo vacío es representable en el modelo; la validación
del CSV lo rechaza según el issue #2.

Para representar redes AON de CPM y PERT, cada vértice identifica una actividad
y las aristas dirigidas expresan precedencia. Una precedencia utiliza
`peso=None`, que indica ausencia de peso y se distingue de un peso cero.
Se admiten actividades aisladas y redes con una única actividad sin aristas:

```python
precedencias = Grafo(
    vertices=("A", "B", "Independiente"),
    aristas=(Arista(0, "A", "B", None, dirigida=True),),
)
actividad_unica = Grafo(vertices=("A",), aristas=())
```

Las duraciones CPM y las estimaciones PERT pertenecen a las actividades y se
asociarán a sus identificadores mediante los parámetros tipados de `Entrada`.
Su carga corresponde al issue #1; su validación, a los issues #2 y #3. El modelo conserva
la topología; cada algoritmo verificará los datos necesarios para ejecutarse.

Para ejecutar las pruebas:

```sh
py -3.14 -m unittest discover -s tests -v
```

### Contrato común de algoritmos (issue #15)

Cada algoritmo hereda de `Algoritmo[Parametros, Solucion, Detalle]` y recibe una
`Entrada(grafo, parametros)`. Los parámetros, la solución y el detalle de cada
paso tienen tipos propios de ese algoritmo. Una implementación mínima se
encuentra en [`tests/test_algoritmo.py`](tests/test_algoritmo.py).

La aplicación puede llamar `es_aplicable(entrada)`, que devuelve `bool`, y
`motivo_inaplicabilidad(entrada)`, que devuelve un motivo o `None`, antes
de iniciar la ejecución. `ejecutar(entrada)` vuelve a comprobar las condiciones:
si no se cumplen, lanza `AlgoritmoNoAplicableError` con el motivo; si se cumplen,
devuelve `Resultado(solucion, pasos)`. Cada implementación recibe sus condiciones
y define `_resolver`; las implementaciones anteriores pueden conservar
`_motivo_inaplicabilidad`, sin cambiar el mecanismo público.

`Resultado.pasos` es una secuencia completa e inmutable en orden de ejecución.
Cada `Paso` contiene un número, una descripción, los identificadores de
vértices y aristas para destacar, y un detalle tipado propio del algoritmo.
La interfaz puede mostrar los conteos a partir de `Entrada.grafo`; las métricas
que correspondan, como el peso total, pertenecen a `Resultado.solucion`.

### Separación de responsabilidades (issue #16)

Cada responsabilidad tiene una clase base abstracta en su propio módulo:

| Componente | Contrato | Responsabilidad |
| --- | --- | --- |
| Lectura | `LectorArchivo.leer(ruta: str \| Path) -> str` | Obtener el texto del archivo, sin interpretarlo como grafo. |
| Procesamiento | `ProcesadorGrafo.procesar(contenido: str) -> Grafo` | Validar e interpretar el texto para construir el grafo, sin acceder a archivos. |
| Resolución | `Algoritmo.ejecutar(entrada: Entrada) -> Resultado` | Verificar las condiciones del algoritmo y calcular su solución y pasos. |
| Visualización | `Visualizador.mostrar_grafo(grafo)` y `mostrar_resultado(grafo, resultado)` | Presentar el grafo original y los resultados ya calculados, sin ejecutar algoritmos. |

Los módulos son [`lectura.py`](arboles_de_red/lectura.py),
[`procesamiento.py`](arboles_de_red/procesamiento.py),
[`algoritmo.py`](arboles_de_red/algoritmo.py) y
[`visualizacion.py`](arboles_de_red/visualizacion.py). Todos los contratos se
exportan desde `arboles_de_red`.

La aplicación coordinará los componentes a través de estas interfaces:

```python
# lector, procesador, algoritmo y visualizador son implementaciones concretas.
contenido = lector.leer(ruta)
grafo = procesador.procesar(contenido)
visualizador.mostrar_grafo(grafo)
resultado = algoritmo.ejecutar(Entrada(grafo, parametros))
visualizador.mostrar_resultado(grafo, resultado)
```

`Visualizador[Solucion, Detalle]` utiliza los mismos tipos de solución y detalle
que el algoritmo. El algoritmo solo recibe `Entrada` y devuelve `Resultado`;
no conoce al lector, al procesador ni a la interfaz gráfica. Las condiciones
de aplicación pertenecen al algoritmo, mientras que la validación del formato
pertenece al procesador.

El issue #16 define contratos y estructura modular. La carga concreta de CSV
se incorpora en el issue #1, como se describe a continuación. La validación
detallada, la interfaz gráfica y los controles de recorrido corresponden a
sus respectivos issues.
[`tests/test_componentes.py`](tests/test_componentes.py) demuestra la integración
mediante dobles en memoria y el algoritmo de ejemplo, sin implementar CSV ni
una interfaz gráfica.

### Carga de CSV (issue #1)

`LectorTexto` implementa `LectorArchivo`: lee archivos UTF-8 con o sin BOM y
devuelve texto. Cada procesador interpreta un formato concreto sin acceder
al sistema de archivos:

| Procesador | `preparar_entrada(contenido)` |
| --- | --- |
| `ProcesadorConexionesCSV` | `Entrada[None]`: grafo con pesos y dirección por arista. |
| `ProcesadorCPMCSV` | `Entrada[ParametrosCPM]`: precedencias y duraciones por actividad. |
| `ProcesadorPERTCSV` | `Entrada[ParametrosPERT]`: precedencias y estimaciones por actividad. |

Los tres heredan de `ProcesadorCSV`, que conserva el contrato
`ProcesadorGrafo.procesar(contenido) -> Grafo`. Para CPM/PERT se usa
`preparar_entrada` cuando también se necesitan los datos de las actividades.
Cada llamada construye un grafo y una entrada nuevos e inmutables. Los mapas
de duraciones y estimaciones también son inmutables y copian sus datos de origen.

Los archivos usan encabezado, coma como separador de columnas y punto decimal.
Las listas de predecesoras se separan con `;`; un campo vacío indica que la
actividad no tiene predecesoras. El orden de las filas no tiene que ser el
orden de precedencia. Los identificadores son alfanuméricos, como exige `Grafo`.

#### Conexiones ponderadas

El formato original `origen,destino,peso` carga aristas no dirigidas:

```csv
origen,destino,peso
A,B,8
B,C,2.5
```

La columna opcional `dirigida` admite `true` o `false` por arista. Si se incluye,
cada fila debe indicar uno de esos valores. Las conexiones dirigidas van de
`origen` a `destino`. Se conservan las conexiones paralelas, con identificadores
distintos asignados desde cero en orden de lectura. Se admiten pesos negativos
y cero; en Flujo Máximo el peso representa la capacidad y las conexiones deben
declararse dirigidas. Ejemplo descargable: [`conexiones.csv`](ejemplos/conexiones.csv).

```csv
origen,destino,peso,dirigida
A,B,8,false
A,C,3.5,true
A,B,8,false
```

El CSV contiene los datos de las conexiones. Los parámetros de ejecución,
como el origen de Dijkstra o la fuente y el sumidero de Flujo Máximo, los aporta
la aplicación al preparar `Entrada(grafo, parametros_del_algoritmo)`.

#### Actividades CPM en AON

Cada fila declara una actividad una única vez, con su duración y sus
predecesoras inmediatas. `C` tiene dos predecesoras y `Independiente` no
participa en ninguna precedencia. Ejemplo: [`cpm.csv`](ejemplos/cpm.csv).

```csv
actividad,duracion,predecesoras
A,2,
B,3,A
C,4.5,A;B
Independiente,1,
```

Las duraciones quedan en `entrada.parametros.duraciones`, un mapa de
identificador de actividad a `float`. Las precedencias son aristas dirigidas
con `peso=None`. Una actividad sin predecesoras puede constituir por sí sola
una red válida; no hace falta agregar actividades ficticias ni aristas con peso.

#### Actividades PERT en AON

Cada actividad conserva sus tres estimaciones originales, sin reemplazarlas
por un peso calculado. Ejemplo: [`pert.csv`](ejemplos/pert.csv).

```csv
actividad,optimista,mas_probable,pesimista,predecesoras
A,1,2,9,
B,2,3,4,A
C,2,4,8,A;B
Independiente,1,1,1,
```

`entrada.parametros.estimaciones` asocia cada identificador a una
`EstimacionesPERT(optimista, mas_probable, pesimista)` inmutable. El tiempo
esperado y la varianza se calcularán al resolver, no durante la carga.

#### Uso desde la aplicación

```python
from arboles_de_red import LectorTexto, ProcesadorCPMCSV

contenido = LectorTexto().leer("ejemplos/cpm.csv")
entrada = ProcesadorCPMCSV().preparar_entrada(contenido)
assert entrada.parametros.duraciones["C"] == 4.5

# Con implementaciones concretas del visualizador y del algoritmo:
# visualizador.mostrar_grafo(entrada.grafo)
# resultado = algoritmo.ejecutar(entrada)
# visualizador.mostrar_resultado(entrada.grafo, resultado)
```

La carga respeta las restricciones del modelo existente y valida el contenido
según el issue #2. Las condiciones propias de cada algoritmo, incluidos ciclos
y conectividad, corresponden al
[issue #3](https://github.com/camilamercad/arboles-de-red/issues/3).
La carga no ejecuta algoritmos ni fija el orden de selección en la interfaz.

### Validación de CSV (issue #2)

Tanto `procesar` como `preparar_entrada` lanzan `ErrorValidacionCSV` cuando el
contenido es inválido. Su atributo `errores` es una tupla de `DiagnosticoCSV`
inmutables con `linea`, `columna` y `mensaje`. Las líneas se numeran desde uno
y corresponden al archivo original; si un registro ocupa varias líneas, se
informa la primera. `columna=None` identifica problemas de la fila completa.
El texto de la excepción incluye todos los diagnósticos reunidos.

| Estructura | Reglas de contenido |
| --- | --- |
| Todas | Encabezado obligatorio, con nombres exactos y sin columnas faltantes, repetidas ni ajenas al formato. Se admite cualquier orden de columnas. Cada fila tiene la misma cantidad de campos que el encabezado. Se rechazan errores de sintaxis CSV y archivos sin datos. |
| Conexiones | Extremos alfanuméricos no vacíos, distintos entre sí; peso real finito, incluyendo cero y negativos. Si está la columna `dirigida`, cada fila debe indicar `true` o `false`. |
| Actividades AON | Identificadores alfanuméricos únicos y predecesoras existentes, aunque se declaren después. Se admite el campo de predecesoras vacío, varias predecesoras y actividades independientes. Cada elemento de una lista no vacía debe ser un identificador; no se admiten lazos, como exige el modelo. |
| CPM | Una duración real finita y no negativa por actividad. |
| PERT | Tres estimaciones reales finitas con `0 <= optimista <= mas_probable <= pesimista`. |

El signo y el orden se verifican sobre los valores decimales originales para
que el redondeo no oculte números negativos ni estimaciones desordenadas.
Los valores también deben poder convertirse a un `float` finito, como exige
el modelo; su normalización se realiza después de validar el contenido.

Los campos obligatorios no pueden estar vacíos, excepto `predecesoras`. Las
líneas vacías después del encabezado se omiten; una fila con campos vacíos se
valida y puede producir errores. Las precedencias no requieren peso, y no se
piden resultados calculados como tiempos tempranos o tardíos, holgura, tiempo
esperado ni varianza. Una red AON de una sola actividad sigue siendo válida.

```python
from arboles_de_red import ErrorValidacionCSV, ProcesadorConexionesCSV

try:
    entrada = ProcesadorConexionesCSV().preparar_entrada(
        "origen,destino,peso,dirigida\nA,B,nan,si\n"
    )
except ErrorValidacionCSV as error:
    for diagnostico in error.errores:
        print(diagnostico)
```

Este ejemplo informa dos errores en la línea 2: peso no finito y dirección
distinta de `true` o `false`. Se reúnen errores de varias filas y campos antes
de construir el grafo. Un encabezado inválido impide interpretar las filas;
un error de sintaxis CSV detiene la lectura, conservando los diagnósticos que
se puedan obtener de los registros anteriores. Una fila con cantidad incorrecta
de campos se informa y se continúa con las siguientes.

Si hay errores no se devuelve una entrada ni un grafo parcial, ni se modifican
las cargas anteriores. Los ciclos entre actividades distintas y los componentes
desconectados se conservan para comprobar la aplicabilidad en el issue #3.

### Condiciones de aplicación (issue #3)

Las condiciones pueden consultarse antes de disponer de la resolución concreta
de cada algoritmo. `CondicionesAplicacion[Parametros]` expone
`es_aplicable(entrada) -> bool` y
`motivo_inaplicabilidad(entrada) -> str | None`. Una entrada compatible devuelve
`True` y motivo `None`; una incompatible devuelve `False` y el primer motivo
encontrado, sin modificar sus datos ni seleccionar otro algoritmo.

| Algoritmo | Condiciones reutilizables | Requisitos |
| --- | --- | --- |
| Prim y Kruskal | `CondicionesArbolExpansion` | Grafo no vacío, no dirigido y conexo, con peso en todas las aristas. Se aceptan pesos negativos y cero. Un vértice aislado impide la conectividad si hay otros vértices; un único vértice constituye una entrada válida. |
| Dijkstra | `CondicionesDijkstra` | Pesos no negativos y `ParametrosDijkstra(origen, destino=None)`, con terminales existentes. Admite aristas dirigidas y no dirigidas, incluso mezcladas, y vértices inalcanzables. |
| Ford–Fulkerson | `CondicionesFlujoMaximo` | Red dirigida con capacidades no negativas y `ParametrosFlujoMaximo(fuente, sumidero)`, ambos existentes y distintos. No exige un camino entre los terminales ni flujo positivo. |
| CPM | `CondicionesCPM` | AON no vacío, dirigido y sin ciclos; `ParametrosCPM` con una duración real finita no negativa por actividad. |
| PERT | `CondicionesPERT` | AON no vacío, dirigido y sin ciclos; `ParametrosPERT` con una tripleta completa por actividad y `0 <= optimista <= mas_probable <= pesimista`, con valores reales finitos. |

`Grafo` ya garantiza que los pesos presentes sean reales finitos. Las condiciones
rechazan pesos ausentes cuando el algoritmo los necesita. Para CPM/PERT, los
mapas deben contener exactamente los identificadores de las actividades: se
rechazan datos faltantes, datos de actividades inexistentes e identificadores
de aristas usados como claves. Las claves son únicas por definición del mapa;
las actividades y columnas repetidas en CSV se rechazan en la validación del #2.

CPM/PERT admiten actividades independientes y redes de una sola actividad sin
aristas. No obtienen duraciones ni estimaciones a partir de los pesos de las
precedencias, ni calculan tiempos esperados al validar. Se conservan las aristas
paralelas; la detección de ciclos las cuenta individualmente y no las confunde
con un ciclo. El signo y el orden de los tiempos se comprueban sobre los números
recibidos, antes de cualquier redondeo.

```python
from arboles_de_red import (
    CondicionesDijkstra, Entrada, ParametrosDijkstra, ProcesadorConexionesCSV,
)

grafo = ProcesadorConexionesCSV().procesar(
    "origen,destino,peso,dirigida\nA,B,2,true\nC,B,1,true\n"
)
entrada = Entrada(grafo, ParametrosDijkstra("A", "C"))
condiciones = CondicionesDijkstra()
assert condiciones.es_aplicable(entrada) is True
assert condiciones.motivo_inaplicabilidad(entrada) is None
assert condiciones.vertices_inalcanzables(entrada) == ("C",)
```

`vertices_inalcanzables` devuelve una tupla en el orden de los vértices del grafo
y respeta la dirección de cada conexión. Es información para presentar al
usuario, no un rechazo de Dijkstra; si los parámetros son inválidos, la consulta
lanza `AlgoritmoNoAplicableError`. No calcula distancias ni una ruta mínima.

Las implementaciones de algoritmos pueden pasar sus condiciones al constructor
de `Algoritmo`, por ejemplo mediante `super().__init__(CondicionesCPM())`, y
definir `_resolver`. `es_aplicable`, `motivo_inaplicabilidad` y `ejecutar` usan
las mismas condiciones. Una consulta previa exitosa no evita la nueva
comprobación de `ejecutar`, que lanza `AlgoritmoNoAplicableError(motivo)` antes
de resolver si la entrada no aplica. Si no se proporcionan condiciones ni se
define `_motivo_inaplicabilidad`, se rechaza la ejecución.

El cálculo de las soluciones y sus pasos corresponde al issue #6; este cambio
implementa sus comprobaciones previas. El código existente ya usa actividades
en vértices; no había resolutores CPM/PERT anteriores que migrar en esta rama.
Las pruebas usan casos representativos y los ejemplos CSV del repositorio.
Las redes exactas de la bibliografía se incorporarán cuando se disponga del
material, según lo acordado para esta implementación.
