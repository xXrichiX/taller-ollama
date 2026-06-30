"""Detección de preguntas de ayuda, capacidades e inputs inválidos."""

import re
import unicodedata

CAPABILITIES_PATTERNS = (
    "qué puedes", "que puedes", "qué sabes", "que sabes",
    "qué tanto", "que tanto", "cuánto puedes", "cuanto puedes",
    "puedes crear", "puedes hacer", "qué haces", "que haces",
    "qué hace", "que hace", "para qué sirves", "para que sirves",
    "cómo funciona", "como funciona", "ayuda", "capacidades",
    "en qué me ayudas", "en que me ayudas", "qué me puedes",
    "que me puedes", "funciones", "opciones",
)

WORKSHOP_HINTS = (
    "cita", "citas", "cliente", "vehiculo", "vehículo", "placa", "auto", "carro",
    "mecanico", "mecánico", "isla", "taller", "falla", "freno", "frenos",
    "ruido", "motor", "aceite", "lista", "listar", "cuant", "cuánt",
    "crea", "crear", "agenda", "marca", "pendiente", "proceso", "complet",
    "cancelar", "cancela", "eliminar", "elimina", "borrar", "editar", "edita",
    "similar", "parecid", "busca", "roberto", "maria", "maría", "abc",
    "hola", "gracias", "salir", "diagn", "servicio", "horario",
    "recuerda", "recuerdas", "anterior", "antes", "conversacion", "conversación",
    "charla", "mencione", "mencioné", "hablamos", "dije",
)

SUBSTANTIVE_WORKSHOP_HINTS = (
    "cita", "citas", "cliente", "clientes", "vehiculo", "vehículo", "vehiculos",
    "vehículos", "placa", "mecanico", "mecánico", "mecanicos", "mecánicos",
    "isla", "islas", "falla", "fallas", "freno", "frenos", "ruido", "motor",
    "aceite", "similar", "parecid", "chirrido", "vibracion", "vibración",
    "roberto", "carlos", "abc", "listame", "listar", "lista las", "lista los",
    "cuant", "cuánt", "total de", "busca fallas", "buscar fallas", "crea cita",
    "crear cita", "agenda", "marca como", "marcar como", "cambia el estado",
    "cambiar estado", "pendiente", "proceso", "completada", "cancelada",
    "cancelar", "eliminar", "borrar", "editar", "actualizar", "modificar",
)

MUTATING_TOOLS = frozenset({
    "crear_cita_natural",
    "cambiar_estado_cita_natural",
    "cambiar_estado_cita",
    "cancelar_cita_natural",
    "editar_cita_natural",
})

_PLACA_RE = re.compile(r"\b[A-Za-z]{3}[-\s]?\d{2,3}\b")

_CANCEL_VERBS = (
    "cancelar", "cancela", "calear", "calea", "canselar", "cansela",
    "eliminar", "elimina", "borrar", "borra", "quitar", "quita",
    "anular", "anula", "dar de baja", "deshacer",
)

_EDIT_MARKERS = (
    "editar cita", "edita cita", "editar la cita", "edita la cita",
    "actualizar cita", "actualiza cita", "actualizar la cita", "actualiza la cita",
    "modificar cita", "modifica cita", "modificar la cita", "modifica la cita",
    "cambiar mecanico", "cambia mecanico", "cambiar mecánico", "cambia mecánico",
    "cambiar falla", "cambia la falla", "cambiar isla", "cambia la isla",
    "mueve la cita", "reagendar", "reagenda",
)

ACKNOWLEDGMENT_PHRASES = (
    "ok", "okay", "vale", "si", "sí", "ah si", "ah sí", "aja", "ajá",
    "claro", "bueno", "genial", "perfecto", "entendido", "de acuerdo",
    "gracias", "muchas gracias", "thx", "thanks",
)


def extract_placa_from_text(text: str) -> str | None:
    match = _PLACA_RE.search(text or "")
    if not match:
        return None
    raw = match.group(0).upper().replace(" ", "")
    if "-" not in raw and len(raw) >= 6:
        return f"{raw[:3]}-{raw[3:]}"
    return raw


