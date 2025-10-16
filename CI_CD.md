# CI/CD - Aleph70

## 🚀 Sistema de Integración y Despliegue Continuo

Este proyecto implementa un sistema completo de CI/CD para garantizar la calidad del código y automatizar las pruebas.

## 📊 Estado Actual

![Tests](https://github.com/argonos1973/copisteria/workflows/Tests%20&%20Coverage/badge.svg)
![Pre-commit](https://github.com/argonos1973/copisteria/workflows/Pre-commit%20Checks/badge.svg)
[![codecov](https://codecov.io/gh/argonos1973/copisteria/branch/main/graph/badge.svg)](https://codecov.io/gh/argonos1973/copisteria)

- **Tests**: 306 tests pasando (99.7%)
- **Cobertura**: 20%
- **Tiempo de ejecución**: ~6 segundos

## 🔄 Workflows de GitHub Actions

### 1. Tests & Coverage (`tests.yml`)

Ejecuta automáticamente en cada push y pull request:

```yaml
- Python 3.11 y 3.12
- Tests con pytest
- Cobertura de código
- Linting con flake8
- Formateo con black
- Ordenamiento de imports con isort
```

**Triggers:**
- Push a `main` o `develop`
- Pull requests a `main` o `develop`

### 2. Pre-commit Checks (`pre-commit.yml`)

Ejecuta hooks de pre-commit para validar calidad del código:

```yaml
- Formateo de código
- Linting
- Type checking
- Security checks
- No print statements en producción
```

### 3. Quality Checks

Checks adicionales de calidad:

```yaml
- Análisis de seguridad (bandit)
- Vulnerabilidades de dependencias (safety)
- Type checking (mypy)
```

## 🛠️ Configuración Local

### Instalación de Dependencias

```bash
# Instalar dependencias del proyecto
make install

# Configurar pre-commit hooks
make setup-hooks
```

### Pre-commit Hooks

Los hooks se ejecutan automáticamente antes de cada commit:

```bash
# Instalar hooks
pre-commit install

# Ejecutar manualmente en todos los archivos
pre-commit run --all-files

# Actualizar hooks a últimas versiones
pre-commit autoupdate
```

### Hooks Configurados

1. **Formateo de Código**
   - `black`: Formateo automático Python
   - `isort`: Ordenamiento de imports

2. **Linting**
   - `flake8`: Detección de errores y code smells
   - `pylint`: Análisis estático avanzado

3. **Type Checking**
   - `mypy`: Verificación de tipos estáticos

4. **Seguridad**
   - `bandit`: Detección de vulnerabilidades
   - `detect-private-key`: Prevención de commits de claves privadas

5. **Validaciones Generales**
   - Trailing whitespace
   - End of file fixer
   - YAML/JSON syntax check
   - No archivos grandes (>1MB)
   - No merge conflicts

6. **Custom Checks**
   - **No print statements**: Previene uso de `print()` en producción

## 📝 Comandos Disponibles

### Tests

```bash
# Ejecutar todos los tests
make test

# Tests en paralelo (más rápido)
make test-fast

# Tests con cobertura
make test-coverage

# Ver reporte de cobertura en navegador
make coverage
```

### Calidad de Código

```bash
# Linting
make lint

# Formateo automático
make format

# Type checking
make type-check

# Análisis de seguridad
make security

# Todos los checks
make quality
```

### Desarrollo

```bash
# Ejecutar servidor de desarrollo
make run-dev

# Ver logs en tiempo real
make logs

# Monitorear todos los logs
make watch-logs

# Buscar print statements
make check-prints

# Limpiar archivos temporales
make clean
```

### CI Local

```bash
# Simular CI localmente (antes de push)
make ci-local
```

## 🎯 Workflow Recomendado

### Antes de Commit

```bash
# 1. Formatear código
make format

# 2. Ejecutar tests
make test-fast

# 3. Ver cobertura (opcional)
make coverage

# 4. Verificar que no hay prints
make check-prints
```

Los pre-commit hooks se ejecutarán automáticamente.

### Antes de Push

```bash
# Ejecutar suite completa de CI localmente
make ci-local
```

### Pull Request

1. Crear branch feature:
   ```bash
   git checkout -b feature/nueva-funcionalidad
   ```

2. Desarrollar y commitear:
   ```bash
   # Los hooks se ejecutan automáticamente
   git add .
   git commit -m "feat: nueva funcionalidad"
   ```

3. Push y crear PR:
   ```bash
   git push origin feature/nueva-funcionalidad
   ```

4. GitHub Actions ejecutará automáticamente:
   - Tests en Python 3.11 y 3.12
   - Coverage check
   - Linting y formateo
   - Security checks
   - Pre-commit hooks

## 📈 Cobertura de Código

### Objetivo

- **Actual**: 20% ✅
- **Objetivo Q4 2025**: 30%
- **Mínimo aceptable**: 15%

### Ver Reporte

```bash
# Generar y abrir reporte HTML
make coverage

# Ver en terminal
pytest tests/ --cov=. --cov-report=term-missing
```

### Coverage por Módulo

Módulos con excelente cobertura (≥97%):
- `test_format_utils`: 100%
- `test_api_integration`: 99%
- `test_conciliacion`: 99%
- `test_factura_extended`: 99%
- `test_productos`: 99%
- Y 6 módulos más...

## 🔒 Seguridad

### Bandit

Análisis de seguridad del código:

```bash
make security
```

Busca:
- SQL injection
- Hard-coded passwords
- Uso inseguro de pickle
- Shell injection
- Etc.

### Safety

Verifica vulnerabilidades en dependencias:

```bash
safety check
```

## 🚫 Reglas Obligatorias

### ❌ NUNCA usar print() en producción

Los pre-commit hooks bloquearán commits con `print()` en archivos de producción.

**Uso correcto:**

```python
from logger_config import get_logger
logger = get_logger(__name__)

# ✅ Correcto
logger.info("Operación exitosa")
logger.error("Error detectado", exc_info=True)

# ❌ Incorrecto
print("Operación exitosa")  # Bloqueado por pre-commit
```

### ✅ Tests Obligatorios

- Nueva funcionalidad → nuevos tests
- Cobertura mínima: 80% para archivos nuevos
- Tests deben pasar en Python 3.11 y 3.12

### 📝 Mensajes de Commit

Seguir convención:

```
feat: nueva funcionalidad
fix: corrección de bug
docs: actualización de documentación
test: añadir tests
refactor: refactorización de código
style: cambios de formateo
perf: mejora de rendimiento
```

## 🐛 Troubleshooting

### Pre-commit falla

```bash
# Ver qué hook falló
pre-commit run --all-files --verbose

# Omitir hooks temporalmente (NO RECOMENDADO)
git commit --no-verify
```

### Tests fallan en CI pero pasan localmente

```bash
# Verificar versión de Python
python --version

# Limpiar cache
make clean

# Ejecutar con misma configuración que CI
pytest tests/ -v --maxfail=5
```

### Problemas de formateo

```bash
# Aplicar formateo automático
make format

# Verificar qué cambiaría black
black --check --diff .
```

## 📚 Recursos

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Pre-commit Docs](https://pre-commit.com/)
- [Pytest Docs](https://docs.pytest.org/)
- [Black Docs](https://black.readthedocs.io/)
- [Codecov Docs](https://docs.codecov.com/)

## 🎯 Próximos Pasos

- [ ] Añadir tests de integración E2E
- [ ] Configurar deployment automático a staging
- [ ] Implementar semantic versioning automático
- [ ] Añadir performance benchmarks
- [ ] Configurar alerts de coverage en PRs
- [ ] Docker automated builds

---

**Mantenido por**: Equipo Aleph70  
**Última actualización**: Oct 16, 2025
