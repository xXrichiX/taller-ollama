"""Entrada de voz en tiempo real para el chat (Tkinter).

Transcripción por WebSocket local con Vosk (parciales mientras hablas).
Al pulsar stop, el texto ya transcrito se conserva en el cuadro de entrada.

Motores STT:
1. Vosk local en español (prioridad, sin internet, tiempo real)
2. Google STT vía SpeechRecognition (respaldo si falta el modelo Vosk)
"""

from __future__ import annotations

import asyncio
import json
import os
import struct
import threading
import time
import zipfile
from pathlib import Path
from typing import Callable
from urllib.request import urlretrieve

from config import (
    VOICE_RMS_CALIBRATION_S,
    VOICE_RMS_MIN,
    VOICE_RMS_MULTIPLIER,
    VOICE_RMS_OFFSET,
    VOICE_SILENCE_SECONDS,
)

SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
MIC_CHUNK = 4000
FALLBACK_CHUNK_BYTES = SAMPLE_RATE * SAMPLE_WIDTH
SILENCE_SECONDS = VOICE_SILENCE_SECONDS

MODEL_NAME = "vosk-model-small-es-0.42"
MODEL_URL = f"https://alphacephei.com/vosk/models/{MODEL_NAME}.zip"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_vosk_model = None
_vosk_model_lock = threading.Lock()


def _whisper_available() -> bool:
    try:
        import torch  # noqa: F401
        import whisper  # noqa: F401
        return True
    except ImportError:
        return False


def _download_vosk_model(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    zip_path = target.with_suffix(".zip")
    urlretrieve(MODEL_URL, zip_path)
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(target.parent)
    zip_path.unlink(missing_ok=True)


def _ensure_vosk_model_path() -> Path | None:
    env_path = os.environ.get("VOSK_MODEL_PATH", "").strip()
    if env_path:
        path = Path(env_path)
        if path.is_dir():
            return path

    model_path = MODELS_DIR / MODEL_NAME
    if model_path.is_dir():
        return model_path

    try:
        _download_vosk_model(model_path)
    except Exception:
        return None
    return model_path if model_path.is_dir() else None


def _get_vosk_model():
    global _vosk_model
    with _vosk_model_lock:
        if _vosk_model is not None:
            return _vosk_model
        model_path = _ensure_vosk_model_path()
        if model_path is None:
            return None
        try:
            from vosk import Model

            _vosk_model = Model(str(model_path))
        except Exception:
            return None
        return _vosk_model


class VoskStreamProcessor:
    """Procesa PCM en streaming y expone texto parcial y final."""

    def __init__(self) -> None:
        from vosk import KaldiRecognizer

        model = _get_vosk_model()
        if model is None:
            raise RuntimeError("Modelo Vosk no disponible")
        self._rec = KaldiRecognizer(model, SAMPLE_RATE)
        self._committed: list[str] = []
        self._last_sent = ""

    def feed(self, pcm: bytes) -> str | None:
        if not pcm:
            return None
        if self._rec.AcceptWaveform(pcm):
            result = json.loads(self._rec.Result())
            text = (result.get("text") or "").strip()
            if text:
                self._committed.append(text)
        partial = json.loads(self._rec.PartialResult()).get("partial", "").strip()
        parts = list(self._committed)
        if partial:
            parts.append(partial)
        full = " ".join(parts).strip()
        if full and full != self._last_sent:
            self._last_sent = full
            return full
        return None

    def finalize(self) -> str:
        final = json.loads(self._rec.FinalResult()).get("text", "").strip()
        if final:
            self._committed.append(final)
        return " ".join(self._committed).strip()


def _create_vosk_processor() -> VoskStreamProcessor | None:
    try:
        return VoskStreamProcessor()
    except Exception:
        return None


def _mic_error_message() -> str:
    return (
        "Voz no disponible. Instala: pip install sounddevice "
        "(incluido en requirements.txt). En Mac alternativa: brew install portaudio && pip install pyaudio"
    )


def _pcm_rms(pcm: bytes) -> float:
    if len(pcm) < 2:
        return 0.0
    count = len(pcm) // 2
    samples = struct.unpack(f"{count}h", pcm[: count * 2])
    if not samples:
        return 0.0
    mean_sq = sum(s * s for s in samples) / len(samples)
    return mean_sq**0.5


def _speech_threshold(ambient_rms: float) -> float:
    """Umbral dinámico: ruido ambiente calibrado + margen mínimo."""
    dynamic = ambient_rms * VOICE_RMS_MULTIPLIER + VOICE_RMS_OFFSET
    return max(VOICE_RMS_MIN, dynamic)


def _calibrate_ambient_rms(
    read_fn: Callable[[], bytes],
    stop_event: threading.Event,
    seconds: float = VOICE_RMS_CALIBRATION_S,
) -> float:
    """Mide ruido de fondo al iniciar (mediana RMS) para ajustar la puerta de ruido."""
    levels: list[float] = []
    deadline = time.monotonic() + max(0.15, seconds)
    while time.monotonic() < deadline and not stop_event.is_set():
        levels.append(_pcm_rms(read_fn()))
    if not levels:
        return VOICE_RMS_MIN * 0.4
    levels.sort()
    return levels[len(levels) // 2]


def _stream_mic_chunks(
    stop_event: threading.Event,
    on_chunk: Callable[[bytes], None],
    *,
    silence_seconds: float = 0,
    on_silence: Callable[[], None] | None = None,
    speech_threshold: float | None = None,
) -> bool:
    """Captura PCM del micrófono con puerta de ruido y detección de silencio."""
    last_voice_at = time.monotonic()
    had_voice = False
    gate = speech_threshold if speech_threshold is not None else VOICE_RMS_MIN

    def process_chunk(pcm: bytes) -> None:
        nonlocal last_voice_at, had_voice
        if _pcm_rms(pcm) >= gate:
            last_voice_at = time.monotonic()
            had_voice = True
            on_chunk(pcm)

    def silence_elapsed() -> bool:
        if not on_silence or silence_seconds <= 0 or not had_voice:
            return False
        return (time.monotonic() - last_voice_at) >= silence_seconds

    def read_loop(read_fn: Callable[[], bytes]) -> None:
        nonlocal gate
        ambient = _calibrate_ambient_rms(read_fn, stop_event)
        gate = _speech_threshold(ambient)
        while not stop_event.is_set():
            pcm = read_fn()
            if stop_event.is_set():
                break
            process_chunk(pcm)
            if silence_elapsed():
                on_silence()
                stop_event.set()
                break

    try:
        import sounddevice as sd

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=MIC_CHUNK,
        ) as stream:
            read_loop(lambda: bytes(stream.read(MIC_CHUNK)[0]))
        return True
    except ImportError:
        pass
    except Exception:
        pass

    try:
        import pyaudio

        pa = pyaudio.PyAudio()
        stream = None
        try:
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=MIC_CHUNK,
            )
            stream.start_stream()
            read_loop(lambda: stream.read(MIC_CHUNK, exception_on_overflow=False))
            return True
        finally:
            if stream is not None:
                stream.stop_stream()
                stream.close()
            pa.terminate()
    except ImportError:
        return False
    except Exception:
        return False


