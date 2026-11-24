# INVESTIGADORES POR PARTE — deep research adaptado (versión I2)

Cada parte aplica el método de la skill `deep-research`: varios investigadores en paralelo, cada uno con un trozo acotado, que dejan notas con cifras, fechas y fuentes. Después, un redactor sintetiza las notas. La diferencia con la skill es el redactor: no escribe el ensayo narrativo de la skill (`report-writer.md`), sino el prompt de la parte, con sus tablas, su bloque puente y su archivo de datos.

Marcadores que rellena el orquestador: {CARPETA}, {NOTAS} (= {CARPETA}notas/parteN/), {SKILL_RESEARCHER} (ruta del `researcher.md` de la skill, o "no disponible"), y las fechas del contrato (§1).

---------------------------------------------------------------
## PLANTILLA DEL PROMPT DE CADA INVESTIGADOR
(El orquestador la rellena con los datos del investigador de la lista de abajo.)

```
Investiga: {TEMA}
Parte {N} del diagnóstico semanal de liquidez global. Semanas: CORTE {CORTE} · COMP {COMP_LUNES}–{COMP_VIERNES} · REV {REV_LUNES}–{REV_VIERNES} · OBJ {OBJ_LUNES}–{OBJ_VIERNES}.

Objetivo: {OBJETIVO}

Preguntas clave:
{PREGUNTAS}

Fuentes (usa estas primero, en este orden; registro completo en el contrato §6):
{FUENTES}

Restricciones:
- Solo tu tema. Otros investigadores cubren el resto en paralelo; no los dupliques.
- Fechas: las de arriba mandan. Cuenta la fecha efectiva del dato, nunca la de una noticia. Nada posterior al CORTE.
- Estados y umbrales de frescura: contrato §3–§4. Un dato sin fecha no existe. Que falte un dato no es señal de tranquilidad.
- Lee las webs con WebFetch pidiendo FILAS LITERALES ("devuelve verbatim las N últimas filas fecha,valor"), nunca un resumen. Si una página es larga, pide un rango de fechas concreto o usa el parámetro offset. El terminal NO llega a estas webs.
- Haz todos los cálculos (diferenciales, sumas, medias, identidades) con Python sobre archivos, nunca de cabeza.
- Presupuesto: hasta 20 llamadas de herramienta web. Un reintento por fuente y luego la alternativa del contrato §6.
- No escribas conclusiones de régimen ni probabilidades: eso lo hace el redactor.

Salida (obligatoria, dos archivos):
1. {NOTAS}{ID}.md — notas con la estructura de la skill: por cada pregunta clave, "### Takeaway" (1–2 frases) y "### Cited Findings" (hechos con [Fuente](URL) y fecha efectiva). Al final, "## Gaps" con lo que no encontraste y por qué. Señala expresamente los conflictos entre fuentes.
2. {NOTAS}{ID}.csv — todas las cifras que hayas obtenido, una por fila, con cabecera:
   serie,fecha,valor,unidad,fuente,estado,retraso_dias,nota
   (estado del contrato §3; retraso en días hábiles respecto al CORTE).

Como primer paso, si {SKILL_RESEARCHER} no es "no disponible", lee ese archivo: es el método de investigación de la skill deep-research y lo aplicas con las restricciones de arriba, que mandan sobre él si chocan (por ejemplo, el presupuesto de 20 llamadas y el CSV obligatorio).

Al terminar responde solo: archivos escritos · 3 hallazgos con cifra y fecha · 3 huecos.
```

---------------------------------------------------------------
## PARTE 1 — FUNDING (3 investigadores)

