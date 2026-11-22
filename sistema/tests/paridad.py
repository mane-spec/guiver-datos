"""Paridad motor.py ↔ motor JS del simulador en escenarios aleatorios."""
import json, random, subprocess, sys, os, importlib.util, re
raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("motor", os.path.join(raiz, "motor", "motor.py")); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
html = open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(raiz, "simulador", "plantilla.html"), encoding="utf-8").read()
js = html[html.index("// MOTOR-INICIO"):html.index("// MOTOR-FIN")]
cat = {"fondo": {k: {"grupo": g, "lado": l, "pts": p} for k, (g, l, p) in m.FONDO.items()},
       "dispersion": {k: {"pts": p, "subasta": s} for k, (p, s) in m.DISPERSION.items()},
       "direccion": {k: {"lado": l, "pts": p, "condicion": c} for k, (l, p, c) in m.DIRECCION.items()},
       "pesos": m.PESOS, "paso": m.PASO, "confirma_tension": list(m.CONFIRMA_TENSION)}
random.seed(7); casos = []
for _ in range(3000):
    porF, porM, sens, forzar = random.random() < .45, random.random() < .1, random.random() < .4, random.random() < .15
    fondo = random.sample(list(m.FONDO), random.randint(0, 6))
    dias = []
    for i in range(5):
        dias.append({"fecha": f"2026-11-0{i+2}", "evento_verificado": random.random() > .15,
                     "dispersion": [{"id": k} for k in random.sample(list(m.DISPERSION), random.randint(0, 4))],
                     "direccion": [{"id": k} for k in random.sample(list(m.DIRECCION), random.randint(0, 3))]})
    base = random.choice([[20, 50, 30], [25, 45, 30], [20, 55, 25], [15, 50, 35], [25, 50, 25]])
    conf = random.choice(["alta", "media", "baja"])
    casos.append({"porF": porF, "porM": porM, "sens": sens, "forzar": forzar, "fondo": fondo, "dias": dias, "base": base, "conf": conf})
py = []
for c in casos:
    # en el simulador, marcar un factor GLI equivale a "supón que tu captura lo muestra"
    d3 = {"modo_tension": {"por_funding": c["porF"], "por_move": c["porM"], "forzar": c["forzar"]}, "base": c["base"], "confianza": c["conf"],
          "fondo": [{"id": f} for f in c["fondo"]], "dias": c["dias"], "gli": {"puntua": {"fuente": "captura"}},
          "sensibilidad_settlement": {"activa": c["sens"]}}
    py.append([[x["prob"]["on"], x["prob"]["neu"], x["prob"]["off"]] for x in m.calcular(d3)["dias"]])
script = js + f"""
const M = Motor({json.dumps(cat)});
const casos = {json.dumps(casos)};
console.log(JSON.stringify(casos.map(c => M.calcular(c).dias.map(d => [d.p.on, d.p.neu, d.p.off]))));
"""
out = json.loads(subprocess.run(["node", "-"], input=script, capture_output=True, text=True, check=True).stdout)
dif = [(i, py[i], out[i]) for i in range(len(casos)) if py[i] != out[i]]
print(f"{len(casos)} escenarios × 5 días: {'PARIDAD EXACTA' if not dif else str(len(dif)) + ' diferencias'}")
for x in dif[:5]: print(x)
# publicado sin captura: motor.py prob limpia el fondo; el simulador recibe el fondo limpio y debe coincidir
dif2 = 0
for c in casos[:500]:
    d3 = {"modo_tension": {"por_funding": c["porF"], "por_move": c["porM"]}, "base": c["base"], "confianza": c["conf"],
          "fondo": [{"id": f} for f in c["fondo"]], "dias": c["dias"]}
    limpio, _ = m.filtrar_gli(d3)
    r_motor = [[x["prob"]["on"], x["prob"]["neu"], x["prob"]["off"]] for x in m.calcular(d3)["dias"]]
    r_limpio = [[x["prob"]["on"], x["prob"]["neu"], x["prob"]["off"]] for x in m.calcular({**d3, "fondo": limpio, "gli": {"puntua": {"fuente": "captura"}}})["dias"]]
    dif2 += r_motor != r_limpio
print("publicado sin captura (fondo limpio):", "OK" if not dif2 else f"{dif2} diferencias")
sys.exit(1 if dif or dif2 else 0)
