import pytest
from app.chat.prompt_builder import build_prompt

SYSTEM_PROMPT = "Eres Huemul, asistente universitario."

def test_prompt_incluye_system_prompt():
    """El prompt debe incluir el system prompt institucional."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="¿Qué es Python?",
    )
    assert SYSTEM_PROMPT in prompt

def test_prompt_modo_analisis():
    """En modo análisis el prompt debe incluir la instrucción correspondiente."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Analiza este código.",
        mode="analysis"
    )
    assert "MODO ANÁLISIS" in prompt
    assert "MODO EDICIÓN" not in prompt

def test_prompt_modo_edicion():
    """En modo edición el prompt debe incluir la instrucción correspondiente."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Edita este código.",
        mode="edit"
    )
    assert "MODO EDICIÓN" in prompt
    assert "MODO ANÁLISIS" not in prompt

def test_prompt_incluye_mensaje_actual():
    """El prompt debe incluir el mensaje actual del usuario."""
    mensaje = "¿Cómo funciona una lista en Python?"
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message=mensaje,
    )
    assert mensaje in prompt

def test_prompt_incluye_historial():
    """El prompt debe incluir el historial de conversación previo."""
    history = [
        {"role": "user", "content": "Hola"},
        {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"},
    ]
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=history,
        message="Cuéntame más.",
    )
    assert "Hola" in prompt
    assert "¡Hola! ¿En qué puedo ayudarte?" in prompt

def test_prompt_sin_historial_no_incluye_seccion():
    """Sin historial no debe aparecer la sección de conversación previa."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Primera pregunta.",
    )
    assert "CONVERSACIÓN PREVIA" not in prompt

def test_prompt_incluye_archivos():
    """El prompt debe incluir los archivos de contexto cuando se proveen."""
    files = [{"filename": "main.py", "content": "print('hola')"}]
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Analiza este archivo.",
        files=files,
    )
    assert "main.py" in prompt
    assert "print('hola')" in prompt

def test_prompt_sin_archivos_no_incluye_seccion():
    """Sin archivos no debe aparecer la sección de archivos de contexto."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Pregunta sin archivos.",
        files=None,
    )
    assert "ARCHIVOS DE CONTEXTO" not in prompt

def test_prompt_termina_con_asistente():
    """El prompt debe terminar con 'Asistente:' para guiar al modelo."""
    prompt = build_prompt(
        system_prompt=SYSTEM_PROMPT,
        history=[],
        message="Cualquier mensaje.",
    )
    assert prompt.strip().endswith("Asistente:")