"""Extrae los poligonos de erosion en PLANTA, por color, y los compara con las
hectareas que declara la leyenda del plano."""
import re
from collections import defaultdict
import numpy as np
import ezdxf

# colores de la leyenda (paperspace) -> periodo
COL_PER = {46: 1, 4: 2, 30: 3, 1: 4, 216: 5, 102: 6, 5: 7, 118: 8, 6: 9, 2: 10}
CAPA_PER = {"EROSION-2018": 11}
HA_LEYENDA = {1: 3.30, 2: 0.44, 3: 0.78, 4: 0.51, 5: 0.20, 6: 0.15,
              7: 0.13, 8: 0.24, 9: 0.13, 10: 0.19, 11: 0.34}
VOL_LEYENDA = {1: 378830, 2: 42850, 3: 105450, 4: 55490, 5: 18920, 6: 11843,
               7: 11121, 8: 16786, 9: 28780, 10: 16831, 11: 26188}
ETIQ = {1: "Mar09-Sep09", 2: "Sep09-Mar10", 3: "Mar10-Sep10", 4: "Sep10-Abr11",
        5: "Abr11-Mar12", 6: "Mar12-Jun13", 7: "Jun13-Ene14", 8: "Ene14-Ene15",
        9: "Ene15-Mar16", 10: "Mar16-Jun17", 11: "Jun17-Nov18"}

# banda de los graficos de perfil: hay que EXCLUIRLA para quedarse con la planta
Y_PLOT = (5407000.0, 5407700.0)
MARCO = {"PGRID", "PGRIDT", "PBASE", "PEGCT", "PEGC", "PROSAM", "PVGRID", "FORMATO",
         "PROF_INFO", "grilla", "ventana", "5-TITULOS", "DCA_INFO", "puntos"}


def verts(e):
    t = e.dxftype()
    if t == "LWPOLYLINE":
        return [[(float(x), float(y)) for x, y in e.get_points("xy")]]
    if t == "POLYLINE":
        return [[(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]]
    if t == "HATCH":
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
                out.append(pts)
        return out
    return []


def shoelace(p):
    a = np.asarray(p, float)
    if len(a) < 3:
        return 0.0
    return 0.5 * abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1))
                           - np.dot(np.roll(a[:, 0], -1), a[:, 1])))


def main(ruta="2018 11 Perfiles Monitoreo RNegro.dxf"):
    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()

    def col(e):
        c = e.dxf.color
        if c == 256:
            try:
                return doc.layers.get(e.dxf.layer).dxf.color
            except Exception:
                return None
        return c

    # agrupar por zona en X, para separar las copias del plano
    items = []
    for e in msp:
        if e.dxftype() not in ("LWPOLYLINE", "POLYLINE", "HATCH"):
            continue
        if e.dxf.layer in MARCO:
            continue
        cs = verts(e)
        if not cs:
            continue
        allp = [q for c in cs for q in c]
        xs = [q[0] for q in allp]
        ys = [q[1] for q in allp]
        if Y_PLOT[0] <= min(ys) and max(ys) <= Y_PLOT[1]:
            continue          # es un grafico de perfil, no planta
        c = col(e)
        per = CAPA_PER.get(e.dxf.layer) or COL_PER.get(c)
        if per is None:
            continue
        items.append(dict(per=per, capa=e.dxf.layer, col=c, tipo=e.dxftype(),
                          area=sum(shoelace(q) for q in cs),
                          x=float(np.mean(xs)), y=float(np.mean(ys)),
                          x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys),
                          nv=len(allp)))

    if not items:
        print("no se hallaron poligonos de erosion en planta")
        return

    xs = np.array([it["x"] for it in items])
    print("--- zonas en X detectadas (copias del plano):")
    orden = np.sort(xs)
    cortes = [0] + [i + 1 for i in range(len(orden) - 1)
                    if orden[i + 1] - orden[i] > 2000] + [len(orden)]
    zonas = []
    for a, b in zip(cortes, cortes[1:]):
        zonas.append((orden[a], orden[b - 1]))
        print(f"    X de {orden[a]:.0f} a {orden[b-1]:.0f}   ({b-a} poligonos)")

    for zi, (za, zb) in enumerate(zonas, 1):
        sel = [it for it in items if za - 1 <= it["x"] <= zb + 1]
        print("\n" + "=" * 92)
        print(f"ZONA {zi}:  X {za:.0f} a {zb:.0f}   ({len(sel)} poligonos)")
        print("=" * 92)
        porper = defaultdict(float)
        nper = defaultdict(int)
        for it in sel:
            porper[it["per"]] += it["area"]
            nper[it["per"]] += 1
        print(f"{'per':<5}{'periodo':<14}{'n':>4}{'area_dxf_m2':>14}{'area_ha':>10}"
              f"{'ha_leyenda':>12}{'razon':>8}{'V/A_m':>8}")
        print("-" * 92)
        tot = 0.0
        for p in sorted(porper):
            a = porper[p]
            ha = a / 10000
            hl = HA_LEYENDA.get(p, float("nan"))
            razon = ha / hl if hl else float("nan")
            va = VOL_LEYENDA.get(p, 0) / a if a else float("nan")
            tot += a
            print(f"{p:<5}{ETIQ[p]:<14}{nper[p]:>4}{a:>14,.0f}{ha:>10.2f}"
                  f"{hl:>12.2f}{razon:>8.2f}{va:>8.1f}")
        print("-" * 92)
        ha_tot = tot / 10000
        hl_tot = sum(HA_LEYENDA[p] for p in porper if p in HA_LEYENDA)
        print(f"{'':5}{'TOTAL':<14}{len(sel):>4}{tot:>14,.0f}{ha_tot:>10.2f}"
              f"{hl_tot:>12.2f}{ha_tot/hl_tot if hl_tot else float('nan'):>8.2f}")


