"""Agente especialista transaccional: function calling y consultas SQL."""

from __future__ import annotations

import json
from typing import Any, Callable

import ollama

from config import OLLAMA_CHAT_MODEL
from services.chat_intents import allows_mutating_tool
from services.text_format import plain_chat_text
from services.tool_resilience import (
  call_signature,
  should_skip_followup_llm,
  tool_failure_user_message,
  tool_message_content,
)
from services.tool_response_format import format_tool_calls_log
from services.tools_service import TOOL_DEFINITIONS, run_sql_query
from services.user_roles import is_cliente, is_mecanico, is_staff_manager, is_workshop_staff

PLAIN_TEXT_RULE = """
FORMATO: texto plano en español, sin markdown ni asteriscos.
"""

SUCURSAL_TOOLS = frozenset({
  "listar_citas", "listar_islas", "contar_citas", "listar_mecanicos",
  "crear_cita_natural", "cambiar_estado_cita_natural",
  "cancelar_cita_natural", "editar_cita_natural",
})

TX_SYSTEM = """Eres el agente transaccional de IESPRO-Taller.
Tu único trabajo es consultar o modificar la base de datos del taller mediante tools.
- Usa function calling para listar, crear, editar o cancelar citas.
- Para conteos exactos puedes usar SQL implícito vía tools.
- No inventes datos. No pidas IDs numéricos al usuario.
- Responde en español, breve y profesional.
"""


class TransactionalAgent:
  def __init__(self, chat_service: Any):
    self.chat = chat_service

  def run(
    self,
    question: str,
    *,
    handoff: dict[str, Any],
    emit_status: Callable[[str, str], None],
    emit_token: Callable[[str], None],
  ) -> tuple[str, list[dict], str]:
    emit_status("searching", "Consultando base de datos...")

    if not is_cliente(self.chat.rol_nombre) and not is_mecanico(self.chat.rol_nombre):
      sql_answer = run_sql_query(question, self.chat.id_sucursal)
      if sql_answer:
        emit_status("thinking", "Preparando respuesta...")
        return self._stream(sql_answer, emit_token), [], "sql"

    return self._with_tools(question, handoff, emit_status, emit_token)

  def _with_tools(
    self,
    question: str,
    handoff: dict[str, Any],
    emit_status: Callable[[str, str], None],
    emit_token: Callable[[str], None],
  ) -> tuple[str, list[dict], str]:
    history = handoff.get("history") or []
    messages = [
      {"role": "system", "content": TX_SYSTEM + "\n" + self.chat._build_system_prompt()},
      *[{"role": m["role"], "content": m.get("content") or m.get("contenido", "")} for m in history],
      {"role": "user", "content": question},
    ]

    tool_calls_log: list[dict] = []
    seen_signatures: set[str] = set()

    emit_status("thinking", "Pensando...")
    try:
      response = ollama.chat(
        model=OLLAMA_CHAT_MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
      )
    except Exception as exc:
      answer = f"Error con Ollama: {exc}"
      return self._stream(answer, emit_token), [], "error"

    msg = response.get("message", {})
    tool_calls = msg.get("tool_calls") or []

    if not tool_calls:
      content = plain_chat_text(msg.get("content", "No pude procesar la solicitud."))
      return self._stream(content, emit_token), [], "llm_direct"

    messages.append(msg)
    for call in tool_calls:
      fn = call.get("function", {})
      name = fn.get("name") or "acción"
      args = fn.get("arguments", {})
      if isinstance(args, str):
        args = json.loads(args) if args else {}

      emit_status("acting", self.chat._tool_status_label(name))

      if "id_sucursal" not in args and name in SUCURSAL_TOOLS:
        args["id_sucursal"] = self.chat.id_sucursal

      sig = call_signature(name, args)
      if sig in seen_signatures:
        result = {"ok": False, "error": "Llamada duplicada omitida.", "recoverable": True}
      else:
        seen_signatures.add(sig)
        if not allows_mutating_tool(
          question,
          name,
          staff_manage=is_staff_manager(self.chat.rol_nombre)
          or (
            is_workshop_staff(self.chat.rol_nombre)
            and name in ("cambiar_estado_cita_natural", "cambiar_estado_cita", "editar_cita_natural")
          ),
        ):
          result = {
            "ok": False,
            "error": "Necesito instrucciones claras para crear o cambiar citas.",
            "recoverable": True,
          }
        else:
          result = self.chat.tools.execute(name, args)

      tool_calls_log.append({"name": name, "arguments": args, "result": result})
      messages.append({"role": "tool", "content": tool_message_content(name or "tool", result)})

    if should_skip_followup_llm(tool_calls_log):
      answer = tool_failure_user_message(tool_calls_log)
      return self._stream(answer, emit_token), tool_calls_log, "function_calling"

    formatted = format_tool_calls_log(tool_calls_log)
    if formatted:
      return self._stream(formatted, emit_token), tool_calls_log, "function_calling"

    emit_status("thinking", "Redactando respuesta final...")
    try:
      parts: list[str] = []
      stream = ollama.chat(
        model=OLLAMA_CHAT_MODEL,
        messages=messages + [{"role": "system", "content": PLAIN_TEXT_RULE}],
        stream=True,
      )
      for chunk in stream:
        token = chunk.get("message", {}).get("content", "")
        if token:
          parts.append(token)
          emit_token(token)
      answer = plain_chat_text("".join(parts)) or formatted
    except Exception:
      answer = tool_failure_user_message(tool_calls_log) or formatted
    return answer, tool_calls_log, "function_calling"

  @staticmethod
  def _stream(text: str, emit_token: Callable[[str], None]) -> str:
    for word in text.split(" "):
      emit_token(word + " ")
    return text
