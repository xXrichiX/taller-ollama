"""Transcripción de voz en el servidor (compatible con cualquier navegador)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_model = None
_MODEL_DIRNAME = "vosk-model-small-es-0.42"


def _model_candidates() -> list[Path]:
    env_path = (os.getenv("VOSK_MODEL_PATH") or "").strip()
    project_root = Path(__file__).resolve().parent.parent
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    candidates.extend([
        project_root / "models" / _MODEL_DIRNAME,
        Path("/models") / _MODEL_DIRNAME,
    ])
    return candidates


def resolve_model_path() -> Path | None:
    for path in _model_candidates():
        if path.is_dir():
            return path
    return None


def speech_available() -> bool:
    return resolve_model_path() is not None


def _get_model():
    global _model
    if _model is None:
        from vosk import Model

        path = resolve_model_path()
        if not path:
            searched = ", ".join(str(p) for p in _model_candidates())
            raise RuntimeError(
                f"Modelo Vosk no encontrado. Descárgalo con: "
                f"bash scripts/download-vosk-model.sh (buscado en: {searched})"
            )
        _model = Model(str(path))
    return _model


def is_allowed_audio_payload(data: bytes) -> bool:
    """Valida magic bytes de contenedores de audio comunes."""
    if len(data) < 12:
        return False
    head = data[:12]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return True
    if head[:4] == b"OggS":
        return True
    if head[:4] == b"\x1aE\xdf\xa3":
        return True
    if b"ftyp" in head[:8]:
        return True
    return False


def transcribe_audio(data: bytes) -> dict:
    """Convierte audio (webm/ogg/mp4/wav) a texto en español."""
    if not data:
        return {"ok": False, "error": "Audio vacío."}
    if len(data) > 5 * 1024 * 1024:
        return {"ok": False, "error": "Audio demasiado largo (máx. 5 MB)."}
    if not is_allowed_audio_payload(data):
        return {"ok": False, "error": "Formato de audio no permitido."}

    if not speech_available():
        return {
            "ok": False,
            "error": (
                "La transcripción por voz no está configurada en este servidor. "
                "Ejecuta: bash scripts/download-vosk-model.sh "
                "o escribe tu mensaje con el teclado."
            ),
        }

    try:
        model = _get_model()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

    with tempfile.TemporaryDirectory() as tmp:
        inp = Path(tmp) / "input.bin"
        wav = Path(tmp) / "audio.wav"
        inp.write_bytes(data)

        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-protocol_whitelist",
                "file,pipe",
                "-y",
                "-i",
                str(inp),
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                str(wav),
            ],
            capture_output=True,
            timeout=45,
        )
        if proc.returncode != 0 or not wav.is_file():
            return {"ok": False, "error": "No se pudo procesar el audio (¿ffmpeg instalado?)."}

        import wave

        from vosk import KaldiRecognizer

        with wave.open(str(wav), "rb") as wf:
            rec = KaldiRecognizer(model, wf.getframerate())
            parts: list[str] = []
            while True:
                chunk = wf.readframes(4000)
                if not chunk:
                    break
                if rec.AcceptWaveform(chunk):
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        parts.append(result["text"])
            final = json.loads(rec.FinalResult())
            if final.get("text"):
                parts.append(final["text"])

        text = " ".join(parts).strip()
        if not text:
            return {"ok": False, "error": "No se detectó voz. Intenta de nuevo."}
        return {"ok": True, "text": text}
