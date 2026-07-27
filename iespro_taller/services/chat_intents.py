"""Detección de preguntas de ayuda, capacidades e inputs inválidos."""

import re
import unicodedata

CAPABILITIES_PATTERNS = (
    "qué puedes hacer", "que puedes hacer",
    "qué sabes hacer", "que sabes hacer",
    "qué tanto puedes", "que tanto puedes",
    "cuánto puedes", "cuanto puedes",
    "para qué sirves", "para que sirves",
    "cómo funciona", "como funciona",
    "en qué me ayudas", "en que me ayudas",
    "qué me puedes", "que me puedes",
    "capacidades", "funciones", "opciones",
    "menú de ayuda", "menu de ayuda",
)

CASUAL_CHAT_PATTERNS = (
    "qué haces", "que haces", "quien eres", "quién eres",
    "que eres", "qué eres", "como estas", "cómo estás",
    "como te llamas", "cómo te llamas",
)

WORKSHOP_HINTS = (
    "cita", "citas", "orden", "ordenes", "órdenes", "órden",
    "cliente", "vehiculo", "vehículo", "placa", "auto", "carro",
    "mecanico", "mecánico", "isla", "taller", "falla", "freno", "frenos",
    "inventario", "stock", "pieza", "piezas", "refaccion", "refacción",
    "ruido", "motor", "aceite", "lista", "listar", "cuant", "cuánt",
    "crea", "crear", "agenda", "marca", "pendiente", "proceso", "complet",
    "cancelar", "cancela", "eliminar", "elimina", "borrar", "editar", "edita",
    "similar", "parecid", "busca", "roberto", "maria", "maría", "abc",
    "hola", "gracias", "salir", "diagn", "servicio", "horario",
    "recuerda", "recuerdas", "anterior", "antes", "conversacion", "conversación",
    "charla", "mencione", "mencioné", "hablamos", "dije",
)

SUBSTANTIVE_WORKSHOP_HINTS = (
    "cita", "citas", "orden", "ordenes", "órdenes", "órden",
    "cliente", "clientes", "vehiculo", "vehículo", "vehiculos",
    "vehículos", "placa", "mecanico", "mecánico", "mecanicos", "mecánicos",
    "isla", "islas", "falla", "fallas", "freno", "frenos", "ruido", "motor",
    "inventario", "stock", "pieza", "piezas", "refaccion", "refacción",
    "aceite", "similar", "parecid", "chirrido", "vibracion", "vibración",
    "roberto", "carlos", "abc", "listame", "listar", "lista las", "lista los",
    "cuant", "cuánt", "total de", "busca fallas", "buscar fallas", "crea cita",
    "crear cita", "agenda", "marca como", "marcar como", "cambia el estado",
    "cambiar estado", "pendiente", "proceso", "completada", "cancelada",
    "cancelar", "eliminar", "borrar", "editar", "actualizar", "modificar",
)

