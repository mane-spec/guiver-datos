#!/usr/bin/env python3
"""P-040: comprueba que las copias de sistema/ son idénticas al manifiesto y que el motor pasa su autotest."""
import hashlib, json, subprocess, sys
m = json.load(open("sistema/manifiesto.json", encoding="utf-8"))
mal = [f for f, h in m["sha256"].items() if hashlib.sha256(open(f, "rb").read()).hexdigest() != h]
for f in mal: print("HUELLA DISTINTA:", f)
r = subprocess.run([sys.executable, "sistema/motor/motor.py", "selftest"], capture_output=True, text=True)
print(r.stdout.strip())
ok = not mal and r.returncode == 0 and "selftest OK" in r.stdout
print("comprobación OK" if ok else "comprobación CON FALLOS")
sys.exit(0 if ok else 1)
