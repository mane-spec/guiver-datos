#!/usr/bin/env python3
"""
Guiver Research · paquete de datos semanal (sistema híbrido).

Se ejecuta en GitHub Actions (internet abierto) y deja en paquete/<CORTE>/
las series que los investigadores sacaban con WebFetch, en el MISMO formato
de CSV que piden investigadores.md:
    serie,fecha,valor,unidad,fuente,estado,retraso_dias,nota

Solo fuentes oficiales o abiertas SIN clave. Cada fuente va aislada: si una
falla, se anota en manifiesto.json y el resto sigue (el orquestador usa
WebFetch como respaldo para lo que falte).

Uso:
    python3 datos.py                      # CORTE = último viernes
    python3 datos.py --corte 2026-11-13   # CORTE explícito
    python3 datos.py --selftest           # prueba sin red
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

UA = "GuiverResearch-datos/1.0 (+github actions)"
CAB = ["serie", "fecha", "valor", "unidad", "fuente", "estado", "retraso_dias", "nota"]

# ------------------------------------------------------------------ series
FRED = {
    # serie: (unidad, parte, nota)
    "IORB": ("%", "P1-A", "solo contraste; fuente principal = nota de implementación del FOMC"),
    "WRESBAL": ("mm USD", "P1-B", "reservas semanales (miércoles)"),
    "BAMLC0A0CM": ("%", "P3-B", "IG OAS (×100 = pb)"),
    "BAMLH0A0HYM2": ("%", "P3-B", "HY OAS (×100 = pb)"),
    "BAMLH0A2HYB": ("%", "P3-B", "Single-B OAS (×100 = pb)"),
    "BAMLH0A3HYC": ("%", "P3-B", "CCC OAS (×100 = pb)"),
    "BAMLH0A0HYM2EY": ("%", "P3-B", "HY rentabilidad total (P-037)"),
    "BAMLH0A2HYBEY": ("%", "P3-B", "B rentabilidad; puede ir cortada (STALE)"),
    "BAMLH0A3HYCEY": ("%", "P3-B", "CCC rentabilidad; puede ir cortada (STALE)"),
    "DGS2": ("%", "P3-B/P3-C", "Treasury 2Y (actas P-035)"),
    "DGS5": ("%", "P3-B", "Treasury 5Y"),
    "SP500": ("índice", "P3-F", "cierre S&P 500"),
    "NASDAQ100": ("índice", "P3-F", "cierre Nasdaq 100"),
}

NYFED = "https://markets.newyorkfed.org/api"
FISCAL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"


# ------------------------------------------------------------------ utilidades
def ultimo_viernes(hoy=None):
    hoy = hoy or dt.date.today()
    return hoy - dt.timedelta(days=(hoy.weekday() - 4) % 7)


def dias_habiles(desde, hasta):
    """Días hábiles (lun–vie) entre dos fechas; 0 si desde >= hasta."""
    if desde >= hasta:
        return 0
    n, d = 0, desde
    while d < hasta:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def get(url, intentos=3, espera=4):
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            ultimo = e
            time.sleep(espera * (i + 1))
    raise RuntimeError(f"{type(ultimo).__name__}: {ultimo}")


def fila(serie, fecha, valor, unidad, fuente, corte, nota="", estado=None):
    f = dt.date.fromisoformat(fecha[:10])
    if estado is None:
        estado = "CONFIRMED" if valor not in (None, "") else "NOT AVAILABLE"
    return {
        "serie": serie, "fecha": f.isoformat(), "valor": "" if valor is None else valor,
        "unidad": unidad, "fuente": fuente, "estado": estado,
        "retraso_dias": dias_habiles(f, corte), "nota": nota,
    }


def a_num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ parsers (sin red, testeables)
def parse_fred(texto, serie):
    """fredgraph.csv: 1ª columna fecha, 2ª valor ('.' = vacío)."""
    out = []
    lector = csv.reader(io.StringIO(texto))
    next(lector, None)
    for r in lector:
        if len(r) < 2 or not r[0]:
            continue
        out.append((r[0], a_num(r[1])))
    return out


def parse_nyfed_tipos(js):
    out = []
    for r in js.get("refRates", []):
        out.append({
            "tipo": r.get("type"), "fecha": r.get("effectiveDate"),
            "tipo_pct": r.get("percentRate"),
            "p1": r.get("percentPercentile1"), "p25": r.get("percentPercentile25"),
            "p75": r.get("percentPercentile75"), "p99": r.get("percentPercentile99"),
            "volumen_bn": r.get("volumeInBillions"),
        })
    return out


def parse_nyfed_rp(js):
    """Suma por día y tipo (Repo = SRF, Reverse Repo = ON RRP)."""
    ops = js.get("repo", {}).get("operations", [])
    agg = {}
    for o in ops:
        clave = (o.get("operationDate"), o.get("operationType"))
        a = agg.setdefault(clave, {"submitted": 0.0, "accepted": 0.0, "n": 0})
        a["submitted"] += a_num(o.get("totalAmtSubmitted")) or 0.0
        a["accepted"] += a_num(o.get("totalAmtAccepted")) or 0.0
        a["n"] += 1
    return [{"fecha": k[0], "tipo": k[1], **v} for k, v in sorted(agg.items())]


def parse_fiscal(js):
    return js.get("data", [])


# ------------------------------------------------------------------ fuentes
def f_fred(corte, desde, filas, man):
    for serie, (unidad, parte, nota) in FRED.items():
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}"
               f"&cosd={desde.isoformat()}&coed={corte.isoformat()}")
        try:
            obs = parse_fred(get(url), serie)
            obs = [o for o in obs if o[0] <= corte.isoformat()]
            for fecha, v in obs:
                filas.append(fila(serie, fecha, v, unidad, "FRED", corte,
                                  nota, estado=None if v is not None else "PENDING"))
            ultima = max((o[0] for o in obs if o[1] is not None), default=None)
            man[serie] = {"ok": True, "parte": parte, "filas": len(obs), "ultima": ultima, "url": url}
        except Exception as e:  # noqa: BLE001
            man[serie] = {"ok": False, "parte": parte, "error": str(e), "url": url}


def f_nyfed(corte, desde, filas, man, carpeta):
    url = f"{NYFED}/rates/all/search.json?startDate={desde}&endDate={corte}"
    try:
        tipos = parse_nyfed_tipos(json.loads(get(url)))
        for t in tipos:
            for campo, unidad in (("tipo_pct", "%"), ("p1", "%"), ("p25", "%"), ("p75", "%"),
                                  ("p99", "%"), ("volumen_bn", "bn USD")):
                if t.get(campo) is None:
                    continue
                nombre = t["tipo"] if campo == "tipo_pct" else f"{t['tipo']}_{campo}"
                filas.append(fila(nombre, t["fecha"], t[campo], unidad, "NY Fed API", corte))
        ult = {}
        for t in tipos:
            ult[t["tipo"]] = max(ult.get(t["tipo"], ""), t["fecha"] or "")
        man["nyfed_tipos"] = {"ok": True, "parte": "P1-A", "filas": len(tipos), "ultima": ult, "url": url}
    except Exception as e:  # noqa: BLE001
        man["nyfed_tipos"] = {"ok": False, "parte": "P1-A", "error": str(e), "url": url}

    url = f"{NYFED}/rp/all/all/results/search.json?startDate={desde}&endDate={corte}"
    try:
        js = json.loads(get(url))
        with open(os.path.join(carpeta, "nyfed_rp_bruto.json"), "w") as fh:
            json.dump(js, fh)
        dias = parse_nyfed_rp(js)
        for d in dias:
            nombre = "ONRRP" if d["tipo"] == "Reverse Repo" else "SRF" if d["tipo"] == "Repo" else d["tipo"]
            filas.append(fila(f"{nombre}_aceptado", d["fecha"], d["accepted"] / 1e9, "bn USD",
                              "NY Fed API", corte, f"{d['n']} operaciones"))
            filas.append(fila(f"{nombre}_solicitado", d["fecha"], d["submitted"] / 1e9, "bn USD",
                              "NY Fed API", corte))
        man["nyfed_rp"] = {"ok": True, "parte": "P1-B", "filas": len(dias),
                           "ultima": max((d["fecha"] for d in dias), default=None), "url": url}
    except Exception as e:  # noqa: BLE001
        man["nyfed_rp"] = {"ok": False, "parte": "P1-B", "error": str(e), "url": url}


def fiscal_todo(ruta, filtro, orden="-record_date"):
    """Pagina hasta el final; devuelve todas las filas."""
    filas, pagina = [], 1
    while True:
        q = {"filter": filtro, "sort": orden, "page[size]": "1000", "page[number]": str(pagina)}
        url = f"{FISCAL}{ruta}?" + urllib.parse.urlencode(q, safe=":,[]-")
        js = json.loads(get(url))
        datos = parse_fiscal(js)
        filas += datos
        total = js.get("meta", {}).get("total-pages", 1)
        if pagina >= total or not datos:
            return filas, url
        pagina += 1


def guardar_csv(ruta, filas):
    if not filas:
        open(ruta, "w").close()
        return
    campos = sorted({k for f in filas for k in f})
    with open(ruta, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)


def f_fiscal(corte, desde, filas, man, carpeta):
    # TGA diario (DTS)
    try:
        datos, url = fiscal_todo("/v1/accounting/dts/operating_cash_balance",
                                 f"record_date:gte:{desde},record_date:lte:{corte}")
        guardar_csv(os.path.join(carpeta, "dts_saldo_bruto.csv"), datos)
        n = 0
        for d in datos:
            tipo = (d.get("account_type") or "")
            if "Closing Balance" in tipo or "TGA" in tipo and "Closing" in tipo:
                v = a_num(d.get("open_today_bal")) or a_num(d.get("close_today_bal"))
                if v is not None:
                    filas.append(fila("TGA_cierre", d["record_date"], v / 1000, "bn USD",
                                      "fiscaldata DTS", corte, tipo))
                    n += 1
        man["tga"] = {"ok": n > 0, "parte": "P2-A", "filas": n,
                      "ultima": max((d["record_date"] for d in datos), default=None), "url": url,
                      **({} if n else {"error": "sin filas de cierre: revisar account_type en dts_saldo_bruto.csv"})}
    except Exception as e:  # noqa: BLE001
        man["tga"] = {"ok": False, "parte": "P2-A", "error": str(e)}

    # Subastas: 18 meses (comparables de 6 previas por tenor, TIPS incluidos)
    hace18 = corte - dt.timedelta(days=550)
    for clave, ruta, filtro, orden, parte in (
        ("subastas", "/v1/accounting/od/auctions_query",
         f"auction_date:gte:{hace18},auction_date:lte:{corte}", "-auction_date", "P2-C/P2-D"),
        ("subastas_proximas", "/v1/accounting/od/upcoming_auctions",
         f"auction_date:gte:{corte}", "auction_date", "P2-B/P2-E"),
        ("buybacks", "/v1/accounting/od/buybacks_operations",
         f"operation_date:gte:{desde}", "-operation_date", "P2-A/P2-B"),
    ):
        try:
            datos, url = fiscal_todo(ruta, filtro, orden)
            guardar_csv(os.path.join(carpeta, f"{clave}.csv"), datos)
            man[clave] = {"ok": True, "parte": parte, "filas": len(datos), "url": url}
        except Exception as e:  # noqa: BLE001
            man[clave] = {"ok": False, "parte": parte, "error": str(e)}


def f_audjpy(corte, desde, filas, man):
    url = f"https://api.frankfurter.app/{desde}..{corte}?from=AUD&to=JPY"
    try:
        js = json.loads(get(url))
        for fecha, r in sorted(js.get("rates", {}).items()):
            filas.append(fila("AUDJPY_BCE", fecha, r.get("JPY"), "JPY", "Frankfurter (BCE)", corte,
                              "fixing BCE ~14:15 CET, NO es el cierre de Nueva York"))
        man["audjpy"] = {"ok": True, "parte": "P3-F", "filas": len(js.get("rates", {})), "url": url}
    except Exception as e:  # noqa: BLE001
        man["audjpy"] = {"ok": False, "parte": "P3-F", "error": str(e), "url": url}


def f_xeurbi(corte, man, carpeta):
    url = "https://www.cmegroup.com/reports/cme-xccy-basis-historical-data.csv"
    try:
        texto = get(url, intentos=2)
        if "<html" in texto[:500].lower():
            raise RuntimeError("CME devolvió HTML (bloqueo anti-bot)")
        with open(os.path.join(carpeta, "xeurbi_bruto.csv"), "w") as fh:
            fh.write(texto)
        man["xeurbi"] = {"ok": True, "parte": "P1-C", "bytes": len(texto), "url": url}
    except Exception as e:  # noqa: BLE001
        man["xeurbi"] = {"ok": False, "parte": "P1-C", "error": str(e), "url": url}


# ------------------------------------------------------------------ principal
def construir(corte, base="paquete"):
    desde = corte - dt.timedelta(days=84)  # 12 semanas
    carpeta = os.path.join(base, corte.isoformat())
    os.makedirs(carpeta, exist_ok=True)
    filas, man = [], {}
    f_fred(corte, desde, filas, man)
    f_nyfed(corte, desde, filas, man, carpeta)
    f_fiscal(corte, desde, filas, man, carpeta)
    f_audjpy(corte, desde, filas, man)
    f_xeurbi(corte, man, carpeta)

    filas.sort(key=lambda f: (f["serie"], f["fecha"]))
    ruta = os.path.join(carpeta, "series.csv")
    with open(ruta, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAB)
        w.writeheader()
        w.writerows(filas)

    huellas = {}
    for nombre in sorted(os.listdir(carpeta)):
        if nombre == "manifiesto.json":
            continue
        with open(os.path.join(carpeta, nombre), "rb") as fh:
            huellas[nombre] = hashlib.sha256(fh.read()).hexdigest()
    ok = sum(1 for v in man.values() if v.get("ok"))
    manifiesto = {
        "corte": corte.isoformat(), "desde": desde.isoformat(),
        "generado_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "fuentes_ok": ok, "fuentes_total": len(man), "fuentes": man, "archivos": huellas,
        "aviso": "Lo que no esté aquí con ok=true se busca con WebFetch como siempre.",
    }
    with open(os.path.join(carpeta, "manifiesto.json"), "w") as fh:
        json.dump(manifiesto, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(base, "ultimo.json"), "w") as fh:
        json.dump({"corte": corte.isoformat(), "carpeta": carpeta,
                   "fuentes_ok": ok, "fuentes_total": len(man)}, fh, indent=1)
    print(f"paquete {carpeta}: {ok}/{len(man)} fuentes OK, {len(filas)} filas")
    for k, v in man.items():
        if not v.get("ok"):
            print(f"  FALLO {k}: {v.get('error')}")
    return manifiesto


def selftest():
    assert ultimo_viernes(dt.date(2026, 11, 18)) == dt.date(2026, 11, 13)
    assert ultimo_viernes(dt.date(2026, 11, 13)) == dt.date(2026, 11, 13)
    assert dias_habiles(dt.date(2026, 11, 12), dt.date(2026, 11, 13)) == 1
    assert dias_habiles(dt.date(2026, 11, 6), dt.date(2026, 11, 13)) == 5
    assert parse_fred("observation_date,DGS2\n2026-11-12,3.51\n2026-11-13,.\n", "DGS2") == \
        [("2026-11-12", 3.51), ("2026-11-13", None)]
    t = parse_nyfed_tipos({"refRates": [{"type": "SOFR", "effectiveDate": "2026-11-12",
                                         "percentRate": 3.9, "volumeInBillions": 2900}]})
    assert t[0]["tipo"] == "SOFR" and t[0]["tipo_pct"] == 3.9
    rp = parse_nyfed_rp({"repo": {"operations": [
        {"operationDate": "2026-11-12", "operationType": "Repo", "totalAmtSubmitted": 5e9, "totalAmtAccepted": 4e9},
        {"operationDate": "2026-11-12", "operationType": "Repo", "totalAmtSubmitted": 1e9, "totalAmtAccepted": 1e9},
        {"operationDate": "2026-11-12", "operationType": "Reverse Repo", "totalAmtSubmitted": 3e9, "totalAmtAccepted": 3e9}]}})
    srf = [d for d in rp if d["tipo"] == "Repo"][0]
    assert srf["accepted"] == 5e9 and srf["n"] == 2
    f = fila("X", "2026-11-12", 1.0, "%", "t", dt.date(2026, 11, 13))
    assert f["retraso_dias"] == 1 and f["estado"] == "CONFIRMED"
    print("selftest OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--corte")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        sys.exit(0)
    corte = dt.date.fromisoformat(a.corte) if a.corte else ultimo_viernes()
    m = construir(corte)
    sys.exit(0 if m["fuentes_ok"] > 0 else 1)