### P1-A · Tipos y presión de funding
- **Objetivo:** serie diaria de COMP y REV de SOFR (con p25/p75/p99 y volumen), EFFR, TGCR, BGCR y OBFR; IORB vigente en cada fecha; diferenciales frente a IORB y presión de funding según la definición común.
- **Preguntas:**
  - ¿Cuáles son los tipos de cada día de COMP y REV, y cuáles quedan PENDING (T+1)?
  - ¿Cuál era el IORB vigente en cada fecha? ¿Hubo FOMC entre la última fila de IORB y la fecha del SOFR?
  - ¿Qué valen, por día, SOFR−IORB, TGCR−IORB, BGCR−IORB, EFFR−IORB y SOFR−EFFR (misma fecha)?
  - ¿Se cumple la presión de funding común (SOFR ≥ IORB y además TGCR/BGCR ≥ IORB o SRF material)? ¿Cuántas sesiones seguidas? ¿Cae en una ventana de calendario?
  - ¿Qué fase EFFR/SOFR/IORB toca (Parte 1, §3)?
- **Fuentes:**
  - markets.newyorkfed.org/api/rates/all/search.json?startDate={COMP_LUNES}&endDate={CORTE}
  - fred.stlouisfed.org/data/IORB.txt
  - federalreserve.gov/monetarypolicy/fomccalendars.htm y la nota de implementación del FOMC si hace falta
- **Nota:** para el SRF material, usa el CSV de P1-B si ya existe; si no, deja el campo pendiente para el redactor.

### P1-B · Operaciones de la Fed y reservas
- **Objetivo:** ON RRP y SRF diarios de COMP y REV (operaciones "Repo" sumadas por día) y reservas semanales.
- **Preguntas:**
  - ¿Cuánto se aceptó cada día en ON RRP y en SRF (submitted y accepted, número de operaciones, tipo)?
  - ¿El uso del SRF es técnico, puntual, recurrente o material? ¿Coincide con fin de mes, fin de trimestre, tax dates o settlements?
  - ¿Cuáles son las tres últimas observaciones de reservas (WRESBAL) en bn, y su cambio?
- **Fuentes:**
  - markets.newyorkfed.org/api/rp/all/all/results/lastTwoWeeks.json (si COMP no entra, añade la búsqueda por fechas: /api/rp/all/all/results/search.json?startDate=…&endDate=…)
  - fred.stlouisfed.org/data/WRESBAL.txt

### P1-C · XEURBI y contexto de funding
- **Objetivo:** los diez últimos XEURBI con fecha y retraso, posibles outliers, y los hechos fechados de la semana que expliquen el funding.
- **Preguntas:**
  - ¿Cuál es la serie de XEURBI (CSV de CME), su retraso, su mínimo y máximo en REV, y su cambio frente a COMP?
  - ¿Algún día rompe la serie (posible outlier)?
  - ¿Qué anuncios oficiales de la Fed o del NY Fed sobre balance, SRF, ON RRP o tipos administrados hay en REV u OBJ? Con fecha y enlace oficial.
  - ¿Qué hay en el calendario de REV y OBJ que afecte al funding (fin de mes o trimestre, tax dates, festivos SIFMA)?
- **Fuentes:**
  - cmegroup.com/reports/cme-xccy-basis-historical-data.csv
  - newyorkfed.org/markets (declaraciones), federalreserve.gov/newsevents/pressreleases.htm
  - sifma.org/resources/general/holiday-schedule/

---------------------------------------------------------------
## PARTE 2 — TREASURY PLUMBING (5 investigadores)
Es la parte con más peso en las probabilidades prospectivas: cada investigador cubre un trozo pequeño para poder ser exhaustivo.

### P2-A · Cash Ledger de REV y TGA
- **Objetivo:** el Cash Ledger completo de REV, con un registro por (día de settlement, familia), y el TGA diario desde el lunes de COMP.
- **Preguntas:**
  - ¿Qué securities liquidan cada día de REV, sea cual sea su fecha de subasta?
  - Por grupo, ¿cuánto suman gross, PHM (una vez por grupo) y NNC? Ruta del NNC usada (1 / 3a / 3b) e identidad comprobada.
  - ¿Qué buybacks ejecutados liquidan en REV (importe aceptado, settlement, tipo)?
  - ¿Cuál fue el cierre del TGA cada día desde el lunes de COMP? ¿Cuánto variaron el TGA y el NNC realizado en REV? ¿Hubo una tax date?
  - Flujo neto de cada día de settlement de REV (P-004): Σ NNC de todas las familias − buybacks ejecutados que liquidan ese día. ¿Qué días tuvieron mucho gross pero neto pequeño, o inyección neta?
