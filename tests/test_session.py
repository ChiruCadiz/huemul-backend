import pytest
import json
from app.memory.session import (
    get_session_history,
    append_to_history,
    clear_session,
)
from app.memory.redis_client import get_redis

SESSION_ID = "test-session-sprint2"

@pytest.mark.asyncio
async def test_historial_vacio_en_sesion_nueva():
    """Una sesión nueva debe retornar historial vacío."""
    history = await get_session_history(SESSION_ID)
    assert history == []

@pytest.mark.asyncio
async def test_append_mensaje_usuario():
    """Agregar un mensaje de usuario debe guardarse correctamente."""
    await append_to_history(SESSION_ID, "user", "Hola, ¿qué es Python?")
    history = await get_session_history(SESSION_ID)
    assert len(history) == 1
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hola, ¿qué es Python?"

@pytest.mark.asyncio
async def test_append_mensaje_asistente():
    """Agregar mensajes de ambos roles debe mantener el orden correcto."""
    await append_to_history(SESSION_ID, "user", "¿Qué es Python?")
    await append_to_history(SESSION_ID, "assistant", "Python es un lenguaje de programación.")
    history = await get_session_history(SESSION_ID)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

@pytest.mark.asyncio
async def test_historial_acumula_mensajes():
    """El historial debe acumular mensajes en orden cronológico."""
    await append_to_history(SESSION_ID, "user", "Mensaje 1")
    await append_to_history(SESSION_ID, "assistant", "Respuesta 1")
    await append_to_history(SESSION_ID, "user", "Mensaje 2")
    await append_to_history(SESSION_ID, "assistant", "Respuesta 2")
    history = await get_session_history(SESSION_ID)
    assert len(history) == 4
    assert history[2]["content"] == "Mensaje 2"
    assert history[3]["content"] == "Respuesta 2"

@pytest.mark.asyncio
async def test_clear_session_elimina_historial():
    """clear_session debe eliminar todos los mensajes de la sesión."""
    await append_to_history(SESSION_ID, "user", "Mensaje a eliminar")
    await clear_session(SESSION_ID)
    history = await get_session_history(SESSION_ID)
    assert history == []

@pytest.mark.asyncio
async def test_ttl_se_asigna_al_guardar():
    """El TTL debe asignarse al guardar un mensaje (mayor a 0)."""
    await append_to_history(SESSION_ID, "user", "Mensaje con TTL")
    redis = await get_redis()
    ttl = await redis.ttl(f"session:{SESSION_ID}")
    assert ttl > 0

@pytest.mark.asyncio
async def test_sesiones_distintas_no_se_mezclan():
    """Dos sesiones distintas deben tener historiales independientes."""
    session_a = "test-session-a"
    session_b = "test-session-b"
    await append_to_history(session_a, "user", "Mensaje sesión A")
    await append_to_history(session_b, "user", "Mensaje sesión B")
    history_a = await get_session_history(session_a)
    history_b = await get_session_history(session_b)
    assert history_a[0]["content"] == "Mensaje sesión A"
    assert history_b[0]["content"] == "Mensaje sesión B"
    assert len(history_a) == 1
    assert len(history_b) == 1
    # Limpieza
    await clear_session(session_a)
    await clear_session(session_b)