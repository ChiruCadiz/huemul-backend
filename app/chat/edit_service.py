import re
from loguru import logger


def extract_diff(text: str) -> str | None:
    """Extrae el bloque diff de la respuesta del modelo."""
    # Buscar bloque ```diff ... ```
    match = re.search(r"```diff\s*\n([\s\S]*?)```", text)
    if match:
        return match.group(1).strip()
    # Fallback: si empieza con --- directamente
    if text.strip().startswith("---"):
        return text.strip()
    return None


def extract_code(text: str) -> str | None:
    """Extrae el bloque de código completo de la respuesta del modelo."""
    # Buscar cualquier bloque de código ``` ... ```
    match = re.search(r"```(?:\w+)?\s*\n([\s\S]*?)```", text)
    if match:
        return match.group(1)
    return None