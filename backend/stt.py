"""Speech-to-Text. Reutiliza el Whisper del VPS de dos formas:
  - OPCIÓN B (STT_SERVICE_URL): llama a un servicio HTTP compartido (1 modelo en RAM).
  - OPCIÓN A: carga faster-whisper local, reusando el caché compartido (WHISPER_DOWNLOAD_ROOT).
"""
import config

_model = None  # singleton perezoso (solo opción A)


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel(
            config.WHISPER_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
            download_root=config.WHISPER_DOWNLOAD_ROOT,  # reusa el caché ya descargado
        )
    return _model


def transcribe(audio_path: str, language: str = "") -> str:
    """Transcribe audio a texto. `language` = código del idioma objetivo (de/en…).

    Whisper es multilingüe, así que basta con pasarle el código correcto. Si viene
    vacío se usa el default de config (STT_LANGUAGE).
    """
    lang = language or config.STT_LANGUAGE
    # OPCIÓN B: delegar a un servicio Whisper compartido (no carga modelo aquí).
    # Compatible con urgencias-er: POST /api/v1/transcribe (Bearer), responde {texto,...}.
    if config.STT_SERVICE_URL:
        import httpx
        headers = {}
        if config.STT_SERVICE_TOKEN:
            headers["Authorization"] = f"Bearer {config.STT_SERVICE_TOKEN}"
        with open(audio_path, "rb") as fh:
            files = {"audio": ("speech.webm", fh, "application/octet-stream")}
            r = httpx.post(
                config.STT_SERVICE_URL,
                files=files,
                data={"language": lang},
                headers=headers,
                timeout=120,
            )
        r.raise_for_status()
        data = r.json()
        return (data.get("texto") or data.get("text") or "").strip()

    # OPCIÓN A: faster-whisper local (caché compartido).
    segments, _info = _get_model().transcribe(audio_path, language=lang, vad_filter=True)
    return " ".join(seg.text for seg in segments).strip()
