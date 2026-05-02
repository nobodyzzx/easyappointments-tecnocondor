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
└── services.yml         # Catálogo de servicios
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

1. **Working Plan** — Horario global
2. **Categorías** — Comercial, Técnico, Soporte
3. **Servicios** — Con nombre, duración y categoría

## Formato de servicios

```yaml
services:
  - name: "Nombre del servicio"
    category: "Nombre categoría"     # OBLIGATORIO
    duration: 30                     # minutos
```

La categoría debe coincidir con un nombre definido en `service_categories.yml`.

## Idempotencia

El script es idempotente: puede ejecutarse múltiples veces sin duplicar
recursos. Usa el patrón GET → indexar → CREATE/UPDATE/SKIP.
