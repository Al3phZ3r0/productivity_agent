"""
DSPy Tools para Google Calendar y ClickUp.
El agente ReAct invoca estas funciones para leer eventos y crear tareas.
"""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from connectors.google_calendar import GoogleCalendarConnector
from connectors.clickup import ClickUpConnector
from config.settings import config

# Instancias reutilizables (se inicializan una sola vez)
_calendar = GoogleCalendarConnector()
_clickup = ClickUpConnector()
_tz = ZoneInfo(config.TIMEZONE)


def _calculate_duration_minutes(start_time: str, end_time: str) -> int:
    """Calcula la duración en minutos entre dos timestamps ISO 8601."""
    try:
        start = datetime.fromisoformat(start_time)
        end = datetime.fromisoformat(end_time)
        return max(0, int((end - start).total_seconds() / 60))
    except Exception:
        return 0


def get_today_calendar_events() -> str:
    """
    Obtiene todos los eventos del calendario de hoy.
    Retorna un JSON con la lista de reuniones (título, hora inicio, hora fin,
    duración en minutos y asistentes).
    Úsala para saber qué reuniones tiene el usuario agendadas hoy.
    """
    events = _calendar.get_events_today()

    if not events:
        return json.dumps({"events": [], "message": "No hay eventos agendados para hoy."})

    parsed = []
    for e in events:
        duration_min = _calculate_duration_minutes(e["start"], e["end"])
        parsed.append({
            "title": e["title"],
            "start": e["start"],
            "end": e["end"],
            "duration_minutes": duration_min,
            "attendees": e["attendees"],
            "meet_link": e["meet_link"],
            "description": e["description"][:200] if e["description"] else "",
        })

    return json.dumps({"events": parsed, "total": len(parsed)}, ensure_ascii=False)


def create_clickup_task_for_meeting(title: str, start_time: str, end_time: str, attendees: str = "") -> str:
    """
    Crea una tarea en ClickUp para una reunión del calendario y registra
    automáticamente el tiempo de duración de la reunión en la tarea.
    Antes de crearla, verifica que no exista ya una tarea con ese nombre para evitar duplicados.

    Parámetros:
        title: Nombre de la reunión (será el nombre de la tarea)
        start_time: Hora de inicio en formato ISO 8601 (e.g. "2025-02-26T09:00:00-06:00")
        end_time: Hora de fin en formato ISO 8601
        attendees: Lista de asistentes separados por coma (opcional)

    Retorna un JSON indicando si la tarea fue creada, el tiempo registrado, o si ya existía.
    """
    # Calcular duración antes de cualquier cosa
    duration_min = _calculate_duration_minutes(start_time, end_time)
    duration_ms = duration_min * 60 * 1000

    # Verificar duplicado
    existing = _clickup.task_exists_with_name('DE: '+title)
    if existing:
        return json.dumps({
            "status": "already_exists",
            "task_id": existing["id"],
            "message": f"Ya existe una tarea para '{title}', no se creó duplicado."
        })

    # Construir descripción
    description_parts = ["📅 Reunión agendada en Google Calendar"]
    if start_time:
        description_parts.append(f"🕐 Inicio: {start_time}")
    if end_time:
        description_parts.append(f"🕑 Fin: {end_time}")
    if duration_min:
        description_parts.append(f"⏱️ Duración: {duration_min} minutos")
    if attendees:
        description_parts.append(f"👥 Asistentes: {attendees}")

    description = "\n".join(description_parts)

    # due_date = hora de inicio de la reunión en ms
    due_date_ms = None
    try:
        dt = datetime.fromisoformat(start_time)
        due_date_ms = int(dt.timestamp() * 1000)
    except Exception:
        pass

    # Crear la tarea
    task = _clickup.create_task(
        name='DE: '+title,
        description=description,
        due_date=due_date_ms,
        tags=["reunión", "calendar-sync"],
    )
    task_id = task["id"]

    # Registrar tiempo de duración automáticamente
    # Se pasa start_time para que el tiempo quede en la fecha real de la reunión,
    # no en la fecha en que se corre el agente.
    time_logged = False
    if duration_ms > 0:
        try:
            _clickup.log_time(
                task_id=task_id,
                duration_ms=duration_ms,
                description=f"Duración de la reunión: {duration_min} min",
                start_time=start_time,
            )
            time_logged = True
        except Exception as e:
            print(f"⚠️  No se pudo registrar tiempo en tarea '{title}': {e}")

    return json.dumps({
        "status": "created",
        "task_id": task_id,
        "task_url": task.get("url", ""),
        "duration_minutes": duration_min,
        "time_logged": time_logged,
        "message": (
            f"Tarea '{title}' creada en ClickUp. "
            f"Duración registrada: {duration_min} min." if time_logged
            else f"Tarea '{title}' creada en ClickUp (sin tiempo registrado)."
        )
    })


def get_existing_clickup_tasks() -> str:
    """
    Obtiene las tareas actuales en ClickUp.
    Úsala para verificar qué tareas ya existen antes de crear nuevas,
    o para tener contexto de lo que ya está registrado.
    Retorna un JSON con la lista de tareas (id, nombre, status).
    """
    tasks = _clickup.get_all_tasks()
    simplified = [
        {
            "id": t["id"],
            "name": t["name"],
            "status": t.get("status", {}).get("status", "unknown"),
            "due_date": t.get("due_date", ""),
        }
        for t in tasks
    ]
    return json.dumps({"tasks": simplified, "total": len(simplified)}, ensure_ascii=False)

def get_calendar_events_for_date(date_str: str) -> str:
    """
    Obtiene los eventos del calendario para una fecha específica.
    date_str: fecha en formato YYYY-MM-DD (e.g. "2026-02-25")
    Retorna un JSON con la lista de reuniones.
    """
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        target = target.replace(tzinfo=_tz)
    except ValueError:
        return json.dumps({"error": f"Formato de fecha inválido: '{date_str}'. Usa YYYY-MM-DD."})

    events = _calendar.get_events_for_date(target)

    if not events:
        return json.dumps({"events": [], "message": f"No hay eventos para {date_str}."})

    parsed = []
    for e in events:
        duration_min = _calculate_duration_minutes(e["start"], e["end"])
        parsed.append({
            "title": e["title"],
            "start": e["start"],
            "end": e["end"],
            "duration_minutes": duration_min,
            "attendees": e["attendees"],
            "meet_link": e["meet_link"],
            "description": e["description"][:200] if e["description"] else "",
        })

    return json.dumps({"events": parsed, "total": len(parsed)}, ensure_ascii=False)