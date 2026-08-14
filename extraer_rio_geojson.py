"""Extrae el poligono del rio (dibujado como HATCH) del DWG a GeoJSON para QGIS.

Un hatch no es un poligono que QGIS pueda usar como mascara, pero si guarda sus
caminos de contorno. Este script los lee y los escribe como GeoJSON en el CRS
indicado, listo para 'Cortar raster por capa de mascara'.

Uso:
    python3 extraer_rio_geojson.py entrada.dxf --capa rio --epsg 32718
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import ezdxf

# ventana UTM del levantamiento; descarta copias desplazadas del plano
VENTANA = (708000.0, 711500.0, 5410500.0, 5413500.0)


def caminos_hatch(e):
    """Devuelve [(vertices, es_isla)] por cada camino del hatch."""
    out = []
    for p in e.paths:
        vs = getattr(p, "vertices", None)
        pts = [(float(v[0]), float(v[1])) for v in vs] if vs else []
        if not pts:
            for ar in getattr(p, "edges", []) or []:
                for a in ("start", "end"):
                    q = getattr(ar, a, None)
                    if q is not None:
                        pts.append((float(q[0]), float(q[1])))
        if len(pts) >= 3:
            flags = int(getattr(p, "path_type_flags", 0))
            # bit 1 = externo, bit 16 = outermost; el resto son islas
            es_isla = not (flags & 1) and not (flags & 16)
            out.append((pts, es_isla))
    return out


def area(p):
    a = np.asarray(p, float)
    if len(a) < 3:
        return 0.0
    return 0.5 * abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1))
                           - np.dot(np.roll(a[:, 0], -1), a[:, 1])))


def cerrar(p):
    return p + [p[0]] if p[0] != p[-1] else p


def en_ventana(pts):
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    x0, x1, y0, y1 = VENTANA
    return (x0 <= min(xs) and max(xs) <= x1 and y0 <= min(ys) and max(ys) <= y1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--capa", default="rio", help="capa del rio (def: rio)")
    ap.add_argument("--epsg", default="32718")
    ap.add_argument("--salida", default="rio.geojson")
    ap.add_argument("--min-area", type=float, default=100.0,
                    help="descarta poligonos menores a esta area en m2")
    args = ap.parse_args()

    doc = ezdxf.readfile(args.dxf)
    msp = doc.modelspace()

    feats = []
    total = 0.0
    for e in msp:
        if e.dxf.layer != args.capa:
            continue
        t = e.dxftype()
        anillos = []

        if t == "HATCH":
            cs = caminos_hatch(e)
            ext = [c for c, isla in cs if not isla]
            islas = [c for c, isla in cs if isla]
            if not ext:
                continue
            # el camino externo mas grande manda; el resto se anexa como anillos
            ext.sort(key=area, reverse=True)
            anillos = [cerrar(ext[0])] + [cerrar(i) for i in islas]
            extras = ext[1:]
        elif t in ("LWPOLYLINE", "POLYLINE"):
            if t == "LWPOLYLINE":
                pts = [(float(x), float(y)) for x, y in e.get_points("xy")]
            else:
                pts = [(float(v.dxf.location[0]), float(v.dxf.location[1]))
                       for v in e.vertices]
            if len(pts) < 3:
                continue
            anillos = [cerrar(pts)]
            extras = []
        else:
            continue

        for grupo in [anillos] + [[cerrar(x)] for x in extras]:
            if not en_ventana(grupo[0]):
                continue
            a = area(grupo[0]) - sum(area(r) for r in grupo[1:])
            if a < args.min_area:
                continue
            total += a
            feats.append({
                "type": "Feature",
                "properties": {"capa": args.capa, "tipo": t,
                               "area_m2": round(a, 1), "area_ha": round(a / 10000, 3),
                               "n_vertices": len(grupo[0])},
                "geometry": {"type": "Polygon",
                             "coordinates": [[[round(x, 3), round(y, 3)] for x, y in r]
                                             for r in grupo]},
            })

    if not feats:
        sys.exit(f"No se hallaron poligonos en la capa '{args.capa}' "
                 f"dentro de la ventana {VENTANA}. Revisa el nombre de la capa.")

    feats.sort(key=lambda f: -f["properties"]["area_m2"])
    gj = {
        "type": "FeatureCollection",
        "name": f"{args.capa}_poligono",
        "crs": {"type": "name",
                "properties": {"name": f"urn:ogc:def:crs:EPSG::{args.epsg}"}},
        "features": feats,
    }
    with open(args.salida, "w") as f:
        json.dump(gj, f, indent=1)

    print(f"capa '{args.capa}': {len(feats)} poligonos, {total/10000:.2f} ha en total")
    for i, ft in enumerate(feats, 1):
        p = ft["properties"]
        print(f"  {i}. {p['tipo']:<11} {p['area_ha']:>8.3f} ha  "
              f"({p['n_vertices']} vertices)")
    print(f"\n-> {args.salida}   EPSG:{args.epsg}")
    print("\nEn QGIS: Capa -> Anadir capa -> Anadir capa vectorial.")
    print("Antes de usarlo como mascara, considera aplicarle un Buffer de 50 a 100 m:")
    print("la erosion ocurre en las MARGENES, fuera del cauce dibujado, y si recortas")
    print("justo al borde del rio te quedas sin la zona que quieres medir.")


if __name__ == "__main__":
    main()