MUTATING_TOOLS = frozenset({
    "crear_cita_natural",
    "crear_cliente_natural",
    "crear_vehiculo_natural",
    "crear_servicio_natural",
    "crear_inventario_natural",
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


def is_create_cita_intent(question: str) -> bool:
    q = _norm(question)
    if not re.search(r"\b(crea|crear|creame|agenda|agendar|solicita|solicitar)\b", q):
        return False
    if re.search(
        r"\b(crea|crear|creame|registra|agrega)\b.*\b(cliente|vehiculo|vehículo|inventario|articulo|artículo|pieza|refaccion|refacción)\b",
        q,
    ):
        return False
    if re.search(r"\b(crea|crear|creame|registra|agrega)\s+(un\s+)?servicio\b", q) and "cita" not in q:
        return False
    if any(w in q for w in ("cita", "citas", "orden", "ordenes")):
        return True
    return bool(re.search(r"\b(crea|crear|creame)\s+(\d+|una?)\b", q))


def is_create_cliente_intent(question: str) -> bool:
    q = _norm(question)
    return bool(re.search(r"\b(crea|crear|creame|registra|agrega)\b.*\bcliente", q))


def is_create_vehiculo_intent(question: str) -> bool:
    q = _norm(question)
    return bool(re.search(r"\b(crea|crear|creame|registra|agrega)\b.*\b(vehiculo|vehículo|auto|carro)\b", q))


def is_create_servicio_intent(question: str) -> bool:
    q = _norm(question)
    return bool(
        re.search(r"\b(crea|crear|creame|registra|agrega)\s+(un\s+)?servicio\b", q)
        and "cita" not in q
    )


def is_create_inventario_intent(question: str) -> bool:
    q = _norm(question)
    return bool(
        re.search(r"\b(crea|crear|creame|registra|agrega)\b.*\b(inventario|articulo|artículo|pieza|refaccion|refacción|stock)\b", q)
    )


def _question_has_cliente_name(question: str) -> bool:
    q = _norm(question)
    return bool(
        re.search(r"\bpara\s+[a-z]", q)
        or re.search(r"\bcliente\s+[a-z]", q)
    )


def _question_has_falla_hint(question: str) -> bool:
    q = _norm(question)
    markers = (
        "falla", "freno", "frenos", "ruido", "problema", "no arranca",
        "aceite", "motor", "vibra", "chirrido", "servicio de", "reparar",
        "reparacion", "reparación", "chequeo", "mantenimiento",
    )
    return any(m in q for m in markers)


def is_incomplete_create_cita_request(question: str) -> bool:
    if not is_create_cita_intent(question):
        return False
    has_placa = bool(extract_placa_from_text(question))
    has_cliente = _question_has_cliente_name(question)
    has_falla = _question_has_falla_hint(question)
    if has_placa and has_falla:
        return False
    if has_cliente and has_placa:
        return not has_falla
    return True


def get_guided_create_cita_answer(
    question: str,
    *,
    es_propietario: bool = False,
    es_cliente: bool = False,
) -> str | None:
    if not is_incomplete_create_cita_request(question):
        return None

    if es_cliente:
        needed = ["placa de tu vehículo", "descripción de la falla"]
        intro = "Con gusto te agendo una cita. Necesito:\n\n"
        ejemplo = "\n\nEjemplo: agenda cita para mi placa ABC-123, falla: ruido en frenos."
    elif es_propietario:
        needed = ["nombre del cliente", "placa del vehículo", "descripción de la falla"]
        intro = "Te ayudo a crear la cita. Dime estos datos (puedes mandarlos poco a poco):\n\n"
        ejemplo = "\n\nEjemplo: crea cita para Juan Pérez, placa ABC-123, falla: ruido en frenos."
    else:
        needed = [
            "nombre del cliente",
            "placa del vehículo",
            "descripción de la falla",
            "mecánico",
            "isla o bahía",
        ]
        intro = "Para crear la cita necesito:\n\n"
        ejemplo = "\n\nEjemplo: crea cita para Juan Pérez, placa ABC-123, mecánico Carlos, isla 1, falla: ruido en frenos."

    return intro + "\n".join(f"- {item}" for item in needed) + ejemplo


def is_incomplete_create_cliente_request(question: str) -> bool:
    if not is_create_cliente_intent(question):
        return False
    q = _norm(question)
    return not re.search(r"\bcliente\s+[a-záéíóúñ]{2,}", q)


def is_incomplete_create_vehiculo_request(question: str) -> bool:
    if not is_create_vehiculo_intent(question):
        return False
    has_placa = bool(extract_placa_from_text(question))
    q = _norm(question)
    has_cliente = _question_has_cliente_name(question) or "mi auto" in q or "mi vehiculo" in q or "mi vehículo" in q
    if has_placa and has_cliente:
        return False
    return True


def is_incomplete_create_servicio_request(question: str) -> bool:
    if not is_create_servicio_intent(question):
        return False
    q = _norm(question)
    return not re.search(r"\bservicio\s+[a-záéíóúñ0-9]", q)


def is_incomplete_create_inventario_request(question: str) -> bool:
    if not is_create_inventario_intent(question):
        return False
    q = _norm(question)
    return not any(
        term in q
        for term in ("llamado", "llamada", "nombre", "de aceite", "de freno", "pieza ")
    ) and not re.search(r"\b(inventario|articulo|artículo|pieza)\s+[a-záéíóúñ]{3,}", q)


def get_guided_create_entity_answer(
    question: str,
    *,
    es_propietario: bool = False,
    es_cliente: bool = False,
) -> str | None:
    if is_incomplete_create_cliente_request(question):
        if es_cliente:
            return None
        return (
            "Te ayudo a registrar al cliente. Necesito:\n\n"
            "- Nombre completo\n"
            "- Teléfono (opcional)\n"
            "- Correo (opcional)\n\n"
            "Ejemplo: crea cliente Juan Pérez, teléfono 9991234567"
        )

    if is_incomplete_create_vehiculo_request(question):
        if es_cliente:
            return (
                "Registro tu vehículo. Dime:\n\n"
                "- Placa\n"
                "- Modelo (opcional)\n\n"
                "Ejemplo: registra mi vehículo placa ABC-123, modelo Corolla 2020"
            )
        return (
            "Te ayudo a registrar el vehículo. Necesito:\n\n"
            "- Placa\n"
            "- Cliente (nombre)\n"
            "- Modelo y marca (opcionales)\n\n"
            "Ejemplo: crea vehículo placa ABC-123 para Juan Pérez, modelo Aveo"
        )

    if is_incomplete_create_servicio_request(question):
        if es_cliente:
            return None
        return (
            "Creo el servicio en tu catálogo. Necesito:\n\n"
            "- Nombre del servicio\n"
            "- Precio (opcional)\n\n"
            "Ejemplo: crea servicio Cambio de aceite, precio 500"
        )

    if is_incomplete_create_inventario_request(question):
        if es_cliente:
            return None
        return (
            "Agrego el artículo al inventario de tu isla. Necesito:\n\n"
            "- Nombre del artículo\n"
            "- Cantidad (opcional)\n"
            "- Código o precio (opcionales)\n\n"
            "Ejemplo: agrega al inventario filtro de aceite, cantidad 10"
        )

    return None


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
    from services.user_roles import is_cliente, is_mecanico

    if is_cliente(rol_nombre):
        return CLIENTE_FALLBACK_ANSWER
    if is_mecanico(rol_nombre):
        return MECANICO_FALLBACK_ANSWER
    return FRIENDLY_FALLBACK_ANSWER


UNCLEAR_INPUT_ANSWER = """No entendí eso. Escríbelo en español claro.

Por ejemplo: lista las citas, crea un cliente, o ¿cuántos vehículos hay?"""


CLIENTE_UNCLEAR_ANSWER = """No entendí eso. Escríbelo en español claro.

Puedo ayudarte con tus citas o vehículos registrados."""


MECANICO_UNCLEAR_ANSWER = """No entendí eso. Escríbelo en español claro.

Dime qué necesitas: citas de tu sucursal, cambiar estado, o buscar una falla parecida."""


def get_unclear_input_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente, is_mecanico

    if is_cliente(rol_nombre):
        return CLIENTE_UNCLEAR_ANSWER
    if is_mecanico(rol_nombre):
        return MECANICO_UNCLEAR_ANSWER
    return UNCLEAR_INPUT_ANSWER


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

    orden_map = (
        (r"\bórdenes\b", "citas"),
        (r"\bordenes\b", "citas"),
        (r"\bórden\b", "cita"),
        (r"\borden\b", "cita"),
    )
    for pattern, replacement in orden_map:
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
        "creame cita", "crea cita", "creame 1 cita", "crea 1 cita",
        "crea cliente", "crear cliente", "registra cliente",
        "crea vehiculo", "crear vehiculo", "registra vehiculo",
        "crea servicio", "crear servicio", "agrega servicio",
        "crea inventario", "agrega inventario", "agregar inventario",
        "agenda una cita", "agendar cita", "marca como", "marcar como",
        "lista los", "lista las", "listar ", "listame", "cambia el estado",
        "buscar fallas", "busca fallas",
        "cancelar cita", "cancela cita", "eliminar cita", "elimina cita",
        "borrar cita", "borra cita", "editar cita", "edita cita",
        "actualizar cita", "actualiza cita", "modificar cita", "modifica cita",
    )
    if any(m in q for m in markers):
        return True
    if re.search(r"\b(crea|crear|creame)\s+(\d+|una?)\s*cita", q):
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
    if any(p in q for p in ("que hace", "qué hace")) and any(
        w in q for w in ("empresa", "taller", "iespro", "sistema")
    ):
        return False
    if not any(p in q for p in CAPABILITIES_PATTERNS):
        return False
    if q.strip() in ("ayuda", "help"):
        return True
    words = q.split()
    return len(words) <= 8


def is_casual_chat(question: str) -> bool:
    """Charla corta (¿qué haces?, ¿quién eres?) sin pedir el menú completo."""
    if _is_action_request(question) or looks_like_workshop_request(question):
        return False
    q = re.sub(r"[^a-z\s]", "", _norm(question)).strip()
    if not q:
        return False
    if any(p in q for p in CASUAL_CHAT_PATTERNS):
        return len(q.split()) <= 6
    return False


def get_casual_chat_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente

    if is_cliente(rol_nombre):
        return (
            "Soy tu asistente. Te ayudo con tus citas y vehículos. "
            "¿Qué necesitas?"
        )
    return (
        "Soy tu asistente. Te ayudo con citas, clientes, vehículos, servicios e inventario. "
        "¿Qué necesitas?"
    )


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


def looks_like_gibberish(question: str) -> bool:
    """Teclado al azar o texto sin intención reconocible: no debe ir al LLM."""
    raw = (question or "").strip()
    if not raw:
        return True
    if _is_action_request(raw) or looks_like_workshop_request(raw):
        return False
    if is_capabilities_question(raw) or is_greeting(raw) or is_acknowledgment(raw):
        return False
    if is_memory_recall_question(raw) or is_similarity_question(raw):
        return False
    if extract_placa_from_text(raw):
        return False

    q = _norm(raw)
    compact = re.sub(r"[^a-z]", "", q)
    if len(compact) < 3:
        return True

    known_gibberish = (
        "asdf", "asdfgh", "qwerty", "zxcv", "qweasdzxc", "quechqcea",
        "lol", "xd", "xdd", "kk",
    )
    if compact in known_gibberish:
        return True

    if re.search(r"jaja|jeje|jiji|haha", compact):
        return True
    if re.fullmatch(r"(.)\1{4,}", compact):
        return True

    if re.search(r"(cq|qx|xq|zq|jq|chq|qch|schw|qce|qcea|hqc)", compact):
        return True
    if re.search(r"[bcdfghjklmnpqrstvwxyz]{5,}", compact):
        return True

    words = q.split()
    if len(words) == 1 and len(compact) >= 7 and not looks_like_workshop_request(raw):
        vowels = sum(1 for c in compact if c in "aeiou")
        consonant_runs = re.findall(r"[bcdfghjklmnpqrstvwxyz]+", compact)
        max_run = max((len(run) for run in consonant_runs), default=0)
        if max_run >= 4:
            return True
        syllables = len(re.findall(r"[aeiou]+", compact))
        if syllables <= 3 and len(compact) >= 8:
            return True
        if vowels / len(compact) < 0.22:
            return True

    if len(words) >= 4 and not looks_like_workshop_request(raw):
        long_words = [w for w in words if len(w) >= 4 and re.search(r"[aeiou]", w)]
        if not long_words:
            return True

    return False


def looks_like_hallucinated_direct_answer(content: str) -> bool:
    """Respuesta larga inventada sin datos de herramientas."""
    text = (content or "").lower()
    if len(text) < 100:
        return False
    signals = (
        "cita 1",
        "cita 2",
        "cita 3",
        "abc-123",
        "mno-789",
        "balatas delanteras",
        "discos rayados",
        "ruido metálico al frenar",
        "ruido metalico al frenar",
        "necesito más información para darte",
        "necesito mas informacion para darte",
    )
    hits = sum(1 for signal in signals if signal in text)
    return hits >= 2


def is_casual_nonsense(question: str) -> bool:
    """Risa, texto random o charla sin tema del taller."""
    if looks_like_gibberish(question):
        return True
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

    return False


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
- ¿Cuántos artículos hay en inventario?

Historial de fallas parecidas:
- ¿Hay casos similares a ruido al frenar?

Acciones que ejecuto en el sistema:
- Te guío paso a paso para crear clientes, vehículos, servicios, inventario y citas.
- Crea cliente Juan Pérez, teléfono 9991234567
- Crea vehículo placa ABC-123 para Juan Pérez
- Crea servicio Cambio de aceite, precio 500
- Agrega al inventario filtro de aceite, cantidad 10
- Crea cita para Roberto García, placa ABC-123, falla: ruido en frenos
- Edita la cita de ABC-123: cambia el mecánico a Ana y la falla a vibración en volante
- Marca como completada la cita de la placa ABC-123
- Cancela (o elimina) la cita de la placa ABC-123 — queda inactiva, no se borra de la base

También puedo listar citas, clientes, vehículos, mecánicos, islas e inventario. Dime qué necesitas en español claro."""


CAPABILITIES_ANSWER_STAFF = """Como personal del taller puedo ayudarte así:

Consultas del taller completo:
- ¿Cuántas citas hay? ¿Cuántos clientes o vehículos?
- Fallas similares por placa, cliente o síntoma en todo el historial

Flujo por chat (te pido los datos que falten):
- Crea cliente → luego vehículo → luego cita, en el orden que quieras
- Ejemplo: Crea cliente María López, luego vehículo ABC-123 para María, luego cita con falla de frenos

Acciones en el sistema:
- Crear clientes, vehículos, servicios del catálogo, artículos de inventario y citas
- Editar o cancelar citas de cualquier placa
- Cambiar mecánico, isla, falla o estado de una cita
- Listar citas, clientes, vehículos, mecánicos, islas e inventario/stock de la isla activa

No uses "mi auto": actúa siempre con el nombre del cliente o la placa que te indiquen."""


def get_capabilities_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente, is_mecanico, is_staff_manager

    if is_staff_manager(rol_nombre):
        return CAPABILITIES_ANSWER_STAFF
    if is_cliente(rol_nombre):
        return CAPABILITIES_ANSWER_CLIENTE
    if is_mecanico(rol_nombre):
        return CAPABILITIES_ANSWER_MECANICO
    return CAPABILITIES_ANSWER


def get_greeting_answer(rol_nombre: str | None = None) -> str:
    from services.user_roles import is_cliente, is_mecanico, is_staff_manager

    if is_staff_manager(rol_nombre):
        return GREETING_ANSWER_STAFF
    if is_cliente(rol_nombre):
        return GREETING_ANSWER_CLIENTE
    if is_mecanico(rol_nombre):
        return GREETING_ANSWER_MECANICO
    return GREETING_ANSWER


CAPABILITIES_ANSWER_CLIENTE = """Puedo ayudarte con tus vehículos y citas:

- Registrar tu vehículo por chat (placa y modelo)
- Ver cuántas citas tienes o listar las tuyas
- Agendar cita con la placa de tu auto y la falla
- Cancelar una cita activa de tu vehículo
- Buscar fallas similares de tu placa

Ejemplo: registra mi vehículo placa ABC-123, modelo Corolla"""


GREETING_ANSWER_CLIENTE = """Hola. Soy tu asistente.

Puedo ayudarte con tus citas y vehículos.

Dime qué necesitas, por ejemplo: lista mis citas, o registra mi vehículo placa ABC-123."""


CAPABILITIES_ANSWER_MECANICO = """Como mecánico solo trabajo con TU historial en la sucursal activa:

- Listar o contar TUS citas asignadas
- Consultar inventario/stock de tu isla activa
- Buscar fallas similares en TUS reparaciones previas
- Cambiar estado / diagnóstico de una cita que te asignaron (por placa)

No puedo ver el trabajo de otros mecánicos ni datos de otras sucursales."""


GREETING_ANSWER_MECANICO = """Hola. Soy tu asistente.

Estás en modo mecánico: solo veo tu historial en esta sucursal.

Dime qué necesitas, por ejemplo: lista mis citas."""


MECANICO_FALLBACK_ANSWER = """No entendí bien eso.

Como mecánico solo puedo ayudarte con tu historial en esta sucursal.

Prueba con:
- Lista mis citas
- ¿Cuántas citas tengo pendientes?
- Fallas similares a ruido al frenar"""


GREETING_ANSWER_STAFF = """Hola. Soy tu asistente.

Puedo crear clientes, vehículos, servicios, inventario y citas; también consultar y buscar fallas.

Dime qué necesitas, por ejemplo: crea un cliente, o ¿cuántas citas hay?"""


GREETING_ANSWER = """Hola. Soy tu asistente.

Puedo ayudarte con citas, clientes, vehículos, servicios e inventario.

Dime qué necesitas, por ejemplo: ¿cuántas citas hay? o crea un cliente."""


FRIENDLY_FALLBACK_ANSWER = """No entendí bien eso, pero aquí estoy.

Soy tu asistente del taller. Puedo consultar datos, crear registros o buscar fallas parecidas.

Prueba con algo como:
- ¿Cuántas citas hay?
- Crea un cliente
- Crea vehículo placa ABC-123 para Juan Pérez"""


INVALID_INPUT_ANSWER = FRIENDLY_FALLBACK_ANSWER

ACKNOWLEDGMENT_ANSWER = """Listo. ¿Quieres que haga algo más?

Puedo crear otro cliente, vehículo, servicio, artículo de inventario o una cita."""
