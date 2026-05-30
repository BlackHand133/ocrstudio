"""FastAPI application entry point.

Serves the JSON API under ``/api`` and, when a built frontend is present at
``server/static``, serves the React SPA for everything else (single-container
deployment). Run with::

    uvicorn server.main:app --reload          # dev (frontend on Vite :5173)
    uvicorn server.main:app --host 0.0.0.0     # prod (serves built SPA too)
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from server.routers import (
    annotations,
    config,
    detect,
    export,
    images,
    jobs,
    versions,
    workspaces,
)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="OCR Studio", version="1.0.0")

# Dev convenience: the Vite dev server (5173) talks to this API directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional HTTP Basic auth: enabled only when OCR_USER + OCR_PASS are set.
# The browser handles the native login prompt and resends credentials, so the
# SPA needs no changes. /api/health is always open (for Docker HEALTHCHECK).
_AUTH_USER = os.environ.get("OCR_USER")
_AUTH_PASS = os.environ.get("OCR_PASS")


class BasicAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path == "/api/health":
            return await call_next(request)
        header = request.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pw = base64.b64decode(header[6:]).decode("utf-8").partition(":")
                if secrets.compare_digest(user, _AUTH_USER or "") and secrets.compare_digest(
                    pw, _AUTH_PASS or ""
                ):
                    return await call_next(request)
            except Exception:  # noqa: BLE001
                pass
        return StarletteResponse(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="OCR Studio"'},
        )


if _AUTH_USER and _AUTH_PASS:
    app.add_middleware(BasicAuthMiddleware)
    logging.getLogger("ocrstudio.server").info("HTTP Basic auth enabled")

for r in (workspaces, images, annotations, detect, export, versions, jobs, config):
    app.include_router(r.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ----------------------------------------------------------------------------
# Static SPA (only present in production / Docker image, after `npm run build`)
# ----------------------------------------------------------------------------
_STATIC = Path(__file__).resolve().parent / "static"

if (_STATIC / "index.html").exists():
    _assets = _STATIC / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        # Never shadow the API.
        if full_path.startswith("api/"):
            return FileResponse(_STATIC / "index.html", status_code=404)
        candidate = _STATIC / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_STATIC / "index.html")
