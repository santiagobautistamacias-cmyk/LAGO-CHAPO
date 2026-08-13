"""
Análisis de perfiles transversales de monitoreo — Río Negro, Lago Chapo.

Calcula variaciones de área y volumen del lecho entre campañas topográficas
(2009-2018) para los 7 cortes de monitoreo, y clasifica cada tramo como
degradación (incisión) o agradación (depositación).

NOTA METODOLÓGICA IMPORTANTE
----------------------------
Las áreas NO se calculan respecto a la cota mínima de cada perfil. Ese enfoque
es incorrecto para comparar campañas: si el lecho se incide, la cota mínima baja
y la referencia se mueve con él, ocultando justamente el cambio que se quiere
medir. Aquí se usan dos métodos válidos:

  1. Área bajo un datum FIJO y común a todas las campañas (`area_bajo_datum`).
  2. Área ENTRE dos perfiles de distinta fecha (`comparar`), que da
     directamente el área erosionada/depositada. Es el método estándar
     ("end-area") y el que se usa para los volúmenes.

Uso rápido:
    python3 analisis_perfiles.py            # corre autotest con datos sintéticos
    python3 analisis_perfiles.py datos.csv  # corre con datos reales
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None


# ----------------------------------------------------------------------------
# Perfil transversal
# ----------------------------------------------------------------------------

@dataclass
class Perfil:
    """Un perfil transversal levantado en una fecha determinada.

    Attributes:
        corte: identificador de la sección (ej. "P3"). Debe ser el mismo entre
            campañas para poder comparar.
        anio: año de la campaña.
        x: abscisa transversal en metros, creciente. Debe medirse siempre desde
            el MISMO punto de referencia y en la MISMA dirección en todas las
            campañas, de lo contrario la comparación no es válida.
        z: cota del terreno en m.s.n.m.
    """

    corte: str
    anio: int
    x: np.ndarray
    z: np.ndarray

    def __post_init__(self) -> None:
        self.x = np.asarray(self.x, dtype=float)
        self.z = np.asarray(self.z, dtype=float)
        if self.x.shape != self.z.shape:
            raise ValueError(
                f"{self.corte}/{self.anio}: x y z deben tener igual longitud "
                f"({self.x.size} vs {self.z.size})"
            )
        if self.x.size < 2:
            raise ValueError(f"{self.corte}/{self.anio}: se requieren >=2 puntos")
        orden = np.argsort(self.x)
        self.x, self.z = self.x[orden], self.z[orden]

    # -- geometría básica ---------------------------------------------------

    @property
    def cota_min(self) -> float:
        return float(self.z.min())

    @property
    def cota_max(self) -> float:
        return float(self.z.max())

    @property
    def ancho_levantado(self) -> float:
        return float(self.x[-1] - self.x[0])

    def area_bajo_datum(self, datum: float) -> float:
        """Área entre el perfil y un plano horizontal fijo, en m².

        Solo integra donde el terreno está por debajo del datum. Al ser el datum
        común a todas las campañas, la diferencia de esta área entre dos años es
        el área neta erosionada (positiva) o depositada (negativa).
        """
        prof = np.clip(datum - self.z, 0.0, None)
        return float(np.trapezoid(prof, self.x))

    # -- hidráulica a un nivel de agua dado --------------------------------

    def geometria_hidraulica(self, nivel: float) -> Dict[str, float]:
        """Área mojada, perímetro mojado, ancho superficial y radio hidráulico.

        Maneja correctamente secciones con varios canales y calcula los puntos
        de intersección exactos con la superficie libre.
        """
        x, z = self.x, self.z
        area = perim = ancho = 0.0

        for i in range(len(x) - 1):
            x0, x1 = x[i], x[i + 1]
            z0, z1 = z[i], z[i + 1]
            d0, d1 = nivel - z0, nivel - z1

            if d0 <= 0 and d1 <= 0:
                continue  # tramo totalmente seco

            if d0 < 0 or d1 < 0:
                # el tramo cruza la superficie: recortar en la intersección
                t = d0 / (d0 - d1)
                xi = x0 + t * (x1 - x0)
                if d0 > 0:
                    x1, z1, d1 = xi, nivel, 0.0
                else:
                    x0, z0, d0 = xi, nivel, 0.0

            dx = x1 - x0
            if dx <= 0:
                continue
            area += 0.5 * (d0 + d1) * dx
            perim += float(np.hypot(dx, z1 - z0))
            ancho += dx

        return {
            "nivel_m": nivel,
            "area_mojada_m2": area,
            "perimetro_mojado_m": perim,
            "ancho_superficial_m": ancho,
            "radio_hidraulico_m": area / perim if perim > 0 else 0.0,
            "profundidad_media_m": area / ancho if ancho > 0 else 0.0,
            "profundidad_max_m": max(nivel - self.cota_min, 0.0),
        }


# ----------------------------------------------------------------------------
# Comparación entre dos campañas del mismo corte
# ----------------------------------------------------------------------------

@dataclass
class Comparacion:
    corte: str
    anio_ini: int
    anio_fin: int
    area_erosion_m2: float      # solo la parte donde el lecho bajó
    area_deposito_m2: float     # solo la parte donde el lecho subió
    area_neta_m2: float         # erosión - depósito (>0 = degradación neta)
    descenso_max_m: float       # máxima profundización puntual
    ascenso_max_m: float        # máximo relleno puntual
    x_traslape: Tuple[float, float]

    @property
    def anios(self) -> int:
        return self.anio_fin - self.anio_ini

    @property
    def proceso(self) -> str:
        if abs(self.area_neta_m2) < 1e-9:
            return "sin cambio"
        return "degradación (incisión)" if self.area_neta_m2 > 0 else "agradación (depósito)"

    @property
    def tasa_area_m2_anio(self) -> float:
        return self.area_neta_m2 / self.anios if self.anios else float("nan")


def comparar(p_ini: Perfil, p_fin: Perfil, paso: float = 0.25) -> Comparacion:
    """Compara dos campañas del mismo corte integrando el área entre perfiles.

    Los perfiles rara vez comparten las mismas abscisas, por lo que ambos se
    interpolan sobre una malla común dentro de la zona de traslape. La
    diferencia dz = z_ini - z_fin es positiva donde el lecho descendió.

    Args:
        p_ini: perfil de la campaña inicial.
        p_fin: perfil de la campaña final.
        paso: resolución de la malla de integración, en metros.
    """
    if p_ini.corte != p_fin.corte:
        raise ValueError(f"cortes distintos: {p_ini.corte} vs {p_fin.corte}")

    x0 = max(p_ini.x[0], p_fin.x[0])
    x1 = min(p_ini.x[-1], p_fin.x[-1])
    if x1 <= x0:
        raise ValueError(f"{p_ini.corte}: los perfiles no se traslapan en x")

    n = max(int(np.ceil((x1 - x0) / paso)) + 1, 2)
    xs = np.linspace(x0, x1, n)
    z_ini = np.interp(xs, p_ini.x, p_ini.z)
    z_fin = np.interp(xs, p_fin.x, p_fin.z)

    dz = z_ini - z_fin  # >0 => el lecho bajó => erosión
    a_ero = float(np.trapezoid(np.clip(dz, 0.0, None), xs))
    a_dep = float(np.trapezoid(np.clip(-dz, 0.0, None), xs))

    return Comparacion(
        corte=p_ini.corte,
        anio_ini=p_ini.anio,
        anio_fin=p_fin.anio,
        area_erosion_m2=a_ero,
        area_deposito_m2=a_dep,
        area_neta_m2=a_ero - a_dep,
        descenso_max_m=abs(float(np.clip(dz, 0.0, None).max())),
        ascenso_max_m=abs(float(np.clip(-dz, 0.0, None).max())),
        x_traslape=(float(x0), float(x1)),
    )


# ----------------------------------------------------------------------------
# Análisis del tramo completo
# ----------------------------------------------------------------------------

class AnalisisTramo:
    """Agrupa los perfiles de todos los cortes y campañas de un tramo de río."""

    def __init__(self, nombre: str = "Río Negro") -> None:
        self.nombre = nombre
        self.perfiles: Dict[str, Dict[int, Perfil]] = {}
        # distancia longitudinal entre cortes consecutivos, en metros
        self.distancias: Dict[Tuple[str, str], float] = {}
        self.orden_cortes: List[str] = []

    # -- carga --------------------------------------------------------------

    def agregar(self, perfil: Perfil) -> None:
        self.perfiles.setdefault(perfil.corte, {})[perfil.anio] = perfil
        if perfil.corte not in self.orden_cortes:
            self.orden_cortes.append(perfil.corte)

    def definir_orden(self, cortes: Sequence[str]) -> None:
        """Fija el orden de los cortes de aguas arriba hacia aguas abajo."""
        faltan = set(cortes) - set(self.perfiles)
        if faltan:
            raise ValueError(f"cortes sin datos: {sorted(faltan)}")
        self.orden_cortes = list(cortes)

    def definir_distancia(self, corte_a: str, corte_b: str, metros: float) -> None:
        self.distancias[(corte_a, corte_b)] = float(metros)

    @property
    def anios(self) -> List[int]:
        vistos = {a for camp in self.perfiles.values() for a in camp}
        return sorted(vistos)

    # -- comparaciones ------------------------------------------------------

    def comparar_corte(self, corte: str, anio_ini: int, anio_fin: int) -> Comparacion:
        camp = self.perfiles[corte]
        if anio_ini not in camp or anio_fin not in camp:
            raise KeyError(
                f"{corte}: faltan campañas {anio_ini}/{anio_fin}; "
                f"disponibles {sorted(camp)}"
            )
        return comparar(camp[anio_ini], camp[anio_fin])

    def comparar_todos(self, anio_ini: int, anio_fin: int) -> List[Comparacion]:
        """Compara todos los cortes que tengan ambas campañas."""
        out = []
        for corte in self.orden_cortes:
            camp = self.perfiles[corte]
            if anio_ini in camp and anio_fin in camp:
                out.append(self.comparar_corte(corte, anio_ini, anio_fin))
        return out

    # -- volúmenes ----------------------------------------------------------

    def volumenes(self, anio_ini: int, anio_fin: int) -> Dict:
        """Volumen erosionado/depositado por el método de áreas medias.

        Para cada par de cortes consecutivos con distancia definida:
            V = (A_i + A_{i+1}) / 2 * L
        aplicado por separado a erosión y a depósito.
        """
        comps = {c.corte: c for c in self.comparar_todos(anio_ini, anio_fin)}
        tramos = []
        tot_ero = tot_dep = long_total = 0.0

        for a, b in zip(self.orden_cortes, self.orden_cortes[1:]):
            if a not in comps or b not in comps:
                continue
            L = self.distancias.get((a, b)) or self.distancias.get((b, a))
            if L is None:
                continue

            v_ero = 0.5 * (comps[a].area_erosion_m2 + comps[b].area_erosion_m2) * L
            v_dep = 0.5 * (comps[a].area_deposito_m2 + comps[b].area_deposito_m2) * L

            tramos.append({
                "tramo": f"{a}-{b}",
                "longitud_m": L,
                "vol_erosion_m3": v_ero,
                "vol_deposito_m3": v_dep,
                "vol_neto_m3": v_ero - v_dep,
                "proceso": "degradación" if v_ero > v_dep else "agradación",
            })
            tot_ero += v_ero
            tot_dep += v_dep
            long_total += L

        neto = tot_ero - tot_dep
        anios = anio_fin - anio_ini
        return {
            "periodo": f"{anio_ini}-{anio_fin}",
            "anios": anios,
            "longitud_analizada_m": long_total,
            "vol_erosion_m3": tot_ero,
            "vol_deposito_m3": tot_dep,
            "vol_neto_m3": neto,
            "tasa_neta_m3_anio": neto / anios if anios else float("nan"),
            "tasa_neta_m3_km_anio": (
                neto / (long_total / 1000) / anios
                if long_total > 0 and anios else float("nan")
            ),
            "tramos": tramos,
        }

    # -- reportes -----------------------------------------------------------

    def tabla_comparaciones(self, anio_ini: int, anio_fin: int):
        filas = [{
            "corte": c.corte,
            "periodo": f"{c.anio_ini}-{c.anio_fin}",
            "area_erosion_m2": round(c.area_erosion_m2, 2),
            "area_deposito_m2": round(c.area_deposito_m2, 2),
            "area_neta_m2": round(c.area_neta_m2, 2),
            "descenso_max_m": round(c.descenso_max_m, 2),
            "ascenso_max_m": round(c.ascenso_max_m, 2),
            "tasa_m2_anio": round(c.tasa_area_m2_anio, 3),
            "proceso": c.proceso,
        } for c in self.comparar_todos(anio_ini, anio_fin)]
        return pd.DataFrame(filas) if pd is not None else filas

    def graficar_corte(self, corte: str, ruta: Optional[str] = None):
        """Superpone todas las campañas de un corte. Requiere matplotlib."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        camp = self.perfiles[corte]
        fig, ax = plt.subplots(figsize=(11, 5))
        colores = plt.cm.viridis(np.linspace(0, 0.9, len(camp)))

        for color, anio in zip(colores, sorted(camp)):
            p = camp[anio]
            ax.plot(p.x, p.z, lw=1.8, color=color, marker="o", ms=3, label=str(anio))

        ax.set_xlabel("Abscisa transversal (m)")
        ax.set_ylabel("Cota (m.s.n.m.)")
        ax.set_title(f"{self.nombre} — {corte}: evolución {min(camp)}–{max(camp)}")
        ax.legend(title="Campaña", fontsize=9)
        ax.grid(alpha=0.3)
        fig.tight_layout()

        destino = ruta or f"perfil_{corte}.png"
        fig.savefig(destino, dpi=200)
        plt.close(fig)
        return destino


