DIAGNÓSTICO DE LIQUIDEZ GLOBAL — PARTE 3 DE 3 (v6.3 · método v6.3; evaluación con P-025 y P-026 desde el 8-nov-2026)
MOVE, fails, crédito, banca, FedWatch, XEURBI, GLI, validación final y probabilidades diarias

Cambios del método frente a v6, aprobados por el usuario el 29-oct-2026. Todo lo demás del método v6 (pesos, umbrales, regla de grupo, topes, fórmula y tabla de control) sigue igual:
- P-002: el anuncio de refinanciación trimestral (QRA) puntúa como evento de dispersión (±1) el día del Policy Statement.
- P-003: el GLI es opcional. Solo puntúa con la captura del usuario y cuando dirección y aceleración confluyen. El GLI proxy G3 es contexto y nunca puntúa. Sin captura, la capa GLI está "sin señal" y no cuenta como NO CONFIRMADA ni baja la confianza.
- P-001: la regla de presión de funding no cambia. Se añade la medición de cuándo y por qué sube SOFR − IORB (sección 4.1), que se acumula semana a semana.

Cambios del método v6.2, aprobados por el usuario el 30-oct-2026:
- P-004, flujo neto y sensibilidad a settlements:
  - Los settlements se miden en NETO del día: NNC de todas las familias (bills, CMB, cupones, TIPS, FRN) menos los buybacks que liquidan. Mucha emisión con muchos vencimientos el mismo día puede dejar un neto pequeño o incluso inyectar cash.
  - Sustituyen a settle_bills_nnc20 y settle_cupones_nnc10_dir: settle_neto_absorcion20 (off +2) y settle_neto_inyeccion20 (on +1).
  - La absorción neta puntúa con presión de funding confirmada O con sensibilidad a settlements: que en los últimos días de absorción neta SOFR − IORB (o TGCR − IORB) haya subido, aunque siga por debajo de IORB (≥ 2 pb en alguno, o ≥ 1 pb en dos). Lo calcula el motor.
  - La capa Cash/settlements tiene criterio objetivo, también del motor.
- P-005, expectativas de tipos:
  - FedWatch se compara semana contra semana, con la lectura posterior al FOMC si hubo reunión.
  - Cada dato de EE. UU. de OBJ lleva consenso, anterior y qué resultado sería hawkish o dovish. El motor calcula la probabilidad del día si sale hawkish (off +1) o dovish (on +1), como regla intrasemanal; ex ante no puntúa.
- Evaluación y trading bias orientados a Nasdaq 100, Russell 2000 y FX:
  - Además de la clasificación principal (S&P 500, HY y MOVE, que no cambia), se evalúan pistas paralelas con las mismas probabilidades: Nasdaq 100 (±0,7 %), Russell 2000 (±0,8 %) y AUD/JPY (±0,3 %), cada una con su Brier.
  - BTC no entra.

Cambios del método v6.3, aprobados por el usuario el 1-nov-2026 (corrigen un sesgo risk-off medido: la semana del 26-oct salieron 2 on, 2 neutrales y 1 off, y se emitió off como lo más probable en 3 de 5 días):
- P-012: la regla de presión de funding no cambia y sigue puntuando. Pero el MODO tensión (funding ×2, peso del modelo 80 %, sin techo) solo se activa si, además, otra capa con dato actual confirma estrés: MOVE ≥ 110, HY ≥ +15 / CCC ≥ +40, fails subiendo, XEURBI ≤ −5 ampliándose, SRF material o tensión bancaria. MOVE > 135 lo sigue activando solo. Lo decide el motor: tú sigues poniendo modo_tension.por_funding = presión confirmada.
- P-013: la base se recalibra cada semana con la fórmula del v6.
- P-014: probabilidades exactas, en puntos enteros, nunca on = off si el cálculo inclina hacia un lado. Cada día lleva su porqué: el factor que lo inclina y si es propio del día (settlement neto, subasta, buyback, dato) o solo viene del fondo de la semana.

Cambios de mecánica frente a v6 (desde v6.1):
- Las fechas y los inputs los pone el orquestador.
- Los puentes llegan junto con sus archivos de datos (datos1.json y datos2.json), que se reconcilian en lugar de descargarse de nuevo.
- El cálculo de probabilidades, del GLI proxy G3, del Brier y de la atribución de subidas de funding lo hace motor.py: el modelo elige los factores con su dato y su fecha, y el código pone los puntos, los topes y la fórmula.
- La base vigente se lee del registro.
- Las fuentes se corrigen tras la auditoría del 28-oct-2026.
- La salida incluye datos3.json para el simulador.
- Desde v6.3: flujo neto diario, sensibilidad a settlements, consenso de datos de EE. UU. y pistas Nasdaq/Russell/AUDJPY.

0. BLOQUEO DE FECHAS E INPUTS
ESTE ES UN INFORME NUEVO Y PROSPECTIVO.

FECHAS (las pone el orquestador; mandan sobre cualquier otra fecha):
CORTE (hoy): {CORTE} ({DIA_SEMANA})
REV (semana de revisión, solo evidencia): {REV_LUNES} – {REV_VIERNES}
OBJ (semana objetivo, única con probabilidades): {OBJ_LUNES} – {OBJ_VIERNES}
HACE_20_SEMANAS: {HACE_20_SEMANAS} · HACE_30_SEMANAS: {HACE_30_SEMANAS} · HACE_9_MESES: {HACE_9_MESES} · HACE_18_MESES: {HACE_18_MESES}
CARPETA: {CARPETA}
HISTORIAL: {HISTORIAL} (solo lectura; lo actualiza el orquestador)
BASE VIGENTE (on/neutral/off): {BASE_VIGENTE} (fuente: registro/historial.json; recalibrada por última vez: {FECHA_RECALIBRACION})

INPUTS (archivos en disco; léelos):
- Puente Parte 1: {CARPETA}puente1.txt · Datos: {CARPETA}datos1.json
- Puente Parte 2: {CARPETA}puente2.txt · Datos: {CARPETA}datos2.json
- Puente Parte 3 de la semana anterior (solo 9.0): {PUENTE3_ANTERIOR} · Datos: {DATOS3_ANTERIOR} (o "no disponible")
- Captura del GLI desplazada 90 días: {CAPTURA_GLI} (o "no disponible")
- Motor de cálculo: {MOTOR} (python3 {MOTOR} …)
- Contrato común: reglas de fechas, festivos, estados, umbrales, fuentes y esquemas JSON.

Las semanas que aparezcan en informes anteriores, puentes antiguos o capturas son historia, no un encargo. Prohibido hacer una reconstrucción ex ante o un backtest, y prohibido fijar un corte anterior al CORTE. No hagas preguntas: decide, anota lo que has decidido y sigue.

Puentes 1 y 2: son el input de partida para funding y Treasury. Un puente es utilizable si trae cifras con fecha y su línea "Semanas" coincide con REV y OBJ. Su JSON manda sobre el texto si discrepan (CONTRATO §5).
Puente 3 anterior: solo para 9.0. No aporta datos, fechas ni evidencia.
Captura del GLI (opcional): si existe y su fecha es posterior al viernes de REV, se lee en 6.6 y solo puntúa si dirección y aceleración confluyen (estado USUARIO). Sin captura, el GLI no puntúa.
Si un puente o su JSON falta, no trae cifras o es de otra semana, reconstruye el mínimo con las fuentes de la sección 3 y márcalo "reconstruido en Parte 3":
- Mínimo de Parte 1: SOFR, TGCR, BGCR y EFFR de la misma fecha, más el IORB vigente esa fecha; ON RRP; SRF aceptado; reservas.
- Mínimo de Parte 2: subastas y settlements de OBJ día a día (gross, PHM, NNC y gross de 10Y o más); resultados de las subastas de cupón de REV; buybacks ejecutados; TGA.

