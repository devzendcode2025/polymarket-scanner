#!/bin/bash
# Backup diario de la base SQLite -> repo privado polymarket-scanner-data.
# Copia consistente via sqlite backup (seguro aunque el scan este corriendo).
# Imprime solo errores (patron watchdog).
set -u
cd /srv/hermes-projects/proyectos/polymarket-scanner || { echo "ERROR: no existe el proyecto"; exit 1; }

SRC=workspace/data/polymarket.db
STAGE=workspace/backups
DATE=$(date +%Y%m%d)
TOKEN=$(cut -d= -f2 .env)
REMOTE="https://devzendcode2025:${TOKEN}@github.com/devzendcode2025/polymarket-scanner-data.git"

[ -f "$SRC" ] || { echo "ERROR: no existe $SRC"; exit 1; }

mkdir -p "$STAGE"

# Copia consistente con sqlite3 backup (via python)
if ! python3 - "$SRC" "$STAGE/polymarket-$DATE.db" <<'EOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
src.backup(dst)
dst.close(); src.close()
print("backup ok")
EOF
then
  echo "ERROR: backup sqlite fallo"
  exit 1
fi

gzip -f "$STAGE/polymarket-$DATE.db"

# Poda local: conservar 30 backups
ls -1t "$STAGE"/polymarket-*.db.gz 2>/dev/null | tail -n +31 | xargs -r rm -f

# Push al repo privado (repo git aislado dentro de backups/, excluido del repo principal)
if [ ! -d "$STAGE/.git" ]; then
  git -C "$STAGE" init -q
  git -C "$STAGE" remote add origin "$REMOTE"
else
  git -C "$STAGE" remote set-url origin "$REMOTE"
fi

git -C "$STAGE" add -A
if git -C "$STAGE" diff --cached --quiet; then
  # nada nuevo que commitear: igual intentar push (por si quedo pendiente)
  git -C "$STAGE" push -q 2>/dev/null || git -C "$STAGE" push -q -u origin main 2>/dev/null || { echo "ERROR: push backup fallo"; exit 1; }
else
  git -C "$STAGE" commit -q -m "backup $DATE"
  git -C "$STAGE" push -q 2>/dev/null || git -C "$STAGE" push -q -u origin main 2>/dev/null || { echo "ERROR: push backup fallo"; exit 1; }
fi

# Poda remota: mantener 30 backups en el repo
git -C "$STAGE" ls-files | sort -r | tail -n +31 | while read -r f; do
  git -C "$STAGE" rm -q --cached "$f" 2>/dev/null
done
git -C "$STAGE" commit -q -m "poda backup $DATE" 2>/dev/null
git -C "$STAGE" push -q 2>/dev/null

exit 0
