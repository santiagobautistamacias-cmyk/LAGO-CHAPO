# Lago Chapo — Análisis de erosión del Río Negro

Análisis de los perfiles de monitoreo del Río Negro (7 cortes), en el contexto del
PRDA ordenado por la Sentencia Rol N° D-4-2022 del Tercer Tribunal Ambiental.

## Entregable principal

**[`Perfiles_RioNegro_analisis.xlsx`](Perfiles_RioNegro_analisis.xlsx)** — libro con
los 7 perfiles extraídos de los DWG, un gráfico por corte, resumen morfométrico,
progresivas UTM y plantilla de volúmenes con fórmulas.

![Perfiles](perfiles_rio_negro.png)

## Documentos

| Archivo | Contenido |
|---|---|
| [DIAGNOSTICO.md](DIAGNOSTICO.md) | El análisis: mecanismo causal, balance de Lane aplicado al caso, hipótesis contrastables |
| [EXTRACCION_PERFILES.md](EXTRACCION_PERFILES.md) | Cómo se extrajeron los perfiles de los DWG. Método reproducible |
| [extraer_perfiles_dwg.py](extraer_perfiles_dwg.py) | Extracción DXF → Excel |
| [analisis_perfiles.py](analisis_perfiles.py) | Cálculo de áreas y volúmenes entre campañas |
| [perfiles_rio_negro.csv](perfiles_rio_negro.csv) | Los 7 perfiles en formato tabular (452 filas) |

## En una línea

El abatimiento del nivel del lago baja el nivel base de los afluentes, lo que
aumenta la pendiente del tramo final y desencadena erosión retrogradante. En
términos de Lane: **`Qs·D50 < Q·S`, donde la variable que cambió es S, no Q.**

## Resultados

Los 7 cortes, ordenados de aguas abajo hacia aguas arriba según la cota de su
thalweg (el orden coincide con la progresión espacial de las coordenadas UTM, lo
que lo corrobora):

| Orden | Corte | Thalweg (m.s.n.m.) | Ancho (m) | Relieve (m) | Progresiva (m) |
|---|---|---|---|---|---|
| 1 | **1** | 225.69 | 626 | 14.2 | 0 |
| 2 | **A** | 227.21 | 842 | 14.4 | 154 |
| 3 | **2** | 231.35 | 383 | 12.5 | 662 |
| 4 | **B** | 232.62 | 440 | 12.7 | 791 |
| 5 | **3** | 235.06 | 436 | 10.2 | 908 |
| 6 | **4** | 239.81 | 205 | 6.7 | 1192 |
| 7 | **C** | 243.62 | 288 | 5.6 | 1591 |

**Solo los cortes 1 y A tienen el lecho bajo la cota 230 m.s.n.m.**, es decir en
la zona de influencia del abatimiento del lago. El resto está sobre la cota 231,
el mínimo provisional ordenado por el tribunal. Son precisamente los dos cortes
más cercanos a la desembocadura, y son los que muestran un canal profundamente
encajonado. La geometría es coherente con el mecanismo de erosión retrogradante
descrito en el informe de INGETEC.

El relieve de la sección decrece monótonamente hacia aguas arriba (14.4 → 5.6 m):
secciones encajonadas abajo, someras arriba.

## Limitación

**No se puede calcular la variación de volumen del cauce con estos DWG.** Las 7
líneas de terreno son idénticas en los planos de 2014 y 2018: hay una sola
geometría de referencia, no dos levantamientos. Los polígonos de erosión dibujados
tampoco sirven como medición por período (son iguales en 4 de los 7 cortes, lo que
indica ediciones del dibujo). Detalle en la hoja `Hallazgos` del Excel.

Para cerrar el análisis de volumen hace falta pedir los perfiles crudos de cada
campaña, o las superficies topográficas por año. El cálculo ya está implementado
en `analisis_perfiles.py` y corre directo sobre un CSV con esa estructura.

## Uso

```bash
pip install -r requirements.txt
python3 extraer_perfiles_dwg.py     # DXF -> Excel
python3 figura_perfiles.py          # figura de los 7 perfiles
python3 analisis_perfiles.py        # autotest del calculo de volumenes
```

La conversión DWG → DXF requiere LibreDWG; los pasos están en
`EXTRACCION_PERFILES.md`.

## Nota metodológica

Los gráficos de perfil de los planos tienen **exageración vertical ×10**. Si no se
corrige, las áreas y volúmenes salen multiplicados por 10. La escala se calibró en
cada gráfico (residuo máximo 0.04 m) y se verificó de forma independiente contra
las coordenadas UTM. Ver la hoja `Calibracion` del Excel.

Para comparar campañas, las áreas nunca se calculan respecto a la cota mínima de
cada perfil: al incidirse el lecho esa cota baja y la referencia se mueve con él,
ocultando el cambio que se busca medir. Se usa datum fijo común o área entre
perfiles.

## Archivos fuente

- `_0895901 -IRF-LBJ-GRAL-0001…Rev B…pdf` — Informe de diagnóstico INGETEC (50 pp.)
- `informe_texto.txt` — texto extraído del anterior, para búsquedas
- `2014 01 Perfiles Monitoreo RNegro b.dwg` — plano enero 2014
- `2018 11 Perfiles Monitoreo RNegro.dwg` / `.pdf` — plano junio 2018
- `PerfilRioNegro.dwg` — perfil longitudinal
