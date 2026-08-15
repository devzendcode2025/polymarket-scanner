#!/bin/bash
# Cron cada 1 minuto: scan -> render -> push condicional a GitHub Pages.
# Silencioso si todo normal (patron watchdog): el cron no_agent entrega
# solo lo que se imprime; en exito no se imprime nada.
# Push solo si: hay detecciones nuevas O pasaron >=6 min (limite Pages ~10 builds/h).
set -u
cd /srv/hermes-projects/proyectos/polymarket-scanner || { echo "ERROR: no existe el proyecto"; exit 1; }

# Lock a prueba de huerfanos: flock del kernel se libera solo si el proceso
# muere (SIGKILL incluido). El mkdir anterior dejo un lock huerfano el
# 2026-08-14 y el cron corrio "ok" sin hacer nada durante ~24h.
LOCK=/tmp/polymarket-scan.lock
exec 9>"$LOCK"
if ! flock -n 9; then
  exit 0  # otro scan en curso, saltar este tick
fi
trap 'rm -f "$LOCK"' EXIT

# 1) Scan (silencioso) + poda de disco
if ! python3 workspace/scripts/run_scan.py --quiet; then
  echo "ERROR: scan fallo a las $(date -u +%H:%M:%S) UTC"
  exit 1
fi

# 2) Regenerar el dashboard (data.json con detecciones del pipeline)
if ! python3 workspace/scripts/render_dashboard.py > /dev/null 2>&1; then
  echo "ERROR: render fallo"
  exit 1
fi

# 2b) App del dashboard (template fijo con JS en vivo) -> docs/
cp -f workspace/web/dashboard.html docs/index.html 2>/dev/null || true

# 3) Decidir push
LAST_PUSH=workspace/data/.last_push
now=$(date +%s)
last=0
[ -f "$LAST_PUSH" ] && last=$(cat "$LAST_PUSH" 2>/dev/null || echo 0)

det=$(python3 - <<'EOF'
import glob, json, os
files = sorted(glob.glob(os.path.join("workspace", "reports", "technical", "scan_*.json")))
if not files:
    print(0)
else:
    r = json.load(open(files[-1], encoding="utf-8"))
    print(len(r.get("ballenas", [])) + len(r.get("mispricings", [])) + len(r.get("momentum", [])))
EOF
)

if [ "$det" -gt 0 ] || [ $((now - last)) -ge 360 ]; then
  git add docs/ > /dev/null 2>&1
  if git diff --cached --quiet; then
    : # sin cambios en docs, no commitear
  else
    git commit -q -m "scan $(date -u +%Y%m%d_%H%M%S)" && git push -q && echo "$now" > "$LAST_PUSH"
  fi
fi

exit 0
