DIAGNÓSTICO DE LIQUIDEZ GLOBAL — PARTE 1 DE 3 (v2)
Funding y money markets: SOFR, IORB, EFFR, TGCR, BGCR, ON RRP, SRF, reservas y EUR/USD CME XEURBI

Cambios frente a v1 (solo mecánica, el análisis no cambia): fechas calculadas por el orquestador; ON RRP y SRF desde la API del NY Fed; reservas añadidas; bloque puente con semanas y presión de funding; salida de datos en datos1.json para la Parte 3.

============================================================
0. FECHAS E INPUTS (los rellena el orquestador)
============================================================
FECHAS:
CORTE: {CORTE} ({DIA_SEMANA})
REV (semana revisada): {REV_LUNES} – {REV_VIERNES}
COMP (semana de comparación): {COMP_LUNES} – {COMP_VIERNES}
OBJ (semana objetivo, la usa la Parte 3): {OBJ_LUNES} – {OBJ_VIERNES}
CARPETA DE SALIDA: {CARPETA}

Reglas de fechas: las del CONTRATO COMÚN §1–§2. En resumen:
1. Estas fechas mandan. No uses otras ni las recalcules; si crees que no cuadran, anótalo como CONFLICT en el control y sigue con estas.
2. Cuenta la fecha efectiva del dato, nunca la de publicación de una noticia o snippet.
3. "Último dato" = el último publicado a fecha de CORTE. "Cambio semanal" = último dato frente al mismo día de COMP. "Dirección reciente" = la serie diaria de REV.
4. SOFR, EFFR, TGCR, BGCR y OBFR son T+1: en sábado o domingo el último dato suele ser el jueves de REV. El viernes se marca PENDING (T+1), no stale ni señal. ON RRP, SRF y XEURBI pueden tener dato del viernes (XEURBI suele ir con días de retraso: anota el retraso real).
5. Festivo o cierre del mercado de bonos dentro de REV o COMP: márcalo "holiday"; no es dato faltante.
6. No hagas preguntas. Si algo falta, sigue y márcalo.

============================================================
PARTE 1 (REPO): TEMA ÚNICO Y OBLIGATORIO
============================================================
Esta parte es exclusivamente sobre: funding, money markets, repo, SOFR, IORB, EFFR, TGCR, BGCR, ON RRP, SRF, reservas y EUR/USD CME Cross Currency Basis Index.
NO es un encargo abierto. NO investigues IA, energía, genética, cuántica, innovación, ciencia, salud, tecnología ni política tecnológica.
NO analices todavía: Treasury auctions en profundidad; QRA; buybacks; TGA (es de la Parte 2); MOVE; fails; crédito; banca; FedWatch; probabilidades diarias. Se hacen en las Partes 2 y 3.

Objetivo: construir la base de funding del diagnóstico y dejar un bloque puente y un archivo de datos para que las Partes 2 y 3 lo integren sin repetir descargas.

Título obligatorio: Diagnóstico de liquidez global — Parte 1: Funding y money markets
Primera sección obligatoria: 0. Control de frescura de datos
Primera frase analítica obligatoria: "Estado actual de funding: normalización / estrés incipiente / estrés sistémico / crisis de liquidez."
Estilo: parte conectada de un informe mayor, no un informe cerrado. Deja claro qué falta validar en las Partes 2 y 3. Las tablas mandan; prosa mínima.

Presupuesto: unas 10 fuentes abiertas. Un reintento por fuente y después la alternativa del CONTRATO §6. Pide siempre a la herramienta web las filas literales, no un resumen, y haz los cálculos (diferenciales, cambios, medias) con código.

============================================================
0. CONTROL DE FRESCURA DE DATOS
============================================================
Línea de control: CORTE · REV · COMP · OBJ · holidays en REV/COMP.

