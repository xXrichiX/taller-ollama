import json
import logging
from typing import Any

import ollama

from config import (
    DEFAULT_SUCURSAL_ID,
    OLLAMA_CHAT_MODEL,
    OLLAMA_CONTEXT_MAX_TOKENS,
    OLLAMA_CONTEXT_MESSAGE_CAP,
    OLLAMA_CONTEXT_RESERVED_TOKENS,
)
from services.context_window import estimate_tokens, trim_messages_for_context
from services.tool_resilience import (
    call_signature,
    should_skip_followup_llm,
    tool_failure_user_message,
    tool_message_content,
)
from db.conversation_repository import ConversationRepository
from services.chat_intents import (
    CAPABILITIES_ANSWER,
    INVALID_INPUT_ANSWER,
    is_capabilities_question,
    is_invalid_input,
    is_memory_recall_question,
)
from services.rag_service import RagService
from services.text_format import plain_chat_text
from services.tool_response_format import format_tool_calls_log
from services.tools_service import TOOL_DEFINITIONS, ToolsService, run_sql_query

SUCURSAL_TOOLS = frozenset({
    "listar_citas", "listar_islas", "contar_citas", "listar_mecanicos",
    "crear_cita_natural", "cambiar_estado_cita_natural",
})

logger = logging.getLogger(__name__)

PLAIN_TEXT_RULE = """
FORMATO DE RESPUESTA (obligatorio):
- Texto plano en español, como un mensaje de WhatsApp profesional.
- NO uses markdown: sin asteriscos (**), sin numerales (#), sin bloques ```.
- Para listas usa guiones simples (-) o frases cortas separadas por líneas.
- No menciones "RAG", "tools" ni nombres técnicos al usuario final.
"""

SYSTEM_PROMPT = """
Eres el asistente IA de IESPRO-Taller (sistema de citas automotrices).

Decide cómo responder:
- Preguntas de conteo o datos estructurados (cuántas citas, clientes, vehículos, mecánicos en isla) → usa tools o SQL.
- Comparar fallas, buscar casos parecidos, contexto de síntomas → usa buscar_fallas_similares (RAG).
- Acciones (cambiar estado de cita, consultar islas, listar citas) → usa function calling.

Reglas:
1. Responde en español, claro y profesional.
2. Si comparas fallas, menciona placa, id de cita y qué tan parecido es el caso.
3. No inventes datos: usa solo resultados de tools/SQL/RAG.
4. Si no hay datos, dilo explícitamente.
""" + PLAIN_TEXT_RULE


