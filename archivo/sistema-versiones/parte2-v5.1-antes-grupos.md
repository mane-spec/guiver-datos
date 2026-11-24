TREASURY RESEARCH PROTOCOL — PARTE 2 (v5.1)
Settlements, Net New Cash, auctions, QRA, buybacks, TGA y liquidity plumbing

Cambios frente a v4 (mecánica y fuentes; el método de cash y de duration no cambia): fechas e inputs los pone el orquestador; fuentes corregidas tras la auditoría del 28-oct-2026 (fiscaldata va con retraso, TreasuryDirect bloqueada); nueva Ruta 3b de PHM con datos oficiales; resultados de subasta con WI y tail desde fuente secundaria; la Parte 2 calcula "previas flojas" para la Parte 3; bloque puente con calendario día a día de OBJ; salida datos2.json.

Cambio de v5.1 (P-004, aprobado el 30-oct-2026): además del NNC por familia, se calcula el FLUJO NETO DEL DÍA = Σ NNC de todas las familias que liquidan ese día − buybacks ejecutados que liquidan ese día. Se puede emitir mucho y, si vence casi lo mismo, el neto es pequeño o incluso inyecta cash. La Parte 3 puntúa con el neto, no con el gross ni con el NNC de una sola familia.

0. INPUTS Y LAS DOS SEMANAS (los rellena el orquestador)
FECHAS:
CORTE: {CORTE} ({DIA_SEMANA})
COMP: {COMP_LUNES} – {COMP_VIERNES}
REV: {REV_LUNES} – {REV_VIERNES}
OBJ: {OBJ_LUNES} – {OBJ_VIERNES}
HACE_9_MESES: {HACE_9_MESES} · HACE_18_MESES: {HACE_18_MESES}
CARPETA DE SALIDA: {CARPETA}

BLOQUE PUENTE PARTE 1:
{PUENTE1}

DATOS PARTE 1 (resumen de datos1.json):
{DATOS1_RESUMEN}

Definición fija (CONTRATO §1): OBJ es el lunes–viernes siguiente al CORTE; REV, el inmediatamente anterior. Las fechas de arriba mandan; si no cumplen la definición, anótalo como CONFLICT y sigue con ellas.
Antes de investigar escribe una línea: REV: … – … | OBJ: … – … | Corte: … | Cierres del mercado de bonos (SIFMA) en REV/OBJ: …
Usa fechas ISO (van dentro de las URLs). No hagas preguntas.

1. MISIÓN, PRIORIDAD Y LÍMITES
Prioridad 1: SETTLEMENTS y CASH. Qué se liquida cada día, gross frente a Publicly Held Maturing (PHM), Net New Cash/(Pay Down), TGA, tax dates y buybacks que liquidan. En REV, lo realizado; en OBJ, lo previsto.
Prioridad 2: AUCTIONS y DURATION. Pricing, tail, demanda, dealer absorption, y la condición "previas flojas" que usa la Parte 3.
Prioridad 3: QRA y contexto.
Si el presupuesto se agota, recorta en orden inverso: nunca recortes settlements.
Fuera de alcance (es Parte 3): MOVE, fails, crédito, banca, FedWatch y probabilidades. No rehagas la Parte 1: usa su bloque puente y su resumen de datos; si están vacíos, escribe "Conexión Parte 1 no disponible/incompleta" y sigue.
Orden obligatorio: DESCUBRIR → UNIVERSO DE SETTLEMENTS (REV y OBJ) → CASH LEDGER → VALIDAR CASH LEDGER → AUCTIONS/DURATION → QRA/TGA/BUYBACKS → INTERPRETAR → VALIDAR → RENDER. No escribas conclusiones de cash antes de validar el Cash Ledger.

2. FUENTES (usa estas primero; pide siempre filas literales y calcula con código)
Base: https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/
Montos en dólares, salvo el DTS (millones). Convierte todo a bn.

AVISO DE FUENTES (auditoría 28-oct-2026):
- auctions_query va con unos 4 días hábiles de retraso en altas y resultados: las subastas de REV pueden faltar o venir con high_yield/BTC en null, y el PHM de settlements recientes puede venir a 0.
- upcoming_auctions mezcla filas antiguas y trae offering_amt en null aunque la subasta esté anunciada.
- TreasuryDirect (tablas, TA_WS, anuncios en PDF) y fsapps (DTS) bloquean la lectura automática: no las uses.
Primera acción: comprueba la fecha más reciente de auctions_query (sort=-auction_date&page[size]=5) y la última fecha del DTS, y anota el retraso real en el control. Ese retraso decide qué rutas usas.