# ----------------------------------------------------------------------------
# Carga desde CSV
# ----------------------------------------------------------------------------

COLUMNAS_CSV = ["anio", "corte", "x_m", "z_msnm"]


def cargar_csv(ruta: str, nombre: str = "Río Negro") -> AnalisisTramo:
    """Carga perfiles desde un CSV con columnas: anio, corte, x_m, z_msnm."""
    if pd is None:
        raise ImportError("se requiere pandas: pip install pandas")

    df = pd.read_csv(ruta)
    faltan = set(COLUMNAS_CSV) - set(df.columns)
    if faltan:
        raise ValueError(
            f"faltan columnas {sorted(faltan)}. Esperadas: {COLUMNAS_CSV}"
        )

    tramo = AnalisisTramo(nombre)
    for (anio, corte), g in df.groupby(["anio", "corte"], sort=True):
        g = g.sort_values("x_m")
        tramo.agregar(Perfil(str(corte), int(anio), g["x_m"].to_numpy(), g["z_msnm"].to_numpy()))
    return tramo


def cargar_distancias_csv(tramo: AnalisisTramo, ruta: str) -> None:
    """Carga distancias con columnas: corte_a, corte_b, distancia_m."""
    if pd is None:
        raise ImportError("se requiere pandas: pip install pandas")
    df = pd.read_csv(ruta)
    for _, r in df.iterrows():
        tramo.definir_distancia(str(r["corte_a"]), str(r["corte_b"]), float(r["distancia_m"]))


