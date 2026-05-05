DOMINIOS_VALIDOS = {"uandresbello.edu", "unab.cl"}

async def validate_university_credentials(email: str, password: str) -> bool:
    """
    Valida que el correo pertenezca a un dominio universitario autorizado.
    """
    try:
        dominio = email.strip().lower().split("@")[1]
        return dominio in DOMINIOS_VALIDOS
    except IndexError:
        return False