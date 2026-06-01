"""Text-to-Speech con Piper (self-hosted, gratis, voz alemana)."""
import os
import subprocess
import tempfile

import config


def synthesize(text: str) -> bytes:
    """Convierte texto alemán a audio WAV (bytes)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = f.name
    try:
        subprocess.run(
            ["piper", "--model", config.PIPER_MODEL, "--output_file", out_path],
            input=text.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        with open(out_path, "rb") as fh:
            return fh.read()
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)
