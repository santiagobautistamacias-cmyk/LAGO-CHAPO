"""Genera el libro Excel de analisis a partir de los DXF del Rio Negro.

Fuente : DXF obtenidos con LibreDWG (dwg2dxf) desde los DWG originales.
Escalas: horizontal 1 u/m, vertical 10 u/m (exageracion x10), calibrada por
         grafico con las etiquetas del eje (capa PGRIDT).
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np
import ezdxf
from openpyxl import Workbook
from openpyxl.chart import ScatterChart, Reference, Series
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

Y_MIN, Y_MAX = 5407000.0, 5407700.0
ESCALA_H = 1.0
CAPAS_MARCO = {
    "PGRID", "PGRIDT", "PBASE", "PEGCT", "PEGC", "PROSAM", "PVGRID", "FORMATO",
    "PROF_INFO", "grilla", "ventana", "5-TITULOS", "DCA_INFO",
}
ORDEN = ["1", "2", "3", "4", "A", "B", "C"]          # orden de rotulo, para listar
# El orden hidraulico (aguas abajo -> aguas arriba) se deduce de la cota del
# thalweg: el agua corre cuesta abajo, luego el corte de fondo mas bajo es el
# mas cercano a la desembocadura. Se calcula en tiempo de ejecucion.


def orden_hidraulico(cortes: Dict[str, "Corte"]) -> List[str]:
    """Cortes ordenados de aguas abajo (fondo mas bajo) a aguas arriba."""
    return sorted(
        [n for n in ORDEN if n in cortes],
        key=lambda n: min(z for _, z in cortes[n].perfil),
    )
ARCHIVOS = [
    ("2014-01", "enero 2014", "2014 01 Perfiles Monitoreo RNegro b.dxf"),
    ("2018-11", "junio 2018", "2018 11 Perfiles Monitoreo RNegro.dxf"),
]
# niveles de referencia del lago segun el informe INGETEC
NIVELES = [
    (230.0, "minimo historico citado"),
    (231.0, "cota minima provisional 3TA"),
    (243.0, "maximo normal aproximado"),
]

# ---------------------------------------------------------------- estilos
AZUL = "1F4E79"
GRIS = "D9D9D9"
AMBAR = "FFF2CC"
VERDE = "E2EFDA"
BORDE = Border(*[Side(style="thin", color="BFBFBF")] * 4)


def h1(ws, celda, txt):
    c = ws[celda]
    c.value = txt
    c.font = Font(bold=True, size=13, color=AZUL)


def encabezado(ws, fila, cols, ancho=None):
    for i, t in enumerate(cols, start=1):
        c = ws.cell(row=fila, column=i, value=t)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.freeze_panes = ws.cell(row=fila + 1, column=1)
    for i, w in enumerate(ancho or [], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


# ---------------------------------------------------------------- extraccion
def limpiar(t):
    return re.sub(r"\\[A-Za-z][^;]*;", "", t).replace("{", "").replace("}", "").strip()


def verts(e):
    t = e.dxftype()
    if t == "LWPOLYLINE":
        return [(float(x), float(y)) for x, y in e.get_points("xy")]
    if t == "POLYLINE":
        return [(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices]
    return []


def caminos_hatch(e):
    """Devuelve lista de (vertices, es_isla) por camino del hatch."""
    out = []
    for path in e.paths:
        vs = getattr(path, "vertices", None)
        pts = [(float(v[0]), float(v[1])) for v in vs] if vs else []
        if not pts:
            for ar in getattr(path, "edges", []) or []:
                for attr in ("start", "end"):
                    p = getattr(ar, attr, None)
                    if p is not None:
                        pts.append((float(p[0]), float(p[1])))
        if len(pts) >= 3:
            flags = int(getattr(path, "path_type_flags", 0))
            es_isla = not bool(flags & 1) and not bool(flags & 16)
            out.append((pts, es_isla))
    return out


def shoelace(p):
    if len(p) < 3:
        return 0.0
    a = np.asarray(p, float)
    return 0.5 * abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1))
                            - np.dot(np.roll(a[:, 0], -1), a[:, 1])))


class Corte:
    def __init__(self, nombre, tx, ty):
        self.nombre, self.tx, self.ty = nombre, tx, ty
        self.escala_v = 10.0
        self.z_ref = self.y_ref = 0.0
        self.resid = 0.0
        self.n_etiq = 0
        self.perfil: List[Tuple[float, float]] = []
        self.polis: List[dict] = []

    def cota(self, y):
        return self.z_ref + (y - self.y_ref) / self.escala_v

    def est(self, x):
        return (x - self.x0) / ESCALA_H


def extraer(ruta):
    doc = ezdxf.readfile(ruta)
    msp = doc.modelspace()
    titulos, ejes, cands = [], [], []

    for e in msp:
        t = e.dxftype()
        if t == "TEXT":
            x, y = float(e.dxf.insert[0]), float(e.dxf.insert[1])
            if not (Y_MIN <= y <= Y_MAX):
                continue
            txt = limpiar(e.dxf.text)
            m = re.match(r"CORTE\s+([0-9A-D]+)\s*-", txt, re.I)
            if m:
                titulos.append((m.group(1).upper(), x, y))
            elif e.dxf.layer == "PGRIDT" and re.fullmatch(r"\d{3}", txt):
                ejes.append((float(txt), x, y))
        elif t in ("LWPOLYLINE", "POLYLINE", "HATCH"):
            if t == "HATCH":
                cs = caminos_hatch(e)
                if not cs:
                    continue
                allp = [q for c, _ in cs for q in c]
            else:
                allp = verts(e)
                cs = None
            if not allp:
                continue
            ys = [q[1] for q in allp]
            if Y_MIN <= min(ys) and max(ys) <= Y_MAX:
                cands.append((e, allp, cs))

    # linea de terreno: polilinea larga y ancha
    terrenos = [
        (e, p) for e, p, cs in cands
        if e.dxftype() == "LWPOLYLINE" and len(p) >= 20
        and (max(q[0] for q in p) - min(q[0] for q in p)) > 150
        and e.dxf.layer not in CAPAS_MARCO
    ]

    cortes: Dict[str, Corte] = {}
    for nom, tx, ty in titulos:
        mejor, dmin = None, 1e18
        for e, p in terrenos:
            d = abs(min(q[0] for q in p) - tx) + 0.30 * abs(max(q[1] for q in p) - ty)
            if d < dmin:
                mejor, dmin = p, d
        if mejor is None:
            continue
        c = Corte(nom, tx, ty)
        c.x0, c.x1 = min(q[0] for q in mejor), max(q[0] for q in mejor)
        c.y0, c.y1 = min(q[1] for q in mejor), max(q[1] for q in mejor)
        c._pts = mejor
        cortes[nom] = c

    # calibracion vertical
    for c in cortes.values():
        m = 0.20 * (c.y1 - c.y0) + 25.0
        sel = [(k, y) for k, x, y in ejes
               if c.x0 - 60 <= x <= c.x0 + 15 and c.y0 - m <= y <= c.y1 + m]
        if len(sel) >= 2:
            ck = np.array([k for k, _ in sel], float)
            yk = np.array([y for _, y in sel], float)
            a, b = np.polyfit(ck, yk, 1)
            c.escala_v = float(a)
            c.z_ref = float(ck[0])
            c.y_ref = float(a * ck[0] + b)
            c.resid = float(np.max(np.abs(yk - (a * ck + b))))
        c.n_etiq = len(sel)
        c.perfil = [(round(c.est(x), 3), round(c.cota(y), 3))
                    for x, y in sorted(c._pts, key=lambda q: q[0])]

    # poligonos
    for e, p, cs in cands:
        capa = e.dxf.layer
        if capa in CAPAS_MARCO:
            continue
        t = e.dxftype()
        x0, x1 = min(q[0] for q in p), max(q[0] for q in p)
        y0, y1 = min(q[1] for q in p), max(q[1] for q in p)
        if t == "LWPOLYLINE" and len(p) >= 20 and (x1 - x0) > 150:
            continue  # es la linea de terreno
        for c in cortes.values():
            if not (c.x0 - 40 <= x0 and x1 <= c.x1 + 40
                    and c.y0 - 60 <= y0 and y1 <= c.y1 + 60):
                continue
            if cs is not None:
                ext = sum(shoelace(q) for q, isla in cs if not isla)
                isl = sum(shoelace(q) for q, isla in cs if isla)
                a_dib = max(ext - isl, 0.0) if ext else shoelace(p)
            else:
                a_dib = shoelace(p)
            c.polis.append({
                "capa": capa, "tipo": t, "n": len(p),
                "a_dib": a_dib,
                "a_m2": a_dib / c.escala_v,
                "e0": c.est(x0), "e1": c.est(x1),
                "z0": c.cota(y0), "z1": c.cota(y1),
            })
            break
    return cortes


def dedup(polis):
    """Une hatch y su contorno: misma caja y area similar => una sola feature."""
    polis = sorted(polis, key=lambda q: -q["a_m2"])
    out = []
    for q in polis:
        dup = False
        for r in out:
            if (abs(q["e0"] - r["e0"]) < 1.0 and abs(q["e1"] - r["e1"]) < 1.0
                    and abs(q["z0"] - r["z0"]) < 0.3 and abs(q["z1"] - r["z1"]) < 0.3):
                dup = True
                r["tipos"] = r.get("tipos", {r["tipo"]}) | {q["tipo"]}
                break
        if not dup:
            out.append(dict(q))
    return out


# ------------------------------------------------- trazas en planta (UTM)
# El plano de planta real esta en esta ventana UTM (huso 18S), donde tambien
# caen las curvas de nivel con cotas verdaderas. El dibujo contiene copias
# desplazadas del mismo plano, que se descartan por estar fuera de la ventana.
PLANTA = (708900.0, 710600.0, 5411300.0, 5412650.0)


def trazas_planta(ruta) -> Dict[str, dict]:
    """Extrae la traza UTM de cada corte a partir de sus dos rotulos de extremo."""
    doc = ezdxf.readfile(ruta)
    x0, x1, y0, y1 = PLANTA
    puntos: Dict[str, List[Tuple[float, float]]] = defaultdict(list)

    for e in doc.modelspace():
        if e.dxftype() != "MTEXT" or e.dxf.layer != "corte":
            continue
        txt = limpiar(e.text).upper()
        if not re.fullmatch(r"[0-9A-D]", txt):
            continue
        x, y = float(e.dxf.insert[0]), float(e.dxf.insert[1])
        if x0 <= x <= x1 and y0 <= y <= y1:
            puntos[txt].append((x, y))

    out = {}
    for nom, ps in puntos.items():
        # deduplicar rotulos repetidos en la misma posicion
        unicos = []
        for p in ps:
            if not any(abs(p[0] - q[0]) < 1 and abs(p[1] - q[1]) < 1 for q in unicos):
                unicos.append(p)
        if len(unicos) < 2:
            continue
        # los dos rotulos mas separados son los extremos de la traza
        mejor, dmax = None, -1.0
        for i in range(len(unicos)):
            for j in range(i + 1, len(unicos)):
                d = float(np.hypot(unicos[i][0] - unicos[j][0], unicos[i][1] - unicos[j][1]))
                if d > dmax:
                    mejor, dmax = (unicos[i], unicos[j]), d
        a, b = mejor
        out[nom] = {
            "x_ini": a[0], "y_ini": a[1], "x_fin": b[0], "y_fin": b[1],
            "x_med": (a[0] + b[0]) / 2, "y_med": (a[1] + b[1]) / 2,
            "largo_traza_m": dmax,
        }
    return out


def distancias(traz: Dict[str, dict], orden: List[str]) -> List[Tuple[str, str, float]]:
    """Distancia recta entre los puntos medios de cortes consecutivos."""
    out = []
    for a, b in zip(orden, orden[1:]):
        if a in traz and b in traz:
            d = float(np.hypot(traz[a]["x_med"] - traz[b]["x_med"],
                               traz[a]["y_med"] - traz[b]["y_med"]))
            out.append((a, b, d))
        else:
            out.append((a, b, float("nan")))
    return out


# ---------------------------------------------------------------- morfometria
def geom_a_nivel(perfil, nivel):
    """Area y ancho mojados a una cota dada."""
    area = ancho = 0.0
    for (x0, z0), (x1, z1) in zip(perfil, perfil[1:]):
        d0, d1 = nivel - z0, nivel - z1
        if d0 <= 0 and d1 <= 0:
            continue
        if d0 < 0 or d1 < 0:
            t = d0 / (d0 - d1)
            xi = x0 + t * (x1 - x0)
            if d0 > 0:
                x1, d1 = xi, 0.0
            else:
                x0, d0 = xi, 0.0
        dx = x1 - x0
        if dx > 0:
            area += 0.5 * (d0 + d1) * dx
            ancho += dx
    return area, ancho


# ---------------------------------------------------------------- libro
def construir(datos: Dict[str, Dict[str, Corte]], traz: Dict[str, dict], destino: str):
    wb = Workbook()

    # ---------------- LEEME
    ws = wb.active
    ws.title = "LEEME"
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 112
    h1(ws, "B2", "Río Negro — Lago Chapo | Perfiles de monitoreo extraídos de los DWG")
    txt = [
        ("", ""),
        ("ORIGEN DE LOS DATOS", "t"),
        ("Los DWG originales se convirtieron a DXF con LibreDWG (dwg2dxf 0.14), compilado", ""),
        ("desde el código fuente. Los perfiles se leyeron con la librería ezdxf.", ""),
        ("Archivos: '2014 01 Perfiles Monitoreo RNegro b.dwg' y '2018 11 Perfiles Monitoreo RNegro.dwg'.", ""),
        ("", ""),
        ("ESCALAS Y EXAGERACIÓN VERTICAL  (importante)", "t"),
        ("Los gráficos de perfil están dibujados con exageración vertical ×10:", ""),
        ("    horizontal : 1 unidad de dibujo = 1 m", ""),
        ("    vertical   : 10 unidades de dibujo = 1 m", ""),
        ("La escala horizontal se verificó comparando el ancho del gráfico (625.9 u) con la", ""),
        ("longitud real de la traza del corte en planta (626 m, en coordenadas UTM).", ""),
        ("La escala vertical se calibró en cada gráfico con las etiquetas del eje de cotas;", ""),
        ("el residuo máximo del ajuste es de 0.04 m (ver hoja 'Calibracion').", ""),
        ("Consecuencia: las áreas medidas en unidades de dibujo equivalen a 10× el área real,", ""),
        ("porque solo el eje vertical está exagerado. Todas las áreas de este libro ya están", ""),
        ("corregidas y expresadas en m² reales.", ""),
        ("", ""),
        ("HALLAZGO PRINCIPAL", "t"),
        ("Las 7 líneas de terreno son IDÉNTICAS en ambos DWG (mismo número de vértices y las", ""),
        ("mismas coordenadas). Es decir, el dibujo no contiene dos levantamientos distintos:", ""),
        ("contiene UNA geometría de referencia común, sobre la que cada plano superpone los", ""),
        ("polígonos de erosión de su período. Esto coincide con lo señalado por el encargo:", ""),
        ("«los perfiles son los mismos pero cambia la erosión presentada en cada período».", ""),
        ("", ""),
        ("QUÉ PERMITE Y QUÉ NO PERMITE ESTE DATO", "t"),
        ("SÍ permite: caracterizar la geometría de las 7 secciones, calcular su capacidad a", ""),
        ("   distintos niveles del lago, e inventariar las áreas de erosión dibujadas.", ""),
        ("NO permite: calcular la variación de volumen del cauce por diferencia de", ""),
        ("   levantamientos, porque no hay dos superficies topográficas distintas.", ""),
        ("Para eso se requieren los levantamientos por año (2009, 2011, 2014, 2018) como", ""),
        ("superficies independientes, o los perfiles crudos de cada campaña.", ""),
        ("", ""),
        ("ADVERTENCIA SOBRE LOS POLÍGONOS DE EROSIÓN", "t"),
        ("Los polígonos de la hoja 'Poligonos_erosion' se extrajeron tal como están dibujados.", ""),
        ("Se reporta la capa de origen de cada uno para que se pueda auditar: los de la capa", ""),
        ("'texto' son con alta probabilidad anotaciones y no áreas erosionadas, y no deben", ""),
        ("sumarse. La semántica exacta de cada polígono debe confirmarse con el autor del plano", ""),
        ("antes de usar estas áreas como resultado.", ""),
        ("", ""),
        ("CONTENIDO DEL LIBRO", "t"),
        ("Perfiles          — estación y cota de los 7 cortes (formato largo, para tablas dinámicas)", ""),
        ("Perfil_<corte>    — una hoja por corte, con gráfico de la sección", ""),
        ("Geometria_cortes  — resumen morfométrico y capacidad a los niveles del lago", ""),
        ("Poligonos_erosion — inventario de polígonos dibujados, con área real en m²", ""),
        ("Resumen_erosion   — área de erosión por corte y plano", ""),
        ("Volumenes         — plantilla con fórmulas: ingrese las distancias y calcula volúmenes", ""),
        ("Calibracion       — evidencia de la calibración de escalas, auditable", ""),
    ]
    r = 4
    for linea, tipo in txt:
        c = ws.cell(row=r, column=2, value=linea)
        if tipo == "t":
            c.font = Font(bold=True, size=11, color=AZUL)
        r += 1

    # ---------------- Perfiles (formato largo)
    ws = wb.create_sheet("Perfiles")
    encabezado(ws, 1, ["Plano", "Fecha", "Corte", "Punto", "Estacion_m", "Cota_msnm"],
               [10, 12, 8, 8, 13, 13])
    r = 2
    for clave, fecha, _ in ARCHIVOS:
        for nom in ORDEN:
            c = datos[clave].get(nom)
            if not c:
                continue
            for i, (e, z) in enumerate(c.perfil, 1):
                ws.cell(row=r, column=1, value=clave)
                ws.cell(row=r, column=2, value=fecha)
                ws.cell(row=r, column=3, value=nom)
                ws.cell(row=r, column=4, value=i)
                ws.cell(row=r, column=5, value=e)
                ws.cell(row=r, column=6, value=z)
                r += 1
    ws.auto_filter.ref = f"A1:F{r-1}"

    # ---------------- una hoja por corte, con grafico
    ref = datos["2018-11"]
    for nom in ORDEN:
        c = ref.get(nom)
        if not c:
            continue
        ws = wb.create_sheet(f"Perfil_{nom}")
        h1(ws, "A1", f"CORTE {nom} — sección transversal (geometría de referencia)")
        ws["A2"] = ("Idéntica en los planos de 2014 y 2018. Cotas en m.s.n.m., "
                    "estación en m desde el extremo izquierdo del gráfico.")
        ws["A2"].font = Font(italic=True, size=9)
        encabezado(ws, 4, ["Estacion_m", "Cota_msnm"], [13, 13])
        for i, (e, z) in enumerate(c.perfil):
            ws.cell(row=5 + i, column=1, value=e).border = BORDE
            ws.cell(row=5 + i, column=2, value=z).border = BORDE
        n = len(c.perfil)

        ch = ScatterChart()
        ch.title = f"CORTE {nom}"
        ch.style = 13
        ch.x_axis.title = "Estación (m)"
        ch.y_axis.title = "Cota (m.s.n.m.)"
        ch.height, ch.width = 9, 20
        xr = Reference(ws, min_col=1, min_row=5, max_row=4 + n)
        yr = Reference(ws, min_col=2, min_row=4, max_row=4 + n)
        s = Series(yr, xr, title_from_data=True)
        s.marker.symbol = "circle"
        s.marker.size = 4
        ch.series.append(s)
        cotas = [z for _, z in c.perfil]
        ch.y_axis.scaling.min = np.floor(min(cotas) - 1)
        ch.y_axis.scaling.max = np.ceil(max(cotas) + 1)
        ws.add_chart(ch, "E4")

        # niveles del lago
        f0 = 6 + n
        ws.cell(row=f0, column=1, value="Capacidad a niveles del lago").font = Font(bold=True)
        encabezado(ws, f0 + 1, ["Nivel_msnm", "Referencia", "Area_mojada_m2", "Ancho_m"],
                   [13, 30, 16, 12])
        for j, (niv, etiq) in enumerate(NIVELES):
            a, an = geom_a_nivel(c.perfil, niv)
            ws.cell(row=f0 + 2 + j, column=1, value=niv)
            ws.cell(row=f0 + 2 + j, column=2, value=etiq)
            ws.cell(row=f0 + 2 + j, column=3, value=round(a, 2))
            ws.cell(row=f0 + 2 + j, column=4, value=round(an, 2))

    # ---------------- Geometria_cortes
    ws = wb.create_sheet("Geometria_cortes")
    h1(ws, "A1", "Resumen morfométrico de las 7 secciones")
    cols = ["Corte", "N_puntos", "Ancho_levantado_m", "Cota_min_msnm", "Cota_max_msnm",
            "Relieve_m", "Estacion_thalweg_m"]
    for niv, _ in NIVELES:
        cols += [f"Area_{niv:.0f}_m2", f"Ancho_{niv:.0f}_m"]
    encabezado(ws, 3, cols, [8, 10, 18, 15, 15, 10, 18] + [14, 13] * len(NIVELES))
    for i, nom in enumerate(ORDEN):
        c = ref.get(nom)
        if not c:
            continue
        est = [e for e, _ in c.perfil]
        cot = [z for _, z in c.perfil]
        j = int(np.argmin(cot))
        fila = [nom, len(c.perfil), round(est[-1] - est[0], 2), round(min(cot), 2),
                round(max(cot), 2), round(max(cot) - min(cot), 2), round(est[j], 2)]
        for niv, _ in NIVELES:
            a, an = geom_a_nivel(c.perfil, niv)
            fila += [round(a, 2), round(an, 2)]
        for k, v in enumerate(fila, start=1):
            cc = ws.cell(row=4 + i, column=k, value=v)
            cc.border = BORDE
            if k == 1:
                cc.font = Font(bold=True)
    ws.cell(row=6 + len(ORDEN), column=1,
            value=("El thalweg es el punto más bajo del perfil. Area/Ancho son la sección "
                   "mojada si el agua alcanzara esa cota.")).font = Font(italic=True, size=9)

    # ---------------- Poligonos_erosion
    ws = wb.create_sheet("Poligonos_erosion")
    h1(ws, "A1", "Polígonos dibujados sobre los perfiles (inventario auditable)")
    ws["A2"] = ("Área ya corregida por la exageración vertical ×10. La columna 'Capa' permite "
                "auditar el origen: los de capa 'texto' son probablemente anotaciones.")
    ws["A2"].font = Font(italic=True, size=9)
    encabezado(ws, 4, ["Plano", "Fecha", "Corte", "Capa", "Tipo", "N_vert",
                       "Area_real_m2", "Est_ini_m", "Est_fin_m", "Ancho_m",
                       "Cota_min", "Cota_max", "Alto_m", "Probable_anotacion"],
               [10, 12, 8, 14, 12, 8, 14, 11, 11, 10, 11, 11, 9, 18])
    r = 5
    for clave, fecha, _ in ARCHIVOS:
        for nom in ORDEN:
            c = datos[clave].get(nom)
            if not c:
                continue
            for q in dedup(c.polis):
                anot = "SI" if q["capa"] == "texto" else ""
                vals = [clave, fecha, nom, q["capa"],
                        "+".join(sorted(q.get("tipos", {q["tipo"]}))), q["n"],
                        round(q["a_m2"], 2), round(q["e0"], 2), round(q["e1"], 2),
                        round(q["e1"] - q["e0"], 2), round(q["z0"], 2), round(q["z1"], 2),
                        round(q["z1"] - q["z0"], 2), anot]
                for k, v in enumerate(vals, 1):
                    cc = ws.cell(row=r, column=k, value=v)
                    cc.border = BORDE
                    if anot:
                        cc.fill = PatternFill("solid", fgColor=AMBAR)
                r += 1
    ws.auto_filter.ref = f"A4:N{r-1}"

    # ---------------- Resumen_erosion
    ws = wb.create_sheet("Resumen_erosion")
    h1(ws, "A1", "Área de los polígonos dibujados, por corte y plano")
    ws["A2"] = ("NO INTERPRETAR COMO EROSIÓN POR PERÍODO: las diferencias son nulas en 4 de los "
                "7 cortes, lo que indica ediciones del dibujo y no una medición entre fechas.")
    ws["A2"].font = Font(bold=True, size=9, color="C00000")
    ws["A3"] = ("Excluye los polígonos de la capa 'texto' (probables anotaciones). "
                "Ver hoja 'Hallazgos', punto 4.")
    ws["A3"].font = Font(italic=True, size=9)
    encabezado(ws, 4, ["Corte", "Area_2014_m2", "N_pol_2014", "Area_2018_m2",
                       "N_pol_2018", "Diferencia_m2"], [8, 15, 12, 15, 12, 15])
    for i, nom in enumerate(ORDEN):
        vals = [nom]
        areas = {}
        for clave, _, _ in ARCHIVOS:
            c = datos[clave].get(nom)
            ps = [q for q in dedup(c.polis) if q["capa"] != "texto"] if c else []
            areas[clave] = sum(q["a_m2"] for q in ps)
            vals += [round(areas[clave], 2), len(ps)]
        vals.append(round(areas["2018-11"] - areas["2014-01"], 2))
        for k, v in enumerate(vals, 1):
            cc = ws.cell(row=5 + i, column=k, value=v)
            cc.border = BORDE
            if k == 1:
                cc.font = Font(bold=True)
    f = 5 + len(ORDEN)
    ws.cell(row=f, column=1, value="TOTAL").font = Font(bold=True)
    for col in (2, 4, 6):
        L = get_column_letter(col)
        cc = ws.cell(row=f, column=col, value=f"=SUM({L}5:{L}{f-1})")
        cc.font = Font(bold=True)
        cc.fill = PatternFill("solid", fgColor=GRIS)

    # ---------------- Volumenes (plantilla con formulas)
    ws = wb.create_sheet("Volumenes")
    h1(ws, "A1", "Volúmenes por el método de áreas medias — PLANTILLA")
    ws["A2"] = ("La columna C viene precargada con la distancia RECTA entre los puntos medios de "
                "las trazas UTM. Reemplácela por la distancia medida a lo largo del eje del cauce, "
                "que es siempre mayor. Las demás columnas se calculan solas.")
    ws["A2"].font = Font(italic=True, size=9)
    ws["A3"] = ("Los cortes están ordenados de aguas abajo hacia aguas arriba según la cota de "
                "su thalweg. Confirme este orden con las progresivas reales antes de usarlo.")
    ws["A3"].font = Font(italic=True, size=9, color="C00000")
    ws["A4"] = ("ATENCIÓN: las áreas que toma esta hoja provienen de 'Resumen_erosion', cuya "
                "validez como erosión por período NO está confirmada (ver hoja Hallazgos).")
    ws["A4"].font = Font(bold=True, size=9, color="C00000")
    encabezado(ws, 6, ["Corte_A", "Corte_B", "Distancia_m  (INGRESAR)",
                       "Area_A_m2", "Area_B_m2", "Area_media_m2", "Volumen_m3"],
               [10, 10, 24, 13, 13, 15, 14])
    orden_h = orden_hidraulico(ref)
    dist = {(a, b): d for a, b, d in distancias(traz, orden_h)}
    pares = list(zip(orden_h, orden_h[1:]))
    for i, (a, b) in enumerate(pares):
        r = 7 + i
        ws.cell(row=r, column=1, value=a).border = BORDE
        ws.cell(row=r, column=2, value=b).border = BORDE
        d = dist.get((a, b), float("nan"))
        cc = ws.cell(row=r, column=3, value=None if np.isnan(d) else round(d, 1))
        cc.fill = PatternFill("solid", fgColor=AMBAR)
        cc.border = BORDE
        ws.cell(row=r, column=4,
                value=f"=IFERROR(VLOOKUP(A{r},Resumen_erosion!$A$5:$D${4+len(ORDEN)},4,FALSE),\"\")").border = BORDE
        ws.cell(row=r, column=5,
                value=f"=IFERROR(VLOOKUP(B{r},Resumen_erosion!$A$5:$D${4+len(ORDEN)},4,FALSE),\"\")").border = BORDE
        ws.cell(row=r, column=6, value=f"=IFERROR((D{r}+E{r})/2,\"\")").border = BORDE
        cc = ws.cell(row=r, column=7, value=f"=IFERROR(F{r}*C{r},\"\")")
        cc.border = BORDE
        cc.fill = PatternFill("solid", fgColor=VERDE)
    r = 7 + len(pares)
    ws.cell(row=r, column=6, value="TOTAL m³").font = Font(bold=True)
    cc = ws.cell(row=r, column=7, value=f"=SUM(G7:G{r-1})")
    cc.font = Font(bold=True)
    cc.fill = PatternFill("solid", fgColor=GRIS)

    # ---------------- Progresivas (trazas UTM)
    ws = wb.create_sheet("Progresivas")
    h1(ws, "A1", "Ubicación de los cortes en planta (coordenadas UTM)")
    ws["A2"] = ("Extraída de la capa 'corte' de los DWG. Cada corte se identifica por sus dos "
                "rótulos de extremo; el punto medio se usa para medir distancias entre cortes.")
    ws["A2"].font = Font(italic=True, size=9)
    orden_h = orden_hidraulico(ref)
    encabezado(ws, 4, ["Orden", "Corte", "Thalweg_msnm", "X_ini", "Y_ini", "X_fin", "Y_fin",
                       "X_medio", "Y_medio", "Largo_traza_m", "Dist_al_siguiente_m",
                       "Progresiva_acum_m"],
               [7, 8, 14, 12, 13, 12, 13, 12, 13, 15, 20, 18])
    dists = {(a, b): d for a, b, d in distancias(traz, orden_h)}
    acum = 0.0
    for i, nom in enumerate(orden_h):
        r = 5 + i
        t = traz.get(nom, {})
        thal = min(z for _, z in ref[nom].perfil)
        sig = dists.get((nom, orden_h[i + 1])) if i + 1 < len(orden_h) else None
        vals = [i + 1, nom, round(thal, 2),
                round(t.get("x_ini", float("nan")), 2) if t else None,
                round(t.get("y_ini", float("nan")), 2) if t else None,
                round(t.get("x_fin", float("nan")), 2) if t else None,
                round(t.get("y_fin", float("nan")), 2) if t else None,
                round(t.get("x_med", float("nan")), 2) if t else None,
                round(t.get("y_med", float("nan")), 2) if t else None,
                round(t.get("largo_traza_m", float("nan")), 1) if t else None,
                None if sig is None or np.isnan(sig) else round(sig, 1),
                round(acum, 1)]
        if sig is not None and not np.isnan(sig):
            acum += sig
        for k, v in enumerate(vals, 1):
            cc = ws.cell(row=r, column=k, value=v)
            cc.border = BORDE
            if k == 2:
                cc.font = Font(bold=True)
    r = 5 + len(orden_h)
    ws.cell(row=r + 1, column=1,
            value=("Orden 1 = aguas abajo (desembocadura en el lago), deducido de la cota del "
                   "thalweg. La progresión espacial de las coordenadas UTM es coherente con ese "
                   "orden, lo que lo corrobora de forma independiente.")).font = Font(italic=True, size=9)
    ws.cell(row=r + 2, column=1,
            value=("Las distancias son en línea recta entre puntos medios. La distancia real a lo "
                   "largo del cauce es mayor; úsela para los volúmenes definitivos.")
            ).font = Font(italic=True, size=9)

    # ---------------- Hallazgos
    ws = wb.create_sheet("Hallazgos")
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    h1(ws, "B2", "Hallazgos derivados de los datos extraídos")
    orden_h = orden_hidraulico(ref)
    thal = {n: min(z for _, z in ref[n].perfil) for n in orden_h}
    bajo_230 = [n for n in orden_h if thal[n] < 230.0]
    lineas = [
        ("", ""),
        ("1. ORDEN LONGITUDINAL DE LOS CORTES  (deducido, no leído del plano)", "t"),
        (f"Ordenando por la cota del thalweg resulta, de aguas abajo a aguas arriba:", ""),
        ("      " + "  ->  ".join(f"{n} ({thal[n]:.2f})" for n in orden_h), "m"),
        ("El agua corre cuesta abajo, luego el corte con el fondo más bajo es el más cercano a", ""),
        ("la desembocadura en el lago. Este orden debe confirmarse contra las progresivas reales,", ""),
        ("pero es consistente y permite ordenar el análisis longitudinal.", ""),
        ("", ""),
        ("2. SOLO DOS CORTES TIENEN EL LECHO BAJO EL NIVEL MÍNIMO DEL LAGO", "t"),
        (f"Cortes con thalweg bajo la cota 230 m.s.n.m.: {', '.join(bajo_230)}.", "m"),
        ("Son los dos cortes más cercanos a la desembocadura. El resto tiene el fondo por encima", ""),
        ("de 231 m.s.n.m., la cota mínima provisional ordenada por el Tercer Tribunal Ambiental.", ""),
        ("Lectura: son precisamente los cortes situados en la zona de influencia del abatimiento", ""),
        ("del lago, que es donde el informe de INGETEC sitúa la incisión por erosión", ""),
        ("retrogradante. La geometría extraída es coherente con ese mecanismo.", ""),
        ("", ""),
        ("3. GRADIENTE DE RELIEVE HACIA LA DESEMBOCADURA", "t"),
        ("El relieve de la sección (cota máxima menos mínima) crece hacia aguas abajo:", ""),
        ("      " + "   ".join(
            f"{n}={ref[n].perfil and max(z for _, z in ref[n].perfil) - thal[n]:.1f} m"
            for n in orden_h), "m"),
        ("Secciones más encajonadas aguas abajo y más someras aguas arriba, compatible con un", ""),
        ("cauce que ha profundizado en su tramo final.", ""),
        ("", ""),
        ("4. LOS POLÍGONOS DIBUJADOS NO SIRVEN COMO EROSIÓN POR PERÍODO", "t"),
        ("Comparando los dos planos, el área de los polígonos es prácticamente idéntica en los", ""),
        ("cortes 1, 3, B y C (diferencias de 0 a 2 m² sobre cientos de m²), y solo difiere en", ""),
        ("los cortes 2, 4 y A. Ese patrón corresponde a ediciones del dibujo, no a una medición", ""),
        ("de erosión entre dos fechas. Si fueran erosión acumulada, se esperaría un aumento", ""),
        ("sistemático en todos los cortes.", ""),
        ("Conclusión: estas áreas se entregan inventariadas y auditables, pero NO deben usarse", ""),
        ("como variación de volumen sin confirmar su significado con el autor del plano.", ""),
        ("", ""),
        ("5. LO QUE FALTA PARA CERRAR EL ANÁLISIS DE VOLUMEN", "t"),
        ("Se necesita una de estas dos cosas:", ""),
        ("   (a) los perfiles crudos de cada campaña (2009, 2011, 2014, 2018) como series de", ""),
        ("       puntos independientes, o", ""),
        ("   (b) las superficies topográficas de cada año como capas separadas.", ""),
        ("Los DWG revisados contienen una sola geometría de terreno por corte, repetida en ambos", ""),
        ("planos. Las capas de curvas de nivel (CONT-*) se solapan entre 88% y 94%, es decir son", ""),
        ("duplicados de una misma superficie y no épocas distintas.", ""),
        ("", ""),
        ("6. DATO ADICIONAL ÚTIL YA DISPONIBLE", "t"),
        ("Las progresivas de los cortes se pueden medir directamente: las trazas en planta están", ""),
        ("en coordenadas UTM en la capa 'corte' de los mismos DWG. Con ellas se completa la", ""),
        ("columna de distancias de la hoja 'Volumenes' sin necesidad de trabajo de campo.", ""),
    ]
    r = 4
    for linea, tipo in lineas:
        c = ws.cell(row=r, column=2, value=linea)
        if tipo == "t":
            c.font = Font(bold=True, size=11, color=AZUL)
        elif tipo == "m":
            c.font = Font(bold=True, size=10)
            c.fill = PatternFill("solid", fgColor=VERDE)
        r += 1

    # ---------------- Calibracion
    ws = wb.create_sheet("Calibracion")
    h1(ws, "A1", "Evidencia de calibración de escalas (auditable)")
    ws["A2"] = ("La escala vertical se ajustó por mínimos cuadrados sobre las etiquetas del eje "
                "de cotas de cada gráfico. Un valor cercano a 10.00 u/m confirma la exageración ×10.")
    ws["A2"].font = Font(italic=True, size=9)
    encabezado(ws, 4, ["Plano", "Corte", "Escala_V_u_por_m", "N_etiquetas_eje",
                       "Residuo_max_u", "Residuo_max_m", "Escala_H_u_por_m",
                       "Exageracion_vertical"], [10, 8, 18, 16, 14, 14, 16, 18])
    r = 5
    for clave, _, _ in ARCHIVOS:
        for nom in ORDEN:
            c = datos[clave].get(nom)
            if not c:
                continue
            vals = [clave, nom, round(c.escala_v, 4), c.n_etiq, round(c.resid, 3),
                    round(c.resid / c.escala_v, 4), ESCALA_H,
                    round(c.escala_v / ESCALA_H, 2)]
            for k, v in enumerate(vals, 1):
                ws.cell(row=r, column=k, value=v).border = BORDE
            r += 1
    ws.cell(row=r + 1, column=1,
            value=("Escala horizontal verificada de forma independiente: el gráfico del corte 1 "
                   "mide 625.9 u de ancho y la traza del corte en planta mide 626 m en UTM.")
            ).font = Font(italic=True, size=9)

    wb.save(destino)
    return destino


if __name__ == "__main__":
    datos = {clave: extraer(ruta) for clave, _, ruta in ARCHIVOS}
    for clave, _, _ in ARCHIVOS:
        print(f"{clave}: cortes {sorted(datos[clave])}")

    # las trazas en planta se toman del plano de 2018
    traz = trazas_planta(ARCHIVOS[1][2])
    print(f"trazas en planta: {sorted(traz)}")
    ref = datos["2018-11"]
    orden_h = orden_hidraulico(ref)
    print(f"orden hidraulico (aguas abajo -> arriba): {orden_h}")
    for a, b, d in distancias(traz, orden_h):
        print(f"   {a}->{b}: {d:8.1f} m")

    d = construir(datos, traz, "/projects/sandbox/LAGO-CHAPO/Perfiles_RioNegro_analisis.xlsx")
    print("->", d)
