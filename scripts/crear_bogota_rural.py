# -*- coding: utf-8 -*-
"""
Taller: modelo 3D del SUELO RURAL DE BOGOTA con datos reales.
Fuentes reales:
  - Elevacion: SRTM 1 arc-sec (NASA/USGS) via AWS Terrain Tiles.
  - Limites y categorias: Datos Abiertos Bogota - POT Decreto 555 de 2021.
Procesado con GDAL de QGIS en modo headless.
Ejecutar:
  blender --background --factory-startup --python crear_bogota_rural.py
"""

import bpy
import json
import math
import os
from mathutils import Vector

BASE = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(BASE, "datos_reales")
RENDERS = os.path.join(BASE, "renders_rural")
os.makedirs(RENDERS, exist_ok=True)

EXAGERACION = 10.0  # exageracion vertical para que se aprecie el relieve

# ---------------------------------------------------------------------------
# 1. Leer los datos reales (ASCII Grid exportado por GDAL)
# ---------------------------------------------------------------------------
def leer_asc(ruta):
    with open(ruta, "r", encoding="utf-8") as f:
        cab = {}
        for _ in range(6):
            k, v = f.readline().split()
            cab[k.lower()] = float(v)
        ncols = int(cab["ncols"])
        nrows = int(cab["nrows"])
        xll = cab["xllcorner"]
        yll = cab["yllcorner"]
        cs = cab["cellsize"]
        nodata = cab.get("nodata_value", -9999.0)
        datos = []
        for _ in range(nrows):
            datos.append([float(x) for x in f.readline().split()])
    return {
        "ncols": ncols, "nrows": nrows, "xll": xll, "yll": yll,
        "cs": cs, "nodata": nodata, "datos": datos,
    }

dem = leer_asc(os.path.join(DATOS, "dem_rural_filtrado.asc"))
cat = leer_asc(os.path.join(DATOS, "categorias_rural_v2.asc"))

ncols, nrows = dem["ncols"], dem["nrows"]
xll, yll, cs = dem["xll"], dem["yll"], dem["cs"]
lon0 = xll + ncols * cs / 2.0
lat0 = yll + nrows * cs / 2.0
MX = 111320.0 * math.cos(math.radians(lat0))
MY = 110574.0

# Limpiar escena
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for mat in list(bpy.data.materials):
    bpy.data.materials.remove(mat)

escena = bpy.context.scene

# ---------------------------------------------------------------------------
# 2. Colores
# ---------------------------------------------------------------------------
def interpolar_color(stops, valor):
    if valor <= stops[0][0]:
        return stops[0][1]
    if valor >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        a, ca = stops[i]
        b, cb = stops[i + 1]
        if a <= valor <= b:
            t = (valor - a) / (b - a)
            return tuple(ca[k] + (cb[k] - ca[k]) * t for k in range(3))
    return stops[-1][1]

STOPS_RELIEVE = [
    (1143, (0.10, 0.35, 0.14)),
    (2000, (0.20, 0.48, 0.16)),
    (2600, (0.36, 0.57, 0.18)),
    (3000, (0.62, 0.66, 0.24)),
    (3400, (0.60, 0.52, 0.27)),
    (3700, (0.52, 0.38, 0.25)),
    (3950, (0.72, 0.68, 0.62)),
    (4128, (0.96, 0.96, 0.96)),
]

COLORES_CATEGORIA = {
    1:  (0.86, 0.62, 0.18),
    2:  (0.72, 0.40, 0.72),
    3:  (0.95, 0.55, 0.18),
    4:  (0.90, 0.35, 0.15),
    5:  (0.13, 0.45, 0.25),
    6:  (0.10, 0.58, 0.30),
    7:  (0.18, 0.32, 0.62),
    8:  (0.55, 0.65, 0.18),
    10: (0.80, 0.15, 0.15),
    11: (0.78, 0.78, 0.22),
    12: (0.20, 0.62, 0.65),
    13: (0.55, 0.30, 0.75),
}

zmin = min(v for fila in dem["datos"] for v in fila if v > -1000)
zmax = max(v for fila in dem["datos"] for v in fila if v > -1000)

