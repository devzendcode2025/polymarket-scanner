#!/usr/bin/env python3
"""Cliente de las APIs publicas de Polymarket (solo lectura).

APIs:
  - Gamma (gamma-api.polymarket.com): descubrimiento de mercados
  - CLOB  (clob.polymarket.com): precios, orderbook, historial
  - Data  (data-api.polymarket.com): trades, open interest
"""
import json
import time
import urllib.parse
import urllib.request

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA = "https://data-api.polymarket.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) polymarket-scanner/0.1"


def _get(base, path, params=None, timeout=20, retries=3):
    """GET con retries y backoff. Devuelve el JSON parseado."""
    url = base + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/json"}
    )
    last = None
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001 - reintentar ante cualquier fallo transitorio
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"Fallo GET {url}: {last}")


# ---------- Gamma ----------

def fetch_markets(limit=100, offset=0, order="volume"):
    """Mercados activos, ordenados por volumen (los mas liquidos primero)."""
    return _get(
        GAMMA, "/markets",
        {"limit": limit, "offset": offset, "active": "true",
         "closed": "false", "order": order, "ascending": "false"},
    )


# ---------- CLOB ----------

def fetch_orderbook(token_id):
    """Libro de ordenes de un token (Yes o No)."""
    return _get(CLOB, "/book", {"token_id": token_id})


def fetch_price_history(condition_id, interval="1w", fidelity=24):
    """Historial de precios del mercado (conditionId)."""
    return _get(
        CLOB, "/prices-history",
        {"market": condition_id, "interval": interval, "fidelity": fidelity},
    )


# ---------- Data ----------

def fetch_trades(condition_id=None, limit=100):
    """Trades recientes (globales o de un mercado)."""
    params = {"limit": limit}
    if condition_id:
        params["market"] = condition_id
    return _get(DATA, "/trades", params)


# ---------- Normalizacion ----------

def parse_market(m):
    """Convierte un market de Gamma a un dict normalizado con precios numericos.

    Solo mercados binarios (2 outcomes). Devuelve None si no aplica.
    """
    try:
        outcomes = json.loads(m.get("outcomes") or "[]")
        if len(outcomes) != 2:
            return None
        prices = json.loads(m.get("outcomePrices") or "[]")
        tokens = json.loads(m.get("clobTokenIds") or "[]")
        if len(prices) != 2 or len(tokens) != 2:
            return None
        yes = float(prices[0])
        no = float(prices[1])
        return {
            "id": m.get("id"),
            "question": m.get("question"),
            "slug": m.get("slug"),
            "condition_id": m.get("conditionId"),
            "yes_token": tokens[0],
            "no_token": tokens[1],
            "category": m.get("category"),
            "volume": float(m.get("volume") or 0),
            "liquidity": float(m.get("liquidity") or 0),
            "open_interest": float(m.get("openInterest") or 0),
            "end_date": m.get("endDate"),
            "active": 1 if m.get("active") else 0,
            "closed": 1 if m.get("closed") else 0,
            "yes": yes,
            "no": no,
            "sum_price": round(yes + no, 4),
            "spread": round(abs(yes + no - 1.0), 4),
        }
    except (ValueError, TypeError):
        return None


def fetch_top_binary_markets(n=200):
    """Trae los N mercados binarios activos con mas volumen."""
    out = []
    for offset in range(0, n, 100):
        batch = fetch_markets(limit=100, offset=offset)
        for m in batch:
            p = parse_market(m)
            if p is not None:
                out.append(p)
        time.sleep(0.3)
    return out
