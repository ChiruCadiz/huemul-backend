import aiosmtplib
from email.message import EmailMessage
from loguru import logger
from app.config import settings


async def send_reset_email(to_email: str, token: str) -> None:
    reset_link = f"http://localhost:8000/auth/reset-password-page?token={token}"

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = "Huemul — Recuperación de contraseña"
    message.set_content(
        f"Recibimos una solicitud para restablecer tu contraseña.\n\n"
        f"Haz clic en el siguiente link (válido por 1 hora):\n{reset_link}\n\n"
        f"Si no solicitaste esto, ignora este correo."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            start_tls=True,
            username=settings.smtp_user,
            password=settings.smtp_password,
        )
        logger.info(f"Email de recuperación enviado a {to_email}")
    except Exception as e:
        logger.error(f"Error enviando email a {to_email}: {e}")