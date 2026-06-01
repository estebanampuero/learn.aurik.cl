FROM python:3.11-slim

# curl: healthcheck + descarga de la voz Piper. (Sin ffmpeg: el STT se delega
# a urgencias-er en este deploy, así que no se decodifica audio aquí.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Voces Piper: alemán (♂ Thorsten / ♀ Kerstin) + inglés (♂ Ryan / ♀ Amy).
# Cada idioma/género = un .onnx + su .onnx.json. Para agregar un idioma, suma su
# ruta aquí y la entrada correspondiente en langs.py.
RUN mkdir -p /app/voices && \
    B="https://huggingface.co/rhasspy/piper-voices/resolve/main" && \
    for v in \
      "de/de_DE/thorsten/medium/de_DE-thorsten-medium" \
      "de/de_DE/kerstin/low/de_DE-kerstin-low" \
      "en/en_US/ryan/medium/en_US-ryan-medium" \
      "en/en_US/amy/medium/en_US-amy-medium" ; do \
        name=$(basename "$v") && \
        curl -fsSL "$B/$v.onnx" -o "/app/voices/$name.onnx" && \
        curl -fsSL "$B/$v.onnx.json" -o "/app/voices/$name.onnx.json" ; \
    done

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