PERSONAL_VEHICLE_MARKERS = (
    "mi auto", "mi carro", "mis autos", "mis carros",
    "mi vehiculo", "mi vehículo", "mis vehiculos", "mis vehículos",
    "mi coche", "mi unidad", "de mi auto", "de mi carro",
    "en mi auto", "en mi carro", "para mi auto", "para mi carro",
)

MI_CITA_MARKERS = (
    "mi cita", "mis citas", "mi turno", "mis turnos",
    "estado de mi cita", "estado de mis citas",
)


def is_personal_vehicle_question(question: str) -> bool:
    q = _norm(question)
    return any(m in q for m in PERSONAL_VEHICLE_MARKERS)


def is_mi_cita_question(question: str) -> bool:
    q = _norm(question)
    return any(m in q for m in MI_CITA_MARKERS)


def norm_placa_token(placa: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _norm(placa or ""))


RAG_SIMILARITY_HINTS = (
    "similar", "parecido", "parecida", "casos similares", "caso similar",
)

STAFF_MI_AUTO_ANSWER = """Eres personal del taller: aquí no aplica "mi auto".

Dime la placa o el cliente, por ejemplo: fallas similares a la placa ABC-123 o del cliente Roberto García."""


def is_similarity_question(question: str) -> bool:
    q = _norm(question)
    return any(h in q for h in RAG_SIMILARITY_HINTS)


CLIENTE_SIN_VEHICULOS_ANSWER = """No tienes ningún vehículo registrado en el sistema.

Regístralo primero en la pestaña Mis Vehículos. Después podré ayudarte con tu auto, tus citas o fallas de tu placa."""

CLIENTE_FALLBACK_ANSWER = """No entendí bien eso.

Puedo ayudarte con tus vehículos y tus citas. Si aún no registras un auto, hazlo en Mis Vehículos.
Si ya tienes uno, dime la placa o pregunta por mis citas."""


def get_friendly_fallback_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente

    if is_cliente(rol_nombre):
        return CLIENTE_FALLBACK_ANSWER
    return FRIENDLY_FALLBACK_ANSWER


def normalize_workshop_question(question: str) -> str:
    """Corrige typos de voz y mapea 'eliminar cita' → cancelar."""
    text = (question or "").strip()
    if not text:
        return text

    typo_map = (
        (r"\bmi\s+audo\b", "mi auto"),
        (r"\bmi\s+oto\b", "mi auto"),
        (r"\bmi\s+auro\b", "mi auto"),
        (r"\bcalear\b", "cancelar"),
        (r"\bcalea\b", "cancela"),
        (r"\bcanselar\b", "cancelar"),
        (r"\bcansela\b", "cancela"),
        (r"\belimnar\b", "eliminar"),
        (r"\belimna\b", "elimina"),
        (r"\beditar\b", "editar"),
        (r"\bedita\b", "edita"),
    )
    for pattern, replacement in typo_map:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    norm = _norm(text)
    if "cita" in norm and any(v in norm for v in ("eliminar", "elimina", "borrar", "borra", "quitar", "quita")):
        text = re.sub(
            r"\b(eliminar|elimina|borrar|borra|quitar|quita)\b",
            "cancelar",
            text,
            flags=re.IGNORECASE,
        )

    from services.spoken_number_normalize import normalize_spoken_numbers

    return normalize_spoken_numbers(text.strip())


def is_cancel_cita_request(question: str) -> bool:
    q = _norm(question)
    if "cita" not in q:
        return False
    return any(v in q for v in _CANCEL_VERBS)


def is_edit_cita_request(question: str) -> bool:
    q = _norm(question)
    if "cita" not in q:
        return False
    return any(m in q for m in _EDIT_MARKERS) or (
        any(w in q for w in ("editar", "edita", "actualizar", "actualiza", "modificar", "modifica"))
        and "cita" in q
    )


