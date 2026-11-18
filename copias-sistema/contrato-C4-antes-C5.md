# CONTRATO COMÚN DEL SISTEMA — Diagnóstico de liquidez global por partes
Versión del contrato: C4 (2026-11-15) · cambios C4: registro de fuentes de subastas, IORB y FedWatch actualizado (P-027, P-028, P-018), estados de SRF/ON RRP (P-009), post_fomc "n/a" (P-032), estado y neto de los eventos (P-008, P-017) · cambios C3: flujo neto diario y sensibilidad a settlements (P-004), consenso de datos y FedWatch post-FOMC (P-005), pistas Nasdaq 100 / Russell 2000 / AUD/JPY

Este documento manda sobre cualquier regla de fechas, festivos, estados, archivos y fuentes que aparezca en los prompts de las Partes 1, 2 y 3. Los prompts solo añaden lo específico de su capa. Si un prompt y este contrato discrepan, manda el contrato y la discrepancia se anota en la auditoría de la parte.

---------------------------------------------------------------
## 1. FECHAS (las calcula el orquestador con código, no el modelo)

- **CORTE** = fecha de ejecución (Europe/Madrid). Solo se ejecuta en sábado o domingo. En cualquier otro día el orquestador no lanza el informe, salvo en modo prueba explícito.
- **OBJ** = lunes–viernes siguiente al CORTE. Es la única semana con probabilidades.
- **REV** = lunes–viernes inmediatamente anterior a OBJ (la semana que acaba de cerrar).
- **COMP** = lunes–viernes anterior a REV (solo comparación).
- **Carpeta de la semana**: `semanas/<lunes de OBJ>/`.

Las tres partes reciben estas fechas ya calculadas en la cabecera `FECHAS` y no las recalculan. Si una parte detecta que no cuadran con la definición, lo anota como CONFLICT en su control y sigue con las del orquestador.

**Corte de datos.** Toda parte usa el último dato publicado a fecha de CORTE. Sin excepciones: no hay "descartar datos posteriores al viernes", porque en sábado o domingo no existen.

**Publicación T+1.** SOFR, EFFR, TGCR, BGCR y OBFR del viernes de REV se publican el lunes. En sábado o domingo su último dato es el jueves de REV. El viernes se marca `PENDING (T+1)`: no es STALE ni señal.

## 2. FESTIVOS Y CIERRES

