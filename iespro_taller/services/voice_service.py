"""Entrada de voz en tiempo real para el chat (Tkinter).

Transcripción por WebSocket local con Vosk (parciales mientras hablas).
Al pulsar stop, el texto ya transcrito se conserva en el cuadro de entrada.

Motores STT:
1. Vosk local en español (prioridad, sin internet, tiempo real)
2. Google STT vía SpeechRecognition (respaldo si falta el modelo Vosk)
"""

from __future__ import annotations

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
        result = " ".join(self._committed).strip()
        if not result:
            partial = json.loads(self._rec.PartialResult()).get("partial", "").strip()
            if partial:
                result = partial
        return result


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
    preroll_chunks: int = 3,
) -> bool:
    """Captura PCM del micrófono.

    La puerta de ruido solo detecta inicio/fin de habla (como WhatsApp o ChatGPT).
    Todo el audio relevante se envía al motor STT; no se descartan trozos bajos
    en volumen, que era lo que truncaba palabras (p. ej. «hola» → «la»).
    """
    last_voice_at = time.monotonic()
    had_voice = False
    gate = speech_threshold if speech_threshold is not None else VOICE_RMS_MIN
    preroll: list[bytes] = []

    def is_speech(pcm: bytes) -> bool:
        return _pcm_rms(pcm) >= gate

    def flush_preroll() -> None:
        for buffered in preroll:
            on_chunk(buffered)
        preroll.clear()

    def process_chunk(pcm: bytes) -> None:
        nonlocal last_voice_at, had_voice
        if is_speech(pcm):
            if not had_voice:
                flush_preroll()
            had_voice = True
            last_voice_at = time.monotonic()
            on_chunk(pcm)
        elif had_voice:
            on_chunk(pcm)
        else:
            preroll.append(pcm)
            if len(preroll) > preroll_chunks:
                preroll.pop(0)

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
    """Sesión de voz: micrófono → Vosk en streaming con detección de silencio."""

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
        self._processor: VoskStreamProcessor | None = None
        self._processor_lock = threading.Lock()
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
        self._processor = None
        self._silence_notified = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> str:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=8)
            self._thread = None
        with self._processor_lock:
            if self._processor is not None:
                final = self._processor.finalize()
                if final:
                    self._transcript = final
        return self._transcript

    def _run(self) -> None:
        try:
            processor = _create_vosk_processor()
            if processor is None:
                self._on_error(
                    "Modelo Vosk no encontrado; usando STT alternativo (más lento). "
                    "Ejecuta la app con internet la primera vez para descargarlo."
                )
                self._run_fallback()
                return

            self._processor = processor
            self._on_ready()
            self._capture_with_processor(processor)
        except Exception as exc:
            self._on_error(f"Error de voz: {exc}")
        finally:
            self._stop.set()

    def _capture_with_processor(self, processor: VoskStreamProcessor) -> None:
        def on_chunk(pcm: bytes) -> None:
            if self._stop.is_set():
                return
            with self._processor_lock:
                text = processor.feed(pcm)
            if text:
                self._transcript = text
                self._on_partial(text)

        self._capture_loop(on_chunk)

    def _run_fallback(self) -> None:
        self._on_ready()
        fallback_buffer = bytearray()
        last_transcribe = 0.0

        def on_chunk(pcm: bytes) -> None:
            nonlocal last_transcribe
            if self._stop.is_set():
                return
            fallback_buffer.extend(pcm)
            now = time.monotonic()
            if len(fallback_buffer) < FALLBACK_CHUNK_BYTES:
                return
            if now - last_transcribe < 0.75:
                return
            chunk = bytes(fallback_buffer)
            fallback_buffer.clear()
            last_transcribe = now
            piece = _transcribe_pcm(chunk)
            if piece:
                self._parts.append(piece)
                text = " ".join(self._parts).strip()
                if text:
                    self._transcript = text
                    self._on_partial(text)

        self._capture_loop(on_chunk)

        if fallback_buffer and not self._stop.is_set():
            piece = _transcribe_pcm(bytes(fallback_buffer))
            if piece:
                self._parts.append(piece)
                text = " ".join(self._parts).strip()
                if text:
                    self._transcript = text

    def _capture_loop(self, on_chunk: Callable[[bytes], None]) -> None:
        def on_silence() -> None:
            if self._silence_notified or self._stop.is_set():
                return
            self._silence_notified = True
            self._on_silence_pause()

        ok = _stream_mic_chunks(
            self._stop,
            on_chunk,
            silence_seconds=self._silence_seconds,
            on_silence=on_silence,
        )
        if not ok and not self._stop.is_set():
            self._on_error(_mic_error_message())
