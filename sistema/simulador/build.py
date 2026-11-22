#!/usr/bin/env python3
"""
Genera el simulador semanal (una sola página HTML) a partir de:
  - registro/historial.json
  - la carpeta de la semana: datos1-3.json, parte1-3.md, auditoria.md, control.json,
    gli_resultado.json, gli_captura.png (opcional)
  - la plantilla HTML
El catálogo de factores y los pesos se importan de motor.py: el simulador usa
exactamente las mismas constantes que el motor.

Uso:
  python3 build.py --historial historial.json --semana semanas/2026-11-02/ \
                   --plantilla plantilla.html --salida simulador.html [--motor ruta/motor.py]
"""
import argparse, base64, importlib.util, json, os, sys

ETIQUETAS = {
    # fondo
    "gli_contraccion_acelerada": "GLI contracción acelerada (supón tu captura)",
    "gli_expansion_acelerada": "GLI expansión acelerada (supón tu captura)",
    "sofr_ge_iorb": "SOFR ≥ IORB",
    "gc_ge_iorb": "TGCR o BGCR ≥ IORB",
    "srf_material": "SRF con uso material",
    "fails_subiendo_sobre_media": "Fails suben (2 patas) y sobre media 8s",
    "xeurbi_le_m5_ampliando3": "XEURBI ≤ −5 pb y ampliándose ≥ 3 pb",
    "sofr_le_iorb_m5_gc_estable": "SOFR ≤ IORB − 5 pb con GC estable",
    "move_110_135": "MOVE 110–135",
    "move_80_110_subiendo10": "MOVE 80–110 subiendo ≥ 10 %",
    "move_lt_80": "MOVE < 80",
    "move_gt_135": "MOVE > 135",
    "fedwatch_hawkish": "FedWatch hawkish",
    "fedwatch_dovish_credito_ampliando": "FedWatch dovish con crédito ampliando",
    "fedwatch_dovish_credito_estable": "FedWatch dovish con crédito estable",
    "hy_ge_15": "HY ≥ +15 pb en la semana",
    "hy_5_15": "HY entre +5 y +15 pb",
    "ccc_ge_40": "CCC ≥ +40 pb en la semana",
    "tension_bancaria": "Tensión bancaria con dato",
    "hy_le_m10": "HY ≤ −10 pb en la semana",
    # dispersión
    "sub_10y_30y": "Subasta 10Y/30Y",
    "sub_20y": "Subasta 20Y",
    "sub_5y_7y": "Subasta 5Y/7Y",
    "tips_10y_mas": "TIPS 10Y+",
    "sub_2y_3y": "Subasta 2Y/3Y",
    "tips_5y": "TIPS 5Y",
    "settle_cupones_nnc10": "Settlement cupones NNC ≥ 10 bn",
    "macro1": "Macro de primer nivel",
    "macro2": "Macro de segundo nivel",
    "megacaps": "Earnings de megacaps",
    "oferta_acciones": "Oferta de acciones grande (IPO/colocación ≥ 10 bn)",
    "qra": "Anuncio del QRA",
    # dirección
    "subasta_cupon_condiciones_2de3": "Subasta 5Y+ con 2 de 3 condiciones",
    "tips_condiciones": "TIPS con MOVE ≥ 110 y hawkish",
    "settle_neto_absorcion20": "Absorción neta del día ≥ 20 bn (NNC − buybacks)",
    "settle_neto_inyeccion20": "Inyección neta del día ≥ 20 bn (pay down)",
    "fin_mes": "Fin de mes",
    "fin_trimestre": "Fin de trimestre",
    "tax_date": "Tax date",
    "buyback_liquidez": "Buyback de liquidez que liquida",
    "subasta_floja_settlement": "Subasta salió floja",
    "subasta_solida_settlement": "Subasta salió sólida",
    "dato_hawkish": "Dato de EE. UU. hawkish frente a consenso",
    "dato_dovish": "Dato de EE. UU. dovish frente a consenso",
}
GRUPOS = {"liquidez": "Liquidez global", "funding": "Funding", "tipos": "Tipos y duration", "credito": "Crédito y banca"}


