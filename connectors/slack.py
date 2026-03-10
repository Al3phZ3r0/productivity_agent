"""
Conector para Slack SDK.
Requiere: Bot Token con scopes chat:write, channels:read
"""
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Optional
from config.settings import config


class SlackConnector:
    def __init__(self):
        self.client = WebClient(token=config.SLACK_BOT_TOKEN)
        self.default_channel = config.SLACK_CHANNEL_ID

    def post_message(self, text: str, channel: Optional[str] = None) -> dict:
        """Postea un mensaje en el canal configurado."""
        target = channel or self.default_channel
        try:
            response = self.client.chat_postMessage(
                channel=target,
                text=text,
                # Permite Markdown básico de Slack (mrkdwn)
                mrkdwn=True,
            )
            print(f"✅ Slack: mensaje enviado a {target}")
            return response.data
        except SlackApiError as e:
            print(f"❌ Slack error: {e.response['error']}")
            raise

    def post_blocks(self, blocks: list, text: str = "", channel: Optional[str] = None) -> dict:
        """Postea con Block Kit para mensajes más ricos."""
        target = channel or self.default_channel
        response = self.client.chat_postMessage(
            channel=target,
            text=text,
            blocks=blocks,
        )
        return response.data

    def post_daily_summary(self, summary: str, date_str: str = "") -> dict:
        """
        Postea el resumen diario con formato agradable.
        summary: texto en markdown de Slack (*bold*, - listas, etc.)
        """
        header = f"📋 *Resumen del día{' — ' + date_str if date_str else ''}*\n\n"
        return self.post_message(header + summary)

    def test_connection(self) -> bool:
        try:
            self.client.auth_test()
            print("✅ Slack: conexión exitosa")
            return True
        except SlackApiError as e:
            print(f"❌ Slack: error → {e.response['error']}")
            return False