# ----------------------------------------------------------------------------
# Balance de Lane
# ----------------------------------------------------------------------------

def balance_lane(area_neta_m2: float, contexto: str = "") -> str:
    """Interpreta un cambio morfológico observado en términos del balance de Lane.

        Qs · D50  ∝  Q · S

    Si el miembro derecho (capacidad de transporte) crece sin que el izquierdo
    (aporte de sedimento) lo acompañe, el cauce responde erosionando su lecho.
    """
    if area_neta_m2 > 0:
        estado = (
            "DEGRADACIÓN. El cauce está incidiendo, luego Qs·D50 < Q·S: la\n"
            "  capacidad de transporte excede al aporte sólido. En este sistema la\n"
            "  causa dominante documentada es el aumento de S en el tramo final por\n"
            "  descenso del nivel base del lago (desnivel colgante en la\n"
            "  desembocadura), no un aumento de Q."
        )
    elif area_neta_m2 < 0:
        estado = (
            "AGRADACIÓN. El cauce está rellenando, luego Qs·D50 > Q·S: el aporte\n"
            "  sólido excede la capacidad de transporte. Compatible con el avance de\n"
            "  barras de sedimento grueso desde la cuenca alta hacia el tramo final."
        )
    else:
        estado = "EQUILIBRIO APARENTE. Sin cambio neto medible en el período."

    txt = f"Balance de Lane — {estado}"
    if contexto:
        txt += f"\n  Contexto: {contexto}"
    return txt


