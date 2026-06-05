import json
from typing import Any

import ollama

from config import DEFAULT_SUCURSAL_ID, OLLAMA_CHAT_MODEL
from services.chat_intents import (
    CAPABILITIES_ANSWER,
    INVALID_INPUT_ANSWER,
    is_capabilities_question,
    is_invalid_input,
)
from services.rag_service import RagService
from services.text_format import plain_chat_text
from services.tools_service import TOOL_DEFINITIONS, ToolsService, run_sql_query

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
        self.rag = RagService()
        self.tools = ToolsService(self.rag)
        self.history: list[dict] = []

    def bootstrap(self) -> tuple[bool, str]:
        try:
            added = self.rag.sync_fallas_from_db()
            return True, f"RAG sincronizado ({added} fallas nuevas indexadas)."
        except Exception as exc:
            return False, str(exc)

    def ask(self, question: str) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            return {
                "answer": INVALID_INPUT_ANSWER,
                "route": "help",
                "tool_calls": [],
                "raw": None,
            }

        if is_invalid_input(question):
            return {
                "answer": INVALID_INPUT_ANSWER,
                "route": "help",
                "tool_calls": [],
                "raw": None,
            }

        if is_capabilities_question(question):
            return {
                "answer": CAPABILITIES_ANSWER,
                "route": "help",
                "tool_calls": [],
                "raw": None,
            }

        sql_answer = run_sql_query(question, self.id_sucursal)
        if sql_answer:
            return {
                "answer": sql_answer,
                "route": "sql",
                "tool_calls": [],
                "raw": None,
            }

        q_lower = question.lower()
        rag_keywords = ("similar", "parecido", "parecida", "falla", "síntoma", "sintoma", "chirrido", "ruido", "vibración", "vibracion", "como el", "como la")
        if any(k in q_lower for k in rag_keywords):
            rag_result = self.tools.execute("buscar_fallas_similares", {"descripcion": question, "limite": 5})
            answer = self._answer_from_rag(question, rag_result)
            return {
                "answer": answer,
                "route": "rag",
                "tool_calls": [{"name": "buscar_fallas_similares", "result": rag_result}],
                "raw": None,
            }

        return self._ask_with_tools(question)
    def _answer_from_rag(self, question: str, rag_result: dict) -> str:
        matches = rag_result.get("matches", [])
        if not matches:
            return "No encontré fallas históricas similares en la base vectorial."

        context = "\n".join(
            f"- Cita {m.get('id_cita') or 'N/A'} | Placa {m.get('placa')} | Similitud(dist)={m.get('distancia')}: {m.get('texto')}"
            for m in matches
        )

        prompt = f"""Eres el asistente del taller IESPRO. Responde SOLO en texto plano en español.
NO uses asteriscos, markdown ni encabezados con #.

Pregunta: {question}

Fallas similares encontradas en el historial:
{context}

Explica si la falla es parecida a casos anteriores (menciona placa y cita si aplica) y qué conviene revisar.
No digas la palabra RAG ni inventes siglas. Sé breve y claro."""

        response = ollama.generate(model=OLLAMA_CHAT_MODEL, prompt=prompt)
        return plain_chat_text(response["response"])

    def _ask_with_tools(self, question: str) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + f"\nSucursal activa: {self.id_sucursal}"},
            *self.history[-6:],
            {"role": "user", "content": question},
        ]

        tool_calls_log = []

        try:
            response = ollama.chat(
                model=OLLAMA_CHAT_MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
            )
        except Exception as exc:
            return {
                "answer": f"Error con Ollama ({OLLAMA_CHAT_MODEL}): {exc}",
                "route": "error",
                "tool_calls": [],
                "raw": None,
            }

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

                if "id_sucursal" not in args and name in ("listar_citas", "listar_islas", "contar_citas"):
                    args["id_sucursal"] = self.id_sucursal

                result = self.tools.execute(name, args)
                tool_calls_log.append({"name": name, "arguments": args, "result": result})

                messages.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

            final = ollama.chat(
                model=OLLAMA_CHAT_MODEL,
                messages=messages + [{"role": "system", "content": PLAIN_TEXT_RULE}],
            )
            answer = plain_chat_text(final["message"]["content"])
            raw = final
            route = "function_calling"
        else:
            answer = plain_chat_text(msg.get("content", "No pude generar respuesta."))
            raw = response
            route = "llm_direct"

        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})

        return {
            "answer": answer,
            "route": route,
            "tool_calls": tool_calls_log,
            "raw": raw,
        }
