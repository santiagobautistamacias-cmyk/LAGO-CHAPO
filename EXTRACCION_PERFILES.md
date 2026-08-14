# Extracción de la geometría de los perfiles — RESUELTO

Los 7 perfiles ya están extraídos. Este documento registra el método, para que el
resultado sea reproducible y auditable.

Resultados: [`Perfiles_RioNegro_analisis.xlsx`](Perfiles_RioNegro_analisis.xlsx),
[`perfiles_rio_negro.csv`](perfiles_rio_negro.csv),
[`perfiles_rio_negro.png`](perfiles_rio_negro.png).

## Formatos de los archivos

| Archivo | Formato interno | Versión AutoCAD |
|---|---|---|
| `2014 01 Perfiles Monitoreo RNegro b.dwg` | `AC1018` | 2004 |
| `2018 11 Perfiles Monitoreo RNegro.dwg` | `AC1024` | 2010 |
| `PerfilRioNegro.dwg` | `AC1032` | 2018 |

## Lo que no funcionó

- **`ezdxf` directamente**: no lee DWG nativo, solo DXF.
- **El PDF de perfiles**: los perfiles son gráficos vectoriales sin texto de
  coordenadas. La extracción de texto devuelve 174 caracteres, todos rótulos del
  plano de ubicación. Ninguna cota.
- **ODA File Converter**: requiere descarga manual con registro.
- **Paquetes de sistema**: no hay `libredwg` en los repositorios de Amazon Linux 2023.

## Lo que funcionó: compilar LibreDWG

```bash
# 1. dependencias de compilación
dnf install -y automake libtool texinfo pcre2-devel

# 2. código fuente
git clone --depth 1 https://github.com/LibreDWG/libredwg.git
cd libredwg

# 3. el submódulo jsmn puede fallar tras un proxy de git; se baja directo.
#    Solo se usa para la salida JSON, que aquí no hace falta.
mkdir -p jsmn
curl -sSL -o jsmn/jsmn.h https://raw.githubusercontent.com/zserge/jsmn/master/jsmn.h

# 4. compilar (sin bindings para que sea más rápido)
sh autogen.sh
./configure --disable-bindings --disable-docs --enable-release
make -j$(nproc)

# 5. convertir
./programs/dwg2dxf -o salida.dxf "entrada.dwg"
```

Los tres DWG se convirtieron sin errores (solo avisos benignos de
`eed/reactors/xdic`). Versión usada: `dwg2dxf 0.14.8580`.

## Estructura encontrada en los DXF

El *modelspace* contiene dos zonas distintas:

| Zona | Ventana | Contenido |
|---|---|---|
| Planta | X 708.9k–710.6k, Y 5411.3k–5412.7k | Topografía en UTM 18S, curvas de nivel con cotas reales, trazas de los cortes |
| Gráficos de perfil | X 715.5k–717.6k, Y 5407.0k–5407.7k | Las 7 secciones dibujadas como diagramas 2D |

Además hay copias desplazadas del plano de planta (a X ≈ 715.6k y ≈ 722.3k, con
Z = −249), que hay que descartar para no duplicar geometría.

Capas relevantes:

| Capa | Contenido |
|---|---|
| `0` | Las 7 líneas de terreno de los perfiles, y los polígonos de erosión |
| `PGRIDT` | Etiquetas del eje de cotas → sirven para calibrar la escala vertical |
| `PGRID`, `PBASE`, `PEGCT` | Marco, ejes y etiquetas de cota del gráfico |
| `corte` | Trazas de los cortes en planta (UTM) y sus rótulos de extremo |
| `CONT-MJR*`, `CONT-MNR*` | Curvas de nivel con cota real en el atributo `elevation` |
| `puntos` | 9.159 rótulos de puntos topográficos con cota |
| `EROSION-2018` | Anotaciones de erosión, solo en el plano de 2018 |

Los 7 cortes se rotulan **1, 2, 3, 4, A, B, C**. Hay una traza `D` en planta que
no tiene gráfico de perfil asociado.

## Escalas: exageración vertical ×10

Este es el punto que más fácilmente arruina el cálculo de áreas y volúmenes.

- **Vertical: 10 unidades de dibujo = 1 m.** Calibrado por mínimos cuadrados en
  cada gráfico con las etiquetas de la capa `PGRIDT`. Resultado: 9.95 a 10.05 u/m
  según el corte, con residuo máximo de 0.04 m. Ver la hoja `Calibracion`.
- **Horizontal: 1 unidad = 1 m.** Verificado de forma independiente: el gráfico
  del corte 1 mide 625.9 unidades de ancho, y la traza de ese corte en planta
  mide 626 m en coordenadas UTM.

**Consecuencia:** un área medida en unidades de dibujo vale **10× el área real en
m²**, porque solo el eje vertical está exagerado. Todas las áreas del Excel ya
están divididas por 10.

## Hallazgo: no hay dos levantamientos

Las 7 líneas de terreno son **idénticas en ambos DWG**: mismo número de vértices
y mismas coordenadas. Los planos comparten una única geometría de referencia y lo
que cambia entre ellos son los polígonos superpuestos.

Esto coincide con el planteamiento del encargo («los perfiles son los mismos pero
cambia la erosión presentada en cada período») y tiene una consecuencia directa:
**no se puede calcular variación de volumen por diferencia de levantamientos**,
porque no hay dos superficies topográficas distintas.

Se descartó también usar las curvas de nivel como épocas separadas: las capas
`CONT-*1/2/3/5` se solapan entre 88% y 94%, es decir son duplicados de una misma
superficie.

## Reproducir

```bash
pip install ezdxf openpyxl numpy matplotlib
python3 extraer_perfiles_dwg.py    # genera el Excel
python3 figura_perfiles.py         # genera la figura
```

Ambos scripts esperan los DXF convertidos en el directorio de trabajo.

## Lo que aún falta pedir

Para cerrar el análisis de variación de volumen se necesita **una** de estas dos:

1. Los perfiles crudos de cada campaña (2009, 2011, 2014, 2018) como series de
   puntos independientes: `año, corte, distancia, cota`.
2. Las superficies topográficas de cada año como capas o archivos separados.

Con eso, el cálculo de áreas y volúmenes ya está implementado en
[`analisis_perfiles.py`](analisis_perfiles.py) y se ejecuta directo sobre el CSV.
