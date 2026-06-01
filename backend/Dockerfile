FROM python:3.11-slim

# curl: healthcheck + descarga de la voz Piper. (Sin ffmpeg: el STT se delega
# a urgencias-er en este deploy, así que no se decodifica audio aquí.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Voz alemana de Piper (Thorsten, medium)
RUN mkdir -p /app/voices && \
    BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium" && \
    curl -fsSL "$BASE/de_DE-thorsten-medium.onnx" -o /app/voices/de_DE-thorsten-medium.onnx && \
    curl -fsSL "$BASE/de_DE-thorsten-medium.onnx.json" -o /app/voices/de_DE-thorsten-medium.onnx.json

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
