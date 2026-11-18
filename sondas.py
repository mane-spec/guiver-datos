#!/usr/bin/env python3
"""Prueba qué fuentes responden desde GitHub Actions (no guarda datos)."""
import json, urllib.request, time

UA = {"User-Agent": "GuiverResearch-datos/1.0 (+github actions; uso propio de research)",
      "Accept": "application/json,text/html,*/*"}
SONDAS = {
    "ff_esta_semana": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "ff_semana_siguiente": "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
    "te_guest": "https://api.tradingeconomics.com/calendar/country/united%20states?c=guest:guest&f=json",
    "nyfed_pd_lista": "https://markets.newyorkfed.org/api/pd/list/timeseries.json",
    "ofr_mnemonics": "https://data.financialresearch.gov/v1/metadata/mnemonics?dataset=nypd",
    "bls_schedule_ics": "https://www.bls.gov/schedule/news_release/bls.ics",
    "bea_schedule": "https://www.bea.gov/news/schedule",
    "fed_calendar": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "treasury_qra": "https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding",
    "treasury_tentativo": "https://home.treasury.gov/system/files/221/Tentative-Auction-Schedule.pdf",
    "sifma_festivos": "https://www.sifma.org/resources/general/holiday-schedule/",
}
out = {}
for k, u in SONDAS.items():
    t = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
        b = r.read().decode("utf-8", "replace")
        muestra = b[:300].replace("\n", " ")
        if k.startswith("yahoo"):
            try:
                j = json.loads(b)["chart"]["result"][0]
                ts = j["timestamp"][-3:]
                cl = j["indicators"]["quote"][0]["close"][-3:]
                muestra = f"ultimos={list(zip(ts, cl))}"
            except Exception as e:  # noqa
                muestra = "sin serie: " + muestra[:150]
        out[k] = {"ok": True, "http": r.status, "bytes": len(b), "seg": round(time.time() - t, 1), "muestra": muestra}
    except Exception as e:  # noqa
        out[k] = {"ok": False, "error": f"{type(e).__name__}: {e}"[:200], "seg": round(time.time() - t, 1)}
    print(k, "OK" if out[k]["ok"] else "FALLO", out[k].get("http", ""), out[k].get("bytes", ""), out[k].get("error", ""))
json.dump(out, open("sondas.json", "w"), indent=1, ensure_ascii=False)