Tabla obligatoria: Métrica · Último dato · Fecha efectiva · Observación de COMP (fecha) · Fuente · Estado · Retraso (días hábiles)
Filas: SOFR (con p25/p75/p99 y volumen) · EFFR · IORB · TGCR · BGCR · OBFR · ON RRP · SRF · Reservas (WRESBAL) · EUR/USD CME XEURBI.
Estados: los del CONTRATO §3 (CONFIRMED, SECONDARY, PENDING (T+1), STALE, CONFLICT, NOT AVAILABLE) más "holiday".
Si una métrica no se encuentra, escribe literalmente: "dato no encontrado / no disponible en abierto / no confirmado". No conviertas ausencia de dato en señal positiva.
Debajo, tabla "Acceso a fuentes": Fuente · Abrió sí/no · Alternativa usada · Fecha del último dato.

============================================================
FUENTES (usa exactamente estas)
============================================================
A) SOFR / EFFR / TGCR / BGCR / OBFR — serie con rango, no "latest":
https://markets.newyorkfed.org/api/rates/all/search.json?startDate={COMP_LUNES}&endDate={CORTE}
Extrae por fecha: effectiveDate, percentRate, percentPercentile25/75/99 (si existen), volumeInBillions. No uses las medias SOFR 30/90/180 como SOFR overnight.

B) IORB:
https://fred.stlouisfed.org/data/IORB.txt
IORB es administrado: usa el valor vigente en la fecha efectiva de cada SOFR. El TXT puede acabar antes de la fecha del SOFR: si entre su última fila y la fecha del SOFR hubo una reunión del FOMC (https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), confirma el IORB en la nota de implementación de esa reunión. Si no hubo FOMC, el IORB vigente es la última fila.

C) ON RRP y D) SRF — API del NY Fed (una sola llamada para los dos):
https://markets.newyorkfed.org/api/rp/all/all/results/lastTwoWeeks.json
- operationType "Reverse Repo" = ON RRP. operationType "Repo" = SRF (Standing Repo Operations).
- Puede haber dos o más operaciones "Repo" por día (mañana, tarde y, a veces, una de precio múltiple): súmalas por día.
- Campos: operationDate, operationType, totalAmtSubmitted, totalAmtAccepted (en dólares: divide entre 1.000.000.000 para bn), tipos si aparecen.
- ON RRP y SRF son cosas distintas: nunca uses Reverse Repo para medir SRF.
Clasificación del SRF por día: 0 o importes de millones = sin uso / técnico; miles de millones, o uso repetido varios días fuera de fin de mes, fin de trimestre y tax dates = material.

E) EUR/USD CME XEURBI — CSV oficial (sin cabecera: fecha,ticker,valor en pb):
https://www.cmegroup.com/reports/cme-xccy-basis-historical-data.csv
Extrae los diez últimos valores diarios con fecha. La página HTML de CME no sirve para leer el valor.
Prohibido: basis JPY/USD, CHF/USD, GBP/USD, basis genérico, proxies no oficiales, snippets, swap lines como sustituto, valores inventados. Si otra fuente da otro valor, se descarta: manda CME.
Si el CSV no abre tras un reintento: "EUR/USD CME XEURBI: dato no confirmado; el CSV oficial de CME no fue accesible."
Un día que rompe la serie (salto de signo o > 5 pb contra los días vecinos que revierte al día siguiente) es posible outlier: márcalo y no bases la lectura en él.

F) Reservas (WRESBAL, semanal, millones de USD):
https://fred.stlouisfed.org/data/WRESBAL.txt → las tres últimas observaciones. Conviértelas a bn y dilo.

============================================================
1. ESTADO DE FUNDING
============================================================
Empieza con: "Estado actual de funding: normalización / estrés incipiente / estrés sistémico / crisis de liquidez."
Explica: si la capa de funding está limpia o tensionada; si el estrés es puntual, técnico, de calendario o estructural; qué dato lidera el diagnóstico; qué dato contradice el estrés; qué dato está no confirmado.

