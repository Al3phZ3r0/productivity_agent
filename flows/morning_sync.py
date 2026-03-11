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
        desc="Resumen de lo que hiciste: cuantas tareas creaste, cuales ya existian, y si hubo errores."
    )


def build_agent(target_date: date, calendar_id: str) -> dspy.ReAct:
    """Construye el agente ReAct con calendar_id y fecha ya fijados."""
    date_str = target_date.strftime("%Y-%m-%d")

    def get_events_for_day() -> str:
        """
        Obtiene todos los eventos del calendario para el dia configurado.
        Retorna un JSON con la lista de reuniones (titulo, hora inicio, hora fin, asistentes).
        """
        return get_calendar_events_for_date(date_str, calendar_id=calendar_id)

    return dspy.ReAct(
        signature=MorningSyncSignature,
        tools=[
            get_events_for_day,
            create_clickup_task_for_meeting,
            get_existing_clickup_tasks,
        ],
        max_iters=15,
    )


def run_morning_sync(
    target_date: Optional[date] = None,
    calendar_id: Optional[str] = None,
    verbose: bool = True,
) -> str:
    """
    Ejecuta el Morning Sync.

    Args:
        target_date: fecha a sincronizar. Default: hoy.
        calendar_id: Google Calendar ID del usuario. Default: el del .env.
        verbose: imprimir logs en consola.
    """
    target = target_date or date.today()
    cal_id = calendar_id or config.GOOGLE_CALENDAR_ID

    lm = dspy.LM(
        model=f"anthropic/{config.CLAUDE_MODEL}",
        api_key=config.ANTHROPIC_API_KEY,
    )
    dspy.configure(lm=lm)

    if verbose:
        print("Morning Sync iniciado...")
        print(f"  Fecha:    {target.strftime('%A %d %B %Y')}")
        print(f"  Calendar: {cal_id}")
        print()

    agent = build_agent(target, cal_id)
    result = agent(result="")

    if verbose:
        print()
        print("Morning Sync completado:")
        print(f"  {result.result}")

    return result.result


if __name__ == "__main__":
    run_morning_sync(verbose=True)