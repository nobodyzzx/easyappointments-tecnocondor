#!/usr/bin/env python3
"""
apply_config.py — Configuración programática de Easy!Appointments vía API REST.

Lee archivos YAML en deploy/config/ y los aplica a la instancia
de Easy!Appointments usando la API v1.

Orden de aplicación:
  1. working_plan (config global de horarios)
  2. holidays (feriados como working_plan_exceptions)
  3. service_categories
  4. services
  5. providers

Uso:
  pip install -r requirements.txt
  cp .env.example .env    # editar con API_TOKEN y API_BASE_URL
  python apply_config.py --dry-run    # simular sin cambios
  python apply_config.py              # aplicar (sin actualizar existentes)
  python apply_config.py --update     # aplicar y actualizar existentes

Flags:
  --dry-run   Simula las operaciones sin hacer cambios
  --update    Actualiza recursos existentes en lugar de omitirlos
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

# ── Colores ANSI ────────────────────────────────────────────────────────────

RESET = "\033[0m"
GREEN = "\033[32m"
BLUE = "\033[34m"
GRAY = "\033[90m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"


def log(action: str, message: str) -> None:
    colors = {
        "CREATED": GREEN,
        "UPDATED": BLUE,
        "SKIPPED": GRAY,
        "ERROR": RED,
        "WARN": YELLOW,
        "INFO": CYAN,
    }
    color = colors.get(action, RESET)
    tag = f"{BOLD}{color}[{action}]{RESET}"
    print(f"  {tag} {message}")


# ── Cliente API ─────────────────────────────────────────────────────────────

class APIClient:
    """Cliente HTTP para la API de Easy!Appointments v1."""

    def __init__(self, base_url: str, token: str, dry_run: bool = False):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self.dry_run = dry_run

    def get(self, endpoint: str) -> Any:
        resp = self.client.get(endpoint)
        resp.raise_for_status()
        return resp.json()

    def post(self, endpoint: str, data: dict) -> Any:
        if self.dry_run:
            return None
        resp = self.client.post(endpoint, json=data)
        resp.raise_for_status()
        return resp.json()

    def put(self, endpoint: str, data: dict) -> Any:
        if self.dry_run:
            return None
        resp = self.client.put(endpoint, json=data)
        resp.raise_for_status()
        return resp.json()

    def put_setting(self, name: str, value: str) -> Any:
        if self.dry_run:
            return None
        resp = self.client.put(f"/api/v1/settings/{name}", json={"value": value})
        resp.raise_for_status()
        return resp.json()


# ── Rutas de configuración ──────────────────────────────────────────────────

CONFIG_DIR = Path(__file__).parent.parent / "config"


def load_yaml(filename: str) -> dict:
    path = CONFIG_DIR / filename
    if not path.exists():
        log("ERROR", f"Archivo no encontrado: {path}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── 1. Working Plan ────────────────────────────────────────────────────────

def apply_working_plan(client: APIClient, config: dict, do_update: bool) -> None:
    plan = config["company_working_plan"]
    value = json.dumps(plan, ensure_ascii=False)

    if client.dry_run:
        log("INFO", f"Working plan: {value}")
        log("CREATED", "company_working_plan (dry-run)")
        return

    client.put_setting("company_working_plan", value)
    log("UPDATED", "company_working_plan")


# ── 2. Holidays ────────────────────────────────────────────────────────────

def apply_holidays(client: APIClient, config: dict, provider_ids: list[int]) -> None:
    holidays = config.get("holidays", [])
    if not holidays:
        log("WARN", "No hay feriados definidos")
        return

    for holiday in holidays:
        name = holiday["name"]
        if "date_start" in holiday and "date_end" in holiday:
            start = holiday["date_start"]
            end = holiday["date_end"]
        else:
            start = end = holiday["date"]

        for pid in provider_ids:
            data = {
                "startDate": start,
                "endDate": end,
                "startTime": None,
                "endTime": None,
                "breaks": [],
                "providerId": pid,
            }

            if client.dry_run:
                log("CREATED", f"Feriado '{name}' para provider {pid} ({start} a {end}) [dry-run]")
                continue

            existing = client.get(f"/api/v1/working_plan_exceptions?providerId={pid}")
            already = False
            for ex in existing:
                if ex["startDate"] == start and ex["endDate"] == end:
                    already = True
                    break

            if already:
                log("SKIPPED", f"Feriado '{name}' para provider {pid} ya existe")
            else:
                client.post("/api/v1/working_plan_exceptions", data)
                log("CREATED", f"Feriado '{name}' para provider {pid} ({start})")


# ── 3. Service Categories ──────────────────────────────────────────────────

def apply_categories(client: APIClient, config: dict, do_update: bool) -> dict[str, int]:
    categories = config.get("categories", [])
    existing = client.get("/api/v1/service_categories")
    by_name = {c["name"]: c for c in existing}
    name_to_id: dict[str, int] = {}

    for cat in categories:
        name = cat["name"]
        desc = cat.get("description", "")

        if name in by_name:
            cat_id = by_name[name]["id"]
            name_to_id[name] = cat_id
            if do_update:
                data = {"name": name, "description": desc}
                if client.dry_run:
                    log("UPDATED", f"Categoría '{name}' (dry-run)")
                else:
                    client.put(f"/api/v1/service_categories/{cat_id}", data)
                    log("UPDATED", f"Categoría '{name}'")
            else:
                log("SKIPPED", f"Categoría '{name}' ya existe")
        else:
            data = {"name": name, "description": desc}
            if client.dry_run:
                log("CREATED", f"Categoría '{name}' (dry-run)")
                name_to_id[name] = -1
            else:
                result = client.post("/api/v1/service_categories", data)
                cat_id = result["id"]
                name_to_id[name] = cat_id
                log("CREATED", f"Categoría '{name}' (ID: {cat_id})")

    return name_to_id


# ── 4. Services ────────────────────────────────────────────────────────────

def apply_services(client: APIClient, config: dict, category_map: dict[str, int], do_update: bool) -> dict[str, int]:
    services = config.get("services", [])
    existing = client.get("/api/v1/services")
    by_name = {s["name"]: s for s in existing}
    name_to_id: dict[str, int] = {}

    for svc in services:
        name = svc["name"]
        cat_id = category_map.get(svc.get("category"))
        buffers = svc.get("buffers", {})

        data = {
            "name": name,
            "duration": svc["duration"],
            "description": svc.get("description", ""),
            "serviceCategoryId": cat_id,
            "slotInterval": 15,
            "attendantsNumber": svc.get("attendants_number", 1),
            "isPrivate": svc.get("is_private", False),
            "price": 0,
            "currency": "",
            "location": "",
        }

        if cat_id is None:
            log("WARN", f"Servicio '{name}': categoría '{svc.get('category')}' no encontrada")

        if name in by_name:
            svc_id = by_name[name]["id"]
            name_to_id[name] = svc_id
            if do_update:
                if client.dry_run:
                    log("UPDATED", f"Servicio '{name}' (dry-run)")
                else:
                    client.put(f"/api/v1/services/{svc_id}", data)
                    log("UPDATED", f"Servicio '{name}'")
            else:
                log("SKIPPED", f"Servicio '{name}' ya existe")
        else:
            if client.dry_run:
                log("CREATED", f"Servicio '{name}' (dry-run)")
                name_to_id[name] = -1
            else:
                result = client.post("/api/v1/services", data)
                svc_id = result["id"]
                name_to_id[name] = svc_id
                log("CREATED", f"Servicio '{name}' (ID: {svc_id})")

    return name_to_id


# ── 5. Providers ───────────────────────────────────────────────────────────

def apply_providers(
    client: APIClient,
    config: dict,
    service_map: dict[str, int],
    do_update: bool,
) -> list[int]:
    providers = config.get("providers", [])
    existing = client.get("/api/v1/providers")
    by_email = {p["email"]: p for p in existing}

    admins = client.get("/api/v1/admins")
    admin_emails = {a["email"]: a for a in admins}

    created_ids: list[int] = []

    for prov in providers:
        email = prov["email"]
        full_name = f"{prov['first_name']} {prov['last_name']}"
        service_ids = [service_map[s] for s in prov.get("services", []) if s in service_map]

        if email in by_email:
            prov_id = by_email[email]["id"]
            created_ids.append(prov_id)
            log("SKIPPED", f"Proveedor '{full_name}' ya existe")
        elif email in admin_emails:
            admin = admin_emails[email]
            admin_name = f"{admin['firstName']} {admin['lastName']}"
            created_ids.append(-1)
            log("SKIPPED", f"'{full_name}' ya existe como admin (ID: {admin['id']}). Crear como provider manualmente si se necesita")
        else:
            if client.dry_run:
                log("CREATED", f"Proveedor '{full_name}' (dry-run)")
                created_ids.append(-1)
            else:
                settings = build_provider_settings(prov, is_new=True)
                data = {
                    "firstName": prov["first_name"],
                    "lastName": prov["last_name"],
                    "email": email,
                    "services": service_ids,
                    "settings": settings,
                }
                result = client.post("/api/v1/providers", data)
                prov_id = result["id"]
                created_ids.append(prov_id)
                log("CREATED", f"Proveedor '{full_name}' (ID: {prov_id})")

    return created_ids


def build_provider_settings(prov: dict, is_new: bool = False) -> dict:
    settings = {
        "username": prov["email"].split("@")[0],
        "notifications": True,
        "calendarView": "default",
    }

    if is_new:
        settings["password"] = prov.get("password", "changeme123")

    return settings


# ── Principal ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Configurar Easy!Appointments vía API REST")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin hacer cambios")
    parser.add_argument("--update", action="store_true", help="Actualizar recursos existentes")
    args = parser.parse_args()

    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    base_url = os.getenv("API_BASE_URL", "https://agenda.tecnocondor.dev")
    token = os.getenv("API_TOKEN")
    if not token:
        print(f"{RED}[ERROR] API_TOKEN no definida en {env_path}{RESET}")
        sys.exit(1)

    client = APIClient(base_url, token, dry_run=args.dry_run)
    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Easy!Appointments — Configuración automática [{mode}]{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    provider_ids: list[int] = []

    # 1. Working plan
    print(f"{BOLD}[1/5] Working Plan{RESET}")
    wp = load_yaml("working_plan.yml")
    apply_working_plan(client, wp, args.update)

    # 2. Categories (necesarias antes de services)
    print(f"\n{BOLD}[2/5] Categorías{RESET}")
    cat_config = load_yaml("service_categories.yml")
    category_map = apply_categories(client, cat_config, args.update)

    # 3. Services
    print(f"\n{BOLD}[3/5] Servicios{RESET}")
    svc_config = load_yaml("services.yml")
    service_map = apply_services(client, svc_config, category_map, args.update)

    # 4. Providers
    print(f"\n{BOLD}[4/5] Proveedores{RESET}")
    prov_config = load_yaml("providers.yml")
    provider_ids = apply_providers(client, prov_config, service_map, args.update)

    # 5. Holidays (después de tener proveedores)
    print(f"\n{BOLD}[5/5] Feriados{RESET}")
    hol_config = load_yaml("holidays.yml")
    all_provider_ids = [p["id"] for p in client.get("/api/v1/providers")]
    if all_provider_ids:
        apply_holidays(client, hol_config, all_provider_ids)
    else:
        log("WARN", "Sin proveedores válidos para asignar feriados")

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Configuración completada [{mode}]{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
