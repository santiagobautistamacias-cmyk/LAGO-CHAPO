# Diagnóstico — Erosión del Río Negro, Lago Chapo

Marco de trabajo para el análisis de los perfiles de monitoreo 2009–2018 (7 cortes).

Todo el contexto de esta sección proviene del informe de diagnóstico de INGETEC
que está en este repositorio (`_0895901-IRF-LBJ-GRAL-0001 … Rev B`, 50 pp.,
contrato PP-176-2026 con COLBÚN S.A., visita del 11 de marzo de 2026).

---

## 1. El diagnóstico ya está establecido: no hay que descubrirlo, hay que cuantificarlo

Este es el punto más importante y cambia por completo el enfoque del trabajo.

El informe **ya identificó el mecanismo causal**. El encargo no es averiguar por
qué el río se erosiona, sino **medir cuánto** y **verificar si los perfiles son
consistentes con el mecanismo propuesto**.

### El mecanismo (según el informe)

El Lago Chapo opera como embalse de la Central Canutillar. Cuando el nivel del
lago se abate de forma extrema y prolongada:

1. Se reduce el *colchón hídrico* que sostiene hidráulicamente las
   desembocaduras de los afluentes.
2. Aparece un **desnivel colgante** entre el lecho del afluente y el nuevo nivel
   base del lago.
3. Ese desnivel **aumenta la pendiente hidráulica** en el tramo final.
4. Aumenta la capacidad de transporte → **erosión retrogradante**: el lecho se
   socava desde aguas abajo hacia aguas arriba, con colapsos laterales
   progresivos en los taludes.

El informe lo resume así: es un caso de *degradación por aumento de la capacidad
de transporte por aumento de gradiente en el tramo final del río*, y señala
explícitamente que **no** es el comportamiento de un delta, donde dominaría la
acumulación.

### Contexto legal y operacional

- **Sentencia Causa Rol N° D-4-2022**, Tercer Tribunal Ambiental: establece
  relación causal entre la operación histórica de Canutillar y la aceleración de
  procesos geomorfológicos en riberas y desembocaduras.
- Ordena un **Plan de Reparación de Daño Ambiental (PRDA)** con cota mínima
  provisional de **231 m.s.n.m.**
- Un objetivo declarado de la Fase 2 es definir la **cota mínima de estabilidad**.

Esto es clave para encuadrar el análisis: **los perfiles son la evidencia
cuantitativa que debe sustentar la definición de esa cota mínima.**

### Niveles del lago (referencia para interpretar los perfiles)

| Referencia | Cota (m.s.n.m.) |
|---|---|
| Máximo observado (creciente 1991) | > 245 |
| Máximo normal aproximado | ~243 |
| Umbral crítico citado en el informe | 230 |
| Cota mínima provisional ordenada por el 3TA | 231 |
| Descenso observado desde 2020 en alta demanda (dic–may) | hasta ~230 |

### Cronología morfológica del Río Negro

| Período | Observación (imágenes aéreas) |
|---|---|
| 1982 (pre-proyecto) | Canal único en el tramo final; barras gruesas aguas arriba |
| 1995 (5 años de operación) | Efecto del nivel máximo normal; acumulación de grueso aguas arriba; inicio de migración lateral |
| 1996–1998 | Sequía → mayor abatimiento; ensanchamiento marcado del cauce; incisión del canal principal |
| 2005 | Erosión lateral y degradación del lecho muy evidentes por el rango extremo de niveles |
| **2010–2012** | Degradación continúa; migración lateral; **corte de meandros** y nuevo canal principal |
| **2016–2018** | Situación similar a 2010–2012 |
| 2020–2023 | Aparente estabilización; recuperación de vegetación; sin incremento de erosión de márgenes |

**El período de los perfiles (2009–2018) cae de lleno en la fase más activa de
degradación.** Es exactamente la ventana donde se espera la señal más fuerte.

### Hallazgos de campo en el Río Negro (marzo 2026)

Es el cauce con **mayor traza de erosión retrogradante documentada** y el de
mayor área de cuenca:

