"""Re-rankeo local: CrossEncoder opcional o fallback con Ollama."""

from __future__ import annotations

import logging
import re
from typing import Any

import ollama

from config import OLLAMA_CHAT_MODEL, RERANKER_MODEL

logger = logging.getLogger(__name__)

_cross_encoder = None
_cross_encoder_failed = False


def _get_cross_encoder():
  global _cross_encoder, _cross_encoder_failed
  if _cross_encoder_failed:
    return None
  if _cross_encoder is not None:
    return _cross_encoder
  try:
    from sentence_transformers import CrossEncoder
    _cross_encoder = CrossEncoder(RERANKER_MODEL)
    return _cross_encoder
  except Exception:
    logger.info("CrossEncoder no disponible; usando reranker Ollama")
    _cross_encoder_failed = True
    return None


def rerank(
  query: str,
  candidates: list[dict[str, Any]],
  *,
  top_k: int = 3,
) -> list[dict[str, Any]]:
  if not candidates:
    return []

  encoder = _get_cross_encoder()
  if encoder is not None:
    pairs = [(query, c.get("texto") or c.get("document") or "") for c in candidates]
    scores = encoder.predict(pairs)
    ranked = sorted(
      zip(candidates, scores),
      key=lambda x: float(x[1]),
      reverse=True,
    )
    out = []
    for item, score in ranked[:top_k]:
      enriched = dict(item)
      enriched["rerank_score"] = round(float(score), 4)
      out.append(enriched)
    return out

  return _rerank_with_ollama(query, candidates, top_k=top_k)


def _rerank_with_ollama(
  query: str,
  candidates: list[dict[str, Any]],
  *,
  top_k: int,
) -> list[dict[str, Any]]:
  scored: list[tuple[dict[str, Any], float]] = []
  for cand in candidates:
    doc = (cand.get("texto") or cand.get("document") or "")[:400]
    prompt = f"""Evalúa relevancia de este fragmento para la pregunta del usuario.
Pregunta: {query}
Fragmento: {doc}
Responde SOLO con un número del 0 al 10 (10 = muy relevante)."""
    try:
      resp = ollama.generate(model=OLLAMA_CHAT_MODEL, prompt=prompt)
      raw = (resp.get("response") or "").strip()
      nums = re.findall(r"\d+(?:\.\d+)?", raw)
      score = float(nums[0]) if nums else float(cand.get("rrf_score") or 0)
    except Exception:
      score = float(cand.get("rrf_score") or cand.get("distancia") or 0)
    scored.append((cand, score))

  scored.sort(key=lambda x: x[1], reverse=True)
  out = []
  for item, score in scored[:top_k]:
    enriched = dict(item)
    enriched["rerank_score"] = round(score, 4)
    out.append(enriched)
  return out