# ---------------------------------------------------------------------------
# 3. Construir la malla del terreno con los datos reales
# ---------------------------------------------------------------------------
def coord(col, fila):
    lon = xll + (col + 0.5) * cs
    lat = yll + (nrows - fila - 0.5) * cs
    return (lon - lon0) * MX / 1000.0, (lat - lat0) * MY / 1000.0

def altura(fila, col):
    v = dem["datos"][fila][col]
    if v <= -1000:
        return None
    return (v - zmin) / 1000.0 * EXAGERACION

vertices = []
for fila in range(nrows):
    for col in range(ncols):
        x, y = coord(col, fila)
        z = altura(fila, col)
        vertices.append((x, y, z if z is not None else 0.0))

caras = []
for fila in range(nrows - 1):
    for col in range(ncols - 1):
        if (altura(fila, col) is None or altura(fila, col + 1) is None or
                altura(fila + 1, col) is None or altura(fila + 1, col + 1) is None):
            continue
        a = fila * ncols + col
        b = (fila + 1) * ncols + col
        c = (fila + 1) * ncols + (col + 1)
        d = fila * ncols + (col + 1)
        caras.append((a, b, c, d))

print("Vertices: %d  Caras: %d" % (len(vertices), len(caras)))
print("Elevacion real: %d - %d m" % (zmin, zmax))

def crear_material(nombre, color, emision=0.0):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    bsdf = nodos.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.85
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.15
    return mat

def crear_terreno(nombre, capa_color, colores_por_vertice):
    malla = bpy.data.meshes.new(nombre + "_malla")
    malla.from_pydata(vertices, [], caras)
    malla.validate()
    malla.update()

    attr = malla.color_attributes.new(name=capa_color, type="FLOAT_COLOR", domain="POINT")
    for i, col in enumerate(colores_por_vertice):
        attr.data[i].color = (col[0], col[1], col[2], 1.0)

    mat = bpy.data.materials.new(nombre + "_mat")
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    enlaces = mat.node_tree.links
    bsdf = nodos.get("Principled BSDF")
    vc = nodos.new("ShaderNodeVertexColor")
    vc.layer_name = capa_color
    enlaces.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    malla.materials.append(mat)

    obj = bpy.data.objects.new(nombre, malla)
    bpy.context.collection.objects.link(obj)
    return obj

colores_relieve = []
colores_categoria = []
for fila in range(nrows):
    for col in range(ncols):
        z = dem["datos"][fila][col]
        if z <= -1000:
            colores_relieve.append((0.25, 0.25, 0.25))
        else:
            colores_relieve.append(interpolar_color(STOPS_RELIEVE, z))
        cid = int(cat["datos"][fila][col])
        colores_categoria.append(COLORES_CATEGORIA.get(cid, (0.30, 0.30, 0.30)))

terreno_relieve = crear_terreno("Terreno_Relieve_SRTM", "Relieve", colores_relieve)
terreno_cat = crear_terreno("Terreno_Categorias_POT", "Categoria", colores_categoria)

# Base neutra que representa el area urbana (hueco dentro del suelo rural)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -3.5))
base_urbana = bpy.context.object
base_urbana.name = "Base_Area_Urbana"
base_urbana.data.materials.append(crear_material("Base_Urbana", (0.20, 0.21, 0.23)))

# ---------------------------------------------------------------------------
# 4. Limite real del suelo rural (GeoJSON oficial)
# ---------------------------------------------------------------------------
def muestra_altura(lon, lat):
    col = int((lon - xll) / cs)
    fila = int((yll + nrows * cs - lat) / cs)
    for radio in range(0, 4):
        for df in range(-radio, radio + 1):
            for dc in range(-radio, radio + 1):
                f, c = fila + df, col + dc
                if 0 <= f < nrows and 0 <= c < ncols:
                    z = altura(f, c)
                    if z is not None:
                        return z
    return 0.0

mat_limite = crear_material("Limite", (1.0, 0.85, 0.1))
mat_limite.use_nodes = True
bsdf = mat_limite.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.85, 0.1, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 2.0