class ChatService:
    def __init__(self, id_sucursal: int = DEFAULT_SUCURSAL_ID):
        self.id_sucursal = id_sucursal
        self.id_usuario: int | None = None
        self.id_conversacion: int | None = None
        self.rag = RagService()
        self.tools = ToolsService(self.rag)
        self.repo = ConversationRepository()
        self._last_context_meta: dict[str, Any] = {}

    def set_user(self, id_usuario: int) -> None:
        self.id_usuario = id_usuario

    def ensure_conversation(self) -> int | None:
        if not self.id_usuario:
            return None

        if self.id_conversacion:
            return self.id_conversacion

        reciente = self.repo.obtener_conversacion_reciente(self.id_usuario, self.id_sucursal)
        if reciente:
            self.id_conversacion = reciente["id"]
            return self.id_conversacion

        self.id_conversacion = self.repo.crear_conversacion(
            self.id_usuario,
            self.id_sucursal,
            titulo="Asistente del taller",
        )
        return self.id_conversacion

    def start_new_conversation(self) -> int | None:
        if not self.id_usuario:
            return None

        self.id_conversacion = self.repo.crear_conversacion(
            self.id_usuario,
            self.id_sucursal,
            titulo="Nueva conversación",
        )
        return self.id_conversacion

    def get_ui_messages(self) -> list[dict]:
        if not self.id_conversacion:
            return []
        return self.repo.obtener_mensajes(self.id_conversacion)

    def list_conversations(self) -> list[dict]:
        if not self.id_usuario:
            return []
        return self.repo.listar_conversaciones(self.id_usuario, self.id_sucursal)

    def switch_conversation(self, id_conversacion: int) -> bool:
        if not self.id_usuario:
            return False
        convs = {c["id"] for c in self.list_conversations()}
        if id_conversacion not in convs:
            return False
        self.id_conversacion = id_conversacion
        return True

    def bootstrap(self) -> tuple[bool, str]:
        try:
            added = self.rag.sync_fallas_from_db()
            return True, f"RAG sincronizado ({added} fallas nuevas indexadas)."
        except Exception as exc:
            return False, str(exc)

    def _ollama_context(self, question: str = "") -> list[dict[str, str]]:
        if not self.id_conversacion:
            return []

        raw = self.repo.obtener_mensajes_para_ollama(
            self.id_conversacion,
            limite=OLLAMA_CONTEXT_MESSAGE_CAP,
        )
        reserved = (
            OLLAMA_CONTEXT_RESERVED_TOKENS
            + estimate_tokens(self._build_system_prompt())
            + estimate_tokens(question)
        )
        trimmed, meta = trim_messages_for_context(
            raw,
            max_tokens=OLLAMA_CONTEXT_MAX_TOKENS,
            reserved_tokens=reserved,
        )
        self._last_context_meta = meta
        if meta.get("dropped_messages", 0) > 0:
            logger.info(
                "Contexto recortado: %s mensajes descartados, %s tokens usados, resumen=%s",
                meta["dropped_messages"],
                meta.get("used_tokens"),
                meta.get("summarized"),
            )
        return trimmed

    def _memory_from_other_conversations(self) -> str:
        if not self.id_usuario or not self.id_conversacion:
            return ""

        rows = self.repo.obtener_memoria_otras_conversaciones(
            self.id_usuario,
            self.id_sucursal,
            self.id_conversacion,
            limite_mensajes=10,
        )
        if not rows:
            return ""

        lines: list[str] = []
        for row in reversed(rows):
            titulo = (row.get("titulo") or "Conversación").strip()[:40]
            role = "Usuario" if row["role"] == "user" else "Asistente"
            texto = (row.get("contenido") or "").strip().replace("\n", " ")[:200]
            if texto:
                lines.append(f"- [{titulo}] {role}: {texto}")

        if not lines:
            return ""

        return (
            "\n\nMemoria de otras conversaciones de este mismo usuario "
            "(úsala si pregunta algo de antes, de otra charla o 'lo que te dije'):\n"
            + "\n".join(lines)
        )

    def _build_system_prompt(self) -> str:
        return (
            SYSTEM_PROMPT
            + f"\nSucursal activa: {self.id_sucursal}"
            + self._memory_from_other_conversations()
        )

    def _maybe_set_titulo(self, question: str) -> None:
        if not self.id_conversacion:
            return

        from db.connection import fetch_one

        conv = fetch_one(
            "SELECT titulo FROM conversaciones WHERE id = %s",
            (self.id_conversacion,),
        )
        if not conv:
            return

        titulo = (conv.get("titulo") or "").strip()
        if titulo in ("Asistente del taller", "Nueva conversación", ""):
            limpio = question.strip().replace("\n", " ")
            self.repo.actualizar_titulo(self.id_conversacion, limpio[:60] or "Conversación")

    def _persist_exchange(self, question: str, answer: str, route: str) -> None:
        if not self.id_conversacion:
            return

        self.repo.guardar_mensaje(self.id_conversacion, "user", question)
        self.repo.guardar_mensaje(self.id_conversacion, "assistant", answer, route=route)
        self._maybe_set_titulo(question)

    def _result(
        self,
        question: str,
        answer: str,
        route: str,
        *,
        tool_calls: list | None = None,
        raw: Any = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        answer = plain_chat_text(answer or "")
        if persist and question:
            self._persist_exchange(question, answer, route)
        return {
            "answer": answer,
            "route": route,
            "tool_calls": tool_calls or [],
            "raw": raw,
        }

    def ask(self, question: str) -> dict[str, Any]:
        question = (question or "").strip()
        self.ensure_conversation()

        if not question:
            return self._result(
                "",
                INVALID_INPUT_ANSWER,
                "help",
                persist=False,
            )

        if is_invalid_input(question):
            return self._result(question, INVALID_INPUT_ANSWER, "help")

        if is_capabilities_question(question):
            return self._result(question, CAPABILITIES_ANSWER, "help")

        if is_memory_recall_question(question):
            return self._answer_from_memory(question)

        sql_answer = run_sql_query(question, self.id_sucursal)
        if sql_answer:
            return self._result(question, sql_answer, "sql")

        q_lower = question.lower()
        rag_keywords = (
            "similar", "parecido", "parecida", "falla", "síntoma", "sintoma",
            "chirrido", "ruido", "vibración", "vibracion", "como el", "como la",
        )
        if any(k in q_lower for k in rag_keywords):
            rag_result = self.tools.execute(
                "buscar_fallas_similares",
                {"descripcion": question, "limite": 5},
            )
            answer = self._answer_from_rag(question, rag_result)
            return self._result(
                question,
                answer,
                "rag",
                tool_calls=[{"name": "buscar_fallas_similares", "result": rag_result}],
            )

        return self._ask_with_tools(question)

    def _format_recall_answer(self, question: str) -> str:
        if not self.id_usuario or not self.id_conversacion:
            return "No hay sesión activa para consultar el historial."

        otras = self.repo.listar_otras_conversaciones_con_mensajes(
            self.id_usuario,
            self.id_sucursal,
            self.id_conversacion,
        )
        actual = self._ollama_context()

        partes: list[str] = []

        if otras:
            partes.append("Sí, revisé tus conversaciones anteriores guardadas:")
            for conv in otras:
                titulo = (conv.get("titulo") or "Conversación").strip()[:60]
                partes.append(f"\nConversación «{titulo}»:")
                for msg in conv["mensajes"]:
                    quien = "Tú" if msg["role"] == "user" else "Asistente"
                    texto = plain_chat_text((msg.get("contenido") or "").strip())
                    if len(texto) > 320:
                        texto = texto[:317] + "..."
                    if texto:
                        partes.append(f"- {quien}: {texto}")

        if actual:
            previos = actual[:-1] if len(actual) > 1 else []
            if previos:
                partes.append("\nEn esta conversación, antes de tu última pregunta:")
                for msg in previos[-6:]:
                    quien = "Tú" if msg["role"] == "user" else "Asistente"
                    texto = plain_chat_text((msg.get("content") or "").strip())
                    if len(texto) > 320:
                        texto = texto[:317] + "..."
                    if texto:
                        partes.append(f"- {quien}: {texto}")

        if not partes:
            return (
                "Aún no tengo mensajes guardados en otras conversaciones contigo. "
                "Cuando charlemos, quedarán guardados y podré recordarlos después."
            )

        partes.append(
            "\nEsto es lo que tengo registrado en la base de datos del taller. "
            "Si quieres retomar algo, dime el tema y seguimos desde ahí."
        )
        return "\n".join(partes)

    def _answer_from_memory(self, question: str) -> dict[str, Any]:
        answer = self._format_recall_answer(question)
        return self._result(question, answer, "memory_recall")

    def _answer_from_rag(self, question: str, rag_result: dict) -> str:
        matches = rag_result.get("matches", [])
        if not matches:
            return "No encontré fallas históricas similares en la base vectorial."

        context = "\n".join(
            f"- Cita {m.get('id_cita') or 'N/A'} | Placa {m.get('placa')} | Similitud(dist)={m.get('distancia')}: {m.get('texto')}"
            for m in matches
        )

        memoria = self._memory_from_other_conversations()

        prompt = f"""Eres el asistente del taller IESPRO. Responde SOLO en texto plano en español.
NO uses asteriscos, markdown ni encabezados con #.

Pregunta: {question}
{memoria}

Fallas similares encontradas en el historial:
{context}

Explica si la falla es parecida a casos anteriores (menciona placa y cita si aplica) y qué conviene revisar.
Si la pregunta alude a algo de una conversación anterior del usuario, usa la memoria de arriba.
No digas la palabra RAG ni inventes siglas. Sé breve y claro."""

        response = ollama.generate(model=OLLAMA_CHAT_MODEL, prompt=prompt)
        return plain_chat_text(response["response"])

    def _ask_with_tools(self, question: str) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            *self._ollama_context(question),
            {"role": "user", "content": question},
        ]

        tool_calls_log = []
        seen_signatures: set[str] = set()

        try:
            response = ollama.chat(
                model=OLLAMA_CHAT_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )
        except Exception as exc:
            logger.exception("Error en ollama.chat")
            return self._result(
                question,
                f"Error con Ollama ({OLLAMA_CHAT_MODEL}): {exc}",
                "error",
            )

        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls") or []

        if tool_calls:
            messages.append(msg)
            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name")
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    args = json.loads(args) if args else {}

                if "id_sucursal" not in args and name in SUCURSAL_TOOLS:
                    args["id_sucursal"] = self.id_sucursal

                sig = call_signature(name, args)
                if sig in seen_signatures:
                    result = {
                        "ok": False,
                        "error": "Llamada duplicada omitida en este turno.",
                        "recoverable": True,
                    }
                else:
                    seen_signatures.add(sig)
                    result = self.tools.execute(name, args)

                tool_calls_log.append({"name": name, "arguments": args, "result": result})
                messages.append({
                    "role": "tool",
                    "content": tool_message_content(name or "tool", result),
                })

            if should_skip_followup_llm(tool_calls_log):
                answer = tool_failure_user_message(tool_calls_log)
                raw = None
            else:
                formatted = format_tool_calls_log(tool_calls_log)
                if formatted:
                    answer = formatted
                    raw = None
                else:
                    try:
                        final = ollama.chat(
                            model=OLLAMA_CHAT_MODEL,
                            messages=messages + [{"role": "system", "content": PLAIN_TEXT_RULE}],
                        )
                        answer = plain_chat_text(final["message"]["content"]) or formatted
                        raw = final
                    except Exception as exc:
                        logger.exception("Error en segunda llamada ollama.chat")
                        answer = tool_failure_user_message(tool_calls_log) or str(exc)
                        raw = None
            route = "function_calling"
        else:
            answer = plain_chat_text(msg.get("content", "No pude generar respuesta."))
            raw = response
            route = "llm_direct"

        return self._result(
            question,
            answer,
            route,
            tool_calls=tool_calls_log,
            raw=raw,
        )
