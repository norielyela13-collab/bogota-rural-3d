# -*- coding: utf-8 -*-
"""
Revision rapida de los datos de entrada antes de procesarlos.

Cuenta cuantas geometrias trae la capa del POT, de que tipo son y que codigos
aparecen en el raster de categorias. Es el paso que evita construir un modelo
sobre una capa vacia o mal recortada.

Uso:
    py scripts/inspeccionar_datos.py
"""
import collections
import io
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
base = BASE / "datos_reales"

with io.open(base / "clasificacionsuelo_wgs84.geojson", "r", encoding="utf-8") as f:
    gj = json.load(f)

print("features:", len(gj["features"]))
for ft in gj["features"]:
    p = ft["properties"]
    g = ft.get("geometry")
    if g is None:
        print(p.get("OBJECTID"), "SIN GEOMETRIA")
        continue
    if g["type"] == "Polygon":
        nparts = 1
        nrings = len(g["coordinates"])
    elif g["type"] == "MultiPolygon":
        nparts = len(g["coordinates"])
        nrings = sum(len(poly) for poly in g["coordinates"])
    else:
        nparts = -1
        nrings = -1
    print("OBJECTID=%s CLASE_SUELO=%s CODIGO=%s geom=%s parts=%s rings=%s" % (
        p.get("OBJECTID"), p.get("CLASE_SUELO"), p.get("CODIGO_ID"),
        g["type"], nparts, nrings))

# Contar valores del raster ASCII de categorias
with io.open(base / "categorias_rural_v2.asc", "r", encoding="utf-8") as f:
    lines = f.read().splitlines()
print("HEADER:", lines[:6])
vals = collections.Counter()
for ln in lines[6:]:
    for tok in ln.split():
        vals[int(float(tok))] += 1
print("VALORES:", sorted(vals.items()))