Settlements y cash (prioridad 1)
S-Q1 — Settlements de REV: od/auctions_query?filter=issue_date:gte:{REV_LUNES},issue_date:lte:{REV_VIERNES}&page[size]=100
S-Q2 — Settlements de OBJ: od/auctions_query?filter=issue_date:gte:{OBJ_LUNES},issue_date:lte:{OBJ_VIERNES}&page[size]=100. Contrasta con od/upcoming_auctions?filter=issue_date:gte:{OBJ_LUNES},issue_date:lte:{OBJ_VIERNES}&page[size]=100 (descarta filas con auction_date anterior a COMP: son residuos).
S-Q3 — Vencimientos de un día X (Ruta 3b del PHM): od/auctions_query?filter=maturity_date:eq:X&page[size]=100 → PHM estimado = Σ total_accepted − Σ soma_accepted de las filas de la misma familia. Validado el 22-oct-2026: 244,0 bn estimado frente a 241,7 bn oficial (error ≈ 1 %).
S-Q4 — TGA (DTS): dts/operating_cash_balance?filter=record_date:gte:{COMP_LUNES}&sort=-record_date&page[size]=100&page[number]=1 (cada día trae 4 filas). Usa open_today_bal de la fila "Treasury General Account (TGA) Closing Balance" (close_today_bal viene en null). Guarda en datos2.tga el cierre de CADA día disponible desde el lunes de COMP: la Parte 3 lo cruza día a día con SOFR − IORB. Si hay una tax date reciente, amplía hasta tener el TGA de antes y de después. Alternativa: FRED WTREGEN (semanal).
S-Q5 — Buybacks ejecutados: od/buybacks_operations?sort=-operation_date&page[size]=10
S-Q6 — Buybacks previstos (OBJ): calendario tentativo de buybacks del último QRA en home.treasury.gov (la API solo trae ejecutados).

Auctions (prioridad 2)
A-Q1 — Subastas de REV: od/auctions_query?filter=auction_date:gte:{REV_LUNES},auction_date:lte:{REV_VIERNES}&page[size]=100
A-Q2 — Subastas de OBJ: od/upcoming_auctions?filter=auction_date:gte:{OBJ_LUNES},auction_date:lte:{OBJ_VIERNES}&sort=auction_date&page[size]=100
A-Q3 — Calendario tentativo (funciona): https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.pdf
A-Q4 — Histórico para comparables: od/auctions_query?filter=security_type:in:(Note,Bond),auction_date:gte:{HACE_9_MESES}&sort=-auction_date&page[size]=100 (TIPS: {HACE_18_MESES}). Sin filtro de fecha la respuesta puede truncarse.
A-Q5 — Resultados y WI cuando auctions_query no los trae: InvestingLive publica cada subasta con high yield, WI, tail, BTC, dealers, directs e indirects. Búscalo con la búsqueda web ("investinglive {tenor} auction high yield {mes año}") y abre la nota fechada. Estado SECONDARY. El tail solo vale si la nota da el WI de antes del cierre.
A-Q6 — Importe anunciado cuando upcoming_auctions trae null: nota de prensa o noticia fechada del anuncio (SECONDARY). Si no aparece: TENTATIVE, sin importe.
Contexto: último QRA (Policy Statement + Financing Estimates) en home.treasury.gov.
Campos clave: security_type, security_term, reopening, cusip, cash_management_bill_cmb, announcemt_date, auction_date, issue_date, maturity_date, offering_amt, est_pub_held_mat_by_type_amt, soma_accepted, total_accepted, high_yield / high_investment_rate, bid_to_cover_ratio, indirect_bidder_accepted, direct_bidder_accepted, primary_dealer_accepted, comp_accepted, floating_rate, inflation_index_security.
Reaperturas con plazo residual: "9-Year 10-Month" = 10Y, "19-Year 10-Month" = 20Y, "29-Year 10-Month" = 30Y. TIPS y FRN salen en las consultas de Note: sepáralas con inflation_index_security y floating_rate (la FRN de 2 años aparece como "Note 2-Year").

