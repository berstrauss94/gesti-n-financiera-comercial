# Análisis Exhaustivo — Gestión Financiera Comercial (FinanzApp)

> Autoanálisis técnico actualizado del proyecto: objetivo, arquitectura, herramientas, modelos, APIs (base + Enterprise), servicios de automatización, frontend con ayudas contextuales, y guía completa de verificación en local.
>
> Estado reflejado al momento de este documento: base de datos local `instance/dev.db` migrada a la revisión `6d0fd66a050c`, con usuario demo `AdminDemo1` y negocio `Mi tienda` ya creados.

---

## 1. Objetivo del proyecto

Aplicación web de **gestión financiera para comercios** (marca de UI: "FinanzApp"). Permite a un dueño registrar ingresos y gastos diarios y obtener una lectura rápida de la salud financiera de cada negocio mediante un **semáforo de calor** de 5 niveles y un **motor de ML** que proyecta tendencias y alerta sobre desviaciones.

Idea central: el **ingreso bruto diario es la base 100%**, y cada gasto se evalúa como **porcentaje del ingreso**. Según ese porcentaje y unos umbrales configurables, cada indicador se pinta de un color (verde a crítico). La **ganancia neta** se calcula como ingreso menos todos los gastos, con lógica invertida (más alta es mejor).

Es **multi-tenant**: un usuario puede tener varios negocios, y toda la data cuelga del negocio activo seleccionado. Sobre esta base se añadió una capa **Enterprise** (banca, OCR, inventario/MRP, campos dinámicos, firma digital y helpdesk).

---

## 2. Stack y herramientas

| Capa | Tecnología |
|------|-----------|
| Lenguaje | Python 3.12 (en el equipo local responde `py`, intérprete 3.14) |
| Framework web | Flask 3.1.1 (patrón Application Factory) |
| ORM | SQLAlchemy 2.0.36 + Flask-SQLAlchemy 3.1.1 |
| Migraciones | Flask-Migrate 4.1.0 (Alembic) |
| Autenticación / sesión | Flask-Login 0.6.3 |
| Hashing de contraseñas | bcrypt 4.3.0 |
| Validación de entrada | marshmallow 3.25.1 |
| CORS | Flask-CORS 5.0.1 |
| Motor ML / cálculo | NumPy 2.2.3, pandas 2.2.3, scikit-learn 1.6.1 |
| Export de reportes | reportlab 4.1.0 (PDF), csv (stdlib) |
| Tareas programadas | APScheduler 3.11.0 (dependencia disponible, sin uso activo) |
| Servidor WSGI | gunicorn 23.0.0 |
| Base de datos | PostgreSQL en producción (psycopg2-binary), SQLite en local |
| Deploy | Docker + Railway (auto-deploy desde GitHub) |
| CI | GitHub Actions (lint flake8 + pytest con cobertura) |
| Tests | pytest 8.3.5 + pytest-cov 6.1.1 (166 tests) |
| Frontend | Jinja2 + CSS propio (tema oscuro) + JavaScript vanilla |

---

## 3. Arquitectura general

```
app/
├── __init__.py        # Application factory: config, extensiones, middleware de sesión, registro de 10 blueprints
├── models/            # 7 modelos base + 9 modelos Enterprise
│   └── enterprise.py  # BankAccount, BankTransaction, DocumentOCR, Product, ProductionOrder, CustomField, CustomFieldValue, DigitalSignature, HelpdeskTicket
├── routes/            # Blueprints (API + frontend)
│   └── enterprise.py  # 14 endpoints de los módulos Enterprise
├── schemas/           # Esquemas Marshmallow de validación
├── services/          # Lógica de negocio
│   ├── heatmap.py              # Semáforo + ganancia neta
│   ├── ml_engine.py            # Motor ML (promedio móvil, predicción, recalibración)
│   ├── ocr_service.py          # OCR → impacto en gastos
│   └── reconciliation_service.py  # Conciliación bancaria
├── templates/         # Vistas Jinja2 (login, register, dashboard, income, expenses, heatmap, reports)
└── static/            # CSS (incluye tooltips de ayuda) y JS por página
migrations/            # Migraciones Alembic (001_initial + 6d0fd66a050c_add_enterprise_modules)
tests/                 # Suite pytest
.kiro/specs/           # Especificaciones (commercial-financial-management, enterprise_features)
Dockerfile, entrypoint.sh, Procfile, railway.toml   # Deploy
```

