#!/usr/bin/env python3
"""
Motor determinista del sistema de liquidez global (método de probabilidades v6).

El modelo de lenguaje decide QUÉ factores aplican (con su dato y fecha) y este
código decide CUÁNTO valen, aplica regla de grupo, topes, modo tensión, fórmula,
mezcla con la base, techo, suelo del neutral y redondeo. Así el cálculo es
idéntico cada semana y el simulador puede reproducirlo.

Uso:
  python3 motor.py selftest
  python3 motor.py prob     <datos3.json>                 # añade "resultado" a datos3.json
  python3 motor.py gli      <gli_input.json> <obj_lunes>  # imprime/guarda tabla GLI proxy G3
  python3 motor.py evaluar  <datos3.json> <datos3_semana_anterior.json>
  python3 motor.py base     <historial.json>              # recalibración (cada 8 semanas)
  python3 motor.py fechas   <AAAA-MM-DD>                  # CORTE -> REV, OBJ, COMP
  python3 motor.py episodios <carpeta> <historial.json> [salida.json]  # funding: subidas, sensibilidad, capa cash
  python3 motor.py neto      <datos2.json> [REV|OBJ]       # flujo neto por día (Σ NNC − buybacks), P-004
  python3 motor.py estado    init|siguiente|hecho|fallo|latido|candado|reanudar|minimo <estado.json> …
  python3 motor.py resumen1  <datos1.json>                # texto de {DATOS1_RESUMEN} para la Parte 2
  python3 motor.py validar   <parte> <carpeta> <marcadores.json>
  python3 motor.py validar_final <carpeta> <marcadores.json>      # documento final de la semana
  python3 motor.py registrar <historial.json> <carpeta> [evaluacion.json]
  python3 motor.py aprender  <historial.json> [salida.json]  # aciertos de dirección, calibración y pesos aprendidos (P-020)
  python3 motor.py rellenar  <plantilla.md> <valores.json> <salida.md>
"""
import json, math, sys, datetime as dt
from collections import defaultdict

METODO = "v6.5"   # v6.4 + P-030 (el motor evalúa las condiciones de las subastas; MOVE ≥ 100 si venía de < 100, ≥ 110 si ya estaba en ≥ 100) · v6.3 + P-021 (funding solo con catalizador) + P-022 (festivo de bonos = base) · aprendizaje A1 (P-020) solo evalúa y propone; no cambia probabilidades · v6.2 + tensión con 2.ª capa (P-012) + base semanal (P-013) + probabilidades exactas sin empates (P-014)
BASE_INICIAL = (20, 50, 30)          # on / neutral / off (%)
PRIOR = (30, 40, 30)
PESO_PRIOR_SESIONES = 10
SEMANAS_RECALIBRACION = 1          # P-013: la base se recalibra cada semana (misma fórmula, prior con peso 10)
PASO = 1                           # P-014: probabilidades exactas (puntos enteros); el autotest del v6 usa paso 5
# P-012: el modo tensión por funding exige además una de estas capas confirmando estrés con dato actual
CONFIRMA_TENSION = ("move_110_135", "move_gt_135", "hy_ge_15", "ccc_ge_40", "fails_subiendo_sobre_media",
                    "xeurbi_le_m5_ampliando3", "srf_material", "tension_bancaria")

# ---------------------------------------------------------------- catálogos v6
# Fondo de la semana: id -> (grupo, lado, puntos normal)
FONDO = {
    # Liquidez global: solo con captura del usuario y confluencia dirección + aceleración (P-003)
    "gli_contraccion_acelerada":          ("liquidez", "off", 1.0),
    "gli_expansion_acelerada":            ("liquidez", "on",  1.0),
    # Funding
    "sofr_ge_iorb":                       ("funding", "off", 1.0),
    "gc_ge_iorb":                         ("funding", "off", 1.0),
    "srf_material":                       ("funding", "off", 1.0),
    "fails_subiendo_sobre_media":         ("funding", "off", 0.5),
    "xeurbi_le_m5_ampliando3":            ("funding", "off", 0.5),
    "sofr_le_iorb_m5_gc_estable":         ("funding", "on",  1.0),
    # Tipos y duration
    "move_110_135":                       ("tipos", "off", 1.0),
    "move_80_110_subiendo10":             ("tipos", "off", 0.5),
    "move_lt_80":                         ("tipos", "on",  1.0),
    "move_gt_135":                        ("tipos", "off", 3.0),   # solo existe en modo tensión
    "fedwatch_hawkish":                   ("tipos", "off", 1.0),
    "fedwatch_dovish_credito_ampliando":  ("tipos", "off", 1.0),
    "fedwatch_dovish_credito_estable":    ("tipos", "on",  1.0),
    # Crédito y banca
    "hy_ge_15":                           ("credito", "off", 1.0),
    "hy_5_15":                            ("credito", "off", 0.5),
    "ccc_ge_40":                          ("credito", "off", 1.0),
    "tension_bancaria":                   ("credito", "off", 1.0),
    "hy_le_m10":                          ("credito", "on",  1.0),
}

# Dispersión del día (suma a los dos lados): id -> (puntos, es_subasta_cupon)
DISPERSION = {
    "sub_10y_30y":          (2.0, True),
    "sub_20y":              (1.5, True),
    "sub_5y_7y":            (1.0, True),
    "tips_10y_mas":         (1.0, True),
    "sub_2y_3y":            (0.5, True),
    "tips_5y":              (0.5, True),
    "settle_cupones_nnc10": (0.5, False),
    "macro1":               (2.0, False),   # CPI, Employment Situation, decisión FOMC, PCE
    "macro2":               (1.0, False),   # PPI, ventas minoristas, ISM, JOLTS, PIB, actas FOMC, earnings 6 grandes bancos
    "megacaps":             (1.0, False),   # máximo 1 por día en total
    "qra":                  (1.0, False),   # anuncio de refinanciación trimestral (Policy Statement), solo ese día (P-002)
}

# Dirección del día: id -> (lado, puntos, condición)
#   condición: None = siempre · "funding" = presión de funding confirmada
#              "funding_o_sensible" = presión confirmada O sensibilidad a settlements demostrada (P-004)
DIRECCION = {
    "subasta_cupon_condiciones_2de3": ("off", 1.0, "subasta_2de3"),   # P-030: 2 de 3 (previas flojas / MOVE / FedWatch hawkish), lo evalúa el motor
    "tips_condiciones":               ("off", 0.5, "tips_move_hawkish"),  # P-030: MOVE y FedWatch hawkish, lo evalúa el motor
    # P-004: el flujo se mide en NETO del día (NNC de todas las familias − buybacks que liquidan)
    "settle_neto_absorcion20":        ("off", 2.0, "funding_o_sensible"),  # absorción neta ≥ +20 bn
    "settle_neto_inyeccion20":        ("on",  1.0, None),                   # inyección neta (pay down) ≥ 20 bn
    "fin_mes":                        ("off", 1.0, "funding"),
    "fin_trimestre":                  ("off", 2.0, "funding"),
    "tax_date":                       ("off", 1.0, "funding"),
    "buyback_liquidez":               ("on",  1.0, None),
    # actualización intrasemanal (simulador y reglas; la Parte 3 no la incluye ex ante)
    "subasta_floja_settlement":       ("off", 1.0, None),
    "subasta_solida_settlement":      ("on",  1.0, None),
    "dato_hawkish":                   ("off", 1.0, None),   # P-005: dato de EE. UU. que sube las expectativas de tipos
    "dato_dovish":                    ("on",  1.0, None),   # P-005: dato que las baja, con crédito estable
}
UMBRAL_NETO_BN = 20.0

PESOS = {  # (normal, tensión)
    "alta":  (0.60, 0.80),
    "media": (0.50, 0.70),
    "baja":  (0.40, 0.60),
}

# ---------------------------------------------------------------- utilidades
def r5(x):
    return int(math.floor(x / 5.0 + 0.5) * 5)

def redondea(x, paso=PASO):
    return int(math.floor(x / paso + 0.5) * paso)

def regla_grupo(valores, tope):
    """El factor de más puntos cuenta entero, los demás a la mitad; tope por grupo."""
    if not valores:
        return 0.0
    v = sorted(valores, reverse=True)
    return min(v[0] + 0.5 * sum(v[1:]), tope)

# ---------------------------------------------------------------- fondo
def puntos_fondo(fondo_ids, por_funding, por_move):
    tension = por_funding or por_move
    tope_grupo = 4.0 if tension else 1.0
    tope_off = 6.0 if tension else 2.0
    tope_on = 2.0
    grupos = defaultdict(list)
    traza, avisos = [], []
    for item in fondo_ids:
        fid = item["id"] if isinstance(item, dict) else item
        if fid not in FONDO:
            avisos.append(f"factor de fondo desconocido: {fid} (ignorado)")
            continue
        grupo, lado, pts = FONDO[fid]
        if fid == "move_gt_135" and not tension:
            avisos.append("move_gt_135 sin modo tensión: incoherente (MOVE>135 activa tensión)")
        if grupo == "funding" and por_funding:
            pts *= 2.0
        grupos[(grupo, lado)].append(pts)
        traza.append({"id": fid, "grupo": grupo, "lado": lado, "pts": pts})
    lado_tot = {"off": 0.0, "on": 0.0}
    por_grupo = {}
    for (grupo, lado), vals in grupos.items():
        g = regla_grupo(vals, tope_grupo)
        por_grupo[f"{grupo}/{lado}"] = g
        lado_tot[lado] += g
    off = min(lado_tot["off"], tope_off)
    on = min(lado_tot["on"], tope_on)
    return {"off": off, "on": on, "por_grupo": por_grupo, "traza": traza,
            "topes": {"grupo": tope_grupo, "off": tope_off, "on": tope_on},
            "antes_de_tope": lado_tot, "avisos": avisos}

# ---------------------------------------------------------------- día
# P-030 (versión del usuario, 2026-11-15): condición de MOVE de las subastas. Referencia = cierre de cinco sesiones antes.
# Si venía de < 100, basta con llegar a 100; si ya estaba en 100 o más, hace falta 110.
MOVE_UMBRAL_BAJO, MOVE_UMBRAL_ALTO = 100.0, 110.0

def condicion_move(series):
    s = [x for x in (series or {}).get("move", []) if x.get("valor") is not None]
    if len(s) < 6: return {"ok": False, "nota": "MOVE sin 6 cierres: condición no confirmada"}
    ult, ref = s[-1], s[-6]
    umbral = MOVE_UMBRAL_BAJO if ref["valor"] < MOVE_UMBRAL_BAJO else MOVE_UMBRAL_ALTO
    return {"ok": ult["valor"] >= umbral, "valor": ult["valor"], "fecha": ult["fecha"], "ref": ref["valor"],
            "ref_fecha": ref["fecha"], "umbral": umbral}

def contexto_subastas(d3):
    ids = {f["id"] if isinstance(f, dict) else f for f in d3.get("fondo", [])}
    return {"move": condicion_move(d3.get("series")), "hawkish": "fedwatch_hawkish" in ids}

def _cond_subasta(cond, e, ctx):
    """P-030: devuelve (cumple, detalle) para las condiciones de subasta, con los datos de datos3."""
    ctx = ctx or {}
    mv = (ctx.get("move") or {}).get("ok", False)
    hk = bool(ctx.get("hawkish"))
    pf = bool(e.get("previas_flojas")) if isinstance(e, dict) else False
    det = {"previas_flojas": pf, "move": mv, "fedwatch_hawkish": hk, "umbral_move": (ctx.get("move") or {}).get("umbral")}
    if cond == "subasta_2de3": return (pf + mv + hk) >= 2, det
    return mv and hk, det

def _cumple(cond, por_funding, sensible):
    if cond is None: return True
    if cond == "funding": return por_funding
    return por_funding or sensible

def puntos_dia(dia, por_funding, sensible=False, ctx=None):
    avisos = []
    sub, otros, mega = [], 0.0, 0.0
    for e in dia.get("dispersion", []):
        eid = e["id"] if isinstance(e, dict) else e
        if eid not in DISPERSION:
            avisos.append(f"dispersión desconocida: {eid}")
            continue
        pts, es_sub = DISPERSION[eid]
        if eid == "megacaps":
            mega = 1.0
        elif es_sub:
            sub.append(pts)
        else:
            otros += pts
    sub_tot = regla_grupo(sub, 99) if sub else 0.0  # 2 subastas: la mayor entera, la otra a la mitad
    disp = sub_tot + otros + mega
    d_off = d_on = 0.0
    traza = []
    for e in dia.get("direccion", []):
        eid = e["id"] if isinstance(e, dict) else e
        if eid not in DIRECCION:
            avisos.append(f"dirección desconocida: {eid}")
            continue
        lado, pts, cond = DIRECCION[eid]
        if cond in ("subasta_2de3", "tips_move_hawkish"):
            ok, det = _cond_subasta(cond, e, ctx)
            if not ok:
                traza.append({"id": eid, "pts": 0.0, "nota": "condiciones de subasta no cumplidas: 0 (P-030)", "condiciones": det})
                continue
            if lado == "off": d_off += pts
            else: d_on += pts
            traza.append({"id": eid, "lado": lado, "pts": pts, "condiciones": det})
            continue
        if not _cumple(cond, por_funding, sensible):
            nota = "sin presión de funding confirmada: 0" if cond == "funding" else "sin presión de funding ni sensibilidad a settlements: 0"
            traza.append({"id": eid, "pts": 0.0, "nota": nota})
            continue
        if lado == "off":
            d_off += pts
        else:
            d_on += pts
        traza.append({"id": eid, "lado": lado, "pts": pts})
    return disp, d_off, d_on, traza, avisos

