import json
import logging
import time
from typing import Any, Callable

import ollama

from config import (
    DEFAULT_SUCURSAL_ID,
    IS_PRODUCTION,
    MAX_TOOL_CALLS_PER_TURN,
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
from db.observability_repository import ObservabilityRepository
from services.guardrails import BLOCKED_MESSAGE, sanitize_llm_context, validate_user_prompt
from services.audit_service import audit
from services import audit_actions
from services.chat_intents import (
    ACKNOWLEDGMENT_ANSWER,
    CLIENTE_SIN_VEHICULOS_ANSWER,
    INVALID_INPUT_ANSWER,
    allows_mutating_tool,
    extract_placa_from_text,
    get_capabilities_answer,
    get_casual_chat_answer,
    get_friendly_fallback_answer,
    get_guided_create_cita_answer,
    get_guided_create_entity_answer,
    get_greeting_answer,
    is_acknowledgment,
    is_capabilities_question,
    is_casual_chat,
    is_casual_nonsense,
    is_greeting,
    is_invalid_input,
    is_memory_recall_question,
    is_mi_cita_question,
    is_personal_vehicle_question,
    is_similarity_question,
    looks_like_workshop_request,
    norm_placa_token,
    normalize_workshop_question,
    parse_cancel_cita_request,
    STAFF_MI_AUTO_ANSWER,
)
from services.estado_labels import estado_a_etiqueta
from services.user_roles import (
    is_admin,
    is_cliente,
    is_mecanico,
    is_pending,
    is_staff_manager,
    is_workshop_staff,
)
from services.rag_service import RagService
from services.text_format import plain_chat_text
from services.tool_response_format import format_tool_calls_log, format_tool_result
from services.tools_service import ToolsService
from services.tool_policy import tools_for_session
from services.agents.orchestrator import MultiAgentOrchestrator
from services.llm_safety import enforce_llm_output

SUCURSAL_TOOLS = frozenset({
    "listar_citas", "listar_islas", "contar_citas", "listar_mecanicos",
    "crear_cita_natural", "crear_cliente_natural", "crear_vehiculo_natural",
    "crear_servicio_natural",
    "cambiar_estado_cita_natural",
    "cancelar_cita_natural", "editar_cita_natural",
})

ISLA_TOOLS = frozenset({
    "listar_inventario",
    "contar_inventario",
    "crear_inventario_natural",
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
Eres el asistente IA del taller (citas automotrices). Preséntate como "tu asistente", sin mencionar marcas ni productos.

Decide cómo responder:
- Preguntas de conteo o datos estructurados (cuántas citas, clientes, vehículos, inventario/stock, mecánicos en isla) → usa las tools del catálogo (nunca SQL directo).
- Comparar fallas, buscar casos parecidos, contexto de síntomas → usa buscar_fallas_similares (RAG).
- Acciones (crear, editar o cancelar citas, clientes, vehículos, servicios, inventario; cambiar estado; listar) → usa function calling.

Reglas:
1. Responde en español, claro y profesional.
2. Si comparas fallas, menciona placa, id de cita y qué tan parecido es el caso.
3. No inventes datos: usa solo resultados de tools internas o RAG.
4. Si no hay datos, dilo explícitamente.
5. "Eliminar", "borrar" o "quitar" una cita significa CANCELARLA (estado CANCELADA, inactiva). Nunca borres registros.
6. Para editar citas usa editar_cita_natural con placa y los campos a cambiar.
7. Para cancelar usa cancelar_cita_natural (también si el usuario dice eliminar o calear por error de voz).
8. Si el usuario dice "orden" u "órdenes", se refiere a CITAS. Usa siempre la palabra cita al responder.
9. Para CREAR algo (cliente, vehículo, servicio, inventario o cita): no llames la tool hasta tener los datos mínimos.
   Si faltan datos, pregunta en español claro, uno o dos campos por mensaje.
   Tras crear algo con éxito, pregunta brevemente si quiere hacer algo más.
10. Flujo típico: cliente → vehículo → cita. Puedes guiar ese orden si el usuario lo pide.
11. Si el usuario es dueño de taller o cliente, no pidas mecánico ni isla al agendar citas (se asignan solos).
""" + PLAIN_TEXT_RULE

STAFF_MANAGER_PROMPT = """
ROL ACTUAL: Administrador de sucursal o jefe de taller. Operas en nombre de cualquier cliente de tu sucursal.

Reglas para admin de sucursal:
- Puedes crear, editar y cancelar citas de cualquier placa o cliente de tu sucursal.
- Puedes asignar y reasignar mecánicos e islas.
- Puedes consultar inventario y stock bajo de la isla activa (cuántos artículos hay o listar piezas).
- Puedes crear clientes, vehículos, servicios del catálogo, artículos de inventario y citas por chat.
- Al crear, pide los datos que falten paso a paso y ofrece seguir con el siguiente paso del flujo.
- Para fallas similares, busca por placa, nombre de cliente o síntoma en todo el historial de la sucursal.
- No asumas "mi auto" ni vehículos del usuario logueado; el personal no tiene autos personales aquí.
"""

ADMIN_PROMPT = """
ROL ACTUAL: Administrador. Tienes visibilidad de todas las sucursales.

Reglas:
- Puedes consultar información de cualquier sucursal si el usuario lo pide.
- Gestiona sucursales, usuarios, códigos de invitación y asignaciones desde la aplicación.
"""
SUPER_ADMIN_PROMPT = ADMIN_PROMPT

MECANICO_PROMPT = """
ROL ACTUAL: Mecánico empleado. Solo ves TU historial en la sucursal activa.

Reglas para mecánico:
- Solo puedes consultar citas, vehículos, clientes y fallas ASIGNADAS A TI en la sucursal activa.
- No menciones ni inventes datos de otros mecánicos, ni de otras sucursales.
- Si no tienes historial propio para una falla, dilo claro: no uses casos ajenos.
- Solo puedes CAMBIAR estado, diagnóstico u observaciones de citas asignadas a ti.
"""

DUENO_TALLER_PROMPT = """
ROL ACTUAL: Dueño de tu taller personal. Eres el único mecánico.

Reglas:
- Ves y gestionas TODO tu taller: clientes, vehículos, citas e historial de fallas.
- Puedes crear, editar y cancelar citas de cualquier cliente de tu taller.
- No hay otros mecánicos ni sucursales: las citas se asignan automáticamente a ti.
- No pidas mecánico ni isla al agendar; el sistema los asigna solo.
- Al buscar fallas similares, usa todo el historial de tu taller.
- Puedes consultar inventario y stock de tu isla activa.
"""

CLIENTE_PROMPT = """
ROL ACTUAL: Cliente del taller. Solo puedes consultar y gestionar TUS vehículos y TUS citas.

Reglas para cliente:
- No listes ni modifiques datos de otros clientes, mecánicos, islas ni el taller completo.
- Si dice "mi auto" o "mi cita", usa solo sus vehículos registrados (por placa).
- Si no tiene vehículos registrados, dilo claro y pídele registrar en Mis Vehículos. No des ejemplos de otros clientes ni del taller completo.
- Si no tiene vehículos registrados, indícale que primero registre uno en la pestaña Vehículos.
- Puede solicitar cita con placa y falla; el taller asignará mecánico e isla.
- Puede cancelar sus citas activas indicando la placa de su vehículo.
"""


class ChatService:
    def __init__(self, id_sucursal: int = DEFAULT_SUCURSAL_ID):
        self._id_sucursal = id_sucursal
        self._id_isla: int | None = None
        self.id_usuario: int | None = None
        self.rol_nombre: str | None = None
        self.user_nombre: str | None = None
        self.id_cliente: int | None = None
        self.nombre_cliente: str | None = None
        self.id_mecanico_scope: int | None = None
        self.es_propietario: bool = False
        self.id_conversacion: int | None = None
        self._pending_new_conversation = False
        self.rag = RagService()
        self.tools = ToolsService(self.rag, id_sucursal=id_sucursal)
        self.repo = ConversationRepository()
        self.obs_repo = ObservabilityRepository()
        self._last_context_meta: dict[str, Any] = {}
        self.orchestrator = MultiAgentOrchestrator(self)
        try:
            self.obs_repo.ensure_table()
        except Exception:
            logger.exception("No se pudo inicializar tabla de observabilidad")

    @property
    def id_sucursal(self) -> int | None:
        return self._id_sucursal

    @id_sucursal.setter
    def id_sucursal(self, value: int | None) -> None:
        self._id_sucursal = value
        if getattr(self, "tools", None) is not None:
            self.tools.id_sucursal = value

    @property
    def id_isla(self) -> int | None:
        return self._id_isla

    @id_isla.setter
    def id_isla(self, value: int | None) -> None:
        self._id_isla = value
        if getattr(self, "tools", None) is not None:
            self.tools.id_isla = value

    def set_user(self, user: int | dict) -> None:
        if isinstance(user, dict):
            self.id_usuario = user.get("id")
            self.rol_nombre = user.get("rol_nombre")
            self.user_nombre = user.get("nombre")
            self.id_cliente = None
            self.nombre_cliente = None
            self.id_mecanico_scope = None
            self.es_propietario = bool(user.get("es_propietario"))
            if is_cliente(self.rol_nombre) and self.id_usuario:
                from services import catalog_service

                cliente = catalog_service.get_cliente_by_usuario(self.id_usuario)
                if cliente:
                    self.id_cliente = cliente["id"]
                    self.nombre_cliente = cliente["nombre"]
            elif is_mecanico(self.rol_nombre) and self.id_usuario:
                if not self.es_propietario:
                    from services import catalog_service

                    self.es_propietario = catalog_service.user_is_propietario(self.id_usuario)
                if not self.es_propietario:
                    self.id_mecanico_scope = self.id_usuario
        else:
            self.id_usuario = user
            self.rol_nombre = None
            self.user_nombre = None
            self.id_cliente = None
            self.nombre_cliente = None
            self.id_mecanico_scope = None
            self.es_propietario = False
        self.tools = ToolsService(
            self.rag,
            id_cliente=self.id_cliente,
            nombre_cliente=self.nombre_cliente,
            es_cliente=is_cliente(self.rol_nombre),
            id_mecanico=self.id_mecanico_scope,
            es_mecanico=is_mecanico(self.rol_nombre) and not self.es_propietario,
            es_propietario=self.es_propietario,
            id_sucursal=self.id_sucursal,
            id_isla=self.id_isla,
        )

    def ensure_conversation(self) -> int | None:
        if not self.id_usuario:
            return None
        if not self.id_sucursal:
            raise ValueError("Selecciona una sucursal para usar el asistente.")

        if self.id_conversacion:
            return self.id_conversacion

        if self._pending_new_conversation:
            self._pending_new_conversation = False
            self.id_conversacion = self.repo.crear_conversacion(
                self.id_usuario,
                self.id_sucursal,
                titulo="Nueva conversación",
            )
            return self.id_conversacion

        reciente = self.repo.obtener_conversacion_reciente(self.id_usuario, self.id_sucursal)
        if reciente:
            self.id_conversacion = reciente["id"]
            return self.id_conversacion

        return None

    def start_new_conversation(self) -> int | None:
        """Abre chat vacío: reutiliza uno sin mensajes o crea uno nuevo."""
        if not self.id_usuario:
            return None
        if not self.id_sucursal:
            raise ValueError("Selecciona una sucursal para usar el asistente.")

        if self.id_conversacion:
            if not self.repo.obtener_mensajes(self.id_conversacion):
                return self.id_conversacion

        vacia = self.repo.obtener_conversacion_vacia(self.id_usuario, self.id_sucursal)
        if vacia:
            self._pending_new_conversation = False
            self.id_conversacion = int(vacia["id"])
            return self.id_conversacion

        self.id_conversacion = None
        self._pending_new_conversation = True
        return self.ensure_conversation()

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
        self._pending_new_conversation = False
        self.id_conversacion = id_conversacion
        return True

    def delete_conversation(self, id_conversacion: int) -> bool:
        if not self.id_usuario or not self.id_sucursal:
            return False
        convs = {c["id"] for c in self.list_conversations()}
        if id_conversacion not in convs:
            return False
        ok = self.repo.eliminar_conversacion(
            id_conversacion,
            self.id_usuario,
            self.id_sucursal,
        )
        if ok and self.id_conversacion == id_conversacion:
            self.id_conversacion = None
            self._pending_new_conversation = False
        return ok

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
            titulo = sanitize_llm_context((row.get("titulo") or "Conversación").strip(), max_len=40)
            role = "Usuario" if row["role"] == "user" else "Asistente"
            texto = sanitize_llm_context(
                (row.get("contenido") or "").strip().replace("\n", " "),
                max_len=200,
            )
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
        prompt = SYSTEM_PROMPT + f"\nSucursal activa: {self.id_sucursal}"
        if self.id_isla:
            prompt += f"\nIsla activa (solo consulta citas y stock de esta bahía): {self.id_isla}"
        if is_admin(self.rol_nombre):
            prompt += ADMIN_PROMPT
        elif is_staff_manager(self.rol_nombre):
            prompt += STAFF_MANAGER_PROMPT
        elif is_mecanico(self.rol_nombre) and self.es_propietario:
            prompt += DUENO_TALLER_PROMPT
        elif is_mecanico(self.rol_nombre):
            prompt += MECANICO_PROMPT
        elif is_cliente(self.rol_nombre):
            prompt += CLIENTE_PROMPT
        else:
            prompt += "\nROL ACTUAL: Usuario pendiente de asignación de rol."

        if self.user_nombre and not is_cliente(self.rol_nombre):
            prompt += f"\nUsuario logueado: {self.user_nombre} ({self.rol_nombre})."
        elif is_cliente(self.rol_nombre):
            if self.nombre_cliente:
                prompt += f"\nCliente logueado: {self.nombre_cliente} (id_cliente={self.id_cliente})."
            vehiculos = []
            if self.id_usuario:
                from services import cita_service

                vehiculos = cita_service.list_vehiculos_por_usuario(self.id_usuario)
            if vehiculos:
                placas = ", ".join(v["placa"] for v in vehiculos)
                prompt += f"\nVehículos registrados del cliente: {placas}."
            else:
                prompt += "\nEl cliente aún no tiene vehículos registrados."
        return prompt + self._memory_from_other_conversations()

    def _get_cliente_vehiculos(self) -> list[dict]:
        if not self.id_usuario:
            return []
        from services import cita_service

        return cita_service.list_vehiculos_por_usuario(self.id_usuario)

    def _cliente_placas(self) -> set[str]:
        return {norm_placa_token(v["placa"]) for v in self._get_cliente_vehiculos() if v.get("placa")}

    def _format_cliente_vehiculos_list(self) -> str:
        vehiculos = self._get_cliente_vehiculos()
        if not vehiculos:
            return CLIENTE_SIN_VEHICULOS_ANSWER
        lines = ["Tus vehículos registrados:"]
        for v in vehiculos:
            marca = v.get("marca") or ""
            modelo = v.get("modelo") or ""
            detalle = f"{marca} {modelo}".strip()
            lines.append(f"- {v['placa']}" + (f" ({detalle})" if detalle else ""))
        lines.append("Dime la placa y qué necesitas: estado de cita, agendar servicio o una falla.")
        return "\n".join(lines)

    def _try_cliente_personal_answer(self, question: str) -> str | None:
        if not is_cliente(self.rol_nombre):
            return None

        vehiculos = self._get_cliente_vehiculos()
        placas_cliente = self._cliente_placas()
        placa = extract_placa_from_text(question)

        if placa and placas_cliente and norm_placa_token(placa) not in placas_cliente:
            return (
                f"La placa {placa} no está entre tus vehículos registrados.\n\n"
                + self._format_cliente_vehiculos_list()
            )

        if is_mi_cita_question(question):
            if not self.id_cliente:
                return "No encontré tu ficha de cliente. Cierra sesión e intenta de nuevo."
            from services import cita_service

            citas = cita_service.list_citas(self.id_sucursal, self.id_cliente)
            if not citas:
                if not vehiculos:
                    return CLIENTE_SIN_VEHICULOS_ANSWER
                return (
                    "No tienes citas registradas todavía.\n\n"
                    "Puedes solicitar una en Mis Citas o dime la placa de tu vehículo y la falla."
                )
            lines = ["Tus citas:"]
            for c in citas[:8]:
                estado = estado_a_etiqueta(c.get("estado"))
                lines.append(
                    f"- {c.get('placa')}: {estado} | Mecánico: {c.get('mecanico') or 'por asignar'} | "
                    f"Isla: {c.get('isla') or 'por asignar'}"
                )
            return "\n".join(lines)

        if is_personal_vehicle_question(question):
            if not vehiculos:
                return CLIENTE_SIN_VEHICULOS_ANSWER
            if is_similarity_question(question) and len(vehiculos) == 1:
                return None
            if len(vehiculos) == 1:
                v = vehiculos[0]
                marca = v.get("marca") or ""
                modelo = v.get("modelo") or ""
                detalle = f"{marca} {modelo}".strip()
                base = f"Tu vehículo registrado es {v['placa']}"
                if detalle:
                    base += f" ({detalle})"
                return base + ". ¿Quieres ver tus citas, el estado o reportar una falla?"
            return self._format_cliente_vehiculos_list()

        return None

    def _filter_rag_for_cliente(self, rag_result: dict) -> dict:
        placas = self._cliente_placas()
        if not placas:
            return {**rag_result, "matches": []}
        filtered = [
            m for m in rag_result.get("matches", [])
            if norm_placa_token(m.get("placa") or "") in placas
        ]
        return {**rag_result, "matches": filtered}

    def _mecanico_cita_ids(self) -> set[str]:
        """Solo citas asignadas a este mecánico en la sucursal activa."""
        from services import cita_service

        if not self.id_mecanico_scope or not self.id_sucursal:
            return set()
        citas = cita_service.list_citas(self.id_sucursal, id_mecanico=self.id_mecanico_scope)
        return {str(c["id"]) for c in citas if c.get("id")}

    def _mecanico_placas(self) -> set[str]:
        """Placas de vehículos/citas propias del mecánico en la sucursal activa."""
        from services import cita_service

        if not self.id_mecanico_scope:
            return set()
        placas: set[str] = set()
        if self.id_sucursal:
            for c in cita_service.list_citas(self.id_sucursal, id_mecanico=self.id_mecanico_scope):
                if c.get("placa"):
                    placas.add(norm_placa_token(c["placa"]))
        for v in cita_service.list_vehiculos(id_mecanico_asignado=self.id_mecanico_scope):
            if self.id_sucursal and v.get("id_sucursal") and v["id_sucursal"] != self.id_sucursal:
                continue
            if v.get("placa"):
                placas.add(norm_placa_token(v["placa"]))
        return placas

    def _filter_rag_for_mecanico(self, rag_result: dict) -> dict:
        """Solo fallas de citas/placas del mecánico en la sucursal activa."""
        cita_ids = self._mecanico_cita_ids()
        placas = self._mecanico_placas()
        if not cita_ids and not placas:
            return {**rag_result, "matches": []}
        filtered = []
        for m in rag_result.get("matches", []):
            id_cita = str(m.get("id_cita") or "")
            placa = norm_placa_token(m.get("placa") or "")
            if (id_cita and id_cita in cita_ids) or (placa and placa in placas):
                filtered.append(m)
        return {**rag_result, "matches": filtered}

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
        return self.ask_stream(question)

    def ask_stream(
        self,
        question: str,
        on_status: Callable[[str, str], None] | None = None,
        on_token: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Procesa una pregunta con guardrails, estados, streaming y observabilidad."""
        start = time.perf_counter()
        first_token_at: float | None = None
        token_count = 0
        question = (question or "").strip()
        self.ensure_conversation()
        session_id = str(self.id_conversacion or "sin-sesion")

        def emit_status(phase: str, label: str) -> None:
            if on_status:
                on_status(phase, label)

        def emit_token(chunk: str) -> None:
            nonlocal first_token_at, token_count
            if not chunk:
                return
            if IS_PRODUCTION:
                return
            if first_token_at is None:
                first_token_at = time.perf_counter()
            token_count += 1
            if on_token:
                on_token(chunk)

        def stream_answer(text: str) -> str:
            answer = plain_chat_text(text or "")
            if not IS_PRODUCTION:
                for char in answer:
                    emit_token(char)
            return answer

        def emit_safe_answer(text: str) -> None:
            nonlocal first_token_at, token_count
            if not on_token or not text:
                return
            if first_token_at is None:
                first_token_at = time.perf_counter()
            for char in text:
                token_count += 1
                on_token(char)

        def finalize(
            answer: str,
            route: str,
            *,
            tool_calls: list | None = None,
            was_blocked: bool = False,
            persist: bool = True,
        ) -> dict[str, Any]:
            total_ms = int((time.perf_counter() - start) * 1000)
            ttft_ms = int((first_token_at - start) * 1000) if first_token_at else None
            generation_s = max((time.perf_counter() - (first_token_at or start)), 0.001)
            tps = round(token_count / generation_s, 2) if first_token_at and token_count else None
            tools_obs = self._format_tools_observability(tool_calls or [])
            safety = enforce_llm_output(answer)
            answer = safety.text
            if IS_PRODUCTION:
                emit_safe_answer(answer)

            try:
                self.obs_repo.insert_log(
                    session_id=session_id,
                    user_prompt=question,
                    system_response=answer,
                    ttft_ms=ttft_ms,
                    total_latency_ms=total_ms,
                    tokens_per_second=tps,
                    was_blocked=was_blocked,
                    tools_executed=tools_obs,
                )
            except Exception:
                logger.exception("No se pudo guardar log de observabilidad")

            result = self._result(
                question,
                answer,
                route,
                tool_calls=tool_calls,
                persist=persist and bool(question) and not was_blocked,
            )
            result["metrics"] = {
                "ttft_ms": ttft_ms,
                "total_latency_ms": total_ms,
                "tokens_per_second": tps,
                "was_blocked": was_blocked or safety.blocked,
            }
            return result

        if not question:
            emit_status("thinking", "Pensando...")
            answer = stream_answer(INVALID_INPUT_ANSWER)
            return finalize(answer, "help", persist=False)

        guard = validate_user_prompt(question)
        if guard.blocked:
            if self.id_usuario:
                audit(
                    accion=audit_actions.CHAT_GUARDRAIL_BLOCKED,
                    id_usuario=self.id_usuario,
                    recurso=f"conversacion:{self.id_conversacion or 'nueva'}",
                    detalle=guard.rule_id or "blocked",
                    resultado="blocked",
                )
            emit_status("thinking", "Validando entrada...")
            answer = stream_answer(BLOCKED_MESSAGE)
            return finalize(answer, "blocked", was_blocked=True)

        question = normalize_workshop_question(question)

        emit_status("thinking", "Pensando...")

        if is_invalid_input(question):
            answer = stream_answer(get_friendly_fallback_answer(self.rol_nombre))
            return finalize(answer, "help")

        if is_greeting(question):
            answer = stream_answer(get_greeting_answer(self.rol_nombre))
            return finalize(answer, "help")

        if is_casual_chat(question):
            answer = stream_answer(get_casual_chat_answer(self.rol_nombre))
            return finalize(answer, "chat")

        if is_acknowledgment(question):
            answer = stream_answer(ACKNOWLEDGMENT_ANSWER)
            return finalize(answer, "help")

        if is_casual_nonsense(question):
            answer = stream_answer(get_friendly_fallback_answer(self.rol_nombre))
            return finalize(answer, "help")

        if is_capabilities_question(question):
            answer = stream_answer(get_capabilities_answer(self.rol_nombre))
            return finalize(answer, "help")

        guided_entity = get_guided_create_entity_answer(
            question,
            es_propietario=self.es_propietario,
            es_cliente=is_cliente(self.rol_nombre),
        )
        if guided_entity:
            answer = stream_answer(guided_entity)
            return finalize(answer, "guided_create")

        guided_create = get_guided_create_cita_answer(
            question,
            es_propietario=self.es_propietario,
            es_cliente=is_cliente(self.rol_nombre),
        )
        if guided_create:
            answer = stream_answer(guided_create)
            return finalize(answer, "guided_create")

        if is_memory_recall_question(question):
            emit_status("searching", "Buscando en conversaciones anteriores...")
            answer = stream_answer(self._format_recall_answer(question))
            return finalize(answer, "memory_recall")

        personal_answer = self._try_cliente_personal_answer(question)
        if personal_answer:
            answer = stream_answer(personal_answer)
            return finalize(answer, "help")

        if (
            is_workshop_staff(self.rol_nombre)
            and not is_cliente(self.rol_nombre)
            and is_personal_vehicle_question(question)
        ):
            answer = stream_answer(STAFF_MI_AUTO_ANSWER)
            return finalize(answer, "help")

        cancel_args = parse_cancel_cita_request(question)
        if cancel_args:
            if not cancel_args.get("placa"):
                if is_cliente(self.rol_nombre):
                    vehiculos = self._get_cliente_vehiculos()
                    if not vehiculos:
                        answer = stream_answer(CLIENTE_SIN_VEHICULOS_ANSWER)
                        return finalize(answer, "help")
                    answer = stream_answer(
                        "Para cancelar una cita necesito la placa de tu vehículo. "
                        + self._format_cliente_vehiculos_list().split("\n", 1)[0]
                    )
                else:
                    answer = stream_answer(
                        "Para cancelar una cita necesito la placa del vehículo. "
                        "Por ejemplo: cancela la cita de ABC-123."
                    )
                return finalize(answer, "help")
            emit_status("acting", "Cancelando cita...")
            tool_args = {**cancel_args, "id_sucursal": self.id_sucursal}
            result = self.tools.execute("cancelar_cita_natural", tool_args)
            answer = format_tool_result("cancelar_cita_natural", result)
            if not answer:
                answer = (
                    "Para cancelar una cita necesito la placa del vehículo, "
                    "por ejemplo: cancela la cita de ABC-123."
                )
            answer = stream_answer(answer)
            return finalize(
                answer,
                "function_calling",
                tool_calls=[{"name": "cancelar_cita_natural", "arguments": tool_args, "result": result}],
            )

        emit_status("searching", "Enrutando a agente especialista...")
        try:
            return self.orchestrator.route_and_run(
                question,
                emit_status=emit_status,
                emit_token=emit_token,
                finalize=finalize,
            )
        except Exception:
            logger.exception("Orquestador falló; usando flujo transaccional directo")
            return self._ask_with_tools_stream(question, emit_status, emit_token, finalize)

    @staticmethod
    def _format_tools_observability(tool_calls_log: list[dict]) -> list[dict[str, Any]]:
        formatted: list[dict[str, Any]] = []
        for entry in tool_calls_log:
            result = entry.get("result")
            status = "SUCCESS"
            if isinstance(result, dict):
                if result.get("ok") is False or result.get("error"):
                    status = "ERROR"
            item: dict[str, Any] = {
                "name": entry.get("name"),
                "parameters": entry.get("arguments", {}),
                "status": status,
            }
            if status == "ERROR" and isinstance(result, dict):
                item["error"] = result.get("error") or result.get("message") or "Error en tool"
            formatted.append(item)
        return formatted

    def _ask_with_tools_stream(
        self,
        question: str,
        emit_status: Callable[[str, str], None],
        emit_token: Callable[[str], None],
        finalize: Callable[..., dict[str, Any]],
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            *self._ollama_context(question),
            {"role": "user", "content": question},
        ]

        tool_calls_log: list[dict] = []
        seen_signatures: set[str] = set()

        emit_status("thinking", "Pensando...")
        tool_defs = tools_for_session(
            es_cliente=is_cliente(self.rol_nombre),
            es_mecanico=is_mecanico(self.rol_nombre) and not self.es_propietario,
            es_propietario=bool(self.es_propietario),
        )
        try:
            response = ollama.chat(
                model=OLLAMA_CHAT_MODEL,
                messages=messages,
                tools=tool_defs,
            )
        except Exception as exc:
            logger.exception("Error en ollama.chat")
            answer = f"Error con Ollama ({OLLAMA_CHAT_MODEL}): {exc}"
            for word in answer.split(" "):
                emit_token(word + " ")
            return finalize(answer, "error")

        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls") or []

        if tool_calls:
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

                emit_status("acting", self._tool_status_label(name))

                if "id_sucursal" not in args and name in SUCURSAL_TOOLS:
                    args["id_sucursal"] = self.id_sucursal

                if "id_isla" not in args and name in ISLA_TOOLS and self.id_isla:
                    args["id_isla"] = self.id_isla

                sig = call_signature(name, args)
                if sig in seen_signatures:
                    result = {
                        "ok": False,
                        "error": "Llamada duplicada omitida en este turno.",
                        "recoverable": True,
                    }
                else:
                    seen_signatures.add(sig)
                    if not allows_mutating_tool(
                        question,
                        name,
                        staff_manage=is_staff_manager(self.rol_nombre)
                        or (
                            is_workshop_staff(self.rol_nombre)
                            and name in ("cambiar_estado_cita_natural", "cambiar_estado_cita", "editar_cita_natural")
                        ),
                    ):
                        result = {
                            "ok": False,
                            "error": (
                                "Necesito instrucciones claras para crear o cambiar citas "
                                "(cliente, placa, mecánico, isla o estado)."
                            ),
                            "recoverable": True,
                        }
                    else:
                        result = self.tools.execute(name, args)

                tool_calls_log.append({"name": name, "arguments": args, "result": result})
                messages.append({
                    "role": "tool",
                    "content": tool_message_content(name or "tool", result),
                })

            if should_skip_followup_llm(tool_calls_log):
                answer = tool_failure_user_message(tool_calls_log)
                for word in answer.split(" "):
                    emit_token(word + " ")
                return finalize(answer, "function_calling", tool_calls=tool_calls_log)

            formatted = format_tool_calls_log(tool_calls_log)
            if formatted:
                for word in formatted.split(" "):
                    emit_token(word + " ")
                return finalize(formatted, "function_calling", tool_calls=tool_calls_log)

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
            except Exception as exc:
                logger.exception("Error en segunda llamada ollama.chat")
                answer = tool_failure_user_message(tool_calls_log) or str(exc)
                for word in answer.split(" "):
                    emit_token(word + " ")
            return finalize(answer, "function_calling", tool_calls=tool_calls_log)

        emit_status("thinking", "Generando respuesta...")
        content = plain_chat_text(msg.get("content", "No pude generar respuesta."))
        for word in content.split(" "):
            emit_token(word + " ")
        return finalize(content, "llm_direct")

    @staticmethod
    def _tool_status_label(tool_name: str) -> str:
        labels = {
            "listar_citas": "Consultando citas del taller...",
            "contar_citas": "Contando citas...",
            "listar_islas": "Consultando islas de trabajo...",
            "listar_inventario": "Consultando inventario...",
            "contar_inventario": "Contando inventario...",
            "listar_mecanicos": "Consultando mecánicos...",
            "buscar_fallas_similares": "Buscando fallas similares...",
            "crear_cita_natural": "Agendando cita...",
            "crear_cliente_natural": "Registrando cliente...",
            "crear_vehiculo_natural": "Registrando vehículo...",
            "crear_servicio_natural": "Creando servicio...",
            "crear_inventario_natural": "Agregando al inventario...",
            "editar_cita_natural": "Actualizando cita...",
            "cancelar_cita_natural": "Cancelando cita...",
            "cambiar_estado_cita_natural": "Actualizando estado de cita...",
        }
        return labels.get(tool_name, f"Ejecutando {tool_name.replace('_', ' ')}...")

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
