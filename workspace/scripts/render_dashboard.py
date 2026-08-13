#!/usr/bin/env python3
"""Genera docs/data.json con las detecciones del ultimo scan para la app del dashboard.

La app (docs/index.html) consulta las APIs de Polymarket EN VIVO desde el
navegador (ballenas, top mercados) y lee data.json para las detecciones que
solo nuestro pipeline puede calcular (mispricings, momentum con historial).

Uso: python3 render_dashboard.py
Salida: <proyecto>/docs/data.json
"""
import glob
import json
import os
import sys

PROYECTO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE = os.path.join(PROYECTO, "workspace")
REPORTS = os.path.join(WORKSPACE, "reports", "technical")
OUT = os.path.join(PROYECTO, "docs", "data.json")


def main():
    files = sorted(glob.glob(os.path.join(REPORTS, "scan_*.json")))
    if not files:
        print("ERROR: no hay reportes de scan todavia", file=sys.stderr)
        sys.exit(1)
    r = json.load(open(files[-1], encoding="utf-8"))
    data = {
        "ts": r["ts"],
        "stamp": r["stamp"],
        "mercados": r["mercados"],
        "mispricings": r["mispricings"],
        "momentum": r["momentum"],
        "ballenas_scan": r["ballenas"],
        "db_size_mb": r.get("db_size_mb", 0),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"data.json generado: {OUT} ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
