# -*- coding: utf-8 -*-
"""
Calcula el area real de cada categoria del POT y resume el DEM.

Como se calcula el area: cada celda del raster mide lo mismo en grados, pero
no en metros (la longitud se acorta al alejarse del ecuador). Por eso se
convierte el tamano de celda a metros con la latitud del centro del recorte y
se multiplica por el numero de celdas de cada categoria.

Uso:
    py scripts/preparar_leyenda.py

Entrada:  datos_reales/categorias_rural_v2.asc
          datos_reales/leyenda_base.json  (codigo -> categoria / subcategoria)
Salida:   datos_reales/leyenda_categorias.json
"""
import collections
import io
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
base = BASE / "datos_reales"

with io.open(base / "leyenda_base.json", "r", encoding="utf-8") as f:
    leyenda = {int(k): v for k, v in json.load(f).items()}

with io.open(base / "categorias_rural_v2.asc", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()

header = {}
for ln in lines[:6]:
    k, v = ln.split()
    header[k.lower()] = float(v)

ncols = int(header["ncols"])
nrows = int(header["nrows"])
cs = header["cellsize"]
yll = header["yllcorner"]
lat0 = yll + nrows * cs / 2.0
dx = cs * 111320.0 * math.cos(math.radians(lat0))
dy = cs * 110574.0
area_celda_km2 = (dx * dy) / 1e6

conteo = collections.Counter()
for ln in lines[6:]:
    for tok in ln.split():
        conteo[int(float(tok))] += 1

total = sum(v for k, v in conteo.items() if k > 0)
print("Celdas rurales:", total, " Area aprox: %.1f km2" % (total * area_celda_km2))
for cid in sorted(leyenda):
    n = conteo.get(cid, 0)
    leyenda[cid]["celdas"] = n
    leyenda[cid]["area_km2"] = round(n * area_celda_km2, 1)
    print("CAT_ID=%2d  %-22s  %-60s  %6d celdas  %7.1f km2" % (
        cid, leyenda[cid]["categoria"], (leyenda[cid]["subcategoria"] or "")[:60],
        n, n * area_celda_km2))

with io.open(base / "leyenda_categorias.json", "w", encoding="utf-8") as f:
    json.dump(leyenda, f, ensure_ascii=False, indent=2)

# Estadisticas del DEM
with io.open(base / "dem_rural.asc", "r", encoding="utf-8") as f:
    dlines = f.read().splitlines()

dvals = []
for ln in dlines[6:]:
    for tok in ln.split():
        v = float(tok)
        if v > -1000:
            dvals.append(v)
dvals.sort()
print("DEM celdas validas:", len(dvals))
print("DEM min/mediana/media/max: %.0f / %.0f / %.0f / %.0f m" % (
    dvals[0], dvals[len(dvals) // 2], sum(dvals) / len(dvals), dvals[-1]))
