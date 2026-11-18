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

    candidatos = [
        f"{NYFED}/rp/all/all/results/search.json?startDate={desde}&endDate={corte}",
        f"{NYFED}/rp/results/search.json?startDate={desde}&endDate={corte}",
        f"{NYFED}/rp/all/all/results/last/150.json",
        f"{NYFED}/rp/all/all/results/lastTwoWeeks.json",
    ]
    try:
        js, url, errores = None, None, []
        for u in candidatos:
            try:
                js, url = json.loads(get(u, intentos=1)), u
                break
            except Exception as e:  # noqa: BLE001
                errores.append(f"{u.split('/api')[1]} → {e}")
        if js is None:
            raise RuntimeError(" | ".join(errores))
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
                           "ultima": max((d["fecha"] for d in dias), default=None), "url": url,
                           "intentos_fallidos": errores}
    except Exception as e:  # noqa: BLE001
        man["nyfed_rp"] = {"ok": False, "parte": "P1-B", "error": str(e), "url": url}


def fiscal_todo(ruta, filtro, orden="-record_date"):
    """Pagina hasta el final; devuelve todas las filas."""
    filas, pagina = [], 1
    while True:
        q = {"sort": orden, "page[size]": "1000", "page[number]": str(pagina)}
        if filtro:
            q["filter"] = filtro
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
         None, "auction_date", "P2-B/P2-E"),
        ("buybacks", "/v1/accounting/od/buybacks_operations",
         f"operation_date:gte:{desde}", "-operation_date", "P2-A/P2-B"),
    ):
        try:
            datos, url = fiscal_todo(ruta, filtro, orden)
            guardar_csv(os.path.join(carpeta, f"{clave}.csv"), datos)
            campo = "operation_date" if clave == "buybacks" else "auction_date"
            ultima = max((d.get(campo) or "" for d in datos), default=None)
            man[clave] = {"ok": True, "parte": parte, "filas": len(datos), "ultima": ultima, "url": url,
                          "fuente": "fiscaldata (secundaria para subastas: puede ir semanas atrasada)"}
        except Exception as e:  # noqa: BLE001
            man[clave] = {"ok": False, "parte": parte, "error": str(e)}


def f_treasurydirect(corte, man, carpeta):
    """Fuente PRINCIPAL de subastas (resultados al día y anunciadas)."""
    base = "https://www.treasurydirect.gov/TA_WS/securities"
    hace18 = corte - dt.timedelta(days=550)
    dias = (dt.date.today() - hace18).days
    for clave, urls, parte in (
        ("subastas_td", [f"{base}/auctioned?format=json&days={dias}",
                         f"{base}/auctioned?format=json&days=365",
                         f"{base}/search?startDate={hace18:%m/%d/%Y}&endDate={corte:%m/%d/%Y}"
                         f"&dateFieldName=auctionDate&format=json"], "P2-C/P2-D"),
        ("anunciadas_td", [f"{base}/announced?format=json&days=30"], "P2-B/P2-E"),
        ("proximas_td", [f"{base}/upcoming?format=json"], "P2-B/P2-E"),
    ):
        datos, url, errores = None, None, []
        for u in urls:
            try:
                datos, url = json.loads(get(u, intentos=2)), u
                break
            except Exception as e:  # noqa: BLE001
                errores.append(f"{u.split('securities/')[1][:40]} → {e}")
        try:
            if datos is None:
                raise RuntimeError(" | ".join(errores))
            if isinstance(datos, dict):
                datos = datos.get("securityList") or datos.get("data") or []
            datos = [{k: v for k, v in d.items() if not isinstance(v, (dict, list))} for d in datos]
            if clave == "subastas_td":  # nada posterior al CORTE
                datos = [d for d in datos
                         if (d.get("competitiveAuctionCloseDate") or "")[:10] <= corte.isoformat()]
            guardar_csv(os.path.join(carpeta, f"{clave}.csv"), datos)
            # fecha de subasta en TreasuryDirect = competitiveAuctionCloseDate
            ultima = max(((d.get("competitiveAuctionCloseDate") or "")[:10] for d in datos), default=None)
            man[clave] = {"ok": True, "parte": parte, "filas": len(datos), "ultima": ultima, "url": url,
                          "intentos_fallidos": errores}
        except Exception as e:  # noqa: BLE001
            man[clave] = {"ok": False, "parte": parte, "error": str(e), "url": url}