3. BLOQUE CENTRAL — SETTLEMENTS Y CASH
S1 — Universo de settlements. Toda security con issue_date en REV o en OBJ, sea cual sea su fecha de subasta: subastas de la semana anterior que liquidan en la ventana, reopenings, CMB, TIPS y FRN. No depende de las subastas de la semana. Toda subasta de OBJ tiene settlement confirmado o un estado explícito (pendiente / no disponible). Si se subasta en OBJ y liquida después: "el auction/pricing risk pertenece a OBJ; el settlement/cash-flow ocurre el [fecha], fuera de la ventana". No traslades settlements de semana. Comprueba cierres SIFMA: desplazan settlements.
Si auctions_query aún no tiene las subastas de REV que liquidan en OBJ (retraso), constrúyelas desde A-Q3 (fechas) + A-Q5/A-Q6 (importe y resultados) y márcalas SECONDARY o TENTATIVE.

S2 — Auction ≠ Settlement ≠ Cash drain.
Auction date: price discovery, concesión WI, tail, demanda, dealers y duration. Una subasta puede mover el mercado sin mover cash.
Settlement date: intercambio de cash por securities; impacta en TGA, reservas, dealer funding, repo y balances.
Gross settlement ≠ drenaje neto. Mantén separados: Announcement · Auction · Settlement · Gross · PHM · NNC/(Pay Down).

S3 — Bills ≠ Coupons (dos canales).
Bills: rollover, absorción de cash, TGA, money markets y funding de front-end. Un gran settlement de bills puede dar poco NNC o Pay Down.
Coupons/TIPS/FRN: el riesgo de pricing va en la fecha de subasta y el de cash en la de settlement.

S4 — Fuente del NNC (rutas acotadas, en este orden):
Ruta 1 — datos estructurados oficiales (S-Q1/S-Q2): offering_amt + est_pub_held_mat_by_type_amt. Estado CONFIRMED. Un PHM igual a 0 en un settlement que sustituye vencimientos es dato aún no cargado, no un cero real: pasa a la Ruta 3b.
Ruta 2 — tabla de TreasuryDirect: NO DISPONIBLE (bloqueada). No la intentes.
Ruta 3a — reconstrucción con cifras ya cargadas: anuncio (SECONDARY) + vencimientos.
Ruta 3b — PHM estimado con S-Q3 (Σ total_accepted − Σ soma_accepted de lo que vence ese día, misma familia). NNC = Gross − PHM. Estado ESTIMATED (error típico ±1–2 %).
Ruta 4 — NOT AVAILABLE / NO CONFIRMADO: solo tras las rutas 1–3.
Disparador: con gross conocido y PHM o NNC ausente, no interpretes el cash sin recorrer 1→3.

S5 — Procedimiento por settlement (A–G): A localiza filas · B Total Offering, PHM, NNC · C reconcilia con el anuncio · D agrupa (S6) · E separa SOMA y add-ons (S7) · F verifica la identidad (S8) · G solo entonces clasifica (S9).

S6 — Agregación (crítica). Agrupa por (issue_date, familia): Bills · Cupones nominales (Note + Bond) · TIPS · FRN · CMB. Las filas que comparten fecha y el mismo est_pub_held_mat_by_type_amt son un grupo: el PHM se aplica una sola vez al agregado. Prohibido restarlo security por security.
Ejemplo real del 15-oct-2026: Bills (6W, 13W, 26W) gross 272,0 bn − PHM 250,412 bn = NNC +21,588 bn. Cupones (3Y, 10Y, 30Y) gross 119,0 bn − PHM 86,437 bn = NNC +32,563 bn (Note y Bond comparten PHM: un grupo).
Anota además, por día, el gross de 10Y o más que liquida (lo usa la Parte 3).

S7 — SOMA y add-ons. No confundas PHM con SOMA holdings, add-ons de la Fed, cuentas del gobierno u otras adjudicaciones non-competitive. El NNC usa PHM (metodología TreasuryDirect). No sumes ni restes soma_accepted dos veces (en la Ruta 3b se resta una vez, del lado de los vencimientos). No uses el total outstanding que vence como PHM.

