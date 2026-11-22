#!/usr/bin/env python3
"""P-040 paso 5: repite con el motor del repo el cálculo de una semana publicada y exige cifras idénticas.

Uso: python3 sistema/tests/repetir_semana.py [caso.json ...]   (por defecto, todos los de sistema/tests/casos/)
Cada caso trae las entradas que lee motor.calcular y, en "esperado", lo publicado.
"""
import glob, importlib.util, json, os, sys

raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("motor", os.path.join(raiz, "motor", "motor.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

casos = sys.argv[1:] or sorted(glob.glob(os.path.join(raiz, "tests", "casos", "*.json")))
fallos = 0
for ruta in casos:
    c = json.load(open(ruta, encoding="utf-8"))
    esp = c["esperado"]
    d3 = {k: v for k, v in c.items() if k not in ("esperado", "nota")}
    limpio, fuera = m.filtrar_gli(d3)          # igual que «motor.py prob»
    if fuera: d3["fondo"] = limpio
    res = m.calcular(d3)
    dif = []
    for d in res["dias"]:
        p = [d["prob"]["on"], d["prob"]["neu"], d["prob"]["off"]]
        if p != esp["prob"].get(d["fecha"]): dif.append(f'{d["fecha"]}: {p} ≠ publicado {esp["prob"].get(d["fecha"])}')
        if d["fecha"] in esp.get("confianza", {}) and d["confianza"] != esp["confianza"][d["fecha"]]:
            dif.append(f'{d["fecha"]}: confianza {d["confianza"]} ≠ {esp["confianza"][d["fecha"]]}')
    if len(res["dias"]) != len(esp["prob"]): dif.append(f'{len(res["dias"])} días ≠ {len(esp["prob"])}')
    for f, p in (esp.get("si_modo_tension") or {}).items():
        q = m.sensibilidad_tension(d3).get(f)
        q = [q["on"], q["neu"], q["off"]] if q else None
        if q != p: dif.append(f"modo tensión {f}: {q} ≠ {p}")
    if "regla_ventas" in esp:
        r = m.reglas_actualizacion(d3)[0]
        for lado in ("hawkish", "dovish"):
            q = [r[lado]["on"], r[lado]["neu"], r[lado]["off"]]
            if q != esp["regla_ventas"][lado]: dif.append(f"regla {lado}: {q} ≠ {esp['regla_ventas'][lado]}")
    nombre = os.path.basename(ruta)
    if dif:
        fallos += 1
        print(f"{nombre}: DIFERENCIAS"); [print("  " + x) for x in dif]
    else:
        print(f"{nombre}: idéntico a lo publicado · " + " · ".join("/".join(map(str, v)) for v in esp["prob"].values()))
print("repetición OK" if not fallos else "repetición CON FALLOS")
sys.exit(1 if fallos else 0)
