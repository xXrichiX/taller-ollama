import uuid
from pathlib import Path
from typing import Any

import chromadb
import ollama

from config import CHROMA_COLLECTION, CHROMA_PATH, OLLAMA_EMBED_MODEL
from services.cita_service import list_fallas


class RagService:
    """RAG con ChromaDB. Indexa fallas de MySQL en db_vectorial/iespro_taller_fallas."""

    def __init__(self):
        Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed(self, text: str) -> list[float]:
        try:
            result = ollama.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text)
            return result["embedding"]
        except Exception as exc:
            raise RuntimeError(
                f"No se pudo generar embedding con '{OLLAMA_EMBED_MODEL}'. "
                f"Ejecuta: ollama pull {OLLAMA_EMBED_MODEL}. Error: {exc}"
            ) from exc

    def sync_fallas_from_db(self) -> int:
        fallas = list_fallas()
        existing = set(self.collection.get(include=[])["ids"])
        added = 0

        for falla in fallas:
            doc_id = f"falla_{falla['id']}"
            if doc_id in existing:
                continue

            text = falla["descripcion"]
            if falla.get("diagnostico"):
                text += f" Diagnóstico: {falla['diagnostico']}"

            self.collection.add(
                ids=[doc_id],
                embeddings=[self._embed(text)],
                documents=[text],
                metadatas=[{
                    "falla_id": str(falla["id"]),
                    "placa": falla.get("placa") or "",
                    "id_cita": str(falla.get("id_cita") or ""),
                    "resuelto": str(falla.get("resuelto", 0)),
                    "origen": "mysql",
                }],
            )
            added += 1

        return added

    def search_similar(self, query: str, n_results: int = 5) -> dict[str, Any]:
        import time

        start = time.perf_counter()
        results = self.collection.query(
            query_embeddings=[self._embed(query)],
            n_results=n_results,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        matches = []
        for doc, meta, dist in zip(docs, metas, distances):
            matches.append({
                "texto": doc,
                "placa": meta.get("placa", ""),
                "id_cita": meta.get("id_cita", ""),
                "distancia": round(dist, 4),
            })

        return {
            "matches": matches,
            "latency_ms": round(latency_ms, 2),
            "total_indexados": self.collection.count(),
        }

    def index_text(self, text: str, metadata: dict | None = None) -> None:
        meta = metadata or {}
        meta.setdefault("origen", "manual")
        self.collection.add(
            ids=[str(uuid.uuid4())],
            embeddings=[self._embed(text)],
            documents=[text],
            metadatas=[meta],
        )

    def info(self) -> dict:
        return {
            "path": CHROMA_PATH,
            "collection": CHROMA_COLLECTION,
            "registros": self.collection.count(),
        }
