# ============================================================
# Ajan OCR Annotation Tool — Multi-stage Dockerfile
#
# Targets:
#   builder       — installs Python dependencies (shared)
#   runtime-cpu   — GUI via noVNC + headless CLI  (CPU PaddlePaddle)
#   runtime-gpu   — same, with CUDA + PaddlePaddle-GPU
#
# Quick start (CPU GUI):
#   docker build --target runtime-cpu -t ajan-cpu .
#   docker run -e MODE=gui -p 6080:6080 -v ./workspaces:/app/workspaces ajan-cpu
#   # Open http://localhost:6080 in your browser
#
# Headless CLI:
#   docker run --rm ajan-cpu python -m modules.cli --help
# ============================================================

# ── 1. Builder ───────────────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /install

# System build deps (needed by some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (Docker layer cache)
COPY requirements.txt .

# Install CPU PaddlePaddle + remaining deps
RUN pip install --no-cache-dir paddlepaddle==2.6.0 \
 && pip install --no-cache-dir -r requirements.txt


# ── 2. runtime-cpu ───────────────────────────────────────────────────────────
FROM python:3.10-slim AS runtime-cpu

LABEL maintainer="Ajan OCR" \
      description="Ajan OCR Annotation Tool — CPU edition with noVNC browser GUI"

WORKDIR /app

# Runtime system packages:
#   libgl1, libglib2.0-0   → OpenCV
#   xvfb, x11vnc           → virtual display + VNC server
#   fluxbox                → lightweight window manager
#   websockify, novnc      → browser VNC (noVNC at port 6080)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libxkbcommon-x11-0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        xvfb \
        x11vnc \
        fluxbox \
        websockify \
        novnc \
        fonts-liberation \
        fonts-noto \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages \
                    /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . /app

# Create runtime directories (will be overlaid by volume mounts)
RUN mkdir -p /app/workspaces /app/models /app/data /app/logs /app/config

# Make entrypoint executable
RUN chmod +x /app/docker/entrypoint.sh

# noVNC browser access
EXPOSE 6080

# Persist annotations, models, config, and app state across runs
VOLUME ["/app/workspaces", "/app/models", "/app/config", "/app/data"]

ENV MODE=gui \
    QT_QPA_PLATFORM=xcb \
    DISPLAY=:99 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["/app/docker/entrypoint.sh"]


# ── 3. runtime-gpu ───────────────────────────────────────────────────────────
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 AS runtime-gpu

LABEL maintainer="Ajan OCR" \
      description="Ajan OCR Annotation Tool — GPU edition (CUDA 11.8)"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3-pip \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libxkbcommon-x11-0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        xvfb \
        x11vnc \
        fluxbox \
        websockify \
        novnc \
        fonts-liberation \
        fonts-noto \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/local/bin/python \
    && ln -sf /usr/bin/pip3 /usr/local/bin/pip

# Install GPU-enabled PaddlePaddle then remaining deps
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir paddlepaddle-gpu==2.6.0.post118 \
        -f https://www.paddlepaddle.org.cn/whl/linux/mkl/avx/stable.html \
 && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

RUN mkdir -p /app/workspaces /app/models /app/data /app/logs /app/config \
 && chmod +x /app/docker/entrypoint.sh

EXPOSE 6080
VOLUME ["/app/workspaces", "/app/models", "/app/config", "/app/data"]

ENV MODE=gui \
    QT_QPA_PLATFORM=xcb \
    DISPLAY=:99 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