Fuente que manda: calendario de SIFMA (https://www.sifma.org/resources/general/holiday-schedule/) para el mercado de bonos, más los festivos de la Fed (sin publicación de tipos del NY Fed).

Lista de respaldo (solo si SIFMA no abre; anotar "respaldo"):
- 2026: 26-nov (Thanksgiving), 25-dic. Cierres anticipados (14:00 ET): 27-nov, 24-dic, 31-dic.
- 2027: 1-ene, 18-ene, 15-feb, 26-mar (Good Friday), 31-may, 18-jun, 5-jul, 6-sep, 11-oct, 11-nov, 25-nov, 24-dic.
- Columbus Day y Veterans Day: bonos cerrados, renta variable abierta. Ese día no hay subastas ni settlements, y la probabilidad del día se refiere a renta variable y crédito; se dice en la fila.

Un día cerrado no es dato faltante y no cuenta como sesión para "cinco sesiones antes". Una fila de FRED en día cerrado repite el valor anterior: se salta.

## 3. ESTADOS DE LOS DATOS (comunes a las tres partes)

| Estado | Significado |
|---|---|
| CONFIRMED | fuente primaria, dentro del umbral de frescura |
| SECONDARY | fuente secundaria identificada, con fecha |
| USUARIO | aportado por el usuario con fecha válida |
| ESTIMATED | reconstruido con cifras oficiales (p. ej. NNC = gross − PHM) |
| TENTATIVE | calendario tentativo oficial, sin anuncio |
| PENDING | evento conocido, dato aún no publicado (incluye T+1) |
| STALE | más antiguo que su umbral |
| CONFLICT | fuentes discrepan y no se resolvió |
| NOT AVAILABLE | tras reintento y alternativa |

Regla general: ausencia de dato ≠ señal tranquila. Un dato STALE se muestra pero no sostiene conclusiones ni suma puntos.

## 4. UMBRALES DE FRESCURA (contados en días hábiles de bonos hasta el CORTE)

| Serie | Umbral | Nota |
|---|---|---|
| SOFR, EFFR, TGCR, BGCR | jueves de REV | T+1 |
| ON RRP, SRF | viernes de REV | |
| IORB | vigente en la fecha del SOFR | cambia solo en FOMC: se toma de la nota de implementación del último FOMC (el TXT de FRED va con semanas de retraso y no cuenta para la frescura) |
| TGA (DTS) | ≤ 3 días hábiles de retraso | la API de fiscaldata va con retraso; anotar el retraso real |
| Reservas (WRESBAL), balance Fed | último miércoles publicado | |
| MOVE | ≤ 2 días hábiles de retraso | Investing va con retraso; ver §6 |
| XEURBI | ≤ 3 días hábiles de retraso | el CSV de CME se actualiza con retraso; anotar el retraso real |
| FedWatch (Fed Rate Monitor) | actualización ≤ 2 días hábiles | si hubo FOMC en REV, la lectura actual debe ser posterior a la decisión |
| Consenso de datos de OBJ | publicado antes del CORTE | SECONDARY; un valor sin rótulo no se asigna |
| Nasdaq 100, AUD/JPY (solo evaluación) | ≤ 2 días hábiles | |
| Russell 2000 (solo evaluación) | sin umbral | retraso de ~5 días observado: lo que falte se completa la semana siguiente (rezagados) |
| OAS (FRED) | último o penúltimo día hábil | |
| Fails (OFR) | última publicación semanal | la referencia suele ser anterior a REV: decirlo |
| GLI proxy G3 (contexto, no puntúa) | último miércoles publicado | |
| Captura del GLI (opcional, la única que puntúa) | posterior al viernes de REV | |

Cada parte registra en su `datos*.json` el **retraso real observado** de cada fuente (campo `retraso_dias`). El orquestador acumula estos retrasos para ajustar umbrales con evidencia (propuesta al usuario, nunca automático).

## 5. ARCHIVOS Y PASO DE INFORMACIÓN

Cada semana, en `semanas/<lunes OBJ>/`:

| Archivo | Lo escribe | Lo lee |
|---|---|---|
| `parte1.md` | Parte 1 | usuario |
| `puente1.txt` | Parte 1 | Parte 2, Parte 3 |
| `datos1.json` | Parte 1 | Parte 3, simulador |
| `parte2.md` | Parte 2 | usuario |
| `puente2.txt` | Parte 2 | Parte 3 |
| `datos2.json` | Parte 2 | Parte 3, simulador |
| `parte3.md` | Parte 3 | usuario |
| `puente3.txt` | Parte 3 | Parte 3 de la semana siguiente (solo 9.0) |
| `datos3.json` | Parte 3 + motor | simulador, orquestador |
| `funding_causas.json` | motor (Parte 3, 4.1): subidas, acumulado, sensibilidad a settlements y capa cash | Parte 3, validador, simulador |
| `control.json` | orquestador | usuario, orquestador |
| `informe_final.md` | redactor final (prompts/final-v1.md) | usuario, simulador (primera pestaña), PDF del aviso |

Fuera de las semanas:
- `registro/historial.json`: resultados por día, probabilidades emitidas, Brier, recuento de base, retrasos de fuentes y la serie diaria de funding (`funding_dias`: SOFR−IORB, settlements, TGA y calendario) para atribuir subidas.
- `registro/propuestas.md`: propuestas de cambio de método pendientes de aprobación.
- `motor/motor.py`: cálculos deterministas (probabilidades v6, GLI proxy G3, evaluación, recalibración).
- `prompts/`: versiones vigentes de los prompts.

**Regla de paso.** El bloque puente es el resumen humano. El `datos*.json` es la fuente de cifras para la parte siguiente. Si puente y JSON discrepan en una cifra, manda el JSON (con su fecha) y la discrepancia se anota en la Tabla R de la Parte 3.

**Regla de no duplicar.** Una parte no vuelve a descargar una serie que la anterior ya trae en su JSON con fecha dentro del umbral. Solo la reabre si está STALE, en CONFLICT o le falta un campo que necesita.

## 6. REGISTRO DE FUENTES (auditado el 2026-10-28)

Lectura siempre con la herramienta web (el terminal del entorno no tiene acceso a estas webs). Pedir a la herramienta **filas literales**, nunca resúmenes, y pasar las cifras a archivos CSV antes de calcular.

| Dato | Fuente principal | Comportamiento observado | Alternativa |
|---|---|---|---|
| Tipos NY Fed + percentiles + volumen | `markets.newyorkfed.org/api/rates/all/search.json?startDate=…&endDate=…` | funciona; T+1 | `…/rates/all/latest.json` |
| IORB | nota de implementación del último FOMC (federalreserve.gov, "Implementation Note") | manda (P-027): IORB solo cambia en FOMC | `fred.stlouisfed.org/data/IORB.txt` solo como contraste (retraso mediano de 17 días hábiles observado en 3 semanas) |
| ON RRP y SRF | `markets.newyorkfed.org/api/rp/all/all/results/lastTwoWeeks.json` | funciona; varias operaciones "Repo" por día: sumar | — |
| XEURBI | `cmegroup.com/reports/cme-xccy-basis-historical-data.csv` | funciona; ~2,5 meses de historia; retraso de varios días observado | ninguna (solo CME) |
| Reservas | `fred.stlouisfed.org/data/WRESBAL.txt` | — | página de la serie |
| TGA | `api.fiscaldata.treasury.gov/…/dts/operating_cash_balance?sort=-record_date&page[size]=20&page[number]=1` | funciona con retraso; usar `open_today_bal` de la fila "Closing Balance" | FRED `WTREGEN` (semanal) |
| Subastas, settlements, PHM | `api.fiscaldata.treasury.gov/…/od/auctions_query` | **retraso de 15–20 días hábiles en altas y resultados** (nov-2026; antes ~4); upcoming_auctions ~19 días y `offering_amt` null. Úsala para el histórico (comparables) y para los vencimientos (Ruta 3b), no para REV ni OBJ (P-028) | ruta por defecto para REV y OBJ: anuncio y resultados SECONDARY (InvestingLive, Newsquawk, SafeRate, TFTC) + vencimientos oficiales → estado ESTIMATED; cupones de refunding: QRA (P-029); si no hay anuncio, TENTATIVE |
| TreasuryDirect, DTS fsapps | — | **bloqueadas para lectura automática** | no usar |
| MOVE | `investing.com/indices/ice-bofaml-move-historical-data` | funciona; retraso de 2–3 días observado | búsqueda web de cierre fechado (SECONDARY). Yahoo: no usar (histórico desfasado) |
| FedWatch | `investing.com/central-banks/fed-rate-monitor` | funciona, pero alterna entre una caché antigua y la lectura actual: comprueba la hora de actualización | 1) reintento con un parámetro de consulta (p. ej. `?refresh=1`); 2) CME FedWatch citado con fecha y hora por una fuente fechada (Reuters, Cboe, prensa), SECONDARY (P-018) |
| Treasury 2 años (P-035, días de actas) | `fred.stlouisfed.org/series/DGS2` (página) | funciona; T+1 | `fred.stlouisfed.org/data/DGS2.txt` |
| Ofertas de acciones ≥ 10 bn (P-036) | EDGAR (S-1/A, 424B4) → CONFIRMED · `nasdaq.com/market-activity/ipos`, Renaissance Capital, IPOScoop → SECONDARY | por verificar en la primera semana de uso | prensa financiera fechada (SECONDARY) |
| OAS crédito | `fred.stlouisfed.org/data/BAML….txt` | funciona; TXT con ~3 años | página de la serie |
| Rentabilidad total HY (P-037) | `fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2EY` | funciona (15-nov); B (…HYBEY) y CCC (…HYCEY) cortadas el 28-oct y 15-oct | ΔOAS + ΔDGS5 como estimación |
| Fails | `data.financialresearch.gov/v1/series/timeseries?mnemonic=…` | funciona | — |
| Balances BCE y BoJ | FRED `ECBASSETSW.txt`, `JPNASSETS.txt` | funciona | — |
| Tipos de cambio | `api.frankfurter.dev/v1/<inicio>..?from=EUR&to=USD,JPY` | funciona | — |
| S&P 500 (solo evaluación) | `investing.com/indices/us-spx-500-historical-data` | funciona | — |
| Nasdaq 100 (solo evaluación) | `fred.stlouisfed.org/series/NASDAQ100` (página; el TXT se corta) | funciona; T+1/T+2 | `investing.com/indices/nq-100-historical-data` (retraso de varios días) |
| Russell 2000 (solo evaluación) | `investing.com/indices/smallcap-2000-historical-data` | funciona con ~5 días de retraso (30-oct-2026) | Yahoo ^RUT (mismo retraso) |
| AUD/JPY (solo evaluación) | `api.frankfurter.dev/v1/<inicio>..?from=AUD&to=JPY,USD` | funciona; fixing BCE ~16:00 CET | — |
| Consenso de datos de EE. UU. | `tradingeconomics.com/united-states/calendar` | funciona (30-oct-2026): Actual · Anterior · Consenso · Previsión TE; en la semana siguiente a veces muestra un valor sin rótulo | MarketWatch: bloqueada · Investing calendario: sin previsiones en lectura automática |

