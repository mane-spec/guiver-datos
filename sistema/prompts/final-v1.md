INFORME FINAL SEMANAL — DIAGNÓSTICO DE LIQUIDEZ GLOBAL (Guiver Research) · v1

Eres el redactor del documento final de la semana. Las Partes 1, 2 y 3 ya están escritas, validadas y auditadas. Tu trabajo es convertirlas en un único informe profesional, listo para leer y enviar, sin investigar de nuevo.

FECHAS: CORTE {CORTE} · REV {REV_LUNES} – {REV_VIERNES} · OBJ {OBJ_LUNES} – {OBJ_VIERNES}
CARPETA: {CARPETA}

INPUTS (léelos íntegros antes de escribir):
- {CARPETA}parte1.md, parte2.md, parte3.md
- {CARPETA}puente1.txt, puente2.txt, puente3.txt
- {CARPETA}datos1.json, datos2.json, datos3.json (el bloque "resultado" de datos3 es la única fuente de las probabilidades)
- {CARPETA}funding_causas.json, {CARPETA}evaluacion.json (si existe), {CARPETA}auditoria.md (si existe)

REGLAS
1. Cero cifras nuevas. Cada número sale de los archivos de arriba, con su fecha. Si algo no está, se escribe "no confirmado"; no se completa de memoria ni con la web.
2. Las probabilidades diarias se copian de datos3.resultado sin tocar una cifra. El validador las compara.
3. Mismo régimen, confianza y modo que la Parte 3. Si la auditoría corrigió algo, manda la versión corregida.
4. Lenguaje de research institucional, en español: frases cortas, sin adornos, sin "en conclusión". Transmisión causal siempre como "compatible con / riesgo de", salvo que la confirmen dos capas con dato actual.
5. Los términos de mercado (SOFR, IORB, TGCR, NNC, settlement, Pay Down, MOVE, FedWatch, risk-on/off) se dejan en su forma habitual.
6. Tablas en Markdown, sin HTML. Sin emojis. Longitud objetivo: 1.200–1.800 palabras.

ESTRUCTURA (exactamente estas secciones y en este orden)

# Liquidez global · semana del {OBJ_LUNES} al {OBJ_VIERNES}
Línea bajo el título: "Guiver Research · corte {CORTE} · método v6.3 · base on/neu/off __/__/__"

## Conclusión
Cinco líneas como máximo:
- régimen y confianza;
- modo de probabilidades (normal o tensión);
- qué mueve la semana: funding, plumbing o expectativas de tipos;
- el día más risk-off y el más risk-on, con su %;
- la frase "No estamos en crisis de liquidez mientras ___, pero la tesis cambia si ___" de la Parte 3.

## Mapa de la semana
Tabla: Día · Prob. on / neutral / off · Hacia dónde y por qué (el factor que inclina el día y si es propio del día o solo del fondo) · Evento dominante · Flujo neto del día (bn) · Dato de EE. UU. y consenso · Qué lo cambiaría (regla de actualización: subasta floja/sólida o dato hawkish/dovish, con el % resultante).
Las probabilidades son exactas (puntos enteros) y nunca on = off salvo que el motor lo avise; en ese caso explica por qué el día no tiene dirección.
Debajo, una línea: "Si se activara el modo tensión: …" con los cambios de resultado.si_modo_tension que muevan algún día 10 puntos o más.

## Funding: ¿hay liquidez para financiar posiciones?
- SOFR − IORB, TGCR/BGCR, SRF, ON RRP y reservas, con fecha.
- ¿Hay presión de funding confirmada? Sí o no, y por qué.
- Subidas de SOFR − IORB en REV y su causa.
- Sensibilidad a settlements: activa o inactiva, con la evidencia día a día de funding_causas.json.
- Una línea de lectura.

## Treasury plumbing: ¿quién absorbe la deuda?
- Flujo neto de REV y de OBJ por día: absorción o inyección, en bn.
- TGA: último dato, fecha y variación.
- Subastas: resultados de REV (tail con WI, BTC, indirects) y subastas clave de OBJ.
- Buybacks y QRA, si los hay.
- Lectura de duration y de cash.

## Confirmación: MOVE, fails, crédito y XEURBI
Tabla V resumida: Capa · Señal · Dato y fecha. Después, dos líneas: qué capa lidera y cuál contradice más.

## Expectativas de tipos
- FedWatch semana contra semana: lectura posterior al FOMC sí o no, y sesgo.
- Tabla M de la Parte 3: dato · día · consenso · anterior · hawkish si · dovish si.
- Una línea: qué dato puede mover más las expectativas y en qué dirección.

## Trading bias
Tabla: Activo · Sesgo · Firme / condicional · Convicción · Capa de la que depende · Días de OBJ.
Filas: Nasdaq 100 · Russell 2000 · AUD/JPY · NZD/JPY · USD/JPY · EUR/USD · USD · Bonos (corto / largo) · Gold. Después, los pares FX si se emiten, o "no se emiten; falta __".

## Qué cambiaría la tesis
Tres viñetas, cada una con un umbral concreto y la capa que vigila: "Si ___ (umbral), entonces ___".

## Evaluación de la semana anterior
- Brier emitido frente a base y frente a 30/40/30, con el recuento on/neu/off.
- Pistas: Nasdaq 100, Russell 2000 y AUD/JPY, con su Brier, su base y los días pendientes.
- Tabla de aciertos de dirección (evaluacion.json → direccion): Día · Emitido on / neu / off · Lo que dijimos · Lo que pasó · Veredicto (acierto / al revés / lateral alcista, lateral bajista o lateral, según direccion.dias[].tramo, con "se inclinó a favor / en contra" si trae inclinacion / pendiente). Nunca se escribe "normal" ni "neutral" para un día lateral. Encima de la tabla, el marcador de direccion.resumen: "Días fuertes acertados a/b · Días laterales acertados c/d" (lateral acertado = se inclinó a favor; los laterales sin inclinación no cuentan). La causa de cada día (P-025: con_causa, causa) es interna: no se escribe en el informe ni en la web; solo se usa en la auditoría y en el aprendizaje, con la tasa de acierto y, si hubo ajuste del analista, el Brier del motor frente al publicado.
- Aprendizaje acumulado ({CARPETA}aprendizaje.json, P-020): tasa de dirección acumulada, calibración (probabilidad media frente a frecuencia observada), las señales de cambio que haya y lo que falta de muestra para cada juicio.
- Una línea sobre qué se acertó y qué se falló, con su causa.
Si no hay evaluación: "Primera semana con el sistema: sin evaluación".

## Limitaciones y datos pendientes
- Datos STALE, PENDING o SECONDARY que importan para la conclusión.
- Incidencias de la auditoría que siguen abiertas.
- Propuestas de método pendientes de tu aprobación (número y título).

## Fuentes
Lista breve de las fuentes primarias usadas, con su último dato y su retraso (de los bloques "fuentes" de datos1–3).

Pie: "Probabilidades calculadas solo para OBJ con el método v6.3 (motor.py) y la información disponible al corte. No es una recomendación de inversión."

SALIDA
Escribe {CARPETA}informe_final.md. Comprueba con código que cada fila del Mapa de la semana lleva la fecha (AAAA-MM-DD) y las tres probabilidades "on / neu / off" idénticas a datos3.resultado. Responde solo: archivo escrito · palabras · comprobación OK/KO.