# ---------------------------------------------------------------- fórmula
def probabilidades(pts_off, pts_on, tension, confianza="alta", base=BASE_INICIAL, paso=PASO):
    bon, bneu, boff = [b / 100.0 for b in base]
    s_off = math.log(boff / bneu) + 0.2 * pts_off
    s_on = math.log(bon / bneu) + 0.2 * pts_on
    den = 1 + math.exp(s_on) + math.exp(s_off)
    modelo = (math.exp(s_on) / den, 1 / den, math.exp(s_off) / den)
    w = PESOS[confianza][1 if tension else 0]
    mezcla = [w * modelo[i] + (1 - w) * b for i, b in enumerate((bon, bneu, boff))]
    techo = False
    if not tension:
        for i in (0, 2):
            if mezcla[i] > 0.60:
                mezcla[1] += mezcla[i] - 0.60
                mezcla[i] = 0.60
                techo = True
    on, off = redondea(mezcla[0] * 100, paso), redondea(mezcla[2] * 100, paso)
    neu = 100 - on - off
    suelo = False
    if not tension:
        while neu < 20:
            if off >= on: off -= paso
            else: on -= paso
            neu = 100 - on - off
            suelo = True
    # P-014: nunca on = off si el cálculo sin redondear inclina hacia un lado (el que va por delante gana un paso)
    empate = False
    if on == off:
        if mezcla[0] > mezcla[2] + 1e-9: on += paso; off -= paso
        elif mezcla[2] > mezcla[0] + 1e-9: off += paso; on -= paso
        else: empate = True
    return {"on": on, "neu": neu, "off": off, "empate_sin_direccion": empate,
            "S_off": round(s_off, 4), "S_on": round(s_on, 4),
            "modelo": [round(x * 100, 2) for x in modelo],
            "peso_modelo": w, "mezcla": [round(x * 100, 2) for x in mezcla],
            "techo": techo, "suelo_neutral": suelo}

GLI_IDS = ("gli_contraccion_acelerada", "gli_expansion_acelerada")

def filtrar_gli(d3):
    """P-003: el GLI solo puntúa con la captura del usuario. Devuelve (fondo_limpio, descartados)."""
    fuente = (d3.get("gli") or {}).get("puntua", {}).get("fuente")
    fondo, fuera = [], []
    for f in d3.get("fondo", []):
        fid = f["id"] if isinstance(f, dict) else f
        if fid in GLI_IDS and fuente != "captura":
            fuera.append(f)
        else:
            fondo.append(f)
    return fondo, fuera

# P-021: la presión de funding solo inclina el día que tiene un catalizador de caja (absorción neta, fin de mes,
# fin de trimestre o tax date). P-022: en un festivo de bonos (renta variable abierta) no hay catalizador ni dato de
# crédito: el día se queda en la base.
FUNDING_CON_CATALIZADOR = ("sofr_ge_iorb", "gc_ge_iorb")
CATALIZADORES_CAJA = ("settle_neto_absorcion20", "fin_mes", "fin_trimestre", "tax_date")

def fondo_del_dia(fondo, dia):
    ids = [f["id"] if isinstance(f, dict) else f for f in fondo]
    if dia.get("bonos_abierto") is False:
        return [], "festivo de bonos: sin catalizador ni dato de crédito, el día se queda en la base (P-022)"
    dir_ids = {e["id"] if isinstance(e, dict) else e for e in dia.get("direccion", [])}
    if dir_ids & set(CATALIZADORES_CAJA):
        return ids, "con catalizador de caja: cuenta todo el fondo"
    fuera = [i for i in ids if i in FUNDING_CON_CATALIZADOR]
    return [i for i in ids if i not in FUNDING_CON_CATALIZADOR], ("sin catalizador de caja: la presión de funding no inclina este día (P-021)" if fuera else "")

def calcular(d3):
    fondo_ok, gli_fuera = filtrar_gli(d3)
    if gli_fuera:
        d3 = {**d3, "fondo": fondo_ok}
    mt = d3.get("modo_tension", {})
    presion, por_move, forzar = bool(mt.get("por_funding")), bool(mt.get("por_move")), bool(mt.get("forzar"))
    ids_fondo = {f["id"] if isinstance(f, dict) else f for f in d3.get("fondo", [])}
    # P-012: la presión de funding (regla del usuario, sin cambios) sigue puntuando; el MODO tensión exige una 2.ª capa
    por_funding = presion and (forzar or bool(ids_fondo & set(CONFIRMA_TENSION)))
    tension = por_funding or por_move
    base = tuple(d3.get("base", BASE_INICIAL))
    conf_global = d3.get("confianza", "alta")
    fondo = puntos_fondo(d3.get("fondo", []), por_funding, por_move)
    out_dias, avisos = [], list(fondo["avisos"])
    cache_fondo = {}
    if presion and not por_funding:
        avisos.append("presión de funding confirmada sin segunda capa que confirme estrés: modo normal (P-012)")
    if gli_fuera:
        avisos.append("factor GLI descartado: solo puntúa con captura del usuario (P-003)")
    sensible = bool((d3.get("sensibilidad_settlement") or {}).get("activa"))
    ctx_sub = contexto_subastas(d3)
    for dia in d3.get("dias", []):
        disp, d_off, d_on, traza, av = puntos_dia(dia, presion, sensible, ctx_sub)
        avisos += [f'{dia.get("fecha")}: {a}' for a in av]
        conf = conf_global if dia.get("evento_verificado", True) else "baja"
        ids_dia, nota_fondo = fondo_del_dia(d3.get("fondo", []), dia)
        clave = tuple(sorted(ids_dia))
        if clave not in cache_fondo: cache_fondo[clave] = puntos_fondo([{"id": i} for i in ids_dia], por_funding, por_move)
        fd = cache_fondo[clave]
        p_off = disp + d_off + fd["off"]
        p_on = disp + d_on + fd["on"]
        pr = probabilidades(p_off, p_on, tension, conf, base)
        if pr["empate_sin_direccion"]:
            avisos.append(f'{dia.get("fecha")}: on = off sin ninguna inclinación en el cálculo: explicar en el informe por qué el día no tiene dirección')
        if not tension and pr["off"] >= 55 and d_off == 0:
            avisos.append(f'{dia.get("fecha")}: risk-off ≥55 % sin tensión ni dirección del Paso 2: revisar puntos')
        out_dias.append({"fecha": dia.get("fecha"), "dia": dia.get("dia"),
                         "dispersion": disp, "dir_off": d_off, "dir_on": d_on,
                         "fondo_off": fd["off"], "fondo_on": fd["on"], "fondo_traza": fd["traza"], "fondo_nota": nota_fondo,
                         "pts_off": p_off, "pts_on": p_on,
                         "modo": "tensión" if tension else "normal",
                         "confianza": conf, "prob": {k: pr[k] for k in ("on", "neu", "off")},
                         "calculo": pr, "traza_direccion": traza})
    # resúmenes
    res = {"metodo": METODO, "base": list(base), "modo": "tensión" if tension else "normal",
           "presion_funding": presion, "tension_por_funding": por_funding,
           "sensibilidad_settlement": sensible, "condiciones_subasta": ctx_sub, "fondo": fondo, "dias": out_dias, "avisos": avisos}
    if out_dias:
        res["dia_mas_on"] = max(out_dias, key=lambda d: (d["prob"]["on"], -d["prob"]["off"]))["fecha"]
        res["dia_mas_off"] = max(out_dias, key=lambda d: (d["prob"]["off"], -d["prob"]["on"]))["fecha"]
        res["dia_mas_dispersion"] = min(out_dias, key=lambda d: d["prob"]["neu"])["fecha"]
    return res

def sensibilidad_tension(d3):
    """Probabilidades de cada día si se activara el modo tensión por funding."""
    alt = json.loads(json.dumps(d3))
    alt.setdefault("modo_tension", {})["por_funding"] = True
    alt["modo_tension"]["forzar"] = True     # hipótesis: tensión activada aunque falte la 2.ª capa
    ids = {f["id"] if isinstance(f, dict) else f for f in alt.get("fondo", [])}
    for fid in ("sofr_ge_iorb", "gc_ge_iorb"):
        if fid not in ids:
            alt["fondo"].append({"id": fid, "dato": "hipótesis de sensibilidad"})
    return {d["fecha"]: d["prob"] for d in calcular(alt)["dias"]}

def reglas_actualizacion(d3):
    """Reglas intrasemanales.
    - Subasta de cupón 5Y+: {subasta, fecha_subasta, dia_settlement} → probabilidad del día del settlement si sale floja o sólida.
    - Dato de EE. UU. (P-005): {tipo: "macro", evento, dia, consenso, anterior, hawkish_si, dovish_si} → probabilidad del día
      si el dato sale hawkish (sube expectativas de tipos) o dovish."""
    out = []
    for regla in d3.get("reglas_actualizacion", []):
        if regla.get("tipo") == "macro":
            dia_obj, casos = regla.get("dia"), (("hawkish", "dato_hawkish"), ("dovish", "dato_dovish"))
        else:
            dia_obj, casos = regla.get("dia_settlement"), (("floja", "subasta_floja_settlement"), ("solida", "subasta_solida_settlement"))
        res = {}
        for caso, fid in casos:
            alt = json.loads(json.dumps(d3))
            for dia in alt.get("dias", []):
                if dia.get("fecha") == dia_obj:
                    dia.setdefault("direccion", []).append({"id": fid})
            c = calcular(alt)
            res[caso] = next((d["prob"] for d in c["dias"] if d["fecha"] == dia_obj), None)
        out.append({**regla, **res})
    return out

# ---------------------------------------------------------------- evaluación REV
# ---------------------------------------------------------------- P-026: cesta por canales de liquidez
# Cada activo: (campo en evaluacion_rev.dias, signo de riesgo, σ diaria de respaldo si no hay historia de 20 sesiones).
CESTA = {
    "renta_variable": [("rut_pct", 1, 1.4), ("rsp_pct", 1, 0.9), ("ndx_pct", 1, 1.3)],
    "credito":        [("hy_pb", -1, 5.0), ("ccc_pb", -1, 15.0)],
    "tipos_colateral": [("move_pct", -1, 4.0)],
    "dolar_carry":    [("dxy_pct", -1, 0.4), ("audjpy_pct", 1, 0.7), ("usdjpy_pct", 1, 0.5)],
    "refugio":        [("vix_pct", -1, 6.0), ("oro_cobre_pct", -1, 1.2)],
}
CESTA_SUSTITUTOS = {"rsp_pct": "spx_pct"}      # sin RSP, el S&P 500 ocupa su sitio
CESTA_UMBRAL_FUERTE, CESTA_UMBRAL_CANAL, CESTA_MIN_CANALES = 0.75, 0.25, 3

def clasificar_cesta(d, sigmas=None):
    """Nota del día = media de canales (cada canal = media de z de sus activos, z = signo·x/σ, recortado a ±3).
    Fuerte si |nota| ≥ 0,75 y ≥ 3 canales apuntan igual (|canal| ≥ 0,25); lateral alcista/bajista si |nota| ≥ 0,25.
    Con menos de 3 canales con dato, o sin el canal de crédito: 'nc'."""
    sigmas = sigmas or {}
    canales, usados = {}, {}
    for c, activos in CESTA.items():
        zs = []
        for campo, sg, s0 in activos:
            x, cp = d.get(campo), campo
            if x is None and campo in CESTA_SUSTITUTOS: cp = CESTA_SUSTITUTOS[campo]; x = d.get(cp)
            if x is None: continue
            sig = sigmas.get(cp) or s0
            zs.append(max(-3.0, min(3.0, sg * x / sig))); usados.setdefault(c, []).append(cp)
        if zs: canales[c] = round(sum(zs) / len(zs), 3)
    if "credito" not in canales:                       # el crédito es obligatorio: sin él (PENDING) el día espera
        return {"resultado": "nc", "nota": None, "canales": canales, "activos": usados, "motivo": "falta el canal de crédito (HY/CCC)"}
    if len(canales) < CESTA_MIN_CANALES:
        return {"resultado": "nc", "nota": None, "canales": canales, "activos": usados, "motivo": f"solo {len(canales)} canales con dato"}
    nota = round(sum(canales.values()) / len(canales), 3)
    a_on = sum(1 for v in canales.values() if v >= CESTA_UMBRAL_CANAL)
    a_off = sum(1 for v in canales.values() if v <= -CESTA_UMBRAL_CANAL)
    if nota >= CESTA_UMBRAL_FUERTE and a_on >= CESTA_MIN_CANALES: o = "on"
    elif nota <= -CESTA_UMBRAL_FUERTE and a_off >= CESTA_MIN_CANALES: o = "off"
    else: o = "neu"
    tramo = None
    if o == "neu":
        tramo = "lateral alcista" if nota >= CESTA_UMBRAL_CANAL else "lateral bajista" if nota <= -CESTA_UMBRAL_CANAL else "lateral"
    return {"resultado": o, "nota": nota, "canales": canales, "canales_on": a_on, "canales_off": a_off,
            "tramo": tramo, "activos": usados, "faltan": [c for c in CESTA if c not in canales]}

def sigmas_de_series(series, n=20):
    """σ de 20 sesiones de los cambios diarios, a partir de datos3.series (hy/ccc en pb, move en %)."""
    out = {}
    def sd(v):
        if len(v) < 10: return None
        m = sum(v) / len(v); return (sum((x - m) ** 2 for x in v) / (len(v) - 1)) ** 0.5
    for k, campo, pct in (("hy", "hy_pb", False), ("ccc", "ccc_pb", False), ("move", "move_pct", True)):
        sr = [x for x in (series or {}).get(k, []) if (x.get("pb") if not pct else x.get("valor")) is not None]
        vals = [x["valor"] if pct else x["pb"] for x in sr]
        ch = [((vals[i] / vals[i-1] - 1) * 100 if pct else vals[i] - vals[i-1]) for i in range(1, len(vals))][-n:]
        s = sd(ch)
        if s: out[campo] = round(s, 3)
    return out

def clasificar(spx, hy, move):
    off = [spx is not None and spx <= -0.5, hy is not None and hy >= 5, move is not None and move >= 3]
    on = [spx is not None and spx >= 0.5, hy is not None and hy <= -5, move is not None and move <= -3]
    if sum(off) >= 2: return "off"
    if sum(on) >= 2: return "on"
    if None in (spx, hy, move): return "nc"
    return "neu"

def brier(p, o):
    obs = {"on": (1, 0, 0), "neu": (0, 1, 0), "off": (0, 0, 1)}[o]
    q = (p["on"] / 100, p["neu"] / 100, p["off"] / 100)
    return sum((q[i] - obs[i]) ** 2 for i in range(3))

