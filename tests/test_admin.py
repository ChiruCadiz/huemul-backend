import pytest
from httpx import AsyncClient
from app.auth.jwt import create_access_token
from app.db.models import User

def get_admin_headers(admin_user: User) -> dict:
    token = create_access_token({
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role,
        "email": admin_user.email
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_config(client: AsyncClient, admin_user: User):
    response = await client.get(
        "/admin/config",
        headers=get_admin_headers(admin_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "system_prompt"
    assert data["value"] == "Prompt de prueba."

@pytest.mark.asyncio
async def test_update_config(client: AsyncClient, admin_user: User):
    nuevo_prompt = "Nuevo system prompt institucional."
    response = await client.put(
        "/admin/config",
        json={"value": nuevo_prompt},
        headers=get_admin_headers(admin_user)
    )
    assert response.status_code == 200
    assert response.json()["value"] == nuevo_prompt

@pytest.mark.asyncio
async def test_update_config_usuario_estandar(client: AsyncClient, regular_user: User):
    token = create_access_token({
        "sub": str(regular_user.id),
        "username": regular_user.username,
        "role": regular_user.role,
        "email": regular_user.email
    })
    response = await client.put(
        "/admin/config",
        json={"value": "Intento no autorizado."},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_list_users(client: AsyncClient, admin_user: User):
    response = await client.get(
        "/admin/users",
        headers=get_admin_headers(admin_user)
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_update_user_role(client: AsyncClient, admin_user: User, regular_user: User):
    response = await client.put(
        f"/admin/users/{regular_user.id}/role?role=admin",
        headers=get_admin_headers(admin_user)
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"

@pytest.mark.asyncio
async def test_update_user_role_invalido(client: AsyncClient, admin_user: User, regular_user: User):
    response = await client.put(
        f"/admin/users/{regular_user.id}/role?role=superusuario",
        headers=get_admin_headers(admin_user)
    )
    assert response.status_code == 400