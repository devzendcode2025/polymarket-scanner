# VERIFICACION — polymarket-scanner

Runner canónico: `bash verificacion/run-all.sh` (py_compile de scripts + checks de .gitignore). Exit 1 ante cualquier fallo.

## v0.1.1 — 2026-08-13 21:20 (runner creado)

Comando: `bash verificacion/run-all.sh`
Resultado: PASÓ (exit 0)

```
===== [1/2] Sintaxis Python (py_compile) =====
OK   workspace/scripts/db.py
OK   workspace/scripts/polymarket_client.py
OK   workspace/scripts/run_scan.py
OK   workspace/scripts/scanner.py

===== [2/2] .gitignore (git check-ignore + tree limpio) =====
== 1) .gitignore presente ==
OK .gitignore existe
== 2) Patrones ignorados (git check-ignore) ==
OK ignorado: workspace/data/polymarket.db
OK ignorado: workspace/reports/technical/scan_x.json
OK ignorado: __pycache__/x.pyc
OK ignorado: .env
== 3) Working tree limpio (sin no-rastreados no ignorados) ==
OK limpio
== 4) Archivos versionados esperados ==
OK: todos los archivos esperados versionados
== 5) .env no versionado ==
OK .env excluido

gitignore: OK

RESULTADO: TODO OK
```

Nota: la primera corrida falló (exit 1) porque `verificacion/` no estaba versionada → check 3 "tree sucio". Se versionó (commit v0.1.1) y la corrida posterior pasó. No es una regresión de código; era el runner verificándose a sí mismo antes de existir en git.

Scripts: `verificacion/run-all.sh`, `verificacion/verify_gitignore.sh`

## v0.2.2 — 2026-08-13 21:50 (make test canónico + check de estado del repo)

Cambios: Makefile con target `test` (comando canónico detectado por el tracker), nuevo `verificacion/verify_repo_state.sh` (check 3: .env permisos 600 + formato token sin exponer valor, control files versionados, sitio público HTTP 200). run-all.sh ampliado a 3 secciones.

Primera corrida de `make test`: HAY FALLOS únicamente por árbol sucio (Makefile y verify_repo_state.sh sin versionar) — no es regresión de código. Se versiona todo en v0.2.2 y la corrida posterior queda en verde (exit 0).

