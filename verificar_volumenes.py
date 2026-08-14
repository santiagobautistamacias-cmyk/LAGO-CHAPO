"""Calcula erosion y depositacion entre DEM, para verificar lo que da QGIS.

No necesita QGIS. Lee GeoTIFF (con rasterio) o ESRI ASCII Grid (.asc, sin
dependencias) y reproduce exactamente la cadena de QGIS:
    recortar -> restar -> umbral de deteccion -> volumen sobre/bajo base 0

Uso:
    python3 verificar_volumenes.py 2009.tif 2014.tif 2018.tif 2026.tif
    python3 verificar_volumenes.py *.asc --umbral 0.5
    python3 verificar_volumenes.py *.tif --mascara rio.geojson

Sirve para contrastar contra Raster Surface Volume. Si los dos coinciden, el
resultado es solido. Si no, hay un problema de CRS, de NoData o de recorte.
"""

from __future__ import annotations

import argparse
import glob
import itertools
import os
import sys

import numpy as np

NODATA_DEF = -9999.0


# ------------------------------------------------------------------ lectura
def leer_asc(ruta):
    with open(ruta) as f:
        cab = {}
        while len(cab) < 6:
            pos = f.tell()
            linea = f.readline()
            if not linea:
                break
            partes = linea.split()
            if len(partes) == 2 and not partes[0][0].isdigit() and partes[0][0] != "-":
                cab[partes[0].lower()] = float(partes[1])
            else:
                f.seek(pos)
                break
        Z = np.loadtxt(f)
    nx = int(cab.get("ncols", Z.shape[1]))
    ny = int(cab.get("nrows", Z.shape[0]))
    celda = float(cab.get("cellsize", 1.0))
    xll = float(cab.get("xllcorner", cab.get("xllcenter", 0.0)))
    yll = float(cab.get("yllcorner", cab.get("yllcenter", 0.0)))
    nd = float(cab.get("nodata_value", NODATA_DEF))
    return dict(Z=Z.reshape(ny, nx), celda=celda, xll=xll, yll=yll, nodata=nd,
                nx=nx, ny=ny, crs=None)


def leer_tif(ruta):
    import rasterio
    with rasterio.open(ruta) as src:
        Z = src.read(1).astype(float)
        tr = src.transform
        if abs(abs(tr.a) - abs(tr.e)) > 1e-6:
            print(f"    [!] pixel no cuadrado: {tr.a} x {tr.e}")
        celda = abs(tr.a)
        nd = src.nodata if src.nodata is not None else NODATA_DEF
        return dict(Z=Z, celda=celda, xll=tr.c, yll=tr.f - src.height * celda,
                    nodata=nd, nx=src.width, ny=src.height,
                    crs=str(src.crs) if src.crs else None)


def leer(ruta):
    if ruta.lower().endswith((".tif", ".tiff")):
        try:
            return leer_tif(ruta)
        except ImportError:
            sys.exit("Para GeoTIFF hace falta rasterio:  pip install rasterio")
    return leer_asc(ruta)


def aplicar_mascara(r, ruta_mascara):
    """Pone NoData fuera del polígono. Requiere rasterio + geopandas."""
    try:
        import geopandas as gpd
        from rasterio.features import geometry_mask
        from rasterio.transform import from_origin
    except ImportError:
        print("    [i] mascara omitida (falta geopandas/rasterio); "
              "recorta en QGIS antes de correr esto")
        return r
    gdf = gpd.read_file(ruta_mascara)
    tr = from_origin(r["xll"], r["yll"] + r["ny"] * r["celda"], r["celda"], r["celda"])
    m = geometry_mask(gdf.geometry, out_shape=(r["ny"], r["nx"]), transform=tr,
                      invert=True)
    Z = r["Z"].copy()
    Z[~m] = r["nodata"]
    r = dict(r)
    r["Z"] = Z
    return r


# ------------------------------------------------------------------ calculo
def volumenes(a, b, umbral):
    """b menos a. Devuelve erosion, depositacion y estadisticas."""
    if a["Z"].shape != b["Z"].shape:
        return None
    celda = a["celda"]
    A = np.where(a["Z"] == a["nodata"], np.nan, a["Z"])
    B = np.where(b["Z"] == b["nodata"], np.nan, b["Z"])
    D = B - A
    valido = np.isfinite(D)

    Df = np.where(np.abs(D) >= umbral, D, 0.0)
    Df[~valido] = np.nan

    area = celda * celda
    ero = float(np.nansum(np.where(Df < 0, -Df, 0.0)) * area)
    dep = float(np.nansum(np.where(Df > 0, Df, 0.0)) * area)
    n_cambio = int(np.nansum(np.abs(Df) > 1e-9))
    return dict(
        erosion=ero, deposito=dep, neto=ero - dep,
        area_cambio_ha=n_cambio * area / 10000,
        area_valida_ha=int(np.sum(valido)) * area / 10000,
        dz_min=float(np.nanmin(D)) if valido.any() else float("nan"),
        dz_max=float(np.nanmax(D)) if valido.any() else float("nan"),
        pct_area=100 * n_cambio / max(int(np.sum(valido)), 1),
    )