S8 — Identidad de cash: Total Offering − PHM = NNC/(Pay Down), tolerancia solo de redondeo. Si no cuadra: CONFLICT y revisa unidades, signo, SOMA, add-ons, vencimientos duplicados, agregación y fecha. Signo: 247,000 − 273,720 = −26,720 → PAY DOWN de 26,720 bn.

S9 — Clasificación: NNC > 0 absorción neta de cash · NNC < 0 Pay Down · NNC estimado: ESTIMATED · no calculable: NNC y riesgo de cash NO CONFIRMADO. Nunca clasifiques un drenaje material solo por el gross. Si el día de mayor gross no es el de mayor NNC, explícalo. Si un gran gross produce Pay Down, di que ese gross no es drenaje. En OBJ, una subasta tentativa sin importe deja su grupo como NNC NO CONFIRMADO; el último comparable solo se cita como referencia rotulada.

S10 — NNC ≠ cambio 1:1 de reservas. Treasury financing flow: NNC/(Pay Down). System liquidity flow: depende del TGA realizado, outlays, tax receipts y timing. Si REV u OBJ contiene una tax date relevante, analízala como flujo separado: NNC + tax receipts − outlays ± otros → posible movimiento del TGA → posible transmisión a reservas/funding. Nunca sumes NNC e impuestos como cambio automático de reservas. En REV compara el NNC realizado con la variación real del TGA (con el retraso real del DTS anotado).

S11 — Buybacks que liquidan: anuncio, fecha de operación, importe máximo y aceptado, settlement, tipo (liquidity support o cash management). Flujo separado, fuera del NNC. Dimensiónalos frente al NNC, el gross y los vencimientos. Un buyback pequeño no es una gran inyección; los buybacks no son QE. Uno PENDING o TENTATIVE no amortigua nada todavía.

S11b — Flujo neto del día (P-004). Para cada día de settlement de REV y de OBJ: neto = Σ NNC/(PD) de todas las familias (Bills, CMB, cupones, TIPS, FRN) − buybacks ejecutados que liquidan ese día. Positivo = absorción neta de cash; negativo = inyección neta (más vencimientos y recompras que emisión). Si alguna familia del día tiene NNC NO CONFIRMADO, el neto es "n/c": no lo completes con el gross. Lectura: ≥ +20 bn absorción neta material · ≤ −20 bn inyección neta material · en medio, neto pequeño. Calcúlalo con código y contrástalo con: python3 {MOTOR} neto {CARPETA}datos2.json (deben coincidir). Inyección neta ≠ inyección de reservas: el efecto pasa por el TGA (S10).

S12 — Settlement day ↔ funding (Parte 1). Auction day: pricing, duration y dealers; un funding tranquilo no garantiza una subasta fuerte y una subasta floja no prueba escasez de reservas. Settlement day: aquí pesa el funding. Secuencia: NNC → posible impacto en TGA/reservas → confirmación o negación con la presión de funding de la Parte 1 (definición común). Nunca: gross issuance → estrés automático.

4. AUCTIONS Y DURATION (prioridad 2)
D1 — Universo de subastas de OBJ: A-Q2 ∪ A-Q3, cruzado por tenor + fecha. Subasta de A-Q3 sin anuncio: TENTATIVE / PENDING ANNOUNCEMENT, sin inventar tamaño. El anuncio más reciente prevalece. No deduzcas el settlement de un reopening por convención: verifícalo en A-Q3. CMB: si no hay: "No hay CMB anunciado a fecha de corte; no excluye un anuncio ad hoc".

D2 — Resultados de REV y scorecard. Puntúa todas las subastas de cupón de REV. Scorecard: última subasta realizada de 5Y, 7Y, 10Y, 20Y y 30Y (nominales), aunque sea de semanas anteriores. Filtros de A-Q4: excluye TIPS y FRN, mapea reopenings, high_yield null = no realizada (o retraso: usa A-Q5).

D3 — Tail = High Yield − WI justo antes de la subasta (negativo = stop-through). Sin WI con hora: NO CONFIRMADO. Prohibido sustituirlo por la subasta previa, el yield del mes anterior, el cupón, un yield posterior o el precio.

D4 — Calidad: fuerte / normal / floja / peligrosa, combinando tail, BTC, indirects, directs y dealers frente a las 3–6 previas del mismo tenor (new issue frente a reopening).

