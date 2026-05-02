# Despliegue en Tecnocondor

Easy!Appointments self-hosted en `agenda.tecnocondor.dev` vía Dokploy en VPS Netcup.

Este fork mantiene la base del proyecto upstream intacta y agrega solo la carpeta `deploy/` con la configuración específica del despliegue de Tecnocondor.

## Configuración en Dokploy

| Campo | Valor |
|---|---|
| Provider | Git |
| Repository URL | `https://github.com/nobodyzzx/easyappointments-tecnocondor.git` |
| Branch | `deploy/tecnocondor` |
| Compose Path | `./deploy/tecnocondor.yml` |
| Domain | `agenda.tecnocondor.dev` → service `nginx` → port `80` |

Las variables sensibles (passwords MySQL) se configuran en **Dokploy → Environment**, nunca en este repo. Ver `.env.example` para la lista de variables requeridas.

## Bind mounts en el host (VPS)

| Ruta del host | Ruta del contenedor | UID:GID |
|---|---|---|
| `/home/nobodyzz/backups_tecnocondor/easyappointments/mysql` | `/var/lib/mysql` | 999:999 |
| `/home/nobodyzz/backups_tecnocondor/easyappointments/storage` | `/var/www/html/storage` | 33:33 |

Las carpetas se respaldan automáticamente vía el cron de rsync de las 8:00 AM hacia la máquina local de Harold.

## Arquitectura

Tres servicios en `deploy/tecnocondor.yml`:

- **php-fpm** — backend PHP, build local desde `docker/php-fpm/Dockerfile` del upstream
- **nginx** — web server, imagen oficial Alpine, monta `nginx.conf` del upstream
- **mysql** — base de datos, imagen oficial 8.0

El código de la aplicación vive en el clone que Dokploy hace del repo y se monta vía volume en `php-fpm` y `nginx`. Esto permite que cambiar de versión solo requiera cambiar de tag en Git, sin rebuild de imagen.

## Actualizar a una versión nueva

Cuando salga una versión nueva del upstream (por ejemplo `1.6.0-beta.3`):

```fish
cd ~/Projects/easyappointments-tecnocondor
git fetch upstream --tags
git checkout 1.6.0-beta.3
git checkout -b deploy/tecnocondor-1.6.0-beta.3

# Traer la carpeta deploy/ desde la rama anterior
git checkout deploy/tecnocondor -- deploy/

git push -u origin deploy/tecnocondor-1.6.0-beta.3
```

En Dokploy: cambiar **Branch** al nombre de la nueva rama → **Save** → **Deploy**.

## Backup antes de upgrade (recomendado en betas)

```bash
ssh nobodyzz@152.53.164.104
docker exec $(docker ps -q -f name=easyappointments.*mysql) \
  mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" easyappointments \
  > /home/nobodyzz/backups_tecnocondor/easyappointments/pre-upgrade-$(date +%Y%m%d).sql
```

## Rollback

Si una versión nueva rompe algo:

1. En Dokploy → Branch → cambiar al nombre de la rama anterior estable
2. Save → Deploy
3. Si la migración de DB rompió datos, restaurar el dump:

```bash
docker exec -i $(docker ps -q -f name=easyappointments.*mysql) \
  mysql -u root -p"$MYSQL_ROOT_PASSWORD" easyappointments \
  < /home/nobodyzz/backups_tecnocondor/easyappointments/pre-upgrade-YYYYMMDD.sql
```

## Setup inicial

Tras el primer Deploy exitoso, la app expone el wizard de instalación en:

`https://agenda.tecnocondor.dev/installation`

Configurar:
1. Email + password del primer admin
2. Datos de Tecnocondor (nombre, dirección, teléfono)
3. Validar acceso con login

Después, ir a **Settings → Integrations** y configurar Jitsi (más simple) o Google Calendar (requiere OAuth).
