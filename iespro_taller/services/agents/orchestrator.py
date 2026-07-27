"""Orquestador multi-agente: rutea y transfiere contexto entre especialistas."""

from __future__ import annotations

from typing import Any, Callable

from services.agents.rag_agent import RagAgent
from services.agents.router_agent import RouteIntent, RouterAgent
from services.agents.transactional_agent import TransactionalAgent
from services.chat_intents import get_friendly_fallback_answer
from services.guardrails import BLOCKED_MESSAGE


class MultiAgentOrchestrator:
  def __init__(self, chat_service: Any):
    self.chat = chat_service
    self.router = RouterAgent()
    self.rag_agent = RagAgent(chat_service)
    self.tx_agent = TransactionalAgent(chat_service)

  def route_and_run(
    self,
    question: str,
    *,
    emit_status: Callable[[str, str], None],
    emit_token: Callable[[str], None],
    finalize: Callable[..., dict[str, Any]],
  ) -> dict[str, Any] | None:
    """Devuelve None si el flujo debe continuar con atajos legacy (cancelar cita, etc.)."""
    history = self.chat._ollama_context(question)
    intent = self.router.classify(
      question,
      history=history,
      rol_nombre=self.chat.rol_nombre,
    )

    if intent == RouteIntent.BLOCKED:
      answer = self._stream(BLOCKED_MESSAGE, emit_token)
      return finalize(answer, "blocked", was_blocked=True)

    handoff = self.router.build_handoff_context(
      history,
      routed_to=intent,
      question=question,
    )

    route_label = f"agent_{intent.value}"

    if intent == RouteIntent.RAG:
      answer, tool_calls, _meta = self.rag_agent.run(
        question,
        handoff=handoff,
        emit_status=emit_status,
        emit_token=emit_token,
      )
      return finalize(answer, route_label, tool_calls=tool_calls)

    if intent == RouteIntent.TRANSACTIONAL:
      answer, tool_calls, sub_route = self.tx_agent.run(
        question,
        handoff=handoff,
        emit_status=emit_status,
        emit_token=emit_token,
      )
      final_route = route_label if sub_route in ("function_calling", "llm_direct") else sub_route
      return finalize(answer, final_route, tool_calls=tool_calls)

    if intent == RouteIntent.HELP:
      fallback = get_friendly_fallback_answer(self.chat.rol_nombre)
      answer = self._stream(fallback, emit_token)
      return finalize(answer, "help")

    return None

  @staticmethod
  def _stream(text: str, emit_token: Callable[[str], None]) -> str:
    for word in text.split(" "):
      emit_token(word + " ")
    return text