- Incisión en el tramo final/confluencia, con exposición de estratos basales de
  depósitos glaciales heterogéneos (grava, arena, limo). *El informe anota que el
  proceso no parece estar activo o en crecimiento actualmente.*
- Erosión de márgenes con caída de vegetación en el exterior de las curvas, pero
  con avance gradual de vegetación sobre los taludes.
- Alta producción de sedimento grueso en la cuenca alta, proyectándose hacia la
  zona afectada.
- Movimiento reciente de barras de sedimento grueso hacia la zona de influencia
  del nivel del lago.
- Meandros cortados o abandonados en las últimas dos décadas.

### Factores concurrentes que hay que separar

- **Erupción del Volcán Calbuco, abril de 2015.** Cae *dentro* del período
  2009–2018 y es un aporte masivo de sedimento. Es el principal factor de
  confusión del análisis: puede enmascarar o invertir localmente la señal de
  incisión. Si hay perfiles pre- y post-2015, esa comparación es de alto valor.
- **Obras 1998–2004**: gradas en el Río Negro, perfilado de taludes, barrera de
  troncos. **Fallaron**, según el informe, porque no se dimensionaron conforme al
  caudal formativo o dominante. Conviene ubicar si algún corte de monitoreo cae
  sobre o cerca de una grada, porque ahí el perfil refleja la obra, no el
  comportamiento natural del cauce.
- Períodos de sequía (marcadamente 1996–1998).

---

## 2. Balance de Lane aplicado a este caso

La relación de Lane expresa el equilibrio entre el trabajo que el agua puede
hacer y el sedimento que debe mover:

```
        Qs · D50        ∝        Q · S
   ─────────────────          ───────────────
   aporte de sedimento        capacidad de transporte
   (lo que hay que mover)     (lo que el río puede mover)
```

Si el miembro derecho crece sin que el izquierdo lo acompañe, el río toma el
sedimento que le falta **del propio lecho**: incisión.

### Lo relevante: aquí la variable que cambió es S, no Q

Es la conclusión central y conviene enunciarla con precisión, porque es lo que
distingue este caso de una erosión "clásica" por crecidas.

| Variable | ¿Cambió? | Cómo |
|---|---|---|
| **S** (pendiente) | **Sí — es el motor** | El abatimiento del lago baja el nivel base. El tramo final queda colgado y su gradiente aumenta. |
| **Q** (caudal) | No de forma atribuible | La hidrología de la cuenca no fue alterada por la central. El informe no invoca aumento de Q. |
| **Qs** (aporte sólido) | Alto, pero **no llega** | La cuenca alta produce mucho grueso, pero queda retenido en barras aguas arriba y no alimenta el tramo final. |
| **D50** | Grueso, acorazamiento | Al lavarse los finos queda material grueso que puede frenar la incisión (control por acorazamiento). |

El desequilibrio es entonces:

```
Qs · D50  <  Q · S        →  degradación en el tramo final
```

con el agravante de que Qs es **bajo justo donde S es alto**: el sedimento grueso
se queda atrás en barras mientras la incisión avanza desde la desembocadura.

### Consecuencia práctica

La palanca de manejo no es aumentar el aporte de sedimento ni reducir el caudal:
es **controlar S restringiendo el abatimiento del nivel del lago**. Eso es
exactamente lo que persigue la cota mínima de estabilidad, y es la razón por la
que este análisis alimenta esa decisión.

### Cómo reportar Lane sin datos hidráulicos

No se necesitan Q, D50 ni Qs medidos para hacer un análisis de Lane defendible.
Lane es una **relación de proporcionalidad cualitativa**, no una fórmula de
diseño. Con los perfiles basta para:

1. Determinar el **signo** del desequilibrio (degradación vs. agradación) por
   tramo y por período.
2. Verificar el **gradiente espacial** de la incisión.
3. Verificar la **coherencia temporal** con el registro de niveles del lago.

Lo que sí conviene declarar explícitamente como vacío de información: D50 (falta
granulometría), Qs (sin mediciones de transporte) y el caudal formativo (que es
justamente el parámetro cuyo desconocimiento hizo fallar las obras de 1998–2004).

---

## 3. Las tres hipótesis a contrastar con los perfiles