Línea de control antes de investigar:
Hoy: … | REV: … – … | OBJ: … – … | Cierres de bonos en REV y OBJ: … | Puente 1: utilizable/reconstruido | Puente 2: utilizable/reconstruido | Puente 3 anterior: sí/no | Captura GLI: sí (fecha)/no | FOMC en REV: sí (fecha)/no | Base: __/__/__

Tres comprobaciones previas:
- OBJ está en el futuro. Su lunes es posterior al CORTE.
- El calendario de Treasury viene de datos2.calendario_obj. Si es de otra semana, reconstrúyelo (sección 5). Prohibido trasladar eventos de una semana a otra.
- Coherencia temporal del puente. Una línea con resultados posteriores al corte del propio puente, o que llama "próximo" a algo ya pasado, queda DESCARTADA hasta reconciliarla.

1. MISIÓN, ALCANCE Y LÍMITES
Tema único: validar o contradecir el riesgo detectado en funding (Parte 1) y Treasury plumbing (Parte 2) con MOVE, fails, crédito, banca, FedWatch, XEURBI y GLI. Después, calcular con el motor las probabilidades diarias de OBJ y dejar la síntesis lista para el informe conjunto.
Fuera de alcance: IA, energía, genética, cuántica, innovación, ciencia, salud, tecnología y política tecnológica. Excepción: las fechas de resultados de las megacaps entran en el calendario de OBJ como evento de dispersión, sin analizar la empresa.
No rehagas Parte 1 ni Parte 2. Reabre un dato concreto solo si:
- hay contradicción entre puente, JSON o un dato fresco;
- viene sin fecha, STALE o no confirmado y hace falta;
- el calendario no corresponde a OBJ.
Sin capa de precio. No construyas la tesis desde equity, DXY, oro, yields ni FX spot. El precio solo aparece en el trading bias final y en 9.0. Los tipos de cambio del GLI forman parte del indicador.
Orden obligatorio: SEMANAS → FRESCURA → RECONCILIAR PUENTES Y JSON → CALENDARIO OBJ → CAPAS → VALIDACIÓN CRUZADA → RÉGIMEN → EVALUACIÓN DE REV → PROBABILIDADES (motor) → TRADING BIAS → AUDITORÍA → RENDER.
Una sola pasada. Si detectas un error, corrígelo volviendo a la fuente concreta, sin reiniciar la investigación.

2. REGLAS DE EVIDENCIA
Dato antiguo ≠ dato actual. Dato no encontrado ≠ señal de tranquilidad. Correlación ≠ transmisión confirmada. Probabilidad que suma 100 % ≠ probabilidad validada.

R1 — Frescura. Todo dato lleva valor · fecha efectiva · fuente · estado.
- Sin fecha efectiva se descarta.
- Prohibido usar valores de informes anteriores, artículos, snippets o ejemplos de este prompt. Cada cifra sale de su fuente o de datos1/datos2 con fecha.
- Umbrales: CONTRATO §4. MOVE con ≤ 2 días hábiles de retraso; XEURBI ≤ 3; FedWatch con actualización ≤ 2; OAS último o penúltimo día hábil; fails, última publicación semanal; GLI proxy G3, último miércoles publicado; captura del GLI, posterior al viernes de REV.
- Un dato STALE se muestra, pero no sostiene conclusiones de régimen ni puntúa.

R2 — Dirección. "Sube / baja / deterioro semanal" exige dos observaciones consecutivas con fecha. Con una sola: "dirección no confirmada". "Cinco sesiones antes" cuenta solo días con el mercado de bonos abierto; las filas de FRED en días de cierre se saltan.

R3 — Observación ≠ inferencia. Equivalencias prohibidas:
- MOVE alto → haircuts más altos.
- Fails elevados → crisis de collateral.
- ON RRP bajo → reservas escasas.
- Pay Down → inyección automática de reservas.
- Gross o NNC → drenaje o risk-off.
- Subasta larga → risk-off.
- GLI cayendo → crisis.
- Sin noticias bancarias → banca sólida.
- Repo tranquilo → buena absorción de duration.
Toda transmisión causal se redacta "compatible con / riesgo de", salvo que la confirmen dos capas con dato actual.

R4 — Sincronía. SOFR-IORB, SOFR-TGCR y EFFR-IORB con valores de la misma fecha.

R5 — Unidades.
- OAS en pb (FRED da %: ×100).
- Fails en millones de USD (la API da dólares: ÷1.000.000).
- TGA y reservas en bn.
- SRF y ON RRP en bn.
- XEURBI en pb.
- GLI en bn.
- NNC y gross en bn.

R6 — Anomalías. Un valor que se aparta bruscamente de sus vecinos y revierte al día siguiente es "posible anomalía de datos": se reporta y no se usa.

Estados: CONTRATO §3. Si una métrica no se encuentra: "dato no encontrado / no disponible en abierto / no confirmado".

Presupuesto: unas 28 fuentes (las Partes 1 y 2 ya traen funding y Treasury). Un reintento y después la alternativa. Pide filas literales a la herramienta web y calcula con código. Si se agota, recorta en este orden: GLI proxy G3 (contexto) → trading bias → CDX → detalle de banca → evaluación de REV. Nunca recortes frescura, calendario de OBJ con su consenso, la lectura de la captura del GLI si existe, la sección 4.1 ni la auditoría.

3. FUENTES (registro completo en CONTRATO §6; aquí, lo propio de la Parte 3)

MOVE
- Fuente: https://www.investing.com/indices/ice-bofaml-move-historical-data. Pide las 12 primeras filas literales.
- Si la última fila tiene más de 2 días hábiles de retraso: busca en la web un cierre fechado del índice ICE BofA MOVE de los días que faltan y márcalo SECONDARY. Si no aparece, STALE.
- No uses Yahoo (histórico desfasado) ni TradingView (sin fecha).

Fails (OFR, FR 2004; pares fecha-valor en dólares; usa las ocho últimas filas)
- Deliver, Treasuries: https://data.financialresearch.gov/v1/series/timeseries?mnemonic=NYPD-PD_AFtD_T-A&start_date={HACE_20_SEMANAS}
- Receive, Treasuries: https://data.financialresearch.gov/v1/series/timeseries?mnemonic=NYPD-PD_AFtR_T-A&start_date={HACE_20_SEMANAS}
- Deliver, total: https://data.financialresearch.gov/v1/series/timeseries?mnemonic=NYPD-PD_AFtD_TOT-A&start_date={HACE_20_SEMANAS}
- Receive, total: https://data.financialresearch.gov/v1/series/timeseries?mnemonic=NYPD-PD_AFtR_TOT-A&start_date={HACE_20_SEMANAS}

Crédito (FRED, en %; pide las 8 últimas filas)
- IG: https://fred.stlouisfed.org/data/BAMLC0A0CM.txt
- HY: https://fred.stlouisfed.org/data/BAMLH0A0HYM2.txt
- Single-B: https://fred.stlouisfed.org/data/BAMLH0A2HYB.txt
- CCC: https://fred.stlouisfed.org/data/BAMLH0A3HYC.txt
- Alternativa: la página de la serie, por ejemplo https://fred.stlouisfed.org/series/BAMLH0A0HYM2.
- CDX IG/HY: solo con una fuente abierta fechada. Si no, "no disponible".

FedWatch
- Fuente: https://www.investing.com/central-banks/fed-rate-monitor. Da la distribución por reunión (actual, día anterior y semana anterior), el precio del futuro y la hora. Estado SECONDARY, derivada de CME.
- Fechas de reunión: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
- Si hubo FOMC en REV, la lectura "actual" tiene que ser posterior a la decisión (hora de actualización después de las 14:00 ET del día de la reunión). Si la fuente solo trae una lectura anterior, el sesgo queda NO CONFIRMADO.

Consenso de datos de EE. UU. (para cada macro1 y macro2 de OBJ)
- Fuente: https://tradingeconomics.com/united-states/calendar. Pide filas literales con las columnas Actual · Anterior · Consenso · Previsión TE, y la hora.
- Usa "Consenso" si existe. Si solo hay "Previsión TE", úsala y márcala "previsión TE (no consenso)".
- Si la página muestra un único valor sin rótulo, no lo asignes: "consenso no confirmado".
- Estado SECONDARY. El evento en sí se sigue verificando con el calendario oficial (BLS, BEA, Census, ISM, Fed).