Si una fuente falla, el patrón es siempre: un reintento → la alternativa de la tabla → NOT AVAILABLE. Nunca un artículo sin fecha ni un snippet.

## 7. ESQUEMAS JSON (mínimos obligatorios)

Todas las cifras llevan fecha. Unidades: tipos en %, diferenciales en pb, importes en miles de millones de USD (`_bn`), salvo que el campo diga otra cosa.

### datos1.json (Parte 1)
```json
{
  "parte": 1, "prompt": "P1 v2", "corte": "AAAA-MM-DD",
  "rev": ["AAAA-MM-DD","AAAA-MM-DD"], "comp": ["…","…"], "obj": ["…","…"],
  "estado_funding": "normalización|estrés incipiente|estrés sistémico|crisis de liquidez",
  "tipos": [{"fecha":"…","sofr":0,"sofr_p25":0,"sofr_p75":0,"sofr_p99":0,"sofr_vol_bn":0,
             "effr":0,"tgcr":0,"bgcr":0,"obfr":0,"iorb":0}],
  "onrrp": [{"fecha":"…","aceptado_bn":0}],
  "srf":   [{"fecha":"…","aceptado_bn":0,"operaciones":0}],
  "xeurbi":[{"fecha":"…","pb":0}],
  "reservas":[{"fecha":"…","bn":0}],
  "presion_funding": {"fecha":"…","sofr_ge_iorb":false,"gc_ge_iorb":false,
                      "srf_material":false,"sesiones_consecutivas":0,
                      "en_ventana_calendario":false,"confirmada":false},
  "srf_estado": "CONFIRMED|STALE (sin viernes de REV)", "onrrp_estado": "CONFIRMED|STALE (sin viernes de REV)",
  "fuentes": [{"fuente":"…","abrio":true,"ultimo_dato":"…","retraso_dias":0,"estado":"…"}]
}
```

