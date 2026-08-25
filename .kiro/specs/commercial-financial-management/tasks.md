# Implementation Plan: Gestión Financiera Comercial

## Overview

Implementación incremental del sistema de gestión financiera comercial siguiendo el orden: modelos de datos y migraciones → autenticación y sesiones → ingresos → gastos y costos → heatmap → ML engine → reportes → CI/CD. Cada fase se construye sobre la anterior para garantizar integración continua sin código huérfano.

## Tasks

- [x] 1. Modelos de datos, esquemas y estructura base
  - [x] 1.1 Crear modelo OwnerWithdrawal y actualizar modelo Salary
    - Crear `app/models/owner_withdrawal.py` con columnas: id, business_id, amount (Numeric 12,2), date, description, created_at
    - Actualizar `app/models/expense.py` para asegurar que Salary incluye employee_name, period_start, period_end
    - Registrar modelos en `app/models/__init__.py`
    - _Requirements: 5.6, 5.7, 5.8, 5.9, 5.10, 6.10_

  - [x] 1.2 Crear modelo ThresholdConfig con defaults
    - Crear `app/models/threshold_config.py` con columnas: id, business_id, category, green_max, yellow_max, orange_max, red_max, is_custom, updated_at
    - Agregar UniqueConstraint en (business_id, category)
    - Implementar función `seed_default_thresholds(business_id)` que crea las configuraciones por defecto para todas las categorías (salarios: 18/22/28/35, retiros: 10/15/20/25, mercadería: 40/45/50/60, etc.)
    - _Requirements: 4.1, 5.1-5.10, 6.2-6.9, 7.1-7.5_

  - [x] 1.3 Crear modelo MLPrediction
    - Crear `app/models/ml_prediction.py` con columnas: id, business_id, category, predicted_value, confidence_lower, confidence_upper, prediction_date, target_date, recalibrated, created_at
    - Registrar en `app/models/__init__.py`
    - _Requirements: 9.1, 9.5_

  - [x] 1.4 Crear migración de base de datos
    - Ejecutar `flask db migrate` para generar migración con todos los modelos nuevos y actualizados
    - Verificar que la migración incluye: owner_withdrawals, threshold_configs, ml_predictions, campos actualizados en users (failed_login_attempts, locked_until)
    - _Requirements: 1.1-1.5, 2.1-2.5_

  - [x] 1.5 Crear schemas Marshmallow para validación
    - Crear `app/schemas/__init__.py` con schemas: UserRegistrationSchema, LoginSchema, IncomeSchema, SalarySchema, OwnerWithdrawalSchema, VariableExpenseSchema, OperatingCostSchema, ThresholdConfigSchema, ReportQuerySchema
    - Implementar validaciones: username (min 8 chars, uppercase), email RFC 5322, phone (7-15 dígitos), amount (0.01-999999999.99), category (enum de 8 valores)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 6.1_

  - [ ]* 1.6 Write property tests for input validation
    - **Property 1: Username validation rejects short or lowercase-only strings**
    - **Property 2: Phone validation enforces digit length bounds**
    - **Property 6: Income amount range enforcement**
    - **Validates: Requirements 1.1, 1.2, 1.4, 3.1**

