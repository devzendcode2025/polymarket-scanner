# Runner canónico de verificación: make test
# Ejecuta verificacion/run-all.sh (sintaxis Python + gitignore + estado del repo)
.PHONY: test
test:
	bash verificacion/run-all.sh