============================================================
2. SOFR VS IORB
============================================================
Incluye: SOFR de cada día de REV con su IORB vigente y SOFR − IORB en pb; percentiles p75 y p99 frente a IORB (vigilancia); volumen; dirección (R2: dos observaciones consecutivas con fecha).
Interpretación: SOFR < IORB repo relativamente tranquilo · SOFR ≈ IORB (±1 pb) vigilancia · SOFR > IORB tensión repo incipiente · SOFR claramente > IORB (≥ +5 pb sostenido) escasez de cash en repo.
No exageres: un solo dato por encima de IORB puede ser técnico si coincide con fin de mes, fin de trimestre, tax date o un settlement grande. Dilo, pero no lo borres: la regla de presión de funding (§9) se aplica igual.

============================================================
3. EFFR VS IORB VS SOFR
============================================================
Incluye: último EFFR y fecha; EFFR − IORB; SOFR − IORB; SOFR − EFFR (misma fecha).
Fases:
Fase 0: EFFR < SOFR < IORB — exceso de liquidez.
Fase 1: IORB < SOFR < EFFR — normalidad funcional.
Fase 2: EFFR < IORB < SOFR — tensión repo incipiente.
Fase 3: IORB < EFFR < SOFR — escasez de reservas.
Fase 4: IORB < EFFR ≈ SOFR — crisis de liquidez / intervención probable.
Si no encaja: "La configuración no encaja limpiamente en las fases simplificadas; lectura ajustada: ___."

============================================================
4. TGCR / BGCR
============================================================
Compáralos con SOFR, EFFR e IORB en la misma fecha.
Lectura: TGCR/BGCR tranquilos = GC repo tranquilo · TGCR/BGCR sobre IORB = tensión más generalizada · SOFR alto con TGCR/BGCR tranquilos = presión localizada · TGCR/BGCR tensos con SOFR > IORB = alerta mayor.

============================================================
5. ON RRP
============================================================
Nivel, cambio diario y cambio semanal (frente a COMP). ¿Sigue actuando como colchón, se está agotando, deja el sistema más sensible a settlements, TGA rebuild o emisión?
Lectura: ON RRP alto = más colchón; bajo o cayendo = menos buffer. ON RRP bajo no implica crisis ni escasez de reservas por sí solo: necesita confirmación en SOFR/EFFR/TGCR/BGCR/SRF y reservas.

============================================================
6. SRF / STANDING REPO
============================================================
Uso de cada día de REV (submitted, accepted, número de operaciones, tipo si aparece); si es técnico, puntual, de minimis, recurrente o elevado; si coincide con fin de mes, fin de trimestre, year-end o settlements.
Lectura: cero/bajo/puntual no confirma crisis · recurrente/elevado alerta · elevado + SOFR > IORB + TGCR/BGCR tensos = tensión seria · elevado con SOFR/EFFR contenidos = backstop funcionando.

============================================================
7. EUR/USD CME XEURBI
============================================================
Los diez últimos valores con fecha; trayectoria día a día (una ida y vuelta no es una caída continua); último valor; mínimo y máximo de REV; cambio frente al último día de COMP; retraso del CSV respecto al CORTE.
Lectura: cerca de 0 no confirma estrés · negativo y estable fricción leve · más negativo y ampliándose presión creciente · deteriorándose junto a SOFR > IORB (o, en Parte 3, MOVE, fails o crédito) señal más seria. Por sí solo no confirma una crisis offshore.

============================================================
8. RESERVAS
============================================================
Tres últimas observaciones semanales de WRESBAL en bn, cambio semanal, y una línea: ¿hay evidencia propia de escasez de reservas (reservas cayendo + SOFR/EFFR presionando IORB + SRF)? Si solo cae el ON RRP, no la hay.

