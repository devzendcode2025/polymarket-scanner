#!/usr/bin/env python3
"""Analista heuristico (F2): asigna a cada deteccion una PROBABILIDAD estimada,
un nivel de CONFIANZA, un HORIZONTE y una JUSTIFICACION en lenguaje natural.

Reglas 100% numericas y transparentes (sin LLM). Las probabilidades son
estimaciones del modelo basadas en heuristica de mercado, NO asesoria
financiera ni garantias de resultado.

Cada senal enriquece el dict original con:
  - prob:      int 0-100 (probabilidad estimada de que la senal funcione)
  - confianza: "alta" | "media" | "baja"
  - horizonte: "24h" | "72h" | "1sem"
  - razon:     texto corto con la justificacion numerica
  - url:       link directo al mercado en Polymarket ("" si no hay slug)
"""

URL_BASE = "https://polymarket.com/market/"


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _url(slug):
    return f"{URL_BASE}{slug}" if slug else ""


# ---------- Mispricing ----------

def analizar_mispricing(d):
    desvio = d.get("desvio", 0)
    vol = d.get("volumen", 0)
    liq = d.get("liquidez") or 0
    # Arbitraje binario: la convergencia a Yes+No=1 es esperable si hay liquidez.
    prob = _clamp(75 + desvio * 400, 75, 95)          # desvio 0.03 -> 87%, 0.05 -> 95%
    if vol < 20_000:
        prob = _clamp(prob - 10, 60, 95)              # poca liquidez => menos convergencia
    if desvio >= 0.05:
        conf = "alta"
    elif desvio >= 0.03:
        conf = "media"
    else:
        conf = "baja"
    if vol >= 50_000 and desvio >= 0.04:
        conf = "alta"
    # v0.8.2: libro sin profundidad -> el desvio puede ser ruido de ordenes
    # ausentes, no arbitraje real. Se degrada la confianza (no se elimina:
    # el dato sigue siendo cierto, solo pesa menos).
    if liq and liq < 10_000 and vol < 20_000:
        conf = "baja"
    horizonte = "24h" if desvio >= 0.04 else "72h"
    liq_txt = f" y ${liq:,.0f} de liquidez en el libro" if liq else ""
    razon = (
        f"Yes+No = {d.get('sum', 0)} se desvía {desvio * 100:.1f} puntos de 1.0 "
        f"en un mercado con ${vol:,.0f} de volumen{liq_txt}. En mercados binarios con "
        f"liquidez, este tipo de desvío tiende a cerrarse: {d.get('direccion', '')}."
    )
    return {**d, "prob": int(prob), "confianza": conf, "horizonte": horizonte,
            "razon": razon, "url": _url(d.get("slug"))}


# ---------- Ballenas ----------

def analizar_ballena(d):
    usd = d.get("usd", 0)
    vol = d.get("volumen_mercado") or 0
    side = str(d.get("side", "")).upper()
    lado = "compra" if side == "BUY" else "venta"
    if vol > 0:
        ratio = usd / vol
        fuerza = min(ratio * 100 * 100, 30)           # 5% del vol -> +10 pts; 30%+ -> +30
        prob = _clamp(50 + fuerza, 52, 80)
        razon = (
            f"Trade de {lado} por ${usd:,.0f} en '{d.get('outcome', '')}' = "
            f"{ratio * 100:.1f}% del volumen del mercado (${vol:,.0f}). "
            f"Órdenes de este tamaño relativo suelen mover el precio en el corto plazo."
        )
    else:
        prob = _clamp(52 + usd / 1000 * 1.5, 52, 70)  # sin volumen de ref: escala por monto
        razon = (
            f"Trade de {lado} por ${usd:,.0f} en '{d.get('outcome', '')}'. "
            f"Monto alto en una sola orden: señal de convicción de un operador grande."
        )
    if (usd >= 5000 and (vol <= 0 or usd / vol >= 0.05)) or usd >= 10_000:
        conf = "alta"
    elif usd >= 2000:
        conf = "media"
    else:
        conf = "baja"
    horizonte = "24h" if conf in ("alta", "media") else "72h"
    return {**d, "prob": int(prob), "confianza": conf, "horizonte": horizonte,
            "razon": razon, "url": _url(d.get("slug"))}


# ---------- Momentum ----------

def analizar_momentum(d):
    cambio = abs(d.get("cambio_pct", 0))
    vol = d.get("volumen", 0)
    # Continuacion a corto plazo, conservador (la regresion a la media es comun).
    prob = _clamp(50 + cambio, 55, 72)                # 5% -> 55%, 15% -> 65%, 22%+ -> 72%
    if cambio >= 15 and vol >= 50_000:
        conf = "alta"
    elif cambio >= 10:
        conf = "media"
    else:
        conf = "baja"
    horizonte = "24h"
    razon = (
        f"Yes {d.get('direccion', '').lower()} {cambio:.1f}% vs el scan anterior "
        f"({d.get('yes_antes', 0)} → {d.get('yes_ahora', 0)}) en un mercado con "
        f"${vol:,.0f} de volumen. Movimientos fuertes en ventanas cortas suelen "
        f"continuar las primeras horas, con riesgo de reversión."
    )
    return {**d, "prob": int(prob), "confianza": conf, "horizonte": horizonte,
            "razon": razon, "url": _url(d.get("slug"))}


# ---------- Edge (cross-check de fuentes externas) ----------

def analizar_edge(d):
    edge = abs(d.get("edge", 0))
    n_f = d.get("n_fuentes", 0)
    razon = (
        f"Polymarket paga este mercado a {d.get('prob_poly', 0)}% y el consenso de "
        f"{n_f} fuente(s) externa(s) ({d.get('fuentes_nombres', '')}) lo paga a "
        f"{d.get('consenso', 0)}%: diferencia de {edge:.1f} puntos. "
        f"Cuando el mercado externo está más informado, el precio de Polymarket "
        f"suele converger hacia el consenso. {d.get('direccion', '')}."
    )
    return {**d, "razon": razon, "url": d.get("url") or ""}


# ---------- Orquestador ----------

def enrich(mispricings, ballenas, momentum, edges=None):
    """Aplica el analisis heuristico a las listas de detecciones."""
    if edges is None:
        edges = []
    for e in edges:
        e["fuentes_nombres"] = ", ".join(f["fuente"] for f in e.get("fuentes", []))
        e = analizar_edge(e)
    return (
        [analizar_mispricing(d) for d in mispricings],
        [analizar_ballena(d) for d in ballenas],
        [analizar_momentum(d) for d in momentum],
        [analizar_edge(d) for d in edges],
    )