XEURBI
- Usa la serie de datos1.json. Solo reabre el CSV de CME (https://www.cmegroup.com/reports/cme-xccy-basis-historical-data.csv) si datos1 no la trae o está STALE.

GLI proxy G3 — solo contexto, recortable (FRED y Frankfurter; pide filas literales "fecha,valor")
- WALCL, WTREGEN y WLRRAOL: https://fred.stlouisfed.org/data/<SERIE>.txt. Las 28 últimas filas, semanales del miércoles, en millones de USD.
- BCE: https://fred.stlouisfed.org/data/ECBASSETSW.txt. Las 30 últimas, viernes, en millones de EUR.
- BoJ: https://fred.stlouisfed.org/data/JPNASSETS.txt. Las 10 últimas, mensual, en cientos de millones de JPY.
- Tipos de cambio: https://api.frankfurter.dev/v1/{HACE_30_SEMANAS}..?from=EUR&to=USD,JPY. Pide solo las filas de los miércoles (o el hábil anterior).
- No uses WLRRAL ni las series DEX… de FRED.

Funding y Treasury
- Vienen en datos1 y datos2. Solo si hay que reconstruir, usa las fuentes del CONTRATO §6 y de la Parte 2 (cuidado con el retraso de fiscaldata y con que TreasuryDirect está bloqueada).

Calendario de OBJ
- BLS: https://www.bls.gov/schedule/2026/home.htm (y 2027)
- BEA: https://www.bea.gov/news/schedule
- Census: https://www.census.gov/economic-indicators/calendar-listview-2026.html
- ISM: https://www.ismworld.org/supply-management-news-and-reports/reports/rob-report-calendar/
- FOMC: calendario de la Fed.
- SIFMA: https://www.sifma.org/resources/general/holiday-schedule/
- Earnings de JPM, GS, Citi, BAC, MS y WFC, y de las megacaps (Apple, Microsoft, Nvidia, Amazon, Alphabet, Meta, Broadcom, Tesla): investor relations o nota de prensa con fecha y hora. Si no, un calendario fechado, marcado SECONDARY.

Evaluación (solo 9.0)
- S&P 500: https://www.investing.com/indices/us-spx-500-historical-data
- HY OAS y MOVE: las fuentes de arriba.
- Nasdaq 100: https://fred.stlouisfed.org/series/NASDAQ100 (la página muestra las últimas observaciones; el TXT se corta). Alternativa: https://www.investing.com/indices/nq-100-historical-data.
- Russell 2000: https://www.investing.com/indices/smallcap-2000-historical-data. Publica con varios días de retraso: lo que falte de REV queda null y se completa la semana siguiente (rezagados, 9.0).
- AUD/JPY y USD/JPY: cierres diarios de https://www.investing.com/currencies/aud-jpy-historical-data y …/usd-jpy-historical-data. El fixing del BCE (Frankfurter) solo como alternativa y marcado "fixing BCE": va con medio día de desfase.
- Cesta P-026: RSP https://www.investing.com/etfs/rydex-s-p-equal-weight-historical-data · DXY https://www.investing.com/indices/usdollar-historical-data · VIX https://fred.stlouisfed.org/series/VIXCLS (alternativa: https://www.investing.com/indices/volatility-s-p-500-historical-data) · oro https://www.investing.com/commodities/gold-historical-data · cobre https://www.investing.com/commodities/copper-historical-data · CCC: la serie de crédito de arriba.
- Comprueba que la última fila de cada página es de REV: estas páginas a veces sirven copias atrasadas. Si no lo es, el campo va null y se anota en la auditoría.

4. RECONCILIACIÓN DE PUENTES Y DATOS (antes de cualquier capa)
Tabla R: Afirmación · Valor (puente) · Valor (JSON) · Fecha efectiva · Comprobación · Decisión (ACEPTADO / REABIERTO → nuevo valor y fuente / DESCARTADO / STALE).

Un dato no queda validado por venir en un puente. Comprueba como mínimo:
- **Funding.** Los cuatro tipos y el IORB con la misma fecha; diferenciales recalculados con código desde datos1.tipos. Anota los percentiles p75 y p99 del SOFR frente a IORB (vigilancia, no puntúan).
- **Presión de funding (definición común).** Recalcúlala desde datos1: SOFR ≥ IORB y además (TGCR o BGCR ≥ IORB, o SRF material). Es la que activa el modo tensión. Anota también las sesiones consecutivas y la ventana de calendario que trae datos1; son información y no cambian la regla.
- **ON RRP.** Saldo y fecha. No lo traduzcas a escasez de reservas.
- **SRF.** Aceptado por día. Uso técnico frente a uso material, con el criterio de la Parte 1.
- **TGA** (de datos2). Saldo, fecha, retraso y variación en REV.
- **Cash Ledger** (de datos2). Gross, PHM y NNC por grupo, con la identidad visible y la ruta. Un NNC sin identidad queda NO CONFIRMADO.
- **Flujo neto diario** (P-004). Por día de settlement de REV y de OBJ: Σ NNC de todas las familias − buybacks ejecutados que liquidan ese día (positivo = absorbe cash; negativo = lo inyecta). Si una familia que liquida ese día no tiene NNC, el neto del día es "n/c".
- **Subastas** (de datos2). Resultados de REV, WI y tail, y las condiciones D5 (floja_2de4 y solida). Sin resultados, la absorción de duration queda NO CONFIRMADA.
- **Buybacks.** Solo cuentan los ejecutados.

Si un puente falta o está incompleto: "Puente Parte X no disponible/incompleto; reconstruido en Parte 3". Obtén el mínimo, baja la confianza y no detengas el informe.

4.1 FUNDING: CUÁNDO Y POR QUÉ SUBE SOFR − IORB (medición; no puntúa ni cambia la regla de presión)
Ejecuta: python3 {MOTOR} episodios {CARPETA} {HISTORIAL} {CARPETA}funding_causas.json
El motor une, por día:
- de datos1: SOFR, IORB, TGCR, SRF y ON RRP;
- de datos2: los settlements de REV por familia y tenor, con gross y NNC, y el cierre diario del TGA;
- su calendario: fin e inicio de mes, día 15 y tax dates.
Marca como "subida" el día en que SOFR − IORB sube ≥ 2 pb frente a la sesión anterior publicada, o cruza de negativo a ≥ 0.
Devuelve cuatro cosas:
- (a) la tabla de REV, con SOFR − IORB, el cambio diario, la subida sí/no, el flujo neto del día y las causas coincidentes;
- (b) el acumulado de todas las semanas registradas: cambio medio con y sin cada rasgo (incluidos absorción neta ≥ 20 bn e inyección neta ≥ 20 bn), % de subidas con ese rasgo, cambio medio por tenor liquidado, por tramo de NNC de cupones, y correlaciones cuando hay al menos 8 sesiones;
- (c) sensibilidad_settlement (P-004): mira las últimas 10 sesiones hasta el viernes de REV. En los días de absorción neta ≥ 20 bn, ¿subió SOFR − IORB o TGCR − IORB, aunque siguiera por debajo de IORB? Activa si alguno subió ≥ 2 pb o al menos dos subieron ≥ 1 pb. Trae la evidencia día a día;
- (d) capa_cash: la señal de la capa Cash/settlements con los días de REV:
  - CONFIRMA ESTRÉS: los días de absorción neta reaccionaron con la regla de (c);
  - CONTRADICE ESTRÉS: hubo flujo neto grande (absorción o inyección ≥ 20 bn) sin subidas ≥ 2 pb;
  - MIXTA: hubo subidas sin absorción neta grande ese día;
  - NO CONFIRMADA: sin ledger de REV o sin tipos.
Muestra (a) entera. De (b), muestra los rasgos con muestra suficiente y di cuáles aún tienen muestra pequeña. Muestra (c) con su evidencia.
Copia sin cambios en datos3.json:
- sensibilidad_settlement = {activa, nota} de (c);
- la señal de (d) en la capa "Cash/settlements".
El validador comprueba que coinciden con el motor.
Para cada subida de REV, añade una línea de lectura propia con la causa más probable, usando solo lo que el motor muestra ese día (por ejemplo: "settlement de 2Y/5Y/7Y con NNC +X bn, en inicio de mes"). Si no hay causa identificada, dilo: es información.
No cambies la presión de funding por esta sección. Los puntos solo cambian por la vía del método: la sensibilidad de (c) habilita settle_neto_absorcion20 en OBJ, y lo aplica el motor. Si el acumulado muestra un patrón estable con muestra suficiente, anótalo en la auditoría como "posible propuesta de método", para que el orquestador lo pase a propuestas.

5. CALENDARIO PROSPECTIVO DE OBJ
Tabla C: Día y fecha · Bonos abierto/cerrado · Subastas de cupón · Subastas de bills · Settlements de cupones (gross / PHM / NNC / gross 10Y+) · Settlements de bills (NNC) · Buybacks · **Flujo neto del día (bn)** · Fin de mes/trimestre · Tax date · Eventos macro (fuente oficial) · Consenso / anterior · Anuncio del QRA · Earnings de los seis grandes bancos · Earnings de megacaps (antes de la apertura / tras el cierre) · Estado.

- **Treasury:** de datos2.calendario_obj y datos2.ledger, si su OBJ coincide.
- **Eventos macro:** solo los del calendario oficial para ese día exacto. Un evento no verificado no existe para el informe, no puntúa y no puede ser dominante. No completes el calendario de memoria.
- **Earnings:** tras el cierre cuentan para el día hábil siguiente; antes de la apertura, para ese mismo día. Los bancos regionales son contexto.
- **Días de mercado cerrado:** sin subastas ni settlements.
- **Flujo neto de OBJ:** con datos2.ledger, el neto de cada día de settlement de OBJ (Σ NNC − buybacks que liquidan). Indica el día de mayor absorción neta y el de mayor inyección neta.
- **Consenso:** para cada macro1 y macro2, el consenso y el anterior de la fuente de la sección 3, más una línea de "hawkish si … / dovish si …" con criterio explícito (por ejemplo: "hawkish si CPI subyacente m/m ≥ consenso + 0,1"). Si el consenso no está confirmado, el evento sigue puntuando como dispersión, pero no lleva regla macro.

Integridad: COMPLETO A FECHA DE CORTE / PARCIAL (qué falta).

6. CAPAS DE CONFIRMACIÓN
Cada capa termina con su frase de cierre y la etiqueta: Señal: CONFIRMA ESTRÉS / CONTRADICE ESTRÉS / MIXTA / NO CONFIRMADA · Dato: actual / stale. Una capa con dato STALE o ausente vale NO CONFIRMADA.

6.1 MOVE y collateral multiplier
- **Recoge:** cierre y fecha; cambio diario; cambio frente a cinco sesiones antes; máximo y mínimo de REV; zona; retraso de la fuente.
- **Zonas:** < 80 tranquilo · 80–110 vigilancia · 110–135 tensión · > 135 peligro macro/liquidez.
- **Lectura, siempre como riesgo:**
  - MOVE bajo: collateral multiplier más estable.
  - MOVE subiendo: más riesgo de haircuts, menos rehypothecation y menos balance. Solo es "deterioro confirmado" si lo acompañan fails subiendo, repo tensionado o SRF material.
  - MOVE subiendo con yields bajando: volatilidad de un rally refugio.
  - MOVE bajo no basta para decir que todo está limpio.
- **Cierre:** "Lectura MOVE: confirma/contradice estrés. Intensidad: leve/moderada/extrema."

6.2 Fails y collateral stress
- **Recoge:** las cuatro series, con las tres últimas observaciones de cada una y su fecha.
- **Dirección:** la última frente a la anterior. Indica también si la última está sobre o bajo la media de las ocho semanas.
- **"Fails subiendo":** exige que suban las dos patas de Treasuries. Si una sube y la otra baja, la dirección es mixta.
- **Retraso:** di expresamente que la referencia suele ser anterior a REV.
- **Lectura:** bajos/estables = collateral funcionando · subiendo = fricción · altos con MOVE subiendo y repo tensionado = riesgo de cascada.
- **Sin dato:** "No puedo afirmar que collateral esté limpio; fails no confirmado."
- **Cierre:** "Lectura fails: collateral funcionando/fricción/deterioro. Dirección: confirmada/no confirmada."

6.3 Crédito y banca
- **Crédito:** IG, HY, Single-B y CCC en pb, con su fecha y su variación frente a cinco sesiones antes.
  - Crédito comprimido contradice crisis sistémica.
  - HY y CCC ampliando confirman deterioro.
  - IG estable con CCC débil es vulnerabilidad de cola.
- **Banca:** depósitos, NII, coste de funding, provisiones, calidad de activos, CRE, private credit y NBFIs, cada afirmación con dato y fecha. Indica qué bancos publican en OBJ.
  - "Bancos sólidos" solo con dato. Sin él: "banca no confirmada".
  - CRE, private credit y NBFIs son vulnerabilidad estructural, salvo que haya dato actual.
- **Contraargumento obligatorio:** "Un escéptico diría que si realmente hubiera un liquidity event inminente, HY/IG no estarían en ___."
- **Cierre:** "Lectura crédito/banca: tensión actual sí/no/no confirmada. Vulnerabilidad estructural sí/no."

6.4 Mini macro: FedWatch frente a la semana pasada y consenso de OBJ
Las expectativas de tipos mueven el risk-on/off. Se miden en dos tiempos: lo que ya cambió (FedWatch semana contra semana) y lo que puede cambiar en OBJ (datos frente a consenso).
- **Lectura semanal:** "actual" frente a "semana anterior" de la fuente. Si hubo FOMC en REV, la lectura actual es posterior a la decisión y la variación semanal incluye la reunión: dilo. No se usa la variación diaria para el sesgo.
- **Para las tres próximas reuniones** (fechas verificadas):
  - distribución completa actual y de la semana anterior;
  - probabilidad de recorte, de no cambio y de subida respecto al rango vigente, y su variación semanal en puntos;
  - tipo implícito = 100 − precio del futuro;
  - movimientos descontados hasta fin de año.
- **Fuente:** indica la hora de actualización y que es SECONDARY.
- **Sesgo:** se clasifica con la distribución de las tres reuniones, usando la probabilidad agregada de recorte y de subida de cada una.
  - Variación < 5 puntos en las tres: "estable".
  - ≥ 5 puntos en alguna hacia subidas o menos recortes: "hawkish".
  - Hacia recortes o menos subidas: "dovish".
- **Sin fuente:** "dato histórico semanal de FedWatch no confirmado"; el sesgo queda no confirmado.
- **Lectura:**
  - más recortes con funding estable = alivio;
  - más recortes con crédito débil = recession pricing;
  - menos recortes o más subidas, con emisión larga o con SOFR cerca de IORB = riesgo de duration indigestion o de funding pressure.
- **Datos de OBJ frente a consenso:** Tabla M con Día · Hora ET · Dato · Nivel (macro1/macro2) · Consenso · Anterior · Hawkish si · Dovish si · Fuente/estado.
  - Elige el criterio con el sesgo actual: con FedWatch descontando recortes, un dato fuerte de empleo o inflación es el que más mueve hacia hawkish.
  - Para cada dato con consenso confirmado, añade a datos3.reglas_actualizacion {tipo: "macro", evento, dia, consenso, anterior, hawkish_si, dovish_si}. Si el dato sale antes de la apertura, el día es ese mismo; si sale tras el cierre, el día hábil siguiente.
  - Escribe la Tabla M también en datos3.macro_obj.
- **Cierre:** "Lectura mini macro/FedWatch: … frente a la semana pasada. Datos de OBJ más capaces de mover las expectativas: … Implicación para liquidez: alivio/tensión/neutro."

6.5 EUR/USD CME XEURBI
- **Serie:** la de datos1, con los diez últimos valores con fecha, el último valor, el mínimo y el máximo de REV, la variación frente a cinco sesiones antes y el retraso.
- **Trayectoria:** descríbela día a día. Aplica R6. Solo vale XEURBI de CME.
- **Lectura:** cerca de 0 no confirma estrés · negativo y estable = fricción leve · más negativo y ampliándose = presión creciente · junto con MOVE, fails, crédito o funding deteriorándose = confirmación más seria.
- **Cierre:** "Lectura EUR/USD CME XEURBI: estrés offshore USD frente a EUR confirmado/no confirmado."

6.6 GLI: liquidez global, dirección y aceleración (OPCIONAL)
El GLI actúa con unos 90 días de adelanto, pero la confluencia de dirección y aceleración no se da todas las semanas, ni siquiera todos los meses. Por eso la capa es opcional y solo puntúa cuando hay señal:
1. **Captura válida en {CAPTURA_GLI}.** Lee la pendiente de la línea amarilla (dirección) y la de la verde (aceleración) entre el lunes y el viernes de OBJ, y en REV para saber si es la primera o la segunda semana del estado.
   - Solo hay señal si las dos líneas van en el mismo sentido: las dos bajando = gli_contraccion_acelerada; las dos subiendo = gli_expansion_acelerada.
   - En cualquier otro caso (sentidos opuestos, plano o lectura dudosa) la capa queda "sin señal (GLI)" y no puntúa.
   - Las cifras se rotulan "lectura aproximada de la captura". Ignora las etiquetas del eje y las velas.
   - En datos3.gli.puntua pon fuente "captura", el estado leído y la semana.
2. **Sin captura.** La capa queda "sin señal (GLI opcional, sin captura)". No puntúa, no cuenta como NO CONFIRMADA y no baja la confianza. En datos3.gli.puntua pon fuente "ninguna".
3. **GLI proxy G3 (contexto, nunca puntúa).** Si el presupuesto lo permite, calcúlalo como estado actual medido y como fila desplazada 13 semanas. Sirve para contrastar la captura. No lo uses como sustituto: confluye en más de la mitad de las semanas (12 de 20 a 21-oct-2026), mucho más que el indicador del usuario. El motor descarta cualquier factor GLI sin captura.

Procedimiento:
1. Descarga las series de la sección 3.
2. Escríbelas en {CARPETA}gli_input.json con el formato que documenta motor.py: walcl, wtregen, wlrraol, ecb, boj y fx como listas [fecha, valor] o [fecha, eurusd, eurjpy].
3. Ejecuta: python3 {MOTOR} gli {CARPETA}gli_input.json {OBJ_LUNES} {CARPETA}gli_resultado.json
4. El motor aplica la construcción del v6:
   - Fed neta = (WALCL − WTREGEN − WLRRAOL)/1.000.
   - BCE × EURUSD.
   - BoJ × 0,1 / USDJPY, publicada desde el día 5 del mes siguiente.
   - Δ4, A y umbral del 0,5 %.
   - Estados y descomposición en balances / TGA / ON RRP / dólar, con Δ4 a tipo de cambio constante y aviso de salto de la BoJ.
5. Muestra la tabla de los nueve últimos miércoles (fecha · Fed neta · BCE · BoJ · GLI · Δ4 · A · estado) y la fila desplazada, rotuladas "contexto".

Etiqueta la causa dominante: "por balances", "por TGA", "por ON RRP" o "por dólar fuerte". Si falta un componente, el GLI proxy G3 queda NO CONFIRMADO. Llámalo siempre "GLI proxy G3"; no es el GLI de CrossBorder Capital.

**Concordancia** (solo con captura): ¿la captura y el proxy desplazado apuntan en la misma dirección?

**Cierre:** "Lectura GLI para OBJ: [captura: estado, primera/segunda semana / sin señal]. Contexto GLI proxy G3 actual: [estado] (semana anterior: [estado]); Δ4 = … bn; A = … bn; causa dominante: … (o "no calculado")."

7. VALIDACIÓN CRUZADA
Responde a cada pregunta con: respuesta · dato (valor y fecha) · estado. Si el dato falta o está STALE, la respuesta es "no confirmado", nunca "no".

1. ¿Funding confirma tensión repo, generalizada o localizada? ¿Qué explicó las subidas de REV (sección 4.1)?
2. ON RRP: ¿qué saldo queda? Por separado: ¿hay evidencia propia de escasez de reservas? ¿El SRF muestra estrés, uso técnico o ningún uso?
3. ¿Hay presión de funding confirmada (definición común)? Activa el modo tensión.
4. ¿Los resultados de subasta confirman mala absorción de duration?
5. ¿Qué días de OBJ concentran subastas y settlements de deuda larga? ¿Alguno cumple las condiciones de dirección del Paso 2?
6. ¿Los buybacks ejecutados amortiguan, y cuánto frente al NNC?
7. ¿El flujo neto de REV absorbió o inyectó cash, y SOFR/TGCR − IORB reaccionó (sensibilidad a settlements, 4.1 c)? ¿Qué días de OBJ absorben o inyectan en neto?
8. ¿MOVE es compatible con un deterioro del collateral multiplier? ¿Lo confirma otra capa?
9. ¿Los fails confirman deterioro de collateral?
10. ¿El crédito confirma o contradice un liquidity event?
11. ¿FedWatch alivia o empeora duration/funding? ¿Qué dato de OBJ puede moverlo más?
12. ¿XEURBI confirma o contradice el estrés offshore en USD?
13. GLI (opcional): ¿la captura muestra confluencia en OBJ? Si no hay captura o no hay confluencia: "sin señal".
14. ¿Qué indicador lidera el riesgo y cuál contradice más la tesis de estrés?

Tabla V: Capa · Señal · Dato actual sí/no · Cuenta para probabilidades sí/no.
La capa Cash/settlements toma la señal del motor (4.1 d). Las capas son: Funding · Auctions/duration · Cash/settlements · MOVE · Fails · Crédito · Banca · FedWatch · XEURBI, más GLI cuando hay captura. Son 9 capas aplicables, o 10 con captura. Un GLI "sin señal" se lista con esa etiqueta y no cuenta como NO CONFIRMADA.

Contradicciones abiertas: lista las que no hayas resuelto.

8. DIAGNÓSTICO DE RÉGIMEN
A) Normalización · B) Estrés incipiente · C) Estrés sistémico · D) Crisis de liquidez.

