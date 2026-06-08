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


def is_memory_recall_question(question: str) -> bool:
    q = _norm(question)
    patterns = (
        "recuerdas", "recuerda lo", "conversacion anterior", "charla anterior",
        "lo que te dije", "lo que dije", "hablamos antes", "mencione antes",
        "mencioné antes", "en la otra conversacion", "otra conversacion",
    )
    return any(p in q for p in patterns)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower().strip()


def is_capabilities_question(question: str) -> bool:
    q = _norm(question)
    return any(p in q for p in CAPABILITIES_PATTERNS)


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


INVALID_INPUT_ANSWER = """No entendí tu mensaje.

Por favor escribe en español algo sobre el taller. Por ejemplo:
- ¿Cuántas citas hay?
- Lista los clientes
- ¿Hay fallas parecidas a vibración en frenos?
- Crea una cita para Roberto García, placa ABC-123, mecánico Carlos, isla 1, falla: ruido al frenar

Si quieres saber qué puedo hacer, pregúntame: ¿Qué puedes hacer?"""
