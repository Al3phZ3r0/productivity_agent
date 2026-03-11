"""
Entry point del agente de productividad.

Uso:
    python main.py morning                       → Morning Sync (hoy)
    python main.py morning --date 2026-02-25     → Morning Sync (fecha específica)
    python main.py eod "hoy tuve una reunión..." → Procesar reporte manual
    python main.py bot                           → Iniciar Slack bot en tiempo real
    python main.py check                         → Verificar todas las conexiones
"""
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def parse_date_arg() -> date:
    """Busca --date YYYY-MM-DD en los argumentos. Default: hoy."""
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        try:
            return datetime.strptime(sys.argv[idx + 1], "%Y-%m-%d").date()
        except (IndexError, ValueError):
            print("❌ Formato inválido. Usa: --date YYYY-MM-DD  (e.g. --date 2026-02-25)")
            sys.exit(1)
    return date.today()


def cmd_morning():
    from flows.morning_sync import run_morning_sync
    target = parse_date_arg()
    run_morning_sync(target_date=target, verbose=True)


def cmd_eod():
    """Procesa un reporte EOD directamente desde la línea de comandos."""
    # Toma todo lo que viene después de 'eod' como el mensaje
    args = sys.argv[2:]
    if not args:
        print("❌ Debes pasar el mensaje. Ejemplo:")
        print('   python main.py eod "Hoy tuve reunión con el equipo, 1 hora"')
        sys.exit(1)
    message = " ".join(args)
    from flows.eod_flow import run_eod_agent
    run_eod_agent(message, verbose=True)


def cmd_bot():
    import re
    from threading import Event
    from slack_sdk.web import WebClient
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.response import SocketModeResponse
    from slack_sdk.socket_mode.request import SocketModeRequest
    from config.settings import config
    from utils.user_resolver import UserResolver

    if not config.SLACK_APP_TOKEN:
        print("Falta SLACK_APP_TOKEN en el .env (xapp-...)")
        sys.exit(1)
    if not config.SLACK_BOT_TOKEN:
        print("Falta SLACK_BOT_TOKEN en el .env (xoxb-...)")
        sys.exit(1)

    web_client = WebClient(token=config.SLACK_BOT_TOKEN)
    resolver = UserResolver()

    def clean_message(text):
        return re.sub(r"<@[A-Z0-9]+>", "", text).strip()

    def reply(channel, text):
        web_client.chat_postMessage(channel=channel, text=text)

    def process(client, req):
        print(f"Request type: {req.type}")

        client.send_socket_mode_response(
            SocketModeResponse(envelope_id=req.envelope_id)
        )

        if req.type != "events_api":
            return

        event = req.payload.get("event", {})
        event_type = event.get("type", "")
        print(f"Evento: {event_type} | texto: {event.get('text', '')[:80]}")

        if event.get("bot_id") or event.get("subtype"):
            return

        channel = event.get("channel", "")
        text_raw = event.get("text", "")
        slack_user_id = event.get("user", "")

        if event_type == "app_mention" or (
            event_type == "message" and event.get("channel_type") == "im"
        ):
            text = clean_message(text_raw)

            if not text:
                reply(channel,
                    "Hola! Puedo ayudarte con:\n"
                    "- *morning* - sincronizar reuniones de hoy con ClickUp\n"
                    "- *morning YYYY-MM-DD* - sincronizar una fecha especifica\n"
                    "- Cualquier reporte de lo que hiciste hoy"
                )
                return

            # Resolver perfil del usuario desde Cortex
            print(f"Resolviendo perfil para Slack ID: {slack_user_id}")
            profile = resolver.get_profile(slack_user_id)

            if not profile:
                reply(channel,
                    "No pude identificar tu perfil. "
                    "Asegurate de que tu informacion este en Cortex."
                )
                return

            print(f"Usuario identificado: {profile}")
            text_lower = text.lower().strip()

            # Comando morning sync
            if text_lower.startswith("morning"):
                parts = text_lower.split()
                target = None
                if len(parts) > 1:
                    try:
                        target = datetime.strptime(parts[1], "%Y-%m-%d").date()
                    except ValueError:
                        reply(channel, "Formato invalido. Usa: morning YYYY-MM-DD")
                        return
                else:
                    target = date.today()

                reply(channel,
                    f"Hola {profile.name}! Iniciando Morning Sync "
                    f"para {target.strftime('%A %d %B %Y')}..."
                )
                try:
                    from flows.morning_sync import run_morning_sync
                    result = run_morning_sync(
                        target_date=target,
                        calendar_id=profile.calendar_id,
                        verbose=True,
                    )
                    reply(channel, f"Morning Sync completado!\n\n{result}")
                except Exception as e:
                    print(f"Error en Morning Sync: {e}")
                    reply(channel, f"Error en Morning Sync: {str(e)}")

            # EOD report
            else:
                reply(channel, f"Procesando tu reporte, {profile.name}... un momento.")
                try:
                    from flows.eod_flow import run_eod_agent
                    result = run_eod_agent(
                        user_message=text,
                        user_profile=profile,
                        verbose=True,
                    )
                    reply(channel, f"Listo!\n\n{result}")
                except Exception as e:
                    print(f"Error en agente EOD: {e}")
                    reply(channel, f"Error: {str(e)}")

    client = SocketModeClient(
        app_token=config.SLACK_APP_TOKEN,
        web_client=web_client,
    )
    client.socket_mode_request_listeners.append(process)
    client.connect()

    print("Slack Bot iniciado en Socket Mode (multi-usuario)...")
    print("Comandos disponibles desde Slack:")
    print("  morning              -> Morning Sync de hoy")
    print("  morning YYYY-MM-DD   -> Morning Sync de una fecha")
    print("  <cualquier texto>    -> EOD report")
    print("Presiona Ctrl+C para detener.\n")
    Event().wait()


def cmd_check():
    from check_connections import check_all
    check_all()


COMMANDS = {
    "morning": cmd_morning,
    "eod": cmd_eod,
    "bot": cmd_bot,
    "check": cmd_check,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None

    if cmd not in COMMANDS:
        print("Uso: python main.py <comando> [opciones]")
        print()
        print("Comandos:")
        print("  morning                      Sincroniza reuniones de hoy con ClickUp")
        print("  morning --date YYYY-MM-DD    Sincroniza una fecha específica")
        print('  eod "mensaje"                Procesa un reporte de actividad manualmente')
        print("  bot                          Inicia el Slack bot en tiempo real")
        print("  check                        Verifica todas las conexiones")
        sys.exit(1)

    COMMANDS[cmd]()