============================================================
9. PRESIÓN DE FUNDING (definición común con la Parte 3)
============================================================
Calcula, con la última fecha con los cuatro tipos publicados:
- sofr_ge_iorb: SOFR ≥ IORB
- gc_ge_iorb: TGCR ≥ IORB o BGCR ≥ IORB
- srf_material: uso material del SRF en REV (§D)
- confirmada = sofr_ge_iorb y (gc_ge_iorb o srf_material)
Anota además, como información (no cambia la regla): sesiones_consecutivas en las que se cumple la condición y si la fecha cae en ventana de calendario (fin de mes ±2 días hábiles, fin de trimestre, tax date o settlement de cupones). Esta presión es la que activa el modo tensión de la Parte 3.

============================================================
10. LECTURA PUENTE HACIA PARTE 2 Y PARTE 3
============================================================
En prosa breve: qué implica el funding actual para la absorción de subastas y settlements de la Parte 2; qué implicaría encontrar emisión larga pesada o NNC grande en OBJ; qué debe confirmar la Parte 3 con MOVE, fails, crédito, FedWatch y GLI; qué dato de funding vigilar día a día en OBJ. Sin probabilidades. Sin cerrar el diagnóstico global.

============================================================
11. BLOQUE PUENTE PARTE 1
============================================================
Termina con este bloque exacto y relleno. Escríbelo también tal cual en {CARPETA}puente1.txt.

BLOQUE PUENTE PARTE 1 — FUNDING
Semanas: CORTE __ · REV __ – __ · COMP __ – __ · OBJ __ – __
Estado funding:
normalización / estrés incipiente / estrés sistémico / crisis de liquidez
SOFR:
valor: __ · fecha efectiva: __ · p75/p99: __ / __ · volumen: __ bn
lectura: __
IORB:
valor vigente: __ · vigente desde / confirmado en: __
SOFR - IORB:
__ pb (fecha: __) · serie REV: __ / __ / __ / __ / __ pb
lectura: __
EFFR:
valor: __ · fecha efectiva: __
lectura: __
Fase EFFR/SOFR/IORB:
Fase __ · lectura: __
TGCR/BGCR:
TGCR: __ · BGCR: __ · fecha: __ · frente a IORB: __ / __ pb
lectura: __
ON RRP:
valor: __ bn · fecha: __ · cambio semanal: __ bn
lectura: colchón suficiente / colchón reducido / colchón agotado / no confirmado
SRF:
uso: __ bn · fecha: __ · días con uso en REV: __
lectura: sin uso relevante / técnico / puntual / recurrente / elevado / no confirmado
Reservas:
valor: __ bn · fecha: __ · cambio semanal: __ bn
EUR/USD CME XEURBI:
valor: __ pb · fecha: __ · retraso: __ días hábiles · cambio vs COMP: __ pb
lectura: no confirma estrés / fricción leve / tensión moderada / tensión seria / no confirmado
Presión de funding (definición común):
confirmada: sí / no · fecha: __ · sesiones consecutivas: __ · ventana de calendario: sí (cuál) / no
Indicador líder de funding:
__
Indicador que contradice estrés:
__
Dato no confirmado más importante:
__
Implicación para Parte 2:
__
Implicación para Parte 3:
__

============================================================
12. SALIDA DE DATOS Y AUDITORÍA
============================================================
Escribe {CARPETA}datos1.json con el esquema del CONTRATO §7 (todas las fechas de REV y COMP en las series, importes en bn). Comprueba que es JSON válido ejecutando un parseo con código.
Escribe el informe completo en {CARPETA}parte1.md.

Auditoría (✓ o explicación, una línea cada uno):
- Todas las fechas están dentro de REV/COMP o marcadas como PENDING/holiday.
- SOFR − IORB, EFFR − IORB y TGCR/BGCR − IORB se calcularon con valores de la misma fecha.
- SRF se midió con operaciones "Repo" sumadas por día; ON RRP con "Reverse Repo".
- XEURBI sale del CSV de CME o está marcado no confirmado.
- Ninguna ausencia de dato se leyó como tranquilidad; ON RRP bajo no se tradujo en escasez de reservas.
- Presión de funding calculada con la definición común.
- puente1.txt y datos1.json coinciden en todas las cifras.