### Application Factory (`app/__init__.py`)
- `create_app()` crea la app, carga config desde variables de entorno, inicializa extensiones (`db`, `migrate`, `login_manager`, `CORS`) y registra los blueprints.
- **`user_loader`**: recarga el `User` por id para Flask-Login.
- **`unauthorized_handler`**: rutas `/api/` → `401 AUTH_SESSION_EXPIRED` (JSON); resto → redirect a `/login`.
- **Middleware `check_session_expiration` (`@app.before_request`)**: expiración por inactividad. Salta estáticos y rutas públicas; para usuarios autenticados compara `session['last_activity']` contra `SESSION_TIMEOUT_MINUTES` (30 min por defecto); si expira hace logout y 401; si es válida, renueva la marca de actividad.

### Configuración por entorno
| Variable | Default | Uso |
|----------|---------|-----|
| `FLASK_SECRET_KEY` | `dev-secret-key` | Firma de sesiones |
| `DATABASE_URL` | `sqlite:///dev.db` | Conexión a BD |
| `SESSION_TIMEOUT_MINUTES` | `30` | Expiración por inactividad |
| `MAX_LOGIN_ATTEMPTS` | `5` | Intentos antes de bloqueo (15 min) |
| `ML_MOVING_AVERAGE_DAYS` | `90` | Ventana del promedio móvil |
| `ML_RECALIBRATION_THRESHOLD` | `0.10` | Umbral de desviación (10%) |
| `ML_MIN_RECORDS` | `5` | Mínimo de registros para predecir |

---

## 4. Modelos de datos

### 4.1 Modelos base (`app/models/`)
| Modelo | Tabla | Campos clave | Restricciones / relaciones |
|--------|-------|--------------|----------------------------|
| **User** | `users` | `username` (unique), `email` (unique), `password_hash`, `phone`, `is_active`, `failed_login_attempts`, `locked_until`, `last_login` | `UserMixin`. 1—N con `Business` |
| **Business** | `businesses` | `name`, `owner_id` (FK users), `is_active` | Ancla del multi-tenancy |
| **DailyIncome** | `daily_incomes` | `business_id`, `date`, `amount`, `notes` | UniqueConstraint `(business_id, date)` |
| **Expense** (base) | `expenses` | `category`, `subcategory`, `amount`, `date` | Genérico, no usado por endpoints |
| **Salary** | `salaries` | `employee_name`, `amount`, `period_start`, `period_end` | Sueldos por rango |
| **VariableExpense** | `variable_expenses` | `category`, `amount`, `date`, `description` | 8 categorías |
| **OperatingCost** | `operating_costs` | `category`, `amount`, `month`, `description` | 5 categorías; `month` = primer día de mes |
| **OwnerWithdrawal** | `owner_withdrawals` | `amount`, `date`, `description` | Retiros del dueño |
| **ThresholdConfig** | `threshold_configs` | `category`, `green_max`, `yellow_max`, `orange_max`, `red_max`, `is_custom` | UniqueConstraint `(business_id, category)` |
| **MLPrediction** | `ml_predictions` | `category`, `predicted_value`, `confidence_lower/upper`, `prediction_date`, `target_date`, `recalibrated` | Historial de predicciones |

### 4.2 Modelos Enterprise (`app/models/enterprise.py`)
Todos llevan `business_id` (FK a `businesses`) para mantener el aislamiento multi-tenant.

| Modelo | Tabla | Para qué sirve |
|--------|-------|----------------|
| **BankAccount** | `bank_accounts` | Cuenta bancaria vinculada; relación 1—N con transacciones (cascade delete) |
| **BankTransaction** | `bank_transactions` | Movimiento importado; `fitid` único (anti-duplicados), `reconciled`, `reconciled_expense_id` |
| **DocumentOCR** | `document_ocrs` | Documento para OCR; `status` (PENDING/PROCESSED/FAILED), campos extraídos (monto, proveedor, fecha), `raw_ocr_json` |
| **Product** | `products` | Catálogo con `sku` y `barcode` (indexados), precios y stock |
| **ProductionOrder** | `production_orders` | Orden MRP; `status` (DRAFT/IN_PROGRESS/DONE/CANCELLED), `quality_check_passed` |
| **CustomField** | `custom_fields` | Definición de campo dinámico para una entidad (`target_model`, `field_type`) |
| **CustomFieldValue** | `custom_field_values` | Valor desacoplado en JSON para un registro |
| **DigitalSignature** | `digital_signatures` | Firma electrónica; `status`, `signature_hash` (SHA-256 de auditoría), `signed_at` |
| **HelpdeskTicket** | `helpdesk_tickets` | Ticket de soporte; `priority`, `status`, `sla_deadline` |

