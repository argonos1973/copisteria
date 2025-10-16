.PHONY: help install test coverage lint format clean pre-commit setup-hooks validate deploy

help:
	@echo "Comandos disponibles para Aleph70:"
	@echo ""
	@echo "  make install       - Instalar dependencias del proyecto"
	@echo "  make setup-hooks   - Configurar pre-commit hooks"
	@echo "  make test          - Ejecutar tests"
	@echo "  make coverage      - Generar reporte de cobertura"
	@echo "  make lint          - Ejecutar linters (flake8, pylint)"
	@echo "  make format        - Formatear código (black, isort)"
	@echo "  make type-check    - Verificar tipos con mypy"
	@echo "  make security      - Análisis de seguridad (bandit, safety)"
	@echo "  make quality       - Ejecutar todos los checks de calidad"
	@echo "  make clean         - Limpiar archivos temporales"
	@echo "  make run-dev       - Ejecutar servidor de desarrollo"
	@echo "  make logs          - Ver logs de la aplicación"
	@echo "  make validate      - Validar sintaxis antes de deployment"
	@echo "  make deploy        - Deployment seguro a producción"
	@echo ""

install:
	pip install --upgrade pip
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-xdist flake8 black isort mypy bandit safety pre-commit

setup-hooks:
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks instalados correctamente"

test:
	@echo "🧪 Ejecutando tests..."
	pytest tests/ -v

test-fast:
	@echo "🧪 Ejecutando tests en paralelo..."
	pytest tests/ -v -n auto --maxfail=3

test-coverage:
	@echo "🧪 Ejecutando tests con cobertura..."
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html --cov-report=xml

coverage:
	@echo "📊 Generando reporte de cobertura..."
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "✅ Reporte generado en htmlcov/index.html"
	@which xdg-open > /dev/null && xdg-open htmlcov/index.html || open htmlcov/index.html || echo "Abre htmlcov/index.html en tu navegador"

lint:
	@echo "🔍 Ejecutando linters..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.venv,__pycache__,.git
	flake8 . --count --exit-zero --max-complexity=15 --max-line-length=120 --statistics --exclude=venv,.venv,__pycache__,.git

format:
	@echo "✨ Formateando código..."
	black . --exclude='venv|.venv|__pycache__|.git'
	isort . --skip venv --skip .venv
	@echo "✅ Código formateado correctamente"

type-check:
	@echo "🔍 Verificando tipos..."
	mypy . --ignore-missing-imports --exclude 'venv|.venv'

security:
	@echo "🔒 Análisis de seguridad..."
	bandit -r . -x ./venv,./tests -ll
	safety check

quality: lint type-check security
	@echo "✅ Todos los checks de calidad completados"

clean:
	@echo "🧹 Limpiando archivos temporales..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "✅ Limpieza completada"

run-dev:
	@echo "🚀 Iniciando servidor de desarrollo..."
	python app.py

logs:
	@echo "📋 Logs de la aplicación (Ctrl+C para salir):"
	tail -f logs/aleph70.log

watch-logs:
	@echo "📋 Monitoreando todos los logs (Ctrl+C para salir):"
	tail -f logs/*.log

check-prints:
	@echo "🔍 Buscando print statements en código de producción..."
	@grep -rn "print(" --include="*.py" --exclude-dir=venv --exclude-dir=.venv --exclude-dir=tests --exclude=logger_config.py . || echo "✅ No se encontraron print statements"

ci-local:
	@echo "🔄 Simulando CI localmente..."
	@make lint
	@make type-check
	@make test-coverage
	@echo "✅ CI local completado"

validate:
	@echo "🛡️ Validando sintaxis antes de deployment..."
	@./scripts/validate_before_deploy.sh
	@echo "✅ Validación completada"

deploy:
	@echo "🚀 Deployment seguro a producción..."
	@if [ -z "$(FILES)" ]; then \
		echo "❌ Error: Debes especificar FILES=\"archivo1.py archivo2.py\""; \
		echo ""; \
		echo "Ejemplo:"; \
		echo "  make deploy FILES=\"factura.py tickets.py\""; \
		echo ""; \
		exit 1; \
	fi
	@./scripts/safe_deploy.sh $(FILES)

.DEFAULT_GOAL := help
