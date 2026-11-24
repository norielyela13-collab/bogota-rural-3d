# -*- coding: utf-8 -*-
"""
Mide el terreno antes de modelarlo: extension real y perfil de alturas.

El DEM viene en grados (WGS84). Para pasar a kilometros se usan dos
constantes: 111.320 m por grado de longitud en el ecuador (corregido por el
coseno de la latitud) y 110.574 m por grado de latitud.

Uso:
    py scripts/analizar_terreno.py
"""
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
base = BASE / "datos_reales"

with open(base / "dem_rural.asc", "r", encoding="utf-8") as f:
    cab = {}
    for _ in range(6):
        k, v = f.readline().split()
        cab[k.lower()] = float(v)
    ncols = int(cab["ncols"])
    nrows = int(cab["nrows"])
    xll = cab["xllcorner"]
    yll = cab["yllcorner"]
    cs = cab["cellsize"]
    datos = [[float(x) for x in f.readline().split()] for _ in range(nrows)]

lon0 = xll + ncols * cs / 2.0
lat0 = yll + nrows * cs / 2.0
MX = 111320.0 * math.cos(math.radians(lat0))
MY = 110574.0


def xy(col, fila):
    lon = xll + (col + 0.5) * cs
    lat = yll + (nrows - fila - 0.5) * cs
    return (lon - lon0) * MX / 1000.0, (lat - lat0) * MY / 1000.0


validos = []
for fila in range(nrows):
    for col in range(ncols):
        if datos[fila][col] > -1000:
            x, y = xy(col, fila)
            validos.append((x, y, datos[fila][col]))

xs = [v[0] for v in validos]
ys = [v[1] for v in validos]
print("BBox terreno valido: x %.1f a %.1f km | y %.1f a %.1f km" % (min(xs), max(xs), min(ys), max(ys)))

print("\nPerfil por franjas de y:")
for yc in (55, 45, 35, 25, 15, 5, -5, -15, -25, -35, -45, -55):
    franja = [(x, y, z) for x, y, z in validos if abs(y - yc) <= 3]
    if franja:
        fx = [p[0] for p in franja]
        fz = [p[2] for p in franja]
        print("y=%+3d km: x %.1f a %.1f (centro %.1f), z %.0f-%.0f m, %d celdas" % (
            yc, min(fx), max(fx), (min(fx) + max(fx)) / 2, min(fz), max(fz), len(franja)))
    else:
        print("y=%+3d km: sin terreno" % yc)
