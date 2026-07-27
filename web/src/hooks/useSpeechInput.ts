import { useCallback, useEffect, useRef, useState } from "react";
import { transcribeSpeech } from "../api/client";

const SILENCE_MS = 2000;
const SILENCE_RMS = 0.012;
const PARTIAL_TRANSCRIBE_MS = 2500;

type SpeechRecognitionInstance = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
};

type SpeechRecognitionEvent = Event & {
  resultIndex: number;
  results: SpeechRecognitionResultList;
};

type SpeechRecognitionErrorEvent = Event & {
  error: string;
};

function getSpeechRecognitionCtor():
  | (new () => SpeechRecognitionInstance)
  | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & {
    SpeechRecognition?: new () => SpeechRecognitionInstance;
    webkitSpeechRecognition?: new () => SpeechRecognitionInstance;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function pickRecorderMimeType(): string | undefined {
  const types = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  return types.find((type) => MediaRecorder.isTypeSupported(type));
}

function secureContextError(): string {
  return "El micrófono requiere HTTPS. Abre el sitio con https:// (por ejemplo el dominio sslip.io).";
}

export function useSpeechInput(options: {
  onTranscript: (text: string) => void;
  onAutoSend: (text: string) => void;
  disabled?: boolean;
  authToken?: string | null;
}) {
  const { onTranscript, onAutoSend, disabled, authToken } = options;
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const wantListeningRef = useRef(false);
  const finalPartsRef = useRef<string[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  const onAutoSendRef = useRef(onAutoSend);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const silenceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasSpeechRef = useRef(false);
  const silenceStartedRef = useRef<number | null>(null);
  const usingServerRef = useRef(false);
  const partialBusyRef = useRef(false);
  const lastPartialAtRef = useRef(0);
  const latestPartialTextRef = useRef("");

  useEffect(() => {
    onTranscriptRef.current = onTranscript;
    onAutoSendRef.current = onAutoSend;
  }, [onTranscript, onAutoSend]);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const stopMediaCapture = useCallback(() => {
    if (silenceIntervalRef.current) {
      clearInterval(silenceIntervalRef.current);
      silenceIntervalRef.current = null;
    }
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    hasSpeechRef.current = false;
    silenceStartedRef.current = null;
    partialBusyRef.current = false;
    lastPartialAtRef.current = 0;
    latestPartialTextRef.current = "";
  }, []);

  const buildTranscript = useCallback((interim = "") => {
    const base = finalPartsRef.current.join(" ").trim();
    return `${base} ${interim}`.trim();
  }, []);

  const finishListening = useCallback(
    (autoSend: boolean) => {
      wantListeningRef.current = false;
      clearSilenceTimer();
      recognitionRef.current?.stop();
      setListening(false);

      const text = buildTranscript();
      finalPartsRef.current = [];
      if (autoSend && text) {
        onAutoSendRef.current(text);
      }
    },
    [buildTranscript, clearSilenceTimer],
  );

  const scheduleAutoSend = useCallback(() => {
    clearSilenceTimer();
    silenceTimerRef.current = setTimeout(() => {
      const text = buildTranscript();
      if (text) finishListening(true);
      else finishListening(false);
    }, SILENCE_MS);
  }, [buildTranscript, clearSilenceTimer, finishListening]);

  const transcribeBlob = useCallback(
    async (blob: Blob, autoSend: boolean) => {
      if (!blob.size) {
        setVoiceError("No se grabó audio. Intenta de nuevo.");
        return;
      }
      setTranscribing(true);
      if (!latestPartialTextRef.current) {
        onTranscriptRef.current("Transcribiendo…");
      }
      try {
        const text = await transcribeSpeech(blob, authToken);
        onTranscriptRef.current(text);
        if (autoSend && text) onAutoSendRef.current(text);
      } catch (err) {
        setVoiceError(err instanceof Error ? err.message : "No se pudo transcribir el audio.");
        onTranscriptRef.current("");
      } finally {
        setTranscribing(false);
      }
    },
    [authToken],
  );

  const finishMediaRecording = useCallback(
    async (autoSend: boolean) => {
      wantListeningRef.current = false;
      setListening(false);
      stopMediaCapture();

      const mimeType = mediaChunksRef.current[0]?.type || "audio/webm";
      const blob = new Blob(mediaChunksRef.current, { type: mimeType });
      mediaChunksRef.current = [];
      latestPartialTextRef.current = "";
      await transcribeBlob(blob, autoSend);
    },
    [stopMediaCapture, transcribeBlob],
  );

  const startServerListening = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setVoiceError("Tu navegador no permite acceso al micrófono.");
      return;
    }
    if (!window.isSecureContext) {
      setVoiceError(secureContextError());
      return;
    }

    setVoiceError("");
    mediaChunksRef.current = [];
    onTranscriptRef.current("");
    usingServerRef.current = true;
    partialBusyRef.current = false;
    lastPartialAtRef.current = 0;
    latestPartialTextRef.current = "";

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mimeType = pickRecorderMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) mediaChunksRef.current.push(event.data);
      };
      recorder.onerror = () => {
        setVoiceError("No se pudo grabar audio.");
        wantListeningRef.current = false;
        setListening(false);
        stopMediaCapture();
      };
      recorder.start(250);

      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);

      hasSpeechRef.current = false;
      silenceStartedRef.current = null;
      wantListeningRef.current = true;
      setListening(true);

      silenceIntervalRef.current = setInterval(() => {
        if (!wantListeningRef.current) return;
        const data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 1) {
          const sample = (data[i] - 128) / 128;
          sum += sample * sample;
        }
        const rms = Math.sqrt(sum / data.length);
        if (rms > SILENCE_RMS) {
          if (!hasSpeechRef.current) {
            onTranscriptRef.current("…");
          }
          hasSpeechRef.current = true;
          silenceStartedRef.current = null;

          const now = Date.now();
          if (
            mediaChunksRef.current.length > 0 &&
            !partialBusyRef.current &&
            now - lastPartialAtRef.current >= PARTIAL_TRANSCRIBE_MS
          ) {
            lastPartialAtRef.current = now;
            partialBusyRef.current = true;
            const mimeType = mediaChunksRef.current[0]?.type || "audio/webm";
            const blob = new Blob(mediaChunksRef.current, { type: mimeType });
            void transcribeSpeech(blob, authToken)
              .then((text) => {
                if (!wantListeningRef.current || !text) return;
                latestPartialTextRef.current = text;
                onTranscriptRef.current(text);
              })
              .catch(() => {
                /* sigue escuchando */
              })
              .finally(() => {
                partialBusyRef.current = false;
              });
          }
          return;
        }
        if (!hasSpeechRef.current) return;
        if (!silenceStartedRef.current) {
          silenceStartedRef.current = Date.now();
          return;
        }
        if (Date.now() - silenceStartedRef.current >= SILENCE_MS) {
          void finishMediaRecording(true);
        }
      }, 200);
    } catch (err) {
      usingServerRef.current = false;
      const denied = err instanceof DOMException && err.name === "NotAllowedError";
      setVoiceError(
        denied
          ? window.isSecureContext
            ? "Permite el micrófono en el navegador."
            : secureContextError()
          : "No se pudo usar el micrófono.",
      );
    }
  }, [authToken, finishMediaRecording, stopMediaCapture]);

  const startNativeListening = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return false;
    if (disabled) return true;

    setVoiceError("");
    finalPartsRef.current = [];
    onTranscriptRef.current("");
    usingServerRef.current = false;

    const recognition = new Ctor();
    recognition.lang = "es-MX";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const text = result[0]?.transcript ?? "";
        if (result.isFinal) {
          finalPartsRef.current.push(text.trim());
        } else {
          interim += text;
        }
      }
      onTranscriptRef.current(buildTranscript(interim));
      scheduleAutoSend();
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === "aborted" || event.error === "no-speech") return;
      if (event.error === "not-allowed") {
        setVoiceError(
          typeof window !== "undefined" && !window.isSecureContext
            ? secureContextError()
            : "Permite el micrófono en el navegador.",
        );
      } else {
        setVoiceError("No se pudo usar el micrófono.");
      }
      finishListening(false);
    };

    recognition.onend = () => {
      if (!wantListeningRef.current) {
        setListening(false);
        return;
      }
      try {
        recognition.start();
      } catch {
        setListening(false);
      }
    };

    recognitionRef.current = recognition;
    wantListeningRef.current = true;
    setListening(true);

    try {
      recognition.start();
    } catch {
      setVoiceError("No se pudo iniciar el micrófono.");
      wantListeningRef.current = false;
      setListening(false);
      return false;
    }
    return true;
  }, [buildTranscript, disabled, finishListening, scheduleAutoSend]);

  const startListening = useCallback(() => {
    if (disabled || transcribing) return;
    if (!window.isSecureContext) {
      setVoiceError(secureContextError());
      return;
    }
    const nativeStarted = startNativeListening();
    if (!nativeStarted) {
      void startServerListening();
    }
  }, [disabled, startNativeListening, startServerListening, transcribing]);

  const toggleListening = useCallback(() => {
    if (transcribing) return;
    if (listening) {
      if (usingServerRef.current) {
        void finishMediaRecording(Boolean(mediaChunksRef.current.length));
        return;
      }
      const text = buildTranscript();
      finishListening(Boolean(text));
      return;
    }
    startListening();
  }, [buildTranscript, finishListening, finishMediaRecording, listening, startListening, transcribing]);

  useEffect(
    () => () => {
      wantListeningRef.current = false;
      clearSilenceTimer();
      recognitionRef.current?.abort();
      stopMediaCapture();
    },
    [clearSilenceTimer, stopMediaCapture],
  );

  return {
    listening: listening || transcribing,
    voiceError,
    toggleListening,
    silenceSeconds: SILENCE_MS / 1000,
    clearVoiceError: () => setVoiceError(""),
  };
}
