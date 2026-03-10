#  Productivity Agent

Agente de productividad construido con **DSPy** que sincroniza Google Calendar, ClickUp, Slack y Cortex.

## Flujos

| Flujo | Cuándo | Qué hace |
|-------|--------|----------|
| **Morning Sync** | Inicio del día | Lee Google Calendar → crea tareas en ClickUp |
| **EOD Check-in** | Final del día | Pregunta a Cortex → desglosa en tareas / registra tiempo |
| **EOD Report** | Final del día | Resume el día → postea en Slack → guarda en Cortex |

---

## Setup

### 1. Clonar e instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales
```

### 3. Google Calendar — Obtener credentials.json

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto → Habilita **Google Calendar API**
3. Crea credenciales OAuth 2.0 (Desktop App)
4. Descarga `credentials.json` y ponlo en `./config/credentials.json`
5. La primera vez que corras el agente se abrirá un browser para autorizar

### 4. ClickUp — Obtener API Token y List ID

- **Token**: Settings → Apps → API Token
- **List ID**: Abre tu lista en ClickUp → la URL tiene el ID: `app.clickup.com/123/v/li/LIST_ID`

### 5. Slack — Crear Bot App

1. Ve a [api.slack.com/apps](https://api.slack.com/apps) → Create App
2. OAuth & Permissions → agrega scopes: `chat:write`, `channels:read`
3. Instala en tu workspace → copia el **Bot User OAuth Token** (`xoxb-...`)
4. Invita al bot al canal: `/invite @tu-bot`

### 6. Verificar conexiones

```bash
python check_connections.py
```

---

## Estructura

```
productivity-agent/
├── config/
│   ├── settings.py          # Configuración central
│   ├── credentials.json     # (no commitear) Google OAuth
│   └── token.json           # (no commitear) Google token cacheado
├── connectors/
│   ├── cortex.py            # Cortex API
│   ├── google_calendar.py   # Google Calendar
│   ├── clickup.py           # ClickUp
│   └── slack.py             # Slack
├── tools/                   # DSPy tools (Fase 2)
├── flows/                   # Flujos del agente (Fase 3)
├── utils/                   # Utilidades
├── check_connections.py     # Verificar integraciones
├── main.py                  # Entry point (Fase 4)
├── requirements.txt
└── .env.example
```

---

## Próximos pasos

- [ ] **Fase 2**: Construir DSPy Tools sobre los conectores
- [ ] **Fase 3**: Implementar los 3 flujos del agente
- [ ] **Fase 4**: Agregar scheduler (APScheduler)
