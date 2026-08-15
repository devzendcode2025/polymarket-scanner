#!/usr/bin/env python3
"""Historico de aciertos (v0.8.0): convergencia de las senales emitidas.

Marketing: "nuestras senales acertaron X%". Para cada mercado RESUELTO
recientemente (Gamma closed=true), se cruza con los trades >= $1k que el
pipeline registro (tabla trades). Acierto = la ballena compro el outcome
ganador (el que Gamma resolvio a precio 1.0).

Diseno:
  - CACHE de 30 min en workspace/data/historico_cache.json (el cron de 1 min
    no golpea Gamma con closed=true en cada tick).
  - Tolerante a fallos: si Gamma falla, devuelve el cache anterior o {}.
  - La tabla trades se poda a 7 dias: el historico cubre la ventana reciente.
"""
import json
import os
import time
import urllib.request

import polymarket_client as pc

CACHE_MIN = 30
MIN_USD = 1000  # solo ballenas (>= $1k)
MAX_MERCADOS = 50

_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historico_cache.json"
)


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": pc.UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _outcome_ganador(m):
    """Devuelve el outcome que gano (precio 1.0) o None si no esta resuelto."""
    try:
        outcomes = json.loads(m.get("outcomes") or "[]")
        prices = json.loads(m.get("outcomePrices") or "[]")
    except (ValueError, TypeError):
        return None
    if len(outcomes) != 2 or len(prices) != 2:
        return None
    for i, p in enumerate(prices):
        try:
            if float(p) >= 0.99:
                return outcomes[i]
        except (TypeError, ValueError):
            continue
    # Diccionario {"YES": "1", "NO": "0"}
    if isinstance(m.get("outcomePrices"), dict):
        for k, v in m["outcomePrices"].items():
            try:
                if float(v) >= 0.99:
                    return k
            except (TypeError, ValueError):
                continue
    return None


def _resueltos():
    data = _get(
        f"{pc.GAMMA}/markets?limit={MAX_MERCADOS}&closed=true"
        "&order=endDate&ascending=false"
    )
    return data if isinstance(data, list) else data.get("markets", [])


def get_historico(conn, force=False):
    """Devuelve {total, aciertos, pct, ejemplos} de senales de ballena resueltas."""
    now = time.time()
    if not force:
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                cache = json.load(f)
            if now - cache.get("ts", 0) < CACHE_MIN * 60:
                return cache.get("historico", {})
        except (OSError, ValueError):
            pass

    try:
        mercados = _resueltos()
    except Exception:  # noqa: BLE001
        return {}

    total = 0
    aciertos = 0
    ejemplos = []
    for m in mercados:
        cond = m.get("conditionId")
        if not cond:
            continue
        ganador = _outcome_ganador(m)
        if ganador is None:
            continue
        cur = conn.cursor()
        cur.execute(
            "SELECT outcome, usd_value FROM trades "
            "WHERE market_id = ? AND usd_value >= ?",
            (cond, MIN_USD),
        )
        trades = cur.fetchall()
        if not trades:
            continue
        ganador_n = str(ganador).strip().lower()
        mercado_total = 0
        mercado_aciertos = 0
        for outcome, usd in trades:
            mercado_total += 1
            if str(outcome or "").strip().lower() == ganador_n:
                mercado_aciertos += 1
        total += mercado_total
        aciertos += mercado_aciertos
        ejemplos.append({
            "question": m.get("question", ""),
            "ganador": ganador,
            "trades": mercado_total,
            "aciertos": mercado_aciertos,
        })

    historico = {
        "ts": int(now),
        "total": total,
        "aciertos": aciertos,
        "pct": round(aciertos * 100.0 / total, 1) if total else 0.0,
        "ejemplos": ejemplos[:5],
    }
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": now, "historico": historico}, f, ensure_ascii=False)
    except OSError:
        pass
    return historico