# ----------------------------------------------------------------------------
# Autotest con datos sintéticos
# ----------------------------------------------------------------------------

def _perfil_sintetico(corte: str, anio: int, incision: float, x0: float = 0.0) -> Perfil:
    """Perfil en V con talud, incidido `incision` metros en el centro."""
    x = np.array([0, 4, 8, 11, 14, 17, 20, 24, 28], dtype=float) + x0
    z = np.array([242.0, 240.5, 237.0, 235.0, 234.5, 235.2, 237.4, 240.8, 242.1])
    centro = (z < 236.5)
    z = z.copy()
    z[centro] -= incision
    return Perfil(corte, anio, x, z)


def _autotest() -> None:
    print("=" * 74)
    print("AUTOTEST — datos sintéticos (NO son datos del Río Negro)")
    print("=" * 74)

    tramo = AnalisisTramo("Río Negro (sintético)")
    # incisión creciente hacia aguas abajo: P1 arriba ... P7 en la desembocadura
    incisiones_2009 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    incisiones_2018 = [0.05, 0.10, 0.25, 0.55, 0.95, 1.40, 1.85]

    cortes = [f"P{i}" for i in range(1, 8)]
    for corte, i09, i18 in zip(cortes, incisiones_2009, incisiones_2018):
        tramo.agregar(_perfil_sintetico(corte, 2009, i09))
        tramo.agregar(_perfil_sintetico(corte, 2018, i18))

    tramo.definir_orden(cortes)
    for a, b in zip(cortes, cortes[1:]):
        tramo.definir_distancia(a, b, 180.0)

    # -- verificación del datum común -------------------------------------
    print("\n1) Por qué importa el datum común")
    p09, p18 = tramo.perfiles["P7"][2009], tramo.perfiles["P7"][2018]
    print(f"   Área respecto a la cota mínima de cada perfil (INCORRECTO):")
    print(f"     2009 = {p09.area_bajo_datum(p09.cota_max):8.2f} m²  (min={p09.cota_min:.2f})")
    print(f"     2018 = {p18.area_bajo_datum(p18.cota_max):8.2f} m²  (min={p18.cota_min:.2f})")
    datum = 242.0
    a09 = p09.area_bajo_datum(datum)
    a18 = p18.area_bajo_datum(datum)
    print(f"   Área bajo datum fijo {datum} m.s.n.m. (CORRECTO):")
    print(f"     2009 = {a09:8.2f} m²")
    print(f"     2018 = {a18:8.2f} m²   ->  Δ = {a18 - a09:+.2f} m² erosionados")

    # -- comparación por corte --------------------------------------------
    print("\n2) Comparación por corte 2009 -> 2018")
    tabla = tramo.tabla_comparaciones(2009, 2018)
    if pd is not None:
        print(tabla.to_string(index=False))
    else:
        for f in tabla:
            print("   ", f)

    # coherencia: el área entre perfiles debe igualar la diferencia bajo datum
    c7 = tramo.comparar_corte("P7", 2009, 2018)
    assert abs(c7.area_neta_m2 - (a18 - a09)) < 0.05, "inconsistencia entre métodos"
    print("\n   [ok] area_entre_perfiles coincide con Δarea_bajo_datum")

    # -- volúmenes ---------------------------------------------------------
    print("\n3) Balance volumétrico del tramo")
    res = tramo.volumenes(2009, 2018)
    print(f"   Período              : {res['periodo']} ({res['anios']} años)")
    print(f"   Longitud analizada   : {res['longitud_analizada_m']:.0f} m")
    print(f"   Volumen erosionado   : {res['vol_erosion_m3']:>10.1f} m³")
    print(f"   Volumen depositado   : {res['vol_deposito_m3']:>10.1f} m³")
    print(f"   Volumen NETO         : {res['vol_neto_m3']:>10.1f} m³")
    print(f"   Tasa neta            : {res['tasa_neta_m3_anio']:.1f} m³/año")
    print(f"   Tasa específica      : {res['tasa_neta_m3_km_anio']:.1f} m³/km/año")
    print("\n   Distribución longitudinal (aguas arriba -> desembocadura):")
    for t in res["tramos"]:
        print(f"     {t['tramo']:>7}  L={t['longitud_m']:6.0f} m  "
              f"neto={t['vol_neto_m3']:>9.1f} m³  {t['proceso']}")

    # -- geometría hidráulica ---------------------------------------------
    print("\n4) Geometría hidráulica de P7 en 2018 (nivel 236.5 m.s.n.m.)")
    for k, v in p18.geometria_hidraulica(236.5).items():
        print(f"     {k:<24} {v:8.3f}")

    # -- Lane --------------------------------------------------------------
    print("\n5) Interpretación")
    print("   " + balance_lane(
        res["vol_neto_m3"],
        "El gradiente de incisión crece hacia la desembocadura, firma "
        "característica\n  de erosión retrogradante propagándose desde el nivel base.",
    ))
    print("\n" + "=" * 74)
    print("Autotest OK. Reemplace los datos sintéticos por el CSV real:")
    print("  python3 analisis_perfiles.py perfiles_rio_negro.csv")
    print("=" * 74)


def _correr_real(ruta_csv: str) -> None:
    tramo = cargar_csv(ruta_csv)
    print(f"Cortes cargados : {tramo.orden_cortes}")
    print(f"Campañas        : {tramo.anios}")

    anios = tramo.anios
    if len(anios) < 2:
        print("Se requieren al menos dos campañas para comparar.")
        return

    ini, fin = anios[0], anios[-1]
    print(f"\nComparación {ini} -> {fin}")
    tabla = tramo.tabla_comparaciones(ini, fin)
    print(tabla.to_string(index=False) if pd is not None else tabla)

    if tramo.distancias:
        res = tramo.volumenes(ini, fin)
        print(f"\nVolumen neto: {res['vol_neto_m3']:.1f} m³ "
              f"({res['tasa_neta_m3_anio']:.1f} m³/año)")
        print(balance_lane(res["vol_neto_m3"]))
    else:
        print("\nSin distancias entre cortes cargadas: no se calculan volúmenes.")
        print("Use cargar_distancias_csv() o definir_distancia().")

    for corte in tramo.orden_cortes:
        print("figura:", tramo.graficar_corte(corte))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        _correr_real(sys.argv[1])
    else:
        _autotest()
