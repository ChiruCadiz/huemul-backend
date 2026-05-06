import pytest
from httpx import AsyncClient
from app.auth.jwt import create_access_token
from app.db.models import User

@pytest.mark.asyncio
async def test_get_current_user_sin_token(client: AsyncClient):
    response = await client.get("/admin/config")
    assert response.status_code == 401  # HTTPBearer retorna 403 sin token

@pytest.mark.asyncio
async def test_get_current_user_token_invalido(client: AsyncClient):
    response = await client.get(
        "/admin/config",
        headers={"Authorization": "Bearer token.invalido.aqui"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_require_admin_con_usuario_estandar(client: AsyncClient, regular_user: User):
    token = create_access_token({
        "sub": str(regular_user.id),
        "username": regular_user.username,
        "role": regular_user.role,
        "email": regular_user.email
    })
    response = await client.get(
        "/admin/config",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_require_admin_con_admin(client: AsyncClient, admin_user: User):
    token = create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role,
        "email": admin_user.email
    })
    response = await client.get(
        "/admin/config",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200