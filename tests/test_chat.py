import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from app.db.models import User
from app.auth.jwt import create_access_token

def get_headers(user: User) -> dict:
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "email": user.email
    })
    return {"Authorization": f"Bearer {token}"}

CHAT_PAYLOAD = {
    "session_id": "test-chat-001",
    "message": "¿Qué es Python?",
    "model": "codellama",
    "mode": "analysis"
}

async def mock_stream(*args, **kwargs):
    """Simula el streaming de tokens de Ollama."""
    for token in ["Python", " es", " un", " lenguaje."]:
        yield token

@pytest.mark.asyncio
async def test_chat_message_exitoso(client: AsyncClient, regular_user: User):
    """POST /chat/message debe retornar respuesta en streaming."""
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        response = await client.post(
            "/chat/message",
            json=CHAT_PAYLOAD,
            headers=get_headers(regular_user)
        )
    assert response.status_code == 200
    assert "Python" in response.text

@pytest.mark.asyncio
async def test_chat_guarda_historial_en_redis(client: AsyncClient, regular_user: User):
    """POST /chat/message debe guardar el historial en Redis."""
    from app.memory.session import get_session_history
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json=CHAT_PAYLOAD,
            headers=get_headers(regular_user)
        )
    history = await get_session_history("test-chat-001")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "¿Qué es Python?"
    assert history[1]["role"] == "assistant"

@pytest.mark.asyncio
async def test_chat_memoria_entre_mensajes(client: AsyncClient, regular_user: User):
    """El segundo mensaje debe encontrar el historial del primero en Redis."""
    from app.memory.session import get_session_history
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json=CHAT_PAYLOAD,
            headers=get_headers(regular_user)
        )
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json={**CHAT_PAYLOAD, "message": "Dame un ejemplo."},
            headers=get_headers(regular_user)
        )
    history = await get_session_history("test-chat-001")
    assert len(history) == 4  # 2 mensajes × 2 turnos

@pytest.mark.asyncio
async def test_chat_sin_token(client: AsyncClient):
    """POST /chat/message sin token debe retornar 401."""
    response = await client.post("/chat/message", json=CHAT_PAYLOAD)
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_chat_modo_analysis(client: AsyncClient, regular_user: User):
    """El modo analysis debe incluirse en el prompt enviado a Ollama."""
    prompts_capturados = []

    async def capture_stream(model, prompt):
        prompts_capturados.append(prompt)
        yield "respuesta"

    with patch("app.chat.router.stream_ollama", side_effect=capture_stream):
        await client.post(
            "/chat/message",
            json={**CHAT_PAYLOAD, "mode": "analysis"},
            headers=get_headers(regular_user)
        )
    assert len(prompts_capturados) > 0
    assert "MODO ANÁLISIS" in prompts_capturados[0]

@pytest.mark.asyncio
async def test_chat_modo_edit(client: AsyncClient, regular_user: User):
    """El modo edit debe incluirse en el prompt enviado a Ollama."""
    prompts_capturados = []

    async def capture_stream(model, prompt):
        prompts_capturados.append(prompt)
        yield "respuesta"

    with patch("app.chat.router.stream_ollama", side_effect=capture_stream):
        await client.post(
            "/chat/message",
            json={**CHAT_PAYLOAD, "mode": "edit"},
            headers=get_headers(regular_user)
        )
    assert "MODO EDICIÓN" in prompts_capturados[0]

@pytest.mark.asyncio
async def test_chat_sesiones_aisladas(client: AsyncClient, regular_user: User):
    """Dos sesiones distintas deben tener historiales independientes."""
    from app.memory.session import get_session_history

    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json={**CHAT_PAYLOAD, "session_id": "test-sesion-x"},
            headers=get_headers(regular_user)
        )
        await client.post(
            "/chat/message",
            json={**CHAT_PAYLOAD, "session_id": "test-sesion-y"},
            headers=get_headers(regular_user)
        )

    history_x = await get_session_history("test-sesion-x")
    history_y = await get_session_history("test-sesion-y")
    assert len(history_x) == 2
    assert len(history_y) == 2