# Pistas adicionales de evaluación (no cambian la clasificación principal ni la base):
# umbral diario en % para risk-on/off; iniciales, se revisan con datos.
PISTAS = {"nasdaq100": ("Nasdaq 100", "ndx_pct", 0.7), "russell2000": ("Russell 2000", "rut_pct", 0.8),
          "audjpy": ("AUD/JPY", "audjpy_pct", 0.3)}

def clasificar_pista(x, umbral):
    if x is None: return "nc"
    return "off" if x <= -umbral else "on" if x >= umbral else "neu"

def evaluar_pistas(d3, prev, base_prev):
    out = {}
    media = lambda v: round(sum(v) / len(v), 4) if v else None
    for k, (nombre, campo, u) in PISTAS.items():
        b_e, b_b, cuenta, dias = [], [], {"on": 0, "neu": 0, "off": 0, "nc": 0}, []
        for d in d3.get("evaluacion_rev", {}).get("dias", []):
            o = clasificar_pista(d.get(campo), u); cuenta[o] += 1
            p = prev.get(d["fecha"])
            fila = {"fecha": d["fecha"], "valor": d.get(campo), "resultado": o}
            if o != "nc" and p:
                fila["brier"] = round(brier(p, o), 4); b_e.append(fila["brier"])
                b_b.append(brier(dict(zip(("on", "neu", "off"), base_prev)), o))
            dias.append(fila)
        out[k] = {"nombre": nombre, "umbral_pct": u, "recuento": cuenta, "brier_emitido": media(b_e),
                  "brier_base": media(b_b), "dias_puntuados": len(b_e), "dias": dias}
    return out

def evaluar(d3, d3_prev):
    prev = {d["fecha"]: d["prob"] for d in d3_prev.get("resultado", {}).get("dias", [])}
    base_prev = d3_prev.get("resultado", {}).get("base", list(BASE_INICIAL))
    filas, b_emit, b_base, b_prior = [], [], [], []
    cuenta = {"on": 0, "neu": 0, "off": 0, "nc": 0}
    ser = [x for x in (d3.get("series") or {}).get("sofr_iorb", []) if x.get("pb") is not None]
    dfund = {ser[i]["fecha"]: ser[i]["pb"] - ser[i - 1]["pb"] for i in range(1, len(ser))}
    sig = {**sigmas_de_series(d3.get("series")), **(d3.get("evaluacion_rev", {}).get("sigmas") or {})}
    for d in d3.get("evaluacion_rev", {}).get("dias", []):
        o_ant = clasificar(d.get("spx_pct"), d.get("hy_pb"), d.get("move_pct"))
        ce = clasificar_cesta(d, sig)                      # P-026: manda la cesta
        o = ce["resultado"]
        cuenta[o] += 1
        fila = {**d, "resultado": o, "cesta": ce, "clasif_anterior": o_ant}
        if o in ("on", "off"):
            fila.update(causa_dia(o, dfund.get(d["fecha"]), d.get("causa"), d.get("causa_motivo")))
        p = prev.get(d["fecha"])
        if o != "nc" and p:
            fila["prob_emitida"] = p
            fila["brier"] = round(brier(p, o), 4)
            b_emit.append(fila["brier"])
            b_base.append(brier(dict(zip(("on", "neu", "off"), base_prev)), o))
            b_prior.append(brier(dict(zip(("on", "neu", "off"), PRIOR)), o))
        filas.append(fila)
    media = lambda v: round(sum(v) / len(v), 4) if v else None
    prev_dias = {d["fecha"]: d for d in d3_prev.get("resultado", {}).get("dias", [])}
    return {"dias": filas, "recuento": cuenta, "brier_emitido": media(b_emit),
            "brier_base": media(b_base), "brier_304030": media(b_prior),
            "dias_puntuados": len(b_emit), "pistas": evaluar_pistas(d3, prev, base_prev),
            "direccion": evaluar_direccion(filas, prev_dias)}

# ---------------------------------------------------------------- aprendizaje (P-020)
# Mide si "lo que dijimos" coincidió con lo que pasó y aprende de ello. Nunca cambia nada solo:
# cuando la evidencia supera los umbrales de muestra, devuelve una propuesta con su porqué.
# El motor ya es una neurona softmax (s = intercepto + 0,2·puntos); aprender = ajustar esos pesos a los resultados,
# con un prior fuerte hacia los pesos vigentes para no sobreajustar con pocas semanas.
MIN_DIAS_DIRECCION = 10     # días con movimiento (on/off) para juzgar la dirección
MIN_DIAS_CALIBRACION = 20   # días puntuados para juzgar la calibración global
MIN_DIAS_FACTOR = 8         # días con un factor activo para juzgarlo
MIN_DIAS_AJUSTE = 30        # días con componentes para proponer pesos nuevos
MIN_AJUSTES_MANUALES = 4    # días con ajuste del analista para juzgar los ajustes
UMBRAL_LR = 14.07           # razón de verosimilitud (χ² 7 g.l., p < 0,05) para proponer pesos nuevos

def lado_emitido(p):
    d = p["on"] - p["off"]
    return "on" if d > 0 else "off" if d < 0 else "eq"

CAUSAS = ("liquidez", "sector", "politico_macro", "desconocida", "otra")

def causa_dia(o, delta_pb, causa_analista=None, motivo=None):
    """P-025 (interno, no va a la web): causa de un día on/off. Manda la del analista; si no hay,
    'liquidez' cuando el funding se movió en la misma dirección ese día (SOFR−IORB ≥ +1 pb en un off,
    ≤ −1 pb en un on) y 'otra' si no."""
    auto = None
    if delta_pb is not None:
        auto = "liquidez" if (delta_pb >= 1 if o == "off" else delta_pb <= -1) else "otra"
    c = causa_analista if causa_analista in CAUSAS else (auto or "desconocida")
    r = {"causa": c, "causa_fuente": "analista" if causa_analista in CAUSAS else "automática", "funding_delta_pb": delta_pb, "causa_auto": auto}
    if motivo: r["causa_motivo"] = motivo
    return r

LATERAL_UMBRAL_PCT = 0.25   # S&P 500: día lateral con sesgo si |%| ≥ 0,25 (la mitad del umbral de 0,5 % de clasificar)

def tramo_lateral(spx):
    """Etiqueta de un día neutral: lateral alcista / lateral bajista / lateral, según el S&P 500."""
    if spx is None: return "lateral"
    return "lateral alcista" if spx >= LATERAL_UMBRAL_PCT else "lateral bajista" if spx <= -LATERAL_UMBRAL_PCT else "lateral"

def evaluar_direccion(filas, prev_dias):
    """Tabla de aciertos de dirección: lo que dijimos (el lado que iba por delante, on u off) frente a lo que pasó."""
    out, c = [], {"acierto": 0, "al_reves": 0, "neutral": 0, "nc": 0, "sin_direccion": 0}
    for f in filas:
        pd_ = prev_dias.get(f["fecha"]) or {}
        p = f.get("prob_emitida") or pd_.get("prob")
        if not p: continue
        lado, o = lado_emitido(p), f["resultado"]
        v = ("nc" if o == "nc" else "neutral" if o == "neu" else "sin_direccion" if lado == "eq"
             else "acierto" if lado == o else "al_reves")
        c[v] += 1
        x = {"fecha": f["fecha"], "prob": {k: p[k] for k in ("on", "neu", "off")}, "dijimos": lado,
             "margen_pts": abs(p["on"] - p["off"]), "resultado": o, "veredicto": v}
        aj = pd_.get("ajuste_manual")
        if isinstance(aj, dict) and isinstance(aj.get("motor"), list):
            pm = dict(zip(("on", "neu", "off"), aj["motor"]))
            x["manual"] = {"motor": pm, "dijo_motor": lado_emitido(pm)}
            if o != "nc":
                x["manual"].update({"brier_motor": round(brier(pm, o), 4), "brier_publicado": round(brier(p, o), 4)})
        if o in ("on", "off") and f.get("causa"):
            x["causa"] = f["causa"]
            if v == "acierto": x["con_causa"] = f["causa"] == "liquidez"
        if o == "neu":
            x["tramo"] = (f.get("cesta") or {}).get("tramo") or tramo_lateral(f.get("spx_pct"))
            if lado in ("on", "off") and x["tramo"] != "lateral":
                x["inclinacion"] = "a favor" if (lado == "on") == (x["tramo"] == "lateral alcista") else "en contra"
        out.append(x)
    mov = c["acierto"] + c["al_reves"]
    lat = [x for x in out if x["veredicto"] == "neutral"]
    resumen = {"fuertes": {"acertados": c["acierto"], "total": mov},
               "laterales": {"acertados": sum(1 for x in lat if x.get("inclinacion") == "a favor"),
                             "total": sum(1 for x in lat if x.get("inclinacion")), "planos": sum(1 for x in lat if not x.get("inclinacion"))},
               "aciertos_sin_causa": sum(1 for x in out if x.get("con_causa") is False)}
    return {"dias": out, "recuento": c, "dias_con_movimiento": mov, "resumen": resumen,
            "tasa_acierto": round(c["acierto"] / mov, 3) if mov else None,
            "nota": "Dirección = el lado (on u off) con más probabilidad emitida. Los días laterales (neutrales) y no clasificables no cuentan como acierto ni fallo; el lateral se etiqueta alcista o bajista si el S&P 500 se movió ≥ 0,25 % y se indica si se inclinó a favor o en contra de lo que dijimos."}

def _registro_factores(d3, res):
    """Factores activos y componentes de puntos de cada día emitido (para aprender después)."""
    fondo = [t["id"] for t in res.get("fondo", {}).get("traza", [])]
    por_fecha = {d.get("fecha"): d for d in d3.get("dias", [])}
    out = []
    for x in res.get("dias", []):
        d = por_fecha.get(x["fecha"], {})
        r = {"fecha": x["fecha"], "prob": x["prob"], "base": res.get("base"), "modo": x["modo"], "confianza": x["confianza"],
             "fondo": fondo, "dispersion": [e["id"] if isinstance(e, dict) else e for e in d.get("dispersion", [])],
             "direccion": [t["id"] for t in x.get("traza_direccion", []) if t.get("pts")],
             "componentes": {"fondo_off": x["fondo_off"], "fondo_on": x["fondo_on"], "disp": x["dispersion"],
                             "dir_off": x["dir_off"], "dir_on": x["dir_on"]}}
        aj = x.get("ajuste_manual")
        if isinstance(aj, dict) and isinstance(aj.get("motor"), list): r["motor"] = aj["motor"]
        out.append(r)
    return out

def dataset_aprendizaje(hist):
    """Une cada día emitido con su resultado (que llega una semana después, en resultados_rev)."""
    emit, resu, excl = {}, {}, set()
    for s in hist.get("semanas", []):
        for p in s.get("prob_emitidas", []):
            emit.setdefault(p["fecha"], {"fecha": p["fecha"], "prob": {k: p[k] for k in ("on", "neu", "off")},
                                         "base": s.get("base_usada")})
        for f in s.get("factores_dias", []): emit[f["fecha"]] = {**emit.get(f["fecha"], {}), **f}
        for d in (s.get("direccion_rev") or {}).get("dias", []):
            if d.get("causa") and d["causa"] != "liquidez": excl.add(d["fecha"])   # P-025
            emit.setdefault(d["fecha"], {"fecha": d["fecha"], "prob": d["prob"]})
            if d.get("manual"): emit[d["fecha"]].setdefault("motor", [d["manual"]["motor"][k] for k in ("on", "neu", "off")])
            resu.setdefault(d["fecha"], d["resultado"])
        for r in s.get("resultados_rev", []): resu[r["fecha"]] = r["resultado"]
    return [{**emit[f], "resultado": resu[f]} for f in sorted(emit) if resu.get(f) in ("on", "neu", "off") and f not in excl]

def _modelo_dia(th, r):
    a_on, a_off, k_fo, k_fn, k_d, k_do, k_dn = th
    c = r["componentes"]
    s_on = a_on + k_fn * c["fondo_on"] + k_d * c["disp"] + k_dn * c["dir_on"]
    s_off = a_off + k_fo * c["fondo_off"] + k_d * c["disp"] + k_do * c["dir_off"]
    m = max(s_on, 0.0, s_off)
    e = (math.exp(s_on - m), math.exp(-m), math.exp(s_off - m))
    t = sum(e); mod = [x / t for x in e]
    b = [v / 100.0 for v in (r.get("base") or BASE_INICIAL)]
    w = PESOS[r.get("confianza", "alta")][1 if r.get("modo") == "tensión" else 0]
    return [w * mod[i] + (1 - w) * b[i] for i in range(3)]

def ajustar_pesos(datos, iters=3000, lr=0.05):
    """Máxima verosimilitud con prior gaussiano hacia los pesos vigentes (σ 0,5 en interceptos, 0,1 en pendientes)."""
    rs = [r for r in datos if r.get("componentes")]
    if not rs: return None
    b = rs[-1].get("base") or list(BASE_INICIAL)
    th0 = [math.log(b[0] / b[1]), math.log(b[2] / b[1]), 0.2, 0.2, 0.2, 0.2, 0.2]
    sig = [0.5, 0.5, 0.1, 0.1, 0.1, 0.1, 0.1]
    idx = {"on": 0, "neu": 1, "off": 2}
    nll = lambda th: -sum(math.log(max(1e-9, _modelo_dia(th, r)[idx[r["resultado"]]])) for r in rs)
    obj = lambda th: nll(th) + sum(((th[i] - th0[i]) / sig[i]) ** 2 / 2 for i in range(7))
    th = list(th0)
    for _ in range(iters):
        g = []
        for i in range(7):
            h = 1e-5; tp = list(th); tp[i] += h; tm = list(th); tm[i] -= h
            g.append((obj(tp) - obj(tm)) / (2 * h))
        th = [th[i] - lr * sig[i] ** 2 * g[i] for i in range(7)]
    lr_stat = 2 * (nll(th0) - nll(th))
    nombres = ["intercepto_on", "intercepto_off", "pts_fondo_off", "pts_fondo_on", "pts_dispersion", "pts_direccion_off", "pts_direccion_on"]
    return {"n": len(rs), "vigente": dict(zip(nombres, [round(x, 4) for x in th0])),
            "aprendido": dict(zip(nombres, [round(x, 4) for x in th])),
            "logverosimilitud_vigente": round(-nll(th0), 3), "logverosimilitud_aprendida": round(-nll(th), 3),
            "razon_verosimilitud": round(lr_stat, 3)}