def cargar_motor(ruta):
    spec = importlib.util.spec_from_file_location("motor", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def leer(path, binario=False):
    if not os.path.exists(path):
        return None
    if binario:
        with open(path, "rb") as fh:
            return fh.read()
    with open(path, encoding="utf-8") as fh:
        txt = fh.read()
    return json.loads(txt) if path.endswith(".json") else txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--historial", required=True)
    ap.add_argument("--semana", required=True)
    ap.add_argument("--plantilla", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--pdf", default=None, help="ruta del PDF del documento final (opcional)")
    ap.add_argument("--motor", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "motor", "motor.py"))
    a = ap.parse_args()
    if not os.path.exists(a.motor):
        a.motor = os.path.join(os.path.dirname(os.path.abspath(a.plantilla)), "motor.py")
    motor = cargar_motor(a.motor)
    w = a.semana if a.semana.endswith("/") else a.semana + "/"

    d3 = leer(w + "datos3.json")
    if not d3 or "resultado" not in d3:
        sys.exit("datos3.json sin bloque 'resultado': ejecuta antes motor.py prob")

    captura = leer(w + "gli_captura.png", binario=True)
    datos = {
        "generado": d3.get("corte"),
        "catalogo": {
            "fondo": {k: {"grupo": g, "lado": l, "pts": p, "etiqueta": ETIQUETAS.get(k, k)} for k, (g, l, p) in motor.FONDO.items()},
            "dispersion": {k: {"pts": p, "subasta": s, "etiqueta": ETIQUETAS.get(k, k)} for k, (p, s) in motor.DISPERSION.items()},
            "direccion": {k: {"lado": l, "pts": p, "condicion": c, "etiqueta": ETIQUETAS.get(k, k)} for k, (l, p, c) in motor.DIRECCION.items()},
            "pesos": motor.PESOS,
            "paso": getattr(motor, "PASO", 5),
            "confirma_tension": list(getattr(motor, "CONFIRMA_TENSION", [])),
            "grupos": GRUPOS,
            "control_normal": [[list(k), list(v)] for k, v in motor.CONTROL_NORMAL.items()],
            "control_tension": [[list(k), list(v)] for k, v in motor.CONTROL_TENSION.items()],
        },
        "historial": leer(a.historial),
        "d1": leer(w + "datos1.json"),
        "d2": leer(w + "datos2.json"),
        "d3": d3,
        "gli": leer(w + "gli_resultado.json"),
        "evaluacion": leer(w + "evaluacion.json"),
        "control": leer(w + "control.json"),
        "informes": {k: leer(w + f) for k, f in (("final", "informe_final.md"), ("parte1", "parte1.md"), ("parte2", "parte2.md"),
                                                  ("parte3", "parte3.md"), ("auditoria", "auditoria.md"))},
        "funding": motor.episodios(w, leer(a.historial) or {}),
        "captura_gli": ("data:image/png;base64," + base64.b64encode(captura).decode()) if captura else None,
    }
    # P-025: la causa de cada día es interna (análisis y aprendizaje); no viaja a la web
    INTERNOS = {"causa", "causa_motivo", "causa_fuente", "causa_auto", "con_causa", "aciertos_sin_causa", "funding_delta_pb"}
    def _limpia(o):
        if isinstance(o, dict): return {k: _limpia(v) for k, v in o.items() if k not in INTERNOS}
        if isinstance(o, list): return [_limpia(v) for v in o]
        return o
    datos = _limpia(datos)
    blob = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    with open(a.plantilla, encoding="utf-8") as fh:
        html = fh.read()
    if "/*__DATOS__*/" not in html:
        sys.exit("la plantilla no tiene el marcador /*__DATOS__*/")
    html = html.replace("/*__DATOS__*/null", blob)
    with open(a.salida, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"simulador generado: {a.salida} ({len(html)//1024} KB)")
    if a.pdf:
        print(generar_pdf(w + "informe_final.md", a.pdf))


PDF_CSS = """
@page{size:A4;margin:16mm 14mm 18mm}
body{font-family:"IBM Plex Sans","Helvetica Neue",Arial,"Liberation Sans",sans-serif;color:#141A26;font-size:10.2pt;line-height:1.5}
.marca{font-family:"IBM Plex Mono",Menlo,"DejaVu Sans Mono",monospace;font-size:8pt;letter-spacing:.16em;color:#3B5BDB;border-bottom:2px solid #3B5BDB;padding-bottom:4px;margin-bottom:14px}
h1{font-size:19pt;color:#0F1B3D;margin:0 0 4px;line-height:1.2}
h1 + p{color:#4A5468;font-size:9pt;margin-top:0}
h2{font-size:11.5pt;color:#3B5BDB;text-transform:uppercase;letter-spacing:.06em;margin:18px 0 6px;break-after:avoid}
table{border-collapse:collapse;width:100%;font-size:8.4pt;margin:6px 0 10px;break-inside:avoid}
th{background:#EEF2FC;color:#0F1B3D;text-align:left;font-weight:600}
th,td{border-bottom:1px solid #D9DEE8;padding:4px 6px;vertical-align:top}
code{font-family:"IBM Plex Mono",Menlo,monospace;font-size:8.6pt}
li{margin:2px 0}
.pie{margin-top:18px;border-top:1px solid #D9DEE8;padding-top:6px;font-size:7.6pt;color:#6B7488}
"""


def generar_pdf(md_path, salida):
    """Documento final en PDF con la estética Guiver de papel (fondo blanco, azules solo como acento)."""
    if not os.path.exists(md_path):
        return "pdf: no hay informe_final.md"
    try:
        import markdown
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "markdown"], check=False)
        try:
            import markdown
        except ImportError:
            return "pdf: no se pudo cargar el conversor de Markdown"
    with open(md_path, encoding="utf-8") as fh:
        cuerpo = markdown.markdown(fh.read(), extensions=["tables"])
    html = (f'<!doctype html><html lang="es"><meta charset="utf-8"><title>Informe final</title><style>{PDF_CSS}</style>'
            f'<body><div class="marca">GUIVER RESEARCH · LIQUIDEZ GLOBAL</div>{cuerpo}</body></html>')
    tmp = os.path.splitext(salida)[0] + ".html"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(html)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto("file://" + os.path.abspath(tmp))
            pg.pdf(path=salida, format="A4", print_background=True, display_header_footer=True,
                   header_template="<span></span>",
                   footer_template='<div style="font-size:7px;color:#6B7488;width:100%;text-align:center">Guiver Research · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
                   margin={"top": "16mm", "bottom": "18mm", "left": "14mm", "right": "14mm"})
            b.close()
        return f"pdf generado: {salida}"
    except Exception as e:
        return f"pdf: no generado ({e}); queda {tmp}"


if __name__ == "__main__":
    main()
