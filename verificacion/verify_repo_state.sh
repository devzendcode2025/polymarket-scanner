#!/bin/bash
# Verificacion de estado del repo: .env protegido (sin imprimir secretos),
# control files versionados, sitio publico en linea.
# Parte de verificacion/run-all.sh — no ejecutar suelto salvo debug.
set -u
PROJ="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ" || exit 1
fail=0

echo "== 1) .env existe, permisos 600, formato valido =="
if [ -f .env ]; then
  perms=$(stat -c '%a' .env)
  [ "$perms" = "600" ] && echo "OK .env permisos $perms" || { echo "FAIL .env permisos $perms (esperado 600)"; fail=1; }
  tok=$(cut -d= -f2 .env)
  case "$tok" in
    ghp_*) len=${#tok}; [ "$len" -ge 36 ] && echo "OK token formato ghp_* (longitud $len, valor no mostrado)" || { echo "FAIL longitud token $len"; fail=1; } ;;
    *) echo "FAIL formato token (no empieza con ghp_)"; fail=1 ;;
  esac
else
  echo "FAIL .env no existe"; fail=1
fi

echo "== 2) Control files versionados =="
for f in README_PROYECTO.md MEMORIA_PROYECTO.md CHAT_RESUMEN.md TAREAS.md REGLAS_PROYECTO.md; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 && echo "OK versionado: $f" || { echo "FAIL falta en git: $f"; fail=1; }
done

echo "== 3) Sitio publico en linea =="
code=$(curl -s -o /dev/null -w "%{http_code}" -m 15 https://devzendcode2025.github.io/polymarket-scanner/ 2>/dev/null)
[ "$code" = "200" ] && echo "OK sitio HTTP $code" || { echo "FAIL sitio HTTP $code"; fail=1; }

if [ $fail -eq 0 ]; then echo ""; echo "repo-state: OK"; else echo "repo-state: FALLO"; fi
exit $fail
