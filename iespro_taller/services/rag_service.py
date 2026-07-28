import uuid
from pathlib import Path
from typing import Any

import chromadb
import ollama
from rank_bm25 import BM25Okapi

from config import (
  CHROMA_COLLECTION,
  CHROMA_PATH,
  OLLAMA_EMBED_MODEL,
  RAG_HYBRID_FETCH_K,
  RAG_RERANK_TOP_K,
)
from services.cita_service import list_fallas
from services.reranker import rerank

_TOKEN_RE = __import__("re").compile(r"\w+", __import__("re").UNICODE)


def _tokenize(text: str) -> list[str]:
  return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


class RagService:
  """RAG con ChromaDB + búsqueda híbrida (BM25 + vector) + reranking."""

  def __init__(self):
    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)

    self.client = chromadb.PersistentClient(path=CHROMA_PATH)
    self.collection = self.client.get_or_create_collection(
      name=CHROMA_COLLECTION,
      metadata={"hnsw:space": "cosine"},
    )
    self._bm25: BM25Okapi | None = None
    self._bm25_docs: list[dict[str, Any]] = []
    self._rebuild_bm25_index()

  def _embed(self, text: str) -> list[float]:
    try:
      result = ollama.embeddings(model=OLLAMA_EMBED_MODEL, prompt=text)
      return result["embedding"]
    except Exception as exc:
      raise RuntimeError(
        f"No se pudo generar embedding con '{OLLAMA_EMBED_MODEL}'. "
        f"Ejecuta: ollama pull {OLLAMA_EMBED_MODEL}. Error: {exc}"
      ) from exc

  def _rebuild_bm25_index(self) -> None:
    data = self.collection.get(include=["documents", "metadatas"])
    ids = data.get("ids") or []
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []
    self._bm25_docs = []
    corpus: list[list[str]] = []
    for doc_id, doc, meta in zip(ids, docs, metas):
      if not doc:
        continue
      self._bm25_docs.append({"id": doc_id, "texto": doc, "meta": meta or {}})
      corpus.append(_tokenize(doc))
    self._bm25 = BM25Okapi(corpus) if corpus else None

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
      if falla.get("solucion"):
        text += f" Solución: {falla['solucion']}"

      self.collection.add(
        ids=[doc_id],
        embeddings=[self._embed(text)],
        documents=[text],
        metadatas=[{
          "falla_id": str(falla["id"]),
          "placa": falla.get("placa") or "",
          "id_cita": str(falla.get("id_cita") or ""),
          "id_mecanico": str(falla.get("id_mecanico") or ""),
          "id_sucursal": str(falla.get("id_sucursal") or ""),
          "resuelto": str(falla.get("resuelto", 0)),
          "origen": "mysql",
        }],
      )
      added += 1

    if added:
      self._rebuild_bm25_index()
    return added

  @staticmethod
  def _rrf_fusion(
    dense: list[dict[str, Any]],
    sparse: list[dict[str, Any]],
    *,
    k: int = 60,
  ) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    items: dict[str, dict[str, Any]] = {}

    for rank, item in enumerate(dense):
      doc_id = item["id"]
      scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
      items[doc_id] = item

    for rank, item in enumerate(sparse):
      doc_id = item["id"]
      scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank + 1)
      items[doc_id] = item

    fused = []
    for doc_id, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
      merged = dict(items[doc_id])
      merged["rrf_score"] = round(score, 6)
      fused.append(merged)
    return fused

  def _bm25_search(self, query: str, n: int) -> list[dict[str, Any]]:
    if not self._bm25 or not self._bm25_docs:
      return []
    tokens = _tokenize(query)
    if not tokens:
      return []
    scores = self._bm25.get_scores(tokens)
    ranked = sorted(
      zip(self._bm25_docs, scores),
      key=lambda x: x[1],
      reverse=True,
    )[:n]
    out = []
    for doc, score in ranked:
      meta = doc.get("meta") or {}
      out.append({
        "id": doc["id"],
        "texto": doc["texto"],
        "placa": meta.get("placa", ""),
        "id_cita": meta.get("id_cita", ""),
        "id_mecanico": meta.get("id_mecanico", ""),
        "id_sucursal": meta.get("id_sucursal", ""),
        "bm25_score": round(float(score), 4),
      })
    return out

  def _vector_search(self, query: str, n: int) -> list[dict[str, Any]]:
    results = self.collection.query(
      query_embeddings=[self._embed(query)],
      n_results=max(n, 1),
    )
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    ids = results.get("ids", [[]])[0]

    out = []
    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
      meta = meta or {}
      out.append({
        "id": doc_id,
        "texto": doc,
        "placa": meta.get("placa", ""),
        "id_cita": meta.get("id_cita", ""),
        "id_mecanico": meta.get("id_mecanico", ""),
        "id_sucursal": meta.get("id_sucursal", ""),
        "distancia": round(dist, 4),
      })
    return out

  def hybrid_search(
    self,
    query: str,
    *,
    fetch_k: int | None = None,
    top_k: int | None = None,
    id_sucursal: int | None = None,
    id_mecanico: int | None = None,
  ) -> dict[str, Any]:
    import time

    start = time.perf_counter()
    fetch = fetch_k or RAG_HYBRID_FETCH_K
    final_k = top_k or RAG_RERANK_TOP_K

    dense = self._vector_search(query, fetch)
    sparse = self._bm25_search(query, fetch)
    fused = self._rrf_fusion(dense, sparse)[:fetch]

    if id_sucursal or id_mecanico:
      filtered = []
      for item in fused:
        meta_suc = str(item.get("id_sucursal") or "")
        meta_mec = str(item.get("id_mecanico") or "")
        if id_sucursal and meta_suc and meta_suc != str(id_sucursal):
          continue
        if id_mecanico and meta_mec and meta_mec != str(id_mecanico):
          continue
        filtered.append(item)
      fused = filtered

    reranked = rerank(query, fused, top_k=final_k)
    latency_ms = (time.perf_counter() - start) * 1000

    return {
      "matches": reranked,
      "latency_ms": round(latency_ms, 2),
      "total_indexados": self.collection.count(),
      "pipeline": "hybrid_rrf_rerank",
      "fetch_k": fetch,
      "top_k": final_k,
    }

  def search_similar(
    self,
    query: str,
    n_results: int = 5,
    *,
    id_sucursal: int | None = None,
    id_mecanico: int | None = None,
  ) -> dict[str, Any]:
    return self.hybrid_search(
      query,
      fetch_k=max(RAG_HYBRID_FETCH_K, n_results * 2),
      top_k=n_results,
      id_sucursal=id_sucursal,
      id_mecanico=id_mecanico,
    )

  def index_text(self, text: str, metadata: dict | None = None) -> None:
    meta = metadata or {}
    meta.setdefault("origen", "manual")
    self.collection.add(
      ids=[str(uuid.uuid4())],
      embeddings=[self._embed(text)],
      documents=[text],
      metadatas=[meta],
    )
    self._rebuild_bm25_index()

  def info(self) -> dict:
    return {
      "path": CHROMA_PATH,
      "collection": CHROMA_COLLECTION,
      "registros": self.collection.count(),
      "bm25_docs": len(self._bm25_docs),
      "pipeline": "hybrid_rrf_rerank",
    }