def parse_cancel_cita_request(question: str) -> dict | None:
    if not is_cancel_cita_request(question):
        return None
    placa = extract_placa_from_text(question)
    return {"placa": placa, "id_cita": None}


def is_memory_recall_question(question: str) -> bool:
    q = _norm(question)
    patterns = (
        "recuerdas", "recuerda lo", "conversacion anterior", "charla anterior",
        "lo que te dije", "lo que dije", "hablamos antes", "mencione antes",
        "mencioné antes", "en la otra conversacion", "otra conversacion",
        "hablamos en", "de que hablamos", "de que hblab", "terior conversacion",
        "conversacion previa", "conversacion pasada", "charla previa",
        "que platicamos", "que charlamos", "que hablamos",
    )
    if any(p in q for p in patterns):
        return True
    if "conversacion" in q or "charla" in q:
        hints = (
            "anterior", "terior", "previa", "pasada", "otra", "antes",
            "hablamos", "hblab", "dije", "platic", "charlamos",
        )
        if any(h in q for h in hints):
            return True
    return False


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()


def _is_action_request(question: str) -> bool:
    """Pedido concreto al taller (crear cita, listar, etc.), no pregunta de capacidades."""
    q = _norm(question)
    markers = (
        "crea una cita", "crear una cita", "creame una cita", "crear cita",
        "agenda una cita", "agendar cita", "marca como", "marcar como",
        "lista los", "lista las", "listar ", "listame", "cambia el estado",
        "buscar fallas", "busca fallas",
        "cancelar cita", "cancela cita", "eliminar cita", "elimina cita",
        "borrar cita", "borra cita", "editar cita", "edita cita",
        "actualizar cita", "actualiza cita", "modificar cita", "modifica cita",
    )
    if any(m in q for m in markers):
        return True
    if re.search(r"(me )?puedes crear\b", q) and any(
        w in q for w in ("cita", "cliente", "vehiculo", "vehículo", "placa")
    ):
        return True
    if re.search(r"(me )?puedes hacer\b", q) and any(
        w in q for w in ("cita", "cliente", "vehiculo", "vehículo", "placa", "taller")
    ):
        return True
    return False


def looks_like_workshop_request(question: str) -> bool:
    """True solo si el mensaje parece pedir algo concreto del taller."""
    if _is_action_request(question):
        return True
    q = _norm(question)
    if any(h in q for h in SUBSTANTIVE_WORKSHOP_HINTS):
        return True
    if any(
        p in q
        for p in (
            "cuantas citas", "cuántas citas", "cuantos clientes", "cuántos clientes",
            "cuantos vehiculos", "cuántos vehículos", "total de citas",
        )
    ):
        return True
    return False


def allows_mutating_tool(question: str, tool_name: str, *, staff_manage: bool = False) -> bool:
    """Evita crear o cambiar citas si el usuario no lo pidió con claridad."""
    if staff_manage and tool_name in MUTATING_TOOLS:
        return True
    if tool_name not in MUTATING_TOOLS:
        return True
    if _is_action_request(question):
        return True
    q = _norm(question)
    state_markers = (
        "marca como", "marcar como", "cambia el estado", "cambiar estado",
        "cambiar a", "pon en", "poner en", "actualiza la cita", "actualizar cita",
        "editar cita", "edita cita", "modificar cita", "modifica cita",
        "cancelar cita", "cancela cita", "eliminar cita", "elimina cita",
        "borrar cita", "borra cita", "calear", "quitar cita",
    )
    if any(m in q for m in state_markers):
        return True
    if is_cancel_cita_request(question) or is_edit_cita_request(question):
        return True
    if "crea" in q or "crear" in q or "agenda" in q or "agendar" in q:
        return True
    return False


