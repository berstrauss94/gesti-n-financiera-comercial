# Requirements: Gestión Financiera Comercial

## Requirement 1: Registro de Usuario

### User Story
Como nuevo usuario, quiero registrarme en la plataforma proporcionando mis datos personales con validaciones estrictas, para tener una cuenta segura.

### Acceptance Criteria
1. Given un formulario de registro, when el usuario ingresa un username con menos de 8 caracteres, then el sistema muestra error "Username debe tener mínimo 8 caracteres"
2. Given un formulario de registro, when el username no contiene al menos una letra mayúscula, then el sistema muestra error "Username debe contener al menos una mayúscula"
3. Given un formulario de registro, when el email no cumple RFC 5322, then el sistema muestra error "Email inválido"
4. Given un formulario de registro, when el número de celular no tiene entre 7 y 15 dígitos, then el sistema muestra error "Número de celular debe tener entre 7 y 15 dígitos"
5. Given datos válidos, when el usuario envía el formulario, then la cuenta se crea exitosamente y se redirige al login

---

## Requirement 2: Login y Multi-Tenant

### User Story
Como usuario registrado, quiero iniciar sesión de forma segura y poder gestionar múltiples negocios desde una sola cuenta.

### Acceptance Criteria
1. Given credenciales correctas, when el usuario inicia sesión, then se crea una sesión activa
2. Given 5 intentos fallidos consecutivos, when el usuario intenta nuevamente, then la cuenta se bloquea temporalmente
3. Given una sesión activa, when pasan 30 minutos sin actividad, then la sesión expira automáticamente
4. Given un usuario autenticado, when accede al dashboard, then puede ver y seleccionar entre sus negocios registrados
5. Given un usuario autenticado, when selecciona un negocio, then solo ve datos pertenecientes a ese negocio (aislamiento multi-tenant)

---

## Requirement 3: Ingreso Bruto Diario

### User Story
Como comerciante, quiero registrar mi ingreso bruto diario como base 100% para todos los cálculos de porcentaje del sistema.

### Acceptance Criteria
1. Given el formulario de ingreso, when se ingresa un monto, then debe estar en el rango 0.01 a 999,999,999.99
2. Given un ingreso registrado, when se calculan gastos y costos, then todos se expresan como porcentaje del ingreso bruto (base 100%)
3. Given un día sin ingreso registrado, when se consulta el dashboard, then muestra indicador neutral (gris)
4. Given un ingreso ya registrado para una fecha, when se intenta registrar otro, then el sistema pide confirmación para sobrescribir
5. Given un ingreso válido, when se guarda exitosamente, then se recalculan todos los indicadores del día

---

## Requirement 4: Mapa de Calor

### User Story
Como comerciante, quiero ver un mapa de calor con semáforo de 5 colores que me muestre el estado financiero de cada categoría de forma visual.

### Acceptance Criteria
1. Given datos financieros, when se renderiza el mapa, then usa 5 colores: 🟢 Verde (saludable), 🟡 Amarillo (precaución), 🟠 Naranja (alerta), 🔴 Rojo (peligro), 🚨 Crítico (emergencia)
2. Given una categoría sin datos, when se renderiza el mapa, then muestra ⚪ Gris (neutral)
3. Given un cambio en ingresos o gastos, when se actualiza un registro, then el mapa se recalcula en menos de 2 segundos
4. Given el mapa visible, when el usuario pasa el cursor sobre un indicador, then muestra tooltip con porcentaje exacto y tendencia
5. Given múltiples categorías, when se muestran juntas, then el layout es responsivo y legible en móvil y desktop

---

## Requirement 5: Salarios y Retiros

### User Story
Como comerciante, quiero registrar salarios de empleados y mis retiros personales, con semáforo independiente para cada uno.

### Acceptance Criteria
1. Given salarios de empleados, when el total es <18% del ingreso bruto, then muestra 🟢
2. Given salarios de empleados, when el total es 18-22%, then muestra 🟡
3. Given salarios de empleados, when el total es 22-28%, then muestra 🟠
4. Given salarios de empleados, when el total es 28-35%, then muestra 🔴
5. Given salarios de empleados, when el total es >35%, then muestra 🚨
6. Given retiros del dueño, when el total es <10% del ingreso bruto, then muestra 🟢
7. Given retiros del dueño, when el total es 10-15%, then muestra 🟡
8. Given retiros del dueño, when el total es 15-20%, then muestra 🟠
9. Given retiros del dueño, when el total es 20-25%, then muestra 🔴
10. Given retiros del dueño, when el total es >25%, then muestra 🚨

---

## Requirement 6: Gastos Variables (8 categorías)