- [x] 2. Checkpoint - Foundation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Autenticación, sesiones y multi-tenant
  - [x] 3.1 Implementar registro de usuario con validaciones completas
    - Actualizar `app/routes/auth.py` endpoint POST /api/auth/register
    - Integrar UserRegistrationSchema para validación de entrada
    - Implementar hashing con bcrypt para contraseñas
    - Retornar errores específicos: VALIDATION_USERNAME_LENGTH, VALIDATION_USERNAME_UPPERCASE, VALIDATION_EMAIL_FORMAT, VALIDATION_PHONE_FORMAT
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 3.2 Implementar login con lockout y manejo de sesión
    - Actualizar `app/routes/auth.py` endpoint POST /api/auth/login
    - Implementar lógica: verificar si cuenta está locked (locked_until > now), incrementar failed_login_attempts en fallo, bloquear tras 5 intentos, resetear contador en login exitoso
    - Crear sesión con Flask-Login y registrar last_login y last_activity
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Implementar expiración de sesión por inactividad
    - Crear middleware `@app.before_request` que verifica elapsed time desde last_activity
    - Si elapsed > 30 minutos: logout automático, retornar AUTH_SESSION_EXPIRED
    - Si válido: actualizar last_activity = now
    - Implementar endpoint GET /api/auth/session para verificar estado
    - _Requirements: 2.3_

  - [x] 3.4 Implementar módulo de negocios y selección multi-tenant
    - Crear `app/routes/business.py` con endpoints: POST/GET/PUT/DELETE /api/businesses, POST /api/businesses/:id/select
    - Implementar decorator `@require_business` que verifica negocio activo en sesión
    - Toda query debe incluir filtro `business_id = session.active_business_id`
    - _Requirements: 2.4, 2.5_

  - [ ]* 3.5 Write property tests for auth and sessions
    - **Property 3: Account lockout activates at threshold**
    - **Property 4: Session expiration by inactivity**
    - **Property 5: Multi-tenant data isolation**
    - **Validates: Requirements 2.2, 2.3, 2.5**

- [x] 4. Checkpoint - Auth & Multi-tenant
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Módulo de Ingresos
  - [x] 5.1 Implementar CRUD de ingreso bruto diario
    - Crear `app/routes/income.py` con endpoints: POST /api/income, GET /api/income?date=, GET /api/income?from=&to=, PUT /api/income/:id
    - Validar monto con IncomeSchema (0.01-999999999.99)
    - Implementar detección de duplicado por fecha: si existe, retornar INCOME_DUPLICATE_DATE con flag para confirmar overwrite
    - Aplicar decorator @require_business para aislamiento
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 5.2 Implementar recálculo de indicadores al guardar ingreso
    - Tras guardar/actualizar ingreso, disparar recálculo de todos los porcentajes del día
    - Recalcular: salarios %, retiros %, cada categoría de gasto variable %, costos operativos %, ganancia neta %
    - Llamar al HeatmapService para actualizar colores
    - _Requirements: 3.2, 3.5_

  - [ ]* 5.3 Write property test for percentage calculation
    - **Property 7: Percentage calculation relative to gross income**
    - **Validates: Requirements 3.2**

- [x] 6. Módulo de Gastos y Costos
  - [x] 6.1 Implementar CRUD de salarios de empleados
    - Crear `app/routes/expenses.py` con endpoints: POST /api/salaries, GET /api/salaries?period=
    - Validar con SalarySchema
    - Aplicar @require_business
    - _Requirements: 5.1-5.5_

  - [x] 6.2 Implementar CRUD de retiros del dueño
    - Agregar endpoints en `app/routes/expenses.py`: POST /api/withdrawals, GET /api/withdrawals?period=
    - Validar con OwnerWithdrawalSchema
    - _Requirements: 5.6-5.10_

  - [x] 6.3 Implementar CRUD de gastos variables (8 categorías)
    - Agregar endpoints: POST /api/variable-expenses, GET /api/variable-expenses?category=&date=
    - Validar categoría contra enum: comisiones, mermas, servicios, insumos, mantenimiento, impuestos_municipales, seguros, logística
    - Rechazar categorías no válidas con VALIDATION_INVALID_CATEGORY
    - _Requirements: 6.1-6.9_

  - [x] 6.4 Implementar CRUD de costos operativos
    - Agregar endpoints: POST /api/operating-costs, GET /api/operating-costs?month=
    - Categorías: electricidad, monotributo, mercadería, alquiler, contable
    - _Requirements: 7.1-7.7_

  - [ ]* 6.5 Write property tests for expense categories
    - **Property 11: Variable expense category exclusivity**
    - **Validates: Requirements 6.1**