def is_acknowledgment(question: str) -> bool:
    """Respuestas cortas sin pedido (ah sí, ok, gracias)."""
    if _is_action_request(question) or looks_like_workshop_request(question):
        return False
    q = re.sub(r"[^a-z\s]", "", _norm(question)).strip()
    if not q:
        return False
    if q in ACKNOWLEDGMENT_PHRASES:
        return True
    words = q.split()
    if len(words) <= 4 and q in ACKNOWLEDGMENT_PHRASES:
        return True
    if len(words) <= 3 and all(w in ("si", "sí", "ah", "ok", "ya", "bueno", "claro", "vale") for w in words):
        return True
    if len(words) == 2 and words[0] in ("ah", "oh") and words[1] in ("si", "sí", "ok", "ya", "claro"):
        return True
    return False


def is_capabilities_question(question: str) -> bool:
    q = _norm(question)
    if _is_action_request(question):
        return False
    # "¿qué hace la empresa/taller?" no es menú de ayuda del asistente
    if any(p in q for p in ("que hace", "qué hace")) and any(
        w in q for w in ("empresa", "taller", "iespro", "sistema")
    ):
        return False
    return any(p in q for p in CAPABILITIES_PATTERNS)


def is_greeting(question: str) -> bool:
    """Saludo simple sin pedido concreto al taller."""
    q = _norm(question)
    q = re.sub(r"[^a-z\s]", "", q).strip()
    if not q:
        return False
    if _is_action_request(question) or is_capabilities_question(question):
        return False
    if any(w in q for w in ("cita", "cliente", "placa", "lista", "cuant", "falla", "vehiculo")):
        return False

    saludos = (
        "hola", "holaa", "holaaa", "holaaaa", "buenas", "buenos dias", "buen dia",
        "hey", "que tal", "qué tal", "saludos", "buenas tardes", "buenas noches",
        "hi", "hello", "qué onda", "que onda",
    )
    if q in saludos:
        return True
    if re.fullmatch(r"hol+a+", q):
        return True
    if len(q.split()) <= 3 and any(q.startswith(s) for s in ("hola", "buenas", "hey")):
        return True
    return False


def is_casual_nonsense(question: str) -> bool:
    """Risa, texto random o charla sin tema del taller."""
    if _is_action_request(question) or is_capabilities_question(question):
        return False
    if is_memory_recall_question(question) or looks_like_workshop_request(question):
        return False
    if is_acknowledgment(question):
        return False

    q = _norm(question)
    compact = re.sub(r"[^a-z]", "", q)
    if not compact:
        return True

    if re.search(r"jaja|jeje|jiji|haha", compact):
        return True
    if compact in ("lol", "xd", "xdd", "kk", "asdf", "asdfgh"):
        return True
    if re.fullmatch(r"(.)\1{4,}", compact):
        return True

    words = q.split()
    if len(words) >= 4:
        return True

    letters = compact
    vowels = sum(1 for c in letters if c in "aeiou")
    if len(letters) <= 10 and vowels <= 1 and " " not in q:
        return True

    return True


def is_invalid_input(question: str) -> bool:
    raw = (question or "").strip()
    if not raw:
        return True
    if len(raw) < 2:
        return True

    q = _norm(raw)

    if any(h in q for h in WORKSHOP_HINTS):
        return False

    if is_capabilities_question(raw):
        return False

    letters = re.sub(r"[^a-z]", "", q)
    if len(letters) < 2:
        return True

    vowels = sum(1 for c in letters if c in "aeiou")
    if len(letters) >= 5 and vowels == 0:
        return True

    if len(raw) >= 7 and " " not in raw:
        ratio = vowels / len(letters)
        if ratio < 0.12:
            return True

    words = re.findall(r"[a-záéíóúüñ]{3,}", q)
    sensible = [w for w in words if any(c in "aeiouáéíóú" for c in w)]
    if len(raw) >= 8 and not sensible:
        return True

    if re.fullmatch(r"(.)\1{3,}", raw.replace(" ", "")):
        return True

    return False


