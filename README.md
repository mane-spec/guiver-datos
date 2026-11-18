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
| P1-C | XEURBI | CSV de CME: **falla** (CME bloquea los servidores de GitHub) → sigue con WebFetch |
| P2-A | TGA diario | fiscaldata DTS |
| P2-C/D | Subastas de 18 meses (high yield, BTC, directs, indirects, dealers) | **TreasuryDirect** `subastas_td.csv` (principal, al día). La fecha de subasta es `competitiveAuctionCloseDate`; las reaperturas llevan plazos como "9-Year 8-Month". `subastas.csv` (fiscaldata) es secundaria: el 18-nov iba atrasada hasta el 22-oct |
| P2-B/E | Subastas anunciadas (con importe) y próximas | TreasuryDirect `anunciadas_td.csv` y `proximas_td.csv`; fiscaldata `subastas_proximas.csv` como secundaria |
| P2-A/B | Buybacks (incluye operaciones programadas) | fiscaldata `buybacks.csv` |
| P3-B | OAS IG/HY/B/CCC y rentabilidades, DGS2 y DGS5 | FRED |
| P3-F | S&P 500 y Nasdaq 100 | FRED |
| P3-F | AUD/JPY | Frankfurter (fixing del BCE, **no** el cierre de NY) |

| P3-A | Fails de primary dealers (Treasuries y total, entregar/recibir) | OFR (principal, la del método) + API del NY Fed (contraste) |
| P1/P2/P3 | Calendario del FOMC, comunicados de la Fed, página del QRA, calendario tentativo de subastas y buybacks (PDF → texto), calendario del BEA, festivos de SIFMA | Páginas oficiales guardadas como `.txt` |
| P3-C/D | Consenso macro de EE. UU. (consenso, anterior, hora ET, impacto) | ForexFactory, feed abierto (SECONDARY). `consenso_semana_siguiente.csv` aparece solo algunos días |

**Siguen con WebFetch (no tienen fuente abierta o bloquean el acceso automático):** MOVE (ICE), Russell 2000 (FTSE Russell), FedWatch y XEURBI (CME), WI y tail de las subastas (no hay fuente pública), calendario del BLS (bloquea), vencimientos de la Ruta 3b, texto de los documentos del QRA, earnings, ofertas de acciones y resultados de los bancos.

**Regla:** solo fuentes oficiales o feeds abiertos, identificándose como bot. No se usan trucos para entrar en webs que bloquean el acceso automático.
