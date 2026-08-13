# Extracción de la geometría de los perfiles

Objetivo: convertir los `.dwg` de monitoreo en un CSV con columnas
`anio, corte, x_m, z_msnm`. Es el único bloqueo para todo el análisis cuantitativo.

## Estado de los archivos

| Archivo | Formato interno | Versión AutoCAD |
|---|---|---|
| `2014 01 Perfiles Monitoreo RNegro b.dwg` | `AC1018` | 2004 |
| `2018 11 Perfiles Monitoreo RNegro.dwg` | `AC1024` | 2010 |
| `PerfilRioNegro.dwg` | `AC1032` | 2018 |

**Lo que ya se intentó y no funcionó:** el PDF `2018 11 Perfiles Monitoreo
RNegro.pdf` contiene los perfiles como gráficos vectoriales sin texto de
coordenadas: la extracción de texto devuelve solo 174 caracteres (rótulos del
plano de ubicación), ninguna cota. Y `.dwg` es un formato binario propietario que
`ezdxf` no lee de forma nativa; requiere un convertidor externo (ODA File
Converter o LibreDWG), que no está disponible en este entorno.

**Conclusión: la extracción requiere una máquina con AutoCAD, o instalar un
convertidor DWG→DXF localmente.** Los métodos siguientes están ordenados de
menor a mayor esfuerzo.

---

## Opción A — ODA File Converter + Python (recomendada)

Convierte DWG a DXF, que sí se puede automatizar. No requiere licencia de
AutoCAD.

1. Descargar el [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) (gratuito).
2. Convertir los `.dwg` a DXF (versión de salida: ASCII DXF R2013 o posterior).
3. Inspeccionar la estructura antes de extraer nada:

```python
import ezdxf

doc = ezdxf.readfile("2018_Perfiles.dxf")
msp = doc.modelspace()

# Qué capas existen y cuánta geometría hay en cada una
from collections import Counter
print(Counter((e.dxf.layer, e.dxftype()) for e in msp))

# Los rótulos de los cortes suelen ser TEXT/MTEXT
for e in msp.query("TEXT MTEXT"):
    print(repr(e.dxf.text), e.dxf.insert)
```

4. Extraer las polilíneas de la capa de perfiles:

```python
import csv

CAPA = "PERFILES"       # ajustar con lo que muestre el paso 3
ANIO = 2018
ESCALA_V = 1.0          # ver "Escalas y exageración vertical" más abajo

with open(f"perfiles_{ANIO}.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["anio", "corte", "x_m", "z_msnm"])
    for i, pl in enumerate(msp.query(f'LWPOLYLINE[layer=="{CAPA}"]'), 1):
        for x, y, *_ in pl.get_points():
            w.writerow([ANIO, f"P{i}", round(x, 3), round(y * ESCALA_V, 3)])
```

El `f"P{i}"` es provisional: hay que **asociar cada polilínea con su rótulo real**
comparando su posición con la de los textos del paso 3. No dar por buena la
numeración automática.

---

## Opción B — AutoCAD

Si hay acceso a AutoCAD, es la vía más directa y confiable.

- **Perfil por perfil:** seleccionar la polilínea → comando `LIST` → copiar las
  coordenadas de los vértices.
- **En lote:** comando `DATAEXTRACTION`, seleccionar las polilíneas de perfiles,
  extraer la propiedad de vértices y exportar a CSV.

Ventaja frente a la opción A: se ve el dibujo, lo que permite confirmar
visualmente qué polilínea es cada corte y detectar bloques o referencias externas
que un lector automático podría pasar por alto.

---

## Opción C — QGIS (libre)

Admite DWG mediante GDAL, aunque con soporte irregular según la versión.

1. `Capa → Añadir capa → Añadir capa vectorial`, seleccionar el `.dwg`.
2. Elegir la capa que contiene las polilíneas de perfiles.
3. `Exportar → Guardar objetos como…` → CSV, con `GEOMETRY = AS_XY`.

---

## Opción D — Digitalización manual desde el PDF

Último recurso, solo si ninguna de las anteriores es viable. Con
[WebPlotDigitizer](https://automeris.io/WebPlotDigitizer/): calibrar los ejes con
dos cotas conocidas del plano y digitalizar cada perfil punto por punto.

Es laborioso y añade error de digitalización, pero para 7 cortes × 2 campañas es
factible. Documentar el error estimado si se usa esta vía.

---

## Verificaciones antes de dar el CSV por bueno

Tres condiciones que, si no se cumplen, invalidan la comparación entre años:

1. **Origen y sentido de la abscisa idénticos entre campañas.** Si en 2009 se
   midió de margen izquierda a derecha y en 2018 al revés, hay que invertir uno
   de los dos. Señal de alarma: los perfiles de dos años parecen espejos.
2. **Mismo datum vertical.** Cotas en m.s.n.m. y no locales. Contrastar contra el
   rango de niveles del lago del informe (230–245 m.s.n.m.): si las cotas del
   lecho salen fuera de un rango plausible respecto a eso, revisar el datum.
3. **Correspondencia física de cada corte entre años.** Que el `P3` de 2009 sea
   la misma sección que el `P3` de 2018.

### Escalas y exageración vertical

Los planos de perfiles suelen dibujarse con **exageración vertical** (típicamente
H 1:200 / V 1:100, es decir factor 2). Si no se corrige, **las áreas y volúmenes
saldrán multiplicados por ese factor.**

Cómo detectarlo: buscar el rótulo de escalas en el plano, y verificar contra una
cota conocida. Si un punto rotulado como 235.00 m.s.n.m. aparece en `y = 470`, la
escala vertical es 2 y hay que dividir por ella (`ESCALA_V = 0.5` en el script).

### Comprobación rápida del CSV

```python
import pandas as pd

df = pd.read_csv("perfiles_rio_negro.csv")
print(df.groupby(["corte", "anio"]).agg(
    n=("x_m", "size"),
    x_ini=("x_m", "min"), x_fin=("x_m", "max"),
    z_min=("z_msnm", "min"), z_max=("z_msnm", "max"),
))
```

Revisar que: el número de puntos por perfil sea razonable (>10); los rangos de
`x_m` de un mismo corte se traslapen entre años; y las cotas caigan en un rango
plausible para el sistema.

---

## Datos complementarios

Además de los perfiles, hacen falta dos archivos.

**`distancias.csv`** — distancia longitudinal entre cortes consecutivos, medida a
lo largo del eje del cauce (no en línea recta):

```csv
corte_a,corte_b,distancia_m
P1,P2,180
P2,P3,210
```

**Progresivas de los cortes**, ordenados de aguas arriba hacia la desembocadura.
Este orden es imprescindible para contrastar H1 y H2 del diagnóstico: sin él no
se puede evaluar si la incisión aumenta hacia el lago.
