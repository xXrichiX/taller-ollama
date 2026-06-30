"""Validación mínima de contraseñas."""

import re

MIN_PASSWORD_LEN = 8
MAX_PASSWORD_LEN = 64

_COMMON_PASSWORDS = frozenset({
    "123456", "12345678", "123456789", "password", "password1",
    "qwerty", "qwerty123", "admin123", "letmein", "welcome",
    "abc123", "111111", "123123", "iloveyou", "monkey",
    "dragon", "master", "login", "princess", "football",
    "shadow", "sunshine", "passw0rd", "admin1234",
})


def normalize_password(password: str) -> str:
    return (password or "").strip()


def validate_password(password: str, email: str | None = None) -> tuple[bool, str]:
    pwd = normalize_password(password)
    if not pwd:
        return False, "La contraseña es obligatoria."
    if len(pwd) < MIN_PASSWORD_LEN:
        return False, f"La contraseña debe tener al menos {MIN_PASSWORD_LEN} caracteres."
    if len(pwd) > MAX_PASSWORD_LEN:
        return False, f"La contraseña no puede superar {MAX_PASSWORD_LEN} caracteres."
    if not re.search(r"[A-Za-z]", pwd):
        return False, "La contraseña debe incluir al menos una letra."
    if not re.search(r"\d", pwd):
        return False, "La contraseña debe incluir al menos un número."
    if email and pwd.lower() == email.strip().lower():
        return False, "La contraseña no puede ser igual al correo."
    if pwd.lower() in _COMMON_PASSWORDS:
        return False, "Esa contraseña es muy común. Elige otra."
    return True, ""
