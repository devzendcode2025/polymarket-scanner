#!/bin/bash
# Verificacion de regresion: .gitignore del proyecto
# Parte de verificacion/run-all.sh — no ejecutar suelto salvo debug
set -u
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ" || { echo "FAIL: no existe $PROJ"; exit 1; }
fail=0

echo "== 1) .gitignore presente =="
[ -f .gitignore ] && echo "OK .gitignore existe" || { echo "FAIL"; exit 1; }

echo "== 2) Patrones ignorados (git check-ignore) =="
for p in workspace/data/polymarket.db workspace/reports/technical/scan_x.json __pycache__/x.pyc .env; do
  if git check-ignore -q "$p"; then echo "OK ignorado: $p"; else echo "FAIL no ignorado: $p"; fail=1; fi
done

echo "== 3) Working tree limpio (sin no-rastreados no ignorados) =="
out=$(git status --porcelain)
if [ -z "$out" ]; then echo "OK limpio"; else echo "FAIL sucio:"; echo "$out"; fail=1; fi

echo "== 4) Archivos versionados esperados =="
expected=".gitignore CHAT_RESUMEN.md MEMORIA_PROYECTO.md README_PROYECTO.md REGLAS_PROYECTO.md TAREAS.md workspace/scripts/db.py workspace/scripts/polymarket_client.py workspace/scripts/run_scan.py workspace/scripts/scanner.py workspace/web/dashboard.html"
missing=0
for f in $expected; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 || { echo "FALTA en repo: $f"; missing=1; }
done
[ $missing -eq 0 ] && echo "OK: todos los archivos esperados versionados"

echo "== 5) .env no versionado =="
git ls-files | grep -q "^\.env$" && { echo "FAIL: .env versionado"; fail=1; } || echo "OK .env excluido"

if [ $fail -eq 0 ]; then echo ""; echo "gitignore: OK"; else echo "gitignore: FALLO"; fi
exit $fail
