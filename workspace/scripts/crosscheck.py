#!/usr/bin/env python3
"""Cross-check de probabilidades con fuentes externas publicas (F3, v0.8.0).

El "dato ganador": si Polymarket paga un mercado a X% y el consenso externo
lo paga a Y% con |X-Y| >= UMBRAL, hay un EDGE (mercado mal pagado).

Fuentes sin autenticacion (verificadas en vivo 2026-08-14):
  - Kalshi    (api.elections.kalshi.com)   -> precios en centavos 0-100
  - Manifold  (api.manifold.markets)       -> probability 0-1
  - PredictIt (www.predictit.org)          -> contratos con margen, bestBuy/bestSell 0-1
  Metaculus quedo fuera (ahora exige cuenta).

Depuracion del matching (v0.8.0, 2026-08-15):
  - v1 (v0.7.0): >=2 tokens raros compartidos + misma categoria -> precision
    alta, recall bajo (1-2 edges/dia).
  - v2: candidatos laxos (>=1 token raro compartido) + CONFIRMACION DeepSeek
    en batch ("mismo evento SI/NO") con cache SQLite (tabla edge_confirm).
    DeepSeek distingue 'mismo evento' de 'mismo tema' (p.ej. Alcaraz en el
    Cincinnati Open vs Alcaraz en el US Open NO son el mismo evento).
  - Fallback si DeepSeek no esta disponible: criterio estricto de v1 (nunca
    degrada la precision del panel publico).

Diseno:
  - CACHE de CACHE_MIN minutos en workspace/data/crosscheck_cache.json para los
    FETCHES de fuentes (10 min); las confirmaciones SI/NO viven en SQLite.
  - Tolerante a fallos: si una fuente cae, el scan sigue con las demas.
"""
import hashlib
import json
import os
import re
import time
import urllib.request

import categorias
import db
from translate import _find_key

UA = "Mozilla/5.0 (X11; Linux x86_64) polymarket-scanner/0.8"
CACHE_MIN = 10
UMBRAL = 0.08  # 8 puntos de diferencia minima para considerar edge
MAX_POLY = 200  # mercados de Polymarket a comparar (los 200 ya se fetchan)
MAX_CANDIDATOS = 60  # pares maximo por corrida para confirmar con DeepSeek

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODELO = "deepseek-chat"

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


def _par_key(poly_q, fuente_titulo):
    """Clave estable del par para el cache de confirmaciones."""
    return hashlib.sha1(f"{poly_q.strip().lower()}|{fuente_titulo.strip().lower()}".encode()).hexdigest()


# Palabras capitalizadas por estilo de titulo que NO son nombres propios.
_TITULO_FALSOS = set("""
score half under over exact will open close closing winner winning won win lose loses
first second third fourth final quarter season series game games match matches round
title champion championship award awards case city state county governor senate senator
president election primary general party democrat democratic republican nominee
candidate candidates total points point goals goal team teams home away night morning
afternoon evening today tonight tomorrow august september october november december
january february march april june july monday tuesday wednesday thursday friday
saturday sunday new york north south east west against during after before between
where while until since because would could should might must have been being going
come comes coming take takes taken make makes made get gets getting year month week
day hour minutes seconds lead leads leading top bottom best worst latest current
previous next last another every other some any both each few own same such only also
than then else more most much many how what when which where who whom whose this that
these those there their they them with without about into onto upon from your our their
""".split())