---

## 5. APIs / Endpoints

### Blueprints y prefijos
| Blueprint | Prefijo |
|-----------|---------|
| `health_bp` | (ninguno) |
| `auth_bp` | `/api/auth` |
| `business_bp` | `/api/businesses` |
| `income_bp` | `/api/income` |
| `expenses_bp` | `/api` (rutas en `/api/salaries`, `/api/withdrawals`, etc.) |
| `heatmap_bp` | `/api/heatmap` |
| `reports_bp` | `/api/reports` |
| `ml_bp` | `/api/ml` |
| `enterprise_bp` | `/api/enterprise` |
| `frontend_bp` | páginas HTML |

### 5.1 Base
- **Health**: `GET /health`, `GET /api/info`.
- **Auth**: `POST /api/auth/register`, `POST /api/auth/login` (bcrypt + lockout 5 intentos/15 min), `GET /api/auth/session`, `POST /api/auth/logout`.
- **Businesses**: `POST`/`GET /api/businesses`, `PUT`/`DELETE /api/businesses/<id>` (soft-delete), `POST /api/businesses/<id>/select` (fija negocio activo).
- **Income** (`@require_business`): `POST /api/income` (409 si fecha duplicada), `GET /api/income` (`?date`, `?from&to`, o todo), `PUT /api/income/<id>` (con `confirm_overwrite`).
- **Expenses** (`@require_business`): `POST`/`GET` de `/api/salaries`, `/api/withdrawals`, `/api/variable-expenses` (8 cat.), `/api/operating-costs` (5 cat.).
- **Heatmap** (`@require_business`): `GET /api/heatmap/daily?date=`, `GET /api/heatmap/summary?from=&to=` (máx 90 días).
- **Reports** (`@require_business`): `GET /api/reports` (granularidad daily→annual + filtro texto), `GET /api/reports/compare`, `GET /api/reports/export?format=pdf|csv`.
- **ML** (`@require_business`): `GET /api/ml/prediction?category=` (422 si <5 registros), `GET /api/ml/trends`, `POST /api/ml/recalibrate`.

### 5.2 Enterprise (`/api/enterprise`, todos `@require_business`)
> Nota de implementación: el decorador `require_business` **no inyecta** `business_id`; cada handler lee `session['active_business_id']`, igual que el resto del proyecto.

| Método + ruta | Función |
|---------------|---------|
| `GET`/`POST /products` | Listar / crear productos del catálogo |
| `GET /products/barcode/<barcode>` | Buscar producto por código de barras |
| `GET`/`POST /production-orders` | Listar / crear órdenes MRP (valida que el producto sea del negocio) |
| `PUT /production-orders/<id>` | Cambiar estado y control de calidad |
| `GET`/`POST /custom-fields` | Definir campos dinámicos (Studio) |
| `POST /custom-values` | Guardar/actualizar (upsert) valor JSON de un campo |
| `GET`/`POST /signatures` | Listar / crear solicitudes de firma |
| `POST /signatures/<id>/sign` | Firmar (genera hash SHA-256 de auditoría) |
| `GET`/`POST /tickets` | Listar / crear tickets de helpdesk |
| `GET`/`POST /bank-accounts` | Listar / crear cuentas bancarias |
| `POST /bank-accounts/<id>/transactions` | Importar movimientos (dedup por `fitid`) |
| `POST /bank-accounts/<id>/reconcile` | Conciliación inteligente |
| `POST /documents` | Registrar documento para OCR |
| `POST /documents/<id>/process` | Procesar OCR e impactar el gasto |

### Frontend (`frontend.py`) — páginas Jinja2
`/` (redirige), `/login`, `/register` (públicas), y `/dashboard`, `/income`, `/expenses`, `/heatmap`, `/reports` (protegidas con `@login_required`).

---

## 6. Lógica de negocio (servicios)

### 6.1 Semáforo de calor (`services/heatmap.py`)
**6 estados**: 🟢 green, 🟡 yellow, 🟠 orange, 🔴 red, 🚨 critical, ⚪ neutral (sin datos).
- `calculate_percentage_of_income` = `(gasto/ingreso)*100`; si ingreso ≤ 0 → `None`.
- `calculate_heatmap_color`: cascada sobre umbrales. Para gastos, **menor % es mejor**.
- `calculate_all_indicators(business_id, date)`: ingreso del día + sueldos que solapan la fecha + retiros del día + gastos variables del día + costos operativos del mes → 14 indicadores con amount, percentage y color.
- `get_net_profit_indicator`: `net_profit = ingreso − (sueldos + retiros + variables + operativos)`; umbral **invertido hardcodeado** (≥20% verde, ≥10% amarillo, ≥5% naranja, <5% rojo).

