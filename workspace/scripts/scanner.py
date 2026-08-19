#!/usr/bin/env python3
"""Motor de deteccion de oportunidades.

Tipos de senal:
  - mispricing: Yes + No != 1 (arbitraje binario) en mercados con volumen
  - ballena: trade individual >= umbral USD
  - momentum: cambio de precio vs snapshot anterior del mismo mercado
"""
import time

import categorias


def detect_mispricing(markets, epsilon=0.03, min_volume=5_000):
    """Mercados donde Yes+No se aleja de 1 en mas de epsilon.

    v0.8.2: umbral de volumen bajado de $10k a $5k y barrido ampliado a la
    cola (offset 200-800) donde el desvio es mas probable. Se incluye la
    liquidez del libro para que el analista distinga arbitraje real de ruido.

    Si Yes+No > 1: los dos lados estan caros -> oportunidad de VENDER ambos.
    Si Yes+No < 1: estan baratos -> oportunidad de COMPRAR ambos (si la
    resolucion es binaria pura, el pago garantizado es 1).
    """
    out = []
    for m in markets:
        if m["volume"] < min_volume:
            continue
        if m["spread"] >= epsilon:
            out.append({
                "tipo": "mispricing",
                "market_id": m["id"],
                "question": m["question"],
                "slug": m.get("slug"),
                "tags": m.get("tags") or [],
                "categoria": categorias.clasificar(m["question"]),
                "yes": m["yes"],
                "no": m["no"],
                "sum": m["sum_price"],
                "desvio": m["spread"],
                "volumen": m["volume"],
                "liquidez": m.get("liquidity") or 0,
                "direccion": "VENDER ambos (caros)" if m["sum_price"] > 1 else "COMPRAR ambos (baratos)",
            })
    out.sort(key=lambda d: d["desvio"], reverse=True)
    return out


def detect_mispricing_libro(markets, books, epsilon=0.03, min_volume=5_000):
    """Mispricings REALES calculados del orderbook de ambos tokens (v0.8.2).

    Hallazgo: Gamma normaliza los precios a Yes+No=1 (spread exacto 0 en los
    800 mercados), asi que el detector de mispricings por precios NUNCA podia
    encontrar un desvio: no es eficiencia del mercado, es la fuente. El desvio
    real vive en el libro: mid_yes = (bid+ask)/2 del token Yes, mid_no igual.

    books: {market_id: {bid_yes, ask_yes, bid_no, ask_no}} del orderbook.
    Ademas del desvio del mid, marca arbitraje directo:
      - ask_yes + ask_no < 1  -> comprar ambos lados paga >1 garantizado
      - bid_yes + bid_no  > 1 -> vender ambos lados cobra >1 garantizado
    """
    out = []
    for m in markets:
        if m["volume"] < min_volume:
            continue
        b = books.get(m["id"])
        if not b:
            continue
        mid_yes = (b["bid_yes"] + b["ask_yes"]) / 2.0
        mid_no = (b["bid_no"] + b["ask_no"]) / 2.0
        sum_mid = mid_yes + mid_no
        desvio = abs(sum_mid - 1.0)
        # Arbitraje directo con el libro (mas fuerte que el desvio del mid)
        arbitraje = None
        if b["ask_yes"] + b["ask_no"] < 1.0:
            arbitraje = "COMPRAR ambos (garantizado)"
            desvio = max(desvio, 1.0 - b["ask_yes"] - b["ask_no"])
        elif b["bid_yes"] + b["bid_no"] > 1.0:
            arbitraje = "VENDER ambos (garantizado)"
            desvio = max(desvio, b["bid_yes"] + b["bid_no"] - 1.0)
        if desvio < epsilon:
            continue
        out.append({
            "tipo": "mispricing",
            "market_id": m["id"],
            "question": m["question"],
            "slug": m.get("slug"),
            "tags": m.get("tags") or [],
            "categoria": categorias.clasificar(m["question"]),
            "yes": round(mid_yes, 4),
            "no": round(mid_no, 4),
            "sum": round(sum_mid, 4),
            "desvio": round(desvio, 4),
            "volumen": m["volume"],
            "liquidez": m.get("liquidity") or 0,
            "origen": "libro",
            "direccion": arbitraje or (
                "VENDER ambos (caros)" if sum_mid > 1 else "COMPRAR ambos (baratos)"),
        })
    out.sort(key=lambda d: d["desvio"], reverse=True)
    return out


def detect_whales(trades, min_usd=1000, limit=25):
    """Trades individuales grandes (size * precio)."""
    out = []
    for t in trades:
        usd = t.get("usd_value") or 0
        if usd >= min_usd:
            out.append({
                "tipo": "ballena",
                "market_id": t.get("market_id"),
                "titulo": t.get("title"),
                "slug": t.get("slug"),
                "outcome": t.get("outcome"),
                "side": t.get("side"),
                "size": t.get("size"),
                "price": t.get("price"),
                "usd": round(usd, 2),
                "ts": t.get("ts"),
            })
    out.sort(key=lambda d: d["usd"], reverse=True)
    return out[:limit]


def detect_momentum(markets, get_last, max_age_h=24, threshold=0.05):
    """Cambio de precio vs el snapshot anterior del mercado.

    get_last: callable(market_id) -> dict {yes, no, ts} o None.
    Solo compara si el snapshot anterior tiene menos de max_age_h.
    """
    out = []
    now = time.time()
    for m in markets:
        prev = get_last(m["id"])
        if not prev:
            continue
        age_h = (now - prev["ts"]) / 3600
        if age_h > max_age_h:
            continue
        if prev["yes"] == 0:
            continue
        delta = (m["yes"] - prev["yes"]) / prev["yes"]
        if abs(delta) >= threshold:
            out.append({
                "tipo": "momentum",
                "market_id": m["id"],
                "question": m["question"],
                "slug": m.get("slug"),
                "tags": m.get("tags") or [],
                "categoria": categorias.clasificar(m["question"]),
                "yes_antes": round(prev["yes"], 3),
                "yes_ahora": round(m["yes"], 3),
                "cambio_pct": round(delta * 100, 1),
                "direccion": "SUBIDA" if delta > 0 else "BAJADA",
                "volumen": m["volume"],
            })
    out.sort(key=lambda d: abs(d["cambio_pct"]), reverse=True)
    return out[:30]


def build_summary(markets, mispricings, whales, momentum):
    lines = []
    lines.append(f"Mercados activos vistos: {len(markets)}")
    lines.append(f"Mispricings (Yes+No != 1): {len(mispricings)}")
    lines.append(f"Ballenas (trades >= $1k): {len(whales)}")
    lines.append(f"Momentum (cambio >= 5%): {len(momentum)}")
    return "\n".join(lines)