D5 — Condiciones que usa la Parte 3 (calcúlalas con código y guárdalas en datos2.json):
Para la ÚLTIMA subasta realizada de cada tenor de cupón de 5Y o más que se subasta en OBJ (nominal o TIPS), con las medias de las seis anteriores del mismo tenor y tipo:
- floja_2de4 = se cumplen al menos dos de: tail ≥ +1 pb con WI fechado · BTC < media · indirects < media · dealers > media.
- solida = stop-through, o BTC e indirects > media con dealers < media.
Si falta un criterio, evalúa con los disponibles y dilo; si faltan tres, null.

5. QRA Y TGA (prioridad 3)
QRA: coupon sizes, bills vs coupons, duration supply, financing needs, net borrowing, TGA target, buybacks y calendario. Separa efecto anuncio, pricing y settlement/cash. Lectura por duration (alivia / tensiona / neutro) y por cash (alivia / absorbe / neutro / no confirmado). Si el anuncio del QRA (Policy Statement) cae en OBJ, ponlo en el calendario con su fecha y hora y marca "qra": true en ese día de calendario_obj: la Parte 3 lo puntúa como evento.
TGA: distingue target, realizado, NNC y flujos diarios. No infieras el TGA diario del target trimestral. Último realizado con su fecha efectiva y retraso.

6. EVIDENCIA Y PRESUPUESTO
Estados del CONTRATO §3. Cada dato material: valor · estado · fuente · fecha. No inventes cifras. Que falte un dato no es señal neutral; que falle la extracción no significa que no exista.
Presupuesto: unas 18 fuentes y hasta 6 búsquedas para A-Q5/A-Q6. Un reintento por fuente y después la alternativa. No reabras fuentes ya leídas. No copies JSON ni páginas enteras al razonamiento: extrae los campos del §2 a CSV y calcula con código.
Fallos parciales: un campo que falla invalida solo ese campo; una sección incompleta se entrega con alcance limitado y motivo; una conclusión sin input queda NO CONFIRMADA.

7. OUTPUT (español; las tablas mandan, la prosa mínima). Escribe el informe en {CARPETA}parte2.md.
0. Control: REV/OBJ/corte/cierres · retraso real de auctions_query y del DTS · integridad del calendario OBJ (COMPLETO A FECHA DE CORTE / PARCIAL) · integridad del Cash Ledger REV | OBJ · método del NNC (Ruta 1 / 3a / 3b / combinación) · securities tentativas/pending · CMB · tabla "Acceso a fuentes" (Fuente · Abrió · Alternativa · Último dato).
1. ESTADO DE TREASURY PLUMBING: absorción fuerte / normal / floja / peligrosa, y de dónde viene el riesgo.
PARTE A — SETTLEMENTS Y CASH
Tabla A1. Cash Ledger REV: Settlement date · Familia · Securities · Gross · PHM (una vez) · NNC/(PD) · Identidad ✓/✗ · Buybacks que liquidan · Neto del día (una vez por fecha) · Estado · Ruta.
Tabla A2. Cash Ledger OBJ: las mismas columnas + Origen (subastado en REV / en OBJ / tentativo).
Tabla A3. Calendario diario de riesgo OBJ: Día · Bonos abierto/cerrado · Announcements · Auctions · Bill settlements · Coupon/TIPS/FRN settlements · Gross · Gross 10Y+ · PHM · NNC/(PD) · Buybacks · Neto del día · Fin de mes/trimestre · Tax date · Riesgo cash · Riesgo duration · Qué importa.
A4. Resumen (una línea cada uno): mayor gross · mayor NNC · mayor Pay Down · mayor absorción neta del día · mayor inyección neta del día · días con mucho gross y neto pequeño · principales settlements · pendientes · TGA y fiscal · buybacks.
PARTE B — AUCTIONS Y DURATION
Tabla B1. Ledger de subastas: Security · Tipo · Tenor · New/Reopen · Status · Announce · Auction · Settlement · Amount · [REV]/[OBJ] · Fuente.
Tabla B2. Resultados de REV + Duration Scorecard (5Y–30Y): Tenor · Fecha · New/Reopen · Size · High Yield · WI (hora) · Tail · BTC · Ind · Dir · Dealers · vs medias 6 previas · Lectura.
Tabla B3. Condiciones para la Parte 3: Tenor de OBJ · Última subasta (fecha) · floja_2de4 (criterios cumplidos) · solida · Estado.
Cierre de la Parte B: lectura de las subastas · riesgo de duration indigestion (bajo / medio / alto) · subasta clave de OBJ y qué resultado la haría preocupante.
PARTE C — QRA, TGA Y PARTE 1
QRA (3–5 líneas, lectura duration | cash | conjunta) · TGA realizado frente a target · Conexión con Parte 1 (¿el funding puede amplificar o absorber los settlements? usa la presión de funding común).

