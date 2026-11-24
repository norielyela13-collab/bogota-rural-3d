# -*- coding: utf-8 -*-
"""
Suaviza el DEM SRTM con un filtro de mediana 5x5.

Para que sirve: el SRTM trae picos y pocitos de una sola celda (ruido del
radar). Un promedio los reparte por todo el terreno; la mediana los elimina
sin inventar alturas, porque toma el valor central de los 25 vecinos.

Uso:
    py scripts/filtrar_dem.py

Entrada:  datos_reales/dem_rural.asc
Salida:   datos_reales/dem_rural_filtrado.asc
"""
import statistics
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATOS = BASE / "datos_reales"
entrada = DATOS / "dem_rural.asc"
salida = DATOS / "dem_rural_filtrado.asc"

with open(entrada, "r", encoding="utf-8") as f:
    cab = {}
    for _ in range(6):
        k, v = f.readline().split()
        cab[k.lower()] = float(v)
    ncols = int(cab["ncols"])
    nrows = int(cab["nrows"])
    datos = [[float(x) for x in f.readline().split()] for _ in range(nrows)]

nuevo = [fila[:] for fila in datos]
for r in range(nrows):
    for c in range(ncols):
        if datos[r][c] <= -1000:
            continue
        vecinos = []
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                rr, cc = r + dr, c + dc
                if 0 <= rr < nrows and 0 <= cc < ncols and datos[rr][cc] > -1000:
                    vecinos.append(datos[rr][cc])
        if vecinos:
            nuevo[r][c] = statistics.median(vecinos)

validos = [v for fila in nuevo for v in fila if v > -1000]
print("Minimo/maximo tras suavizado: %.0f / %.0f m" % (min(validos), max(validos)))

with open(salida, "w", encoding="utf-8") as f:
    f.write("ncols         %d\n" % ncols)
    f.write("nrows         %d\n" % nrows)
    f.write("xllcorner     %.12f\n" % cab["xllcorner"])
    f.write("yllcorner     %.12f\n" % cab["yllcorner"])
    f.write("cellsize      %.12f\n" % cab["cellsize"])
    f.write("NODATA_value  %g\n" % cab.get("nodata_value", -9999))
    for fila in nuevo:
        f.write(" ".join("%.0f" % v for v in fila) + "\n")
print("Guardado:", salida)
