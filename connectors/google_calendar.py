"""
Conector para Google Calendar.
Requiere: credentials.json descargado desde Google Cloud Console.
Scopes necesarios: https://www.googleapis.com/auth/calendar.readonly
"""
import os
from datetime import datetime, timedelta
from typing import List, Dict
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.settings import config

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


class GoogleCalendarConnector:
    def __init__(self):
        self.timezone = ZoneInfo(config.TIMEZONE)
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None

        if os.path.exists(config.GOOGLE_TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(config.GOOGLE_TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(config.GOOGLE_TOKEN_PATH, "w") as token:
                token.write(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    def get_events_today(self) -> List[Dict]:
        """Devuelve todos los eventos de hoy."""
        now = datetime.now(self.timezone)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=0)

        return self._get_events(start_of_day, end_of_day)

    def get_events_for_date(self, date: datetime) -> List[Dict]:
        """Devuelve eventos de una fecha específica."""
        tz_date = date.replace(tzinfo=self.timezone) if date.tzinfo is None else date
        start = tz_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = tz_date.replace(hour=23, minute=59, second=59, microsecond=0)
        return self._get_events(start, end)

    def _get_events(self, start: datetime, end: datetime) -> List[Dict]:
        events_result = self.service.events().list(
            calendarId=config.GOOGLE_CALENDAR_ID,
            timeMin=start.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        return [self._parse_event(e) for e in events]

    def _parse_event(self, event: dict) -> Dict:
        start = event.get("start", {})
        end = event.get("end", {})

        start_time = start.get("dateTime", start.get("date", ""))
        end_time = end.get("dateTime", end.get("date", ""))

        return {
            "id": event.get("id"),
            "title": event.get("summary", "Sin título"),
            "description": event.get("description", ""),
            "start": start_time,
            "end": end_time,
            "attendees": [
                a.get("email") for a in event.get("attendees", [])
            ],
            "location": event.get("location", ""),
            "meet_link": event.get("hangoutLink", ""),
        }

    def test_connection(self) -> bool:
        try:
            self.service.calendarList().list().execute()
            print("✅ Google Calendar: conexión exitosa")
            return True
        except Exception as e:
            print(f"❌ Google Calendar: error → {e}")
            return False
