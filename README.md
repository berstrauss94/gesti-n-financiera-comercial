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
