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

@pytest.mark.asyncio
async def test_get_models_ollama_disponible(client: AsyncClient, regular_user: User):
    """GET /models debe retornar lista de modelos cuando Ollama responde."""
    with patch(
        "app.models.router.fetch_available_models",
        return_value=["gemma4:26b", "llama2"]
    ):
        response = await client.get(
            "/models",
            headers=get_headers(regular_user)
        )
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "gemma4:26b" in data["models"]

@pytest.mark.asyncio
async def test_get_models_ollama_caido(client: AsyncClient, regular_user: User):
    """GET /models debe retornar lista vacía con mensaje si Ollama no responde."""
    with patch(
        "app.models.router.fetch_available_models",
        return_value=[]
    ):
        response = await client.get(
            "/models",
            headers=get_headers(regular_user)
        )
    assert response.status_code == 200
    data = response.json()
    assert data["models"] == []
    assert "message" in data

@pytest.mark.asyncio
async def test_get_models_sin_token(client: AsyncClient):
    """GET /models sin token debe retornar 401."""
    response = await client.get("/models")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_default_model(client: AsyncClient, regular_user: User):
    """GET /models/default debe retornar el modelo configurado."""
    response = await client.get(
        "/models/default",
        headers=get_headers(regular_user)
    )
    assert response.status_code == 200
    data = response.json()
    assert "default_model" in data
    assert data["default_model"] == "gemma4:26b"

@pytest.mark.asyncio
async def test_get_default_model_sin_token(client: AsyncClient):
    """GET /models/default sin token debe retornar 401."""
    response = await client.get("/models/default")
    assert response.status_code == 401