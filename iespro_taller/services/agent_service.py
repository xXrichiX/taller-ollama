"""Agente solo con Function Calling — sin atajos SQL/RAG (para demo Actividad 3)."""

import json
from typing import Any

import ollama

from config import DEFAULT_SUCURSAL_ID, OLLAMA_CHAT_MODEL
from services.chat_intents import (
    CAPABILITIES_ANSWER,
    INVALID_INPUT_ANSWER,
    is_capabilities_question,
    is_invalid_input,
    normalize_workshop_question,
)
from services.text_format import plain_chat_text
from services.tools_service import TOOL_DEFINITIONS, ToolsService

MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """Eres el agente de IESPRO-Taller (citas automotrices).

REGLAS:
- SIEMPRE usa las tools para consultar o modificar datos reales. No inventes datos.
- NUNCA pidas IDs numéricos al usuario (cliente, vehículo, mecánico, isla).
- Para crear citas usa crear_cita_natural con nombre_cliente, placa, nombre_mecanico, isla y descripcion_fallo.
- Para editar citas usa editar_cita_natural con placa y los campos a cambiar.
- Para cancelar usa cancelar_cita_natural. Si el usuario dice eliminar, borrar o quitar una cita, cancélala (estado CANCELADA).
- Para cambiar estado usa cambiar_estado_cita_natural con placa o id_cita.
- Si falta un dato, pregunta en lenguaje natural (nombre, placa, isla), no en IDs.
- Responde en español, breve y profesional. NUNCA respondas con JSON ni listas de funciones técnicas.
- Texto plano solamente: sin asteriscos (**), sin markdown, sin encabezados #.

Ejemplo de creación:
"Crea cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido en frenos"
→ llamar crear_cita_natural con esos campos.

Sucursal activa por defecto: {sucursal}.
"""

SUCURSAL_TOOLS = frozenset({
    "listar_citas", "listar_islas", "contar_citas", "listar_mecanicos",
    "crear_cita_natural", "cambiar_estado_cita_natural",
    "cancelar_cita_natural", "editar_cita_natural",
})


def _looks_like_fake_json(text: str) -> bool:
    stripped = (text or "").strip()
    return bool(stripped.startswith("{") or stripped.startswith("["))


class AgentService:
    def __init__(self, id_sucursal: int = DEFAULT_SUCURSAL_ID):
        self.id_sucursal = id_sucursal
        self.tools = ToolsService(rag_service=None)
        self.history: list[dict] = []

    def _inject_sucursal(self, name: str, args: dict) -> dict:
        if "id_sucursal" not in args and name in SUCURSAL_TOOLS:
            args["id_sucursal"] = self.id_sucursal
        return args

    def ask(self, question: str) -> dict[str, Any]:
        question = normalize_workshop_question((question or "").strip())
        if not question or is_invalid_input(question):
            return {"answer": INVALID_INPUT_ANSWER, "tool_calls": [], "route": "help"}

        if is_capabilities_question(question):
            return {"answer": CAPABILITIES_ANSWER, "tool_calls": [], "route": "help"}

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(sucursal=self.id_sucursal)},
            *self.history[-8:],
            {"role": "user", "content": question},
        ]

        tool_calls_log: list[dict] = []
        answer = ""
        route = "llm_direct"

        try:
            for _ in range(MAX_TOOL_ROUNDS):
                response = ollama.chat(
                    model=OLLAMA_CHAT_MODEL,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                )
                msg = response.get("message", {})
                tool_calls = msg.get("tool_calls") or []

                if not tool_calls:
                    answer = plain_chat_text(msg.get("content", "No pude procesar la solicitud."))
                    break

                route = "function_calling"
                messages.append(msg)

                for call in tool_calls:
                    fn = call.get("function", {})
                    name = fn.get("name")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        args = json.loads(args) if args else {}

                    args = self._inject_sucursal(name, args)
                    result = self.tools.execute(name, args)
                    tool_calls_log.append({"name": name, "arguments": args, "result": result})

                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })
            else:
                final = ollama.chat(
                    model=OLLAMA_CHAT_MODEL,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                )
                answer = plain_chat_text(final["message"]["content"])
                route = "function_calling"

        except Exception as exc:
            return {
                "answer": f"Error Ollama: {exc}",
                "tool_calls": [],
                "route": "error",
            }

        if route == "llm_direct" and _looks_like_fake_json(answer):
            answer = CAPABILITIES_ANSWER

        answer = plain_chat_text(answer)

        self.history.append({"role": "user", "content": question})
        self.history.append({"role": "assistant", "content": answer})

        return {"answer": answer, "tool_calls": tool_calls_log, "route": route}
