"""Verificación de correo en registro (producción)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from config import (
  EMAIL_VERIFICATION_SECRET,
  IS_PRODUCTION,
  SMTP_FROM,
  SMTP_HOST,
  SMTP_PASSWORD,
  SMTP_PORT,
  SMTP_USE_TLS,
  SMTP_USER,
)
from db.connection import execute, fetch_one


def smtp_configured() -> bool:
  return bool(SMTP_HOST and SMTP_FROM)


def ensure_email_verification_columns() -> None:
  cols = fetch_one(
    """
    SELECT COUNT(*) AS n FROM information_schema.columns
    WHERE table_schema = DATABASE() AND table_name = 'usuarios' AND column_name = 'email_verificado'
    """
  )
  if cols and int(cols["n"]) == 0:
    execute("ALTER TABLE usuarios ADD COLUMN email_verificado TINYINT(1) NOT NULL DEFAULT 1")
    execute("ALTER TABLE usuarios ADD COLUMN email_verify_hash VARCHAR(128) NULL")
    execute("ALTER TABLE usuarios ADD COLUMN email_verify_expires DATETIME NULL")


def _hash_code(email: str, code: str) -> str:
  secret = EMAIL_VERIFICATION_SECRET or "dev-only-email-secret"
  payload = f"{email.strip().lower()}:{code}"
  return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_verification_code(id_usuario: int, email: str) -> str:
  code = f"{secrets.randbelow(1_000_000):06d}"
  expires = datetime.now(timezone.utc) + timedelta(minutes=30)
  execute(
    """
    UPDATE usuarios
    SET email_verificado = 0,
        email_verify_hash = %s,
        email_verify_expires = %s
    WHERE id = %s
    """,
    (_hash_code(email, code), expires.replace(tzinfo=None), id_usuario),
  )
  return code


def send_verification_email(to_email: str, code: str) -> bool:
  if not smtp_configured():
    return False
  msg = EmailMessage()
  msg["Subject"] = "Verifica tu correo — IESPRO Taller"
  msg["From"] = SMTP_FROM
  msg["To"] = to_email
  msg.set_content(
    f"Tu código de verificación es: {code}\n\n"
    "Expira en 30 minutos. Si no solicitaste este registro, ignora este mensaje."
  )
  try:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
      if SMTP_USE_TLS:
        smtp.starttls()
      if SMTP_USER:
        smtp.login(SMTP_USER, SMTP_PASSWORD)
      smtp.send_message(msg)
    return True
  except OSError:
    return False


def verify_email_code(email: str, code: str) -> bool:
  row = fetch_one(
    """
    SELECT id, email_verify_hash, email_verify_expires, email_verificado
    FROM usuarios
    WHERE LOWER(email) = %s AND activo = 1
    """,
    (email.strip().lower(),),
  )
  if not row or int(row.get("email_verificado") or 0) == 1:
    return False
  expires = row.get("email_verify_expires")
  if not expires or expires < datetime.utcnow():
    return False
  expected = row.get("email_verify_hash") or ""
  if not hmac.compare_digest(expected, _hash_code(email, code.strip())):
    return False
  execute(
    """
    UPDATE usuarios
    SET email_verificado = 1, email_verify_hash = NULL, email_verify_expires = NULL
    WHERE id = %s
    """,
    (row["id"],),
  )
  return True


def is_email_verified(id_usuario: int) -> bool:
  if not IS_PRODUCTION:
    return True
  if not smtp_configured():
    return True
  row = fetch_one(
    "SELECT email_verificado FROM usuarios WHERE id = %s AND activo = 1",
    (id_usuario,),
  )
  if not row:
    return False
  return int(row.get("email_verificado") or 0) == 1


def resend_verification_email(email: str) -> bool:
  row = fetch_one(
    """
    SELECT id, email_verificado
    FROM usuarios
    WHERE LOWER(email) = %s AND activo = 1
    """,
    (email.strip().lower(),),
  )
  if not row or int(row.get("email_verificado") or 0) == 1:
    return False
  code = issue_verification_code(int(row["id"]), email)
  return send_verification_email(email, code)