def aprendizaje(hist):
    """Diagnóstico acumulado: dirección, calibración, factores, ajustes manuales y pesos aprendidos, con señales de cambio."""
    datos = dataset_aprendizaje(hist)
    media = lambda v: round(sum(v) / len(v), 2) if v else None
    out = {"dias_puntuados": len(datos), "desde": datos[0]["fecha"] if datos else None, "hasta": datos[-1]["fecha"] if datos else None}
    # 1. dirección
    mov = [r for r in datos if r["resultado"] in ("on", "off") and lado_emitido(r["prob"]) != "eq"]
    ac = [r for r in mov if lado_emitido(r["prob"]) == r["resultado"]]
    ult = mov[-MIN_DIAS_DIRECCION:]
    out["direccion"] = {"dias_con_movimiento": len(mov), "aciertos": len(ac), "tasa": round(len(ac) / len(mov), 3) if mov else None,
                        "tasa_ultimos": round(sum(1 for r in ult if lado_emitido(r["prob"]) == r["resultado"]) / len(ult), 3) if ult else None,
                        "al_reves": [r["fecha"] for r in mov if lado_emitido(r["prob"]) != r["resultado"]]}
    # 2. calibración
    cal = {}
    for k in ("on", "neu", "off"):
        cal[k] = {"prob_media": media([r["prob"][k] for r in datos]),
                  "frecuencia": round(100 * sum(1 for r in datos if r["resultado"] == k) / len(datos), 1) if datos else None}
    out["calibracion"] = cal
    out["brier"] = {"emitido": round(media([brier(r["prob"], r["resultado"]) for r in datos]) or 0, 4) if datos else None}
    # 3. factores
    fac = defaultdict(list)
    for r in datos:
        for fid in set(r.get("fondo", []) + r.get("dispersion", []) + r.get("direccion", [])): fac[fid].append(r)
    out["factores"] = {f: {"n": len(v), "off_predicho": media([r["prob"]["off"] for r in v]),
                           "off_observado": round(100 * sum(1 for r in v if r["resultado"] == "off") / len(v), 1),
                           "on_predicho": media([r["prob"]["on"] for r in v]),
                           "on_observado": round(100 * sum(1 for r in v if r["resultado"] == "on") / len(v), 1),
                           "muestra": "suficiente" if len(v) >= MIN_DIAS_FACTOR else "pequeña"} for f, v in sorted(fac.items())}
    # 4. ajustes manuales
    man = [r for r in datos if r.get("motor")]
    out["ajustes_manuales"] = {"n": len(man), "dias": [{"fecha": r["fecha"], "resultado": r["resultado"],
                                                        "brier_publicado": round(brier(r["prob"], r["resultado"]), 4),
                                                        "brier_motor": round(brier(dict(zip(("on", "neu", "off"), r["motor"])), r["resultado"]), 4)} for r in man]}
    # 5. pesos aprendidos (neurona softmax del motor)
    out["pesos"] = ajustar_pesos(datos) if sum(1 for r in datos if r.get("componentes")) >= 3 else None
    out["senales"] = senales_aprendizaje(out)
    return out

def senales_aprendizaje(a):
    """Convierte el diagnóstico en propuestas solo cuando la muestra lo permite; si no, dice cuánto falta."""
    s, falta = [], []
    d = a.get("direccion", {})
    if d.get("dias_con_movimiento", 0) >= MIN_DIAS_DIRECCION:
        if d["tasa_ultimos"] is not None and d["tasa_ultimos"] < 0.5:
            s.append(f"Dirección: en los últimos {MIN_DIAS_DIRECCION} días con movimiento solo se acertó el {round(100 * d['tasa_ultimos'])} % "
                     f"(fallos al revés: {', '.join(d['al_reves'][-5:])}). Revisar qué factores de dirección y fondo estaban activos esos días.")
    else: falta.append(f"dirección: {d.get('dias_con_movimiento', 0)}/{MIN_DIAS_DIRECCION} días con movimiento")
    n = a.get("dias_puntuados", 0)
    if n >= MIN_DIAS_CALIBRACION:
        for k, t in (("off", "risk-off"), ("on", "risk-on"), ("neu", "neutral")):
            c = a["calibracion"][k]
            if c["prob_media"] is not None and abs(c["prob_media"] - c["frecuencia"]) > 10:
                s.append(f"Calibración: se emite {t} con {c['prob_media']} % de media y ocurre el {c['frecuencia']} % de los días ({n} días). "
                         f"Valorar mover la base o el peso del modelo hacia la frecuencia observada.")
    else: falta.append(f"calibración: {n}/{MIN_DIAS_CALIBRACION} días")
    for f, v in a.get("factores", {}).items():
        if v["n"] >= MIN_DIAS_FACTOR:
            for lado in ("off", "on"):
                gap = v[f"{lado}_observado"] - v[f"{lado}_predicho"]
                if abs(gap) > 15:
                    s.append(f"Factor {f}: con él activo se predijo {lado} {v[f'{lado}_predicho']} % y ocurrió {v[f'{lado}_observado']} % "
                             f"({v['n']} días). Su peso parece {'corto' if gap > 0 else 'excesivo'}.")
    man = a.get("ajustes_manuales", {})
    if man.get("n", 0) >= MIN_AJUSTES_MANUALES:
        peor = sum(1 for x in man["dias"] if x["brier_publicado"] > x["brier_motor"])
        if peor > man["n"] / 2:
            s.append(f"Ajustes manuales: en {peor} de {man['n']} días el ajuste del analista puntuó peor que el motor. Valorar dejar de ajustar a mano.")
    elif man.get("n"): falta.append(f"ajustes manuales: {man['n']}/{MIN_AJUSTES_MANUALES} días")
    p = a.get("pesos")
    if p and p["n"] >= MIN_DIAS_AJUSTE and p["razon_verosimilitud"] > UMBRAL_LR:
        cambios = [f"{k} {p['vigente'][k]} → {p['aprendido'][k]}" for k in p["vigente"]
                   if abs(p["aprendido"][k] - p["vigente"][k]) > 0.25 * max(abs(p["vigente"][k]), 0.1)]
        if cambios:
            s.append(f"Pesos: con {p['n']} días, los pesos aprendidos explican los resultados mejor que los vigentes "
                     f"(razón de verosimilitud {p['razon_verosimilitud']} > {UMBRAL_LR}). Cambios: {'; '.join(cambios)}.")
    elif p: falta.append(f"pesos: {p['n']}/{MIN_DIAS_AJUSTE} días")
    a["falta_muestra"] = falta
    return s

# ---------------------------------------------------------------- recalibración de la base
def recalibrar(hist):
    """base_k = (N_k + 10·prior_k) / (N + 10), con N acumulado desde la semilla; redondeo a 5."""
    n = {"on": 0, "neu": 0, "off": 0}
    for s in hist.get("semilla", []):
        for k in n: n[k] += s.get(k, 0)
    for sem in hist.get("semanas", []):
        for k in n: n[k] += sem.get("recuento", {}).get(k, 0)
    N = sum(n.values())
    pr = dict(zip(("on", "neu", "off"), PRIOR))
    raw = {k: (n[k] + PESO_PRIOR_SESIONES * pr[k] / 100) / (N + PESO_PRIOR_SESIONES) * 100 for k in n}
    on, off = r5(raw["on"]), r5(raw["off"])
    return {"N": N, "recuento": n, "sin_redondeo": {k: round(v, 2) for k, v in raw.items()},
            "base": [on, 100 - on - off, off]}

def toca_recalibrar(hist):
    ult = hist.get("ultima_recalibracion_semanas", 0)
    return len(hist.get("semanas", [])) - ult >= SEMANAS_RECALIBRACION

# ---------------------------------------------------------------- GLI proxy G3
def _d(s): return dt.date.fromisoformat(s[:10])

def _ultimo_le(serie, fecha):
    cand = [(d, v) for d, v in serie if d <= fecha]
    return cand[-1] if cand else (None, None)

def gli(inp, obj_lunes=None):
    """
    inp: {"walcl":[[fecha,millones]], "wtregen":[...], "wlrraol":[...],
          "ecb":[[viernes,millones EUR]], "boj":[[AAAA-MM-01, cientos de millones JPY]],
          "fx":[[fecha, eurusd, eurjpy]]}
    """
    s = {k: sorted((_d(a), float(b)) for a, b in inp[k]) for k in ("walcl", "wtregen", "wlrraol", "ecb", "boj")}
    fx = sorted((_d(a), float(b), float(c)) for a, b, c in inp["fx"])
    tga, rrp = dict(s["wtregen"]), dict(s["wlrraol"])
    filas = []
    for t, walcl in s["walcl"]:
        if t not in tga or t not in rrp:
            continue
        fxr = [x for x in fx if x[0] <= t]
        if not fxr: continue
        _, eurusd, eurjpy = fxr[-1]
        usdjpy = eurjpy / eurusd
        de, ecb = _ultimo_le(s["ecb"], t)
        # BoJ: dato de fin de mes M (fila fechada el día 1 de M) publicado desde el día 5 de M+1
        boj_ok = [(m, v) for m, v in s["boj"]
                  if (dt.date(m.year + (m.month == 12), m.month % 12 + 1, 5)) <= t]
        if ecb is None or not boj_ok: continue
        mb, boj = boj_ok[-1]
        fed = (walcl - tga[t] - rrp[t]) / 1000
        ecb_usd = ecb * eurusd / 1000
        boj_usd = boj * 0.1 / usdjpy
        filas.append({"fecha": t.isoformat(), "walcl": walcl, "tga": tga[t], "rrp": rrp[t],
                      "ecb_eur": ecb, "ecb_fecha": de.isoformat(), "boj_jpy": boj, "boj_mes": mb.isoformat()[:7],
                      "eurusd": eurusd, "usdjpy": round(usdjpy, 4),
                      "fed_neta": round(fed, 1), "bce": round(ecb_usd, 1), "boj": round(boj_usd, 1),
                      "gli": round(fed + ecb_usd + boj_usd, 1)})
    for i, f in enumerate(filas):
        if i >= 4:
            p = filas[i - 4]
            f["d4"] = round(f["gli"] - p["gli"], 1)
            # descomposición
            d_bal_fed = (f["walcl"] - p["walcl"]) / 1000
            d_tga = -(f["tga"] - p["tga"]) / 1000
            d_rrp = -(f["rrp"] - p["rrp"]) / 1000
            ecb_bal = (f["ecb_eur"] - p["ecb_eur"]) * f["eurusd"] / 1000
            ecb_fx = (f["bce"] - p["bce"]) - ecb_bal
            boj_bal = (f["boj_jpy"] - p["boj_jpy"]) * 0.1 / f["usdjpy"]
            boj_fx = (f["boj"] - p["boj"]) - boj_bal
            comp = {"balances": d_bal_fed + ecb_bal + boj_bal, "TGA": d_tga, "ON RRP": d_rrp,
                    "dólar": ecb_fx + boj_fx}
            f["descomposicion"] = {k: round(v, 1) for k, v in comp.items()}
            f["d4_fx_constante"] = round(d_bal_fed + d_tga + d_rrp + ecb_bal + boj_bal, 1)
            sgn = 1 if f["d4"] >= 0 else -1
            f["causa_dominante"] = max(comp, key=lambda k: sgn * comp[k])
            f["salto_boj"] = (f["boj_mes"] != p["boj_mes"]) and abs(boj_bal) > 0.5 * abs(f["d4"]) if f["d4"] else False
        if i >= 8:
            f["A"] = round(f["d4"] - filas[i - 4]["d4"], 1)
            f["estado"] = estado_gli(f["d4"], f["A"], f["gli"])
    res = {"filas": filas}
    con_estado = [f for f in filas if "estado" in f]
    if con_estado:
        res["actual"] = con_estado[-1]
        res["anterior"] = con_estado[-2] if len(con_estado) > 1 else None
    if obj_lunes and con_estado:
        obj_mie = _d(obj_lunes) + dt.timedelta(days=2)
        objetivo = obj_mie - dt.timedelta(weeks=13)
        res["desplazado"] = min(con_estado, key=lambda f: abs((_d(f["fecha"]) - objetivo).days))
        res["desplazado_objetivo"] = objetivo.isoformat()
    return res

def estado_gli(d4, a, nivel):
    umbral = 0.005 * nivel
    dir_ = 0 if abs(d4) < umbral else (1 if d4 > 0 else -1)
    acc = 0 if abs(a) < umbral else (1 if a > 0 else -1)
    if dir_ == 0: return "Plano"
    if dir_ < 0: return "Contracción acelerada" if acc < 0 else "Contracción que se frena"
    return "Expansión acelerada" if acc > 0 else "Expansión que se frena"

# ---------------------------------------------------------------- fechas
def fechas(corte):
    c = _d(corte)
    dias_a_lunes = (7 - c.weekday()) % 7 or 7
    obj_l = c + dt.timedelta(days=dias_a_lunes)
    rev_l = obj_l - dt.timedelta(days=7)
    comp_l = rev_l - dt.timedelta(days=7)
    f = lambda l: [l.isoformat(), (l + dt.timedelta(days=4)).isoformat()]
    def meses_atras(d, m):
        y, mo = d.year, d.month - m
        while mo <= 0: mo += 12; y -= 1
        return dt.date(y, mo, min(d.day, 28)).isoformat()
    out = {"corte": c.isoformat(), "dia_semana": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][c.weekday()],
           "es_fin_de_semana": c.weekday() >= 5, "comp": f(comp_l), "rev": f(rev_l), "obj": f(obj_l),
           "carpeta": f"semanas/{obj_l.isoformat()}/"}
    # marcadores para rellenar los prompts
    out["marcadores"] = {
        "CORTE": out["corte"], "DIA_SEMANA": out["dia_semana"],
        "COMP_LUNES": out["comp"][0], "COMP_VIERNES": out["comp"][1],
        "REV_LUNES": out["rev"][0], "REV_VIERNES": out["rev"][1],
        "OBJ_LUNES": out["obj"][0], "OBJ_VIERNES": out["obj"][1],
        "HACE_20_SEMANAS": (c - dt.timedelta(weeks=20)).isoformat(),
        "HACE_30_SEMANAS": (c - dt.timedelta(weeks=30)).isoformat(),
        "HACE_9_MESES": meses_atras(c, 9), "HACE_18_MESES": meses_atras(c, 18),
    }
    return out

