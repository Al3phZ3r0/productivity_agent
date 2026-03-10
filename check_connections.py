"""
Corre este script primero para verificar que todas las integraciones funcionan.
Uso: python check_connections.py
"""
import sys
import os

# Asegura que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_all():
    print("=" * 50)
    print("🔍 Verificando conexiones...")
    print("=" * 50)

    results = {}

    # --- Cortex ---
    print("\n[1/4] Cortex")
    try:
        from connectors.cortex import CortexConnector
        results["cortex"] = CortexConnector().test_connection()
    except Exception as e:
        print(f"❌ Cortex: excepción → {e}")
        results["cortex"] = False

    # --- Google Calendar ---
    print("\n[2/4] Google Calendar")
    try:
        from connectors.google_calendar import GoogleCalendarConnector
        results["google"] = GoogleCalendarConnector().test_connection()
    except Exception as e:
        print(f"❌ Google Calendar: excepción → {e}")
        results["google"] = False

    # --- ClickUp ---
    print("\n[3/4] ClickUp")
    try:
        from connectors.clickup import ClickUpConnector
        results["clickup"] = ClickUpConnector().test_connection()
    except Exception as e:
        print(f"❌ ClickUp: excepción → {e}")
        results["clickup"] = False

    # --- Slack ---
#    print("\n[4/4] Slack")
#    try:
#       from connectors.slack import SlackConnector
#       results["slack"] = SlackConnector().test_connection()
#   except Exception as e:
#        print(f"❌ Slack: excepción → {e}")
#       results["slack"] = False

    # --- Resumen ---
    print("\n" + "=" * 50)
    print("📊 Resultado:")
    all_ok = True
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name.capitalize()}")
        if not ok:
            all_ok = False

    print("=" * 50)
    if all_ok:
        print("\n🎉 Todo listo. Puedes continuar con el agente.")
    else:
        print("\n⚠️  Hay conexiones fallidas. Revisa tu .env antes de continuar.")

    return all_ok


if __name__ == "__main__":
    check_all()
