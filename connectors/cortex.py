"""
Conector para Cortex usando el SDK oficial cortex-client.
Repositorio: https://github.com/Grupo-Abraxas/cortex-client

Instalación:
    pip install git+https://github.com/Grupo-Abraxas/cortex-client.git
    (o según como lo distribuyan internamente)

Variables de entorno requeridas (.env):
    CORTEX_API_KEY=your-api-key-here
    CORTEX_API_URL=https://cortex-stage.arkondata.net   # opcional
    CORTEX_CONTEXT_GROUP_ID=your-group-id               # para guardar contexto diario
"""
import os
import tempfile
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from cortex import Cortex, ContextChunk
from config.settings import config


class CortexConnector:
    def __init__(self):
        # El SDK lee CORTEX_API_KEY y CORTEX_API_URL automáticamente del entorno
        # También se puede pasar explícitamente: Cortex(kg_api_key=config.CORTEX_API_KEY)
        self.client = Cortex()
        self.context_group_id = os.getenv("CORTEX_CONTEXT_GROUP_ID", "")
        self.timezone = ZoneInfo(config.TIMEZONE)

    def query_context(self, question: str, limit: int = 10) -> str:
        """
        Busca contexto relevante para una pregunta.
        Retorna el resultado como markdown (ideal para pasarle al agente DSPy).
        """
        markdown = self.client.context(query=question, limit=limit)
        return markdown

    def query_chunks(self, question: str, limit: int = 10) -> list[ContextChunk]:
        """
        Busca chunks de contexto. Útil cuando necesitas procesar los resultados
        de forma estructurada (títulos, tags, relevancia, etc).
        """
        return self.client.context_chunks(query=question, limit=limit)

    def add_daily_activity(self, content: str, date: Optional[datetime] = None) -> str:
        """
        Guarda el resumen de actividad del día en Cortex como un archivo de texto
        dentro de un context group.

        Estrategia: crea un archivo .txt temporal y lo sube al context group configurado.
        Si no hay CORTEX_CONTEXT_GROUP_ID, crea un nuevo grupo para hoy.
        """
        if date is None:
            date = datetime.now(self.timezone)

        date_str = date.strftime("%Y-%m-%d")

        # Escribe el contenido a un archivo temporal
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            prefix=f"daily_activity_{date_str}_",
            delete=False,
            encoding="utf-8"
        ) as tmp:
            tmp.write(f"# Actividad del día: {date_str}\n\n")
            tmp.write(content)
            tmp_path = tmp.name

        try:
            if self.context_group_id:
                # Agrega el archivo al context group existente
                self.client.update_context_group(
                    context_group_id=self.context_group_id,
                    files=[tmp_path],
                    description=f"Actividad diaria actualizada {date_str}",
                )
                print(f"✅ Cortex: contexto del día agregado al grupo {self.context_group_id}")
                return self.context_group_id
            else:
                # Crea un nuevo context group para hoy
                group = self.client.create_context_group(
                    files=[tmp_path],
                    description=f"Actividad diaria {date_str}",
                )
                print(f"✅ Cortex: nuevo context group creado → {group.id}")
                print(f"   💡 Guarda este ID en CORTEX_CONTEXT_GROUP_ID para reutilizarlo:")
                print(f"   CORTEX_CONTEXT_GROUP_ID={group.id}")
                return group.id
        finally:
            os.unlink(tmp_path)

    def get_libraries(self) -> list:
        """Lista todas las librerías accesibles (útil para debug/configuración)."""
        return self.client.get_libraries()

    def test_connection(self) -> bool:
        """Verifica que la conexión y autenticación funcionen."""
        try:
            libraries = self.client.get_libraries()
            lib_names = [lib.name for lib in libraries]
            print(f"✅ Cortex: conexión exitosa — {len(libraries)} librerías accesibles")
            if lib_names:
                print(f"   Librerías: {', '.join(lib_names)}")
            return True
        except Exception as e:
            print(f"❌ Cortex: error de conexión → {e}")
            return False
