"""Genera el Excel de comparacion entre periodos y las figuras del analisis."""
import sys
from datetime import date

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, "/projects/build")
from analisis_periodos import (PERIODOS, ETIQ, ORDEN_H, DIST, bandas_por_corte,
                               vol_areas_medias)

PROG = {"1": 0, "A": 154.3, "2": 662.3, "B": 791.2, "3": 908.2, "4": 1191.9, "C": 1591.4}
THAL = {"1": 225.69, "A": 227.21, "2": 231.35, "B": 232.62, "3": 235.06,
        "4": 239.81, "C": 243.62}

AZUL, GRIS, AMBAR, VERDE, ROJO = "1F4E79", "D9D9D9", "FFF2CC", "E2EFDA", "C00000"
BORDE = Border(*[Side(style="thin", color="BFBFBF")] * 4)


def h1(ws, celda, txt):
    ws[celda].value = txt
    ws[celda].font = Font(bold=True, size=13, color=AZUL)


def enc(ws, fila, cols, anchos=None):
    for i, t in enumerate(cols, 1):
        c = ws.cell(row=fila, column=i, value=t)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDE
    ws.freeze_panes = ws.cell(row=fila + 1, column=1)
    for i, w in enumerate(anchos or [], 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def meses(p):
    return (p["fin"] - p["ini"]).days / 30.44


# ------------------------------------------------------------------ figuras
def figuras(area):
    etq = [ETIQ[p["n"]] for p in PERIODOS]
    vol = [p["vol"] for p in PERIODOS]
    mes = [meses(p) for p in PERIODOS]
    tasa = [v / m * 12 for v, m in zip(vol, mes)]
    acum = np.cumsum(vol)

    # --- Figura 1: volumen, tasa y acumulado
    fig, ax = plt.subplots(3, 1, figsize=(13, 13))
    x = np.arange(len(etq))

    ax[0].bar(x, vol, color="#1F4E79")
    ax[0].set_title("Volumen erosionado por período", fontsize=13, fontweight="bold")
    ax[0].set_ylabel("Volumen (m³)")
    for i, v in enumerate(vol):
        ax[0].text(i, v, f"{v:,.0f}".replace(",", "."), ha="center", va="bottom", fontsize=8)
    ax[0].annotate("el primer período concentra el 53% del total",
                   xy=(0, vol[0]), xytext=(2.2, vol[0] * 0.85), fontsize=9, color=ROJO,
                   arrowprops=dict(arrowstyle="->", color=ROJO))

    ax[1].bar(x, tasa, color="#C55A11")
    ax[1].set_title("Tasa de erosión — es la comparación correcta, porque los períodos "
                    "duran distinto (6 a 17 meses)", fontsize=12, fontweight="bold")
    ax[1].set_ylabel("Tasa (m³/año)")
    ax[1].set_yscale("log")
    for i, v in enumerate(tasa):
        ax[1].text(i, v, f"{v:,.0f}".replace(",", "."), ha="center", va="bottom", fontsize=8)
    ax[1].annotate(f"cae por un factor de {tasa[0]/tasa[-1]:.0f}\n(escala logarítmica)",
                   xy=(0.5, tasa[0] * 0.5), fontsize=9, color=ROJO)

    ax[2].plot(x, acum, "-o", color="#1F4E79", lw=2)
    ax[2].fill_between(x, 0, acum, alpha=0.15, color="#1F4E79")
    ax[2].set_title("Volumen acumulado — la curva se aplana: el sistema se está estabilizando",
                    fontsize=12, fontweight="bold")
    ax[2].set_ylabel("Acumulado (m³)")
    ax[2].text(len(etq) - 1, acum[-1], f"  {acum[-1]:,.0f} m³".replace(",", "."),
               va="center", fontsize=10, fontweight="bold")

    for a in ax:
        a.set_xticks(x)
        a.set_xticklabels(etq, rotation=45, ha="right", fontsize=9)
        a.grid(alpha=0.3, axis="y")
        a.margins(x=0.02)
    fig.suptitle("Río Negro — Erosión por período, marzo 2009 a noviembre 2018",
                 fontsize=15, fontweight="bold", y=0.998)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    fig.savefig("/projects/sandbox/LAGO-CHAPO/comparacion_periodos.png", dpi=140)
    plt.close(fig)

    # --- Figura 2: donde ocurre la erosion en el tiempo (migracion del frente)
    M = np.zeros((len(ORDEN_H), len(PERIODOS)))
    for i, c in enumerate(ORDEN_H):
        for j, p in enumerate(PERIODOS):
            M[i, j] = area.get((c, p["n"]), 0.0)

    fig, (axa, axb) = plt.subplots(1, 2, figsize=(17, 6.5),
                                   gridspec_kw={"width_ratios": [1.25, 1]})
    Mm = np.ma.masked_where(M <= 0, M)
    im = axa.imshow(Mm, aspect="auto", cmap="YlOrRd", origin="upper")
    axa.set_xticks(range(len(PERIODOS)))
    axa.set_xticklabels(etq, rotation=45, ha="right", fontsize=9)
    axa.set_yticks(range(len(ORDEN_H)))
    axa.set_yticklabels([f"{c}  (prog. {PROG[c]:.0f} m)" for c in ORDEN_H], fontsize=9)
    axa.set_ylabel("Corte — aguas abajo arriba, aguas arriba abajo", fontsize=10)
    axa.set_title("Dónde hubo erosión, período por período\n"
                  "Gris = sin erosión registrada en ese corte y período",
                  fontsize=12, fontweight="bold")
    for i in range(len(ORDEN_H)):
        for j in range(len(PERIODOS)):
            if M[i, j] > 0:
                axa.text(j, i, f"{M[i,j]:.0f}", ha="center", va="center", fontsize=7.5)
    plt.colorbar(im, ax=axa, label="Área de banda erosionada (m²)")
    axa.set_facecolor("#F2F2F2")

    # ventana de actividad de cada corte: primer y ultimo periodo con erosion
    axb.set_title("Ventana de actividad de cada corte\n"
                  "Aguas abajo se apaga tras 2013; el corte 4 se activa desde 2012",
                  fontsize=11.5, fontweight="bold")
    for i, c in enumerate(ORDEN_H):
        act = [j for j in range(len(PERIODOS)) if M[i, j] > 0]
        if not act:
            axb.text(0.2, i, "sin erosión registrada", va="center", fontsize=9, color="gray")
            continue
        axb.barh(i, act[-1] - act[0] + 0.8, left=act[0] - 0.4, height=0.5,
                 color="#BFBFBF", zorder=1)
        tam = M[i, act] / M.max() * 320 + 25
        axb.scatter(act, [i] * len(act), s=tam, color="#C55A11", zorder=3,
                    edgecolor="white", lw=0.8)
    axb.set_yticks(range(len(ORDEN_H)))
    axb.set_yticklabels([f"{c} ({PROG[c]:.0f} m)" for c in ORDEN_H], fontsize=9)
    axb.invert_yaxis()
    axb.set_xticks(range(len(PERIODOS)))
    axb.set_xticklabels(etq, rotation=45, ha="right", fontsize=8.5)
    axb.set_xlim(-0.8, len(PERIODOS) - 0.2)
    axb.grid(alpha=0.3, axis="x")
    axb.set_ylabel("Corte (progresiva desde la desembocadura)", fontsize=10)
    axb.text(0.40, 0.52,
             "El tamaño del punto es proporcional al área erosionada.\n"
             "El patrón es compatible con un frente que avanza hacia\n"
             "aguas arriba, pero con 7 cortes y varios vacíos NO\n"
             "permite estimar una velocidad fiable.",
             transform=axb.transAxes, fontsize=8.5, va="center",
             bbox=dict(boxstyle="round", fc="#FFF2CC", ec="#BFBFBF"))
    fig.tight_layout()
    fig.savefig("/projects/sandbox/LAGO-CHAPO/migracion_frente_erosion.png", dpi=140)
    plt.close(fig)

    # --- Figura 3: retroceso de la ladera en el corte 1
    fig, ax = plt.subplots(figsize=(12, 6))
    cmap = plt.cm.viridis(np.linspace(0, 0.92, len(PERIODOS)))
    hay = False
    for j, p in enumerate(PERIODOS):
        k = ("est", "1", p["n"])
        if k not in area:
            continue
        hay = True
        for e0, e1 in area[k]:
            ax.barh(j, e1 - e0, left=e0, height=0.72, color=cmap[j],
                    edgecolor="white", lw=0.6)
        e0 = min(q[0] for q in area[k])
        ax.text(e0 - 4, j, ETIQ[p["n"]], ha="right", va="center", fontsize=9)
    if hay:
        ax.axvline(262.4, color=ROJO, ls="--", lw=1.5)
        ax.text(264, len(PERIODOS) * 0.5, "eje del cauce\n(thalweg, est. 262 m)",
                color=ROJO, fontsize=9, va="center")
        ax.set_yticks([])
        ax.invert_yaxis()
        ax.set_xlabel("Estación en el perfil (m)", fontsize=10)
        ax.set_title("CORTE 1 — retroceso progresivo de la ladera\n"
                     "Cada banda es el material perdido en un período; el frente avanza "
                     "alejándose del cauce", fontsize=12, fontweight="bold")
        ax.grid(alpha=0.3, axis="x")
    fig.tight_layout()
    fig.savefig("/projects/sandbox/LAGO-CHAPO/retroceso_ladera_corte1.png", dpi=140)
    plt.close(fig)
    print("figuras generadas")


# ------------------------------------------------------------------ excel
def excel(area, destino):
    wb = Workbook()

    ws = wb.active
    ws.title = "LEEME"
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 108
    h1(ws, "B2", "Río Negro — Comparación de la erosión entre períodos (2009–2018)")
    for i, (t, k) in enumerate([
        ("", ""),
        ("DE DÓNDE SALEN ESTOS DATOS", "t"),
        ("De la leyenda del plano de 2018, que está en el paperspace del DWG (Layout1) y no en", ""),
        ("el modelo. Ahí el levantamiento declara, para cada uno de los 11 períodos, el color con", ""),
        ("que se dibujó, la superficie afectada en hectáreas y el volumen erosionado en m³.", ""),
        ("El perfil de referencia es la 'SECCION ORIGINAL RIO SEGUN TOPOGRAFIA MARZO 2009'.", ""),
        ("Plano: 'PERFILES TRANSVERSALES Y SUPERFICIES', lámina 2 de 2, 23-11-2018, COLBÚN S.A.", ""),
        ("", ""),
        ("LA ESCALA DEL PLANO CONFIRMA LA EXAGERACIÓN VERTICAL", "t"),
        ("El rótulo dice 'Esc Vert 1/300, Hrz 1/3000'. La razón 3000/300 = 10 es exactamente la", ""),
        ("exageración vertical ×10 que se había deducido midiendo el dibujo. Queda confirmada por", ""),
        ("dos vías independientes.", ""),
        ("", ""),
        ("QUÉ TIPO DE EROSIÓN ES", "t"),
        ("Es erosión LATERAL de las márgenes, no profundización del fondo. Se ve en dos cosas:", ""),
        ("las bandas de cada período están dibujadas una al lado de otra avanzando hacia los", ""),
        ("costados, y el volumen dividido por la superficie da entre 7 y 13 m, que coincide con la", ""),
        ("altura de las laderas de los perfiles. O sea: la ladera retrocede en toda su altura.", ""),
        ("", ""),
        ("CÓMO COMPARAR BIEN LOS PERÍODOS", "t"),
        ("Los períodos NO duran lo mismo: van de 5,9 a 17 meses. Comparar los volúmenes crudos", ""),
        ("entre sí es un error, porque un período largo acumula más solo por ser largo.", ""),
        ("Hay que comparar la TASA (m³/año), que es la columna que normaliza por duración.", ""),
        ("", ""),
        ("LOS DOS RESULTADOS PRINCIPALES", "t"),
        ("1) La tasa se desploma: de 752.060 m³/año en el primer período a 18.467 m³/año en el", ""),
        ("   último, un factor de 41. Aun descartando el primer período, cae de 86.477 a 18.467.", ""),
        ("   Es la firma de un sistema que se relaja hacia un nuevo equilibrio: el descenso del", ""),
        ("   nivel base disparó la erosión, y al erosionar el río fue reduciendo su propia", ""),
        ("   pendiente, de modo que el proceso se frena solo. Concuerda con el informe de INGETEC,", ""),
        ("   que observa que el proceso 'no parece estar activo o en crecimiento'.", ""),
        ("2) La erosión cambia de lugar con el tiempo. Los cortes 2, 3 y B solo registran erosión", ""),
        ("   en 2009-2010; el corte 1 la registra hasta 2013 y después se apaga; y el corte 4, que", ""),
        ("   está 1.192 m aguas arriba, recién se activa en 2012 y llega a su máximo en 2015-2016.", ""),
        ("   El corte C, el más aguas arriba, no registra erosión en ningún período.", ""),
        ("   Este patrón es COMPATIBLE con un frente que avanza hacia aguas arriba, pero no lo", ""),
        ("   demuestra: el corte A permanece activo casi todo el período y hay muchos vacíos en la", ""),
        ("   matriz, de modo que con 7 cortes no se puede estimar una velocidad de avance fiable.", ""),
        ("   Se calculó el centroide de la erosión por período y resulta errático, no monótono.", ""),
        ("   Para sostener la hipótesis del frente migrando hacen falta más secciones intermedias.", ""),
        ("", ""),
        ("SOBRE EL MÉTODO DE CÁLCULO DEL VOLUMEN", "t"),
        ("La evidencia apunta a que NO se usó áreas medias ni prismoidal entre secciones, sino", ""),
        ("superficie en planta × altura de la ladera. Razón: el plano informa hectáreas para cada", ""),
        ("período, que es una medida en planta, y el cociente volumen/superficie da valores de", ""),
        ("altura de talud coherentes (7 a 13 m). Ver la hoja 'Metodo_volumen'.", ""),
        ("Para confirmarlo hay que pedir la memoria de cálculo. Es una pregunta legítima y", ""),
        ("necesaria, porque el método cambia el resultado.", ""),
        ("", ""),
        ("LO QUE SIGUE: CORRELACIÓN CON EL NIVEL DEL LAGO", "t"),
        ("La hoja 'Nivel_lago' está preparada para eso. Se pegan los niveles diarios y las", ""),
        ("fórmulas cuentan, para cada período, cuántos días el lago estuvo bajo las cotas 231 y", ""),
        ("230. Después se grafica ese número contra la tasa de erosión del período.", ""),
        ("Si la correlación aparece, es la evidencia que conecta la operación de la central con", ""),
        ("el daño, y la que sustenta técnicamente la cota mínima de estabilidad.", ""),
        ("", ""),
        ("ADVERTENCIA SOBRE EL PRIMER PERÍODO", "t"),
        ("Marzo-septiembre 2009 declara 378.830 m³ en 6 meses: 3,5 veces el segundo período más", ""),
        ("alto y el 53% de todo el total. Puede ser real (fue el primer levantamiento tras años de", ""),
        ("operación sin monitoreo, así que probablemente arrastra erosión anterior), pero conviene", ""),
        ("verificarlo y reportar los resultados con y sin él.", ""),
    ]):
        c = ws.cell(row=4 + i, column=2, value=t)
        if k == "t":
            c.font = Font(bold=True, size=11, color=AZUL)

    # ---- Periodos
    ws = wb.create_sheet("Periodos")
    h1(ws, "A1", "Erosión por período — tabla base de la comparación")
    ws["A2"] = ("Compare la columna 'Tasa_m3_año', no el volumen crudo: los períodos duran "
                "entre 5,9 y 17 meses.")
    ws["A2"].font = Font(italic=True, size=9, color=ROJO)
    enc(ws, 4, ["N", "Periodo", "Inicio", "Fin", "Meses", "Area_ha", "Volumen_m3",
                "Tasa_m3_mes", "Tasa_m3_año", "Acumulado_m3", "Espesor_medio_m",
                "Pct_del_total"],
        [5, 15, 12, 12, 8, 10, 13, 13, 13, 14, 15, 13])
    total = sum(p["vol"] for p in PERIODOS)
    acum = 0.0
    for i, p in enumerate(PERIODOS):
        r = 5 + i
        m = meses(p)
        acum += p["vol"]
        vals = [p["n"], ETIQ[p["n"]], p["ini"].isoformat(), p["fin"].isoformat(),
                round(m, 1), p["ha"], p["vol"], round(p["vol"] / m), round(p["vol"] / m * 12),
                round(acum), round(p["vol"] / (p["ha"] * 10000), 1),
                round(p["vol"] / total * 100, 1)]
        for k, v in enumerate(vals, 1):
            c = ws.cell(row=r, column=k, value=v)
            c.border = BORDE
            if k == 9:
                c.fill = PatternFill("solid", fgColor=VERDE)
        if p["n"] == 1:
            for k in range(1, 13):
                ws.cell(row=r, column=k).fill = PatternFill("solid", fgColor=AMBAR)
    r = 5 + len(PERIODOS)
    ws.cell(row=r, column=2, value="TOTAL").font = Font(bold=True)
    for col in (6, 7):
        L = get_column_letter(col)
        c = ws.cell(row=r, column=col, value=f"=SUM({L}5:{L}{r-1})")
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor=GRIS)
    ws.cell(row=r + 2, column=2,
            value="Fila ámbar = primer período, revisar (53% del total). "
                  "Espesor medio = volumen / superficie, debe parecerse a la altura del talud."
            ).font = Font(italic=True, size=9)

    ch = BarChart()
    ch.title = "Tasa de erosión por período (m³/año)"
    ch.y_axis.title = "m³/año"
    ch.height, ch.width = 9, 24
    ch.add_data(Reference(ws, min_col=9, min_row=4, max_row=4 + len(PERIODOS)),
                titles_from_data=True)
    ch.set_categories(Reference(ws, min_col=2, min_row=5, max_row=4 + len(PERIODOS)))
    ws.add_chart(ch, "N4")

    ch2 = LineChart()
    ch2.title = "Volumen acumulado (m³)"
    ch2.y_axis.title = "m³"
    ch2.height, ch2.width = 9, 24
    ch2.add_data(Reference(ws, min_col=10, min_row=4, max_row=4 + len(PERIODOS)),
                 titles_from_data=True)
    ch2.set_categories(Reference(ws, min_col=2, min_row=5, max_row=4 + len(PERIODOS)))
    ws.add_chart(ch2, "N24")

    # ---- Bandas por corte y periodo
    ws = wb.create_sheet("Erosion_por_corte")
    h1(ws, "A1", "Dónde ocurrió la erosión: área de banda por corte y período (m²)")
    ws["A2"] = ("Cortes ordenados de aguas abajo hacia aguas arriba. Se ve el frente migrando: "
                "los de arriba de la tabla se apagan y el corte 4 se activa después.")
    ws["A2"].font = Font(italic=True, size=9)
    enc(ws, 4, ["Corte", "Progresiva_m", "Thalweg_msnm"] + [ETIQ[p["n"]] for p in PERIODOS]
        + ["Total_m2", "Primer_periodo", "Ultimo_periodo"],
        [8, 13, 13] + [12] * len(PERIODOS) + [11, 15, 15])
    for i, c in enumerate(ORDEN_H):
        r = 5 + i
        ws.cell(row=r, column=1, value=c).font = Font(bold=True)
        ws.cell(row=r, column=2, value=PROG[c])
        ws.cell(row=r, column=3, value=THAL[c])
        act = []
        for j, p in enumerate(PERIODOS):
            a = area.get((c, p["n"]), 0.0)
            cc = ws.cell(row=r, column=4 + j, value=round(a, 1) if a else None)
            cc.border = BORDE
            if a:
                act.append(ETIQ[p["n"]])
                cc.fill = PatternFill("solid", fgColor=AMBAR)
        L0 = get_column_letter(4)
        L1 = get_column_letter(3 + len(PERIODOS))
        ws.cell(row=r, column=4 + len(PERIODOS), value=f"=SUM({L0}{r}:{L1}{r})")
        ws.cell(row=r, column=5 + len(PERIODOS), value=act[0] if act else "sin erosión")
        ws.cell(row=r, column=6 + len(PERIODOS), value=act[-1] if act else "sin erosión")

    # ---- Metodo de volumen
    ws = wb.create_sheet("Metodo_volumen")
    h1(ws, "A1", "¿Con qué método se calcularon los volúmenes?")
    for i, t in enumerate([
        "Se probó recalcular cada período por ÁREAS MEDIAS, usando las áreas de banda medidas",
        "en los perfiles y las distancias entre cortes obtenidas de las trazas UTM:",
        "        V = (A₁ + A₂) / 2 × L",
        "El resultado no reproduce los volúmenes del plano, salvo en el período 2 (−4,4%).",
        "",
        "La explicación más probable es que el volumen se calculó como superficie en planta ×",
        "altura de la ladera, no por secciones. Dos indicios lo respaldan: el plano informa la",
        "superficie de cada período en HECTÁREAS, que es una medida en planta; y el cociente",
        "volumen/superficie da entre 7 y 13 m, coherente con la altura de los taludes.",
        "",
        "También influye que las bandas dibujadas no cubren los 7 cortes en todos los períodos,",
        "de modo que el recálculo por secciones queda incompleto por construcción.",
        "",
        "QUÉ PEDIR: la memoria de cálculo. La pregunta concreta es si el volumen se obtuvo por",
        "áreas medias entre secciones, por el método prismoidal, o por superficie en planta por",
        "altura media de talud. El método cambia el resultado y hay que declararlo en el informe.",
    ]):
        ws.cell(row=3 + i, column=1, value=t)
    ws.column_dimensions["A"].width = 100
    f = 21
    enc(ws, f, ["N", "Periodo", "Cortes_con_banda", "V_areas_medias_m3", "V_del_plano_m3",
                "Dif_pct", "Espesor_V_sobre_A_m"], [5, 15, 17, 19, 17, 11, 20])
    for i, p in enumerate(PERIODOS):
        r = f + 1 + i
        v, _ = vol_areas_medias(area, p["n"])
        nc = sum(1 for c in ORDEN_H if area.get((c, p["n"]), 0) > 0)
        dif = (v - p["vol"]) / p["vol"] * 100
        vals = [p["n"], ETIQ[p["n"]], nc, round(v), p["vol"], round(dif, 1),
                round(p["vol"] / (p["ha"] * 10000), 1)]
        for k, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=k, value=val)
            c.border = BORDE
            if k == 6 and abs(dif) < 10:
                c.fill = PatternFill("solid", fgColor=VERDE)

    # ---- Nivel del lago
    ws = wb.create_sheet("Nivel_lago")
    h1(ws, "A1", "Correlación con el nivel del lago — plantilla")
    for i, t in enumerate([
        "PASO 1. Pegue el registro diario en las columnas A y B (fecha y cota en m.s.n.m.).",
        "        COLBÚN tiene el registro desde el inicio de operación de Canutillar (1990).",
        "PASO 2. Las columnas F a J se calculan solas para cada período.",
        "PASO 3. Grafique 'Dias_bajo_231' contra 'Tasa_m3_año' en un gráfico de dispersión.",
        "        Si los puntos se alinean, hay relación entre el abatimiento y la erosión.",
        "",
        "Ese gráfico es el resultado más importante de todo el encargo: es lo que conecta la",
        "operación de la central con el daño, y lo que sustenta la cota mínima de estabilidad.",
    ]):
        ws.cell(row=3 + i, column=1, value=t).font = Font(size=9)
    enc(ws, 12, ["Fecha  (PEGAR)", "Cota_msnm  (PEGAR)"], [18, 20])
    for r in range(13, 40):
        for c in (1, 2):
            ws.cell(row=r, column=c).fill = PatternFill("solid", fgColor=AMBAR)

    enc(ws, 12, ["Fecha  (PEGAR)", "Cota_msnm  (PEGAR)", "", "N", "Periodo", "Inicio", "Fin",
                 "Dias_bajo_231", "Dias_bajo_230", "Cota_minima", "Tasa_m3_año"],
        [18, 20, 3, 5, 15, 12, 12, 15, 15, 13, 13])
    for i, p in enumerate(PERIODOS):
        r = 13 + i
        m = meses(p)
        ws.cell(row=r, column=4, value=p["n"])
        ws.cell(row=r, column=5, value=ETIQ[p["n"]])
        ws.cell(row=r, column=6, value=p["ini"].isoformat())
        ws.cell(row=r, column=7, value=p["fin"].isoformat())
        ws.cell(row=r, column=8,
                value=f'=COUNTIFS($A:$A,">="&DATEVALUE(F{r}),$A:$A,"<="&DATEVALUE(G{r}),$B:$B,"<231")')
        ws.cell(row=r, column=9,
                value=f'=COUNTIFS($A:$A,">="&DATEVALUE(F{r}),$A:$A,"<="&DATEVALUE(G{r}),$B:$B,"<230")')
        ws.cell(row=r, column=10,
                value=f'=IFERROR(MINIFS($B:$B,$A:$A,">="&DATEVALUE(F{r}),$A:$A,"<="&DATEVALUE(G{r})),"")')
        ws.cell(row=r, column=11, value=round(p["vol"] / m * 12))
        for k in (8, 9, 10):
            ws.cell(row=r, column=k).fill = PatternFill("solid", fgColor=VERDE)

    wb.save(destino)
    print("->", destino)


if __name__ == "__main__":
    _, area = bandas_por_corte()
    figuras(area)
    excel(area, "/projects/sandbox/LAGO-CHAPO/Comparacion_periodos_RioNegro.xlsx")
