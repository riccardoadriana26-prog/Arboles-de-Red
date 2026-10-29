"""Oráculos de prueba por enumeración: no llaman a los resolutores del proyecto."""

from fractions import Fraction
from itertools import combinations


def racional(valor):
    return Fraction(str(valor))


def arbol_minimo(grafo):
    costos = []
    for seleccion in combinations(grafo.aristas, len(grafo.vertices) - 1):
        vistos = {grafo.vertices[0]}
        for _ in grafo.vertices:
            for a in seleccion:
                if a.origen in vistos or a.destino in vistos:
                    vistos.update((a.origen, a.destino))
        if len(vistos) == len(grafo.vertices):
            costos.append(sum((racional(a.peso) for a in seleccion), Fraction(0)))
    return min(costos) if costos else None


def caminos_simples(grafo, origen):
    distancias = dict.fromkeys(grafo.vertices)
    pila = [(origen, (origen,), Fraction(0))]
    while pila:
        actual, ruta, costo = pila.pop()
        if distancias[actual] is None or costo < distancias[actual]:
            distancias[actual] = costo
        for a in grafo.aristas:
            destino = a.destino if a.origen == actual else a.origen if not a.dirigida and a.destino == actual else None
            if destino is not None and destino not in ruta:
                pila.append((destino, ruta + (destino,), costo + racional(a.peso)))
    return distancias


def corte_minimo(grafo, fuente, sumidero):
    interiores = [v for v in grafo.vertices if v not in (fuente, sumidero)]
    capacidades = []
    for mascara in range(1 << len(interiores)):
        lado = {fuente} | {v for i, v in enumerate(interiores) if mascara & (1 << i)}
        capacidades.append(sum((racional(a.peso) for a in grafo.aristas
                                if a.origen in lado and a.destino not in lado), Fraction(0)))
    return min(capacidades)


def planificacion(grafo, duraciones):
    """Obtiene cada tiempo a partir de todos los caminos completos de una AON pequeña."""
    entradas = {v: set() for v in grafo.vertices}
    salidas = {v: set() for v in grafo.vertices}
    for a in grafo.aristas:
        entradas[a.destino].add(a.origen)
        salidas[a.origen].add(a.destino)
    pila = [(v,) for v in grafo.vertices if not entradas[v]]
    rutas = []
    while pila:
        ruta = pila.pop()
        if not salidas[ruta[-1]]:
            rutas.append(ruta)
        for v in salidas[ruta[-1]]:
            pila.append(ruta + (v,))
    costos = {ruta: sum((duraciones[v] for v in ruta), Fraction(0)) for ruta in rutas}
    duracion = max(costos.values())
    criticas = {ruta for ruta, costo in costos.items() if costo == duracion}
    tiempos = {}
    for v in grafo.vertices:
        prefijos = [sum((duraciones[u] for u in ruta[:ruta.index(v)]), Fraction(0)) for ruta in rutas if v in ruta]
        sufijos = [sum((duraciones[u] for u in ruta[ruta.index(v):]), Fraction(0)) for ruta in rutas if v in ruta]
        ic, il = max(prefijos), duracion - max(sufijos)
        tiempos[v] = (ic, ic + duraciones[v], il, il + duraciones[v], il - ic)
    return duracion, criticas, tiempos
