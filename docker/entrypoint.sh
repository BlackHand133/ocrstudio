#!/bin/bash
# docker/entrypoint.sh
#
# Ajan OCR — container entry point
#
# MODE=gui       Start noVNC GUI session (accessible at http://localhost:6080)
# MODE=headless  Run the CLI tool directly (pass args after --)
#
# Examples:
#   docker run -e MODE=gui -p 6080:6080 ajan-cpu
#   docker run -e MODE=headless ajan-cpu python -m modules.cli detect --help

set -e

MODE="${MODE:-gui}"

case "$MODE" in
  gui)
    echo "[entrypoint] Starting GUI mode (noVNC on port 6080)..."

    # Virtual framebuffer
    Xvfb :99 -screen 0 1280x900x24 &
    export DISPLAY=:99
    sleep 1

    # Minimal window manager
    fluxbox &
    sleep 1

    # VNC server (no password for personal use; add -passwd /vnc_password for production)
    x11vnc -display :99 -forever -nopw -quiet -xkb &
    sleep 1

    # WebSocket bridge → noVNC serves at port 6080
    websockify --web /opt/novnc 6080 localhost:5900 &
    sleep 1

    echo "[entrypoint] GUI ready — open http://localhost:6080 in your browser"
    exec python main.py
    ;;

  headless)
    echo "[entrypoint] Starting headless CLI mode..."
    # Use JSON logging so log aggregators (e.g. docker logs, Fluentd) can parse lines
    export LOG_FORMAT=json
    exec "$@"
    ;;

  *)
    echo "[entrypoint] Unknown MODE='$MODE'. Use MODE=gui or MODE=headless."
    exit 1
    ;;
esac