- **Fuentes:** S-Q1, S-Q3 (Ruta 3b), S-Q4 y S-Q5 de la Parte 2.
- **CSV obligatorio:** filas `ledger_rev` (fecha de settlement, familia, securities en tenores cortos, gross, phm, nnc, gross_10y_mas, ruta, identidad), `buyback` (fecha de settlement, aceptado en bn, tipo), `neto_dia` (fecha, neto en bn o n/c) y `tga` (fecha, cierre en bn).

### P2-B · Cash Ledger de OBJ
- **Objetivo:** el Cash Ledger previsto de OBJ, con un registro por (día, familia), incluidas las subastas de REV que liquidan en OBJ.
- **Preguntas:**
  - ¿Qué liquida cada día de OBJ, y con qué origen (subastado en REV, en OBJ o tentativo)?
  - ¿Qué gross, PHM y NNC tiene cada grupo (Rutas 1 / 3a / 3b)? Si no hay importe anunciado: TENTATIVE, sin inventar.
  - ¿Hay CMB anunciados? ¿Algún festivo desplaza settlements?
  - ¿Cuánto gross de 10Y o más liquida cada día de OBJ?
  - Flujo neto previsto de cada día de OBJ (Σ NNC − buybacks previstos que ya estén ejecutados o anunciados con importe). Si una familia del día no tiene NNC, el neto es n/c.
- **Fuentes:** S-Q2, upcoming_auctions, S-Q3 (vencimientos de cada día de OBJ), A-Q3 (calendario tentativo).
- **CSV obligatorio:** filas `ledger_obj` (como `ledger_rev`, más origen) y `neto_dia` (fecha, neto en bn o n/c).

### P2-C · Resultados de las subastas de REV
- **Objetivo:** el resultado completo de cada subasta de cupón de REV.
- **Preguntas:**
  - Para cada subasta de cupón de REV: high yield, WI con su hora, tail o stop-through, BTC, indirects, directs y dealers.
  - Calidad frente a las previas del mismo tenor (fuerte / normal / floja / peligrosa).
  - Bills de REV: high rate, BTC y tamaño (resumen).
- **Fuentes:** A-Q1 (auctions_query); A-Q5 (InvestingLive por subasta, con la búsqueda "investinglive {tenor} auction high yield {mes año}"), estado SECONDARY.
- **Regla:** un tail sin WI con hora es NO CONFIRMADO.

### P2-D · Comparables y condiciones para la Parte 3
- **Objetivo:** para cada tenor de cupón de 5Y o más que se subasta en OBJ (nominal o TIPS), la última subasta y las medias de las seis anteriores del mismo tenor y tipo. Con eso, las condiciones D5 calculadas con código. Además, el scorecard de duration de 5Y a 30Y.
- **Preguntas:**
  - ¿Qué tenores de 5Y o más se subastan en OBJ?
  - Para cada uno: última subasta (fecha, tail con WI, BTC, indirects, dealers) y medias de las seis previas.
  - ¿floja_2de4? ¿sólida? Con los criterios cumplidos y los que faltan.
  - Scorecard: última subasta de 5Y, 7Y, 10Y, 20Y y 30Y.
- **Fuentes:** A-Q4 con filtro de fecha ({HACE_9_MESES}; TIPS {HACE_18_MESES}); A-Q5 para el WI.

