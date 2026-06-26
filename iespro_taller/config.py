import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root2919")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "iespro_taller_app")

# Ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
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

# Voz (micrófono): umbrales anti-ruido; ajustables por env si hace falta
VOICE_SILENCE_SECONDS = float(os.getenv("VOICE_SILENCE_SECONDS", "1.2"))
VOICE_RMS_MIN = float(os.getenv("VOICE_RMS_MIN", "450"))
VOICE_RMS_CALIBRATION_S = float(os.getenv("VOICE_RMS_CALIBRATION_S", "0.35"))
VOICE_RMS_MULTIPLIER = float(os.getenv("VOICE_RMS_MULTIPLIER", "2.4"))
VOICE_RMS_OFFSET = float(os.getenv("VOICE_RMS_OFFSET", "120"))