Mínimos (solo cuentan las capas con dato actual):
- B: 2 capas confirman estrés.
- C: 4 capas, entre ellas funding y crédito.
- D: lo de C más SRF con uso material o disfunción de funding observada.
- Sin B pero con 3 o más capas NO CONFIRMADAS: "A provisional, con evidencia insuficiente".

Reglas:
- Si el régimen cambia respecto al puente, nombra el dato nuevo que lo justifica.
- Si B se alcanza justo en el mínimo, nombra la capa que lo devolvería a A.
- Probabilidades por régimen: múltiplos de 5 que sumen 100, cada una con su evidencia.
- Confianza, según la proporción de capas aplicables con dato actual: ≥ 80 % alta (8 de 10, u 8 de 9) · 60–79 % media (6–7 de 10, 6–7 de 9) · < 60 % baja. Es juicio estructurado, no un modelo estadístico.
- Explica qué capa lidera, cuál contradice, qué dato puede cambiar la tesis y cuál sigue sin confirmar.
- Prohibido "dato no confirmado más importante: ninguno" si alguna fila está en PENDING, STALE, SECONDARY, CONFLICT o NOT AVAILABLE.

9. PROBABILIDADES DIARIAS DE OBJ (método v6, calculadas por motor.py)

9.0 Evaluación de la semana anterior
**Datos.** Para cada día de REV recoge en datos3.json → evaluacion_rev.dias:
- la cesta de cinco canales (P-026), cambios diarios de cierre a cierre:
  - renta variable: Russell 2000 (rut_pct), S&P 500 equiponderado RSP (rsp_pct), Nasdaq 100 (ndx_pct) y S&P 500 (spx_pct, que sustituye a RSP si falta);
  - crédito: HY OAS (hy_pb) y CCC OAS (ccc_pb), en pb diarios;
  - tipos y colateral: MOVE (move_pct);
  - dólar y carry: DXY (dxy_pct), AUD/JPY (audjpy_pct) y USD/JPY (usdjpy_pct), con cierres de Nueva York, no el fixing del BCE;
  - refugio: VIX (vix_pct) y la relación oro/cobre (oro_cobre_pct, cambio % del cociente de futuros);
