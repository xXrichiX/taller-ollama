"""Entrada de voz para el chat oficial (Tkinter).

Prioridad:
1. Whisper local (si openai-whisper + torch están instalados)
2. Google STT vía SpeechRecognition (alternativa ligera con internet)
"""

from __future__ import annotations


def _whisper_available() -> bool:
    try:
        import torch  # noqa: F401
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def transcribe_from_microphone() -> tuple[bool, str]:
    """
    Graba audio del micrófono y transcribe a texto en español.
    Requiere: pip install SpeechRecognition pyaudio
    Whisper opcional: pip install openai-whisper torch
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return False, (
            "Voz no disponible. Instala: pip install SpeechRecognition pyaudio "
            "(y brew install portaudio en Mac)"
        )

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=25)
    except sr.WaitTimeoutError:
        return False, "No escuché nada. Intenta de nuevo hablando más cerca del micrófono."
    except Exception as exc:
        return False, f"No pude acceder al micrófono: {exc}"

    if _whisper_available():
        try:
            text = recognizer.recognize_whisper(audio, model="base", language="es")
            cleaned = (text or "").strip()
            if cleaned:
                return True, cleaned
        except Exception as exc:
            # Si Whisper falla, intentamos alternativa ligera.
            fallback = _transcribe_google(recognizer, audio)
            if fallback[0]:
                return fallback
            return False, f"Whisper falló ({exc}). Instala torch o usa conexión a internet."

    return _transcribe_google(recognizer, audio)


def _transcribe_google(recognizer, audio) -> tuple[bool, str]:
    try:
        import speech_recognition as sr

        text = recognizer.recognize_google(audio, language="es-ES")
        cleaned = (text or "").strip()
        if not cleaned:
            return False, "No se detectó texto en el audio."
        return True, cleaned
    except sr.UnknownValueError:
        return False, "No entendí el audio. Habla más claro e intenta otra vez."
    except sr.RequestError as exc:
        return False, f"STT alternativo requiere internet: {exc}"
    except Exception as exc:
        return False, f"Error al transcribir: {exc}"
