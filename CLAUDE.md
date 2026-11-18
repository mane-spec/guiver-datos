# guiver-datos — reglas para Claude

Repo del paquete de datos semanal de Guiver Research (diagnóstico de liquidez global). `datos.py` descarga, cada sábado, series de fuentes oficiales y las deja en `paquete/<viernes REV>/` con `manifiesto.json`. El orquestador del informe (en el Project "REPORTES POR PARTES" de claude.ai) clona este repo y usa el paquete; lo que falte lo busca con WebFetch.

## Reglas
- Solo fuentes oficiales o feeds abiertos (FRED, NY Fed, OFR, fiscaldata, TreasuryDirect, Fed, Tesoro, BEA, SIFMA, Frankfurter). El User-Agent dice siempre que es un bot (`GuiverResearch-datos/...`). Nunca te hagas pasar por un navegador ni intentes saltar bloqueos (Cloudflare, 403, captchas). Investing, Yahoo, CME, Stooq, ICE y FTSE Russell no se usan desde aquí.
- No cambies el formato de salida: `series.csv` con cabecera `serie,fecha,valor,unidad,fuente,estado,retraso_dias,nota`, los nombres de serie y de archivo existentes, y las claves del manifiesto. El orquestador depende de ellos.
- Nada posterior al CORTE (viernes). Un valor vacío es PENDING, nunca cero.
- Antes de cada commit: `python3 datos.py --selftest` debe decir `selftest OK`.
- Una fuente que no se pueda arreglar se deja con `ok: false` y un `error` claro en el manifiesto: el orquestador la buscará con WebFetch. Mejor un hueco declarado que un dato inventado o de otra fecha.
- `xeurbi` falla siempre (CME bloquea a GitHub): no intentes arreglarla.
- No toques `respaldo/` (copias del orquestador).
- Commits en español, cortos, diciendo qué fuente se arregló y por qué falló.