- si tienes 21 cierres o más de un activo, añade su σ de 20 sesiones en evaluacion_rev.sigmas = {campo: σ}; si no, el motor usa la de respaldo (HY, CCC y MOVE salen de datos3.series);
- el dato que no haya salido por retraso va como null; no lo estimes.
- causa (P-025, interna): para cada día que el motor clasifique on/off, evaluacion_rev.dias[].causa ∈ liquidez / sector / politico_macro / desconocida, con causa_motivo en una línea. Decide con la amplitud (¿cae solo un sector o un canal?) y con el funding de ese día (¿apretó o se relajó?). No se escribe en el informe final ni en la web.

**Rezagados.** Si la evaluación de la semana anterior (en {HISTORIAL}, semanas[-1].pistas_rev) dejó días "nc" por retraso, búscalos ahora y escríbelos en evaluacion_rev.rezagados = [{fecha, rut_pct|ndx_pct|audjpy_pct}]. El orquestador los completa en el historial.

**Cálculo.** Ejecuta: python3 {MOTOR} evaluar {CARPETA}datos3.json {DATOS3_ANTERIOR}
- Si no hay DATOS3_ANTERIOR pero sí PUENTE3_ANTERIOR, crea {CARPETA}datos3_anterior_min.json con resultado.dias = [{fecha, prob:{on,neu,off}}] y resultado.base, copiados de las líneas del puente, y úsalo.
- El motor clasifica cada día con la cesta (P-026):
  - cada movimiento se divide por su σ de 20 sesiones, con el signo del riesgo (VIX, DXY, MOVE y diferenciales que suben = off) y recortado a ±3;
  - nota del canal = media de sus activos; nota del día = media de los canales con dato;
  - risk-on / risk-off (día fuerte) si la nota es ≥ +0,75 / ≤ −0,75 y al menos 3 canales apuntan igual (|canal| ≥ 0,25);
  - lateral alcista / lateral bajista si la nota es ≥ +0,25 / ≤ −0,25; lateral en el resto;
  - "no clasificable" si falta el canal de crédito o hay menos de 3 canales con dato;
  - guarda también la clasificación anterior (2 de 3 con S&P, HY y MOVE) como clasif_anterior, para comparar.
