# CENTINELA — atajos de desarrollo.
#
# Todo corre con `uv`; no hace falta activar ningun entorno a mano.
# El objetivo O4 de la especificacion es que `make country ISO=COL` reconstruya
# el activo de exposicion de un pais desde fuentes publicas, sin credenciales.

UV ?= uv run --python 3.12
DEV := $(UV) --extra dev

.DEFAULT_GOAL := help
.PHONY: help setup lint format typecheck test test-golden check manifests trigger country site clean

help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:  ## Instala dependencias de desarrollo
	uv sync --python 3.12 --extra dev

lint:  ## Ruff (lint + formato)
	$(DEV) ruff check .
	$(DEV) ruff format --check .

format:  ## Aplica formato y arreglos automaticos
	$(DEV) ruff check --fix .
	$(DEV) ruff format .

typecheck:  ## mypy estricto
	$(DEV) mypy

test:  ## Suite completa sin red
	$(DEV) pytest -m "not network"

test-golden:  ## Solo pruebas de regresion
	$(DEV) pytest -m golden

check: lint typecheck test  ## Todo lo que corre en CI

manifests:  ## Lint de licencias y vintages (§2.4)
	$(UV) centinela lint-manifests

trigger:  ## P1 en seco contra el feed vivo (no escribe estado)
	$(UV) centinela trigger --dry-run

country:  ## P0: reconstruye el activo de un pais — make country ISO=COL
	@test -n "$(ISO)" || (echo "Uso: make country ISO=COL" && exit 1)
	$(UV) --extra geo centinela country $(ISO)

site:  ## Sirve el visor estatico en localhost:8080
	python3 -m http.server 8080 --directory site

clean:  ## Borra artefactos efimeros (nunca toca events/ ni reports/)
	rm -rf work data/cache data/build .pytest_cache .ruff_cache .mypy_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
