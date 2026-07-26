import { useCallback, useEffect, useRef, useState } from "react";

const SILENCE_MS = 2000;

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

export function useSpeechInput(options: {
  onTranscript: (text: string) => void;
  onAutoSend: (text: string) => void;
  disabled?: boolean;
}) {
  const { onTranscript, onAutoSend, disabled } = options;
  const [listening, setListening] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const wantListeningRef = useRef(false);
  const finalPartsRef = useRef<string[]>([]);
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  const onAutoSendRef = useRef(onAutoSend);

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

  const buildTranscript = useCallback((interim = "") => {
    const base = finalPartsRef.current.join(" ").trim();
    const merged = `${base} ${interim}`.trim();
    return merged;
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

  const startListening = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) {
      if (typeof window !== "undefined" && !window.isSecureContext) {
        setVoiceError(
          "Abre el sitio con https:// (candado). Si el navegador advierte del certificado, elige Avanzado → Continuar.",
        );
      } else {
        setVoiceError("Usa Google Chrome o Microsoft Edge para dictar por voz.");
      }
      return;
    }
    if (disabled) return;

    setVoiceError("");
    finalPartsRef.current = [];
    onTranscriptRef.current("");

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
            ? "Abre https:// en la barra de direcciones y acepta el certificado del servidor."
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
    }
  }, [buildTranscript, disabled, finishListening, scheduleAutoSend]);

  const toggleListening = useCallback(() => {
    if (listening) {
      const text = buildTranscript();
      finishListening(Boolean(text));
      return;
    }
    startListening();
  }, [buildTranscript, finishListening, listening, startListening]);

  useEffect(
    () => () => {
      wantListeningRef.current = false;
      clearSilenceTimer();
      recognitionRef.current?.abort();
    },
    [clearSilenceTimer],
  );

  return {
    listening,
    voiceError,
    toggleListening,
    silenceSeconds: SILENCE_MS / 1000,
    clearVoiceError: () => setVoiceError(""),
  };
}
