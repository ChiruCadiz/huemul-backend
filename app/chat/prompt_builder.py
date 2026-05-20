def build_prompt(
    system_prompt: str,
    history: list[dict],
    message: str,
    files: list[dict] = None,
    mode: str = "analysis"
) -> str:
    """
    Construye el prompt completo para enviar a Ollama.
    Incluye: system prompt, instrucción de modo, archivos, historial y mensaje actual.
    """
    parts = []

    # System prompt institucional
    parts.append(f"[SISTEMA]\n{system_prompt}")

    # Instrucción según modo
    if mode == "edit":
        parts.append(
            "[MODO EDICIÓN]\n"
            "Estás en modo edición. Responde únicamente con el código modificado. "
            "No incluyas explicaciones largas. Usa formato de archivo completo."
        )
    else:
        parts.append(
            "[MODO ANÁLISIS]\n"
            "Estás en modo análisis. Responde con explicaciones claras y detalladas. "
            "No modifiques archivos directamente."
        )

    # Contexto de archivos si los hay
    if files:
        parts.append("[ARCHIVOS DE CONTEXTO]")
        for f in files:
            parts.append(f"--- {f['filename']} ---\n{f['content']}")

    # Historial de conversación previa
    if history:
        parts.append("[CONVERSACIÓN PREVIA]")
        for msg in history:
            role = "Usuario" if msg["role"] == "user" else "Asistente"
            parts.append(f"{role}: {msg['content']}")

    # Mensaje actual del usuario
    parts.append(f"[MENSAJE ACTUAL]\nUsuario: {message}")
    parts.append("Asistente:")

    return "\n\n".join(parts)