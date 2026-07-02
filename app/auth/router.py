from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from loguru import logger

from app.db.database import get_db
from app.db.models import User, PasswordResetToken
from app.auth.jwt import create_access_token
from app.auth.password_service import hash_password, verify_password
from app.auth.email_service import send_reset_email
from app.auth.jwt import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])

ALLOWED_DOMAINS = ("@uandresbello.edu", "@unab.cl")


def _is_university_email(email: str) -> bool:
    return email.strip().lower().endswith(ALLOWED_DOMAINS)


# ══════════════════════════════════════════════════════════════
# Registro
# ══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="El registro público está deshabilitado. Contacta al administrador."
    )

# ══════════════════════════════════════════════════════════════
# Login
# ══════════════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    must_change_password: bool = False

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Mismo mensaje de error tanto si el usuario no existe como si la
    # contraseña es incorrecta — evita revelar qué correos están registrados.
    if not user or not verify_password(body.password, user.password_hash):
        logger.warning(f"Login fallido: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos."
        )

    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "email": user.email,
        "must_change_password": user.must_change_password,
    })

    logger.info(f"Login exitoso: {email} | role={user.role}")
    return LoginResponse(access_token=token, role=user.role, email=user.email, must_change_password=user.must_change_password,)


@router.post("/logout")
async def logout():
    logger.info("Logout solicitado.")
    return {"message": "Sesión cerrada correctamente."}


# ══════════════════════════════════════════════════════════════
# Recuperación de contraseña
# ══════════════════════════════════════════════════════════════

class ForgotPasswordRequest(BaseModel):
    email: str

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    # Responder igual exista o no el usuario — evita enumeración de correos
    if user:
        token = secrets.token_urlsafe(32)
        reset = PasswordResetToken(
            user_id=user.id,
            token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset)
        await db.commit()
        await send_reset_email(user.email, token)
        logger.info(f"Token de recuperación generado para: {email}")

    return {"message": "Si el correo existe, se envió un link de recuperación."}


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    reset = result.scalar_one_or_none()

    if not reset or reset.used or reset.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El link de recuperación es inválido o expiró. Solicita uno nuevo."
        )

    if len(body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 8 caracteres."
        )

    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado.")

    user.password_hash = hash_password(body.new_password)
    reset.used = True
    await db.commit()

    logger.info(f"Contraseña restablecida para: {user.email}")
    return {"message": "Contraseña actualizada correctamente. Ya puedes iniciar sesión."}


# ══════════════════════════════════════════════════════════════
# Página simple para que el usuario ingrese la nueva contraseña
# (el link del email apunta aquí)
# ══════════════════════════════════════════════════════════════

@router.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page(token: str):
    return f"""
    <html>
      <body style="font-family: sans-serif; max-width: 400px; margin: 60px auto;">
        <h2>Huemul — Nueva contraseña</h2>
        <form id="resetForm">
          <input type="hidden" id="token" value="{token}" />
          <label>Nueva contraseña (mínimo 8 caracteres):</label><br/>
          <input type="password" id="newPassword" minlength="8" required style="width:100%;padding:8px;margin:8px 0;" /><br/>
          <button type="submit" style="padding:8px 16px;">Actualizar contraseña</button>
        </form>
        <p id="status"></p>
        <script>
          document.getElementById('resetForm').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const token = document.getElementById('token').value;
            const new_password = document.getElementById('newPassword').value;
            const res = await fetch('/auth/reset-password', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ token, new_password }})
            }});
            const data = await res.json();
            document.getElementById('status').textContent = data.detail || data.message;
          }});
        </script>
      </body>
    </html>
    """

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(401, "Contraseña actual incorrecta.")

    if len(body.new_password) < 8:
        raise HTTPException(400, "La nueva contraseña debe tener al menos 8 caracteres.")

    current_user.password_hash = hash_password(body.new_password)
    current_user.must_change_password = False
    await db.commit()

    logger.info(f"Contraseña cambiada: {current_user.email}")
    return {"message": "Contraseña actualizada correctamente."}