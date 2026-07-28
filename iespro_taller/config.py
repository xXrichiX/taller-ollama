import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "iespro_app")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_APP_PASSWORD", "iespro_dev_only")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "iespro_taller_app")

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("OLLAMA_HOST", OLLAMA_HOST)
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Ventana de contexto del chat (llama3.2:3b soporta 128k; reservamos poco en local por VRAM/latencia)
OLLAMA_CONTEXT_MAX_TOKENS = int(os.getenv("OLLAMA_CONTEXT_MAX_TOKENS", "2048"))
OLLAMA_CONTEXT_MESSAGE_CAP = int(os.getenv("OLLAMA_CONTEXT_MESSAGE_CAP", "40"))
OLLAMA_CONTEXT_RESERVED_TOKENS = int(os.getenv("OLLAMA_CONTEXT_RESERVED_TOKENS", "768"))

# ChromaDB — misma carpeta que el proyecto RAG original (./db_vectorial)
CHROMA_PATH = os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "db_vectorial"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "iespro_taller_fallas")

DOCUMENTS_PATH = BASE_DIR / "data" / "documentos"
DEFAULT_SUCURSAL_ID = int(os.getenv("DEFAULT_SUCURSAL_ID", "1"))

# API / CORS (Semana 6)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

# Advanced RAG (Semana 7)
RAG_HYBRID_FETCH_K = int(os.getenv("RAG_HYBRID_FETCH_K", "10"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "3"))
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

# Evaluador
EVAL_API_BASE = os.getenv("EVAL_API_BASE", f"http://localhost:{API_PORT}")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", OLLAMA_CHAT_MODEL)

# Seguridad / entorno
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV in ("production", "prod")
REGISTRATION_ENABLED = os.getenv(
  "REGISTRATION_ENABLED",
  "0" if IS_PRODUCTION else "1",
) == "1"
REGISTRATION_INVITE_CODE = os.getenv("REGISTRATION_INVITE_CODE", "").strip()
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") == "1"

SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "iespro_session")
SESSION_COOKIE_SECURE = os.getenv(
  "SESSION_COOKIE_SECURE",
  "1" if IS_PRODUCTION else "0",
) == "1"
SESSION_COOKIE_MAX_AGE = int(os.getenv("SESSION_COOKIE_MAX_AGE", str(60 * 60 * 24 * 7)))
SESSION_IDLE_SECONDS = int(os.getenv("SESSION_IDLE_SECONDS", str(60 * 60 * 24)))

TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "1" if IS_PRODUCTION else "0") == "1"
MAX_TOOL_CALLS_PER_TURN = int(os.getenv("MAX_TOOL_CALLS_PER_TURN", "8"))

TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "").strip()
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "").strip()

# Límites de creación de recursos (anti-DoS)
MAX_SUCURSALES_PER_OWNER = int(os.getenv("MAX_SUCURSALES_PER_OWNER", "5"))
MAX_ISLAS_PER_SUCURSAL = int(os.getenv("MAX_ISLAS_PER_SUCURSAL", "12"))

# Auditoría forense
AUDIT_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "365"))
AUDIT_HMAC_SECRET = os.getenv("AUDIT_HMAC_SECRET", "").strip()

# Métricas Prometheus (red interna o METRICS_TOKEN)
METRICS_TOKEN = os.getenv("METRICS_TOKEN", "").strip()

# Sesiones API (memory en dev, mysql en producción)
SESSION_STORE = os.getenv(
  "SESSION_STORE",
  "mysql" if IS_PRODUCTION else "memory",
).strip().lower()

# Verificación de correo (desactivada por defecto; Clouding y otros VPS suelen bloquear SMTP saliente)
EMAIL_VERIFICATION_ENABLED = os.getenv("EMAIL_VERIFICATION_ENABLED", "0") == "1"

# SMTP / verificación de correo (solo si EMAIL_VERIFICATION_ENABLED=1)
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
SMTP_FROM = os.getenv("SMTP_FROM", "").strip()
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "1") == "1"
EMAIL_VERIFICATION_SECRET = os.getenv("EMAIL_VERIFICATION_SECRET", AUDIT_HMAC_SECRET).strip()

# Voz (micrófono): umbrales anti-ruido; ajustables por env si hace falta
VOICE_SILENCE_SECONDS = float(os.getenv("VOICE_SILENCE_SECONDS", "1.2"))
VOICE_RMS_MIN = float(os.getenv("VOICE_RMS_MIN", "450"))
VOICE_RMS_CALIBRATION_S = float(os.getenv("VOICE_RMS_CALIBRATION_S", "0.35"))
VOICE_RMS_MULTIPLIER = float(os.getenv("VOICE_RMS_MULTIPLIER", "2.4"))
VOICE_RMS_OFFSET = float(os.getenv("VOICE_RMS_OFFSET", "120"))