def _nombres_propios(titulo):
    """Tokens capitalizados en el original (candidatos a nombre propio).

    Filtra: longitud <5, primera palabra del titulo (estilo 'Will...'),
    STOP/_GENERICOS del pipeline y capitalizaciones de titulo comunes.
    """
    out = set()
    primera = True
    for tok in re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ][A-Za-zÁÉÍÓÚÑáéíóúñ'-]*", titulo or ""):
        t = tok.lower()
        if (not primera and len(t) >= 5 and tok[0].isupper() and not tok[1:].isupper()
                and t not in categorias._STOP and t not in categorias._GENERICOS
                and t not in _TITULO_FALSOS):
            out.add(t)
        primera = False
    return out


def _match_score_v2(pt, fuente, df):
    """Candidato hibrido: (a) >=1 nombre propio comun, o (b) >=2 tokens comunes con raro.

    Los nombres propios son los mejores identificadores de evento (misma persona,
    equipo, pais, torneo); el LLM confirma luego la instancia exacta (mismo
    partido/fecha), asi que aqui se permite recall amplio. El ruido de 1 token
    unico generico ('score' cruzando golf con futbol) queda fuera.
    """
    pn = _nombres_propios(fuente.get("_poly_question") or "")
    fn = _nombres_propios(fuente["titulo"])
    comunes_np = pn.intersection(fn)
    if comunes_np:
        return 3 * len(comunes_np)

    ft = categorias.tokens(fuente["titulo"])
    comunes = pt.intersection(ft)
    if len(comunes) < 2:
        return 0
    raros = {t for t in comunes if df.get(t, 0) <= 5}
    if not raros:
        return 0
    return len(comunes) + len(raros) * 2


def _confirmar_con_deepseek(conn, pares):
    """Confirma con DeepSeek en batch cuales pares son el MISMO evento.

    pares: lista de dicts {key, poly_q, fuente_titulo}. Devuelve dict key->'SI'/'NO'.
    Usa cache SQLite; solo consulta pares nuevos (max MAX_CANDIDATOS por corrida).
    Devuelve {} si no hay clave o falla la API (el llamador usa el fallback estricto).
    """
    key_api = _find_key()
    if not key_api:
        return {}

    pendientes = []
    for p in pares:
        res = db.get_confirmacion(conn, p["key"])
        if res in ("SI", "NO"):
            continue
        pendientes.append(p)
    if not pendientes:
        return {}

    nuevos = pendientes[:MAX_CANDIDATOS]
    lineas = [f"{i}: POLY: \"{p['poly_q']}\" | EXT: \"{p['fuente_titulo']}\""
              for i, p in enumerate(nuevos)]
    prompt = (
        "Eres un indexador de mercados de prediccion. Para cada PAR de titulos, "
        "decide si se refieren al MISMO EVENTO (misma competicion o partido o "
        "eleccion o persona Y la misma instancia/fecha) o solo al mismo tema.\n"
        "Ejemplo MISMO EVENTO: \"Will Alcaraz win the Cincinnati Open?\" y "
        "\"Alcaraz to win Cincinnati Open title\".\n"
        "Ejemplo NO (mismo tema, distinto evento): \"Will Alcaraz win the "
        "Cincinnati Open?\" y \"Will Alcaraz win the US Open?\" (torneos distintos).\n"
        "Responde SOLO con un JSON: {\"0\": \"SI\", \"1\": \"NO\", ...}. Sin explicaciones.\n\n"
        + "\n".join(lineas)
    )
    body = json.dumps({
        "model": MODELO,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max(400, len(nuevos) * 15 + 100),  # el JSON de salida crece con los pares
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key_api}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
        content = data["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        obj = json.loads(content)
        out = {}
        for k, v in obj.items():
            try:
                idx = int(k)
                res = str(v).strip().upper()
                if res in ("SI", "NO"):
                    out[nuevos[idx]["key"]] = res
            except (KeyError, ValueError):
                continue
        if out:
            db.save_confirmaciones(conn, out)
        return out
    except Exception:  # noqa: BLE001 - fallback estricto
        return {}


def get_edges(conn, markets_poly, max_edges=20):
    """Compara mercados de Polymarket contra fuentes externas. Devuelve edges.

    conn: conexion SQLite (para el cache de confirmaciones SI/NO).
    markets_poly: lista de dicts {question, slug, yes, volume}.
    Edge positivo = Polymarket BARATO (el consenso externo paga mas).
    """
    # Cache de fetches (10 min)
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
    por_fuente = {}
    for f in fuentes:
        por_fuente.setdefault(f["fuente"], []).append(f)

    # 1) Candidatos laxos (v2): mejor candidato por fuente para cada mercado Poly
    candidatos = []
    for m in markets_poly[:MAX_POLY]:
        pt = categorias.tokens(m["question"])
        if not pt:
            continue
        for nombre, lista in por_fuente.items():
            mejor = None
            for f in lista:
                f["_poly_question"] = m["question"]
                s = _match_score_v2(pt, f, df)
                if s > 0 and (mejor is None or s > mejor[0]):
                    mejor = (s, f)
            if mejor:
                candidatos.append({
                    "key": _par_key(m["question"], mejor[1]["titulo"]),
                    "poly_q": m["question"],
                    "fuente_titulo": mejor[1]["titulo"],
                    "poly": m,
                    "fuente": mejor[1],
                    "score": mejor[0],
                })

    # 2) Confirmar con DeepSeek (cache SQLite). SIN confirmacion NO hay edge:
    #    decision firme del proyecto = precision absoluta en el panel publico.
    #    (v1 tenia un fallback por tokens que dejo pasar falsos positivos como
    #    "Taylor Swift GRAMMY" vs "gira en Nueva Zelanda"; se elimino.)
    confirmados = {}
    para_confirmar = []
    for c in candidatos:
        res = db.get_confirmacion(conn, c["key"])
        if res == "SI":
            confirmados[c["key"]] = c
        elif res != "NO":
            para_confirmar.append(c)
    if para_confirmar:
        res = _confirmar_con_deepseek(conn, para_confirmar)
        for c in para_confirmar:
            if res.get(c["key"]) == "SI":
                confirmados[c["key"]] = c

    # 3) Agrupar por mercado Poly y construir edges
    por_poly = {}
    for c in confirmados.values():
        por_poly.setdefault(c["poly_q"], []).append(c["fuente"])

    edges = []
    for q, fuentes_match in por_poly.items():
        m = next((x for x in markets_poly[:MAX_POLY] if x["question"] == q), None)
        if m is None:
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
