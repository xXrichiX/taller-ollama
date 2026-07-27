#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="$ROOT/iespro_taller/models/vosk-model-small-es-0.42"
ZIP_URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"

if [ -d "$MODEL_DIR" ]; then
  echo "Modelo Vosk ya existe en $MODEL_DIR"
  exit 0
fi

mkdir -p "$ROOT/iespro_taller/models"
TMP_ZIP="$(mktemp /tmp/vosk-es.XXXXXX.zip)"
trap 'rm -f "$TMP_ZIP"' EXIT

echo "Descargando modelo Vosk en español (~40 MB)..."
curl -fsSL -o "$TMP_ZIP" "$ZIP_URL"
unzip -q "$TMP_ZIP" -d "$ROOT/iespro_taller/models"
echo "Listo: $MODEL_DIR"