def rellenar(plantilla, valores):
    """Sustituye {CLAVE} por su valor; avisa de marcadores sin rellenar."""
    import re
    txt = plantilla
    for k, v in valores.items():
        txt = txt.replace("{" + k + "}", str(v))
    pendientes = sorted(set(re.findall(r"\{([A-Z][A-Z0-9_]+)\}", txt)))
    return txt, pendientes

# ---------------------------------------------------------------- autotest
CONTROL_NORMAL = {(0,0):(20,50,30),(2,0):(20,45,35),(4,0):(15,45,40),(6,0):(15,40,45),(8,0):(15,30,55),
                  (10,0):(10,30,60),(12,0):(10,30,60),(2,2):(20,45,35),(4,2):(20,40,40),(0,2):(25,45,30),(0,4):(30,45,25)}
CONTROL_TENSION = {(4,0):(15,40,45),(6,0):(15,30,55),(8,0):(10,30,60),(10,0):(10,25,65),(12,0):(10,20,70),
                   (4,1):(20,35,45),(7,1):(15,30,55)}

def selftest():
    ok = True
    for tab, t in ((CONTROL_NORMAL, False), (CONTROL_TENSION, True)):
        for (po, pn), esp in tab.items():
            p = probabilidades(po, pn, t, paso=5)
            got = (p["on"], p["neu"], p["off"])
            if got != esp:
                ok = False
                print("FALLA", "tensión" if t else "normal", (po, pn), got, "esperado", esp)
    # regla de grupo: dos factores de funding 1 + 0.5 -> 1 (tope 1) en normal; 2+1=2.5 en tensión
    f = puntos_fondo([{"id": "sofr_ge_iorb"}, {"id": "fails_subiendo_sobre_media"}], False, False)
    assert f["off"] == 1.0, f
    f = puntos_fondo([{"id": "sofr_ge_iorb"}, {"id": "gc_ge_iorb"}, {"id": "srf_material"}], True, False)
    assert f["off"] == 4.0, f            # 2 + 1 + 1 = 4 (tope de grupo 4)
    f = puntos_fondo([{"id": "move_110_135"}, {"id": "hy_ge_15"}, {"id": "gli_contraccion_acelerada"}], False, False)
    assert f["off"] == 2.0, f            # tope del lado 2
    # recalibración con la semilla del v6 (16/58/26 sobre 19 sesiones) reproduce 20/50/30
    assert recalibrar({"semilla": [{"on": 3, "neu": 11, "off": 5}]})["base"] == [20, 50, 30]
    # fechas
    assert fechas("2026-10-11")["obj"] == ["2026-10-12", "2026-10-16"]
    assert fechas("2026-10-11")["rev"] == ["2026-10-05", "2026-10-09"]
    assert puntos_dia({"dispersion": [{"id": "qra"}, {"id": "sub_10y_30y"}, {"id": "sub_5y_7y"}]}, False)[0] == 3.5
    d = {"fondo": [{"id": "gli_contraccion_acelerada"}], "dias": [{"fecha": "x"}], "gli": {"puntua": {"fuente": "proxy_desplazado"}}}
    assert calcular(d)["fondo"]["off"] == 0.0
    d["gli"]["puntua"]["fuente"] = "captura"
    assert calcular(d)["fondo"]["off"] == 1.0
    d = {"dias": [{"fecha": "x", "direccion": [{"id": "settle_neto_absorcion20"}]}]}
    assert calcular(d)["dias"][0]["dir_off"] == 0.0                      # sin presión ni sensibilidad
    d["sensibilidad_settlement"] = {"activa": True}
    assert calcular(d)["dias"][0]["dir_off"] == 2.0                      # P-004: sensibilidad basta
    assert calcular({"dias": [{"fecha": "x", "direccion": [{"id": "settle_neto_inyeccion20"}]}]})["dias"][0]["dir_on"] == 1.0
    assert clasificar_pista(-0.8, 0.7) == "off" and clasificar_pista(0.2, 0.7) == "neu"
    # P-012: presión sin 2.ª capa → normal; con MOVE 110–135 → tensión
    d = {"modo_tension": {"por_funding": True}, "fondo": [{"id": "sofr_ge_iorb"}], "dias": [{"fecha": "x"}]}
    assert calcular(d)["modo"] == "normal"
    d["fondo"].append({"id": "move_110_135"}); assert calcular(d)["modo"] == "tensión"
    # P-014: probabilidades exactas y sin empate cuando el cálculo inclina
    p = probabilidades(4, 3, False, "alta", (25, 50, 25)); assert p["off"] > p["on"] and p["on"] + p["neu"] + p["off"] == 100
    assert probabilidades(0, 0, False, "alta", (25, 50, 25))["empate_sin_direccion"]
    assert clasificar(-0.6, 6, None) == "off" and clasificar(0.1, 1, 1) == "neu" and clasificar(0.6, None, 1) == "nc"
    # P-021 / P-022: funding solo con catalizador de caja; festivo de bonos = base
    d = {"fondo": [{"id": "sofr_ge_iorb"}, {"id": "hy_ge_15"}], "dias": [{"fecha": "a"}, {"fecha": "b", "direccion": [{"id": "settle_neto_absorcion20"}]}, {"fecha": "c", "bonos_abierto": False}]}
    r = calcular(d)["dias"]; assert r[0]["fondo_off"] == 1.0 and r[1]["fondo_off"] == 2.0 and r[2]["fondo_off"] == 0.0, r
    # días laterales: alcista / bajista / lateral y si se inclinaron a favor o en contra
    t = evaluar_direccion([{"fecha": "z", "resultado": "neu", "spx_pct": -0.4, "prob_emitida": {"on": 34, "neu": 40, "off": 26}},
                           {"fecha": "w", "resultado": "neu", "spx_pct": 0.1, "prob_emitida": {"on": 20, "neu": 40, "off": 40}}], {})
    assert t["dias"][0]["tramo"] == "lateral bajista" and t["dias"][0]["inclinacion"] == "en contra" and t["dias"][1]["tramo"] == "lateral" and "inclinacion" not in t["dias"][1]
    # P-025: causa del día (manda el analista; si no, el funding de ese día) y resumen fuertes/laterales
    assert causa_dia("off", -2)["causa"] == "otra" and causa_dia("off", 2)["causa"] == "liquidez" and causa_dia("on", -3, "politico_macro")["causa"] == "politico_macro"
    t = evaluar_direccion([{"fecha": "a", "resultado": "off", "causa": "sector", "prob_emitida": {"on": 20, "neu": 40, "off": 40}}], {})
    assert t["dias"][0]["con_causa"] is False and t["resumen"]["fuertes"] == {"acertados": 1, "total": 1} and t["resumen"]["aciertos_sin_causa"] == 1
    # P-026: cesta por canales
    c = clasificar_cesta({"rut_pct": -3, "spx_pct": -2, "ndx_pct": -3, "hy_pb": 12, "move_pct": 6, "audjpy_pct": -1})
    assert c["resultado"] == "off" and len(c["canales"]) == 4, c
    c = clasificar_cesta({"ndx_pct": -4, "rut_pct": 0.2, "spx_pct": -0.3, "hy_pb": 0, "move_pct": 0, "audjpy_pct": 0.1})
    assert c["resultado"] == "neu" and c["tramo"] == "lateral", c   # caída solo de un canal: se diluye
    assert clasificar_cesta({"spx_pct": 1})["resultado"] == "nc" and clasificar_cesta({"spx_pct": 1, "move_pct": -5, "audjpy_pct": 1})["resultado"] == "nc"
    # P-020: tabla de dirección y aprendizaje sin datos
    t = evaluar_direccion([{"fecha": "x", "resultado": "off", "prob_emitida": {"on": 20, "neu": 40, "off": 40}},
                           {"fecha": "y", "resultado": "on", "prob_emitida": {"on": 20, "neu": 40, "off": 40}}], {})
    assert t["recuento"]["acierto"] == 1 and t["recuento"]["al_reves"] == 1 and t["tasa_acierto"] == 0.5
    assert aprendizaje({})["senales"] == []
    # P-030: MOVE ≥ 100 si venía de < 100; ≥ 110 si ya estaba en ≥ 100; 2 de 3 en subastas; TIPS exige MOVE y hawkish
    mv = lambda vals: {"move": [{"fecha": str(i), "valor": v} for i, v in enumerate(vals)]}
    assert condicion_move(mv([95, 96, 97, 98, 99, 101]))["ok"] and not condicion_move(mv([102, 99, 99, 99, 99, 105]))["ok"]
    assert condicion_move(mv([102, 99, 99, 99, 99, 110]))["ok"] and not condicion_move(mv([95, 96, 97, 98, 99, 99.5]))["ok"]
    base_d = {"series": mv([95, 96, 97, 98, 99, 101]), "fondo": [{"id": "fedwatch_hawkish"}]}
    r = calcular({**base_d, "dias": [{"fecha": "a", "direccion": [{"id": "subasta_cupon_condiciones_2de3", "previas_flojas": False}]},
                                     {"fecha": "b", "direccion": [{"id": "tips_condiciones"}]}]})["dias"]
    assert r[0]["dir_off"] == 1.0 and r[1]["dir_off"] == 0.5, r
    r = calcular({"series": mv([95, 96, 97, 98, 99, 99]), "fondo": [{"id": "fedwatch_hawkish"}],
                  "dias": [{"fecha": "a", "direccion": [{"id": "subasta_cupon_condiciones_2de3", "previas_flojas": False}]}]})["dias"]
    assert r[0]["dir_off"] == 0.0, r
    print("selftest OK" if ok else "selftest CON FALLOS")
    return ok

# ---------------------------------------------------------------- funding: cuándo y por qué sube (P-001, medición)
# Solo mide y atribuye. No cambia la regla de presión de funding ni puntúa.
FESTIVOS_BONOS = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03",
    "2026-09-07", "2026-10-12", "2026-11-11", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05",
    "2027-09-06", "2027-10-11", "2027-11-11", "2027-11-25", "2027-12-24",
}
UMBRAL_SUBIDA_PB = 2.0

def habil(d):
    return d.weekday() < 5 and d.isoformat() not in FESTIVOS_BONOS

def _sig_habil(d):
    while not habil(d): d += dt.timedelta(days=1)
    return d

def calendario_dia(fecha):
    d = _d(fecha)
    sig = d + dt.timedelta(days=1)
    while not habil(sig): sig += dt.timedelta(days=1)
    ant = d - dt.timedelta(days=1)
    while not habil(ant): ant -= dt.timedelta(days=1)
    quince = _sig_habil(dt.date(d.year, d.month, 15))
    tax = d.month in (1, 4, 6, 9, 12) and d == quince
    return {"fin_mes": sig.month != d.month, "inicio_mes": ant.month != d.month,
            "fin_trimestre": sig.month != d.month and d.month in (3, 6, 9, 12),
            "mediados_mes": d == quince, "tax_date": tax}

def neto_por_dia(d2, semana=None):
    """P-004: flujo neto por día de settlement = Σ NNC de todas las familias − buybacks ejecutados que liquidan.
    Positivo = absorbe cash; negativo = lo inyecta. Si alguna fila del día no tiene NNC, el neto es None (n/c)."""
    dias = {}
    for l in (d2 or {}).get("ledger", []):
        if semana and l.get("semana") != semana: continue
        x = dias.setdefault(l["settlement"], {"fecha": l["settlement"], "semana": l.get("semana"), "nnc_bn": 0.0,
                                              "buyback_bn": 0.0, "completo": True, "familias": []})
        x["familias"].append(l.get("familia"))
        if l.get("nnc_bn") is None: x["completo"] = False
        else: x["nnc_bn"] += l["nnc_bn"]
    for b in (d2 or {}).get("buybacks", []):
        if b.get("estado") == "ejecutado" and b.get("settlement") in dias and b.get("aceptado_bn"):
            dias[b["settlement"]]["buyback_bn"] += b["aceptado_bn"]
    out = []
    for f in sorted(dias):
        x = dias[f]
        x["neto_bn"] = round(x["nnc_bn"] - x["buyback_bn"], 3) if x["completo"] else None
        x["lectura"] = ("n/c" if x["neto_bn"] is None else "absorción neta" if x["neto_bn"] >= UMBRAL_NETO_BN
                        else "inyección neta" if x["neto_bn"] <= -UMBRAL_NETO_BN else "neto pequeño")
        x["nnc_bn"], x["buyback_bn"] = round(x["nnc_bn"], 3), round(x["buyback_bn"], 3)
        out.append(x)
    return out