- [x] 7. Heatmap Service
  - [x] 7.1 Implementar algoritmo de cálculo de color heatmap
    - Actualizar `app/services/heatmap.py` con función `calculate_heatmap_color(percentage, thresholds) -> str`
    - Implementar lógica: None → neutral, <= green → green, <= yellow → yellow, <= orange → orange, <= red → red, else → critical
    - Implementar `calculate_percentage_of_income(expense_amount, gross_income) -> float | None`
    - _Requirements: 4.1, 4.2_

  - [x] 7.2 Implementar cálculo de todos los indicadores por día
    - Implementar `calculate_all_indicators(business_id, date) -> HeatmapResult`
    - Consultar ingreso del día, sumar cada tipo de gasto, calcular porcentaje de cada uno, aplicar threshold correspondiente
    - Retornar dict con color por categoría: salarios, retiros, cada gasto variable, cada costo operativo, ganancia neta
    - _Requirements: 4.1, 5.1-5.10, 6.2-6.9, 7.1-7.5_

  - [x] 7.3 Implementar panel de ganancia neta
    - Implementar `get_net_profit_indicator(business_id, date) -> NetProfitResult`
    - Fórmula: Ingreso Bruto - Salarios - Retiros - Variables - Operativos
    - Calcular porcentaje: (net_profit / gross_income) * 100
    - Aplicar thresholds: >=20 green, 10-20 yellow, 5-10 orange, <5 red
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [x] 7.4 Crear endpoints REST del heatmap
    - Crear endpoints: GET /api/heatmap/daily?date=, GET /api/heatmap/summary?from=&to=
    - Incluir tooltip data: porcentaje exacto, monto absoluto, tendencia
    - Asegurar respuesta < 2 segundos
    - _Requirements: 4.3, 4.4, 4.5_

  - [ ]* 7.5 Write property tests for heatmap
    - **Property 8: Heatmap color mapping is deterministic and exhaustive**
    - **Property 9: Salary threshold color mapping**
    - **Property 10: Owner withdrawal threshold color mapping**
    - **Property 12: Category-specific threshold application**
    - **Property 13: Net profit formula consistency**
    - **Property 14: Net profit threshold color mapping**
    - **Validates: Requirements 4.1, 4.2, 5.1-5.10, 6.2-6.9, 7.1-7.5, 8.1-8.5**

- [x] 8. Checkpoint - Core Financial Logic
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Motor de Machine Learning
  - [x] 9.1 Implementar cálculo de promedio móvil
    - Actualizar `app/services/ml_engine.py` con función `calculate_moving_average(values, window=90) -> list[float] | None`
    - Rechazar si len(values) < 5 (retornar None)
    - Ajustar window = min(window, len(values))
    - Usar numpy convolution con weights uniformes
    - _Requirements: 9.1, 9.3_

  - [x] 9.2 Implementar lógica de recalibración
    - Implementar `needs_recalibration(current_value, predicted_value) -> bool`
    - Si predicted == 0: retornar current != 0
    - variation = |current - predicted| / |predicted|, retornar variation > 0.10
    - Implementar `recalibrate(business_id, category)` que actualiza ThresholdConfig si is_custom=False
    - _Requirements: 9.2, 9.4_

  - [x] 9.3 Implementar predicción con intervalo de confianza
    - Implementar `predict_next_period(business_id, category) -> PredictionResult`
    - Fetch últimos 90 días, calcular MA, calcular std de residuales
    - Confidence interval: predicted ± 1.96 * std (95% CI)
    - Determinar tendencia: up/down/stable basado en pendiente del MA
    - _Requirements: 9.5_

  - [x] 9.4 Crear endpoints REST del ML engine
    - Agregar endpoints: GET /api/ml/prediction?category=, GET /api/ml/trends, POST /api/ml/recalibrate
    - Retornar ML_INSUFFICIENT_DATA si < 5 registros
    - Rate limit: 10 requests/minuto para predicciones
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]* 9.5 Write property tests for ML engine
    - **Property 15: Moving average requires minimum records**
    - **Property 16: Recalibration triggers on variation exceeding 10%**
    - **Validates: Requirements 9.1, 9.2, 9.3**