### 6.2 Motor ML (`services/ml_engine.py`)
- Promedio móvil simple (90 días) con `np.convolve`.
- `predict_next_period`: predicción = último valor del MA; intervalo de confianza 95% (±1.96·std); tendencia (up/down/stable); **persiste un `MLPrediction`** (target +30 días).
- `needs_recalibration`: desviación `|real − predicho|/|predicho| > 10%`.
- `recalibrate`: solo umbrales no custom; usa 180 días y recalcula sobre media/std como % del ingreso medio.

### 6.3 OCR (`services/ocr_service.py`)
- `process_document(document_id, override)`: extrae monto/proveedor/fecha/categoría y crea un `VariableExpense` (o `OperatingCost` si la categoría es operativa). Marca el documento PROCESSED/FAILED.
- `_run_ocr` es el **punto de extensión** para integrar un motor OCR real (Tesseract o cloud). Hoy usa los datos ya cargados o un `override`, de modo que el flujo contable es funcional y testeable sin dependencias externas.

### 6.4 Conciliación bancaria (`services/reconciliation_service.py`)
- `reconcile_account(account_id, tolerance_days=2)`: cruza transacciones no conciliadas contra gastos/ingresos por **monto** (valor absoluto, precisión de centavos) y **fecha** (dentro de la tolerancia). Importe negativo → busca gastos; positivo → busca ingresos. Marca `reconciled=True` y guarda el id del registro emparejado.

---

## 7. Frontend y ayudas contextuales

- Plantillas Jinja2 con un `base.html` que arma la barra lateral (usuario, negocio activo, Dashboard, Ingresos, Gastos, Heatmap, Reportes, Cerrar Sesión).
- **Semáforo del dashboard** (`dashboard.js`): corregido para iterar sobre `heatmap.indicators` (antes mostraba por error las claves `date`/`gross_income`/`indicators`). Etiquetas en español, incluida `retiros_dueno` → "Retiros del Dueño".
- **Iconos de ayuda (?)**: cada ítem del sidebar, cada tarjeta de información, cada pestaña y los campos de formulario tienen un icono `?` con tooltip accesible (hover + foco de teclado, `aria-label`) que explica el porqué y para qué de cada punto. CSS en `styles.css` (clase `.help-tip`). Los tooltips del sidebar se abren hacia la derecha, flotando sobre el contenido (z-index alto, fondo opaco) para no superponerse con otros ítems.

---

## 8. Deploy y CI/CD

- **Dockerfile**: `python:3.12-slim`, instala `gcc`/`libpq-dev`, usuario no-root, healthcheck sobre `/health`, arranca con `entrypoint.sh`.
- **entrypoint.sh**: `flask db upgrade` y luego `gunicorn` (2 workers).
- **Procfile / railway.toml**: gunicorn + healthcheck `/health` + reinicio on_failure.
- **CI (`.github/workflows/test.yml`)**: en push/PR a `main`, instala deps, flake8 (no bloqueante), `pytest --cov`, verifica migraciones. Usa `DATABASE_URL=sqlite:///test.db`.

---

## 9. Verificación en local (paso a paso — Windows / PowerShell)

> El intérprete en este equipo responde como `py`. La base `instance/dev.db` ya está migrada a `6d0fd66a050c` y contiene el usuario demo y el negocio "Mi tienda". Si partes de cero, sigue 9.1–9.3.

### 9.1. Entorno e instalación
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
pip install -r requirements.txt
```

### 9.2. Variables de entorno (sesión actual)
```powershell
$env:FLASK_APP = "app:create_app()"
$env:FLASK_SECRET_KEY = "dev-secret-key"
$env:DATABASE_URL = "sqlite:///dev.db"
$env:FLASK_DEBUG = "1"
```

### 9.3. Base de datos (migraciones)
```powershell
py -m flask db upgrade
py -m flask db current   # debe mostrar 6d0fd66a050c (head)
```

### 9.4. Levantar el servidor
```powershell
py -m flask run --port 5000
```
Abre `http://localhost:5000/login`.

