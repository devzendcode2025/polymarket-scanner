#!/usr/bin/env python3
"""Narrativa DeepSeek (F4): justificaciones narradas de las mejores senales.

Diseno de costo (misma filosofia que translate.py):
  - CACHE en SQLite (tabla narrativas): clave = tipo + identidad + datos clave.
    Si la senal no cambio (mismo edge, misma ballena, mismo momentum), la
    narrativa se reutiliza -> ~0 llamadas en mercados quietos.
  - Limite por corrida: MAX_POR_CORRIDA (5). El cron de 1 min jamas hace
    rafagas: solo se narran senales NUEVAS.
  - Fallback robusto: si no hay clave o falla la API, la senal queda con su
    razon heuristica (la tarjeta del dashboard la muestra igual).

La clave se lee igual que en translate.py: env -> .env del perfil -> .env del
proyecto. Nunca se imprime ni se versiona.
"""
import json
import os
import urllib.request

import db

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODELO = "deepseek-chat"
MAX_POR_CORRIDA = 5

_PROJ_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)
_HERMES_ENV = "/home/devzendcode/.hermes/profiles/codigo/.env"


def _find_key():
    k = os.environ.get("DEEPSEEK_API_KEY")
    if k:
        return k
    for path in (_HERMES_ENV, _PROJ_ENV):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DEEPSEEK_API_KEY="):
                        return line.strip().split("=", 1)[1]
        except OSError:
            continue
    return None


def _llamada_deepseek(senales):
    """Genera narrativas para una lista de senales. Devuelve {key: texto} o None."""
    key = _find_key()
    if not key:
        return None
    lineas = []
    for i, s in enumerate(senales):
        datos = json.dumps(s["_datos"], ensure_ascii=False)
        lineas.append(f"{i}: {s['_tipo'].upper()} | {datos}")
    prompt = (
        "Eres un analista de mercados de prediccion. Para cada senal, escribe una "
        "narracion de 2 a 3 frases en espanol que explique POR QUE es una oportunidad, "
        "usando los numeros reales (edge en puntos, consenso externo, monto del trade, "
        "cambio porcentual, desvio, etc.). Tono profesional de boletin de trading, "
        "sin prometer resultados. Cierra con una nota breve de riesgo si aplica "
        "(ej. 'riesgo: poca liquidez'). NO es asesoria financiera, no lo digas en el "
        "texto. Devuelve SOLO un JSON con formato {\"0\": \"texto\", \"1\": \"...\"}. "
        "Sin explicaciones ni comillas externas.\n\n"
        + "\n".join(lineas)
    )
    body = json.dumps({
        "model": MODELO,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5,
        "max_tokens": 1500,
    }).encode()
    req = urllib.request.Request(
        DEEPSEEK_URL, data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
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
                out[senales[idx]["_key"]] = v.strip()
            except (KeyError, ValueError):
                continue
        return out
    except Exception:  # noqa: BLE001 - el fallback es la razon heuristica
        return None


# ---------- Claves de cache y datos para el prompt ----------

def _datos_senal(d):
    """Devuelve (tipo, key, datos) para una senal ya enriquecida por analyst."""
    identidad = d.get("slug") or d.get("url") or d.get("question") or d.get("titulo") or ""
    if d.get("tipo") == "edge":
        key = f"edge:{identidad}:{d.get('edge', 0)}:{d.get('consenso', 0)}"
        datos = {
            "evento": d.get("question_es") or d.get("question"),
            "polymarket_paga": d.get("prob_poly"),
            "consenso_externo": d.get("consenso"),
            "diferencia_puntos": d.get("edge"),
            "direccion": d.get("direccion"),
            "fuentes": d.get("fuentes_nombres"),
        }
        return "edge", key, datos
    if d.get("tipo") == "ballena":
        key = f"ballena:{identidad}:{round(d.get('usd', 0))}:{d.get('side', '')}"
        datos = {
            "evento": d.get("titulo_es") or d.get("titulo"),
            "lado": "compra" if str(d.get("side", "")).upper() == "BUY" else "venta",
            "monto_usd": d.get("usd"),
            "outcome": d.get("outcome"),
            "volumen_mercado_usd": d.get("volumen_mercado"),
        }
        return "ballena", key, datos
    if d.get("tipo") == "momentum":
        key = f"momentum:{identidad}:{round(d.get('cambio_pct', 0), 1)}"
        datos = {
            "evento": d.get("question_es") or d.get("question"),
            "cambio_pct": d.get("cambio_pct"),
            "direccion": d.get("direccion"),
            "yes_antes": d.get("yes_antes"),
            "yes_ahora": d.get("yes_ahora"),
            "volumen_usd": d.get("volumen"),
        }
        return "momentum", key, datos
    # mispricing
    key = f"mispricing:{identidad}:{round(d.get('desvio', 0), 4)}"
    datos = {
        "evento": d.get("question_es") or d.get("question"),
        "yes_mas_no": d.get("sum"),
        "desvio": round(d.get("desvio", 0) * 100, 1),
        "direccion": d.get("direccion"),
        "volumen_usd": d.get("volumen"),
    }
    return "mispricing", key, datos


# ---------- Seleccion de top senales ----------

_PESO_CONF = {"alta": 100, "media": 50, "baja": 0}


def seleccionar_top(mispricings, ballenas, momentum, edges, n=5):
    """Top-N senales por relevancia (confianza + prob + bonus de tipo)."""
    todas = []
    for d in mispricings + ballenas + momentum + edges:
        tipo, key, datos = _datos_senal(d)
        bonus = 20 if tipo == "edge" else (10 if tipo == "ballena" else 0)
        score = _PESO_CONF.get(d.get("confianza", "baja"), 0) + (d.get("prob") or 0) + bonus
        todas.append((score, d, tipo, key, datos))
    todas.sort(key=lambda x: x[0], reverse=True)
    return [{"_tipo": t, "_key": k, "_datos": dt, "_senal": d}
            for _, d, t, k, dt in todas[:n]]


# ---------- Orquestador ----------

def narrar(conn, seleccionadas):
    """Genera y cachea narrativas para las senales seleccionadas. Las muta in-place.

    seleccionadas: salida de seleccionar_top(). Agrega d["narrativa"] a cada senal.
    """
    conn = conn or db.init_db(os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "workspace", "data", "polymarket.db",
    ))
    pendientes = []
    for item in seleccionadas:
        texto = db.get_narrativa(conn, item["_key"])
        if texto:
            item["_senal"]["narrativa"] = texto
        else:
            pendientes.append(item)
    if not pendientes:
        return
    nuevos = pendientes[:MAX_POR_CORRIDA]
    res = _llamada_deepseek(nuevos)
    if res:
        db.save_narrativas(conn, res)
        for item in nuevos:
            if item["_key"] in res:
                item["_senal"]["narrativa"] = res[item["_key"]]
