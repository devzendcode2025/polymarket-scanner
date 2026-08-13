#!/bin/bash
# Runner canonico de verificaciones del proyecto polymarket-scanner
# Uso: make test   (o bash verificacion/run-all.sh)   (exit 1 si algo falla)
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0

echo "===== [1/5] Sintaxis Python (py_compile) ====="
for f in workspace/scripts/*.py; do
  if python3 -m py_compile "$f"; then echo "OK   $f"; else echo "FAIL $f"; fail=1; fi
done

echo ""
echo "===== [2/5] Sintaxis bash (bash -n) ====="
for f in workspace/scripts/*.sh; do
  if bash -n "$f"; then echo "OK   $f"; else echo "FAIL $f"; fail=1; fi
done

echo ""
echo "===== [3/5] JS del dashboard (node --check) ====="
if command -v node >/dev/null 2>&1; then
  tmp=$(mktemp /tmp/hermes-jsXXXXXX.js)
  python3 - "$tmp" <<'EOF'
import re, sys
html = open("docs/index.html", encoding="utf-8").read()
m = re.search(r"<script>(.*?)</script>", html, re.S)
open(sys.argv[1], "w", encoding="utf-8").write(m.group(1) if m else "// sin script")
EOF
  if node --check "$tmp"; then echo "OK   docs/index.html (JS valido)"; else echo "FAIL docs/index.html (JS)"; fail=1; fi
  rm -f "$tmp"
else
  echo "OK   (node no instalado, check JS omitido)"
fi

echo ""
echo "===== [4/5] .gitignore (git check-ignore + tree limpio) ====="
if bash verificacion/verify_gitignore.sh; then :; else fail=1; fi

echo ""
echo "===== [5/5] Estado del repo (.env protegido, control files, sitio en linea) ====="
if bash verificacion/verify_repo_state.sh; then :; else fail=1; fi

echo ""
if [ $fail -eq 0 ]; then
  echo "RESULTADO: TODO OK"
else
  echo "RESULTADO: HAY FALLOS"
fi
exit $fail
