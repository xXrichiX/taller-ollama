"""Agente especialista en RAG: búsqueda híbrida y respuestas sobre fallas históricas."""

from __future__ import annotations

from typing import Any, Callable

import ollama

from config import OLLAMA_CHAT_MODEL
from services.text_format import plain_chat_text
from services.user_roles import is_cliente, is_mecanico


class RagAgent:
  def __init__(self, chat_service: Any):
    self.chat = chat_service

  def run(
    self,
    question: str,
    *,
    handoff: dict[str, Any],
    emit_status: Callable[[str, str], None],
    emit_token: Callable[[str], None],
  ) -> tuple[str, list[dict], dict]:
    emit_status("searching", "Buscando fallas similares (híbrido + rerank)...")

    if is_cliente(self.chat.rol_nombre):
      vehiculos = self.chat._get_cliente_vehiculos()
      if not vehiculos:
        text = "Aún no tienes vehículos registrados. Regístralos en la pestaña Vehículos."
        return self._stream(text, emit_token), [], {}

    rag_result = self.chat.tools.execute(
      "buscar_fallas_similares",
      {"descripcion": question, "limite": 3},
    )

    if is_cliente(self.chat.rol_nombre):
      rag_result = self.chat._filter_rag_for_cliente(rag_result)
    elif is_mecanico(self.chat.rol_nombre):
      rag_result = self.chat._filter_rag_for_mecanico(rag_result)

    emit_status("thinking", "Analizando casos encontrados...")
    answer = self._answer_from_rag(question, rag_result, handoff, emit_token)
    tool_calls = [{
      "name": "buscar_fallas_similares",
      "arguments": {"descripcion": question, "limite": 3},
      "result": rag_result,
    }]
    return answer, tool_calls, rag_result

  def _answer_from_rag(
    self,
    question: str,
    rag_result: dict,
    handoff: dict[str, Any],
    emit_token: Callable[[str], None],
  ) -> str:
    matches = rag_result.get("matches", [])
    if not matches:
      if is_cliente(self.chat.rol_nombre):
        text = "No encontré fallas similares en el historial de tus vehículos registrados."
      elif is_mecanico(self.chat.rol_nombre):
        text = "No encontré fallas similares en tu historial de esta sucursal."
      else:
        text = "No encontré fallas históricas similares en la base vectorial."
      return self._stream(text, emit_token)

    context = "\n".join(
      f"- Cita {m.get('id_cita') or 'N/A'} | Placa {m.get('placa')} | "
      f"Score={m.get('rerank_score', m.get('rrf_score', m.get('distancia')))}: {m.get('texto')}"
      for m in matches
    )
    memoria = handoff.get("summary") or self.chat._memory_from_other_conversations()
    scope_rule = ""
    if is_cliente(self.chat.rol_nombre):
      scope_rule = "Responde solo sobre los vehículos del cliente logueado."
    elif is_mecanico(self.chat.rol_nombre):
      scope_rule = "Responde SOLO con el historial propio del mecánico en la sucursal activa."

    prompt = f"""Eres el especialista RAG de IESPRO-Taller. Responde en texto plano en español.
{scope_rule}
NO uses markdown ni asteriscos.

Pregunta: {question}
Contexto de conversación previa:
{memoria}

Fallas similares (Top-3 tras reranking):
{context}

Explica si la falla es parecida a casos anteriores y qué conviene revisar. Sé breve."""

    parts: list[str] = []
    stream = ollama.generate(model=OLLAMA_CHAT_MODEL, prompt=prompt, stream=True)
    for chunk in stream:
      token = chunk.get("response", "")
      if token:
        parts.append(token)
        emit_token(token)
    return plain_chat_text("".join(parts))

  @staticmethod
  def _stream(text: str, emit_token: Callable[[str], None]) -> str:
    for word in text.split(" "):
      emit_token(word + " ")
    return text
