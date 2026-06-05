"""Convierte respuestas del modelo a texto plano para la UI (Tkinter no renderiza markdown)."""

import re


def plain_chat_text(text: str) -> str:
    if not text:
        return ""

    s = str(text)

    s = re.sub(r"```[\w]*\n?", "", s)
    s = s.replace("```", "")

    s = re.sub(r"^#{1,6}\s*", "", s, flags=re.MULTILINE)

    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"__(.+?)__", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", s, flags=re.DOTALL)
    s = re.sub(r"(?<!_)_(?!_)(.+?)(?<!_)_(?!_)", r"\1", s, flags=re.DOTALL)

    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)

    s = re.sub(r"^\s*[*\-•]\s+", "• ", s, flags=re.MULTILINE)

    s = s.replace("**", "").replace("__", "")

    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
