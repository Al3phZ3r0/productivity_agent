"""
Flujo EOD: El usuario le dice al agente en Slack qué hizo en el día.
El agente decide si crear una tarea nueva o agregar tiempo a una existente.

Este módulo contiene:
  - run_eod_agent(message): procesa un mensaje y actúa en ClickUp
  - El Slack bot que escucha mensajes y llama al agente
"""
import dspy
from config.settings import config
from tools.eod_tools import (
    get_existing_tasks,
    create_task,
    add_time_to_task,
    get_cortex_context,
)


# ─── DSPy Signature ───────────────────────────────────────────────────────────

class EODSignature(dspy.Signature):
    """
    Eres un asistente de productividad. El usuario te va a decir qué hizo hoy
    en su trabajo. Tu tarea es registrar ese trabajo en ClickUp correctamente.

    Proceso:
    1. Revisa las tareas existentes en ClickUp para ver si el trabajo reportado
       corresponde a alguna tarea abierta.
    2. Si corresponde a una tarea existente → agrega el tiempo trabajado a esa tarea.
    3. Si es trabajo nuevo que no corresponde a ninguna tarea → crea una tarea nueva.
    4. Si el usuario menciona múltiples actividades → procesa cada una por separado.
    5. Si el usuario menciona tiempo (e.g. "2 horas", "30 minutos") úsalo.
       Si no menciona tiempo, no registres tiempo (pon 0).
    6. Puedes consultar Cortex si necesitas más contexto sobre el trabajo del usuario.
    7. Al final responde con un resumen claro de lo que hiciste en ClickUp.

    Sé conciso en tu respuesta final — el usuario la verá en Slack.
    """
    user_message: str = dspy.InputField(desc="Lo que el usuario reporta que hizo hoy")
    result: str = dspy.OutputField(desc="Resumen de lo que registraste en ClickUp (para mostrar en Slack)")


# ─── Agent builder ────────────────────────────────────────────────────────────

def build_eod_agent() -> dspy.ReAct:
    return dspy.ReAct(
        signature=EODSignature,
        tools=[
            get_existing_tasks,
            create_task,
            add_time_to_task,
            #get_cortex_context,
        ],
        max_iters=20,
    )


# ─── Main runner ──────────────────────────────────────────────────────────────

def run_eod_agent(user_message: str, verbose: bool = True) -> str:
    """
    Procesa el mensaje del usuario y actúa en ClickUp.
    Retorna el resumen para mostrar de vuelta en Slack.
    """
    lm = dspy.LM(
        model=f"anthropic/{config.CLAUDE_MODEL}",
        api_key=config.ANTHROPIC_API_KEY,
    )
    dspy.configure(lm=lm)

    if verbose:
        print(f"\n🤖 EOD Agent procesando: '{user_message}'")

    agent = build_eod_agent()
    result = agent(user_message=user_message)

    if verbose:
        print(f"✅ Resultado: {result.result}")

    return result.result