def areas_planta(ruta="2018 11 Perfiles Monitoreo RNegro.dxf",
                 zona=(715000.0, 719500.0)):
    """Area total en planta por periodo, dentro de una zona en X.

    Devuelve {periodo: (area_m2, n_poligonos)}. Se usa la zona del 'detalle
    seccion', que es donde estan dibujados los poligonos de todos los periodos.
    """
    doc = ezdxf.readfile(ruta)

    def col(e):
        c = e.dxf.color
        if c == 256:
            try:
                return doc.layers.get(e.dxf.layer).dxf.color
            except Exception:
                return None
        return c

    out = defaultdict(lambda: [0.0, 0])
    for e in doc.modelspace():
        if e.dxftype() not in ("LWPOLYLINE", "POLYLINE", "HATCH"):
            continue
        if e.dxf.layer in MARCO:
            continue
        cs = verts(e)
        if not cs:
            continue
        allp = [q for c in cs for q in c]
        xs = [q[0] for q in allp]
        ys = [q[1] for q in allp]
        if Y_PLOT[0] <= min(ys) and max(ys) <= Y_PLOT[1]:
            continue
        if not (zona[0] <= float(np.mean(xs)) <= zona[1]):
            continue
        per = CAPA_PER.get(e.dxf.layer) or COL_PER.get(col(e))
        if per is None:
            continue
        a = sum(shoelace(q) for q in cs)
        # descartar poligonos absurdamente grandes: son geometria ajena que
        # comparte color (bordes de lamina, poligonos de predio, etc.)
        if a > 60000:
            continue
        out[per][0] += a
        out[per][1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


if __name__ == "__main__":
    main()
    print("\n" + "=" * 92)
    print("AREA POR PERIODO EN LA ZONA DEL DETALLE, CON FILTRO DE POLIGONOS ANOMALOS")
    print("=" * 92)
    ap = areas_planta()
    print(f"{'per':<5}{'periodo':<14}{'n':>4}{'area_ha':>10}{'ha_leyenda':>12}"
          f"{'razon':>8}{'espesor_m':>11}")
    print("-" * 92)
    ok = 0
    for p in sorted(HA_LEYENDA):
        a, n = ap.get(p, (0.0, 0))
        ha = a / 10000
        hl = HA_LEYENDA[p]
        raz = ha / hl if hl else float("nan")
        esp = VOL_LEYENDA[p] / a if a else float("nan")
        if abs(raz - 1) <= 0.05:
            ok += 1
        print(f"{p:<5}{ETIQ[p]:<14}{n:>4}{ha:>10.2f}{hl:>12.2f}{raz:>8.2f}{esp:>11.1f}")
    print("-" * 92)
    print(f"Coinciden {ok} de {len(HA_LEYENDA)} periodos dentro del 5%.")
