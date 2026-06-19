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
)

MUTATING_TOOLS = frozenset({
    "crear_cita_natural",
    "cambiar_estado_cita_natural",
    "cambiar_estado_cita",
})

ACKNOWLEDGMENT_PHRASES = (
    "ok", "okay", "vale", "si", "sí", "ah si", "ah sí", "aja", "ajá",
    "claro", "bueno", "genial", "perfecto", "entendido", "de acuerdo",
    "gracias", "muchas gracias", "thx", "thanks",
)


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


def allows_mutating_tool(question: str, tool_name: str) -> bool:
    """Evita crear o cambiar citas si el usuario no lo pidió con claridad."""
    if tool_name not in MUTATING_TOOLS:
        return True
    if _is_action_request(question):
        return True
    q = _norm(question)
    state_markers = (
        "marca como", "marcar como", "cambia el estado", "cambiar estado",
        "cambiar a", "pon en", "poner en", "actualiza la cita", "actualizar cita",
    )
    if any(m in q for m in state_markers):
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
- Marca como completada la cita de la placa ABC-123

También puedo listar citas, clientes, vehículos, mecánicos e islas. Dime qué necesitas en español claro."""


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
