# Gestión Financiera Comercial

Sistema de gestión financiera para comercios, con semáforo de calor, motor ML predictivo y reportes comparativos.

## Stack Tecnológico

- **Backend**: Python 3.12 + Flask
- **Base de Datos**: PostgreSQL (Railway)
- **ML**: NumPy, Pandas, Scikit-learn
- **Deploy**: Docker + Railway (auto-deploy desde GitHub)
- **CI/CD**: GitHub Actions → Railway

## Funcionalidades Principales

1. **Registro/Login** con validaciones estrictas y multi-tenant
2. **Ingreso Bruto Diario** como base 100% para cálculos
3. **Mapa de Calor** con semáforo de 5 colores (🟢🟡🟠🔴🚨)
4. **Salarios y Retiros** con umbrales independientes
5. **Gastos Variables** - 8 categorías con umbrales propios
6. **Costos Operativos** - Fijos con control por categoría
7. **Panel Ganancia Neta** - Semáforo maestro de salud financiera
8. **Motor ML** - Promedio móvil 90 días, alertas de desviación
9. **Reportes Temporales** - Diario a anual, comparativa entre períodos

## Desarrollo Local

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env

# Correr servidor de desarrollo
flask run --debug
```

## Deploy

El deploy es automático: push a `main` → Railway despliega via Dockerfile.

### Variables de Entorno (Railway)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `FLASK_SECRET_KEY` | Clave secreta para sesiones Flask | String aleatorio largo |
| `SESSION_TIMEOUT_MINUTES` | Minutos de inactividad antes de expirar sesión | `30` |
| `MAX_LOGIN_ATTEMPTS` | Intentos máximos de login antes de lockout | `5` |

### Pipeline CI/CD

1. **Push a `main`** o apertura de PR dispara GitHub Actions
2. **CI (GitHub Actions)** ejecuta:
   - Instalación de dependencias
   - Lint con flake8 (no bloqueante)
   - Tests unitarios con cobertura (`pytest --cov=app`)
   - Tests de propiedades (`pytest tests/property/ -x`)
   - Verificación de migraciones (`flask db upgrade`)
3. **CD (Railway)** despliega automáticamente tras push exitoso a `main`

### HTTPS

Railway proporciona HTTPS por defecto para todos los deployments. No se requiere configuración adicional de certificados SSL.

### Rollback

Railway mantiene automáticamente los últimos 5 deploys. Para hacer rollback:

1. Ir al dashboard de Railway → proyecto → pestaña "Deployments"
2. Identificar el deploy anterior que funcionaba correctamente
3. Click en "Redeploy" en ese deploy específico
4. Railway restaura la versión anterior en segundos

### Migraciones

Las migraciones de base de datos se ejecutan automáticamente al inicio del contenedor, antes de arrancar el servidor web. El comando `flask db upgrade` se ejecuta en el entrypoint del Dockerfile y en el `startCommand` de Railway.

## Estructura del Proyecto

```
├── app/
│   ├── __init__.py          # Application factory
│   ├── models/              # SQLAlchemy models
│   ├── routes/              # API endpoints
│   └── services/            # Business logic (heatmap, ML)
├── tests/                   # Test suite
├── Dockerfile               # Container build
├── railway.toml             # Railway config
├── requirements.txt         # Python deps
└── .kiro/specs/             # Feature specs
```