Este es el núcleo del trabajo analítico. La erosión retrogradante deja **firmas
geométricas específicas** que se pueden verificar o refutar con los 7 cortes.

### H1 — Gradiente longitudinal de incisión

**Predicción:** la incisión debe ser **máxima en el corte más cercano al lago** y
decrecer hacia aguas arriba, hasta anularse en un punto de detención
(*knickpoint*).

**Cómo se verifica:** graficar el área neta erosionada de cada corte contra su
progresiva. Debe salir una curva monótona decreciente hacia aguas arriba.

**Por qué es decisiva:** una erosión generalizada por crecidas produciría un
patrón *sin* orden longitudinal claro. Si el gradiente aparece ordenado y
anclado en la desembocadura, el control por nivel base queda demostrado con los
propios datos.

### H2 — Migración del knickpoint

**Predicción:** el punto donde la incisión se anula debe **migrar hacia aguas
arriba** entre campañas sucesivas.

**Cómo se verifica:** ubicar en cada período el corte donde el área neta pasa de
positiva a ~0, y ver si ese límite se desplaza. Con 7 cortes la resolución
espacial es gruesa, pero la tendencia debería ser visible.

**Valor añadido:** permite estimar una **velocidad de propagación** (m/año), que
es un insumo directo para proyectar hasta dónde llegaría la erosión si se
mantuviera el régimen de abatimiento.

### H3 — Desacople entre incisión aguas abajo y agradación aguas arriba

**Predicción:** los cortes de aguas arriba pueden mostrar **agradación** (llegada
de barras de sedimento grueso) mientras los de aguas abajo muestran incisión.

**Cómo se verifica:** por eso el script reporta erosión y depósito **por
separado** en lugar de solo el neto. Un balance neto cercano a cero puede
esconder 2000 m³ erosionados abajo y 2000 m³ depositados arriba: dos procesos
distintos, no un río en equilibrio.

**Nota:** este desacople es *la firma* del desequilibrio de Lane en este sistema
—Qs alto donde no se necesita, bajo donde sí— y por sí solo justifica no
reportar únicamente el volumen neto.

---

## 4. Qué hacer, en orden

### Paso 1 — Extraer la geometría de los perfiles

Es el único bloqueo real. Ver [`EXTRACCION_PERFILES.md`](EXTRACCION_PERFILES.md).

Salida requerida: un CSV con columnas `anio, corte, x_m, z_msnm`.

Tres exigencias que invalidan el análisis si no se cumplen:

1. **Mismo origen y sentido de la abscisa** en todas las campañas de un corte.
2. **Mismo datum vertical** en todas las campañas.
3. **Correspondencia verificada** de cada corte entre años (que el "P3" de 2009
   sea físicamente el mismo que el "P3" de 2018).

### Paso 2 — Cuantificar áreas y volúmenes

```bash
pip install -r requirements.txt
python3 analisis_perfiles.py perfiles_rio_negro.csv
```

El script entrega, por corte y período: área erosionada, área depositada, área
neta, descenso máximo puntual y tasas; y por tramo: volúmenes por el método de
áreas medias.

### Paso 3 — Contrastar H1, H2 y H3

Graficar área neta vs. progresiva, por período. Es el resultado analítico
central.

### Paso 4 — Cruzar con el registro de niveles del lago

El informe indica que existe registro de nivel desde el inicio de operación.
Para cada período entre campañas, calcular cuántos días el lago estuvo bajo la
cota 231 (y bajo 230) y contrastarlo con el volumen erosionado del período.

Si la correlación aparece, es la evidencia cuantitativa que conecta la operación
con el daño y la que sustenta la cota mínima de estabilidad. **Este es el
resultado de mayor valor de todo el encargo.**

### Paso 5 — Aislar el efecto Calbuco 2015

Comparar la tasa de erosión de los períodos pre-2015 y post-2015. Si hay
agradación anómala post-2015, atribuirla al aporte volcánico y no a un cambio en
el régimen de operación.

---

## 5. Vacíos de información a declarar

Conviene declararlos explícitamente en el entregable: el informe de INGETEC
identifica "vacíos críticos de información" como parte del alcance, de modo que
documentarlos es parte del trabajo, no una excusa.