def dias_funding(d1, d2):
    """Une, por fecha, tipos y SRF (datos1) con settlements y TGA (datos2). Una fila por día."""
    filas = {}
    for t in (d1 or {}).get("tipos", []):
        if t.get("sofr") is None or t.get("iorb") is None: continue
        filas[t["fecha"]] = {"fecha": t["fecha"], "sofr": t["sofr"], "iorb": t["iorb"],
                             "tgcr": t.get("tgcr"), "bgcr": t.get("bgcr"), "sofr_p99": t.get("sofr_p99"),
                             "sofr_vol_bn": t.get("sofr_vol_bn")}
    rev = set()
    if d2 and d2.get("rev"):
        a = _d(d2["rev"][0])
        rev = {(a + dt.timedelta(days=i)).isoformat() for i in range(5)}
    for f in rev:
        if habil(_d(f)):
            filas.setdefault(f, {"fecha": f})
            # el Cash Ledger de REV es completo por contrato: un día sin filas = día sin settlements
            if "ledger" in (d2 or {}): filas[f]["ledger_ok"] = True
    for s in (d1 or {}).get("srf", []):
        if s["fecha"] in filas: filas[s["fecha"]]["srf_bn"] = s.get("aceptado_bn")
    for s in (d1 or {}).get("onrrp", []):
        if s["fecha"] in filas: filas[s["fecha"]]["onrrp_bn"] = s.get("aceptado_bn")
    for t in (d2 or {}).get("tga", []):
        filas.setdefault(t["fecha"], {"fecha": t["fecha"]})["tga_cierre_bn"] = t.get("cierre_bn")
    for l in (d2 or {}).get("ledger", []):
        if l.get("semana") != "REV": continue
        f = filas.setdefault(l["settlement"], {"fecha": l["settlement"]})
        f["ledger_ok"] = True
        fam = l.get("familia", "")
        if fam in ("Bills", "CMB"):
            if l.get("nnc_bn") is not None: f["bills_nnc_bn"] = f.get("bills_nnc_bn", 0) + l["nnc_bn"]
            f["bills_gross_bn"] = f.get("bills_gross_bn", 0) + (l.get("gross_bn") or 0)
        else:
            if l.get("nnc_bn") is not None: f["cupones_nnc_bn"] = f.get("cupones_nnc_bn", 0) + l["nnc_bn"]
            f["cupones_gross_bn"] = f.get("cupones_gross_bn", 0) + (l.get("gross_bn") or 0)
            f["gross_10y_mas_bn"] = f.get("gross_10y_mas_bn", 0) + (l.get("gross_10y_mas_bn") or 0)
            f["tenores"] = sorted(set(f.get("tenores", [])) | {f"{fam}:{x}" if fam not in ("Cupones",) else x for x in l.get("securities", [])})
    for b in (d2 or {}).get("buybacks", []):
        if b.get("estado") == "ejecutado" and b.get("settlement") in filas and b.get("aceptado_bn"):
            f = filas[b["settlement"]]; f["buyback_bn"] = f.get("buyback_bn", 0) + b["aceptado_bn"]
    for f in filas.values():
        f.update(calendario_dia(f["fecha"]))
        if f["fecha"] in rev: f["semana_rev"] = True
        if f.get("ledger_ok"):
            # P-004: flujo NETO del día = NNC de todas las familias − buybacks que liquidan (positivo = absorbe cash)
            f["nnc_neto_bn"] = _neto(f)
    return filas

def fusionar_funding(previos, nuevos):
    """Upsert: completa campos que faltaban (p. ej. el SOFR del viernes que llega T+1 la semana siguiente)."""
    out = {f["fecha"]: dict(f) for f in previos}
    for k, f in nuevos.items():
        if k not in out: out[k] = dict(f); continue
        for c, v in f.items():
            if v is not None and (out[k].get(c) is None or c in ("ledger_ok", "semana_rev", "nnc_neto_bn")):
                out[k][c] = v
    return [out[k] for k in sorted(out)]

def _neto(f):
    """Flujo neto del día (bn): NNC de bills/CMB + NNC del resto − buybacks. None si alguna familia que liquida no tiene NNC."""
    if (f.get("bills_gross_bn") and f.get("bills_nnc_bn") is None) or (f.get("cupones_gross_bn") and f.get("cupones_nnc_bn") is None):
        return None
    return round((f.get("bills_nnc_bn") or 0) + (f.get("cupones_nnc_bn") or 0) - (f.get("buyback_bn") or 0), 3)

def _derivados(serie):
    """Añade SOFR−IORB, GC−IORB, sus cambios frente a la sesión anterior publicada, ΔTGA y la marca de subida."""
    prev = prev_tga = None
    for f in serie:
        if f.get("ledger_ok") and f.get("nnc_neto_bn") is None:
            f["nnc_neto_bn"] = _neto(f)
        if f.get("sofr") is not None and f.get("iorb") is not None:
            f["sofr_iorb_pb"] = round((f["sofr"] - f["iorb"]) * 100, 1)
            if f.get("tgcr") is not None: f["tgcr_iorb_pb"] = round((f["tgcr"] - f["iorb"]) * 100, 1)
            if prev is not None:
                f["d_pb"] = round(f["sofr_iorb_pb"] - prev["sofr_iorb_pb"], 1)
                if "tgcr_iorb_pb" in f and "tgcr_iorb_pb" in prev:
                    f["d_tgcr_pb"] = round(f["tgcr_iorb_pb"] - prev["tgcr_iorb_pb"], 1)
                f["subida"] = f["d_pb"] >= UMBRAL_SUBIDA_PB or (prev["sofr_iorb_pb"] < 0 <= f["sofr_iorb_pb"])
            prev = f
        if f.get("tga_cierre_bn") is not None:
            if prev_tga is not None and (_d(f["fecha"]) - _d(prev_tga["fecha"])).days <= 4:
                f["dtga_bn"] = round(f["tga_cierre_bn"] - prev_tga["tga_cierre_bn"], 1)
            prev_tga = f
    return serie

def _causas_dia(f):
    c = []
    if (f.get("cupones_nnc_bn") or 0) >= 10:
        c.append(f'settlement cupones {", ".join(f.get("tenores", []))} NNC +{f["cupones_nnc_bn"]:.1f} bn')
    elif f.get("cupones_gross_bn"):
        c.append(f'settlement cupones {", ".join(f.get("tenores", []))} (NNC {f.get("cupones_nnc_bn", "n/c")})')
    if (f.get("bills_nnc_bn") or 0) >= 20: c.append(f'settlement bills NNC +{f["bills_nnc_bn"]:.1f} bn')
    if f.get("nnc_neto_bn") is not None and abs(f["nnc_neto_bn"]) >= UMBRAL_NETO_BN:
        c.append(("absorción" if f["nnc_neto_bn"] > 0 else "inyección") + f' neta del día {f["nnc_neto_bn"]:+.1f} bn')
    if (f.get("dtga_bn") or 0) >= 20: c.append(f'TGA +{f["dtga_bn"]:.1f} bn')
    for k, t in (("fin_mes", "fin de mes"), ("inicio_mes", "inicio de mes"), ("fin_trimestre", "fin de trimestre"),
                 ("tax_date", "tax date"), ("mediados_mes", "mediados de mes")):
        if f.get(k): c.append(t)
    if (f.get("srf_bn") or 0) >= 1: c.append(f'SRF {f["srf_bn"]:.1f} bn')
    return c or ["ninguna causa de calendario o Treasury identificada"]

RASGOS = {
    "cupones_nnc_ge10": ("Settlement de cupones con NNC ≥ 10 bn", lambda f: (f.get("cupones_nnc_bn") or 0) >= 10, lambda f: f.get("ledger_ok")),
    "bills_nnc_ge20":   ("Settlement de bills con NNC ≥ 20 bn",   lambda f: (f.get("bills_nnc_bn") or 0) >= 20,   lambda f: f.get("ledger_ok")),
    "neto_absorcion20": ("Absorción neta del día ≥ +20 bn",      lambda f: (f.get("nnc_neto_bn") or 0) >= UMBRAL_NETO_BN,  lambda f: f.get("ledger_ok")),
    "neto_inyeccion20": ("Inyección neta del día ≥ 20 bn",       lambda f: (f.get("nnc_neto_bn") or 0) <= -UMBRAL_NETO_BN, lambda f: f.get("ledger_ok")),
    "dtga_ge20":        ("TGA sube ≥ 20 bn en el día",            lambda f: (f.get("dtga_bn") or 0) >= 20,        lambda f: f.get("dtga_bn") is not None),
    "fin_mes":          ("Último día hábil del mes",              lambda f: f.get("fin_mes"),                     lambda f: True),
    "inicio_mes":       ("Primer día hábil del mes",              lambda f: f.get("inicio_mes"),                  lambda f: True),
    "mediados_mes":     ("Día 15 (o siguiente hábil)",            lambda f: f.get("mediados_mes"),                lambda f: True),
    "tax_date":         ("Tax date corporativa/estimada",         lambda f: f.get("tax_date"),                    lambda f: True),
}

def _pearson(x, y):
    n = len(x)
    if n < 8: return None
    mx, my = sum(x) / n, sum(y) / n
    sx = sum((a - mx) ** 2 for a in x) ** .5; sy = sum((b - my) ** 2 for b in y) ** .5
    return round(sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy), 2) if sx and sy else None

def causas_funding(serie):
    """Estadística acumulada: Δ(SOFR−IORB) medio con y sin cada rasgo, y qué parte de las subidas lo tenía."""
    obs = [f for f in serie if f.get("d_pb") is not None]
    subidas = [f for f in obs if f.get("subida")]
    media = lambda v: round(sum(v) / len(v), 2) if v else None
    tabla = []
    for k, (txt, tiene, medible) in RASGOS.items():
        m = [f for f in obs if medible(f)]
        con = [f["d_pb"] for f in m if tiene(f)]; sin = [f["d_pb"] for f in m if not tiene(f)]
        sub_m = [f for f in subidas if medible(f)]
        tabla.append({"rasgo": k, "descripcion": txt, "n_con": len(con), "n_sin": len(sin),
                      "d_medio_con": media(con), "d_medio_sin": media(sin),
                      "diferencia": round(media(con) - media(sin), 2) if con and sin else None,
                      "pct_subidas_con": round(100 * sum(1 for f in sub_m if tiene(f)) / len(sub_m)) if sub_m else None,
                      "muestra": "suficiente" if len(con) >= 8 else "pequeña"})
    por_tenor = defaultdict(list)
    for f in obs:
        for t in f.get("tenores", []): por_tenor[t].append(f["d_pb"])
    tramos = {"sin settlement de cupones": [], "NNC < 10": [], "NNC 10–30": [], "NNC > 30": []}
    for f in obs:
        if not f.get("ledger_ok"): continue
        n = f.get("cupones_nnc_bn")
        k = "sin settlement de cupones" if not f.get("cupones_gross_bn") else "NNC < 10" if (n or 0) < 10 else "NNC 10–30" if n <= 30 else "NNC > 30"
        tramos[k].append(f["d_pb"])
    cont = [f for f in obs if f.get("ledger_ok")]
    corr = {
        "cupones_nnc_bn": _pearson([f.get("cupones_nnc_bn") or 0 for f in cont], [f["d_pb"] for f in cont]),
        "bills_nnc_bn": _pearson([f.get("bills_nnc_bn") or 0 for f in cont], [f["d_pb"] for f in cont]),
        "nnc_neto_bn": _pearson([f.get("nnc_neto_bn") or 0 for f in cont], [f["d_pb"] for f in cont]),
        "dtga_bn": _pearson(*zip(*[(f["dtga_bn"], f["d_pb"]) for f in obs if f.get("dtga_bn") is not None])) if sum(1 for f in obs if f.get("dtga_bn") is not None) >= 8 else None,
    }
    return {"sesiones": len(obs), "subidas": len(subidas), "umbral_pb": UMBRAL_SUBIDA_PB,
            "desde": obs[0]["fecha"] if obs else None, "hasta": obs[-1]["fecha"] if obs else None,
            "rasgos": tabla,
            "por_tenor": {t: {"n": len(v), "d_medio": media(v)} for t, v in sorted(por_tenor.items())},
            "por_tramo_nnc_cupones": {k: {"n": len(v), "d_medio": media(v)} for k, v in tramos.items()},
            "correlaciones": corr,
            "nota": "Medición descriptiva: coincidencia en el día, no causalidad probada. Con menos de 8 casos por rasgo la muestra es pequeña."}

def episodios(carpeta, hist):
    c = carpeta if carpeta.endswith("/") else carpeta + "/"
    import os
    d1 = _load(c + "datos1.json") if os.path.exists(c + "datos1.json") else {}
    d2 = _load(c + "datos2.json") if os.path.exists(c + "datos2.json") else {}
    serie = _derivados(fusionar_funding(hist.get("funding_dias", []), dias_funding(d1, d2)))
    semana = [dict(f, causas=_causas_dia(f)) for f in serie if f.get("semana_rev") and f["fecha"] in
              {(_d(d2["rev"][0]) + dt.timedelta(days=i)).isoformat() for i in range(5)}] if d2.get("rev") else []
    return {"semana": semana, "acumulado": causas_funding(serie),
            "sensibilidad_settlement": sensibilidad_settlement(serie, d2.get("rev", [None])[0] if d2 else None),
            "capa_cash": capa_cash(semana)}

UMBRAL_LEVE_PB = 1.0   # P-004: "si subió" aunque siga bajo IORB; ≥1 pb es leve, ≥2 pb es subida

def _sube(f, u=UMBRAL_LEVE_PB):
    return max(f.get("d_pb") or 0, f.get("d_tgcr_pb") or 0) >= u

def _reaccion(dias):
    """Activa si algún día de absorción neta subió ≥ 2 pb, o al menos dos subieron ≥ 1 pb."""
    fuertes = [f for f in dias if _sube(f, UMBRAL_SUBIDA_PB)]
    leves = [f for f in dias if _sube(f)]
    return bool(fuertes) or len(leves) >= 2, fuertes, leves

def sensibilidad_settlement(serie, rev_lunes, sesiones=10):
    """P-004: ¿los últimos settlements con absorción neta subieron SOFR−IORB o TGCR−IORB (≥ +2 pb), aunque fuera por debajo de IORB?
    Ventana: las últimas `sesiones` con datos hasta el viernes de REV."""
    if not rev_lunes: return {"activa": False, "evidencia": [], "nota": "sin REV"}
    fin = (_d(rev_lunes) + dt.timedelta(days=4)).isoformat()
    ult = [f for f in serie if f["fecha"] <= fin and f.get("d_pb") is not None][-sesiones:]
    absor = [f for f in ult if (f.get("nnc_neto_bn") or 0) >= UMBRAL_NETO_BN]
    activa, fuertes, leves = _reaccion(absor)
    ev = [{"fecha": f["fecha"], "nnc_neto_bn": f["nnc_neto_bn"], "d_sofr_pb": f.get("d_pb"), "d_tgcr_pb": f.get("d_tgcr_pb"),
           "sofr_iorb_pb": f.get("sofr_iorb_pb"),
           "subio": "≥2 pb" if f in fuertes else "≥1 pb" if f in leves else "no"} for f in absor]
    return {"activa": activa, "evidencia": ev,
            "nota": f"{len(absor)} días de absorción neta ≥ {UMBRAL_NETO_BN:.0f} bn en las últimas {len(ult)} sesiones: "
                    f"{len(fuertes)} con subida ≥ 2 pb y {len(leves)} con subida ≥ 1 pb de SOFR/TGCR − IORB (cuente o no por encima de IORB). "
                    f"Regla: activa si alguno sube ≥ 2 pb o al menos dos suben ≥ 1 pb."}

