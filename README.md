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

El paquete `arboles_de_red` expone `Grafo` y `Arista` para que los
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

# Con una implementación concreta del visualizador y uno de los algoritmos del #6:
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
Un valor no nulo demasiado pequeño para representarse se rechaza con su línea
y columna, en lugar de convertirlo silenciosamente en cero. El modelo aplica
la misma restricción a los pesos recibidos directamente.

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

El cálculo de las soluciones y sus pasos se incorpora en el issue #6, descrito
más abajo. El código usa actividades en vértices. Las pruebas de resolución
incluyen los casos del material de la cátedra, redes pequeñas contrastadas con
enumeración exhaustiva y ejecuciones de los seis algoritmos con 200 vértices.

### Registro de algoritmos (issue #17)

`RegistroAlgoritmos` permite incorporar implementaciones sin modificar la
selección, la consulta de condiciones ni la ejecución. Cada
`RegistroAlgoritmo[Parametros, Solucion, Detalle]` reúne un identificador único,
un nombre, una fábrica de `Algoritmo` y una función que prepara sus parámetros
desde la carga original y las opciones de ejecución. La fábrica debe devolver
una instancia nueva en cada llamada. Los contratos del registro y de
`EjecucionPreparada` son clases base abstractas, como las demás interfaces del
proyecto.

`crear_registro_catedra` conecta los seis algoritmos de la consigna mediante
fábricas recibidas por nombre: `prim`, `kruskal`, `dijkstra`, `flujo_maximo`,
`cpm` y `pert`. Sus identificadores de selección son los mismos. La composición
de estos registros está en [`catedra.py`](arboles_de_red/catedra.py); el mecanismo
general está en [`registro.py`](arboles_de_red/registro.py) y no contiene casos
por nombre de algoritmo.

| Registro | Opciones de ejecución | Parámetros preparados |
| --- | --- | --- |
| `prim`, `kruskal` | Ninguna. | `None`, conservando el grafo cargado. |
| `dijkstra` | `origen` obligatorio y `destino` opcional. | `ParametrosDijkstra`. |
| `flujo_maximo` | `fuente` y `sumidero` obligatorios. | `ParametrosFlujoMaximo`. |
| `cpm` | Ninguna; reutiliza la carga CPM. | `ParametrosCPM` con sus duraciones por actividad. |
| `pert` | Ninguna; reutiliza la carga PERT. | `ParametrosPERT` con sus tres estimaciones por actividad. |

Las opciones son un mapa de texto, por ejemplo `{"origen": "A", "destino": "C"}`.
`ErrorPreparacionEntrada` informa terminales faltantes o vacíos, opciones no
admitidas o ausencia de los datos de actividades requeridos. No se inventan
duraciones ni se convierten estimaciones PERT en duraciones CPM. La existencia
de los terminales y las demás condiciones del algoritmo se consultan después
mediante el contrato del issue #3.

Con las fábricas de las implementaciones concretas disponibles, la aplicación
configura el catálogo una sola vez:

```python
from arboles_de_red import crear_registro_catedra

# crear_prim, crear_kruskal, etc. son fábricas de las implementaciones del #6.
registro = crear_registro_catedra(
    prim=crear_prim,
    kruskal=crear_kruskal,
    dijkstra=crear_dijkstra,
    flujo_maximo=crear_flujo_maximo,
    cpm=crear_cpm,
    pert=crear_pert,
)
```

Después utiliza el mismo recorrido para cualquier identificador, una `carga`
obtenida mediante `preparar_entrada` del CSV y sus `opciones` de ejecución:

```python
opcion = registro.seleccionar(identificador)
ejecucion = opcion.preparar(carga, opciones)
motivo = ejecucion.motivo_inaplicabilidad()
if motivo is None:
    resultado = ejecucion.ejecutar()
```

`ejecucion.entrada` conserva el grafo original y contiene los parámetros tipados
del algoritmo elegido. `EjecucionPreparada` expone `es_aplicable()`,
`motivo_inaplicabilidad()` y `ejecutar()`; delega en la implementación registrada
y conserva su solución y sus pasos sin transformarlos. `ejecutar()` vuelve a
comprobar las condiciones y propaga `AlgoritmoNoAplicableError` cuando no aplica.
Cada consulta y cada ejecución obtiene una instancia mediante la fábrica, sin
compartir el estado mutable de una resolución anterior.

`registro.identificadores` devuelve una tupla en orden de incorporación.
`seleccionar` lanza `KeyError` si el identificador no existe. `registrar` rechaza
un identificador repetido con `ValueError`, sin sustituir su registro anterior.
Las opciones registradas y las ejecuciones preparadas son inmutables; ampliar
el catálogo conserva las selecciones, entradas y resultados anteriores. Para
incorporar otra implementación se agrega un `RegistroAlgoritmo` con su fábrica
y preparador; no se modifica el mecanismo general.