| Dato | Estado | Para qué se necesita |
|---|---|---|
| Geometría digital de los perfiles | En DWG, sin extraer | Todo el análisis cuantitativo |
| Progresivas de los 7 cortes | No confirmadas | H1, H2 y volúmenes |
| Campañas intermedias 2009–2018 | Solo se ven 2014 y 2018 en el repo | Resolución temporal, H2 |
| Registro diario de nivel del lago | Existe (citado en el informe) | Paso 4, correlación con la operación |
| Granulometría (D50) | No disponible | Lane cuantitativo, acorazamiento |
| Transporte de sedimentos (Qs) | Sin mediciones | Lane cuantitativo |
| Caudal formativo/dominante | No disponible | Diseño de obras (causa de la falla 1998–2004) |

---

## 6. Advertencia sobre el volumen neto

Los volúmenes "de terreno erosionado por franja de tiempo" que se entregaron
conviene tratarlos como **valor a reproducir y auditar**, no como dato de
entrada. Al recalcularlos desde los perfiles, verificar:

- **Referencia vertical usada.** Si se calculó respecto a la cota mínima de cada
  perfil, el valor está sesgado: la referencia se mueve con la incisión. Debe
  usarse un datum fijo común o el área entre perfiles.
- **Si erosión y depósito se compensaron.** Un neto pequeño puede ocultar dos
  procesos grandes y opuestos (H3).
- **Longitud de influencia** asignada a cada corte.
- **Zona de traslape** entre campañas: si un levantamiento es más ancho que el
  otro, comparar solo el traslape (el script lo hace y lo reporta).

---

---

## 7. Estructura sugerida del entregable

Una nota técnica de 12–20 páginas es suficiente. No hace falta reconstruir el
contexto que ya está en el informe de INGETEC: conviene citarlo y concentrar el
esfuerzo en los resultados propios (secciones 4 y 5, que son el aporte nuevo).

| § | Sección | Contenido | Ext. |
|---|---|---|---|
| 1 | Objeto y alcance | Qué se analiza, período, los 7 cortes | ½ p. |
| 2 | Antecedentes | Resumen del mecanismo y del marco legal, **citando** el informe INGETEC | 1–2 p. |
| 3 | Metodología | Datum común, área entre perfiles, áreas medias, zona de traslape, tratamiento de la exageración vertical | 2 p. |
| 4 | **Resultados** | Perfiles superpuestos por corte; tabla de áreas (erosión / depósito / neta); volúmenes por tramo y período; tasas | 4–6 p. |
| 5 | **Contraste de hipótesis** | H1 gradiente longitudinal, H2 migración del knickpoint, H3 desacople incisión/agradación | 3–4 p. |
| 6 | Balance de Lane | Signo del desequilibrio por tramo; S como variable de control | 1–2 p. |
| 7 | Correlación con niveles del lago | Días bajo cota 231/230 vs. volumen erosionado por período | 1–2 p. |
| 8 | Vacíos e incertidumbre | Tabla de §5; error de extracción y de método | 1 p. |
| 9 | Conclusiones | Cifras cerradas y su lectura respecto a la cota mínima de estabilidad | 1 p. |

Figuras mínimas: 7 de perfiles superpuestos, 1 de área neta vs. progresiva (H1,
la figura clave), 1 de volumen por tramo y período, 1 de nivel del lago con las
fechas de campaña marcadas.

Dos recomendaciones de forma:

- **Reportar siempre erosión, depósito y neto por separado**, nunca solo el neto.
- **Declarar el signo de las convenciones** en la metodología: aquí, área neta
  positiva = degradación.

---

## Referencias

- INGETEC (2026). *Informe Técnico de Diagnóstico Lago Chapo*, Rev. B, doc.
  0895901-IRF-LBJ-GRAL-0001, contrato PP-176-2026, COLBÚN S.A. — incluido en
  este repositorio.
- Tercer Tribunal Ambiental de Chile. Sentencia Causa Rol N° D-4-2022.
- Lane, E. W. (1955). The importance of fluvial morphology in hydraulic
  engineering. *Proceedings ASCE*, 81(745), 1–17.