def main():
    ap = argparse.ArgumentParser(description="Verifica volúmenes entre DEM")
    ap.add_argument("dems", nargs="+", help="DEM en orden cronológico")
    ap.add_argument("--umbral", type=float, default=0.5,
                    help="umbral de detección en m (def 0.5)")
    ap.add_argument("--mascara", default=None, help="polígono de recorte (geojson/shp)")
    args = ap.parse_args()

    rutas = []
    for a in args.dems:
        rutas.extend(sorted(glob.glob(a)) or [a])
    if len(rutas) < 2:
        sys.exit("Hacen falta al menos dos DEM.")

    print("=" * 84)
    print("1) LECTURA Y VERIFICACION DE LAS GRILLAS")
    print("=" * 84)
    caps = []
    for r in rutas:
        d = leer(r)
        d["nombre"] = os.path.basename(r)
        if args.mascara:
            d = aplicar_mascara(d, args.mascara)
            d["nombre"] = os.path.basename(r)
        Zv = np.where(d["Z"] == d["nodata"], np.nan, d["Z"])
        nval = int(np.sum(np.isfinite(Zv)))
        print(f"\n  {d['nombre']}")
        print(f"    grilla   : {d['nx']} x {d['ny']}  celda {d['celda']} m")
        print(f"    esquina  : xll={d['xll']:.2f}  yll={d['yll']:.2f}")
        print(f"    cotas    : {np.nanmin(Zv):.2f} a {np.nanmax(Zv):.2f} m")
        print(f"    con dato : {nval:,} celdas = {nval*d['celda']**2/10000:.2f} ha")
        if d["crs"]:
            print(f"    CRS      : {d['crs']}")
        caps.append(d)

    firmas = {(c["nx"], c["ny"], round(c["xll"], 2), round(c["yll"], 2),
               round(c["celda"], 4)) for c in caps}
    print()
    if len(firmas) == 1:
        print("  [ok] las grillas coinciden: se pueden restar directamente.")
    else:
        print("  [!] LAS GRILLAS NO COINCIDEN. Alinea o recorta todo con la misma")
        print("      mascara antes de continuar. Los pares que no calcen se omiten.")

    print("\n" + "=" * 84)
    print(f"2) VOLUMENES  (umbral de deteccion = {args.umbral} m)")
    print("=" * 84)
    print(f"\n{'par':<34}{'erosion m3':>13}{'deposito m3':>13}"
          f"{'neto m3':>12}{'area cambio':>13}")
    print("-" * 84)

    consecutivos = []
    for a, b in zip(caps, caps[1:]):
        v = volumenes(a, b, args.umbral)
        nom = f"{a['nombre'][:14]} -> {b['nombre'][:14]}"
        if v is None:
            print(f"{nom:<34}{'grillas distintas':>51}")
            continue
        consecutivos.append(v)
        print(f"{nom:<34}{v['erosion']:>13,.0f}{v['deposito']:>13,.0f}"
              f"{v['neto']:>12,.0f}{v['area_cambio_ha']:>10.2f} ha")

    if len(caps) > 2:
        v = volumenes(caps[0], caps[-1], args.umbral)
        if v:
            print("-" * 84)
            nom = f"TOTAL {caps[0]['nombre'][:11]} -> {caps[-1]['nombre'][:11]}"
            print(f"{nom:<34}{v['erosion']:>13,.0f}{v['deposito']:>13,.0f}"
                  f"{v['neto']:>12,.0f}{v['area_cambio_ha']:>10.2f} ha")
            if consecutivos:
                se = sum(c["erosion"] for c in consecutivos)
                print(f"{'suma de los consecutivos':<34}{se:>13,.0f}")
                dif = (se - v["erosion"]) / v["erosion"] * 100 if v["erosion"] else 0
                estado = "[ok]" if abs(dif) < 5 else "[!] revisar"
                print(f"\n  {estado} la suma de los periodos vs el total difiere {dif:+.1f}%")
                print("       Diferencias grandes indican NoData distinto entre epocas")
                print("       o que el umbral esta recortando cambios pequenos repetidos.")

    print("\n" + "=" * 84)
    print("3) CONTROLES CONTRA LO YA CONOCIDO DEL PLANO")
    print("=" * 84)
    print("  El plano de 2018 declara, entre marzo 2009 y noviembre 2018:")
    print("      volumen erosionado  =  713.089 m3")
    print("      superficie afectada =    6,41 ha")
    print("  Si tu rango temporal es parecido, tus cifras deberian ser del mismo")
    print("  orden. Ordenes de magnitud distintos = problema de CRS o de unidades.")
    print("  Area de cambio mucho mayor que 6,41 ha = umbral bajo, estas contando ruido.")

    print("\n" + "=" * 84)
    print("4) SENSIBILIDAD AL UMBRAL")
    print("=" * 84)
    print("  Conviene reportar como varia el resultado con el umbral elegido:\n")
    pares = list(zip(caps, caps[1:]))
    encabezados = [a["nombre"][:11] + "->" + b["nombre"][:8] for a, b in pares]
    print(f"{'umbral m':>10}" + "".join(f"{h:>26}" for h in encabezados))
    for u in (0.0, 0.25, 0.5, 1.0, 1.5):
        celdas = []
        for a, b in pares:
            v = volumenes(a, b, u)
            celdas.append(f"{v['erosion']:,.0f}" if v else "n/d")
        print(f"{u:>10.2f}" + "".join(f"{c:>26}" for c in celdas))
    print("\n  Si el volumen cae mucho al subir el umbral, buena parte de lo que")
    print("  contabas era ruido de interpolacion y no erosion real.")


if __name__ == "__main__":
    main()
