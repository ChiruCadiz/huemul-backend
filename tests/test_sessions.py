import uuid
import pytest
from httpx import AsyncClient
from app.db.models import User
from app.auth.jwt import create_access_token
from app.sessions.service import (
    create_session,
    list_sessions,
    get_session_detail,
    delete_session,
    persist_messages,
    load_history,
    generate_session_title,
)
from app.memory.session import append_to_history, get_session_history

def get_headers(user: User) -> dict:
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "email": user.email
    })
    return {"Authorization": f"Bearer {token}"}

MODEL = "gemma4:26b"

# ══════════════════════════════════════════════════════════════
# Tests unitarios de app/sessions/service.py
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_create_session(db_session, regular_user: User, session_cleanup):
    """create_session debe crear una sesión con título por defecto."""
    session = await create_session(regular_user.id, MODEL, db_session)
    session_cleanup.append(str(session.id))

    assert session.user_id == regular_user.id
    assert session.model_used == MODEL
    assert session.title == "Nueva sesión"
    assert session.is_active is True

@pytest.mark.asyncio
async def test_list_sessions_empty(db_session, regular_user: User):
    """Un usuario sin sesiones debe recibir lista vacía."""
    sessions = await list_sessions(regular_user.id, db_session)
    assert sessions == []

@pytest.mark.asyncio
async def test_list_sessions_ordenadas_por_actividad(db_session, regular_user: User, session_cleanup):
    """Las sesiones deben listarse ordenadas por última actividad descendente."""
    from datetime import datetime, timedelta, UTC
    from sqlalchemy import update
    from app.db.models import Session as SessionModel

    s1 = await create_session(regular_user.id, MODEL, db_session)
    s2 = await create_session(regular_user.id, MODEL, db_session)
    session_cleanup += [str(s1.id), str(s2.id)]

    now = datetime.now(UTC).replace(tzinfo=None)  # ← cambio aquí
    await db_session.execute(
        update(SessionModel).where(SessionModel.id == s1.id)
        .values(last_active_at=now - timedelta(seconds=1))
    )

    await db_session.execute(
        update(SessionModel).where(SessionModel.id == s2.id)
        .values(last_active_at=now)
    )
    await db_session.commit()

    sessions = await list_sessions(regular_user.id, db_session)
    assert len(sessions) == 2
    assert sessions[0].id == s2.id

@pytest.mark.asyncio
async def test_list_sessions_excluye_inactivas(db_session, regular_user: User, session_cleanup):
    """Las sesiones eliminadas (soft delete) no deben aparecer en el listado."""
    session = await create_session(regular_user.id, MODEL, db_session)
    session_cleanup.append(str(session.id))

    await delete_session(str(session.id), regular_user.id, db_session)
    sessions = await list_sessions(regular_user.id, db_session)
    assert sessions == []

