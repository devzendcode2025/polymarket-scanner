#!/usr/bin/env python3
"""Genera docs/index.html (el sitio publico) desde el ultimo reporte de scan.

Uso: python3 render_dashboard.py
Salida: <proyecto>/docs/index.html  (lo que GitHub Pages publica)
"""
import glob
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

PROYECTO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE = os.path.join(PROYECTO, "workspace")
REPORTS = os.path.join(WORKSPACE, "reports", "technical")
OUT = os.path.join(PROYECTO, "docs", "index.html")

NICA = timezone(timedelta(hours=-6))  # Nicaragua no usa horario de verano

CSS = """
  :root {
    --bg: #0b0e14; --panel: #131722; --card: #1a2030; --line: #232b3d;
    --text: #e6e9f0; --dim: #8b93a7; --green: #26a69a; --red: #ef5350;
    --accent: #ffd166; --blue: #4e8cff;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; line-height:1.5; }
  .wrap { max-width:1100px; margin:0 auto; padding:20px; }
  header { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; padding:18px 0; border-bottom:1px solid var(--line); }
  .logo { display:flex; align-items:center; gap:10px; font-weight:700; font-size:1.25rem; }
  .logo .dot { width:12px; height:12px; border-radius:50%; background:var(--green); box-shadow:0 0 12px var(--green); animation:pulse 2s infinite; }
  @keyframes pulse { 50% { opacity:.4; } }
  .live { background:rgba(38,166,154,.12); color:var(--green); border:1px solid rgba(38,166,154,.4); padding:4px 12px; border-radius:999px; font-size:.8rem; font-weight:600; }
  .scan-info { color:var(--dim); font-size:.8rem; text-align:right; }
  .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:14px; margin:22px 0; }
  .stat { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; }
  .stat .num { font-size:1.7rem; font-weight:700; }
  .stat .lbl { color:var(--dim); font-size:.8rem; margin-top:2px; }
  .stat.green .num { color:var(--green); } .stat.red .num { color:var(--red); } .stat.accent .num { color:var(--accent); } .stat.blue .num { color:var(--blue); }
  .panel { background:var(--card); border:1px solid var(--line); border-radius:12px; margin-bottom:18px; overflow:hidden; }
  .panel h2 { font-size:1rem; padding:14px 18px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; }
  .panel h2 .tag { font-size:.7rem; font-weight:600; padding:3px 10px; border-radius:999px; }
  .tag.green { background:rgba(38,166,153,.15); color:var(--green); } .tag.red { background:rgba(239,83,80,.15); color:var(--red); } .tag.dim { background:rgba(139,147,167,.12); color:var(--dim); }
  table { width:100%; border-collapse:collapse; font-size:.88rem; }
  th { text-align:left; color:var(--dim); font-weight:600; font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; padding:10px 18px; border-bottom:1px solid var(--line); }
  td { padding:12px 18px; border-bottom:1px solid rgba(35,43,61,.5); }
  tr:last-child td { border-bottom:none; }
  tr:hover td { background:rgba(78,140,255,.05); }
  .buy { color:var(--green); font-weight:700; } .sell { color:var(--red); font-weight:700; }
  .money { font-weight:600; font-variant-numeric:tabular-nums; }
  .q { color:var(--dim); font-size:.8rem; }
  .prob { display:flex; align-items:center; gap:8px; }
  .prob .bar { flex:1; max-width:140px; height:6px; border-radius:3px; background:#2a3348; overflow:hidden; }
  .prob .bar span { display:block; height:100%; background:linear-gradient(90deg,var(--red),var(--accent),var(--green)); }
  .prob .pct { font-weight:600; font-variant-numeric:tabular-nums; width:48px; text-align:right; }
  .empty { padding:26px 18px; text-align:center; color:var(--dim); font-size:.9rem; }
  .cta { background:linear-gradient(135deg,#1a2030,#14201f); border:1px solid rgba(38,166,153,.35); border-radius:12px; padding:22px; text-align:center; margin:24px 0; }
  .cta h3 { font-size:1.1rem; margin-bottom:6px; }
  .cta p { color:var(--dim); font-size:.9rem; margin-bottom:14px; }
  .cta .btn { display:inline-block; background:var(--green); color:#04110f; font-weight:700; padding:10px 26px; border-radius:8px; text-decoration:none; }
  footer { text-align:center; color:var(--dim); font-size:.75rem; padding:20px 0 30px; }
  @media (max-width:640px){ th,td { padding:8px 10px; } .prob .bar { display:none; } }
"""


def e(s):
    return html.escape(str(s), quote=True)


def fmt_money(x):
    return f"${x:,.0f}"


def load_latest():
    files = sorted(glob.glob(os.path.join(REPORTS, "scan_*.json")))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        return json.load(f)


