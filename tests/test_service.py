import pytest
from app.auth.service import validate_university_credentials

@pytest.mark.asyncio
async def test_dominio_valido_uandresbello():
    result = await validate_university_credentials("alumno@uandresbello.edu", "1234")
    assert result is True

@pytest.mark.asyncio
async def test_dominio_valido_unab():
    result = await validate_university_credentials("alumno@unab.cl", "1234")
    assert result is True

@pytest.mark.asyncio
async def test_dominio_invalido_gmail():
    result = await validate_university_credentials("alumno@gmail.com", "1234")
    assert result is False

@pytest.mark.asyncio
async def test_dominio_invalido_sin_arroba():
    result = await validate_university_credentials("correo_sin_arroba", "1234")
    assert result is False

@pytest.mark.asyncio
async def test_dominio_invalido_vacio():
    result = await validate_university_credentials("", "1234")
    assert result is False