@pytest.mark.asyncio
async def test_persist_messages_guarda_en_postgres(db_session, regular_user: User, session_cleanup):
    """persist_messages debe guardar el historial de Redis en PostgreSQL."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Hola, ¿qué es una lista?")
    await append_to_history(sid, "assistant", "Una lista es una estructura de datos.")

    await persist_messages(sid, db_session)

    # Verificar leyendo directamente desde PostgreSQL
    from sqlalchemy import select
    from app.db.models import Message
    result = await db_session.execute(
        select(Message).where(Message.session_id == session.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"

@pytest.mark.asyncio
async def test_persist_messages_evita_duplicados(db_session, regular_user: User, session_cleanup):
    """Llamar persist_messages dos veces no debe duplicar mensajes."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Mensaje único")
    await persist_messages(sid, db_session)
    await persist_messages(sid, db_session)  # segunda llamada

    from sqlalchemy import select
    from app.db.models import Message
    result = await db_session.execute(
        select(Message).where(Message.session_id == session.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 1

@pytest.mark.asyncio
async def test_load_history_desde_postgres(db_session, regular_user: User, session_cleanup):
    """load_history debe recuperar mensajes desde PostgreSQL y cargarlos en Redis."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Pregunta original")
    await append_to_history(sid, "assistant", "Respuesta original")
    await persist_messages(sid, db_session)

    # Simular pérdida de Redis
    from app.memory.session import clear_session
    await clear_session(sid)

    history = await load_history(sid, db_session)
    assert len(history) == 2
    assert history[0]["content"] == "Pregunta original"

    # Confirmar que también quedó cargado en Redis
    redis_history = await get_session_history(sid)
    assert len(redis_history) == 2

@pytest.mark.asyncio
async def test_get_session_detail_desde_redis(db_session, regular_user: User, session_cleanup):
    """get_session_detail debe priorizar el historial de Redis si existe."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Mensaje en Redis")

    found_session, history = await get_session_detail(sid, regular_user.id, db_session)
    assert found_session is not None
    assert len(history) == 1
    assert history[0]["content"] == "Mensaje en Redis"

@pytest.mark.asyncio
async def test_get_session_detail_fallback_postgres(db_session, regular_user: User, session_cleanup):
    """Si Redis no tiene historial, debe recuperarlo desde PostgreSQL."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Mensaje persistido")
    await persist_messages(sid, db_session)

    from app.memory.session import clear_session
    await clear_session(sid)

    found_session, history = await get_session_detail(sid, regular_user.id, db_session)
    assert found_session is not None
    assert len(history) == 1
    assert history[0]["content"] == "Mensaje persistido"

@pytest.mark.asyncio
async def test_get_session_detail_no_encontrada(db_session, regular_user: User):
    """get_session_detail debe retornar None si la sesión no existe."""
    fake_id = str(uuid.uuid4())
    found_session, history = await get_session_detail(fake_id, regular_user.id, db_session)
    assert found_session is None
    assert history == []

@pytest.mark.asyncio
async def test_get_session_detail_usuario_incorrecto(db_session, regular_user: User, second_user: User, session_cleanup):
    """Un usuario no debe poder ver el detalle de la sesión de otro usuario."""
    session = await create_session(regular_user.id, MODEL, db_session)
    session_cleanup.append(str(session.id))

    found_session, history = await get_session_detail(str(session.id), second_user.id, db_session)
    assert found_session is None

@pytest.mark.asyncio
async def test_delete_session_soft_delete(db_session, regular_user: User, session_cleanup):
    """delete_session debe marcar is_active=False sin borrar la fila."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    deleted = await delete_session(sid, regular_user.id, db_session)
    assert deleted is True

    from sqlalchemy import select
    from app.db.models import Session as SessionModel
    result = await db_session.execute(
        select(SessionModel).where(SessionModel.id == session.id)
    )
    refreshed = result.scalar_one()
    assert refreshed.is_active is False

@pytest.mark.asyncio
async def test_delete_session_persiste_antes_de_cerrar(db_session, regular_user: User, session_cleanup):
    """delete_session debe persistir el historial de Redis antes de cerrar la sesión."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Último mensaje antes de cerrar")
    await delete_session(sid, regular_user.id, db_session)

    from sqlalchemy import select
    from app.db.models import Message
    result = await db_session.execute(
        select(Message).where(Message.session_id == session.id)
    )
    messages = result.scalars().all()
    assert len(messages) == 1

@pytest.mark.asyncio
async def test_delete_session_limpia_redis(db_session, regular_user: User, session_cleanup):
    """delete_session debe limpiar el historial de Redis tras cerrar."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Mensaje temporal")
    await delete_session(sid, regular_user.id, db_session)

    history = await get_session_history(sid)
    assert history == []

@pytest.mark.asyncio
async def test_delete_session_no_encontrada(db_session, regular_user: User):
    """delete_session debe retornar False si la sesión no existe."""
    fake_id = str(uuid.uuid4())
    deleted = await delete_session(fake_id, regular_user.id, db_session)
    assert deleted is False

