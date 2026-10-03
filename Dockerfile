# Dockerfile for deploying the pipeline backend to Render (or any Docker host).
# Render's Starter tier (1GB RAM) runs Whisper + pyannote fine.

FROM python:3.11-slim

# ffmpeg is required for audio decoding (both Whisper and our manual
# ffmpeg-based waveform loading for pyannote).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render assigns its own port at runtime via the PORT env var (it varies,
# not always 7860) - the shell-form CMD below reads whatever Render sets,
# falling back to 7860 for local Docker testing.
EXPOSE 7860
CMD uvicorn server:app --host 0.0.0.0 --port ${PORT:-7860}
