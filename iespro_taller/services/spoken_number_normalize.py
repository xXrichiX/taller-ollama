"""Convierte números hablados en español a dígitos (p. ej. mil cuatrocientos → 1400)."""

from __future__ import annotations

import re
import unicodedata

_STT_NUMBER_TYPOS = (
    (r"\bcuatrociones\b", "cuatrocientos"),
    (r"\bcuatrocione\b", "cuatrocientos"),
    (r"\bmil\s+cuatrociones\b", "mil cuatrocientos"),
    (r"\bdos\s+mil\b", "dos mil"),
)

_UNITS = {
    "cero": 0,
    "un": 1,
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20,
    "veintiuno": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
}

_HUNDREDS = {
    "cien": 100,
    "ciento": 100,
    "doscientos": 200,
    "doscientas": 200,
    "trescientos": 300,
    "trescientas": 300,
    "cuatrocientos": 400,
    "cuatrocientas": 400,
    "quinientos": 500,
    "quinientas": 500,
    "seiscientos": 600,
    "seiscientas": 600,
    "setecientos": 700,
    "setecientas": 700,
    "ochocientos": 800,
    "ochocientas": 800,
    "novecientos": 900,
    "novecientas": 900,
}

_MAGNITUDE = {
    "mil": 1_000,
    "millon": 1_000_000,
    "millones": 1_000_000,
}

_NUMBER_WORDS = set(_UNITS) | set(_HUNDREDS) | set(_MAGNITUDE) | {"y"}


def _norm_token(word: str) -> str:
    text = unicodedata.normalize("NFD", (word or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.strip()


def _parse_number_tokens(tokens: list[str]) -> int | None:
    total = 0
    current = 0

    for raw in tokens:
        tok = _norm_token(raw)
        if not tok or tok == "y":
            continue
        if tok in _MAGNITUDE:
            if current == 0:
                current = 1
            current *= _MAGNITUDE[tok]
            if _MAGNITUDE[tok] >= 1_000:
                total += current
                current = 0
            continue
        if tok in _HUNDREDS:
            current += _HUNDREDS[tok]
            continue
        if tok in _UNITS:
            current += _UNITS[tok]
            continue
        return None

    return total + current


def _fix_stt_number_typos(text: str) -> str:
    out = text
    for pattern, replacement in _STT_NUMBER_TYPOS:
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


def _replace_spoken_numbers_in_text(text: str) -> str:
    if not text or not text.strip():
        return text

    parts = re.split(r"(\s+)", text)
    result: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if not part or part.isspace():
            result.append(part)
            i += 1
            continue

        if _norm_token(part) not in _NUMBER_WORDS:
            result.append(part)
            i += 1
            continue

        number_tokens: list[str] = []
        j = i
        while j < len(parts):
            piece = parts[j]
            if not piece:
                j += 1
                continue
            if piece.isspace():
                k = j + 1
                while k < len(parts) and (not parts[k] or parts[k].isspace()):
                    k += 1
                if k < len(parts) and _norm_token(parts[k]) in _NUMBER_WORDS:
                    j = k
                    continue
                break
            if _norm_token(piece) in _NUMBER_WORDS:
                number_tokens.append(piece)
                j += 1
                continue
            break

        value = _parse_number_tokens(number_tokens)
        if value is not None and number_tokens:
            result.append(str(value))
            if j < len(parts) and parts[j].isspace():
                result.append(parts[j])
                j += 1
            i = j
        else:
            result.append(part)
            i += 1

    return "".join(result)


def normalize_spoken_numbers(text: str) -> str:
    """Convierte frases numéricas en español a dígitos sin alterar el resto del texto."""
    if not text:
        return text
    cleaned = _fix_stt_number_typos(text)
    return _replace_spoken_numbers_in_text(cleaned)
