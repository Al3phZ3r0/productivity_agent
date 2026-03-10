"""
Conector para ClickUp API v2.
Docs: https://clickup.com/api/
"""
import requests
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from config.settings import config

# ─── Custom Fields ────────────────────────────────────────────────────────────

SPRINT_ARKON_FIELD_ID = "d0c016df-e09a-492e-a7a2-cc92e1993627"

# Punto de anclaje: sprint c08 empezó el lunes 23 de febrero de 2026
# Cada sprint dura 2 semanas (14 días). A partir de aquí se calcula cualquier sprint.
SPRINT_ANCHOR_DATE = date(2026, 2, 23)  # lunes inicio de c08
SPRINT_ANCHOR_NUMBER = 8

SPRINT_OPTIONS: Dict[str, str] = {
    "2026c08": "cae799cd-e932-4f1e-91ba-a2b57c577b75",
    "2026c07": "277a358e-e245-47ae-9398-9283d50dca88",
    "2026c06": "23bdb71e-04dc-4622-85ce-5a47a375fd0d",
    "2026c05": "9a664fde-54c9-4fa5-afe8-77e6ec09e9b0",
    "2026c04": "bdedb19c-5d9c-4c6a-b09b-cdaf8b23c6b7"
}

def get_current_sprint_label(for_date: Optional[date] = None) -> str:
    """
    Calcula el label del sprint activo para una fecha dada (default: hoy).
    Lógica: desde el anclaje c08 (2026-02-23), cada sprint dura 14 días.
    Formato de salida: '2026c08', '2026c09', etc.
    """
    target = for_date or date.today()
    delta_days = (target - SPRINT_ANCHOR_DATE).days

    if delta_days < 0:
        # Fecha anterior al anclaje — calcular hacia atrás
        sprint_offset = -((-delta_days - 1) // 14 + 1)
    else:
        sprint_offset = delta_days // 14

    sprint_number = SPRINT_ANCHOR_NUMBER + sprint_offset
    year = target.year
    return f"{year}c{sprint_number:02d}"


def get_current_sprint_option_id(for_date: Optional[date] = None) -> Optional[str]:
    """
    Retorna el option_id del sprint activo.
    Retorna None si el sprint no está en SPRINT_OPTIONS todavía.
    """
    label = get_current_sprint_label(for_date)
    return SPRINT_OPTIONS.get(label)

# ─── Conector ─────────────────────────────────────────────────────────────────

class ClickUpConnector:
    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self):
        self.headers = {
            "Authorization": config.CLICKUP_API_TOKEN,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        self.list_id = config.CLICKUP_LIST_ID

    def _get(self, endpoint: str, params: dict = None) -> dict:
        response = requests.get(
            f"{self.BASE_URL}/{endpoint}",
            headers=self.headers,
            params=params or {}
        )
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.BASE_URL}/{endpoint}",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def _put(self, endpoint: str, payload: dict) -> dict:
        response = requests.put(
            f"{self.BASE_URL}/{endpoint}",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def create_task(
        self,
        name: str,
        description: str = "",
        due_date: Optional[int] = None,   # timestamp en ms
        tags: List[str] = None,
        set_current_sprint: bool = True,
    ) -> Dict:
        """Crea una tarea en la lista configurada.
        Asigna automáticamente el Sprint Arkon activo si set_current_sprint=True."""
        payload = {
            "name": name,
            "description": description,
            }
        if due_date:
            payload["due_date"] = due_date

        if set_current_sprint:
            sprint_label = get_current_sprint_label()
            sprint_id = get_current_sprint_option_id()
            if sprint_id:
                payload["custom_fields"] = [
                    {
                        "id": SPRINT_ARKON_FIELD_ID,
                        "value": [sprint_id],
                    }
                ]
                print(f"   📅 Sprint asignado: {sprint_label}")
            else:
                print(f"   ⚠️  Sprint '{sprint_label}' no tiene option_id — agrégalo a SPRINT_OPTIONS en clickup.py")

        task = self._post(f"list/{self.list_id}/task", payload)
        print(f"✅ Tarea creada en ClickUp: '{name}' (id: {task['id']})")
        return task

    def set_sprint(self, task_id: str, sprint_label: Optional[str] = None) -> bool:
            """
            Asigna Sprint Arkon a una tarea existente.
            Si sprint_label es None usa el sprint activo de hoy.
            """
            label = sprint_label or get_current_sprint_label()
            option_id = SPRINT_OPTIONS.get(label)

            if not option_id:
                print(f"⚠️  Sprint '{label}' no encontrado en SPRINT_OPTIONS")
                return False

            self._post(f"task/{task_id}/field/{SPRINT_ARKON_FIELD_ID}", {
                "value": [option_id]
            })
            print(f"✅ Sprint '{label}' asignado a tarea {task_id}")
            return True

    def get_tasks_today(self) -> List[Dict]:
        """Obtiene tareas de la lista con due_date hoy."""
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(config.TIMEZONE)
        now = datetime.now(tz)
        start_ms = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000)
        end_ms = int(now.replace(hour=23, minute=59, second=59).timestamp() * 1000)

        result = self._get(f"list/{self.list_id}/task", {
            "due_date_gt": start_ms,
            "due_date_lt": end_ms,
        })
        return result.get("tasks", [])

    def get_all_tasks(self, include_closed: bool = False) -> List[Dict]:
        """Obtiene todas las tareas de la lista."""
        params = {}
        if include_closed:
            params["include_closed"] = "true"
        result = self._get(f"list/{self.list_id}/task", params)
        return result.get("tasks", [])

    def update_task_description(self, task_id: str, new_description: str) -> Dict:
        """Actualiza la descripción de una tarea existente."""
        return self._put(f"task/{task_id}", {"description": new_description})

    def log_time(
        self,
        task_id: str,
        duration_ms: int,
        description: str = "",
        start_time: Optional[str] = None,  # ISO 8601, e.g. "2026-02-25T09:00:00-06:00"
    ) -> Dict:
        """
        Registra tiempo en una tarea.
        duration_ms: duración en milisegundos (e.g. 3600000 = 1 hora)
        start_time: hora de inicio real (ISO 8601). Si no se pasa, usa datetime.now().
                    Siempre pasa start_time para que el tiempo quede en la fecha correcta.
        Nota: ClickUp requiere 'time' (no 'duration') y el campo 'end' = start + duration_ms. Aunque esto es legacy
        """
        if start_time:
            try:
                start_ms = int(datetime.fromisoformat(start_time).timestamp() * 1000)
            except ValueError:
                start_ms = int(datetime.now().timestamp() * 1000)
        else:
            start_ms = int(datetime.now().timestamp() * 1000)

        payload = {
            "time": duration_ms,
            "description": description,
            "start": start_ms,
            "end": start_ms + duration_ms,
        }
        result = self._post(f"task/{task_id}/time", payload)
        print(f"✅ Tiempo registrado en tarea {task_id}: {duration_ms // 60000} min")
        return result

    def task_exists_with_name(self, name: str) -> Optional[Dict]:
        """Busca si ya existe una tarea con ese nombre exacto (evita duplicados)."""
        tasks = self.get_all_tasks()
        for task in tasks:
            if task.get("name", "").strip().lower() == name.strip().lower():
                return task
        return None

    def test_connection(self) -> bool:
        try:
            self._get(f"list/{self.list_id}")
            print("✅ ClickUp: conexión exitosa")
            return True
        except Exception as e:
            print(f"❌ ClickUp: error → {e}")
            return False