Un registro genérico usado directamente conserva también los tipos estáticos
de solución y detalle. Al seleccionar por un identificador dinámico, el catálogo
expone esos tipos como `object`, manteniendo intactos los objetos tipados que
devuelve cada implementación. No utiliza `Any` ni conversiones de soluciones.

El registro permite suministrar fábricas propias. `crear_registro_predeterminado()`
lo configura con las seis implementaciones reales incorporadas en el #6.
Las pruebas del registro conservan implementaciones mínimas para verificar
su extensibilidad; las pruebas de selección e integración ejecutan los resolutores reales.

### Resolución de los algoritmos (issue #6)

Los seis algoritmos implementan `Algoritmo`, reutilizan las condiciones del #3
y devuelven `Resultado` con solución tipada y pasos numerados desde uno.
La lógica se desarrolla en el proyecto, sin librerías de grafos ni resolutores
externos. Solo se utiliza la biblioteca estándar de Python para estructuras
básicas, tipos de datos y aritmética.

| Clase | Solución y decisiones registradas |
| --- | --- |
| `Prim` | `SolucionArbolExpansion`: aristas originales elegidas y `peso_total`. Crece desde el primer vértice cargado y selecciona la arista mínima de la frontera. |
| `Kruskal` | La misma solución de árbol. Ordena aristas, une componentes con una estructura propia y registra tanto aceptaciones como rechazos por ciclo. |
| `Dijkstra` | `SolucionDijkstra`: `ruta`, `aristas_ruta`, `costo`, mapas de distancias y predecesores e identificadores `inalcanzables`. Registra fijaciones y relajaciones de distancias. |
| `FordFulkerson` | `SolucionFlujoMaximo`: `flujo_maximo`, `flujo_por_arco` y corte mínimo. Busca caminos residuales en anchura mediante una implementación propia y registra cada camino, cuello de botella y actualización directa e inversa. |
| `CPM` | `SolucionCPM`: mapa `actividades` con IC, TC, IL, TL y holgura, `duracion_proyecto`, orden topológico y `rutas_criticas`. Registra la pasada hacia adelante y la pasada hacia atrás. |
| `PERT` | `SolucionPERT`: estimaciones originales, `tiempos_esperados`, `varianzas`, planificación AON y `duracion_esperada`. Calcula `(a + 4m + b) / 6` y `((b - a) / 6)²` por actividad y realiza las dos pasadas sobre los tiempos esperados. |

Las aristas paralelas conservan sus identificadores en las soluciones y los
pasos. Los empates de Prim/Kruskal se resuelven por identificador de arista;
Dijkstra conserva la primera ruta de igual costo y fija primero el vértice que
aparece antes en la carga. Ford–Fulkerson visita los arcos residuales en orden
de incorporación. No se modifica el grafo ni se guarda estado de una resolución
en la siguiente.

```python
from arboles_de_red import CPM, LectorTexto, ProcesadorCPMCSV

entrada = ProcesadorCPMCSV().preparar_entrada(LectorTexto().leer("ejemplos/cpm.csv"))
resultado = CPM().ejecutar(entrada)
assert resultado.solucion.duracion_proyecto == 9.5
assert resultado.solucion.actividades["C"].holgura == 0
assert tuple(resultado.solucion.rutas_criticas) == (("A", "B", "C"),)
```

Dijkstra admite `destino=None`: calcula todas las distancias desde el origen y
permite consultar `solucion.ruta_hasta(identificador)`. Si se proporciona un
destino inalcanzable, `ruta`, `aristas_ruta` y `costo` son `None`; su distancia
es infinito y su identificador aparece en `inalcanzables`. Una consulta del
origen a sí mismo devuelve `(origen,)`, ninguna arista y costo cero. El cálculo
se completa para todos los vértices alcanzables aunque se indique un destino.

En CPM/PERT las actividades independientes terminan dentro de la duración
global del proyecto. Las precedencias paralelas no duplican rutas de actividades.
`rutas_criticas.cantidad` cuenta todas las rutas y `rutas_criticas.sucesoras`
conserva su red compacta. Se pueden recorrer con `for ruta in rutas_criticas`;
su cantidad puede ser exponencial y enumerarlas todas tiene ese costo. Para
una vista previa acotada, puede usarse `itertools.islice(rutas_criticas, 10)`.

