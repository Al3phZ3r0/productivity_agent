"""
Flujo Morning Sync: Google Calendar → ClickUp
El agente lee los eventos del día y crea una tarea en ClickUp por cada reunión.

Uso:
    python main.py morning                  → sincroniza hoy
    python main.py morning --date 2026-02-25  → sincroniza una fecha específica
    Desde Slack bot: resuelve el calendar_id del usuario via Cortex
"""
import dspy
from datetime import datetime, date
from typing import Optional
from zoneinfo import ZoneInfo

from config.settings import config
from tools.calendar_tools import (
    get_today_calendar_events,
    get_calendar_events_for_date,
    create_clickup_task_for_meeting,
    get_existing_clickup_tasks,
)


def build_agent(target_date: date) -> dspy.ReAct:
    """Construye el agente ReAct con las tools del Morning Sync."""

    # Wrap get_calendar_events_for_date con la fecha ya fijada
    # para que el agente no tenga que pasarla como argumento
    date_str = target_date.strftime("%Y-%m-%d")

    def get_events_for_day() -> str:
        """
        Obtiene todos los eventos del calendario para el día configurado.
        Retorna un JSON con la lista de reuniones (título, hora inicio, hora fin, asistentes).
        """
        return get_calendar_events_for_date(date_str)

    return dspy.ReAct(
        signature=MorningSyncSignature,
        tools=[
            get_events_for_day,
            create_clickup_task_for_meeting,
            get_existing_clickup_tasks,
        ],
        max_iters=15,
    )


class MorningSyncSignature(dspy.Signature):
    """
    Eres un asistente de productividad. Tu tarea es sincronizar las reuniones
    del calendario de Google con ClickUp.

    Proceso:
    1. Obtén los eventos del calendario del día.
    2. Para cada evento/reunión encontrado, crea una tarea en ClickUp con el
       nombre de la reunión, hora de inicio, hora de fin y asistentes.
    3. Si ya existe una tarea con ese nombre, NO la dupliques.
    4. Al final, reporta cuántas tareas creaste y cuáles ya existían.
    """
    result: str = dspy.OutputField(
        desc="Resumen de lo que hiciste: cuántas tareas creaste, cuáles ya existían, y si hubo errores."
    )


def run_morning_sync(target_date: Optional[date] = None, verbose: bool = True) -> str:
    """
    Ejecuta el Morning Sync para una fecha específica (default: hoy).

    Args:
        target_date: fecha a sincronizar, e.g. date(2026, 2, 25). Default: hoy.
        verbose: imprimir logs en consola.
    """
    target = target_date or date.today()

    lm = dspy.LM(
        model=f"anthropic/{config.CLAUDE_MODEL}",
        api_key=config.ANTHROPIC_API_KEY,
    )
    dspy.configure(lm=lm)

    if verbose:
        print("🌅 Iniciando Morning Sync...")
        print(f"   Modelo: {config.CLAUDE_MODEL}")
        print(f"   Fecha:  {target.strftime('%A %d %B %Y')}")
        print()

    agent = build_agent(target)
    result = agent(result="")

    if verbose:
        print()
        print("✅ Morning Sync completado:")
        print(f"   {result.result}")

    return result.result


if __name__ == "__main__":
    run_morning_sync(verbose=True)