### datos2.json (Parte 2)
```json
{
  "parte": 2, "prompt": "P2 v5.1", "corte": "…", "rev": ["…","…"], "obj": ["…","…"],
  "estado_plumbing": "fuerte|normal|floja|peligrosa",
  "ledger": [{"settlement":"…","semana":"REV|OBJ","familia":"Bills|Cupones|TIPS|FRN|CMB",
              "securities":["…"],"gross_bn":0,"phm_bn":0,"nnc_bn":0,"gross_10y_mas_bn":0,
              "identidad_ok":true,"origen":"subastado en REV|en OBJ|tentativo","estado":"…"}],
  "subastas": [{"fecha":"…","semana":"REV|OBJ","tenor":"10Y","tipo":"nominal|TIPS|FRN|bill",
                "nueva_reapertura":"nueva|reapertura","importe_bn":0,"settlement":"…",
                "resultado":{"high_yield":null,"wi":null,"wi_hora":null,"tail_pb":null,
                             "btc":null,"indirects_pct":null,"directs_pct":null,"dealers_pct":null},
                "medias_6_previas":{"btc":null,"indirects_pct":null,"dealers_pct":null},
                "floja_2de4": null, "solida": null, "calidad":"…","estado":"…","fuente":"…"}],
  "buybacks": [{"operacion":"…","settlement":"…","tipo":"liquidity|cash management",
                "aceptado_bn":0,"estado":"ejecutado|tentativo"}],
  "neto_dia": [{"fecha":"…","semana":"REV|OBJ","neto_bn":0,"lectura":"absorción neta|inyección neta|neto pequeño|n/c"}],
  "tga": [{"fecha":"…","cierre_bn":0}],
  "calendario_obj": [{"fecha":"…","bonos_abierto":true,"fin_mes":false,"fin_trimestre":false,
                      "tax_date":false,"qra":false,"nota":"…"}],
  "fuentes": [{"fuente":"…","abrio":true,"ultimo_dato":"…","retraso_dias":0,"estado":"…"}]
}
```
En `ledger`, la semana REV lleva un registro por (día de settlement, familia). `neto_dia` = Σ NNC de todas las familias del día − buybacks ejecutados que liquidan ese día (null si alguna familia no tiene NNC); el validador lo recalcula con `motor.py neto`. `securities` usa tenores cortos ("2Y", "7Y", "20Y", "13W"). `tga` lleva el cierre de cada día desde el lunes de COMP.

