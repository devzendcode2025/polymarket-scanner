#!/usr/bin/env python3
"""Orquestador: recoge datos -> guarda (con poda) -> detecta -> reporta.

Uso:  python3 run_scan.py [--limit N] [--quiet]
Salidas: workspace/reports/technical/scan_<timestamp>.json y .txt
Politica de disco (scan cada 1 min):
  - Snapshots de precio SOLO si el precio cambio >= 0.5% vs el anterior
  - Snapshots viejos (>30 dias) se podan en cada corrida
  - Reportes: se conservan solo los ultimos 20
"""
import argparse
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import polymarket_client as pc  # noqa: E402
import db as dbmod  # noqa: E402
import scanner  # noqa: E402
import analyst  # noqa: E402
import translate  # noqa: E402
import crosscheck  # noqa: E402
import categorias  # noqa: E402
import narrativa  # noqa: E402
import historico_aciertos  # noqa: E402

PROYECTO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORKSPACE = os.path.join(PROYECTO, "workspace")
DB_PATH = os.path.join(WORKSPACE, "data", "polymarket.db")
REPORTS = os.path.join(WORKSPACE, "reports", "technical")

CAMBIOS_MIN = 0.005    # 0.5% de cambio de precio para guardar snapshot
SNAPSHOT_TTL_DIAS = 30  # retencion de snapshots
MAX_REPORTES = 20       # reportes conservados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200, help="mercados a barrer")
    ap.add_argument("--quiet", action="store_true", help="sin salida en consola (cron)")
    args = ap.parse_args()

    if args.quiet:
        sys.stdout = open(os.devnull, "w")

    ts = int(time.time())
    stamp = time.strftime("%Y%m%d_%H%M%S")

    print(f"[{time.strftime('%H:%M:%S')}] Iniciando scan...")
    conn = dbmod.init_db(DB_PATH)

    # 1. Recoger mercados top por volumen
    markets = pc.fetch_top_binary_markets(args.limit)
    print(f"  Mercados binarios activos: {len(markets)}")
    dbmod.upsert_markets(conn, markets)

    # 2. Snapshots SOLO con cambio significativo (control de disco a 1/min)
    snap_guardados = 0
    for m in markets:
        prev = dbmod.last_snapshot(conn, m["id"])
        if prev and prev["yes"] != 0:
            delta = abs(m["yes"] - prev["yes"]) / prev["yes"]
            if delta < CAMBIOS_MIN:
                continue  # precio estable, no guardar
        dbmod.insert_snapshot(conn, m)
        snap_guardados += 1

    # 2b. Poda de snapshots viejos + trades viejos (control de disco)
    podados = dbmod.prune_snapshots(conn, SNAPSHOT_TTL_DIAS)
    podados_t = dbmod.prune_trades(conn, 7)
    print(f"  Snapshots guardados: {snap_guardados} | podados (>30d): {podados} | trades podados (>7d): {podados_t}")

    # 3. Detecciones
    # 3a. Mispricings: ademas del top-200 (eficientes), barrer la cola
    #     (offset 200-400, menor volumen) donde es mas probable el desvio.
    #     La cola NO se guarda en snapshots ni trades (solo se escanea).
    cola = []
    try:
        cola = pc.fetch_top_binary_markets(200, offset=200)
    except Exception:  # noqa: BLE001 - el barrido extra no rompe el scan
        pass
    mispricings = scanner.detect_mispricing(markets + cola)
    print(f"  Mispricings (Yes+No != 1, vol>=$10k): {len(mispricings)} "
          f"(barrido: {len(markets)} top + {len(cola)} cola)")

    trades = pc.fetch_trades(limit=200)
    norm_trades = []
    for t in trades:
        try:
            size = float(t.get("size") or 0)
            price = float(t.get("price") or 0)
            norm_trades.append({
                "tx_hash": t.get("transactionHash") or f"{t.get('slug')}-{t.get('timestamp')}-{t.get('outcome')}",
                "market_id": t.get("conditionId"),
                "title": t.get("title"),
                "slug": t.get("slug"),
                "outcome": t.get("outcome"),
                "side": t.get("side"),
                "size": size,
                "price": price,
                "usd_value": size * price,
                "ts": t.get("timestamp"),
            })
        except (TypeError, ValueError):
            continue
    dbmod.insert_trades(conn, norm_trades)
    whales = scanner.detect_whales(norm_trades)
    print(f"  Ballenas (trades >= $1k): {len(whales)}")

    # Enriquecer ballenas con volumen/tags del mercado (para el analista y el filtro por pais)
    markets_by_cond = {m["condition_id"]: m for m in markets if m.get("condition_id")}
    for w in whales:
        m = markets_by_cond.get(w.get("market_id"))
        if m is None and w.get("slug"):
            m = next((x for x in markets if x.get("slug") == w["slug"]), None)
        if m:
            w["volumen_mercado"] = m["volume"]
            w.setdefault("slug", m.get("slug"))
            w.setdefault("tags", m.get("tags") or [])
        w.setdefault("categoria", categorias.clasificar(w.get("titulo") or ""))

    momentum = scanner.detect_momentum(markets, lambda mid: dbmod.last_snapshot(conn, mid))
    print(f"  Momentum (>=5% vs scan anterior): {len(momentum)}")

    # 3b. Cross-check fuentes externas (F3): edge = "datos ganadores"
    edges = crosscheck.get_edges(conn, [
        {"question": m["question"], "slug": m.get("slug"),
         "yes": m["yes"], "volume": m["volume"]}
        for m in markets
    ])
    print(f"  Edges (consenso externo vs Polymarket): {len(edges)}")

    # 3c. Analista heuristico: probabilidad + confianza + horizonte + justificacion
    mispricings, whales, momentum, edges = analyst.enrich(mispricings, whales, momentum, edges)
    print(f"  Analisis: {sum(1 for d in mispricings + whales + momentum + edges if d.get('confianza') == 'alta')} senales de confianza alta")

    # 3d. Traduccion de titulos al espanol (DeepSeek + cache SQLite; fallback silencioso)
    top_volumen = [
        {"question": m["question"], "slug": m.get("slug"), "yes": m["yes"], "no": m["no"],
         "volumen": m["volume"], "spread": m["spread"],
         "categoria": categorias.clasificar(m["question"])}
        for m in sorted(markets, key=lambda x: x["volume"], reverse=True)[:25]
    ]
    textos = ([d["question"] for d in mispricings] + [d["titulo"] for d in whales] +
              [d["question"] for d in momentum] + [m["question"] for m in top_volumen] +
              [e["question"] for e in edges] +
              [f["titulo"] for e in edges for f in e.get("fuentes", [])])
    trad = translate.traducir(conn, textos)
    print(f"  Traducciones: {len(trad)} titulos al espanol")
    for d in mispricings + momentum:
        if d["question"] in trad:
            d["question_es"] = trad[d["question"]]
    for d in whales:
        if d["titulo"] in trad:
            d["titulo_es"] = trad[d["titulo"]]
    for m in top_volumen:
        if m["question"] in trad:
            m["question_es"] = trad[m["question"]]
    for e in edges:
        if e["question"] in trad:
            e["question_es"] = trad[e["question"]]
        for f in e.get("fuentes", []):
            if f["titulo"] in trad:
                f["titulo_es"] = trad[f["titulo"]]

    # 3e. Narrativa DeepSeek (F4): justificaciones narradas de las top-5 senales.
    # La clave de cache incluye los datos numericos: mercados quietos = 0 llamadas.
    seleccion = narrativa.seleccionar_top(mispricings, whales, momentum, edges, n=5)
    narrativa.narrar(conn, seleccion)
    n_narr = sum(1 for d in mispricings + whales + momentum + edges if d.get("narrativa"))
    print(f"  Narrativas F4: {n_narr} senales con analisis narrado")

    # 3f. Historico de aciertos (marketing): convergencia de ballenas resueltas
    historico = historico_aciertos.get_historico(conn)
    if historico:
        print(f"  Historico aciertos: {historico['aciertos']}/{historico['total']} "
              f"({historico['pct']}%)")

    # 4. Reporte
    report = {
        "ts": ts,
        "stamp": stamp,
        "mercados": len(markets),
        "snapshots_guardados": snap_guardados,
        "db_size_mb": dbmod.db_size_mb(DB_PATH),
        "mispricings": mispricings,
        "ballenas": whales,
        "momentum": momentum,
        "edges": edges,
        "top_volumen": top_volumen,
        "historico": historico,
    }
    os.makedirs(REPORTS, exist_ok=True)
    json_path = os.path.join(REPORTS, f"scan_{stamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    txt_path = os.path.join(REPORTS, f"scan_{stamp}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(scanner.build_summary(markets, mispricings, whales, momentum) + "\n\n")
        f.write("=== MISPRICINGS ===\n")
        for d in mispricings[:10]:
            f.write(f"  {d.get('question_es') or d['question']}\n"
                    f"    Yes {d['yes']} + No {d['no']} = {d['sum']} "
                    f"(desvio {d['desvio']}) -> {d['direccion']} | vol ${d['volumen']:,.0f}\n"
                    f"    Prob {d['prob']}% ({d['confianza']}, {d['horizonte']}) | {d['url']}\n")
        f.write("\n=== BALLENAS ===\n")
        for d in whales[:10]:
            f.write(f"  {d['side']} ${d['usd']:,.0f} en '{d['outcome']}' - {d.get('titulo_es') or d['titulo']} "
                    f"| prob {d['prob']}% ({d['confianza']}, {d['horizonte']}) | {d['url']}\n")
        f.write("\n=== MOMENTUM ===\n")
        for d in momentum[:10]:
            f.write(f"  {d['direccion']} {d['cambio_pct']}% -> '{d.get('question_es') or d['question']}' "
                    f"(yes {d['yes_antes']} -> {d['yes_ahora']}) "
                    f"| prob {d['prob']}% ({d['confianza']}, {d['horizonte']}) | {d['url']}\n")
        f.write("\n=== EDGES (consenso externo vs Polymarket) ===\n")
        for e in edges[:10]:
            f.write(f"  {e['direccion']} | edge {e['edge']:+.1f} pts -> '{e.get('question_es') or e['question']}'\n"
                    f"    Poly {e['prob_poly']}% vs consenso {e['consenso']}% "
                    f"({e.get('fuentes_nombres', '')}) | prob {e['prob']}% ({e['confianza']}, {e['horizonte']})\n"
                    f"    {e['url']}\n")

    dbmod.log_scan(conn, len(markets), len(mispricings) + len(whales) + len(momentum),
                   scanner.build_summary(markets, mispricings, whales, momentum))

    # 5. Poda de reportes viejos (mantener los ultimos MAX_REPORTES)
    rep_files = sorted(glob.glob(os.path.join(REPORTS, "scan_*")))
    for f in rep_files[:-MAX_REPORTES]:
        try:
            os.remove(f)
        except OSError:
            pass

    print(f"\nReporte guardado: {json_path}")
    print(f"BD: {dbmod.db_size_mb(DB_PATH)} MB")
    print(scanner.build_summary(markets, mispricings, whales, momentum))


if __name__ == "__main__":
    main()
