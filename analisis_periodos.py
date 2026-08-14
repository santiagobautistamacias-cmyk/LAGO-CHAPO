"""Analisis por periodo: tasas, acumulados y verificacion del metodo de volumenes."""
import re
from datetime import date
import numpy as np
import ezdxf

Y0, Y1 = 5407000.0, 5407700.0
MARCO = {"PGRID", "PGRIDT", "PBASE", "PEGCT", "PEGC", "PROSAM", "PVGRID", "FORMATO",
         "PROF_INFO", "grilla", "ventana", "5-TITULOS", "DCA_INFO"}

# orden hidraulico y distancias, medidos antes desde las trazas UTM
ORDEN_H = ["1", "A", "2", "B", "3", "4", "C"]
DIST = {("1", "A"): 154.3, ("A", "2"): 508.0, ("2", "B"): 128.9,
        ("B", "3"): 117.0, ("3", "4"): 283.7, ("4", "C"): 399.5}

# Leyenda del paperspace. color 46 y 118 se infieren por descarte y magnitud.
PERIODOS = [
    dict(n=1,  ini=date(2009, 3, 1),  fin=date(2009, 9, 1),  col=46,  capa=None,
         ha=3.30, vol=378830, inferido=True),
    dict(n=2,  ini=date(2009, 9, 1),  fin=date(2010, 3, 1),  col=4,   capa=None,
         ha=0.44, vol=42850,  inferido=False),
    dict(n=3,  ini=date(2010, 3, 1),  fin=date(2010, 9, 1),  col=30,  capa=None,
         ha=0.78, vol=105450, inferido=False),
    dict(n=4,  ini=date(2010, 9, 1),  fin=date(2011, 4, 1),  col=1,   capa=None,
         ha=0.51, vol=55490,  inferido=False),
    dict(n=5,  ini=date(2011, 4, 1),  fin=date(2012, 3, 1),  col=216, capa=None,
         ha=0.20, vol=18920,  inferido=False),
    dict(n=6,  ini=date(2012, 3, 1),  fin=date(2013, 6, 1),  col=102, capa=None,
         ha=0.15, vol=11843,  inferido=False),
    dict(n=7,  ini=date(2013, 6, 1),  fin=date(2014, 1, 1),  col=5,   capa=None,
         ha=0.13, vol=11121,  inferido=False),
    dict(n=8,  ini=date(2014, 1, 1),  fin=date(2015, 1, 1),  col=118, capa=None,
         ha=0.24, vol=16786,  inferido=True),
    dict(n=9,  ini=date(2015, 1, 1),  fin=date(2016, 3, 1),  col=6,   capa=None,
         ha=0.13, vol=28780,  inferido=False),
    dict(n=10, ini=date(2016, 3, 1),  fin=date(2017, 6, 1),  col=2,   capa=None,
         ha=0.19, vol=16831,  inferido=False),
    dict(n=11, ini=date(2017, 6, 1),  fin=date(2018, 11, 1), col=None, capa="EROSION-2018",
         ha=0.34, vol=26188,  inferido=False),
]
ETIQ = {1: "Mar09-Sep09", 2: "Sep09-Mar10", 3: "Mar10-Sep10", 4: "Sep10-Abr11",
        5: "Abr11-Mar12", 6: "Mar12-Jun13", 7: "Jun13-Ene14", 8: "Ene14-Ene15",
        9: "Ene15-Mar16", 10: "Mar16-Jun17", 11: "Jun17-Nov18"}


def limpiar(t):
    return re.sub(r"\\[A-Za-z][^;]*;", "", t).replace("{", "").replace("}", "").strip()


def caminos(e):
    t = e.dxftype()
    if t == "LWPOLYLINE":
        return [[(float(x), float(y)) for x, y in e.get_points("xy")]]
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


def bandas_por_corte(ruta="2018 11 Perfiles Monitoreo RNegro.dxf"):
    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()

    def col_real(e):
        c = e.dxf.color
        if c == 256:
            try:
                return doc.layers.get(e.dxf.layer).dxf.color
            except Exception:
                return None
        return c

    titulos, refs, cands = [], [], []
    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            x, y = float(e.dxf.insert[0]), float(e.dxf.insert[1])
            if Y0 <= y <= Y1:
                m = re.match(r"CORTE\s+([0-9A-D]+)\s*-", limpiar(e.dxf.text), re.I)
                if m:
                    titulos.append((m.group(1).upper(), x, y))
        elif t in ("HATCH", "LWPOLYLINE"):
            cs = caminos(e)
            if not cs:
                continue
            allp = [q for c in cs for q in c]
            ys = [q[1] for q in allp]
            if not (Y0 <= min(ys) and max(ys) <= Y1) or e.dxf.layer in MARCO:
                continue
            xs = [q[0] for q in allp]
            it = dict(tipo=t, capa=e.dxf.layer, col=col_real(e), x0=min(xs), x1=max(xs),
                      y0=min(ys), y1=max(ys), area=sum(shoelace(c) for c in cs) / 10.0,
                      nv=len(allp))
            (refs if (t == "LWPOLYLINE" and it["nv"] >= 20
                      and it["x1"] - it["x0"] > 150) else cands).append(it)

    graf = {}
    for nom, tx, ty in titulos:
        mejor, dmin = None, 1e18
        for r in refs:
            d = abs(r["x0"] - tx) + 0.3 * abs(r["y1"] - ty)
            if d < dmin:
                mejor, dmin = r, d
        graf[nom] = dict(ref=mejor, bandas=[])
    for it in cands:
        for nom, g in graf.items():
            r = g["ref"]
            if r and (r["x0"] - 40 <= it["x0"] and it["x1"] <= r["x1"] + 40
                      and r["y0"] - 60 <= it["y0"] and it["y1"] <= r["y1"] + 60):
                it["est0"] = it["x0"] - r["x0"]
                it["est1"] = it["x1"] - r["x0"]
                g["bandas"].append(it)
                break

    # area por (corte, periodo)
    area = {}
    for nom, g in graf.items():
        for b in g["bandas"]:
            p = None
            for per in PERIODOS:
                if per["capa"] and b["capa"] == per["capa"]:
                    p = per["n"]; break
                if per["col"] is not None and b["col"] == per["col"] and b["capa"] != "EROSION-2018":
                    p = per["n"]; break
            if p is None:
                continue
            k = (nom, p)
            area[k] = area.get(k, 0.0) + b["area"]
            area.setdefault(("est", nom, p), []).append((b["est0"], b["est1"]))
    return graf, area