- Calcula también el Brier frente a la base y frente a 30/40/30.
- Para cada pista paralela, con las mismas probabilidades emitidas: risk-off si cae al menos el umbral (Nasdaq −0,7 %, Russell −0,8 %, AUD/JPY −0,3 %), risk-on si sube al menos el umbral, y neutral en el resto. Calcula su Brier y su Brier de base. No cambia la base ni la recalibración.

**Añade a mano:**
- la causa de cada día on/off, con una línea sobre lo que lo movió y si coincide con el evento puntuado (en el informe, sin la etiqueta interna de P-025);
- qué canales de la cesta movieron el día y cuál discrepó;
- los días de deuda larga, con cuántos fueron off y cuántos on;
- los días de absorción e inyección neta, con cuántos fueron off y cuántos on (en la clasificación principal y en Russell);
- dónde divergieron las pistas de la clasificación principal (por ejemplo, Russell off con S&P neutral) y qué capa lo explica;
- una línea de observación para el puente.

Sin puente anterior: "Evaluación de REV no disponible".

9.1 Principio (v6)
- La oferta del Tesoro, la macro y las megacaps aumentan la dispersión, no la dirección: suman lo mismo a on y a off.
- La dirección solo sale de datos con signo conocido y, sobre todo, de la presión de funding confirmada o de la sensibilidad demostrada a settlements.
- El fondo de la semana inclina, no decide.
- Sin presión de funding ni MOVE > 135, ningún resultado pasa del 60 %.
- Se calcula desde cero cada semana y solo para OBJ.

9.2 Qué decides tú y qué calcula el motor
Tú decides qué factores aplican, con dato y fecha actuales, usando EXACTAMENTE estos identificadores del catálogo de motor.py. El motor asigna los puntos del v6.

PASO 1 — Dispersión del día (lista "dispersion" de cada día; solo eventos verificados en la Tabla C):
- sub_10y_30y (±2): subasta de 10Y o 30Y, nueva o reapertura.
- sub_20y (±1,5).
- sub_5y_7y (±1).
- tips_10y_mas (±1).
- sub_2y_3y (±0,5).
- tips_5y (±0,5).
- settle_cupones_nnc10 (±0,5): settlement de cupones con NNC ≥ +10 bn.
- macro1 (±2): CPI, Employment Situation, decisión FOMC, PCE. Una entrada por evento.
- macro2 (±1): PPI, ventas minoristas, ISM, JOLTS, PIB, actas FOMC, earnings de los seis grandes bancos. Una entrada por evento.
- megacaps (±1 en total por día).
- qra (±1): anuncio de refinanciación trimestral (Policy Statement), solo ese día y con la fecha verificada en home.treasury.gov o en el calendario de la Parte 2.
- El motor aplica "dos subastas de cupón el mismo día: la mayor entera, la otra a la mitad".

PASO 2 — Dirección del día (lista "direccion"):
- subasta_cupon_condiciones_2de3 (off +1): subasta de cupón de 5Y o más que cumple 2 de 3:
  - previas flojas (datos2: floja_2de4 de la última subasta del mismo tenor);
  - MOVE ≥ 110;
  - FedWatch hawkish.
- tips_condiciones (off +0,5): TIPS con MOVE ≥ 110 y FedWatch hawkish.
- settle_neto_absorcion20 (off +2): el flujo neto del día (Σ NNC de todas las familias − buybacks que liquidan) absorbe ≥ +20 bn. Una entrada por día, aunque liquiden varias familias. Puntúa con presión de funding confirmada O con sensibilidad a settlements activa (4.1 c); si no hay ninguna, el motor lo pone a 0.
- settle_neto_inyeccion20 (on +1): el flujo neto del día inyecta ≥ 20 bn (neto ≤ −20 bn: vence más de lo que se emite y se recompra). Puntúa siempre; se redacta "compatible con alivio de cash", no "inyección de reservas" (R3).
- fin_mes (off +1) · fin_trimestre (off +2) · tax_date (off +1): solo con presión de funding confirmada.
- buyback_liquidez (on +1): buyback de liquidez ejecutado que liquida ese día. Si ya está descontado en el neto y el neto llega a −20 bn, puntúan los dos: uno mide el flujo y otro la operación.
- Incluye siempre los factores si el evento existe: el motor los pone a 0 cuando no se cumple su condición y lo deja en la traza.
- dato_hawkish y dato_dovish no se ponen ex ante: son las reglas macro de actualización.

PASO 3 — Fondo de la semana (lista "fondo"; solo capas con dato actual):
- Liquidez global (solo con captura y confluencia; el motor lo descarta si no hay captura): gli_contraccion_acelerada (off 1) · gli_expansion_acelerada (on 1).
- Funding:
  - sofr_ge_iorb (off 1) · gc_ge_iorb (off 1) · srf_material (off 1);
  - fails_subiendo_sobre_media (off 0,5): las dos patas suben y la última está sobre la media de 8 semanas;
  - xeurbi_le_m5_ampliando3 (off 0,5): ≤ −5 pb y ampliándose ≥ 3 pb en la semana;
  - sofr_le_iorb_m5_gc_estable (on 1).
