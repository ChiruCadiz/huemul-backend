import httpx
from loguru import logger
from app.config import settings

async def fetch_available_models() -> list[str]:
    """
    Consulta Ollama /api/tags y retorna lista de modelos disponibles.
    Retorna lista vacía si Ollama no responde.
    """
    url = f"{settings.ollama_base_url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            if response.status_code != 200:
                logger.warning(f"Ollama retornó status {response.status_code} en /api/tags")
                return []
            data = response.json()
            model_names = [m["name"] for m in data.get("models", [])]
            logger.info(f"Modelos disponibles en Ollama: {model_names}")
            return sorted(model_names)
    except httpx.ConnectError:
        logger.error(f"No se pudo conectar a Ollama en {settings.ollama_base_url}")
        return []
    except Exception as e:
        logger.error(f"Error al obtener modelos de Ollama: {e}")
        return []