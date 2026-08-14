"""Convierte superficies LandXML (TIN) a raster de elevacion para QGIS.

Uso:
    python3 landxml_a_raster.py superficie.xml
    python3 landxml_a_raster.py *.xml --celda 1.0 --epsg 32718
    python3 landxml_a_raster.py sup.xml --orden xyz     # forzar orden de coordenadas

Salida:
    <nombre>.asc   ESRI ASCII Grid, que QGIS abre directamente
    <nombre>.prj   proyeccion, si se indica --epsg
    <nombre>.tif   GeoTIFF, solo si rasterio esta instalado

Por que ASCII Grid: es texto plano, no necesita GDAL ni rasterio, y QGIS lo lee
sin plugins. Sirve igual para la calculadora raster y para Raster Surface Volume.

NOTA SOBRE EL ORDEN DE COORDENADAS
LandXML guarda los puntos como "norte este cota" (Y X Z), no como X Y Z. Es la
causa mas comun de que una superficie aparezca rotada o en medio del oceano.
El script lo detecta solo comparando magnitudes, y se puede forzar con --orden.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np

NODATA = -9999.0


# --------------------------------------------------------------- lectura
def sin_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def leer_landxml(ruta: str):
    """Devuelve lista de (nombre, puntos Nx3, caras Mx3) por superficie."""
    arbol = ET.parse(ruta)
    raiz = arbol.getroot()

    # unidades y sistema de coordenadas declarados, solo informativo
    info = {}
    for e in raiz.iter():
        t = sin_ns(e.tag)
        if t == "Metric" or t == "Imperial":
            info["unidades"] = t
            info["lineal"] = e.attrib.get("linearUnit", "?")
        elif t == "CoordinateSystem":
            info["crs"] = (e.attrib.get("name") or e.attrib.get("desc")
                           or e.attrib.get("epsgCode") or "no declarado")

    superficies = []
    for sup in raiz.iter():
        if sin_ns(sup.tag) != "Surface":
            continue
        nombre = sup.attrib.get("name", "surface")

        pnts_por_id = {}
        caras = []
        orden_ids = []
        for nodo in sup.iter():
            t = sin_ns(nodo.tag)
            if t == "P":
                txt = (nodo.text or "").strip()
                if not txt:
                    continue
                vals = [float(v) for v in re.split(r"[\s,]+", txt) if v]
                if len(vals) < 3:
                    continue
                pid = nodo.attrib.get("id")
                if pid is None:
                    pid = str(len(orden_ids) + 1)
                pnts_por_id[pid] = vals[:3]
                orden_ids.append(pid)
            elif t == "F":
                txt = (nodo.text or "").strip()
                if not txt:
                    continue
                # las caras eliminadas se marcan con i="1"; se omiten
                if nodo.attrib.get("i") == "1":
                    continue
                ids = [v for v in re.split(r"[\s,]+", txt) if v]
                if len(ids) >= 3:
                    caras.append(ids[:3])

        if not pnts_por_id:
            continue

        # indice contiguo respetando el orden de aparicion
        idx = {pid: i for i, pid in enumerate(orden_ids)}
        P = np.array([pnts_por_id[pid] for pid in orden_ids], dtype=float)
        F = []
        for c in caras:
            try:
                F.append([idx[c[0]], idx[c[1]], idx[c[2]]])
            except KeyError:
                continue
        F = np.array(F, dtype=int) if F else np.zeros((0, 3), int)
        superficies.append((nombre, P, F))

    return superficies, info


def resolver_orden(P: np.ndarray, forzado: str | None):
    """Decide si las dos primeras columnas son (norte,este) o (este,norte).

    Heuristica: en UTM el norte del hemisferio sur es del orden de millones y el
    este de cientos de miles, asi que la columna de mayor magnitud es el norte.
    """
    if forzado == "xyz":
        return P[:, 0].copy(), P[:, 1].copy(), "forzado XYZ"
    if forzado == "yxz":
        return P[:, 1].copy(), P[:, 0].copy(), "forzado YXZ"

    c0 = float(np.median(np.abs(P[:, 0])))
    c1 = float(np.median(np.abs(P[:, 1])))
    if c0 > c1 * 3:
        # col0 mucho mayor => col0 es el norte => LandXML clasico "Y X Z"
        return P[:, 1].copy(), P[:, 0].copy(), f"auto YXZ (|c0|={c0:.0f} > |c1|={c1:.0f})"
    if c1 > c0 * 3:
        return P[:, 0].copy(), P[:, 1].copy(), f"auto XYZ (|c1|={c1:.0f} > |c0|={c0:.0f})"
    return (P[:, 1].copy(), P[:, 0].copy(),
            f"auto YXZ por defecto (magnitudes similares: {c0:.0f} vs {c1:.0f}) "
            "-- VERIFICAR con --orden")


# --------------------------------------------------------------- rasterizar
def rasterizar(x, y, z, F, celda: float):
    """Interpola el TIN a una grilla regular. Usa las caras del LandXML si estan."""
    x0 = np.floor(x.min() / celda) * celda
    x1 = np.ceil(x.max() / celda) * celda
    y0 = np.floor(y.min() / celda) * celda
    y1 = np.ceil(y.max() / celda) * celda

    nx = max(int(round((x1 - x0) / celda)), 1)
    ny = max(int(round((y1 - y0) / celda)), 1)

    # centros de celda
    xs = x0 + (np.arange(nx) + 0.5) * celda
    ys = y0 + (np.arange(ny) + 0.5) * celda
    GX, GY = np.meshgrid(xs, ys)

    if len(F):
        import matplotlib.tri as mtri
        tri = mtri.Triangulation(x, y, triangles=F)
        interp = mtri.LinearTriInterpolator(tri, z)
        Z = interp(GX, GY)
        Z = np.ma.filled(Z, NODATA)
        origen = f"TIN del LandXML ({len(F):,} caras)"
    else:
        from scipy.interpolate import LinearNDInterpolator
        interp = LinearNDInterpolator(np.column_stack([x, y]), z, fill_value=NODATA)
        Z = interp(GX, GY)
        origen = "Delaunay recalculada (el LandXML no traia caras)"

    Z = np.asarray(Z, dtype=float)
    Z[~np.isfinite(Z)] = NODATA
    # ASCII Grid espera la primera fila arriba (norte)
    return Z[::-1, :], x0, y0, nx, ny, origen


def escribir_asc(ruta, Z, x0, y0, celda):
    ny, nx = Z.shape
    with open(ruta, "w") as f:
        f.write(f"ncols {nx}\nnrows {ny}\n")
        f.write(f"xllcorner {x0:.6f}\nyllcorner {y0:.6f}\n")
        f.write(f"cellsize {celda:.6f}\nNODATA_value {NODATA:.0f}\n")
        for fila in Z:
            f.write(" ".join("-9999" if v == NODATA else f"{v:.3f}" for v in fila))
            f.write("\n")


def escribir_prj(ruta, epsg):
    try:
        from pyproj import CRS
        wkt = CRS.from_epsg(int(epsg)).to_wkt("WKT1_ESRI")
        open(ruta, "w").write(wkt)
        return True
    except Exception:
        return False


def escribir_tif(ruta, Z, x0, y0, celda, epsg):
    try:
        import rasterio
        from rasterio.transform import from_origin
    except ImportError:
        return False
    ny, nx = Z.shape
    tr = from_origin(x0, y0 + ny * celda, celda, celda)
    kw = dict(driver="GTiff", height=ny, width=nx, count=1, dtype="float32",
              transform=tr, nodata=NODATA, compress="deflate")
    if epsg:
        kw["crs"] = f"EPSG:{epsg}"
    with rasterio.open(ruta, "w", **kw) as dst:
        dst.write(Z.astype("float32"), 1)
    return True


# --------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="LandXML (TIN) -> raster para QGIS")
    ap.add_argument("archivos", nargs="+", help="archivos .xml")
    ap.add_argument("--celda", type=float, default=1.0, help="tamaño de celda en m (def 1.0)")
    ap.add_argument("--epsg", default=None, help="codigo EPSG, ej 32718")
    ap.add_argument("--orden", choices=["auto", "xyz", "yxz"], default="auto",
                    help="orden de las dos primeras columnas de cada punto")
    ap.add_argument("--salida", default=".", help="carpeta de salida")
    args = ap.parse_args()

    rutas = []
    for a in args.archivos:
        rutas.extend(sorted(glob.glob(a)) or [a])

    os.makedirs(args.salida, exist_ok=True)
    resumen = []

    for ruta in rutas:
        if not os.path.exists(ruta):
            print(f"[!] no existe: {ruta}")
            continue
        print("=" * 74)
        print(ruta)
        print("=" * 74)
        try:
            sups, info = leer_landxml(ruta)
        except ET.ParseError as ex:
            print(f"  [!] no es XML valido: {ex}")
            continue

        if info:
            print(f"  declarado en el archivo: {info}")
        if not sups:
            print("  [!] no se encontro ninguna <Surface> con puntos.")
            continue

        for nombre, P, F in sups:
            x, y, orden = resolver_orden(P, None if args.orden == "auto" else args.orden)
            z = P[:, 2].copy()
            print(f"\n  superficie '{nombre}'")
            print(f"    puntos={len(P):,}  caras={len(F):,}")
            print(f"    orden de coordenadas: {orden}")
            print(f"    este  X: {x.min():14.2f}  a {x.max():14.2f}")
            print(f"    norte Y: {y.min():14.2f}  a {y.max():14.2f}")
            print(f"    cota  Z: {z.min():14.2f}  a {z.max():14.2f}")

            Z, x0, y0, nx, ny, origen = rasterizar(x, y, z, F, args.celda)
            validos = int(np.sum(Z != NODATA))
            print(f"    grilla: {nx} x {ny} celdas de {args.celda} m  "
                  f"({validos:,} con dato, {validos*args.celda**2/10000:.2f} ha)")
            print(f"    interpolacion: {origen}")

            base = re.sub(r"[^A-Za-z0-9_.-]+", "_",
                          f"{os.path.splitext(os.path.basename(ruta))[0]}_{nombre}")
            asc = os.path.join(args.salida, base + ".asc")
            escribir_asc(asc, Z, x0, y0, args.celda)
            print(f"    -> {asc}")
            if args.epsg:
                if escribir_prj(os.path.join(args.salida, base + ".prj"), args.epsg):
                    print(f"    -> {base}.prj  (EPSG:{args.epsg})")
                else:
                    print(f"    [i] no se pudo escribir .prj (falta pyproj); "
                          f"asigna EPSG:{args.epsg} en QGIS a mano")
            if escribir_tif(os.path.join(args.salida, base + ".tif"),
                            Z, x0, y0, args.celda, args.epsg):
                print(f"    -> {base}.tif")

            resumen.append((base, nx, ny, x0, y0, z.min(), z.max(), validos))

    if len(resumen) > 1:
        print("\n" + "=" * 74)
        print("COMPARACION ENTRE SUPERFICIES  (deben coincidir para poder restarlas)")
        print("=" * 74)
        print(f"{'superficie':<34}{'nx':>6}{'ny':>6}{'xll':>12}{'yll':>13}{'ha':>9}")
        for b, nx, ny, x0, y0, zmin, zmax, val in resumen:
            print(f"{b[:34]:<34}{nx:>6}{ny:>6}{x0:>12.0f}{y0:>13.0f}"
                  f"{val*args.celda**2/10000:>9.2f}")
        nxs = {r[1] for r in resumen}
        nys = {r[2] for r in resumen}
        x0s = {round(r[3], 3) for r in resumen}
        y0s = {round(r[4], 3) for r in resumen}
        if len(nxs) == 1 and len(nys) == 1 and len(x0s) == 1 and len(y0s) == 1:
            print("\n  [ok] misma grilla: se pueden restar directo en la calculadora raster.")
        else:
            print("\n  [!] LAS GRILLAS NO COINCIDEN. Antes de restar, usa en QGIS")
            print("      Raster -> Alinear raster, tomando una como referencia.")
            print("      Si no, la resta produce resultados sin sentido.")


if __name__ == "__main__":
    main()
