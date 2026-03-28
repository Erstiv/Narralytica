FROM python:3.12-slim

WORKDIR /app

# System deps: FFmpeg for compression/media extraction
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python deps for the pipeline
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic \
    "scenedetect[opencv]" \
    faster-whisper \
    rapidfuzz \
    google-genai

COPY . .

EXPOSE 8006

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8006"]