def vol_areas_medias(area, p):
    """Volumen del periodo p por areas medias, con las distancias medidas."""
    tot, tramos = 0.0, []
    for a, b in zip(ORDEN_H, ORDEN_H[1:]):
        L = DIST.get((a, b), DIST.get((b, a)))
        if L is None:
            continue
        Aa = area.get((a, p), 0.0)
        Ab = area.get((b, p), 0.0)
        v = (Aa + Ab) / 2 * L
        tot += v
        tramos.append((f"{a}-{b}", Aa, Ab, L, v))
    return tot, tramos


if __name__ == "__main__":
    graf, area = bandas_por_corte()

    print("=" * 96)
    print("TABLA POR PERIODO — lo que hay que comparar")
    print("=" * 96)
    print(f"{'#':<3}{'periodo':<14}{'meses':>6}{'area_ha':>9}{'volumen_m3':>12}"
          f"{'m3/mes':>10}{'m3/año':>11}{'acum_m3':>12}")
    print("-" * 96)
    acum = 0.0
    filas = []
    for per in PERIODOS:
        meses = (per["fin"] - per["ini"]).days / 30.44
        tasa_m = per["vol"] / meses
        tasa_a = tasa_m * 12
        acum += per["vol"]
        filas.append((per["n"], meses, tasa_m, tasa_a, acum))
        print(f"{per['n']:<3}{ETIQ[per['n']]:<14}{meses:>6.1f}{per['ha']:>9.2f}"
              f"{per['vol']:>12,.0f}{tasa_m:>10,.0f}{tasa_a:>11,.0f}{acum:>12,.0f}")
    print("-" * 96)
    tot_ha = sum(p["ha"] for p in PERIODOS)
    tot_v = sum(p["vol"] for p in PERIODOS)
    meses_tot = (PERIODOS[-1]["fin"] - PERIODOS[0]["ini"]).days / 30.44
    print(f"{'':3}{'TOTAL':<14}{meses_tot:>6.1f}{tot_ha:>9.2f}{tot_v:>12,.0f}"
          f"{tot_v/meses_tot:>10,.0f}{tot_v/meses_tot*12:>11,.0f}")

    print("\n>>> La tasa cae de {:,.0f} m3/año en el primer periodo a {:,.0f} m3/año en el ultimo:"
          .format(filas[0][3], filas[-1][3]))
    print("    un factor de {:.0f}. Sin el periodo 1, la caida sigue siendo de {:,.0f} a {:,.0f}."
          .format(filas[0][3] / filas[-1][3], filas[1][3], filas[-1][3]))

    print("\n" + "=" * 96)
    print("VERIFICACION DEL METODO DE VOLUMENES")
    print("=" * 96)
    print("Se recalcula cada periodo por AREAS MEDIAS con las areas de banda medidas en los")
    print("perfiles y las distancias entre cortes obtenidas de las trazas UTM, y se compara")
    print("contra el volumen que declara la leyenda del plano.\n")
    print(f"{'#':<3}{'periodo':<14}{'cortes_con_banda':>18}{'V_calculado':>14}"
          f"{'V_plano':>12}{'dif_%':>9}")
    print("-" * 96)
    for per in PERIODOS:
        p = per["n"]
        v, _ = vol_areas_medias(area, p)
        ncortes = sum(1 for c in ORDEN_H if area.get((c, p), 0) > 0)
        dif = (v - per["vol"]) / per["vol"] * 100 if per["vol"] else float("nan")
        marca = "  <<< coincide" if abs(dif) < 10 else ""
        print(f"{p:<3}{ETIQ[p]:<14}{ncortes:>18}{v:>14,.0f}{per['vol']:>12,.0f}"
              f"{dif:>9.1f}{marca}")

    print("\n" + "=" * 96)
    print("AREA DE BANDA POR CORTE Y PERIODO  (m2)")
    print("=" * 96)
    print(f"{'corte':<7}" + "".join(f"{ETIQ[p['n']][:9]:>10}" for p in PERIODOS))
    for c in ORDEN_H:
        fila = f"{c:<7}"
        for per in PERIODOS:
            a = area.get((c, per["n"]), 0.0)
            fila += f"{a:>10.1f}" if a else f"{'-':>10}"
        print(fila)

    print("\n--- retroceso de la ladera en el corte 1 (estacion de cada banda):")
    for per in PERIODOS:
        k = ("est", "1", per["n"])
        if k in area:
            for e0, e1 in sorted(area[k]):
                print(f"    {ETIQ[per['n']]:<14} est=[{e0:7.1f},{e1:7.1f}]")