CAPABILITIES_ANSWER = """Puedo ayudarte con el taller de estas formas:

Consultas (datos exactos):
- ¿Cuántas citas hay registradas?
- ¿Cuántos clientes o vehículos hay?

Historial de fallas parecidas:
- ¿Hay casos similares a ruido al frenar?

Acciones que ejecuto en el sistema:
- Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido en frenos
- Edita la cita de ABC-123: cambia el mecánico a Ana y la falla a vibración en volante
- Marca como completada la cita de la placa ABC-123
- Cancela (o elimina) la cita de la placa ABC-123 — queda inactiva, no se borra de la base

También puedo listar citas, clientes, vehículos, mecánicos e islas. Dime qué necesitas en español claro."""


CAPABILITIES_ANSWER_STAFF = """Como personal del taller puedo ayudarte así:

Consultas del taller completo:
- ¿Cuántas citas hay? ¿Cuántos clientes o vehículos?
- Fallas similares por placa, cliente o síntoma en todo el historial

Flujo de mostrador (cliente sin app):
- Registra cliente, vehículo y cita desde las pestañas Clientes, Vehículos y Citas
- O pídeme por chat, por ejemplo:
  Crea una cita para María López, placa XYZ-789, mecánico Carlos, isla 2, falla: ruido en frenos

Acciones en el sistema:
- Crear, editar o cancelar citas de cualquier placa
- Cambiar mecánico, isla, falla o estado de una cita
- Listar citas, clientes, vehículos, mecánicos e islas

No uses "mi auto": actúa siempre con el nombre del cliente o la placa que te indiquen."""


def get_capabilities_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente, is_staff_manager

    if is_staff_manager(rol_nombre):
        return CAPABILITIES_ANSWER_STAFF
    if is_cliente(rol_nombre):
        return CAPABILITIES_ANSWER_CLIENTE
    return CAPABILITIES_ANSWER


def get_greeting_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente, is_staff_manager

    if is_staff_manager(rol_nombre):
        return GREETING_ANSWER_STAFF
    if is_cliente(rol_nombre):
        return GREETING_ANSWER_CLIENTE
    return GREETING_ANSWER


CAPABILITIES_ANSWER_CLIENTE = """Puedo ayudarte con tus vehículos y citas:

- Ver cuántas citas tienes o listar las tuyas
- Agendar cita con la placa de tu auto y la falla (el taller asigna mecánico e isla)
- Cancelar una cita activa de tu vehículo, por ejemplo: cancela la cita de ABC-123
- Buscar fallas similares si mencionas la placa de tu auto

Primero registra tu vehículo en la pestaña Vehículos si aún no lo has hecho.
No puedo ver datos de otros clientes ni gestionar el taller completo."""


GREETING_ANSWER_CLIENTE = """Hola. Soy el asistente de IESPRO-Taller.

Puedo ayudarte con tus citas y tus vehículos registrados.

Dime qué necesitas, por ejemplo: lista mis citas, o agenda cita para mi placa ABC-123 con falla de frenos."""


GREETING_ANSWER_STAFF = """Hola. Soy el asistente de IESPRO-Taller.

Estás en modo personal del taller: puedo consultar todo el historial, buscar fallas por placa o cliente, y crear o modificar citas en nombre de cualquier cliente.

Dime qué necesitas, por ejemplo: fallas similares a la placa ABC-123, o crea una cita para Roberto García."""


GREETING_ANSWER = """Hola. Soy el asistente de IESPRO-Taller.

Puedo ayudarte con citas, clientes, vehículos, islas y mecánicos del taller.

Dime qué necesitas, por ejemplo: ¿Cuántas citas hay? o lista los clientes."""


FRIENDLY_FALLBACK_ANSWER = """No entendí bien eso, pero aquí estoy.

Soy el asistente del taller. Puedo consultar datos, crear citas o buscar fallas parecidas.

Prueba con algo como:
- ¿Cuántas citas hay?
- Lista los clientes
- Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido en frenos"""


INVALID_INPUT_ANSWER = FRIENDLY_FALLBACK_ANSWER

ACKNOWLEDGMENT_ANSWER = """Entendido. ¿En qué más te ayudo con el taller?

Puedo listar citas, contar pendientes, buscar fallas parecidas o agendar una cita."""