def capa_cash(semana):
    """P-004: señal objetiva de la capa Cash/settlements con los días de REV.
    CONFIRMA ESTRÉS: en los días de absorción neta ≥ 20 bn, SOFR/TGCR − IORB sube ≥ 2 pb en alguno, o ≥ 1 pb en dos
    (aunque siga bajo IORB).
    CONTRADICE ESTRÉS: hubo absorción neta ≥ 20 bn sin subidas, o inyección neta ≥ 20 bn sin subidas, y ningún día confirma.
    MIXTA: hubo subidas pero sin absorción neta grande ese día. NO CONFIRMADA: sin ledger o sin tipos."""
    dias = [f for f in semana if f.get("ledger_ok") and f.get("d_pb") is not None]
    if not dias: return {"senal": "NO CONFIRMADA", "motivo": "sin ledger de REV o sin tipos publicados"}
    absor = [f for f in dias if (f.get("nnc_neto_bn") or 0) >= UMBRAL_NETO_BN]
    activa, fuertes, leves = _reaccion(absor)
    if activa: return {"senal": "CONFIRMA ESTRÉS", "dias": [f["fecha"] for f in (fuertes or leves)]}
    grandes = [f["fecha"] for f in dias if abs(f.get("nnc_neto_bn") or 0) >= UMBRAL_NETO_BN]
    if grandes and not any(_sube(f, UMBRAL_SUBIDA_PB) for f in dias): return {"senal": "CONTRADICE ESTRÉS", "dias": grandes}
    if any(_sube(f, UMBRAL_SUBIDA_PB) for f in dias):
        return {"senal": "MIXTA", "dias": [f["fecha"] for f in dias if _sube(f, UMBRAL_SUBIDA_PB)]}
    return {"senal": "CONTRADICE ESTRÉS" if grandes else "MIXTA", "dias": grandes}

# ---------------------------------------------------------------- resumen de datos1 para el prompt de la Parte 2
def resumen1(d1):
    """Texto fijo con las cifras diarias de datos1.json que la Parte 2 recibe junto al puente."""
    L = [f'Datos Parte 1 · corte {d1.get("corte")} · REV {d1.get("rev")} · estado funding: {d1.get("estado_funding")}']
    L.append("Tipos (fecha: SOFR / IORB / SOFR−IORB pb / TGCR / BGCR / EFFR):")
    for t in d1.get("tipos", []):
        try: sp = f'{(t["sofr"] - t["iorb"]) * 100:+.0f}'
        except Exception: sp = "n/d"
        L.append(f'  {t.get("fecha")}: {t.get("sofr")} / {t.get("iorb")} / {sp} / {t.get("tgcr")} / {t.get("bgcr")} / {t.get("effr")}')
    for k, tit in (("onrrp", "ON RRP aceptado (bn)"), ("srf", "SRF aceptado (bn)"), ("reservas", "Reservas (bn)"), ("xeurbi", "XEURBI (pb)")):
        serie = d1.get(k, [])
        if serie:
            campo = "pb" if k == "xeurbi" else ("bn" if k == "reservas" else "aceptado_bn")
            L.append(f'{tit}: ' + " · ".join(f'{x.get("fecha")} {x.get(campo)}' for x in serie))
    pf = d1.get("presion_funding") or {}
    if pf:
        L.append(f'Presión de funding (definición común): confirmada={pf.get("confirmada")} · fecha {pf.get("fecha")} · '
                 f'SOFR≥IORB={pf.get("sofr_ge_iorb")} · GC≥IORB={pf.get("gc_ge_iorb")} · SRF material={pf.get("srf_material")} · '
                 f'sesiones consecutivas={pf.get("sesiones_consecutivas")} · ventana de calendario={pf.get("en_ventana_calendario")}')
    return "\n".join(L)

# ---------------------------------------------------------------- estado de la ejecución (puntos de control y reanudación)
PASOS = (["p1.A", "p1.B", "p1.C", "p1.redactor", "p1.validar",
          "p2.A", "p2.B", "p2.C", "p2.D", "p2.E", "p2.redactor", "p2.validar",
          "p3.A", "p3.B", "p3.C", "p3.D", "p3.E", "p3.F", "p3.redactor", "p3.validar",
          "auditoria", "registro", "final", "simulador", "publicar", "aviso"])
OPCIONALES_MODO_MINIMO = {"p3.E", "auditoria"}   # solo si el usuario lo pide expresamente (`estado minimo`); nunca automático
MAX_INTENTOS = 2
LATIDO_CADUCA_MIN = 90

def _ahora():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)

def estado_init(marc, modo_prueba=False):
    return {"version": 1, "obj_lunes": marc["OBJ_LUNES"], "corte": marc["CORTE"], "marcadores": marc,
            "modo_prueba": bool(modo_prueba), "modo_minimo": False, "estado": "en curso",
            "inicio": _ahora().isoformat(), "ultimo_latido": _ahora().isoformat(), "ejecuciones": 1,
            "pasos": {p: {"estado": "pendiente", "intentos": 0} for p in PASOS}, "incidencias": []}

def estado_siguiente(e):
    """Devuelve el grupo de pasos que toca ahora (los investigadores de una parte van juntos, en paralelo)."""
    if e["estado"] != "en curso": return []
    for p in PASOS:   # estado creado con una versión anterior: los pasos nuevos se añaden como pendientes
        e["pasos"].setdefault(p, {"estado": "pendiente", "intentos": 0})
    pend = [p for p in PASOS if e["pasos"][p]["estado"] in ("pendiente", "fallo")]
    if e.get("modo_minimo"):
        for p in list(pend):
            if p in OPCIONALES_MODO_MINIMO:
                e["pasos"][p]["estado"] = "omitido"; pend.remove(p)
    if not pend: return []
    primero = pend[0]
    parte = primero.split(".")[0]
    if parte in ("p1", "p2", "p3") and len(primero.split(".")[1]) == 1:
        return [p for p in pend if p.startswith(parte + ".") and len(p.split(".")[1]) == 1]
    return [primero]

def estado_marcar(e, paso, resultado, nota=""):
    s = e["pasos"][paso]
    if resultado == "hecho":
        s["estado"] = "hecho"
    else:
        s["intentos"] += 1
        s["estado"] = "fallo" if s["intentos"] < MAX_INTENTOS else "omitido"
        e["incidencias"].append(f"{paso}: {nota} (intento {s['intentos']})")
    if nota and resultado == "hecho": s["nota"] = nota
    e["ultimo_latido"] = _ahora().isoformat()
    if all(v["estado"] in ("hecho", "omitido") for v in e["pasos"].values()):
        e["estado"] = "completo"
    return e

def estado_candado(e):
    """'libre' si se puede trabajar; 'ocupado' si otra ejecución dio señales de vida hace menos de LATIDO_CADUCA_MIN."""
    if e["estado"] != "en curso": return e["estado"]
    ult = dt.datetime.fromisoformat(e["ultimo_latido"])
    return "ocupado" if (_ahora() - ult).total_seconds() < LATIDO_CADUCA_MIN * 60 else "libre"

def estado_reanudar(e, ahora_madrid=None):
    """Al reanudar: suma una ejecución y decide si toca modo mínimo o abandono según la hora (Europe/Madrid)."""
    e["ejecuciones"] = e.get("ejecuciones", 1) + 1
    e["ultimo_latido"] = _ahora().isoformat()
    obj = _d(e["obj_lunes"])
    h = ahora_madrid or dt.datetime.now()
    if isinstance(h, str): h = dt.datetime.fromisoformat(h)
    h = h.replace(tzinfo=None)
    # Decisión del usuario (30-oct-2026): calidad completa antes que rapidez. Nunca hay modo mínimo automático:
    # se completa todo aunque tarde. Si se pasa de la apertura de EE. UU. del lunes, se marca "tarde" y se sigue.
    # Solo se abandona si el martes de OBJ termina sin informe (para entonces ya no sirve para la semana).
    lunes_15 = dt.datetime(obj.year, obj.month, obj.day, 15, 0)
    fin_martes = dt.datetime(obj.year, obj.month, obj.day, 23, 59) + dt.timedelta(days=1)
    if h >= fin_martes:
        e["estado"] = "abandonado"
        e["incidencias"].append("abandonado: terminó el martes de OBJ sin completar el informe")
    elif h >= lunes_15 and not e.get("tarde"):
        e["tarde"] = True
        e["incidencias"].append("tarde: el informe sigue completo, pero se entrega después de la apertura del lunes")
    return e

def estado_resumen(e):
    c = defaultdict(int)
    for v in e["pasos"].values(): c[v["estado"]] += 1
    return {"estado": e["estado"], "obj": e["obj_lunes"], "ejecuciones": e.get("ejecuciones"),
            "modo_minimo": e.get("modo_minimo"), "cuenta": dict(c), "siguiente": estado_siguiente(json.loads(json.dumps(e))),
            "incidencias": e["incidencias"][-5:]}

# ---------------------------------------------------------------- validación de cada parte
CAMPOS_PUENTE = {
    1: ["BLOQUE PUENTE PARTE 1", "Semanas:", "Estado funding", "SOFR - IORB", "ON RRP", "SRF", "Reservas", "Presión de funding"],
    2: ["BLOQUE PUENTE PARTE 2", "Semanas:", "Calendario OBJ día a día", "Resultados de cupón de REV", "Previas flojas", "TGA y fiscal", "Flujo neto REV"],
    3: ["BLOQUE PUENTE PARTE 3", "Corte:", "Probabilidades diarias de OBJ", "Estado final preliminar", "Funding reconciliado",
        "Sensibilidad a settlements", "Datos de OBJ frente a consenso", "Pistas:"],
}

def validar(parte, carpeta, marc):
    import os, re
    err, av = [], []
    c = carpeta if carpeta.endswith("/") else carpeta + "/"
    for nombre in (f"parte{parte}.md", f"puente{parte}.txt", f"datos{parte}.json"):
        if not os.path.exists(c + nombre) or os.path.getsize(c + nombre) < 200:
            err.append(f"falta o vacío: {nombre}")
    if err: return {"ok": False, "errores": err, "avisos": av}
    puente = open(c + f"puente{parte}.txt", encoding="utf-8").read()
    for campo in CAMPOS_PUENTE[parte]:
        if campo not in puente: err.append(f"puente{parte}: falta '{campo}'")
    for k in ("REV_LUNES", "OBJ_LUNES"):
        if marc[k] not in puente: err.append(f"puente{parte}: no aparece {k} = {marc[k]}")
    try:
        d = _load(c + f"datos{parte}.json")
    except Exception as e:
        return {"ok": False, "errores": err + [f"datos{parte}.json no es JSON válido: {e}"], "avisos": av}
    if d.get("rev", [None])[0] != marc["REV_LUNES"] or d.get("obj", [None])[0] != marc["OBJ_LUNES"]:
        err.append(f"datos{parte}.json: semanas rev/obj no coinciden con el orquestador")
    if parte == 1 and not d.get("tipos"): err.append("datos1: sin serie de tipos")
    if parte == 2 and not d.get("calendario_obj"): err.append("datos2: sin calendario_obj")
    if parte == 2:
        calc = {x["fecha"]: x["neto_bn"] for x in neto_por_dia(d)}
        for x in d.get("neto_dia", []):
            m = calc.get(x.get("fecha"))
            if x.get("neto_bn") is None or m is None:
                if (x.get("neto_bn") is None) != (m is None): err.append(f'datos2.neto_dia {x.get("fecha")}: {x.get("neto_bn")} ≠ motor {m}')
            elif abs(x["neto_bn"] - m) > 0.1: err.append(f'datos2.neto_dia {x["fecha"]}: {x["neto_bn"]} ≠ motor {m} (Σ NNC − buybacks)')
        if not d.get("neto_dia"): av.append("datos2: sin neto_dia (P-004); la Parte 3 lo toma del motor")
    if parte == 3:
        res = d.get("resultado")
        if not res: err.append("datos3: falta el bloque 'resultado' del motor (no se ejecutó motor.py prob)")
        else:
            fechas_obj = [(_d(marc["OBJ_LUNES"]) + dt.timedelta(days=i)).isoformat() for i in range(5)]
            if [x["fecha"] for x in res["dias"]] != fechas_obj:
                err.append("datos3.resultado: los días no son los cinco de OBJ")
            # recálculo independiente: el resultado guardado debe coincidir con el motor
            rec = calcular(d)
            for a, b in zip(rec["dias"], res["dias"]):
                if a["prob"] != b["prob"]: err.append(f'{a["fecha"]}: resultado guardado {b["prob"]} ≠ recálculo {a["prob"]}')
            # las cifras del puente deben coincidir con el motor
            for x in res["dias"]:
                p = x["prob"]
                patron = rf'{x["fecha"]}[^\n]*?{p["on"]}\s*/\s*{p["neu"]}\s*/\s*{p["off"]}'
                if not re.search(patron, puente):
                    err.append(f'puente3: la fila de {x["fecha"]} no muestra {p["on"]}/{p["neu"]}/{p["off"]}')
            for x in res.get("avisos", []):
                (err if "desconocid" in x else av).append(x)   # un id fuera del catálogo no puntúa: se corrige
            # P-004: sensibilidad y capa cash deben ser las que calculó el motor (funding_causas.json)
            if os.path.exists(c + "funding_causas.json"):
                fc = _load(c + "funding_causas.json")
                s_m = bool((fc.get("sensibilidad_settlement") or {}).get("activa"))
                s_d = bool((d.get("sensibilidad_settlement") or {}).get("activa"))
                if s_m != s_d: err.append(f"datos3.sensibilidad_settlement.activa = {s_d} ≠ motor {s_m}")
                cc = (fc.get("capa_cash") or {}).get("senal")
                capa = next((k for k in d.get("capas", []) if k.get("capa", "").lower().startswith("cash")), None)
                if cc and capa and capa.get("senal") != cc:
                    err.append(f'capa Cash/settlements = {capa.get("senal")} ≠ motor {cc}')
    return {"ok": not err, "errores": err, "avisos": av}