def fmt_ts(ts):
    dt = datetime.fromtimestamp(ts, tz=NICA)
    meses = ["ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dt.day} {meses[dt.month-1]} {dt.year}, {dt.strftime('%H:%M')}"


def whales_table(whales):
    if not whales:
        return '<div class="empty">Sin ballenas en el último scan.</div>'
    rows = []
    for w in whales[:10]:
        side = "COMPRA" if str(w["side"]).upper() == "BUY" else "VENTA"
        cls = "buy" if side == "COMPRA" else "sell"
        rows.append(
            f"<tr><td class='{cls}'>{side}</td>"
            f"<td class='money'>{fmt_money(w['usd'])}</td>"
            f"<td>{e(w['outcome'])}</td>"
            f"<td class='q'>{e(w['titulo'])}</td></tr>"
        )
    return "<table><thead><tr><th>Dirección</th><th>Monto</th><th>Resultado</th><th>Mercado</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def mispricings_table(mispricings):
    if not mispricings:
        return ('<div class="empty">Sin ineficiencias en los mercados de alta liquidez en este scan.<br>'
                'El barrido de mercados de menor volumen está en desarrollo — ahí aparecen las oportunidades.</div>')
    rows = []
    for d in mispricings[:10]:
        rows.append(
            f"<tr><td class='q'>{e(d['question'])}</td>"
            f"<td class='money'>{d['yes']}</td><td class='money'>{d['no']}</td>"
            f"<td class='money'>{d['sum']}</td>"
            f"<td style='color:var(--accent)'>{d['direccion']}</td></tr>"
        )
    return ("<table><thead><tr><th>Mercado</th><th>Sí</th><th>No</th><th>Suma</th><th>Oportunidad</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def momentum_table(momentum):
    if not momentum:
        return '<div class="empty">Acumulando historial de precios. Las alertas de momentum aparecen cuando un precio se mueve ≥ 5% entre scans.</div>'
    rows = []
    for d in momentum[:10]:
        cls = "buy" if d["direccion"] == "SUBIDA" else "sell"
        rows.append(
            f"<tr><td class='{cls}'>{d['direccion']}</td>"
            f"<td class='money'>{d['cambio_pct']}%</td>"
            f"<td class='q'>{e(d['question'])}</td>"
            f"<td class='money'>{d['yes_antes']} → {d['yes_ahora']}</td></tr>"
        )
    return ("<table><thead><tr><th>Dirección</th><th>Cambio</th><th>Mercado</th><th>Prob. Sí</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def top_table(top):
    rows = []
    for m in top:
        pct = max(0.2, min(100, m["yes"] * 100))
        rows.append(
            f"<tr><td class='q'>{e(m['question'])}</td>"
            f"<td><div class='prob'><div class='bar'><span style='width:{pct:.1f}%'></span></div>"
            f"<span class='pct'>{m['yes']*100:.1f}%</span></div></td>"
            f"<td class='money' style='color:var(--green)'>{m['no']*100:.1f}%</td>"
            f"<td class='money'>{fmt_money(m['volumen'])}</td></tr>"
        )
    return ("<table><thead><tr><th>Mercado</th><th>Sí</th><th>No</th><th>Volumen</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table>")


def build(r):
    ts_str = fmt_ts(r["ts"])
    whales = r.get("ballenas", [])
    misp = r.get("mispricings", [])
    mom = r.get("momentum", [])
    whale_total = sum(w["usd"] for w in whales)
    n_whales = len(whales)

    n_whale_tag = f'<span class="tag green">{n_whales} nueva(s)</span>' if n_whales else '<span class="tag dim">0</span>'
    misp_tag = f'<span class="tag green">{len(misp)}</span>' if misp else '<span class="tag dim">0 activos</span>'
    mom_tag = f'<span class="tag green">{len(mom)}</span>' if mom else '<span class="tag dim">0 alertas</span>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Polymarket Scanner — Señales en vivo</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="logo"><span class="dot"></span> Polymarket Scanner</div>
    <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
      <span class="live">● EN VIVO</span>
      <div class="scan-info">Último scan: {ts_str} (hora Nicaragua)<br>Datos: APIs públicas de Polymarket</div>
    </div>
  </header>

  <div class="stats">
    <div class="stat blue"><div class="num">{r.get('mercados', 0)}</div><div class="lbl">Mercados monitoreados</div></div>
    <div class="stat green"><div class="num">{n_whales}</div><div class="lbl">Ballenas último scan</div></div>
    <div class="stat accent"><div class="num">{fmt_money(whale_total)}</div><div class="lbl">Volumen de ballenas</div></div>
    <div class="stat"><div class="num">{len(misp)}</div><div class="lbl">Mispricings activos</div></div>
    <div class="stat"><div class="num">{len(mom)}</div><div class="lbl">Alertas de momentum</div></div>
  </div>

  <div class="panel">
    <h2>🐋 Movimientos de ballenas {n_whale_tag}</h2>
    {whales_table(whales)}
  </div>

  <div class="panel">
    <h2>🎯 Mispricings detectados (Yes + No ≠ 1) {misp_tag}</h2>
    {mispricings_table(misp)}
  </div>

  <div class="panel">
    <h2>📈 Momentum (cambio ≥ 5%) {mom_tag}</h2>
    {momentum_table(mom)}
  </div>

  <div class="panel">
    <h2>🔥 Top mercados por volumen <span class="tag dim">actualizado cada scan</span></h2>
    {top_table(r.get('top_volumen', []))}
  </div>

  <div class="cta">
    <h3>🚀 ¿Quieres estas alertas en tiempo real?</h3>
    <p>Ballenas, mispricings y momentum directo a tu Telegram. Plan Starter $10/mes · Plan Pro $25/mes.</p>
    <a class="btn" href="#">Suscribirme — pago en USDC</a>
  </div>

  <footer>Polymarket Scanner — datos de fuentes públicas. No es asesoría financiera. · Hecho en Nicaragua 🇳🇮</footer>
</div>
</body>
</html>
"""


def main():
    r = load_latest()
    if r is None:
        print("ERROR: no hay reportes de scan todavia", file=sys.stderr)
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(r))
    print(f"Dashboard generado: {OUT} ({os.path.getsize(OUT)} bytes, scan {r['stamp']})")


if __name__ == "__main__":
    main()
