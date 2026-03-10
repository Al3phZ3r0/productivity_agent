"""
Slack Bot usando Socket Mode — escucha mensajes en tiempo real sin necesidad
de un servidor público con URL.

Requisitos en tu Slack App:
  1. Socket Mode habilitado → genera un App-Level Token (xapp-...)
  2. Event Subscriptions → suscribirse a: message.im (DMs) y/o message.channels
  3. Bot Token Scopes: chat:write, im:history, channels:history (según necesites)

Variables de entorno necesarias:
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_APP_TOKEN=xapp-...

Uso:
  python slack_bot.py
"""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import config


# ─── Inicializar Slack App ────────────────────────────────────────────────────

app = App(token=config.SLACK_BOT_TOKEN)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def is_eod_message(text: str) -> bool:
    """
    Detecta si el mensaje parece un reporte de actividad del día.
    Filtra mensajes cortos o que no sean reportes de trabajo.
    """
    text = text.lower().strip()

    # Ignorar mensajes muy cortos
    if len(text) < 10:
        return False

    # Keywords que indican un reporte de trabajo
    keywords = [
        "hice", "trabajé", "terminé", "completé", "estuve", "tuve",
        "reunión", "llamada", "revisé", "desarrollé", "arreglé", "implementé",
        "i did", "i worked", "i finished", "i completed", "i had", "meeting",
        "hoy", "today", "hora", "horas", "minutos", "hour", "hours", "minutes"
    ]
    return any(kw in text for kw in keywords)


def clean_message(text: str) -> str:
    """Limpia el texto del mensaje (remueve menciones al bot, etc.)"""
    # Remover menciones tipo <@U123ABC>
    text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
    return text


# ─── Event Handlers ───────────────────────────────────────────────────────────

@app.message()
def handle_message(message, say, client):
    """
    Maneja todos los mensajes donde el bot está presente.
    Solo procesa si parece un reporte de actividad.
    """
    text = message.get("text", "")
    user = message.get("user", "")
    channel = message.get("channel", "")
    subtype = message.get("subtype", "")

    # Ignorar mensajes del bot mismo y mensajes de sistema
    if subtype in ("bot_message", "message_changed", "message_deleted"):
        return
    if message.get("bot_id"):
        return

    text_clean = clean_message(text)

    if not is_eod_message(text_clean):
        return

    # Confirmar recepción inmediatamente
    say(
        text="📋 Procesando tu reporte... un momento.",
        channel=channel,
    )

    try:
        from flows.eod_flow import run_eod_agent
        result = run_eod_agent(text_clean, verbose=True)

        # Responder con el resultado
        say(
            text=f"✅ *Listo!*\n\n{result}",
            channel=channel,
        )

    except Exception as e:
        print(f"❌ Error en EOD agent: {e}")
        say(
            text=f"❌ Ocurrió un error procesando tu reporte: `{str(e)}`",
            channel=channel,
        )


@app.event("app_mention")
def handle_mention(event, say):
    """
    Maneja cuando alguien menciona al bot directamente (@bot).
    Siempre procesa el mensaje sin filtrar por keywords.
    """
    text = clean_message(event.get("text", ""))
    channel = event.get("channel", "")

    if not text:
        say("Cuéntame qué hiciste hoy y lo registro en ClickUp. 📋")
        return

    say(text="📋 Procesando tu reporte... un momento.", channel=channel)

    try:
        from flows.eod_flow import run_eod_agent
        result = run_eod_agent(text, verbose=True)
        say(text=f"✅ *Listo!*\n\n{result}", channel=channel)
    except Exception as e:
        say(text=f"❌ Error: `{str(e)}`", channel=channel)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not config.SLACK_APP_TOKEN:
        print("❌ Falta SLACK_APP_TOKEN en el .env")
        print("   Ve a tu Slack App → Settings → Socket Mode → Enable → genera el App-Level Token")
        sys.exit(1)

    print("🤖 Slack Bot iniciado en Socket Mode...")
    print("   Escuchando mensajes. Presiona Ctrl+C para detener.")

    handler = SocketModeHandler(app, config.SLACK_APP_TOKEN)
    handler.start()