def validar_final(carpeta, marc):
    """Documento final: existe, tiene las secciones fijas y copia las probabilidades del motor sin cambios."""
    import os, re
    c = carpeta if carpeta.endswith("/") else carpeta + "/"
    if not os.path.exists(c + "informe_final.md") or os.path.getsize(c + "informe_final.md") < 1500:
        return {"ok": False, "errores": ["falta o vacío: informe_final.md"], "avisos": []}
    t = open(c + "informe_final.md", encoding="utf-8").read()
    err = [f"falta la sección '{x}'" for x in ("## Conclusión", "## Mapa de la semana", "## Funding", "## Treasury plumbing",
           "## Confirmación", "## Expectativas de tipos", "## Trading bias", "## Qué cambiaría la tesis",
           "## Evaluación de la semana anterior", "## Limitaciones", "## Fuentes") if x not in t]
    res = _load(c + "datos3.json").get("resultado", {})
    for x in res.get("dias", []):
        p = x["prob"]
        if not re.search(rf'{x["fecha"]}[^\n]*?{p["on"]}\s*/\s*{p["neu"]}\s*/\s*{p["off"]}', t):
            err.append(f'mapa de la semana: la fila de {x["fecha"]} no muestra {p["on"]} / {p["neu"]} / {p["off"]}')
    if marc["OBJ_LUNES"] not in t: err.append("el título no lleva el lunes de OBJ")
    return {"ok": not err, "errores": err, "avisos": [], "palabras": len(t.split())}

# ---------------------------------------------------------------- historial semanal
def registrar(hist, carpeta, evaluacion=None):
    c = carpeta if carpeta.endswith("/") else carpeta + "/"
    d3 = _load(c + "datos3.json")
    res = d3["resultado"]
    sem = {"obj": d3["obj"], "rev": d3["rev"], "corte": d3["corte"], "prompt": d3.get("prompt"),
           "base_usada": res["base"], "modo": res["modo"],
           "regimen": d3.get("regimen", {}).get("estado"),
           "prob_emitidas": [{"fecha": x["fecha"], **x["prob"]} for x in res["dias"]]}
    if evaluacion:
        sem["evaluacion_rev"] = {k: evaluacion[k] for k in ("recuento", "brier_emitido", "brier_base", "brier_304030", "dias_puntuados")}
        sem["recuento"] = {k: evaluacion["recuento"][k] for k in ("on", "neu", "off")}
        sem["resultados_rev"] = [{"fecha": x["fecha"], "resultado": x["resultado"]} for x in evaluacion["dias"]]
        if evaluacion.get("pistas"):
            sem["pistas_rev"] = {k: {**{c: v[c] for c in ("recuento", "brier_emitido", "brier_base", "dias_puntuados")},
                                     "dias": [{"fecha": x["fecha"], "valor": x["valor"], "resultado": x["resultado"]} for x in v["dias"]]}
                                 for k, v in evaluacion["pistas"].items()}
        if evaluacion.get("direccion"):
            sem["direccion_rev"] = evaluacion["direccion"]
    sem["factores_dias"] = _registro_factores(d3, res)
    rez = completar_rezagados(hist, d3.get("evaluacion_rev", {}).get("rezagados", []))
    retrasos = {}
    for n in (1, 2, 3):
        try:
            for f in _load(c + f"datos{n}.json").get("fuentes", []):
                if f.get("retraso_dias") is not None: retrasos[f["fuente"]] = f["retraso_dias"]
        except Exception:
            pass
    sem["retrasos_fuentes"] = retrasos
    import os
    d1 = _load(c + "datos1.json") if os.path.exists(c + "datos1.json") else {}
    d2 = _load(c + "datos2.json") if os.path.exists(c + "datos2.json") else {}
    hist["funding_dias"] = [{k: v for k, v in f.items() if k not in ("sofr_iorb_pb", "tgcr_iorb_pb", "d_pb", "d_tgcr_pb", "subida", "dtga_bn")}
                            for f in fusionar_funding(hist.get("funding_dias", []), dias_funding(d1, d2))]
    hist.setdefault("semanas", [])
    hist["semanas"] = [s for s in hist["semanas"] if s["obj"] != sem["obj"]] + [sem]
    out = {"semana_registrada": sem["obj"][0], "recalibrada": False, "rezagados_completados": rez}
    if toca_recalibrar(hist):
        r = recalibrar(hist)
        out.update({"recalibrada": True, "base_anterior": hist.get("base_vigente"), "base_nueva": r["base"], "detalle": r})
        hist["base_vigente"] = r["base"]
        hist["fecha_recalibracion"] = d3["corte"]
        hist["ultima_recalibracion_semanas"] = len(hist["semanas"])
    ap = aprendizaje(hist)                                   # P-020: tabla de aciertos y aprendizaje acumulado
    _save(c + "aprendizaje.json", ap)
    out["aprendizaje"] = {"direccion": ap["direccion"], "senales": ap["senales"], "falta_muestra": ap["falta_muestra"]}
    return hist, out

def completar_rezagados(hist, rezagados):
    """Pistas con retraso (p. ej. Russell 2000 publica con varios días de retraso): la semana siguiente trae
    `evaluacion_rev.rezagados = [{fecha, rut_pct|ndx_pct|audjpy_pct}]` de días ya evaluados como "nc";
    se completan en la semana del historial que evaluó ese día, con la probabilidad emitida para ese día."""
    hechos = []
    emit = {p["fecha"]: p for s in hist.get("semanas", []) for p in s.get("prob_emitidas", [])}
    for r in rezagados or []:
        for s in hist.get("semanas", []):
            for k, v in s.get("pistas_rev", {}).items():
                campo, u = PISTAS[k][1], PISTAS[k][2]
                for d in v.get("dias", []):
                    if d["fecha"] == r.get("fecha") and d["resultado"] == "nc" and r.get(campo) is not None:
                        d["valor"], d["resultado"] = r[campo], clasificar_pista(r[campo], u)
                        hechos.append(f'{k} {d["fecha"]}')
                if hechos:
                    v["recuento"] = {c: sum(1 for d in v["dias"] if d["resultado"] == c) for c in ("on", "neu", "off", "nc")}
                    b = [brier({c: emit[d["fecha"]][c] for c in ("on", "neu", "off")}, d["resultado"])
                         for d in v["dias"] if d["resultado"] != "nc" and d["fecha"] in emit]
                    if b: v["brier_emitido"], v["dias_puntuados"] = round(sum(b) / len(b), 4), len(b)
    return hechos

def propuestas_automaticas(hist):
    """Borradores de cambio basados en evidencia. Nunca se aplican solos."""
    props = []
    ev = [s["evaluacion_rev"] for s in hist.get("semanas", []) if s.get("evaluacion_rev", {}).get("brier_emitido") is not None]
    ult = ev[-6:]
    peor = sum(1 for e in ult if e["brier_emitido"] > e["brier_base"])
    if len(ult) >= 4 and peor >= 4:
        props.append(f"En {peor} de las últimas {len(ult)} semanas las probabilidades emitidas puntuaron peor (Brier) que la base sin ajustes. Revisar qué factores suman puntos con más frecuencia en semanas falladas.")
    from statistics import median
    por_fuente = defaultdict(list)
    for s in hist.get("semanas", [])[-4:]:
        for f, r in s.get("retrasos_fuentes", {}).items(): por_fuente[f].append(r)
    for f, v in por_fuente.items():
        if len(v) >= 3 and median(v) >= 3:
            props.append(f"La fuente '{f}' acumula un retraso mediano de {median(v)} días hábiles en {len(v)} semanas: valorar ampliar su umbral de frescura o cambiar de fuente.")
    props += aprendizaje(hist)["senales"]                    # P-020: solo con muestra suficiente
    return props

# ---------------------------------------------------------------- CLI
def _load(p):
    with open(p, encoding="utf-8") as fh: return json.load(fh)

def _save(p, obj):
    with open(p, "w", encoding="utf-8") as fh: json.dump(obj, fh, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        sys.exit(0 if selftest() else 1)
    elif cmd == "prob":
        d3 = _load(sys.argv[2])
        limpio, fuera = filtrar_gli(d3)
        if fuera:
            d3["fondo"], d3["fondo_descartado"] = limpio, fuera
        res = calcular(d3)
        res["si_modo_tension"] = sensibilidad_tension(d3)
        res["reglas_actualizacion"] = reglas_actualizacion(d3)
        d3["resultado"] = res
        _save(sys.argv[2], d3)
        for d in res["dias"]:
            p = d["prob"]
            print(f'{d["fecha"]} {d.get("dia","")}: {p["on"]}/{p["neu"]}/{p["off"]}  pts off {d["pts_off"]} on {d["pts_on"]}  {d["modo"]} {d["confianza"]}')
        for a in res["avisos"]: print("AVISO:", a)
    elif cmd == "gli":
        r = gli(_load(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None)
        out = sys.argv[4] if len(sys.argv) > 4 else "gli_resultado.json"
        _save(out, r)
        for f in r["filas"][-10:]:
            print(f["fecha"], f["gli"], f.get("d4"), f.get("A"), f.get("estado"), f.get("causa_dominante"))
        if "desplazado" in r: print("PUNTÚA (desplazado 13 semanas):", r["desplazado"]["fecha"], r["desplazado"].get("estado"))
    elif cmd == "evaluar":
        print(json.dumps(evaluar(_load(sys.argv[2]), _load(sys.argv[3])), ensure_ascii=False, indent=2))
    elif cmd == "aprender":   # aprender <historial.json> [salida.json]
        a = aprendizaje(_load(sys.argv[2]))
        if len(sys.argv) > 3: _save(sys.argv[3], a)
        print(json.dumps({k: a[k] for k in ("dias_puntuados", "direccion", "calibracion", "brier", "pesos", "senales", "falta_muestra")}, ensure_ascii=False, indent=2))
    elif cmd == "base":
        h = _load(sys.argv[2])
        print(json.dumps({"toca": toca_recalibrar(h), **recalibrar(h)}, ensure_ascii=False, indent=2))
    elif cmd == "fechas":
        print(json.dumps(fechas(sys.argv[2]), ensure_ascii=False, indent=2))
    elif cmd == "neto":  # neto <datos2.json> [REV|OBJ]
        for x in neto_por_dia(_load(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else None):
            neto = "n/c (falta el NNC de alguna familia)" if x["neto_bn"] is None else f'{x["neto_bn"]:+.3f} bn'
            print(f'{x["fecha"]} {x["semana"]}: NNC {x["nnc_bn"]:+.3f} − buybacks {x["buyback_bn"]:.3f} = neto {neto} · {x["lectura"]} · {", ".join(map(str, x["familias"]))}')
    elif cmd == "episodios":  # episodios <carpeta> <historial.json> [salida.json]
        r = episodios(sys.argv[2], _load(sys.argv[3]))
        if len(sys.argv) > 4: _save(sys.argv[4], r)
        for f in r["semana"]:
            print(f'{f["fecha"]}: SOFR-IORB {f.get("sofr_iorb_pb")} pb (Δ {f.get("d_pb")}){" SUBIDA" if f.get("subida") else ""} · {"; ".join(f["causas"])}')
        a = r["acumulado"]
        print(f'acumulado: {a["sesiones"]} sesiones, {a["subidas"]} subidas ({a["desde"]} → {a["hasta"]})')
        for t in a["rasgos"]:
            print(f'  {t["descripcion"]}: Δ con {t["d_medio_con"]} (n={t["n_con"]}) vs sin {t["d_medio_sin"]} · {t["pct_subidas_con"]} % de subidas · muestra {t["muestra"]}')
    elif cmd == "resumen1":   # resumen1 <datos1.json>  -> texto para {DATOS1_RESUMEN}
        print(resumen1(_load(sys.argv[2])))
    elif cmd == "estado":     # estado <accion> <estado.json> [args]
        acc, ruta = sys.argv[2], sys.argv[3]
        if acc == "init":       # estado init <estado.json> <marcadores.json> [prueba]
            e = estado_init(_load(sys.argv[4]), len(sys.argv) > 5 and sys.argv[5] in ("si", "sí", "true", "1"))
        else:
            e = _load(ruta)
        if acc == "siguiente":
            print(json.dumps(estado_siguiente(e))); _save(ruta, e); sys.exit(0)
        elif acc == "hecho":    # estado hecho <estado.json> <paso> [nota]
            estado_marcar(e, sys.argv[4], "hecho", " ".join(sys.argv[5:]))
        elif acc == "fallo":    # estado fallo <estado.json> <paso> <motivo>
            estado_marcar(e, sys.argv[4], "fallo", " ".join(sys.argv[5:]))
        elif acc == "latido":
            e["ultimo_latido"] = _ahora().isoformat()
        elif acc == "candado":
            print(estado_candado(e)); sys.exit(0)
        elif acc == "reanudar": # estado reanudar <estado.json> [AAAA-MM-DDTHH:MM hora de Madrid]
            estado_reanudar(e, sys.argv[4] if len(sys.argv) > 4 else None)
        elif acc == "minimo":
            e["modo_minimo"] = True
        _save(ruta, e)
        print(json.dumps(estado_resumen(e), ensure_ascii=False))
    elif cmd == "validar":    # validar <parte> <carpeta> <marcadores.json>
        r = validar(int(sys.argv[2]), sys.argv[3], _load(sys.argv[4]))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
    elif cmd == "validar_final":  # validar_final <carpeta> <marcadores.json>
        r = validar_final(sys.argv[2], _load(sys.argv[3]))
        print(json.dumps(r, ensure_ascii=False, indent=2))
        sys.exit(0 if r["ok"] else 1)
    elif cmd == "registrar":  # registrar <historial.json> <carpeta> [evaluacion.json]
        h = _load(sys.argv[2])
        ev = _load(sys.argv[4]) if len(sys.argv) > 4 else None
        h, out = registrar(h, sys.argv[3], ev)
        out["propuestas"] = propuestas_automaticas(h)
        _save(sys.argv[2], h)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif cmd == "rellenar":   # rellenar <plantilla.md> <valores.json> <salida.md>
        with open(sys.argv[2], encoding="utf-8") as fh: plantilla = fh.read()
        txt, pend = rellenar(plantilla, _load(sys.argv[3]))
        with open(sys.argv[4], "w", encoding="utf-8") as fh: fh.write(txt)
        print("marcadores sin rellenar:", pend if pend else "ninguno")
        sys.exit(1 if pend else 0)
    else:
        print(__doc__)
