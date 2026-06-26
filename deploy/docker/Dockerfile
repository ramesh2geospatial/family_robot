# FamilyRobot – Development Dockerfile
# python:3.11-slim-bookworm + minimal deps for the core + web services.
# Audio adapter runs on host (container audio is blocked on most setups).

FROM python:3.11-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for OpenCV headless, audio libs (optional), and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install Python dependencies ─────────────────────────────────
COPY pyproject.toml ./
# Install in editable mode without the project itself first (cache layer)
RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir pyyaml pydantic fastapi uvicorn numpy \
    sentence-transformers pyttsx3 sqlite-vec

# ── Copy source ─────────────────────────────────────────────────
COPY packages/ packages/
COPY apps/ apps/
COPY config/ config/
COPY tests/ tests/

# Ensure data directory exists
RUN mkdir -p data models

# ── Expose ports ─────────────────────────────────────────────────
# 8080 = PWA web UI
# 1883 = MQTT (when broker is co-located)
EXPOSE 8080

# ── Health check ─────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

# ── Default entrypoint ───────────────────────────────────────────
# Start the PWA web server (the core voice loop runs on the host)
CMD ["uvicorn", "packages.core.webapp.app:app", "--host", "0.0.0.0", "--port", "8080"]
