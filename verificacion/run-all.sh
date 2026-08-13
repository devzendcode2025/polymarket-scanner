#!/bin/bash
# Runner canonico de verificaciones del proyecto polymarket-scanner
# Uso: make test   (o bash verificacion/run-all.sh)   (exit 1 si algo falla)
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0

echo "===== [1/3] Sintaxis Python (py_compile) ====="
for f in workspace/scripts/*.py; do
  if python3 -m py_compile "$f"; then echo "OK   $f"; else echo "FAIL $f"; fail=1; fi
done

echo ""
echo "===== [2/3] .gitignore (git check-ignore + tree limpio) ====="
if bash verificacion/verify_gitignore.sh; then :; else fail=1; fi

echo ""
echo "===== [3/3] Estado del repo (.env protegido, control files, sitio en linea) ====="
if bash verificacion/verify_repo_state.sh; then :; else fail=1; fi

echo ""
if [ $fail -eq 0 ]; then
  echo "RESULTADO: TODO OK"
else
  echo "RESULTADO: HAY FALLOS"
fi
exit $fail
