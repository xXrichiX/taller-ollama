"""Agente especialista transaccional: function calling sobre servicios internos (sin SQL)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import ollama

from config import MAX_TOOL_CALLS_PER_TURN, OLLAMA_CHAT_MODEL
from services.chat_intents import allows_mutating_tool, get_friendly_fallback_answer, is_gibberish_input
from services.text_format import plain_chat_text
from services.tool_resilience import (
  call_signature,
  should_skip_followup_llm,
  tool_failure_user_message,
  tool_message_content,
)
from services.tool_response_format import format_tool_calls_log
from services.tools_service import ToolsService
from services.tool_policy import tools_for_session
from services.user_roles import is_cliente, is_mecanico, is_staff_manager, is_workshop_staff

logger = logging.getLogger(__name__)

PLAIN_TEXT_RULE = """
FORMATO: texto plano en español, sin markdown ni asteriscos.
"""

SUCURSAL_TOOLS = frozenset({
  "listar_citas", "listar_islas", "contar_citas", "listar_mecanicos",
  "crear_cita_natural", "cambiar_estado_cita_natural",
  "cancelar_cita_natural", "editar_cita_natural",
})

ISLA_TOOLS = frozenset({
  "listar_inventario",
  "contar_inventario",
})

TX_SYSTEM = """Eres el agente transaccional del taller.
Tu único trabajo es consultar o modificar datos del taller mediante las tools disponibles (function calling).
- NUNCA ejecutes SQL ni pidas acceso directo a la base de datos: solo las tools del catálogo.
- Usa function calling para listar, crear, editar o cancelar citas, clientes, vehículos, servicios e inventario.
- Para conteos exactos usa contar_inventario, contar_citas o las tools de listado.
- No inventes datos. No pidas IDs numéricos al usuario.
- Si el mensaje no tiene sentido o no entiendes qué pide, di que no entendiste y pide que lo reformule. NUNCA inventes citas, placas ni diagnósticos.
- Si piden crear algo y faltan datos, NO llames la tool: pregunta qué falta.
- Tras un registro exitoso, ofrece ayudar con el siguiente paso (ej. vehículo después de cliente).
- Preséntate como "tu asistente", sin marcas. "Orden" y "cita" son lo mismo; di siempre cita.
- Responde en español, breve y profesional.
- No compartas correos, teléfonos ni datos personales masivos; resume con nombres y totales.
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

    if is_gibberish_input(question):
      return self._stream(get_friendly_fallback_answer(self.chat.rol_nombre), emit_token), [], "help"

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
    tool_defs = tools_for_session(
      es_cliente=is_cliente(self.chat.rol_nombre),
      es_mecanico=is_mecanico(self.chat.rol_nombre) and not self.chat.es_propietario,
      es_propietario=bool(self.chat.es_propietario),
    )
    try:
      response = ollama.chat(
        model=OLLAMA_CHAT_MODEL,
        messages=messages,
        tools=tool_defs,
      )
    except Exception as exc:
      answer = f"Error con Ollama: {exc}"
      return self._stream(answer, emit_token), [], "error"

    msg = response.get("message", {})
    tool_calls = msg.get("tool_calls") or []

    if not tool_calls:
      content = plain_chat_text(msg.get("content", "No pude procesar la solicitud."))
      return self._stream(content, emit_token), [], "llm_direct"

    if len(tool_calls) > MAX_TOOL_CALLS_PER_TURN:
      logger.warning(
        "Truncando tool_calls de %d a %d",
        len(tool_calls),
        MAX_TOOL_CALLS_PER_TURN,
      )
      tool_calls = tool_calls[:MAX_TOOL_CALLS_PER_TURN]

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

      if "id_isla" not in args and name in ISLA_TOOLS and self.chat.id_isla:
        args["id_isla"] = self.chat.id_isla

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