def _record_blocking(seconds: float = 12.0) -> bytes | None:
    try:
        import sounddevice as sd

        frames = int(seconds * SAMPLE_RATE)
        recording = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16")
        sd.wait()
        return recording.tobytes()
    except ImportError:
        pass
    except Exception:
        return None

    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=int(seconds))
        return audio.get_raw_data(convert_rate=SAMPLE_RATE, convert_width=2)
    except Exception:
        return None


def transcribe_from_microphone() -> tuple[bool, str]:
    """
    Graba audio del micrófono y transcribe a texto en español (modo bloqueante).
    Requiere: pip install sounddevice (o pyaudio en Mac)
    """
    try:
        import speech_recognition as sr
    except ImportError:
        return False, _mic_error_message()

    pcm = _record_blocking(12.0)
    if not pcm:
        return False, _mic_error_message()

    recognizer = sr.Recognizer()
    audio = sr.AudioData(pcm, SAMPLE_RATE, SAMPLE_WIDTH)

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
        on_silence_pause: Callable[[], None] | None = None,
        silence_seconds: float = SILENCE_SECONDS,
    ):
        self._on_partial = on_partial
        self._on_error = on_error or (lambda _msg: None)
        self._on_ready = on_ready or (lambda: None)
        self._on_silence_pause = on_silence_pause or (lambda: None)
        self._silence_seconds = silence_seconds
        self._silence_notified = False
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

        processor = await asyncio.to_thread(_create_vosk_processor)
        use_vosk = processor is not None
        if not use_vosk:
            self._on_error(
                "Modelo Vosk no encontrado; usando STT alternativo (más lento). "
                "Ejecuta la app con internet la primera vez para descargarlo."
            )

        connected = asyncio.Event()

        async def ws_handler(websocket):
            connected.set()
            fallback_buffer = bytearray()
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
                            if use_vosk and processor:
                                text = processor.finalize()
                                if text:
                                    self._transcript = text
                                    await websocket.send(
                                        json.dumps({"type": "partial", "text": text})
                                    )
                            break
                        continue
                    if not isinstance(message, (bytes, bytearray)):
                        continue

                    pcm = bytes(message)
                    text: str | None = None
                    if use_vosk and processor:
                        text = processor.feed(pcm)
                    else:
                        fallback_buffer.extend(pcm)
                        if len(fallback_buffer) >= FALLBACK_CHUNK_BYTES:
                            chunk = bytes(fallback_buffer)
                            fallback_buffer.clear()
                            piece = await asyncio.to_thread(_transcribe_pcm, chunk)
                            if piece:
                                self._parts.append(piece)
                                text = " ".join(self._parts)

                    if text:
                        self._transcript = text
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

                _done, pending = await asyncio.wait(
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
        await loop.run_in_executor(None, self._capture_blocking, ws, loop)

    def _capture_blocking(self, ws, loop) -> None:
        def send_pcm(pcm: bytes) -> None:
            asyncio.run_coroutine_threadsafe(ws.send(pcm), loop).result(timeout=2)

        def on_silence() -> None:
            if self._silence_notified or self._stop.is_set():
                return
            self._silence_notified = True
            self._on_silence_pause()

        try:
            ok = _stream_mic_chunks(
                self._stop,
                send_pcm,
                silence_seconds=self._silence_seconds,
                on_silence=on_silence,
            )
            if not ok and not self._stop.is_set():
                self._on_error(_mic_error_message())
        except Exception as exc:
            if not self._stop.is_set():
                self._on_error(f"No pude usar el micrófono: {exc}")