En PERT, `solucion.variabilidad_rutas()` recorre a demanda objetos
`VariabilidadRutaPERT`, con actividades, duración esperada, suma de varianzas
y desviación estándar de **cada** ruta crítica. Esta suma supone actividades
independientes, como el modelo PERT del material. Si varias rutas empatan en
duración, se conservan todas con su variabilidad: no se elige una ni se presenta
su varianza como la varianza exacta del máximo aleatorio entre rutas.
La consulta contra una fecha objetivo corresponde al #9 y el crashing de CPM
queda fuera de #6.

Las soluciones y detalles concretos son inmutables; los mapas copian sus datos.
Los controles del #12 podrán reproducir `Resultado.pasos` después del cálculo;
estos resolutores entregan la secuencia completa y no ejecutan una animación.
La aritmética interna de Dijkstra, Ford–Fulkerson y de las dos pasadas usa
racionales a partir de la representación decimal normalizada de los datos.
Esto evita falsos empates en distancias, residuos negativos artificiales y
falsas holguras por sumas decimales. Los resultados públicos se expresan como
`float`. Si un resultado o un dato de los pasos desborda ese rango, o un valor
no nulo se convertiría en cero, se informa `ErrorCalculoNumerico`. Un candidato
descartado de Dijkstra no necesita convertirse ni puede provocar ese error.
La suma de varianzas de una ruta PERT se calcula a demanda; un desborde de esa
suma se informa al recorrer `variabilidad_rutas()`.

### Selección desde la aplicación (issue #5)

`SelectorAlgoritmos` es la API para la futura interfaz gráfica. Su catálogo
predeterminado incluye Prim, Kruskal, Dijkstra, Flujo Máximo, CPM y PERT.
No requiere una tecnología de interfaz ni incorpora una consola.

```python
from arboles_de_red import ProcesadorConexionesCSV, SelectorAlgoritmos

carga = ProcesadorConexionesCSV().preparar_entrada(
    "origen,destino,peso\nA,B,2\nB,C,3\nA,C,8\n"
)
selector = SelectorAlgoritmos()
opciones_disponibles = selector.opciones  # Tupla de OpcionAlgoritmo: identificador y nombre.
seleccion = selector.seleccionar("dijkstra", carga, {"origen": "A", "destino": "C"})
if seleccion.puede_ejecutarse:
    resultado = seleccion.ejecutar()
    assert resultado.solucion.ruta == ("A", "B", "C")
    assert resultado.solucion.costo == 5
else:
    motivo_para_mostrar = seleccion.motivo
```

La selección prepara los parámetros y consulta las condiciones del #3 sin
resolver. `SeleccionAlgoritmo` conserva `identificador`, `nombre`, `entrada`,
`ejecucion`, `motivo` y `puede_ejecutarse`. Para CPM/PERT se reutilizan los datos
de la carga; para Dijkstra se aportan origen y destino opcional; para Flujo
Máximo, fuente y sumidero obligatorios. Los parámetros y sus errores conservan
el contrato documentado en el registro del #17.

Una entrada incompatible devuelve una selección con `puede_ejecutarse=False`
y su motivo. No se sustituye por otro algoritmo. Si se intenta ejecutar, se
verifican nuevamente las condiciones y se lanza `AlgoritmoNoAplicableError`.
Los parámetros ausentes o no admitidos producen `ErrorPreparacionEntrada`;
un identificador desconocido produce `KeyError`.

Se puede inyectar un `RegistroAlgoritmos` en `SelectorAlgoritmos(registro)`.
Así, nuevas opciones que cumplan el contrato aparecen en el catálogo sin
modificar el selector. La API conserva las soluciones y pasos propios de
cada algoritmo para que la visualización de los issues #7, #8 y #9 los utilice.

### Verificación del núcleo

El alcance, los oráculos independientes, las regresiones y las limitaciones
de las pruebas se describen en [PRUEBAS.md](PRUEBAS.md). La suite usa `unittest`
y la biblioteca estándar; no utiliza librerías de algoritmos para comprobar
los resultados. Desde la raíz del repositorio:

```sh
py -3.14 -m unittest discover -s tests -v
```

Para guardar el log completo, contar subcasos y registrar los hashes de los
archivos efectivamente probados:

```sh
py -3.14 scripts/ejecutar_pruebas.py --salida informes/pruebas-core
```

La medición opcional de líneas y ramas requiere una herramienta de desarrollo:

```sh
py -3.14 -m pip install coverage==7.17.0
py -3.14 scripts/ejecutar_pruebas.py --cobertura --salida informes/pruebas-core
```

`coverage` no es una dependencia de ejecución del programa. La evidencia de la
ejecución se guarda en `resultado.json`, `ejecucion.txt`, `cobertura.json` y
`cobertura.txt` dentro de la carpeta de salida. La enumeración exhaustiva se
limita a los dominios finitos definidos en el informe; no prueba todos los
grafos posibles.
