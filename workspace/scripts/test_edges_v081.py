#!/usr/bin/env python3
"""Test del recall boost v0.8.1: mide fuentes, candidatos y edges reales."""
import json, os, sys, time
sys.path.insert(0, "/srv/hermes-projects/proyectos/polymarket-scanner/workspace/scripts")

import polymarket_client as pc
import crosscheck
import db

WS = "/srv/hermes-projects/proyectos/polymarket-scanner/workspace"
DB = os.path.join(WS, "data", "polymarket.db")
conn = db.init_db(DB)

t0 = time.time()
print("== Fuentes (paginadas) ==")
fuentes = crosscheck._fetch_todas()
por_f = {}
for f in fuentes:
    por_f[f["fuente"]] = por_f.get(f["fuente"], 0) + 1
for k, v in sorted(por_f.items()):
    print(f"  {k}: {v} mercados")
print(f"  total: {len(fuentes)} (fetch {time.time()-t0:.1f}s)")

print("\n== Mercados Polymarket ==")
markets = pc.fetch_top_binary_markets(200)
cola = pc.fetch_top_binary_markets(200, offset=200)
poly = [{"question": m["question"], "slug": m.get("slug"), "yes": m["yes"], "volume": m["volume"]}
        for m in markets + cola]
print(f"  top: {len(markets)} + cola: {len(cola)} = {len(poly)} (MAX_POLY={crosscheck.MAX_POLY})")

print("\n== Candidatos (v0.8.1) ==")
df = crosscheck._build_doc_freq(fuentes)
for f in fuentes:
    f.setdefault("_tokens", __import__("categorias").tokens(f["titulo"]))
    f.setdefault("_np", crosscheck._nombres_propios(f["titulo"]))
    f.setdefault("_bg", crosscheck._bigramas_np(f["titulo"]))
por_fuente = {}
for f in fuentes:
    por_fuente.setdefault(f["fuente"], []).append(f)

TOP_K = 2
candidatos, vistos = [], set()
for m in poly[:crosscheck.MAX_POLY]:
    pt = __import__("categorias").tokens(m["question"])
    if not pt:
        continue
    for nombre, lista in por_fuente.items():
        puntuados = []
        for f in lista:
            f["_poly_question"] = m["question"]
            s = crosscheck._match_score_v2(pt, f, df)
            if s > 0:
                puntuados.append((s, f))
        puntuados.sort(key=lambda x: -x[0])
        for s, f in puntuados[:TOP_K]:
            key = crosscheck._par_key(m["question"], f["titulo"])
            if key in vistos:
                continue
            vistos.add(key)
            candidatos.append({"key": key, "poly_q": m["question"], "fuente_titulo": f["titulo"],
                               "poly": m, "fuente": f, "score": s})
print(f"  candidatos totales: {len(candidatos)}")
en_cache = sum(1 for c in candidatos if db.get_confirmacion(conn, c["key"]) in ("SI", "NO"))
nuevos = len(candidatos) - en_cache
print(f"  ya confirmados en caché: {en_cache} | nuevos para DeepSeek: {nuevos}")

print("\n== Edges finales (con confirmación DeepSeek) ==")
edges = crosscheck.get_edges(conn, poly)
print(f"  EDGES: {len(edges)} (antes: 2)")
for e in edges:
    print(f"  - {e['edge']:+.1f} pts | {e['question'][:70]}")
    print(f"      poly {e['prob_poly']}% vs consenso {e['consenso']}% | {e['direccion']} | n_fuentes {e['n_fuentes']}")
    for f in e.get("fuentes", []):
        print(f"      * {f['fuente']} | {f['titulo'][:60]} | {f['prob']}")
print(f"\nTiempo total: {time.time()-t0:.1f}s")
