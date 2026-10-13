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
