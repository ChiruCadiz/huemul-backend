MAX_CONTEXT_CHARS = 12000  # ~3.000 tokens, ajustable

# Archivos prioritarios que se incluyen primero si están disponibles
PRIORITY_FILES = [
    "README.md", "readme.md",
    "package.json", "pyproject.toml", "requirements.txt",
    "Cargo.toml", "go.mod", "pom.xml",
]

def build_prompt(
    system_prompt: str,
    history: list[dict],
    message: str,
    files: list[dict] | None = None,
    mode: str = "analysis",
    max_context_chars: int = 12000,
) -> str:
    parts = []

    # ── System prompt ──────────────────────────────────────
    parts.append(f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}")

    # ── Modo de trabajo ────────────────────────────────────
    if mode == "analysis":
        parts.append(
            "[MODO ANÁLISIS]\n"
            "Analiza el código proporcionado con detalle. "
            "Explica su funcionamiento, detecta posibles problemas "
            "y sugiere mejoras. Responde siempre en español."
        )
    elif mode == "edit":
        parts.append(
            "[MODO EDICIÓN]\n"
            "Proporciona el código modificado directamente. "
            "Incluye solo el código corregido dentro de bloques ```. "
            "Explica brevemente los cambios realizados. Responde en español."
        )

    # ── Archivos de contexto (multi-archivo) ──────────────
    if files:
        ordered = _order_files(files)
        truncated = _truncate_files(ordered, max_context_chars)

        parts.append("[ARCHIVOS DE CONTEXTO]")
        for f in truncated:
            parts.append(
                f"── Archivo: {f['filename']} ──\n"
                f"```\n{f['content']}\n```"
            )

    # ── Historial de conversación ──────────────────────────
    if history:
        parts.append("[CONVERSACIÓN PREVIA]")
        for msg in history:
            role_label = "Usuario" if msg["role"] == "user" else "Asistente"
            parts.append(f"{role_label}: {msg['content']}")

    # ── Mensaje actual ─────────────────────────────────────
    parts.append(f"[MENSAJE ACTUAL]\nUsuario: {message}")
    parts.append("Asistente:")

    return "\n\n".join(parts)


def _order_files(files: list[dict]) -> list[dict]:
    """Ordena los archivos poniendo los prioritarios primero."""
    priority = []
    rest = []
    for f in files:
        name = f.get("filename", "").split("/")[-1]
        if name in PRIORITY_FILES:
            priority.append(f)
        else:
            rest.append(f)
    return priority + rest


def _truncate_files(files: list[dict], max_chars: int) -> list[dict]:
    """
    Aplica truncado inteligente respetando el límite total de caracteres.
    Prioriza el primer archivo (archivo activo) y trunca los demás si es necesario.
    """
    if not files:
        return []

    result = []
    used_chars = 0

    for i, f in enumerate(files):
        content = f.get("content", "")
        filename = f.get("filename", "")
        available = max_chars - used_chars

        if available <= 0:
            break

        if len(content) <= available:
            result.append(f)
            used_chars += len(content)
        elif i == 0:
            # El archivo activo siempre se incluye aunque sea truncado
            truncated_content = content[:available]
            result.append({
                "filename": f"{filename} (truncado)",
                "content": truncated_content,
            })
            used_chars += len(truncated_content)
        # Los archivos secundarios que no caben se descartan

    return result

def build_diff_prompt(
    system_prompt: str,
    filename: str,
    content: str,
    instruction: str,
) -> str:
    return "\n\n".join([
        f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}",
        "[MODO SUGERENCIA — DIFF UNIFICADO]\n"
        "Responde ÚNICAMENTE con un bloque diff en formato unificado (unified diff).\n"
        "No incluyas explicaciones fuera del bloque diff.\n"
        "Usa exactamente este formato:\n"
        "```diff\n"
        "--- a/nombre_archivo\n"
        "+++ b/nombre_archivo\n"
        "@@ -línea,cantidad +línea,cantidad @@\n"
        "-línea eliminada\n"
        "+línea agregada\n"
        "```",
        f"[ARCHIVO A MODIFICAR]\n── {filename} ──\n```\n{content}\n```",
        f"[INSTRUCCIÓN DEL USUARIO]\n{instruction}",
        "Asistente:",
    ])


def build_edit_prompt(
    system_prompt: str,
    filename: str,
    content: str,
    instruction: str,
) -> str:
    return "\n\n".join([
        f"[INSTRUCCIONES DEL SISTEMA]\n{system_prompt}",
        "[MODO EDICIÓN DIRECTA]\n"
        "Responde ÚNICAMENTE con el archivo completo modificado dentro de un bloque de código.\n"
        "No incluyas explicaciones antes ni después del bloque.\n"
        "Usa exactamente este formato:\n"
        "```\n"
        "contenido completo del archivo modificado\n"
        "```",
        f"[ARCHIVO A MODIFICAR]\n── {filename} ──\n```\n{content}\n```",
        f"[INSTRUCCIÓN DEL USUARIO]\n{instruction}",
        "Asistente:",
    ])