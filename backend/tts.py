"""Text-to-Speech con Piper (self-hosted, gratis). Una voz .onnx por idioma/género."""
import os
import subprocess
import tempfile

import config


def synthesize(text: str, model_path: str = "") -> bytes:
    """Convierte texto a audio WAV (bytes) usando la voz `model_path`.

    Si no se entrega `model_path`, usa la voz por defecto (config.PIPER_MODEL).
    """
    model = model_path or config.PIPER_MODEL
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = f.name
    try:
        subprocess.run(
            ["piper", "--model", model, "--output_file", out_path],
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        with open(out_path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
