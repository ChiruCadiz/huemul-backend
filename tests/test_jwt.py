import pytest
from app.auth.jwt import create_access_token, decode_token

def test_crear_token_valido():
    token = create_access_token({"sub": "1", "role": "user"})
    assert token is not None
    assert isinstance(token, str)

def test_decodificar_token_valido():
    payload = {"sub": "1", "username": "alumno", "role": "user"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "1"
    assert decoded["role"] == "user"

def test_decodificar_token_invalido():
    result = decode_token("esto.no.es.un.token")
    assert result is None

def test_decodificar_token_vacio():
    result = decode_token("")
    assert result is None