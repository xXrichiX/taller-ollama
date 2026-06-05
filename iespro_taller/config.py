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

# ChromaDB — misma carpeta que el proyecto RAG original (./db_vectorial)
CHROMA_PATH = os.getenv("CHROMA_PATH", str(PROJECT_ROOT / "db_vectorial"))
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "iespro_taller_fallas")

DOCUMENTS_PATH = BASE_DIR / "data" / "documentos"
DEFAULT_SUCURSAL_ID = int(os.getenv("DEFAULT_SUCURSAL_ID", "1"))
