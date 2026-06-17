import uuid
import pytest
from unittest.mock import patch
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

async def mock_stream(*args, **kwargs):
    """Simula el streaming de tokens de Ollama."""
    for token in ["Python", " es", " un", " lenguaje."]:
        yield token


@pytest.mark.asyncio
async def test_chat_message_exitoso(client: AsyncClient, regular_user: User, session_cleanup):
    """POST /chat/message debe retornar respuesta en streaming."""
    session_id = str(uuid.uuid4())
    session_cleanup.append(session_id)
    payload = {
        "session_id": session_id,
        "message": "¿Qué es Python?",
        "model": "gemma4:26b",
        "mode": "analysis"
    }
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        response = await client.post(
            "/chat/message",
            json=payload,
            headers=get_headers(regular_user)
        )
    assert response.status_code == 200
    assert "Python" in response.text


@pytest.mark.asyncio
async def test_chat_guarda_historial_en_redis(client: AsyncClient, regular_user: User, session_cleanup):
    """POST /chat/message debe guardar el historial en Redis."""
    from app.memory.session import get_session_history
    session_id = str(uuid.uuid4())
    session_cleanup.append(session_id)
    payload = {
        "session_id": session_id,
        "message": "¿Qué es Python?",
        "model": "gemma4:26b",
        "mode": "analysis"
    }
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json=payload,
            headers=get_headers(regular_user)
        )
    history = await get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "¿Qué es Python?"
    assert history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_memoria_entre_mensajes(client: AsyncClient, regular_user: User, session_cleanup):
    """El segundo mensaje debe encontrar el historial del primero en Redis."""
    from app.memory.session import get_session_history
    session_id = str(uuid.uuid4())
    session_cleanup.append(session_id)
    base_payload = {
        "session_id": session_id,
        "model": "gemma4:26b",
        "mode": "analysis"
    }
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json={**base_payload, "message": "¿Qué es Python?"},
            headers=get_headers(regular_user)
        )
    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json={**base_payload, "message": "Dame un ejemplo."},
            headers=get_headers(regular_user)
        )
    history = await get_session_history(session_id)
    assert len(history) == 4  # 2 mensajes × 2 turnos


@pytest.mark.asyncio
async def test_chat_sin_token(client: AsyncClient):
    """POST /chat/message sin token debe retornar 401."""
    payload = {
        "session_id": str(uuid.uuid4()),
        "message": "¿Qué es Python?",
        "model": "gemma4:26b",
        "mode": "analysis"
    }
    response = await client.post("/chat/message", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_modo_analysis(client: AsyncClient, regular_user: User, session_cleanup):
    """El modo analysis debe incluirse en el prompt enviado a Ollama."""
    session_id = str(uuid.uuid4())
    session_cleanup.append(session_id)
    prompts_capturados = []

    async def capture_stream(model, prompt):
        prompts_capturados.append(prompt)
        yield "respuesta"

    payload = {
        "session_id": session_id,
        "message": "Analiza este código.",
        "model": "gemma4:26b",
        "mode": "analysis"
    }
    with patch("app.chat.router.stream_ollama", side_effect=capture_stream):
        await client.post(
            "/chat/message",
            json=payload,
            headers=get_headers(regular_user)
        )
    assert len(prompts_capturados) > 0
    assert "MODO ANÁLISIS" in prompts_capturados[0]


@pytest.mark.asyncio
async def test_chat_modo_edit(client: AsyncClient, regular_user: User, session_cleanup):
    """El modo edit debe incluirse en el prompt enviado a Ollama."""
    session_id = str(uuid.uuid4())
    session_cleanup.append(session_id)
    prompts_capturados = []

    async def capture_stream(model, prompt):
        prompts_capturados.append(prompt)
        yield "respuesta"

    payload = {
        "session_id": session_id,
        "message": "Edita este código.",
        "model": "gemma4:26b",
        "mode": "edit"
    }
    with patch("app.chat.router.stream_ollama", side_effect=capture_stream):
        await client.post(
            "/chat/message",
            json=payload,
            headers=get_headers(regular_user)
        )
    assert len(prompts_capturados) > 0
    assert "MODO EDICIÓN" in prompts_capturados[0]


@pytest.mark.asyncio
async def test_chat_sesiones_aisladas(client: AsyncClient, regular_user: User, session_cleanup):
    """Dos sesiones distintas deben tener historiales independientes."""
    from app.memory.session import get_session_history

    session_x = str(uuid.uuid4())
    session_y = str(uuid.uuid4())
    session_cleanup += [session_x, session_y]

    with patch("app.chat.router.stream_ollama", side_effect=mock_stream):
        await client.post(
            "/chat/message",
            json={"session_id": session_x, "message": "¿Qué es Python?", "model": "gemma4:26b", "mode": "analysis"},
            headers=get_headers(regular_user)
        )
        await client.post(
            "/chat/message",
            json={"session_id": session_y, "message": "¿Qué es Python?", "model": "gemma4:26b", "mode": "analysis"},
            headers=get_headers(regular_user)
        )

    history_x = await get_session_history(session_x)
    history_y = await get_session_history(session_y)
    assert len(history_x) == 2
    assert len(history_y) == 2