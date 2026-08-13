# Lago Chapo — Análisis de erosión del Río Negro

Marco de análisis para los perfiles de monitoreo del Río Negro (7 cortes,
2009–2018), en el contexto del PRDA ordenado por la Sentencia Rol N° D-4-2022 del
Tercer Tribunal Ambiental.

## Por dónde empezar

| Documento | Contenido |
|---|---|
| **[DIAGNOSTICO.md](DIAGNOSTICO.md)** | El análisis. Mecanismo causal, balance de Lane aplicado al caso, las 3 hipótesis a contrastar y el plan de trabajo. **Leer primero.** |
| [EXTRACCION_PERFILES.md](EXTRACCION_PERFILES.md) | Cómo sacar la geometría de los `.dwg`. Es el bloqueo actual. |
| [analisis_perfiles.py](analisis_perfiles.py) | Cálculo de áreas, volúmenes y clasificación degradación/agradación. |

## En una línea

El abatimiento del nivel del lago baja el nivel base de los afluentes, lo que
aumenta la pendiente del tramo final y desencadena erosión retrogradante. En
términos de Lane: **`Qs·D50 < Q·S`, donde la variable que cambió es S, no Q.**

## Estado

- [x] Contexto y mecanismo causal extraídos del informe de INGETEC
- [x] Marco de análisis y hipótesis contrastables definidos
- [x] Herramienta de cálculo verificada con datos sintéticos
- [ ] **Geometría de los perfiles extraída de los `.dwg`** ← bloqueo
- [ ] Cuantificación con datos reales
- [ ] Correlación con el registro de niveles del lago

No hay resultados numéricos del Río Negro todavía: los `.dwg` son binarios y en
este entorno no fue posible convertirlos (detalle y alternativas en
`EXTRACCION_PERFILES.md`). Las cifras que imprime el script son de un **autotest
con datos sintéticos**, no del río.

## Uso

```bash
pip install -r requirements.txt

# Autotest con datos sintéticos: verifica la herramienta
python3 analisis_perfiles.py

# Con datos reales, una vez extraídos
python3 analisis_perfiles.py perfiles_rio_negro.csv
```

Formato del CSV: `anio, corte, x_m, z_msnm` (una fila por punto del perfil).

## Nota metodológica

Las áreas **no** se calculan respecto a la cota mínima de cada perfil. Al
incidirse el lecho, esa cota baja y la referencia se mueve con él, ocultando
justamente el cambio que se quiere medir. Se usa un **datum fijo común** o el
**área entre perfiles** de distinta fecha. El autotest verifica que ambos métodos
coincidan.

El script reporta erosión y depósito **por separado**, no solo el neto: en este
sistema se espera incisión aguas abajo y agradación aguas arriba
simultáneamente, y un neto cercano a cero podría ocultar ambos procesos.

## Archivos fuente

- `_0895901 -IRF-LBJ-GRAL-0001…Rev B…pdf` — Informe de diagnóstico INGETEC (50 pp.)
- `informe_texto.txt` — texto extraído del anterior, para búsquedas
- `2014 01 Perfiles Monitoreo RNegro b.dwg` — campaña 2014
- `2018 11 Perfiles Monitoreo RNegro.dwg` / `.pdf` — campaña 2018
- `PerfilRioNegro.dwg` — perfil longitudinal
