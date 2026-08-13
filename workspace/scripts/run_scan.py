#!/usr/bin/env python3
"""Orquestador: recoge datos -> guarda -> detecta -> reporta.

Uso:  python3 run_scan.py [--limit N]
Salidas: workspace/reports/technical/scan_<timestamp>.json y .txt
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import polymarket_client as pc  # noqa: E402
import db as dbmod  # noqa: E402
import scanner  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE, "data", "polymarket.db")
REPORTS = os.path.join(BASE, "reports", "technical")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=200, help="mercados a barrer")
    args = ap.parse_args()

    ts = int(time.time())
    stamp = time.strftime("%Y%m%d_%H%M%S")

    print(f"[{time.strftime('%H:%M:%S')}] Iniciando scan...")
    conn = dbmod.init_db(DB_PATH)

    # 1. Recoger mercados top por volumen
    markets = pc.fetch_top_binary_markets(args.limit)
    print(f"  Mercados binarios activos: {len(markets)}")
    dbmod.upsert_markets(conn, markets)

    # 2. Snapshots de precios (para momentum futuro)
    for m in markets:
        dbmod.insert_snapshot(conn, m)

    # 3. Detecciones
    mispricings = scanner.detect_mispricing(markets)
    print(f"  Mispricings (Yes+No != 1, vol>=$10k): {len(mispricings)}")

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

    momentum = scanner.detect_momentum(markets, lambda mid: dbmod.last_snapshot(conn, mid))
    print(f"  Momentum (>=5% vs scan anterior): {len(momentum)}")

    # 4. Reporte
    report = {
        "ts": ts,
        "stamp": stamp,
        "mercados": len(markets),
        "mispricings": mispricings,
        "ballenas": whales,
        "momentum": momentum,
        "top_volumen": [
            {"question": m["question"], "yes": m["yes"], "no": m["no"],
             "volumen": m["volume"], "spread": m["spread"]}
            for m in sorted(markets, key=lambda x: x["volume"], reverse=True)[:10]
        ],
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
            f.write(f"  {d['question']}\n    Yes {d['yes']} + No {d['no']} = {d['sum']} "
                    f"(desvio {d['desvio']}) -> {d['direccion']} | vol ${d['volumen']:,.0f}\n")
        f.write("\n=== BALLENAS ===\n")
        for d in whales[:10]:
            f.write(f"  {d['side']} ${d['usd']:,.0f} en '{d['outcome']}' - {d['titulo']}\n")
        f.write("\n=== MOMENTUM ===\n")
        for d in momentum[:10]:
            f.write(f"  {d['direccion']} {d['cambio_pct']}% -> '{d['question']}' "
                    f"(yes {d['yes_antes']} -> {d['yes_ahora']})\n")

    dbmod.log_scan(conn, len(markets), len(mispricings) + len(whales) + len(momentum),
                   scanner.build_summary(markets, mispricings, whales, momentum))

    print(f"\nReporte guardado:")
    print(f"  {json_path}")
    print(f"  {txt_path}")
    print(scanner.build_summary(markets, mispricings, whales, momentum))


if __name__ == "__main__":
    main()
