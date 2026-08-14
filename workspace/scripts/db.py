#!/usr/bin/env python3
"""SQLite local: mercados, snapshots de precios, trades y log de scans."""
import os
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    question TEXT,
    slug TEXT,
    condition_id TEXT,
    yes_token TEXT,
    no_token TEXT,
    category TEXT,
    volume REAL,
    liquidity REAL,
    open_interest REAL,
    end_date TEXT,
    active INTEGER,
    closed INTEGER,
    updated_at INTEGER
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market_id TEXT,
    yes_price REAL,
    no_price REAL,
    sum_price REAL,
    spread REAL,
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_hash TEXT UNIQUE,
    market_id TEXT,
    title TEXT,
    outcome TEXT,
    side TEXT,
    size REAL,
    price REAL,
    usd_value REAL,
    ts INTEGER
);

CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts INTEGER,
    markets_seen INTEGER,
    detections INTEGER,
    summary TEXT
);

CREATE TABLE IF NOT EXISTS translations (
    source TEXT PRIMARY KEY,
    target TEXT,
    ts INTEGER
);
"""


def init_db(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_markets(conn, markets):
    cur = conn.cursor()
    now = int(time.time())
    for m in markets:
        cur.execute(
            """INSERT OR REPLACE INTO markets
               (id, question, slug, condition_id, yes_token, no_token, category,
                volume, liquidity, open_interest, end_date, active, closed, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (m["id"], m["question"], m["slug"], m["condition_id"], m["yes_token"],
             m["no_token"], m["category"], m["volume"], m["liquidity"],
             m["open_interest"], m["end_date"], m["active"], m["closed"], now),
        )
    conn.commit()


def insert_snapshot(conn, market):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO price_snapshots (market_id, yes_price, no_price, sum_price, spread, ts)
           VALUES (?,?,?,?,?,?)""",
        (market["id"], market["yes"], market["no"], market["sum_price"],
         market["spread"], int(time.time())),
    )
    conn.commit()


def last_snapshot(conn, market_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT yes_price, no_price, ts FROM price_snapshots
           WHERE market_id = ? ORDER BY ts DESC LIMIT 1""",
        (market_id,),
    )
    row = cur.fetchone()
    if row:
        return {"yes": row[0], "no": row[1], "ts": row[2]}
    return None


def insert_trades(conn, trades):
    cur = conn.cursor()
    for t in trades:
        try:
            cur.execute(
                """INSERT OR IGNORE INTO trades
                   (tx_hash, market_id, title, outcome, side, size, price, usd_value, ts)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (t["tx_hash"], t.get("market_id"), t.get("title"), t.get("outcome"),
                 t.get("side"), t.get("size"), t.get("price"), t.get("usd_value"),
                 t.get("ts")),
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()


def log_scan(conn, markets_seen, detections, summary):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scans (ts, markets_seen, detections, summary) VALUES (?,?,?,?)",
        (int(time.time()), markets_seen, detections, summary),
    )
    conn.commit()


def get_translations(conn, sources):
    """Devuelve {source: target} para los textos ya traducidos (cache)."""
    cur = conn.cursor()
    out = {}
    for s in sources:
        cur.execute("SELECT target FROM translations WHERE source = ?", (s,))
        row = cur.fetchone()
        if row:
            out[s] = row[0]
    return out


def save_translations(conn, pairs):
    """Guarda traducciones nuevas {source: target}."""
    cur = conn.cursor()
    now = int(time.time())
    for s, t in pairs.items():
        cur.execute(
            "INSERT OR REPLACE INTO translations (source, target, ts) VALUES (?,?,?)",
            (s, t, now),
        )
    conn.commit()


def prune_snapshots(conn, max_age_days=30):
    """Elimina snapshots mas viejos que max_age_days. Devuelve filas borradas."""
    cur = conn.cursor()
    cutoff = int(time.time()) - max_age_days * 86400
    cur.execute("DELETE FROM price_snapshots WHERE ts < ?", (cutoff,))
    conn.commit()
    return cur.rowcount


def db_size_mb(path):
    """Tamano del archivo de base en MB."""
    try:
        return round(os.path.getsize(path) / 1_048_576, 2)
    except OSError:
        return 0.0