### P2-E · Calendario de OBJ, anuncios, QRA y buybacks previstos
- **Objetivo:** el calendario de OBJ día a día, con sus anuncios, el QRA y los buybacks previstos.
- **Preguntas:**
  - ¿Qué subastas hay en OBJ (A-Q2 cruzado con A-Q3), con su estado (anunciada / TENTATIVE) e importe si está anunciado (A-Q6)?
  - ¿Qué anuncios de Treasury caen en OBJ, con día y hora? ¿Cae en OBJ el anuncio del QRA (Policy Statement)? Si es así, márcalo `qra`.
  - ¿Qué buybacks hay previstos en OBJ según el calendario tentativo del último QRA?
  - Lectura del último QRA: tamaños de cupones, bills frente a cupones, objetivo de TGA, buybacks.
  - ¿Cae en OBJ algún fin de mes, fin de trimestre o tax date? ¿Hay cierres SIFMA?
- **Fuentes:** A-Q2, A-Q3, home.treasury.gov (QRA y quarterly refunding), calendario de buybacks del QRA, SIFMA.

---------------------------------------------------------------
## PARTE 3 — CONFIRMACIÓN Y PROBABILIDADES (6 investigadores)

### P3-A · MOVE y fails
- **Objetivo:** MOVE con cierre, cambio diario, cambio frente a cinco sesiones antes, máximo y mínimo de REV, zona y retraso; las cuatro series de fails con dirección y media de 8 semanas.
- **Preguntas:**
  - ¿Cuáles son los últimos 12 cierres del MOVE con fecha? Si hay más de 2 días hábiles de retraso, busca los cierres que faltan (SECONDARY).
  - ¿Qué dicen las cuatro series de fails (D/R Treasuries y total): tres últimas observaciones, dirección y si están sobre o bajo la media de 8 semanas?
- **Fuentes:** sección 3 de la Parte 3 (Investing MOVE; OFR con {HACE_20_SEMANAS}).

### P3-B · Crédito y banca
- **Objetivo:** OAS de IG, HY, Single-B y CCC en pb con su cambio frente a cinco sesiones; banca con dato.
- **Preguntas:**
  - ¿Cuáles son las 8 últimas filas de cada OAS? Calcula los cambios con código.
  - ¿Qué bancos publicaron en REV o publican en OBJ? ¿Qué cifras de depósitos, NII, coste de funding, provisiones, CRE o NBFI dieron, con fecha?
  - ¿Hay CDX IG/HY con fuente abierta fechada?
- **Fuentes:** FRED (BAMLC0A0CM, BAMLH0A0HYM2, BAMLH0A2HYB, BAMLH0A3HYC); investor relations de los bancos.

### P3-C · Expectativas de tipos: FedWatch semanal y consenso de OBJ (P-005)
- **Objetivo:**
  - la distribución de las tres próximas reuniones, actual y de la semana anterior, con el tipo implícito y la hora de actualización;
  - para cada dato macro1/macro2 de OBJ: consenso, anterior y qué resultado movería las expectativas hacia hawkish o dovish.
- **Preguntas:**
  - Para cada reunión (fechas verificadas en el calendario de la Fed): distribución actual y de la semana anterior, probabilidad de recorte, de no cambio y de subida respecto al rango vigente, tipo implícito (100 − precio).
  - ¿Hubo FOMC en REV? Si lo hubo, ¿la lectura "actual" es posterior a la decisión (hora de actualización)? Si no lo es, dilo: el sesgo queda NO CONFIRMADO.
  - ¿Cuál es el sesgo con la regla de la Parte 3 (6.4), semana contra semana?
  - ¿Hay declaraciones de la Fed con fecha en REV que expliquen el cambio?
  - Consenso de OBJ: para cada dato de EE. UU. de primer y segundo nivel, el consenso y el anterior (columnas rotuladas de la fuente), la hora ET y una propuesta de criterio "hawkish si … / dovish si …" con umbral numérico. Prioriza los que más pueden mover el precio de la próxima reunión dado el sesgo actual (empleo, inflación, ISM).