def html_a_texto(html):
    """Texto plano de una página HTML (sin scripts ni estilos)."""
    from html.parser import HTMLParser

    class P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.trozos, self.saltar = [], 0

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "noscript"):
                self.saltar += 1
            if tag in ("br", "p", "tr", "li", "h1", "h2", "h3", "h4", "div", "td", "th"):
                self.trozos.append("\n" if tag != "td" and tag != "th" else " | ")

        def handle_endtag(self, tag):
            if tag in ("script", "style", "noscript") and self.saltar:
                self.saltar -= 1

        def handle_data(self, d):
            if not self.saltar and d.strip():
                self.trozos.append(d.strip() + " ")

    p = P()
    p.feed(html)
    import re
    t = "".join(p.trozos)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def f_fails(corte, filas, man, carpeta):
    """Fails de primary dealers (NY Fed, semanal): todas las series de fails."""
    try:
        lista = json.loads(get(f"{NYFED}/pd/list/timeseries.json"))["pd"]["timeseries"]
        fails = [s for s in lista if "fail" in (s.get("description") or "").lower()]
        with open(os.path.join(carpeta, "fails_series.json"), "w") as fh:
            json.dump(fails, fh, indent=1)
        hace20 = (corte - dt.timedelta(weeks=20)).isoformat()
        n, ultima = 0, None
        for s in fails:
            kid = s["keyid"]
            js = json.loads(get(f"{NYFED}/pd/get/{kid}.json", intentos=2))
            for o in js.get("pd", {}).get("timeseries", []):
                f = o.get("asofdate")
                if not f or f < hace20 or f > corte.isoformat():
                    continue
                v = a_num(o.get("value"))
                filas.append(fila(f"FAILS_{kid}", f, v, "mm USD", "NY Fed primary dealer API", corte,
                                  s.get("description", "")[:120]))
                n += 1
                ultima = max(ultima or "", f)
        man["fails"] = {"ok": n > 0, "parte": "P3-A", "series": len(fails), "filas": n, "ultima": ultima,
                        **({} if n else {"error": "sin observaciones en 20 semanas"})}
    except Exception as e:  # noqa: BLE001
        man["fails"] = {"ok": False, "parte": "P3-A", "error": str(e)}


def f_calendarios(corte, man, carpeta):
    """Páginas oficiales guardadas como texto, para no depender de WebFetch."""
    paginas = {
        "fomc_calendario": ("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm", "P1-A/P3-C/P3-D"),
        "qra_pagina": ("https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding", "P2-E"),
        "bea_calendario": ("https://www.bea.gov/news/schedule", "P3-D"),
        "sifma_festivos": ("https://www.sifma.org/resources/general/holiday-schedule/", "P1-C/P2-E/P3-D"),
        "fed_comunicados": ("https://www.federalreserve.gov/newsevents/pressreleases.htm", "P1-C"),
    }
    for clave, (url, parte) in paginas.items():
        try:
            texto = html_a_texto(get(url, intentos=2))
            with open(os.path.join(carpeta, f"{clave}.txt"), "w") as fh:
                fh.write(f"Fuente: {url}\nDescargado: {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC\n\n{texto}")
            man[clave] = {"ok": len(texto) > 500, "parte": parte, "caracteres": len(texto), "url": url,
                          **({} if len(texto) > 500 else {"error": "página casi vacía (¿se carga con JavaScript?)"})}
        except Exception as e:  # noqa: BLE001
            man[clave] = {"ok": False, "parte": parte, "error": str(e), "url": url}

    # Calendario tentativo de subastas (PDF) → texto con pdftotext
    url = "https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.pdf"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            pdf = r.read()
        ruta = os.path.join(carpeta, "calendario_tentativo.pdf")
        with open(ruta, "wb") as fh:
            fh.write(pdf)
        import subprocess
        subprocess.run(["pdftotext", "-layout", ruta, ruta[:-4] + ".txt"], check=True, timeout=60)
        os.remove(ruta)
        man["calendario_tentativo"] = {"ok": True, "parte": "P2-B/P2-E", "bytes": len(pdf), "url": url}
    except Exception as e:  # noqa: BLE001
        man["calendario_tentativo"] = {"ok": False, "parte": "P2-B/P2-E", "error": str(e), "url": url}

    # Calendario macro con consenso (ForexFactory, feed abierto). "thisweek" = semana dom–sáb en curso;
    # "nextweek" solo aparece algunos días. Se guardan solo los eventos de USD.
    for clave, url in (("consenso_semana_actual", "https://nfs.faireconomy.media/ff_calendar_thisweek.json"),
                       ("consenso_semana_siguiente", "https://nfs.faireconomy.media/ff_calendar_nextweek.json")):
        try:
            datos = [e for e in json.loads(get(url, intentos=2)) if e.get("country") == "USD"]
            guardar_csv(os.path.join(carpeta, f"{clave}.csv"), datos)
            fechas = sorted(e.get("date", "")[:10] for e in datos)
            man[clave] = {"ok": bool(datos), "parte": "P3-C/P3-D", "filas": len(datos),
                          "desde": fechas[0] if fechas else None, "hasta": fechas[-1] if fechas else None,
                          "url": url, "fuente": "ForexFactory (SECONDARY); hora en ET con desfase incluido"}
        except Exception as e:  # noqa: BLE001
            man[clave] = {"ok": False, "parte": "P3-C/P3-D", "error": str(e), "url": url}


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
        texto = get(url, intentos=1)
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
    f_treasurydirect(corte, man, carpeta)
    f_fails(corte, filas, man, carpeta)
    f_calendarios(corte, man, carpeta)
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
    t = html_a_texto("<html><script>x()</script><h1>FOMC</h1><p>November 3-4</p><style>a{}</style></html>")
    assert "FOMC" in t and "November 3-4" in t and "x()" not in t
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
