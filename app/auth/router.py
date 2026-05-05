from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.db.database import get_db
from app.db.models import User
from app.auth.service import validate_university_credentials
from app.auth.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Validar dominio universitario
    valid = await validate_university_credentials(body.email, body.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El correo debe pertenecer a @uandresbello.edu o @unab.cl"
        )

    # 2. Buscar usuario — si no existe, crearlo automáticamente con rol "user"
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        username = body.email.strip().lower().split("@")[0]
        user = User(username=username, email=body.email, role="user")
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # 3. Emitir JWT con id, username, role y email
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "email": user.email
    })

    return LoginResponse(
        access_token=token,
        role=user.role,
        email=user.email
    )

@router.post("/logout")
async def logout():
    return {"message": "Sesión cerrada correctamente."}