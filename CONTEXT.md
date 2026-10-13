# Grafos de red

Vocabulario común para los grafos que cargará la aplicación y utilizarán los algoritmos de redes.

## Lenguaje

**Grafo**:
Conjunto de vértices y aristas sobre el que se puede evaluar la aplicación de un algoritmo de redes. Puede contener aristas dirigidas y no dirigidas, incluso en un mismo grafo.

**Vértice**:
Elemento del grafo identificado por un valor alfanumérico. Un vértice aislado no forma parte de los grafos admitidos.

**Arista**:
Conexión entre dos vértices con un peso real finito que puede ser dirigida o no dirigida. Una arista no puede unir un vértice consigo mismo.

**Aristas paralelas**:
Aristas individuales que conectan el mismo par de vértices. Pueden compartir dirección y peso sin convertirse en una sola arista.

**Peso**:
Valor numérico real y finito asociado a una arista; puede ser positivo, negativo o cero.

**Entrada de algoritmo**:
Grafo y parámetros tipados propios del algoritmo que se utilizarán en una ejecución.

**Condiciones de aplicación**:
Requisitos específicos del algoritmo que se verifican antes de resolver una entrada.

**Paso de ejecución**:
Decisión ordenada con descripción, referencias a vértices y aristas destacados, y un detalle propio del algoritmo.

**Resultado de algoritmo**:
Solución tipada propia del algoritmo y secuencia completa e inmutable de pasos. La solución contiene las métricas que correspondan, como el peso total.

## Decisiones acordadas

| Decisión | Referencia en el código |
| --- | --- |
| El grafo es la entrada común, independiente de los algoritmos. La dirección se define en cada arista; un mismo grafo puede combinar aristas dirigidas y no dirigidas. | [`Grafo`](./arboles_de_red/grafo.py#L56), [`Arista`](./arboles_de_red/grafo.py#L17), [API pública](./arboles_de_red/__init__.py) |
| Los vértices tienen identificadores alfanuméricos únicos. No se admiten vértices aislados ni lazos. | [Validación de vértices y lazos](./arboles_de_red/grafo.py#L9), [validación del grafo](./arboles_de_red/grafo.py#L66) |
| Se conservan las aristas paralelas como entidades individuales, incluso si sus extremos, dirección y peso coinciden. Cada una tiene un identificador entero único dentro del grafo. Flujo Máximo podrá usar ambas; la selección de aristas para una solución corresponde al algoritmo. | [`Arista`](./arboles_de_red/grafo.py#L17), [unicidad en `Grafo`](./arboles_de_red/grafo.py#L81), [prueba de paralelas](./tests/test_grafo.py#L20) |
| Todas las aristas tienen peso. Los enteros y reales finitos se normalizan a `float`, por lo que `8` y `8.0` representan el mismo peso. Se aceptan valores negativos y cero; se rechazan texto, `NaN` e infinitos. | [Validación del peso](./arboles_de_red/grafo.py#L39), [pruebas de pesos](./tests/test_grafo.py#L28) |
| El modelo es inmutable. Cargar otro CSV dará lugar a otro `Grafo`, no a una modificación del existente. | [`dataclass` inmutables y conversión a tuplas](./arboles_de_red/grafo.py#L16), [prueba de inmutabilidad](./tests/test_grafo.py#L72) |
| Un grafo puede tener componentes desconectados. Cada algoritmo verificará sus propias condiciones de aplicación antes de ejecutarse, según el [issue #3](https://github.com/camilamercad/arboles-de-red/issues/3). | [`Grafo`](./arboles_de_red/grafo.py#L56), [prueba de desconexión](./tests/test_grafo.py#L48) |
| El modelo puede representar un grafo vacío. La validación del CSV deberá rechazarlo cuando se implementen los [issues #1](https://github.com/camilamercad/arboles-de-red/issues/1) y [#2](https://github.com/camilamercad/arboles-de-red/issues/2). | [Prueba del grafo vacío](./tests/test_grafo.py#L86); validación CSV pendiente |
| La versión mínima es Python 3.14. Pueden incorporarse dependencias externas, pero la lógica de los algoritmos se implementará en el proyecto. Este modelo utiliza la biblioteca estándar. | [Configuración del proyecto](./pyproject.toml#L5), [modelo](./arboles_de_red/grafo.py) |
| Todos los algoritmos comparten una clase base genérica y reciben `Entrada` con `Grafo` y parámetros propios tipados. También son tipados la solución y el detalle de los pasos. | [`Algoritmo` y `Entrada`](./arboles_de_red/algoritmo.py), [ejemplo de implementación](./tests/test_algoritmo.py) |
| `es_aplicable` devuelve solamente `bool`. `ejecutar` verifica nuevamente las condiciones antes de resolver y, si falla, lanza `AlgoritmoNoAplicableError` con el motivo. Cada algoritmo define sus condiciones y resolución. | [Comprobación y ejecución](./arboles_de_red/algoritmo.py), [pruebas de rechazo](./tests/test_algoritmo.py) |
| El resultado contiene la solución propia del algoritmo y una secuencia completa e inmutable de pasos. Cada paso lleva número, descripción, identificadores de vértices y aristas destacados, y detalle tipado propio. | [`Resultado` y `Paso`](./arboles_de_red/algoritmo.py), [pruebas de inmutabilidad](./tests/test_algoritmo.py) |
| Los conteos de vértices y aristas salen del `Grafo`. Las métricas como peso total se exponen, cuando corresponda, desde la solución tipada del algoritmo. | [`Grafo`](./arboles_de_red/grafo.py), [solución del ejemplo](./tests/test_algoritmo.py) |
| Los seis algoritmos previstos se implementarán en sus issues. El contrato se verifica con una implementación mínima dentro de las pruebas. | [Ejemplo y pruebas](./tests/test_algoritmo.py), [issue #15](https://github.com/camilamercad/arboles-de-red/issues/15) |

Estas decisiones concretan los [issues #14](https://github.com/camilamercad/arboles-de-red/issues/14) y [#15](https://github.com/camilamercad/arboles-de-red/issues/15). Los seis algoritmos y el lector de CSV todavía no están implementados; sus filas indican el contrato que deberán respetar.