@pytest.mark.asyncio
async def test_generate_session_title_trunca_a_50_caracteres(db_session, regular_user: User, session_cleanup):
    """El título generado no debe exceder 50 caracteres + '...'."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    mensaje_largo = "Este es un mensaje extremadamente largo que definitivamente supera los cincuenta caracteres permitidos"
    await generate_session_title(sid, mensaje_largo, db_session)

    from sqlalchemy import select
    from app.db.models import Session as SessionModel
    result = await db_session.execute(
        select(SessionModel).where(SessionModel.id == session.id)
    )
    refreshed = result.scalar_one()
    assert len(refreshed.title) <= 53  # 50 + "..."
    assert refreshed.title.endswith("...")

@pytest.mark.asyncio
async def test_generate_session_title_mensaje_corto(db_session, regular_user: User, session_cleanup):
    """Un mensaje corto no debe llevar puntos suspensivos."""
    session = await create_session(regular_user.id, MODEL, db_session)
    sid = str(session.id)
    session_cleanup.append(sid)

    await generate_session_title(sid, "Hola", db_session)

    from sqlalchemy import select
    from app.db.models import Session as SessionModel
    result = await db_session.execute(
        select(SessionModel).where(SessionModel.id == session.id)
    )
    refreshed = result.scalar_one()
    assert refreshed.title == "Hola"
    assert not refreshed.title.endswith("...")

# ══════════════════════════════════════════════════════════════
# Tests de integración — endpoints HTTP
# ══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_post_sessions_endpoint(client: AsyncClient, regular_user: User, session_cleanup):
    """POST /sessions debe crear una sesión y retornar su UUID."""
    response = await client.post(
        "/sessions",
        json={"model": MODEL},
        headers=get_headers(regular_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["model_used"] == MODEL
    assert data["is_active"] is True
    session_cleanup.append(data["id"])

@pytest.mark.asyncio
async def test_get_sessions_endpoint(client: AsyncClient, regular_user: User, session_cleanup):
    """GET /sessions debe listar las sesiones del usuario autenticado."""
    create_resp = await client.post(
        "/sessions", json={"model": MODEL}, headers=get_headers(regular_user)
    )
    session_cleanup.append(create_resp.json()["id"])

    response = await client.get("/sessions", headers=get_headers(regular_user))
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1

@pytest.mark.asyncio
async def test_get_sessions_aislamiento_entre_usuarios(
    client: AsyncClient, regular_user: User, second_user: User, session_cleanup
):
    """Un usuario no debe ver sesiones creadas por otro usuario."""
    create_resp = await client.post(
        "/sessions", json={"model": MODEL}, headers=get_headers(regular_user)
    )
    session_cleanup.append(create_resp.json()["id"])

    response = await client.get("/sessions", headers=get_headers(second_user))
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_session_detail_endpoint(client: AsyncClient, regular_user: User, session_cleanup):
    """GET /sessions/{id} debe retornar el detalle con mensajes."""
    create_resp = await client.post(
        "/sessions", json={"model": MODEL}, headers=get_headers(regular_user)
    )
    sid = create_resp.json()["id"]
    session_cleanup.append(sid)

    await append_to_history(sid, "user", "Mensaje de prueba")

    response = await client.get(f"/sessions/{sid}", headers=get_headers(regular_user))
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sid
    assert len(data["messages"]) == 1

@pytest.mark.asyncio
async def test_get_session_detail_endpoint_404(client: AsyncClient, regular_user: User):
    """GET /sessions/{id} con UUID inexistente debe retornar 404."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/sessions/{fake_id}", headers=get_headers(regular_user))
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_session_detail_endpoint_otro_usuario_404(
    client: AsyncClient, regular_user: User, second_user: User, session_cleanup
):
    """Un usuario no debe poder ver el detalle de sesión de otro usuario (404, no 403)."""
    create_resp = await client.post(
        "/sessions", json={"model": MODEL}, headers=get_headers(regular_user)
    )
    sid = create_resp.json()["id"]
    session_cleanup.append(sid)

    response = await client.get(f"/sessions/{sid}", headers=get_headers(second_user))
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_session_endpoint(client: AsyncClient, regular_user: User, session_cleanup):
    """DELETE /sessions/{id} debe eliminar (soft delete) la sesión."""
    create_resp = await client.post(
        "/sessions", json={"model": MODEL}, headers=get_headers(regular_user)
    )
    sid = create_resp.json()["id"]
    session_cleanup.append(sid)

    response = await client.delete(f"/sessions/{sid}", headers=get_headers(regular_user))
    assert response.status_code == 200
    assert response.json()["session_id"] == sid

    # La sesión ya no debe aparecer en el listado
    list_resp = await client.get("/sessions", headers=get_headers(regular_user))
    assert list_resp.json() == []

@pytest.mark.asyncio
async def test_delete_session_endpoint_404(client: AsyncClient, regular_user: User):
    """DELETE /sessions/{id} con UUID inexistente debe retornar 404."""
    fake_id = str(uuid.uuid4())
    response = await client.delete(f"/sessions/{fake_id}", headers=get_headers(regular_user))
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_sessions_requieren_autenticacion(client: AsyncClient):
    """Todos los endpoints de /sessions deben requerir token."""
    assert (await client.post("/sessions", json={"model": MODEL})).status_code == 401
    assert (await client.get("/sessions")).status_code == 401
    fake_id = str(uuid.uuid4())
    assert (await client.get(f"/sessions/{fake_id}")).status_code == 401
    assert (await client.delete(f"/sessions/{fake_id}")).status_code == 401