BLOQUE PUENTE PARTE 2 (escríbelo también en {CARPETA}puente2.txt)
BLOQUE PUENTE PARTE 2 — TREASURY PLUMBING
Semanas: CORTE __ · REV __ – __ · OBJ __ – __ · Cierres de bonos: __
Estado y alcance: estado de plumbing __ · integridad calendario __ | cash __ · método del NNC __ · retraso fiscaldata __ días
Bills: gross / PHM / NNC en REV __ | OBJ __
Cupones/TIPS/FRN: gross / PHM / NNC en REV __ | OBJ __ (dentro/fuera de la ventana)
Calendario OBJ día a día (una línea por día):
[día fecha]: subastas __ · settlements bills NNC __ · settlements cupones gross __ / NNC __ · gross 10Y+ __ · buybacks __ · neto del día __ bn · fin de mes/trim/tax __ · estado __
Flujo neto REV (una línea por día con settlement): [fecha] neto __ bn (absorción / inyección / pequeño / n/c) · gross total __
Resultados de cupón de REV (una línea por subasta): tenor · fecha · high yield · WI · tail · BTC · ind · dealers · calidad · fuente
Previas flojas para OBJ: tenor → floja_2de4 sí/no/null · sólida sí/no/null
Días críticos de OBJ: mayor gross __ · mayor NNC __ · mayor Pay Down __ · mayor absorción neta __ · mayor inyección neta __ · por settlement/TGA/cash __
TGA y fiscal: tax-date/fiscal flow __ · último TGA __ bn (fecha __) · ΔTGA en REV __ bn
Buybacks: alivian / alivio marginal / insuficientes / no confirmados (fecha, importe, settlement)
Duration: lectura __ · riesgo __ · día crítico de pricing __ · subasta clave __
QRA: duration __ | cash __ · bills vs coupons __ · fecha del próximo anuncio __
Pendientes: dato no confirmado más importante __ · conexión con funding de Parte 1 __
Parte 3 debe confirmar: MOVE · fails · crédito · FedWatch · funding (si el NNC o los settlements son materiales)
Cierre fijo: "No se han calculado probabilidades finales en Parte 2. Calendario completo solo respecto a la información oficial disponible al corte."

SALIDA DE DATOS: escribe {CARPETA}datos2.json con el esquema del CONTRATO §7 (ledger REV y OBJ, subastas con resultados y medias, condiciones D5 en cada subasta de OBJ de 5Y+, buybacks con su settlement, neto_dia por fecha de REV y OBJ, TGA, calendario_obj, fuentes con retraso). El validador recalcula neto_dia desde el ledger y los buybacks y rechaza discrepancias de más de 0,1 bn. Valida que es JSON correcto con código. puente2.txt y datos2.json deben coincidir en todas las cifras.

CHECKLIST FINAL (✓ o explicación, una línea cada uno):
Toda fila está etiquetada [REV]/[OBJ] y no hay nada fuera de las dos ventanas, salvo el histórico.
Toda security con settlement en REV/OBJ aparece aunque su subasta fuera anterior o no esté aún en auctions_query.
Toda subasta de OBJ tiene settlement o estado explícito; A-Q3 está cubierto.
Las rutas de NNC 1→3b se recorrieron antes de cualquier NOT AVAILABLE; ningún PHM = 0 de carga pendiente se usó como cero.
El PHM se usó una vez por grupo; las identidades de cash están verificadas; SOMA y add-ons van separados; buybacks fuera del NNC y restados una sola vez en el neto del día; neto_dia coincide con motor.py neto.
Ningún drenaje se ha inferido solo del gross. No hay tail sin WI con hora. No hay celda inventada.
D5 calculado con código para cada tenor de 5Y+ de OBJ.
puente2.txt y datos2.json coinciden.