with open(os.path.join(DATOS, "rural_mask.geojson"), "r", encoding="utf-8") as f:
    mask = json.load(f)

def anillos(geom):
    if geom is None:
        return []
    if geom["type"] == "Polygon":
        return geom["coordinates"]
    if geom["type"] == "MultiPolygon":
        out = []
        for poly in geom["coordinates"]:
            out.extend(poly)
        return out
    return []

n_anillos = 0
for ft in mask["features"]:
    for anillo in anillos(ft.get("geometry")):
        pts = []
        for lon, lat in anillo:
            x = (lon - lon0) * MX / 1000.0
            y = (lat - lat0) * MY / 1000.0
            z = muestra_altura(lon, lat) + 0.18
            pts.append((x, y, z))
        if len(pts) < 2:
            continue
        curva = bpy.data.curves.new("Limite_%d" % n_anillos, type="CURVE")
        curva.dimensions = "3D"
        curva.bevel_depth = 0.10
        curva.bevel_resolution = 2
        spline = curva.splines.new("POLY")
        spline.points.add(len(pts) - 1)
        for i, p in enumerate(pts):
            spline.points[i].co = (p[0], p[1], p[2], 1.0)
        obj = bpy.data.objects.new("Limite_%d" % n_anillos, curva)
        bpy.context.collection.objects.link(obj)
        curva.materials.append(mat_limite)
        n_anillos += 1
print("Anillos del limite rural dibujados:", n_anillos)

# Falda vertical: da grosor al terreno para que se vea como un bloque solido
mat_falda = crear_material("Falda", (0.26, 0.19, 0.13))
verts_falda = []
caras_falda = []
grosor = 1.5
for ft in mask["features"]:
    for anillo in anillos(ft.get("geometry")):
        pts = []
        for lon, lat in anillo:
            x = (lon - lon0) * MX / 1000.0
            y = (lat - lat0) * MY / 1000.0
            z = muestra_altura(lon, lat)
            pts.append((x, y, z))
        if len(pts) < 4:
            continue
        if abs(pts[0][0] - pts[-1][0]) < 1e-6 and abs(pts[0][1] - pts[-1][1]) < 1e-6:
            pts = pts[:-1]
        n = len(pts)
        if n < 3:
            continue
        base = len(verts_falda)
        for (x, y, z) in pts:
            verts_falda.append((x, y, z + 0.18))
        for (x, y, z) in pts:
            verts_falda.append((x, y, z - grosor))
        for i in range(n):
            j = (i + 1) % n
            caras_falda.append((base + i, base + j, base + n + j, base + n + i))

malla_falda = bpy.data.meshes.new("Falda_malla")
malla_falda.from_pydata(verts_falda, [], caras_falda)
malla_falda.validate()
malla_falda.update()
malla_falda.materials.append(mat_falda)
falda = bpy.data.objects.new("Falda_Terreno", malla_falda)
bpy.context.collection.objects.link(falda)
print("Falda: %d vertices, %d caras" % (len(verts_falda), len(caras_falda)))

# ---------------------------------------------------------------------------
# 5. Etiquetas de lugares reales
# ---------------------------------------------------------------------------
mat_texto = crear_material("Texto", (1.0, 1.0, 1.0))
mat_texto.use_nodes = True
bsdf = mat_texto.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Emission Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 1.2

LUGARES = [
    ("SUMAPAZ", 3.870, -74.350),
    ("USME", 4.430, -74.120),
    ("CIUDAD BOLIVAR", 4.540, -74.185),
    ("CERROS ORIENTALES", 4.660, -74.030),
    ("SUBA", 4.750, -74.070),
]

etiquetas = []
for nombre, lat, lon in LUGARES:
    z = muestra_altura(lon, lat)
    x = (lon - lon0) * MX / 1000.0
    y = (lat - lat0) * MY / 1000.0
    bpy.ops.object.text_add(location=(x, y, z + 0.35))
    txt = bpy.context.object
    txt.name = "Lugar_" + nombre.replace(" ", "_")
    txt.data.body = nombre
    txt.data.size = 2.6
    txt.data.extrude = 0.05
    txt.data.align_x = "CENTER"
    txt.data.align_y = "CENTER"
    txt.data.materials.append(mat_texto)
    etiquetas.append(txt)

