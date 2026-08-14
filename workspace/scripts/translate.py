#!/usr/bin/env python3
"""Traduccion de titulos de mercados al espanol usando DeepSeek (F4, v0.6.0).

Diseno de costo:
  - CACHE en SQLite (tabla translations): solo se traducen titulos NUEVOS.
  - Limite por corrida (MAX_NUEVOS_POR_CORRIDA): el cron de 1 min jamas hace
    rafagas; el primer dia consume unas decenas de llamadas, despues ~0.
  - Fallback robusto: si no hay clave o la API falla, devuelve traducciones
    vacias y el scan sigue con el titulo original (nunca rompe el pipeline).

La clave se lee de (en orden): env DEEPSEEK_API_KEY -> .env del perfil de
Hermes -> .env del proyecto. Nunca se imprime ni se versiona.
"""
import json
import os
import urllib.request

import db

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
MODELO = "deepseek-chat"
MAX_NUEVOS_POR_CORRIDA = 30

_PROJ_ENV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"
)
_HERMES_ENV = "/home/devzendcode/.hermes/profiles/codigo/.env"


def _find_key():
    """Localiza la clave DeepSeek sin exponerla."""
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


def _llamada_deepseek(textos):
    """Traduce una lista de textos con DeepSeek. Devuelve {texto: traduccion} o None."""
    key = _find_key()
    if not key:
        return None
    prompt = (
        "Traduce al español los siguientes títulos de mercados de predicción. "
        "Devuelve SOLO un JSON con el formato {\"0\": \"traducción\", \"1\": \"...\"}. "
        "Sin explicaciones. Conserva nombres propios, siglas y cifras (ej. ETF, NFL, Fed, $1B).\n\n"
        + "\n".join(f"{i}: {t}" for i, t in enumerate(textos))
    )
    body = json.dumps({
        "model": MODELO,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2000,
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
        return {textos[int(k)]: v for k, v in obj.items()}
    except Exception:  # noqa: BLE001 - el fallback es el texto original
        return None


def traducir(conn, textos, max_nuevos=MAX_NUEVOS_POR_CORRIDA):
    """Traduce textos no vistos (cache SQLite). Devuelve {texto: es}."""
    textos = [t for t in dict.fromkeys(textos) if t]
    if not textos:
        return {}
    out = db.get_translations(conn, textos)
    faltantes = [t for t in textos if t not in out]
    if faltantes:
        nuevos = faltantes[:max_nuevos]
        res = _llamada_deepseek(nuevos)
        if res:
            db.save_translations(conn, res)
            out.update(res)
    return out
