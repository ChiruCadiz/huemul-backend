import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login_exitoso(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": "nuevo@uandresbello.edu",
        "password": "cualquier_cosa"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "user"
    assert data["email"] == "nuevo@uandresbello.edu"

@pytest.mark.asyncio
async def test_login_dominio_invalido(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": "alumno@gmail.com",
        "password": "1234"
    })
    assert response.status_code == 401
    assert "uandresbello" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_crea_usuario_automaticamente(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": "nuevo@uandresbello.edu",
        "password": "1234"
    })
    assert response.status_code == 200
    # Segunda llamada — el usuario ya existe, no debe duplicarse
    response2 = await client.post("/auth/login", json={
        "email": "nuevo@uandresbello.edu",
        "password": "1234"
    })
    assert response2.status_code == 200
    assert response2.json()["email"] == "nuevo@uandresbello.edu"

@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Sesión cerrada correctamente."