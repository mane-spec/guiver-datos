# guiver-datos

Paquete de datos semanal para el diagnóstico de liquidez global (Guiver Research). Es la parte "local" del sistema híbrido, pero corre en GitHub Actions, así que no hace falta tener el PC encendido.

- **Cuándo:** el sábado a las 05:17 UTC, o a mano desde la pestaña Actions → "Paquete de datos semanal" → Run workflow.
- **Qué deja:** `paquete/<CORTE>/series.csv`, con el mismo formato que el CSV de los investigadores, más los archivos en bruto (subastas, DTS, operaciones del NY Fed) y `manifiesto.json`, que indica qué fuente salió bien y con qué última fecha. `paquete/ultimo.json` apunta a la semana más reciente.
- **Respaldo:** lo que no salga con `ok: true` se sigue buscando con WebFetch.
- **Sin claves:** todas las fuentes son públicas y no necesitan registro.

## Inventario: qué sale de una API y qué sigue con WebFetch

| Parte | Serie | Fuente en el paquete |
|---|---|---|
| P1-A | SOFR (p1/p25/p75/p99, volumen), EFFR, TGCR, BGCR, OBFR | API del NY Fed |
| P1-A | IORB (contraste) | FRED |
| P1-B | ON RRP y SRF por día (solicitado/aceptado, nº de operaciones) | API del NY Fed |
| P1-B | WRESBAL | FRED |
| P1-C | XEURBI | CSV de CME (puede bloquear; si falla → WebFetch) |
| P2-A | TGA diario | fiscaldata DTS |
| P2-C/D | Subastas de 18 meses (high yield, BTC, directs, indirects, dealers) | fiscaldata auctions_query |
| P2-B/E | Subastas próximas | fiscaldata upcoming_auctions |
| P2-A/B | Buybacks | fiscaldata (endpoint por confirmar en la primera ejecución) |
| P3-B | OAS IG/HY/B/CCC y rentabilidades, DGS2 y DGS5 | FRED |
| P3-F | S&P 500 y Nasdaq 100 | FRED |
| P3-F | AUD/JPY | Frankfurter (fixing del BCE, **no** el cierre de NY) |

**Siguen con WebFetch:** MOVE, Russell 2000, FedWatch, consenso macro, WI y tail de las subastas (InvestingLive), vencimientos de la Ruta 3b, QRA, calendarios (BLS/BEA/ISM/earnings/IPO), SIFMA, fails de la OFR, declaraciones de la Fed y resultados de los bancos.