# ---------------------------------------------------------------------------
# 6. Iluminacion y cielo
# ---------------------------------------------------------------------------
mundo = escena.world
if mundo is None:
    mundo = bpy.data.worlds.new("Mundo")
    escena.world = mundo
mundo.use_nodes = True
fondo = mundo.node_tree.nodes.get("Background")
if fondo:
    fondo.inputs["Color"].default_value = (0.58, 0.72, 0.88, 1.0)
    fondo.inputs["Strength"].default_value = 1.1

bpy.ops.object.light_add(type="SUN", location=(60, -40, 100))
sol = bpy.context.object
sol.name = "Sol"
sol.data.energy = 3.5
sol.data.angle = math.radians(3)
sol.rotation_euler = (math.radians(50), math.radians(15), math.radians(40))

# ---------------------------------------------------------------------------
# 7. Camara de sobrevuelo y camara cenital
# ---------------------------------------------------------------------------
bpy.ops.object.camera_add(location=(150, 0, 90))
cam = bpy.context.object
cam.name = "Camara_Sobrevuelo"
cam.data.lens = 28
cam.data.clip_end = 2000
escena.camera = cam

objetivo = Vector((0, 0, 10))
radio = 125.0
altura = 78.0
for frame, angulo in ((1, 70), (90, 0), (180, -70)):
    a = math.radians(angulo)
    cam.location = (radio * math.cos(a), radio * math.sin(a), altura)
    direccion = objetivo - cam.location
    cam.rotation_euler = direccion.to_track_quat("-Z", "Y").to_euler()
    cam.keyframe_insert(data_path="location", frame=frame)
    cam.keyframe_insert(data_path="rotation_euler", frame=frame)

escena.frame_start = 1
escena.frame_end = 180
escena.render.fps = 24

bpy.ops.object.camera_add(location=(0, 0, 200))
cam_top = bpy.context.object
cam_top.name = "Camara_Cenital"
cam_top.data.type = "ORTHO"
cam_top.data.ortho_scale = 140
cam_top.rotation_euler = (0, 0, 0)

# ---------------------------------------------------------------------------
# 8. Render
# ---------------------------------------------------------------------------
escena.render.engine = "CYCLES"
escena.cycles.device = "CPU"
escena.cycles.samples = 16
try:
    escena.cycles.use_denoising = True
except Exception:
    pass
escena.render.resolution_x = 1100
escena.render.resolution_y = 700
escena.render.resolution_percentage = 100
escena.render.image_settings.file_format = "PNG"
escena.view_settings.view_transform = "Standard"

# Guardar el .blend
blend_path = os.path.join(BASE, "modelo_bogota_rural.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("Guardado:", blend_path)

def mostrar(version, etiquetas_visibles=False):
    terreno_relieve.hide_render = (version != "relieve")
    terreno_cat.hide_render = (version != "categorias")
    for t in etiquetas:
        t.hide_render = not etiquetas_visibles

for frame in (1, 90, 180):
    escena.frame_set(frame)
    escena.camera = cam
    for version in ("relieve", "categorias"):
        mostrar(version)
        escena.render.filepath = os.path.join(
            RENDERS, "%s_%03d.png" % (version, frame))
        print("Renderizando", version, "frame", frame)
        bpy.ops.render.render(write_still=True)

# Mapa cenital con categorias reales
mostrar("categorias", etiquetas_visibles=True)
base_urbana.hide_render = True  # sin sombra gigante en el mapa
escena.camera = cam_top
escena.render.resolution_x = 1000
escena.render.resolution_y = 1500
escena.render.filepath = os.path.join(RENDERS, "mapa_categorias_cenital.png")
print("Renderizando mapa cenital")
bpy.ops.render.render(write_still=True)

# Exportar GLB (opcional)
try:
    glb_path = os.path.join(BASE, "modelo_bogota_rural.glb")
    bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB")
    print("GLB exportado:", glb_path)
except Exception as e:
    print("No se pudo exportar GLB:", e)

print("PROCESO TERMINADO")