### datos3.json (Parte 3) — entrada del motor y del simulador
```json
{
  "parte": 3, "prompt": "P3 v6.3", "metodo": "v6.3", "corte": "…", "base": [20, 50, 30],
  "rev": ["…","…"], "obj": ["…","…"],
  "confianza": "alta|media|baja", "capas_con_dato_actual": 0,
  "modo_tension": {"por_funding": false, "por_move": false},
  "sensibilidad_settlement": {"activa": false, "nota": "… (copiado de funding_causas.json)"},
  "regimen": {"estado":"…","prob":{"normalizacion":0,"incipiente":0,"sistemico":0,"crisis":0}},
  "capas": [{"capa":"Funding","senal":"CONFIRMA ESTRÉS|CONTRADICE ESTRÉS|MIXTA|NO CONFIRMADA",
             "dato_actual":true,"valor":"…","fecha":"…"}],
  "fondo": [{"id":"<id del catálogo del motor>","dato":"…","fecha":"…"}],
  "dias": [{"fecha":"…","dia":"lunes","bonos_abierto":true,"evento_verificado":true,
            "dispersion":[{"id":"<catálogo>","evento":"…","estado":"CONFIRMED|SECONDARY"}],
            "direccion":[{"id":"<catálogo>","evento":"…","neto_bn":0,"estado":"…","previas_flojas":false}]}],
  "reglas_actualizacion": [{"subasta":"…","fecha_subasta":"…","dia_settlement":"…"},
                           {"tipo":"macro","evento":"…","dia":"…","consenso":"…","anterior":"…",
                            "hawkish_si":"…","dovish_si":"…"}],
  "macro_obj": [{"fecha":"…","hora_et":"…","evento":"…","nivel":"macro1|macro2","consenso":"…","anterior":"…",
                 "hawkish_si":"…","dovish_si":"…","fuente":"…","estado":"…"}],
  "flujo_neto_obj": [{"fecha":"…","neto_bn":0}],
  "series": {"move":[{"fecha":"…","valor":0}], "xeurbi":[{"fecha":"…","pb":0}], "hy":[{"fecha":"…","pb":0}],
             "ccc":[], "ig":[], "b":[], "sofr_iorb":[{"fecha":"…","pb":0}]},
  "fedwatch": [{"reunion":"…","actual":{},"semana_anterior":{},"tipo_implicito":0,"hora_lectura":"…","post_fomc":true|false|"n/a"}],
  "gli": {"puntua": {"fuente":"captura|ninguna","estado":"…|sin señal","semana":"primera|segunda"},
          "proxy_actual": {"estado":"…","estado_ant":"…","causa":"…"}},
  "evaluacion_rev": {"dias":[{"fecha":"…","spx_pct":null,"hy_pb":null,"move_pct":null,
                              "ndx_pct":null,"rut_pct":null,"audjpy_pct":null}],
                     "rezagados":[{"fecha":"…","rut_pct":null}]}
}
```
`capas` incluye "Cash/settlements" con la señal que da el motor en funding_causas.json → capa_cash. Las pistas (ndx, rut, audjpy) solo se evalúan: no cambian la clasificación principal, la base ni la recalibración.

Las probabilidades **no las escribe el modelo**: las calcula `motor.py` a partir de `fondo`, `dias`, `modo_tension` y `confianza`, y las añade a `datos3.json` en el bloque `resultado`. El informe de la Parte 3 copia esas cifras.
