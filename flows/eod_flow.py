"""
Flujo EOD: El usuario le dice al agente en Slack que hizo en el dia.
El agente decide si crear una tarea nueva o agregar tiempo a una existente.
Soporta multiples usuarios via UserProfile.
"""
import dspy
from typing import Optional
from config.settings import config
from tools.eod_tools import (
    get_existing_tasks,
    create_task,
    add_time_to_task,
    get_cortex_context,
)


class EODSignature(dspy.Signature):
    """
    Eres un asistente de productividad. El usuario te va a decir que hizo hoy
    en su trabajo. Tu tarea es registrar ese trabajo en ClickUp correctamente.

    Proceso:
    1. Revisa las tareas existentes en ClickUp para ver si el trabajo reportado
       corresponde a alguna tarea abierta.
    2. Si corresponde a una tarea existente -> agrega el tiempo trabajado a esa tarea.
    3. Si es trabajo nuevo que no corresponde a ninguna tarea -> crea una tarea nueva.
    4. Si el usuario menciona multiples actividades -> procesa cada una por separado.
    5. Si el usuario menciona tiempo (e.g. "2 horas", "30 minutos") usalo.
       Si no menciona tiempo, no registres tiempo (pon 0).
    6. Puedes consultar Cortex si necesitas mas contexto sobre el trabajo del usuario.
    7. Al final responde con un resumen claro de lo que hiciste en ClickUp.

    Se conciso en tu respuesta final — el usuario la vera en Slack.
    """
    user_name: str = dspy.InputField(desc="Nombre del usuario que reporta")
    user_message: str = dspy.InputField(desc="Lo que el usuario reporta que hizo hoy")
    result: str = dspy.OutputField(desc="Resumen de lo que registraste en ClickUp")


def build_eod_agent() -> dspy.ReAct:
    return dspy.ReAct(
        signature=EODSignature,
        tools=[
            get_existing_tasks,
            create_task,
            add_time_to_task,
            get_cortex_context,
        ],
        max_iters=20,
    )


def run_eod_agent(
    user_message: str,
    user_profile=None,
    verbose: bool = True,
) -> str:
    """
    Procesa el mensaje del usuario y actua en ClickUp.

    Args:
        user_message: lo que el usuario reporto que hizo
        user_profile: UserProfile con nombre, email, etc. (opcional)
        verbose: imprimir logs en consola
    """
    lm = dspy.LM(
        model=f"anthropic/{config.CLAUDE_MODEL}",
        api_key=config.ANTHROPIC_API_KEY,
    )
    dspy.configure(lm=lm)

    user_name = user_profile.name if user_profile else "Usuario"

    if verbose:
        print(f"\nEOD Agent procesando para {user_name}: '{user_message[:80]}'")

    agent = build_eod_agent()
    result = agent(user_name=user_name, user_message=user_message)

    if verbose:
        print(f"Resultado: {result.result}")

    return result.result
