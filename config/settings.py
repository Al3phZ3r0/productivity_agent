from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    # LLM - Gemini
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

    # Cortex (el SDK lee estas variables automáticamente del entorno)
    CORTEX_API_KEY: str = os.getenv("CORTEX_API_KEY", "")
    #CORTEX_API_URL: str = os.getenv("CORTEX_API_URL", "https://cortex-stage.arkondata.net")
    CORTEX_CONTEXT_GROUP_ID: str = os.getenv("CORTEX_CONTEXT_GROUP_ID", "")

    # Google Calendar
    GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "./config/credentials.json")
    GOOGLE_TOKEN_PATH: str = os.getenv("GOOGLE_TOKEN_PATH", "./config/token.json")
    GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    # ClickUp
    CLICKUP_API_TOKEN: str = os.getenv("CLICKUP_API_TOKEN", "")
    CLICKUP_LIST_ID: str = os.getenv("CLICKUP_LIST_ID", "")
    CLICKUP_TASKS_LIST_ID: str = os.getenv("CLICKUP_TASKS_LIST_ID", "")

    # Slack
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID: str = os.getenv("SLACK_CHANNEL_ID", "")
    SLACK_APP_TOKEN: str = os.getenv("SLACK_APP_TOKEN", "")

    # General
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Mexico_City")
    MORNING_SYNC_HOUR: int = int(os.getenv("MORNING_SYNC_HOUR", "8"))
    EOD_HOUR: int = int(os.getenv("EOD_HOUR", "18"))

config = Config()