### 9.5. Credenciales de demo (local)
| Campo | Valor |
|-------|-------|
| Usuario | `AdminDemo1` |
| Contraseña | `ClaveDemo123` |

> Si la base estuviera vacía, crea el usuario con el endpoint de registro (username 8+ caracteres y al menos una mayúscula).

### 9.6. Smoke test de la API base (otra terminal)
```powershell
Invoke-RestMethod http://localhost:5000/health

$s = Invoke-RestMethod -Method Post http://localhost:5000/api/auth/login `
  -ContentType "application/json" `
  -Body '{"username":"AdminDemo1","password":"ClaveDemo123"}' -SessionVariable sess

# Negocio activo (Mi tienda tiene id 1)
Invoke-RestMethod -Method Post http://localhost:5000/api/businesses/1/select -WebSession $sess

# Ingreso del día + semáforo
Invoke-RestMethod -Method Post http://localhost:5000/api/income `
  -ContentType "application/json" `
  -Body '{"amount":50000,"date":"2026-10-05","notes":"venta"}' -WebSession $sess
Invoke-RestMethod "http://localhost:5000/api/heatmap/daily?date=2026-10-05" -WebSession $sess
```

### 9.7. Smoke test de la API Enterprise
```powershell
# Crear producto y buscarlo por barcode
Invoke-RestMethod -Method Post http://localhost:5000/api/enterprise/products `
  -ContentType "application/json" `
  -Body '{"name":"Cafe 1kg","sku":"CAF-1","barcode":"7791234567890","sale_price":1800,"stock_quantity":25}' -WebSession $sess
Invoke-RestMethod http://localhost:5000/api/enterprise/products/barcode/7791234567890 -WebSession $sess
```

### 9.8. Suite de tests
```powershell
$env:FLASK_SECRET_KEY = "ci-test-secret-key"
$env:DATABASE_URL = "sqlite:///test.db"
pytest --cov=app --cov-report=term-missing -v
# Resultado esperado: 166 passed
```

### 9.9. Checklist de verificación funcional
- [ ] `flask db current` muestra `6d0fd66a050c (head)` y existen las 20 tablas (10 base + 9 enterprise + alembic_version).
- [ ] `GET /health` responde `{status:'healthy'}`.
- [ ] Login con `AdminDemo1` / `ClaveDemo123` devuelve 200.
- [ ] Operar sin negocio seleccionado → `403 BUSINESS_NOT_SELECTED`.
- [ ] Crear negocio siembra automáticamente los `threshold_configs`.
- [ ] Ingreso duplicado en la misma fecha → `409 INCOME_DUPLICATE_DATE`.
- [ ] `GET /api/heatmap/daily` devuelve 14 indicadores + `net_profit` con su color.
- [ ] `GET /api/ml/prediction?category=ingresos` → `422` con menos de 5 registros.
- [ ] `POST /api/enterprise/products` crea y `GET .../barcode/<x>` lo encuentra.
- [ ] Importar transacciones banca con `fitid` repetido las deduplica.
- [ ] Firmar un documento genera `signature_hash` y `status=SIGNED`.
- [ ] En el dashboard, el semáforo muestra categorías en español (no `Date`/`Gross Income`).
- [ ] Los iconos `?` del sidebar muestran su tooltip sin superponerse con otros ítems.
- [ ] La suite `pytest` pasa en verde (166).

---

## 10. Observaciones y posibles mejoras

- **Prefijo de expenses**: `expenses_bp` usa `/api` (no `/api/expenses`); las rutas son `/api/salaries`, `/api/withdrawals`, etc.
- **GET con efecto de escritura**: `/api/ml/prediction` persiste una fila `MLPrediction` en cada llamada.
- **Ganancia neta no configurable**: usa umbrales hardcodeados en el servicio, a diferencia del resto que lee de `ThresholdConfig`.
- **Modelo base `Expense`**: definido pero sin uso por endpoints; candidato a limpieza.
- **OCR simulado**: `ocr_service._run_ocr` no integra aún un motor OCR real; es un punto de extensión funcional.
- **Leyenda del Heatmap**: la leyenda de colores de `heatmap.html` (`<50% Excelente`, etc.) no coincide con los umbrales reales por categoría; conviene alinearla o marcarla como orientativa.
- **APScheduler**: en dependencias pero sin tareas programadas activas.
- **Migración Enterprise**: fue depurada a mano para evitar operaciones destructivas que el autogenerate proponía sobre tablas preexistentes (se conservaron todos los índices base).
