"""Entrada de voz en tiempo real para el chat (Tkinter).

Transcripción por WebSocket local: el micrófono envía fragmentos de audio y el
servidor devuelve texto parcial mientras hablas. Al pulsar stop, el texto
ya transcrito se conserva en el cuadro de entrada.

Motores STT (por fragmento):
1. Whisper local (si openai-whisper + torch están instalados)
2. Google STT vía SpeechRecognition (requiere internet)
"""

from __future__ import annotations

import asyncio
import json
import threading
from typing import Callable

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHUNK_SECONDS = 1.0


def _whisper_available() -> bool:
    try:
        import torch  # noqa: F401
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def transcribe_from_microphone() -> tuple[bool, str]:
    """
    Graba audio del micrófono y transcribe a texto en español (modo bloqueante).
    Requiere: pip install SpeechRecognition pyaudio
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


def _transcribe_pcm(pcm: bytes, sample_rate: int = SAMPLE_RATE) -> str:
    if not pcm:
        return ""
    try:
        import speech_recognition as sr
    except ImportError:
        return ""

    recognizer = sr.Recognizer()
    audio = sr.AudioData(pcm, sample_rate, SAMPLE_WIDTH)

    if _whisper_available():
        try:
            text = recognizer.recognize_whisper(audio, model="base", language="es")
            return (text or "").strip()
        except Exception:
            pass

    try:
        text = recognizer.recognize_google(audio, language="es-ES")
        return (text or "").strip()
    except Exception:
        return ""


class RealtimeVoiceSession:
    """Sesión de voz con WebSocket local y transcripción en tiempo real."""

    def __init__(
        self,
        on_partial: Callable[[str], None],
        on_error: Callable[[str], None] | None = None,
        on_ready: Callable[[], None] | None = None,
    ):
        self._on_partial = on_partial
        self._on_error = on_error or (lambda _msg: None)
        self._on_ready = on_ready or (lambda: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._transcript = ""
        self._parts: list[str] = []

    @property
    def transcript(self) -> str:
        return self._transcript

    @property
    def active(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.active:
            return
        self._stop.clear()
        self._transcript = ""
        self._parts = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> str:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=8)
            self._thread = None
        return self._transcript

    def _run(self) -> None:
        try:
            asyncio.run(self._async_main())
        except Exception as exc:
            self._on_error(f"Error de voz: {exc}")

    async def _async_main(self) -> None:
        import websockets

        connected = asyncio.Event()

        async def ws_handler(websocket):
            connected.set()
            try:
                async for message in websocket:
                    if self._stop.is_set():
                        break
                    if isinstance(message, str):
                        try:
                            payload = json.loads(message)
                        except json.JSONDecodeError:
                            continue
                        if payload.get("type") == "stop":
                            break
                        continue
                    if not isinstance(message, (bytes, bytearray)):
                        continue
                    text = await asyncio.to_thread(_transcribe_pcm, bytes(message))
                    if text:
                        self._parts.append(text)
                        self._transcript = " ".join(self._parts)
                        await websocket.send(
                            json.dumps({"type": "partial", "text": self._transcript})
                        )
            except websockets.exceptions.ConnectionClosed:
                pass

        async with websockets.serve(ws_handler, "127.0.0.1", 0) as server:
            port = server.sockets[0].getsockname()[1]
            uri = f"ws://127.0.0.1:{port}"

            async with websockets.connect(uri) as ws:
                await connected.wait()
                self._on_ready()

                recv_task = asyncio.create_task(self._receive_partials(ws))
                capture_task = asyncio.create_task(self._capture_audio(ws))

                done, pending = await asyncio.wait(
                    [recv_task, capture_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)

                if not self._stop.is_set():
                    self._stop.set()
                try:
                    await ws.send(json.dumps({"type": "stop"}))
                except Exception:
                    pass

    async def _receive_partials(self, ws) -> None:
        import websockets

        try:
            async for message in ws:
                if not isinstance(message, str):
                    continue
                payload = json.loads(message)
                if payload.get("type") != "partial":
                    continue
                text = (payload.get("text") or "").strip()
                if text:
                    self._transcript = text
                    self._on_partial(text)
        except websockets.exceptions.ConnectionClosed:
            pass

    async def _capture_audio(self, ws) -> None:
        loop = asyncio.get_running_loop()

        def _capture_blocking() -> None:
            try:
                import speech_recognition as sr
            except ImportError:
                self._on_error(
                    "Voz no disponible. Instala SpeechRecognition y pyaudio."
                )
                return

            recognizer = sr.Recognizer()
            try:
                with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.35)
                    while not self._stop.is_set():
                        audio = recognizer.record(source, duration=CHUNK_SECONDS)
                        pcm = audio.get_raw_data(convert_rate=16000, convert_width=2)
                        if pcm and not self._stop.is_set():
                            asyncio.run_coroutine_threadsafe(ws.send(pcm), loop).result(timeout=5)
            except Exception as exc:
                if not self._stop.is_set():
                    self._on_error(f"No pude usar el micrófono: {exc}")

        await loop.run_in_executor(None, _capture_blocking)
