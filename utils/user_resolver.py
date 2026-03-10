"""
Resuelve el perfil de un usuario a partir de su Slack user_id.

Flujo:
1. Obtiene el email del usuario via Slack API (users.info)
2. Consulta Cortex con ese email para obtener su perfil completo
3. Retorna el perfil: nombre, email, calendar_id, equipo, etc.

Scope requerido en Slack App: users:read, users:read.email
"""
import json
from typing import Optional
from slack_sdk.web import WebClient
from connectors.cortex import CortexConnector
from config.settings import config


class UserProfile:
    def __init__(self, slack_id: str, email: str, name: str,
                 calendar_id: str = "", team: str = ""):
        self.slack_id = slack_id
        self.email = email
        self.name = name
        self.calendar_id = calendar_id or email  # Google Calendar acepta email como ID
        self.team = team

    def __repr__(self):
        return f"UserProfile(name={self.name}, email={self.email}, calendar={self.calendar_id})"


class UserResolver:
    def __init__(self):
        self._web_client = WebClient(token=config.SLACK_BOT_TOKEN)
        self._cortex = CortexConnector()
        self._cache: dict = {}  # cache en memoria por sesión

    def get_profile(self, slack_user_id: str) -> Optional[UserProfile]:
        """
        Obtiene el perfil completo de un usuario dado su Slack user_id.
        Usa cache en memoria para evitar consultas repetidas en la misma sesión.
        """
        if slack_user_id in self._cache:
            print(f"Usuario {slack_user_id} obtenido del cache")
            return self._cache[slack_user_id]

        # 1. Obtener email desde Slack
        email = self._get_email_from_slack(slack_user_id)
        if not email:
            print(f"No se pudo obtener email para Slack ID: {slack_user_id}")
            return None

        # 2. Obtener perfil completo desde Cortex
        profile = self._get_profile_from_cortex(slack_user_id, email)

        # 3. Guardar en cache
        if profile:
            self._cache[slack_user_id] = profile
            print(f"Perfil resuelto: {profile}")

        return profile

    def _get_email_from_slack(self, slack_user_id: str) -> Optional[str]:
        """Obtiene el email de un usuario via Slack API."""
        try:
            response = self._web_client.users_info(user=slack_user_id)
            user = response.get("user", {})
            profile = user.get("profile", {})
            email = profile.get("email", "")
            if email:
                print(f"Email obtenido de Slack: {email}")
            return email or None
        except Exception as e:
            print(f"Error obteniendo email de Slack: {e}")
            return None

    def _get_profile_from_cortex(self, slack_id: str, email: str) -> Optional[UserProfile]:
        """
        Consulta Cortex para obtener el perfil completo del usuario.
        Fallback: usa email como calendar_id si Cortex no tiene el dato.
        """
        try:
            query = (
                f"perfil del usuario con email {email}. "
                f"Necesito su nombre completo, Google Calendar ID y equipo."
            )
            context = self._cortex.query_context(query, limit=5)

            if not context or context.strip() == "":
                print(f"Cortex no retorno contexto para {email}, usando fallback")
                return UserProfile(
                    slack_id=slack_id,
                    email=email,
                    name=email.split("@")[0],
                    calendar_id=email,
                )

            # Extraer datos estructurados del contexto con LLM
            profile_data = self._extract_profile_with_llm(email, context)

            return UserProfile(
                slack_id=slack_id,
                email=email,
                name=profile_data.get("name", email.split("@")[0]),
                calendar_id=profile_data.get("calendar_id", email),
                team=profile_data.get("team", ""),
            )

        except Exception as e:
            print(f"Error obteniendo perfil de Cortex: {e}")
            return UserProfile(
                slack_id=slack_id,
                email=email,
                name=email.split("@")[0],
                calendar_id=email,
            )

    def _extract_profile_with_llm(self, email: str, cortex_context: str) -> dict:
        """
        Usa el LLM para extraer datos estructurados del contexto de Cortex.
        Retorna dict con: name, calendar_id, team.
        """
        import dspy

        class ExtractProfile(dspy.Signature):
            """
            Dado el contexto de Cortex sobre un usuario, extrae su informacion en JSON.
            Responde SOLO con un JSON valido, sin texto adicional ni backticks.
            Campos requeridos:
            - name: nombre completo del usuario
            - calendar_id: su Google Calendar ID (generalmente su email corporativo)
            - team: equipo o area al que pertenece
            Si un campo no esta disponible en el contexto, usa string vacio.
            """
            email: str = dspy.InputField(desc="Email del usuario a buscar")
            context: str = dspy.InputField(desc="Contexto retornado por Cortex")
            profile_json: str = dspy.OutputField(desc="JSON con name, calendar_id, team")

        try:
            lm = dspy.LM(
                model=f"anthropic/{config.CLAUDE_MODEL}",
                api_key=config.ANTHROPIC_API_KEY,
            )
            dspy.configure(lm=lm)

            predictor = dspy.Predict(ExtractProfile)
            result = predictor(email=email, context=cortex_context)

            raw = result.profile_json.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)

        except Exception as e:
            print(f"Error extrayendo perfil con LLM: {e}")
            return {"name": email.split("@")[0], "calendar_id": email, "team": ""}
