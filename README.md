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
Los pesos se almacenan como `float` finitos; se aceptan valores negativos y
cero. La dirección se define por arista, así que un grafo puede combinar
aristas dirigidas y no dirigidas.

El modelo es inmutable y rechaza lazos, vértices aislados, identificadores de
vértice no alfanuméricos, extremos inexistentes e identificadores repetidos.
Acepta componentes desconectados: cada algoritmo decidirá si puede aplicarse
según el issue #3. Un grafo vacío es representable en el modelo; la validación
del CSV lo rechazará al implementar los issues #1 y #2.

Para ejecutar las pruebas:

```sh
py -3.14 -m unittest discover -s tests -v
```

### Contrato común de algoritmos (issue #15)

Cada algoritmo hereda de `Algoritmo[Parametros, Solucion, Detalle]` y recibe una
`Entrada(grafo, parametros)`. Los parámetros, la solución y el detalle de cada
paso tienen tipos propios de ese algoritmo. Una implementación mínima se
encuentra en [`tests/test_algoritmo.py`](tests/test_algoritmo.py).

La aplicación puede llamar `es_aplicable(entrada)`, que devuelve `bool`, antes
de iniciar la ejecución. `ejecutar(entrada)` vuelve a comprobar las condiciones:
si no se cumplen, lanza `AlgoritmoNoAplicableError` con el motivo; si se cumplen,
devuelve `Resultado(solucion, pasos)`. Cada implementación define
`_motivo_inaplicabilidad` y `_resolver`, sin cambiar el mecanismo público.

`Resultado.pasos` es una secuencia completa e inmutable en orden de ejecución.
Cada `Paso` contiene un número, una descripción, los identificadores de
vértices y aristas para destacar, y un detalle tipado propio del algoritmo.
La interfaz puede mostrar los conteos a partir de `Entrada.grafo`; las métricas
que correspondan, como el peso total, pertenecen a `Resultado.solucion`.
