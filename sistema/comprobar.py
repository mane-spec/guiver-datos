#!/usr/bin/env python3
"""P-040: comprueba el sistema copiado al repo.
1. Huellas SHA-256 de sistema/manifiesto.json.  2. motor.py selftest.  3. paridad motor Python ↔ réplica JS.
4. Repetición de semanas publicadas (probabilidades idénticas).  5. Todos los JSON de sistema/ válidos.
6. Los archivos que el orquestador descarga existen con esos nombres."""
import glob, hashlib, json, os, re, subprocess, sys
fallos = []
m = json.load(open("sistema/manifiesto.json", encoding="utf-8"))
for f, h in m["sha256"].items():
    if not os.path.exists(f) or hashlib.sha256(open(f, "rb").read()).hexdigest() != h: fallos.append("huella distinta: " + f)
def corre(nombre, args, debe):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    print(f"[{nombre}]", (r.stdout.strip().splitlines() or [""])[-1])
    if r.returncode != 0 or debe not in r.stdout: fallos.append(f"{nombre}: {r.stdout[-400:]}{r.stderr[-400:]}")
corre("motor", ["sistema/motor/motor.py", "selftest"], "selftest OK")
corre("paridad", ["sistema/tests/paridad.py"], "PARIDAD EXACTA")
corre("repetición", ["sistema/tests/repetir_semana.py"], "repetición OK")
for f in glob.glob("sistema/**/*.json", recursive=True):
    try: json.load(open(f, encoding="utf-8"))
    except Exception as e: fallos.append(f"JSON no válido: {f} ({e})")
orq = open("sistema/orquestador.md", encoding="utf-8").read()
fase0 = orq[orq.index("FASE 0"):orq.index("FASE 1A")]
for nombre in set(re.findall(r"(?:sistema/[\w/.-]+|parte\d-v[\d.]+\.md|final-v\d\.md)", fase0)):
    ruta = nombre if nombre.startswith("sistema/") else "sistema/prompts/" + nombre
    ruta = ruta.rstrip(".,")
    if not os.path.exists(ruta): fallos.append("el orquestador pide un archivo que no está: " + ruta)
for x in fallos: print("FALLO:", x)
print("comprobación OK" if not fallos else "comprobación CON FALLOS")
sys.exit(1 if fallos else 0)
