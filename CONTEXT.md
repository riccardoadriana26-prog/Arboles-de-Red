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

Estas decisiones concretan el [issue #14](https://github.com/camilamercad/arboles-de-red/issues/14). Los algoritmos y el lector de CSV todavía no están implementados; sus filas indican el contrato que deberán respetar.
