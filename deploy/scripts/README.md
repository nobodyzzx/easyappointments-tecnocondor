# Configuración programática de Easy!Appointments

Scripts y configuración para automatizar la configuración de Easy!Appointments
vía API REST.

## Estructura

```
scripts/
├── apply_config.py      # Script principal
├── .env                 # API key (NO commitear — crear desde .env.example)
├── .env.example         # Plantilla de variables
└── requirements.txt     # Dependencias Python

../config/
├── working_plan.yml     # Horario global de la empresa
├── holidays.yml         # Feriados (excepciones al plan)
├── service_categories.yml  # Categorías de servicios
├── services.yml         # Catálogo de servicios
└── providers.yml        # Proveedores
```

## Prerrequisitos

- Python 3.10+
- Una API key válida de Easy!Appointments

## Generar API Key

1. Iniciar sesión como admin en https://agenda.tecnocondor.dev
2. Ir a **Settings** (engranaje) → pestaña **API**
3. Click en **New Key**
4. Copiar la key generada
5. Crear archivo `.env` en esta carpeta:

```bash
cp .env.example .env
```

6. Editar `.env` y pegar la key:

```
API_BASE_URL=https://agenda.tecnocondor.dev
API_TOKEN=tu-api-key-aqui
```

## Instalar dependencias

```bash
cd deploy/scripts
pip install -r requirements.txt
```

## Ejecutar

### Simular sin cambios (recomendado primero)

```bash
python apply_config.py --dry-run
```

### Aplicar configuración (no sobrescribe existentes)

```bash
python apply_config.py
```

### Aplicar y actualizar existentes

```bash
python apply_config.py --update
```

## Output

El script muestra el progreso con colores:

| Color | Significado |
|-------|-------------|
| Verde CREATED | Recurso creado nuevo |
| Azul UPDATED | Recurso actualizado (solo con --update) |
| Gris SKIPPED | Recurso ya existe, se omite |
| Rojo ERROR | Error en la operación |
| Amarillo WARN | Advertencia no bloqueante |

## Orden de aplicación

1. **Working Plan** — Horario global (L-V 09:00-18:00, break 13:00-14:00, fines de semana cerrado)
2. **Categorías** — Comercial, Técnico, Soporte
3. **Servicios** — 6 servicios con duración y descripción
4. **Proveedores** — Harold (skip si existe), Valeria (nuevo)
5. **Feriados** — 8 feriados bolivianos 2026 para todos los proveedores

## Agregar nuevos recursos

### Nuevo servicio

Editar `../config/services.yml`:

```yaml
services:
  - name: "Nuevo Servicio"
    duration: 45
    category: "Comercial"
    description: "Descripción que verá el cliente"
    buffers:
      before: 15
      after: 15
    attendants_number: 1
    is_private: false
```

### Nueva categoría

Editar `../config/service_categories.yml`:

```yaml
categories:
  - name: "Nueva Categoría"
    description: "Descripción"
    color: "#FF5733"
```

### Nuevo proveedor

Editar `../config/providers.yml`:

```yaml
providers:
  - first_name: "Nombre"
    last_name: "Apellido"
    email: "email@ejemplo.com"
    services:
      - "Nombre del Servicio"
    working_plan: "inherit"
    password: "temporal123"
```

### Nuevos feriados

Editar `../config/holidays.yml`. Para un solo día:

```yaml
holidays:
  - name: "Feriado nuevo"
    date: "2026-03-15"
```

Para un rango (como Carnaval):

```yaml
  - name: "Carnaval"
    date_start: "2026-02-16"
    date_end: "2026-02-17"
```

## Idempotencia

El script es idempotente: puede ejecutarse múltiples veces sin duplicar
recursos. Usa el patrón GET → indexar → CREATE/UPDATE/SKIP.

## Notas

- Los feriados se aplican como `working_plan_exceptions` (día cerrado) a todos los proveedores
- Harold Navía tiene `skip_if_exists: true` — se omite si ya existe
- Los servicios sin categoría válida muestran un WARN pero no fallan