- Tipos y duration:
  - move_110_135 (off 1) · move_80_110_subiendo10 (off 0,5): +10 % o más en la semana · move_lt_80 (on 1) · move_gt_135 (off 3, solo en modo tensión);
  - fedwatch_hawkish (off 1) · fedwatch_dovish_credito_ampliando (off 1) · fedwatch_dovish_credito_estable (on 1).
- Crédito y banca:
  - hy_ge_15 (off 1) · hy_5_15 (off 0,5) · ccc_ge_40 (off 1);
  - tension_bancaria (off 1): con dato de depósitos, coste de funding o provisiones;
  - hy_le_m10 (on 1).

PASO 4 — Modo tensión (datos3.modo_tension):
- por_funding = presión de funding confirmada con dato actual (el motor solo activa el modo tensión si otra capa confirma, P-012; si no, lo avisa y calcula en modo normal: dilo en el informe);
- por_move = MOVE > 135 con dato actual;
- sin dato actual de funding, el modo tensión no se activa.

El motor aplica:
- regla de grupo: el mayor factor entero y los demás a la mitad;
- topes: 1 por grupo y 2 por lado en modo normal; 4 por grupo, 6 off y 2 on en modo tensión;
- funding ×2 en tensión por funding;
- fórmula: S_off = ln(base_off/base_neu) + 0,2·Pts_off · S_on = ln(base_on/base_neu) + 0,2·Pts_on;
- softmax con neutral = 1;
- mezcla con la base según la confianza: alta 60/80 · media 50/70 · baja 40/60; un día con evento sin verificar va a confianza baja;
- techo del 60 % sin tensión, probabilidades exactas en puntos enteros sin empate on = off (P-014) y neutral ≥ 20 % sin tensión;
- el autotest contra la tabla de control del v6.

Ejecuta:
python3 {MOTOR} selftest      (debe decir "selftest OK"; si no, no sigas: avisa en la auditoría)
python3 {MOTOR} prob {CARPETA}datos3.json

El motor añade a datos3.json el bloque "resultado": probabilidades por día, traza, topes, S_off/S_on, modelo, mezcla, techo, sensibilidad si se activara el modo tensión y reglas de actualización de cada subasta. Copia esas cifras al informe sin modificarlas. Si el motor emite avisos, explícalos en la auditoría.

Reglas de actualización intrasemanal:
- **Subastas:** para cada subasta de cupón de 5Y o más de OBJ, añade a datos3.reglas_actualizacion {subasta, fecha_subasta, dia_settlement}. El motor calcula la probabilidad del día del settlement si la subasta sale floja (off +1) o sólida (on +1). Si el settlement cae fuera de OBJ, indícalo y no lo calcules.
- **Datos de EE. UU. (P-005):** las reglas {tipo: "macro", …} de 6.4. El motor calcula la probabilidad del día si el dato sale hawkish (off +1) o dovish (on +1).

9.3 Tablas de salida
**Tabla P1. Mapa diario:**
- Columnas: Día (fecha) · Dispersión (±) · Dirección (off/on) · Fondo (off/on) · Total (off/on) · Modo · Prob. on · Prob. neutral · Prob. off · Confianza · Evento dominante · Por qué (hacia dónde inclina y por qué: propio del día o solo fondo).
- Todas las cifras son del motor.
- En un día con bonos cerrados, dilo y di a qué mercados se refiere la probabilidad.

**Tabla P2. Traza:** cada factor con su dato, su fecha y sus puntos (de resultado.fondo.traza y de la traza de cada día), la regla de grupo y los topes aplicados, S_off, S_on, el modelo, la mezcla, el techo y el redondeo.

**Sensibilidad:**
- Para cada día, el dato que movería el risk-off 5 puntos o más.
- Usa resultado.si_modo_tension para "si se activa el modo tensión, pasa de X a Y".
- Usa resultado.reglas_actualizacion para cada subasta y cada dato de EE. UU.

Después responde, con día y motivo en una línea:
- día más risk-on;
- día más risk-off;
- día con más dispersión;
- día más dependiente de auction outcome;
- día más dependiente de FedWatch o de un dato frente a consenso;
- día de mayor absorción neta y de mayor inyección neta;
- día más peligroso si se activa el modo tensión.

10. TRADING BIAS MACRO, SUBORDINADO A FUNDING (foco: Nasdaq 100, Russell 2000 y FX)
Transmisión que se vigila, siempre como "compatible con / riesgo de" (R3):
- **Russell 2000:** el más sensible a funding, crédito y expectativas de tipos cortos (más deuda a tipo variable y refinanciación). Lee juntos la sensibilidad a settlements, HY/CCC y FedWatch.
- **Nasdaq 100:** más sensible a duration y tipos reales. Lee juntos las subastas largas, MOVE y FedWatch; las megacaps solo como dispersión.
- **FX:** AUD/JPY y NZD/JPY son el barómetro de carry y apetito por riesgo; USD/JPY, de diferencial de tipos; EUR/USD, de XEURBI y del sesgo de la Fed.

Los pares FX solo se emiten si se cumplen las tres condiciones:
- funding sincronizado con dato actual;
- calendario de OBJ completo a fecha de corte;
- sesgo FedWatch confirmado.

Si falla alguna, el sesgo va en condicional y se escribe "Pares FX: no se emiten; falta [condición]".

Un sesgo solo es "firme" si algún día de OBJ tiene on u off ≥ 50 % y la capa de la que depende tiene dato actual. Si no, todos son condicionales con "convicción baja".

Activos: Nasdaq 100 · Russell 2000 · USD · AUD/JPY · NZD/JPY · USD/JPY · EUR/USD · GBP · CHF · CAD · Bonos (corto / largo) · Gold · Pares FX (1, 2, 3). Cada sesgo indica de qué capa depende y en qué días de OBJ se concentra (por ejemplo: "Russell, sesgo bajista condicional el día de absorción neta si la sensibilidad sigue activa"). La última evaluación de las pistas (9.0) se cita para dar contexto, no para cambiar el sesgo.

11. OUTPUT (español; las tablas mandan, la prosa mínima)
Escribe el informe en {CARPETA}parte3.md.

Título: Diagnóstico de liquidez global — Parte 3: MOVE, fails, crédito, FedWatch, GLI y probabilidades finales

**0. Control de frescura de datos**
- Línea de control.
- Tabla "Acceso a fuentes": Fuente · Abrió · Alternativa · Último dato · Retraso.
- Tabla de frescura (Métrica · Último dato · Fecha efectiva · Observación anterior comparable · Fuente · Estado) con estas filas: MOVE · fails D/R Treasuries y total · IG/HY/B/CCC OAS · FedWatch actual y semana anterior (y hora: posterior al FOMC si lo hubo) · consenso de datos de OBJ · XEURBI · captura del GLI (opcional) · GLI proxy G3 (contexto) · SOFR/TGCR/BGCR/EFFR/IORB · SRF · ON RRP · TGA · reservas.
- "Datos stale o no confirmados: …".

**Primera frase analítica**, redactada al final y mostrada arriba: "Estado actual de confirmación macro-financiera: … (confianza …). Modo de probabilidades: normal / tensión." Debe coincidir con el bloque puente.

**Secciones, en este orden:**
1. Control de frescura
2. Reconciliación (Tabla R)
2b. Funding: cuándo y por qué sube (4.1)
3. Calendario OBJ (Tabla C)
4. MOVE
5. Fails
6. Crédito y banca
7. FedWatch y consenso de OBJ (Tabla M)
8. XEURBI
9. GLI (opcional)
10. Validación cruzada
11. Diagnóstico final
12. Evaluación de la semana anterior
13. Probabilidades (P1, P2, sensibilidad, seis respuestas)
14. Trading bias
15. Auditoría
16. Bloque Puente Parte 3

**Bloque puente.** Escríbelo también en {CARPETA}puente3.txt:

BLOQUE PUENTE PARTE 3 — CONFIRMACIÓN FINAL

