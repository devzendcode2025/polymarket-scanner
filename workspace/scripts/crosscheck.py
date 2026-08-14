#!/usr/bin/env python3
"""Cross-check de probabilidades con fuentes externas publicas (F3, v0.7.0).

El "dato ganador": si Polymarket paga un mercado a X% y el consenso externo
lo paga a Y% con |X-Y| >= UMBRAL, hay un EDGE (mercado mal pagado).

Fuentes sin autenticacion (verificadas en vivo 2026-08-14):
  - Kalshi    (api.elections.kalshi.com)   -> precios en centavos 0-100
  - Manifold  (api.manifold.markets)       -> probability 0-1
  - PredictIt (www.predictit.org)          -> contratos con margen, bestBuy/bestSell 0-1
  Metaculus quedo fuera (ahora exige cuenta).

Diseno:
  - CACHE de CACHE_MIN minutos en workspace/data/crosscheck_cache.json: el cron
    corre cada minuto, pero las fuentes externas solo se consultan cada 10 min.
  - Matching heuristico por tokens compartidos (>=2 tokens significativos).
    Version 1: simple; se afina en la depuracion posterior.
  - Tolerante a fallos: si una fuente cae, el scan sigue con las demas.
"""
import json
import os
import time
import urllib.request

import categorias

UA = "Mozilla/5.0 (X11; Linux x86_64) polymarket-scanner/0.7"
CACHE_MIN = 10
UMBRAL = 0.08  # 8 puntos de diferencia minima para considerar edge
MAX_POLY = 50  # mercados de Polymarket a comparar (los mas liquidos)

_CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "crosscheck_cache.json"
)


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _fetch_kalshi():
    data = _get("https://api.elections.kalshi.com/trade-api/v2/markets?limit=100")
    out = []
    for m in data.get("markets", []):
        ask = m.get("yes_ask")
        bid = m.get("yes_bid")
        if ask is None and bid is None:
            continue
        prob = ((bid if bid is not None else 0) + (ask if ask is not None else 0)) / 2.0
        out.append({
            "fuente": "Kalshi",
            "titulo": m.get("question") or m.get("ticker", ""),
            "prob": prob,  # centavos = %
            "url": f"https://kalshi.com/markets/{m.get('ticker', '')}",
        })
    return out


def _fetch_manifold():
    data = _get("https://api.manifold.markets/v0/markets?limit=200")
    out = []
    for m in data or []:
        p = m.get("probability")
        if p is None:
            continue
        out.append({
            "fuente": "Manifold",
            "titulo": m.get("question", ""),
            "prob": float(p) * 100.0,
            "url": m.get("url", ""),
        })
    return out


def _fetch_predictit():
    data = _get("https://www.predictit.org/api/marketdata/all/")
    out = []
    for mk in data.get("markets", []):
        for c in mk.get("contracts", []):
            buy = c.get("bestBuyYesCost")
            sell = c.get("bestSellYesCost")
            if buy is None and sell is None:
                continue
            prob = ((buy or 0) + (sell or 0)) / 2.0 * 100.0
            out.append({
                "fuente": "PredictIt",
                "titulo": c.get("shortName") or c.get("name", ""),
                "prob": prob,
                "url": f"https://www.predictit.org/markets/detail/{mk.get('id', '')}",
            })
    return out


def _fetch_todas():
    """Trae las 3 fuentes; cada una falla de forma independiente."""
    res = []
    for fn in (_fetch_kalshi, _fetch_manifold, _fetch_predictit):
        try:
            res.extend(fn())
        except Exception:  # noqa: BLE001 - una fuente caida no rompe el scan
            pass
    return res


def _build_doc_freq(fuentes):
    """Frecuencia de cada token en todos los titulos de las fuentes (para IDF)."""
    df = {}
    for f in fuentes:
        for t in categorias.tokens(f["titulo"]):
            df[t] = df.get(t, 0) + 1
    return df


def _match_score(pt, fuente, df):
    """Score de matching: tokens comunes con al menos UNO raro (df<=5) y misma categoria.

    Evita falsos positivos tipo 'Chargers NFL' vs 'MLB entradas extra'
    (comparten solo palabras genericas como games/season/regular).
    """
    ft = categorias.tokens(fuente["titulo"])
    comunes = pt & ft
    if len(comunes) < 2:
        return 0
    raros = {t for t in comunes if df.get(t, 0) <= 5}
    if not raros:
        return 0
    if categorias.clasificar(fuente["titulo"]) != categorias.clasificar(
        fuente.get("_poly_question", fuente["titulo"])):
        return 0
    return len(comunes) + len(raros) * 2  # prioriza tokens raros compartidos


def get_edges(markets_poly, max_edges=20):
    """Compara mercados de Polymarket contra fuentes externas. Devuelve edges.

    markets_poly: lista de dicts {question, slug, yes, volume}.
    Edge positivo = Polymarket BARATO (el consenso externo paga mas).
    """
    # Cache
    now = time.time()
    try:
        with open(_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
        if now - cache.get("ts", 0) < CACHE_MIN * 60:
            return cache.get("edges", [])
    except (OSError, ValueError):
        pass

    fuentes = _fetch_todas()
    df = _build_doc_freq(fuentes)
    # Indice por fuente para busqueda rapida
    por_fuente = {}
    for f in fuentes:
        por_fuente.setdefault(f["fuente"], []).append(f)

    edges = []
    for m in markets_poly[:MAX_POLY]:
        pt = categorias.tokens(m["question"])
        if not pt:
            continue
        fuentes_match = []
        for nombre, lista in por_fuente.items():
            mejor = None
            for f in lista:
                f["_poly_question"] = m["question"]
                s = _match_score(pt, f, df)
                if s > 0 and (mejor is None or s > mejor[0]):
                    mejor = (s, f)
            if mejor:
                fuentes_match.append(mejor[1])
        if not fuentes_match:
            continue
        consenso = sum(f["prob"] for f in fuentes_match) / len(fuentes_match)
        edge = consenso - m["yes"] * 100.0
        if abs(edge) < UMBRAL * 100:
            continue
        conf = "alta" if abs(edge) >= 15 and len(fuentes_match) >= 2 else (
            "media" if abs(edge) >= 8 else "baja")
        prob_conv = min(85, 55 + abs(edge) * 1.2)
        direccion = "Polymarket BARATO (comprar Sí)" if edge > 0 else "Polymarket CARO (comprar No)"
        edges.append({
            "tipo": "edge",
            "question": m["question"],
            "slug": m.get("slug"),
            "url": f"https://polymarket.com/market/{m['slug']}" if m.get("slug") else "",
            "prob_poly": round(m["yes"] * 100.0, 1),
            "consenso": round(consenso, 1),
            "edge": round(edge, 1),
            "direccion": direccion,
            "fuentes": fuentes_match,
            "n_fuentes": len(fuentes_match),
            "categoria": categorias.clasificar(m["question"]),
            "prob": int(prob_conv),
            "confianza": conf,
            "horizonte": "72h" if conf == "alta" else "1sem",
        })
    edges.sort(key=lambda e: abs(e["edge"]), reverse=True)

    # Guardar cache (con los titulos de fuentes crudos)
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": now, "edges": edges}, f, ensure_ascii=False)
    except OSError:
        pass
    return edges[:max_edges]