- **Fuentes:** investing.com/central-banks/fed-rate-monitor; federalreserve.gov (calendario y comunicados); tradingeconomics.com/united-states/calendar (consenso, SECONDARY; un valor sin rótulo no se asigna).
- **CSV obligatorio:** filas `fedwatch` (reunión, recorte/no cambio/subida actual y semana anterior, hora) y `consenso` (fecha, hora ET, dato, nivel, consenso, anterior, hawkish_si, dovish_si, rótulo de la fuente).

### P3-D · Calendario de OBJ
- **Objetivo:** todos los eventos de OBJ verificados en su fuente oficial para su día exacto. El consenso de cada dato lo recoge P3-C; la evaluación de REV, P3-F.
- **Preguntas:**
  - Macro de OBJ (BLS, BEA, Census, ISM, FOMC), con día y hora oficiales.
  - Earnings de los seis grandes bancos y de las megacaps en OBJ, con día y si es antes de la apertura o tras el cierre.
  - QRA: ¿se confirma la fecha y la hora del Policy Statement si cae en OBJ?
  - Cierres y sesiones cortas de SIFMA en OBJ.
- **Fuentes:** sección 3 de la Parte 3 (calendario).

### P3-E · GLI (opcional; el primero que se recorta)
- **Objetivo:**
  - Si hay captura ({CAPTURA_GLI}): leer la pendiente de la amarilla y de la verde en REV y OBJ, y decir si hay confluencia.
  - Contexto: series del GLI proxy G3 en {CARPETA}gli_input.json y ejecución de `python3 {MOTOR} gli …` (no puntúa).
- **Fuentes:** sección 3 de la Parte 3 (GLI proxy G3).
- **Nota:** si el orquestador va justo de tiempo (modo mínimo), este investigador no se lanza.

### P3-F · Evaluación de REV y pistas paralelas
- **Objetivo:** los datos diarios de REV para evaluar la semana anterior, en la clasificación principal y en las pistas Nasdaq 100, Russell 2000 y AUD/JPY, más los rezagados de la semana anterior.
- **Preguntas:**
  - Para cada día de REV: S&P 500 en % diario, HY OAS en cambio diario (pb) y MOVE en % diario.
  - Para cada día de REV: Nasdaq 100, Russell 2000 y AUD/JPY en % diario (calcula el % con código desde los cierres; necesitas el cierre del viernes de COMP). Lo que no haya salido por retraso va como null, sin estimar.
  - Rezagados: en {HISTORIAL} → semanas[-1].pistas_rev, ¿qué días quedaron "nc"? Busca ahora su valor.
  - Para cada día on/off: ¿qué lo movió? (una línea con fuente fechada).
- **Fuentes:** sección 3 de la Parte 3 (evaluación): Investing S&P 500 y Russell 2000, FRED NASDAQ100 (página de la serie), Frankfurter AUD/JPY, FRED HY OAS e Investing MOVE.
- **CSV obligatorio:** filas `eval` (fecha, spx_pct, hy_pb, move_pct, ndx_pct, rut_pct, audjpy_pct) y `rezagado` (fecha, campo, valor).

---------------------------------------------------------------
## INSTRUCCIONES PARA EL REDACTOR DE CADA PARTE
(Se añaden delante del prompt de la parte.)

```
Eres el redactor de la Parte {N}. Los investigadores ya han recogido los datos. Están en {NOTAS}: un .md con notas citadas y un .csv con las cifras de cada investigador.
1. Lee todas las notas y los CSV antes de escribir nada. Junta los CSV en un único archivo con Python.
2. Aplica íntegro el prompt de la Parte {N} que va debajo: método, reglas, tablas, bloque puente, datos{N}.json y auditoría. Sus secciones de fuentes y presupuesto te dicen dónde están los datos; ya los han descargado los investigadores. No repitas descargas.
3. Si falta un dato crítico o hay un conflicto entre notas, puedes hacer como máximo 8 llamadas web para cerrarlo. Lo demás se marca con su estado (NOT AVAILABLE, CONFLICT…), sin inventar.
4. Todos los cálculos, con código.
5. No escribas el ensayo narrativo de la skill: el formato es el del prompt de la parte.
```