Alcance:
Corte: __ · REV: __ · OBJ: __ · Cierres de mercado en OBJ: __
Puentes: Parte 1 utilizable/reconstruido · Parte 2 utilizable/reconstruido · Captura GLI: sí (fecha) / no
Calendario OBJ: completo a fecha de corte / parcial (falta: __)
Confianza general: alta / media / baja
Método de probabilidades: v6.3 (motor.py) · base __/__/__ · modo normal / tensión · sensibilidad a settlements activa / inactiva

Estado final preliminar:
normalización / estrés incipiente / estrés sistémico / crisis de liquidez

Probabilidades por régimen:
Normalización: __ · Estrés incipiente: __ · Estrés sistémico: __ · Crisis de liquidez: __

MOVE: valor __ · fecha __ · cambio semanal __ · lectura __
Fails: valor/dirección __ (confirmada / no confirmada) · referencia __ · lectura __
Crédito: IG __ · HY __ · B __ · CCC __ (pb; fecha __) · lectura __
Banca: __ (con dato / no confirmada)
FedWatch: sesgo dovish / hawkish / estable / no confirmado (lectura __, posterior al FOMC sí/no/no aplica) · implicación alivio / tensión / recession pricing / neutro
Datos de OBJ frente a consenso: [día] [dato] consenso __ (anterior __) · hawkish si __ · dovish si __ (uno por dato con regla)
EUR/USD CME XEURBI: valor __ · fecha __ · lectura __
GLI (opcional):
para OBJ: captura (fecha __) · estado __ (primera/segunda semana) / sin señal
contexto proxy G3: estado __ (anterior: __) · fecha __ · Δ4 __ bn · A __ bn · causa __ / no calculado

Funding reconciliado:
SOFR-IORB __ pb (fecha __) · TGCR/BGCR __ · SRF __ · ON RRP __ · TGA __ (fecha __) · Reservas __
presión de funding confirmada: sí / no
Subidas de SOFR-IORB en REV: [fecha] Δ __ pb · causa __ (una por subida, o "ninguna")
Flujo neto REV: [fecha] __ bn (absorbe/inyecta) · reacción SOFR/TGCR − IORB __ pb (uno por día con settlement)
Sensibilidad a settlements: activa / inactiva · __ (nota del motor) · Capa Cash/settlements: __
Flujo neto OBJ: [fecha] __ bn (uno por día con settlement) · mayor absorción __ · mayor inyección __
Patrón acumulado de funding: __ (rasgo con muestra suficiente y su efecto medio, o "muestra aún pequeña")

Probabilidades diarias de OBJ (on / neutral / off · pts off/on · modo · evento dominante):
Lunes __: __ / __ / __ · __ · __ · __ · por qué __
Martes __: __ / __ / __ · __ · __ · __ · por qué __
Miércoles __: __ / __ / __ · __ · __ · __ · por qué __
Jueves __: __ / __ / __ · __ · __ · __ · por qué __
Viernes __: __ / __ / __ · __ · __ · __ · por qué __

Reglas de actualización intrasemanal:
[subasta]: floja → [día del settlement] __ % risk-off · sólida → __ %
[dato]: hawkish → [día] __ % risk-off · dovish → __ %
Modo tensión activado: lunes __ · martes __ · miércoles __ · jueves __ · viernes __ (risk-off)

Mapa diario final:
Más risk-on __ · Más risk-off __ · Más dispersión __ · Más sensible a auction __ · Más sensible a FedWatch/consenso __ · Más peligroso con modo tensión __ · Mayor absorción neta __ · Mayor inyección neta __

Evaluación de la semana anterior:
Brier __ (base __: __ · 30/40/30: __) · resultados REV on/neu/off __/__/__ · días de deuda larga: __ off y __ on de __ · observación __
Pistas: Nasdaq 100 Brier __ (base __) · Russell 2000 Brier __ (base __; pendientes __) · AUD/JPY Brier __ (base __)

Indicador líder: __ · Indicador que más contradice: __ · Dato no confirmado más importante: __
Contradicciones abiertas: __ · Principal riesgo: __ · Principal alivio: __

Trading bias subordinado (firme / condicional · convicción alta / baja):
Nasdaq 100 __ · Russell 2000 __ · USD __ · AUD/JPY __ · NZD/JPY __ · USD/JPY __ · EUR/USD __ · GBP __ · CHF __ · CAD __ · Bonos __ · Gold __
Pares FX: 1) __ 2) __ 3) __ (o "no se emiten; falta __")

Frase final preliminar:
"No estamos en crisis de liquidez mientras ___, pero la tesis cambia si ___."

Cierre fijo:
"Probabilidades calculadas solo para OBJ con el método v6.3 (motor.py) y la información disponible al corte. No reutilizar en informes posteriores, salvo para medir aciertos."

**datos3.json.** Debe tener el esquema del CONTRATO §7, con:
- capas, régimen, fondo, días, reglas de actualización (subastas y macro), modo de tensión, sensibilidad_settlement y confianza;
- macro_obj (Tabla M) y flujo_neto_obj [{fecha, neto_bn}];
- series de MOVE, XEURBI, HY, CCC, IG, B y SOFR-IORB;
- FedWatch (con la hora de la lectura), GLI (puntua.fuente = "captura" o "ninguna") y evaluación de REV con las pistas y los rezagados;
- el bloque "resultado" del motor.

Incluye además "base": la BASE VIGENTE de la cabecera como lista [on, neu, off], y las series con este formato: move [{fecha, valor}], xeurbi [{fecha, pb}], hy/ccc/ig/b [{fecha, pb}], sofr_iorb [{fecha, pb}].
Valida con código que es JSON correcto.

12. AUDITORÍA FINAL (✓ o explicación, una línea cada uno)
- Fechas: OBJ posterior al CORTE; las cinco filas de P1 son de OBJ; sin reconstrucción ex ante.
- Calendario: nada trasladado de otra semana; macro y earnings verificados para su día exacto; cierres SIFMA comprobados.
- Frescura: cada métrica tiene valor, fecha, fuente y estado; nada STALE puntúa.
- Sincronía y unidades correctas; los festivos no cuentan como sesión.
- Inferencias: dirección con dos observaciones; ninguna equivalencia de R3; ninguna ausencia leída como señal positiva.
- Puentes y JSON: cada afirmación material tiene decisión en la Tabla R; puente y JSON coinciden o la discrepancia está resuelta.
- GLI: solo puntúa con captura y confluencia; sin captura figura "sin señal" y no baja la confianza; el proxy G3, si se calculó, va rotulado como contexto.
- Funding 4.1: la tabla de REV está completa, con el flujo neto por día; cada subida tiene su lectura de causa; el acumulado indica el tamaño de la muestra; sensibilidad_settlement y la capa Cash/settlements son las del motor.
- Expectativas de tipos: FedWatch semanal con lectura posterior al FOMC si lo hubo; cada macro de OBJ con consenso confirmado tiene su regla hawkish/dovish; ningún consenso sin rótulo.
- Probabilidades:
  - selftest OK;
  - todos los factores son identificadores del catálogo con dato actual (el validador rechaza los desconocidos, incluidos los retirados settle_bills_nnc20 y settle_cupones_nnc10_dir);
  - cada día de settlement de OBJ con neto ≥ +20 bn lleva settle_neto_absorcion20, y con neto ≤ −20 bn lleva settle_neto_inyeccion20;
  - las cifras de P1, del puente y de datos3.resultado coinciden;
  - el modo tensión solo está activo con presión confirmada o MOVE > 135;
  - los avisos del motor están explicados.
- Coherencia: el régimen cumple los mínimos y coincide en la primera frase, el diagnóstico y el puente.
- Cierre: los pares FX cumplen las tres condiciones o no se emiten; ningún sesgo es firme sin un día ≥ 50 %; Nasdaq 100 y Russell 2000 tienen sesgo propio con su capa.

Si algo no es ✓, corrígelo o di exactamente qué queda limitado y por qué.
