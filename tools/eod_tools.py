"""
DSPy Tools para el flujo EOD (End of Day).
El agente recibe lo que el usuario hizo en el día y decide si crear
una tarea nueva o agregar tiempo a una tarea existente en ClickUp.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from connectors.clickup import ClickUpConnector, SPRINT_ARKON_FIELD_ID, SPRINT_OPTIONS, get_current_sprint_label, get_current_sprint_option_id
#from connectors.cortex import CortexConnector
from config.settings import config

_tz = ZoneInfo(config.TIMEZONE)

# Conector apuntando a la lista de tareas (no la de reuniones)
_clickup = ClickUpConnector()
_clickup.list_id = config.CLICKUP_TASKS_LIST_ID

#_cortex = CortexConnector()


def get_existing_tasks() -> str:
    """
    Obtiene todas las tareas abiertas en la lista de tareas de ClickUp.
    Úsala para decidir si el trabajo que reporta el usuario corresponde
    a una tarea existente (agregar tiempo) o es una nueva (crear tarea).
    Retorna JSON con id, nombre y status de cada tarea.
    """
    tasks = _clickup.get_all_tasks()
    simplified = [
        {
            "id": t["id"],
            "name": t["name"],
            "status": t.get("status", {}).get("status", "unknown"),
        }
        for t in tasks
    ]
    return json.dumps({"tasks": simplified, "total": len(simplified)}, ensure_ascii=False)


def create_task(name: str, description: str = "", estimated_minutes: int = 0) -> str:
    """
    Crea una nueva tarea en la lista de tareas de ClickUp.
    Úsala cuando el trabajo reportado no corresponde a ninguna tarea existente.

    Parámetros:
        name: nombre descriptivo de la tarea
        description: detalle de lo que se hizo
        estimated_minutes: tiempo estimado/trabajado en minutos (0 si no se especificó)
    """
    task = _clickup.create_task(
        name='DE: '+name,
        description=description,
        tags=["eod", "slack-report"],
        set_current_sprint=True,
    )
    task_id = task["id"]

    # Si se indicó tiempo, registrarlo
    if estimated_minutes > 0:
        duration_ms = estimated_minutes * 60 * 1000
        start_time_iso = datetime.now(_tz).isoformat()
        try:
            _clickup.log_time(
                task_id=task_id,
                duration_ms=duration_ms,
                description=f"Tiempo reportado vía Slack EOD",
                start_time=start_time_iso,
            )
        except Exception as e:
            print(f"⚠️  No se pudo registrar tiempo: {e}")

    return json.dumps({
        "status": "created",
        "task_id": task_id,
        "task_url": task.get("url", ""),
        "message": f"Tarea '{name}' creada" + (f" con {estimated_minutes} min registrados." if estimated_minutes > 0 else ".")
    })


def add_time_to_task(task_id: str, minutes: int, notes: str = "") -> str:
    """
    Agrega tiempo trabajado a una tarea existente en ClickUp.
    Úsala cuando el trabajo reportado corresponde a una tarea que ya existe.

    Parámetros:
        task_id: ID de la tarea existente (obtenido de get_existing_tasks)
        minutes: minutos trabajados
        notes: descripción de lo que se hizo en ese tiempo
    """
    if minutes <= 0:
        return json.dumps({"status": "error", "message": "Los minutos deben ser mayor a 0."})

    duration_ms = minutes * 60 * 1000
    start_time_iso = datetime.now(_tz).isoformat()

    try:
        _clickup.log_time(
            task_id=task_id,
            duration_ms=duration_ms,
            description=notes or "Tiempo registrado vía Slack EOD",
            start_time=start_time_iso,
        )
        return json.dumps({
            "status": "logged",
            "task_id": task_id,
            "minutes": minutes,
            "message": f"{minutes} min registrados en tarea {task_id}."
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_cortex_context(query: str) -> str:
    """
    Consulta Cortex para obtener contexto relevante sobre el trabajo del usuario.
    Úsala para entender mejor el contexto de lo que reporta el usuario,
    por ejemplo para identificar a qué proyecto o tarea pertenece su trabajo.

    Parámetros:
        query: pregunta o tema a consultar en Cortex
    """
    try:
        context = _cortex.query_context(query, limit=5)
        return context or "No se encontró contexto relevante en Cortex."
    except Exception as e:
        return f"Error consultando Cortex: {e}"