### User Story
Como comerciante, quiero categorizar mis gastos variables en 8 categorías con umbrales propios, para identificar dónde estoy gastando más de lo saludable.

### Acceptance Criteria
1. Given las 8 categorías: comisiones, mermas, servicios, insumos, mantenimiento, impuestos municipales, seguros, logística, when se registra un gasto, then debe asignarse a exactamente una categoría
2. Given comisiones, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
3. Given mermas, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
4. Given servicios, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
5. Given insumos, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
6. Given mantenimiento, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
7. Given impuestos municipales, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
8. Given seguros, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
9. Given logística, when el porcentaje sobre ingreso bruto excede su umbral específico, then cambia de color según la escala de 5 niveles
10. Given todos los gastos variables, when se suman, then el total debe ser coherente con el panel de ganancia neta

---

## Requirement 7: Costos Operativos

### User Story
Como comerciante, quiero registrar mis costos operativos fijos (electricidad, monotributo, mercadería, alquiler, contable) con umbrales específicos.

### Acceptance Criteria
1. Given mercadería, when representa <40% del ingreso bruto, then muestra 🟢
2. Given mercadería, when representa 40-45%, then muestra 🟡
3. Given mercadería, when representa 45-50%, then muestra 🟠
4. Given mercadería, when representa 50-60%, then muestra 🔴
5. Given mercadería, when representa >60%, then muestra 🚨
6. Given electricidad, monotributo, alquiler, contable, when se registran, then cada uno tiene sus propios umbrales configurados
7. Given todos los costos operativos, when se suman, then se incluyen en el cálculo del panel de ganancia neta

---

## Requirement 8: Panel Ganancia Neta

### User Story
Como comerciante, quiero ver un panel maestro con mi ganancia neta y un semáforo que resuma la salud financiera general.

### Acceptance Criteria
1. Given todos los ingresos y egresos del período, when se calcula ganancia neta, then se aplica: Ingreso Bruto - Salarios - Retiros - Gastos Variables - Costos Operativos
2. Given ganancia neta ≥20% del ingreso bruto, then muestra 🟢
3. Given ganancia neta entre 10% y 20%, then muestra 🟡
4. Given ganancia neta entre 5% y 10%, then muestra 🟠
5. Given ganancia neta <5%, then muestra 🔴
6. Given el panel maestro, when se muestra, then incluye el monto en valor absoluto y el porcentaje relativo al ingreso bruto

---

## Requirement 9: Motor ML (Machine Learning)

### User Story
Como comerciante, quiero que el sistema aprenda de mis patrones financieros y me alerte cuando algo se desvía significativamente.

### Acceptance Criteria
1. Given al menos 5 registros históricos, when el motor ML se activa, then calcula promedio móvil de 90 días
2. Given un valor actual, when la variación respecto al promedio móvil supera el 10%, then se dispara recalibración automática
3. Given menos de 5 registros, when se consulta predicción, then muestra mensaje "Datos insuficientes, se requieren mínimo 5 registros"
4. Given recalibración activa, when se completa, then actualiza los umbrales de alerta para el negocio
5. Given datos suficientes, when se genera predicción, then muestra tendencia con intervalo de confianza

---

## Requirement 10: Reportes Temporales

### User Story
Como comerciante, quiero generar reportes por diferentes períodos (diario, semanal, mensual, trimestral, semestral, anual) y comparar entre períodos.

### Acceptance Criteria
1. Given la vista de reportes, when selecciono un período, then genera reporte con granularidad: diario, semanal, mensual, trimestral, semestral o anual
2. Given dos períodos seleccionados, when activo comparativa, then muestra lado a lado con variación porcentual y absoluta
3. Given un reporte generado, when aplico filtro de texto, then filtra resultados por categoría o descripción
4. Given datos del período, when se genera reporte, then incluye totales, promedios y tendencia visual
5. Given un reporte, when solicito exportación, then permite descarga en formato compatible (PDF o CSV)

---

## Requirement 11: CI/CD GitHub + Railway

### User Story
Como desarrollador, quiero que el proyecto tenga despliegue automático desde GitHub a Railway con HTTPS y capacidad de rollback.

### Acceptance Criteria
1. Given un push a la rama main, when GitHub detecta el cambio, then Railway despliega automáticamente la nueva versión
2. Given el proyecto, when se despliega, then usa Dockerfile para construir la imagen
3. Given la aplicación desplegada, when un usuario accede, then la conexión es por HTTPS
4. Given un deploy fallido o con errores, when se detecta el problema, then se puede hacer rollback a la versión anterior
5. Given el pipeline, when se ejecuta, then corre los tests antes de desplegar (CI antes de CD)
