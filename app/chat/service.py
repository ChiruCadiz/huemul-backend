import httpx
import json
from loguru import logger
from app.config import settings

async def stream_ollama(model: str, prompt: str):
    """
    Llama a Ollama con stream=True y hace yield de cada token recibido.
    """
    url = f"{settings.ollama_base_url}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": True}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    logger.error(f"Ollama retornó status {response.status_code}")
                    yield "[ERROR] El modelo no pudo generar una respuesta."
                    return
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    except httpx.ConnectError:
        logger.error(f"No se pudo conectar a Ollama en {settings.ollama_base_url}")
        yield "[ERROR] No se pudo conectar al modelo de IA. Contacte al administrador."
    except Exception as e:
        logger.error(f"Error durante streaming de Ollama: {e}")
        yield "[ERROR] Ocurrió un error durante la generación de respuesta."