- [x] 10. Checkpoint - ML Engine
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Módulo de Reportes
  - [x] 11.1 Implementar generación de reportes por período
    - Crear `app/routes/reports.py` con endpoint GET /api/reports?granularity=&from=&to=
    - Soportar granularidades: daily, weekly, monthly, quarterly, semiannual, annual
    - Agregar totales, promedios y datos de tendencia visual
    - _Requirements: 10.1, 10.4_

  - [x] 11.2 Implementar comparativa entre períodos
    - Agregar endpoint GET /api/reports/compare?period1=&period2=
    - Implementar `compare_periods(period1_data, period2_data) -> ComparisonResult`
    - Calcular diferencia absoluta y porcentual para cada métrica
    - Manejar caso period1.value == 0 (percentage_diff = None)
    - _Requirements: 10.2_

  - [x] 11.3 Implementar filtro de texto en reportes
    - Agregar parámetro de query `filter` a endpoints de reportes
    - Filtrar por categoría o descripción, case-insensitive
    - Asegurar que ningún item que coincida quede excluido
    - _Requirements: 10.3_

  - [x] 11.4 Implementar exportación PDF y CSV
    - Agregar endpoint GET /api/reports/export?format=pdf|csv
    - Para CSV: usar módulo csv estándar de Python
    - Para PDF: usar reportlab o weasyprint para generación
    - Agregar dependencia necesaria a requirements.txt
    - _Requirements: 10.5_

  - [ ]* 11.5 Write property tests for reports
    - **Property 17: Period comparison calculation**
    - **Property 18: Text filter correctness**
    - **Validates: Requirements 10.2, 10.3**

- [x] 12. Checkpoint - Reports
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. CI/CD y configuración de despliegue
  - [x] 13.1 Crear pipeline GitHub Actions para CI
    - Crear `.github/workflows/test.yml` con jobs: lint, test (pytest --cov=app), property tests (pytest tests/property/ -x)
    - Configurar matrix para Python 3.11+
    - Agregar step de verificación de migraciones
    - _Requirements: 11.5_

  - [x] 13.2 Configurar despliegue automático a Railway
    - Actualizar `Dockerfile` y `railway.toml` para incluir migraciones en startup
    - Configurar variables de entorno en Railway: DATABASE_URL, FLASK_SECRET_KEY, SESSION_TIMEOUT_MINUTES, MAX_LOGIN_ATTEMPTS
    - Verificar que HTTPS está habilitado por defecto en Railway
    - Documentar proceso de rollback en README.md
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ]* 13.3 Write integration tests for deployment verification
    - Test health endpoint responds 200
    - Test database connectivity
    - Test que migraciones se aplican correctamente
    - _Requirements: 11.1, 11.5_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at each major milestone
- Property tests validate universal correctness properties defined in the design document (18 properties total)
- Unit tests validate specific examples and edge cases
- The `hypothesis` library must be added to requirements.txt for property-based testing
- All monetary amounts use `Decimal(12,2)` for precision in PostgreSQL
- Multi-tenant isolation (`@require_business` decorator) must be applied to ALL data endpoints
- The ML engine requires numpy for convolution-based moving averages

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5"] },
    { "id": 2, "tasks": ["1.6", "3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3", "3.4"] },
    { "id": 4, "tasks": ["3.5", "5.1"] },
    { "id": 5, "tasks": ["5.2", "6.1", "6.2", "6.3", "6.4"] },
    { "id": 6, "tasks": ["5.3", "6.5", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3"] },
    { "id": 8, "tasks": ["7.4", "7.5"] },
    { "id": 9, "tasks": ["9.1", "9.2"] },
    { "id": 10, "tasks": ["9.3", "9.4"] },
    { "id": 11, "tasks": ["9.5", "11.1"] },
    { "id": 12, "tasks": ["11.2", "11.3"] },
    { "id": 13, "tasks": ["11.4", "11.5"] },
    { "id": 14, "tasks": ["13.1", "13.2"] },
    { "id": 15, "tasks": ["13.3"] }
  ]
}
```
