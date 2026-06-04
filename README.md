# OCR Studio

[![CI](https://github.com/BlackHand133/ocrstudio/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackHand133/ocrstudio/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![React 18 + TS](https://img.shields.io/badge/React_18-TypeScript-61dafb.svg)](https://react.dev/)
[![PaddleOCR 3.x](https://img.shields.io/badge/PaddleOCR-3.x-green.svg)](https://github.com/PaddlePaddle/PaddleOCR)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://img.shields.io/github/v/release/BlackHand133/ocrstudio?label=release&color=brightgreen)](https://github.com/BlackHand133/ocrstudio/releases)
[![Container image](https://img.shields.io/badge/ghcr.io-ocrstudio-2496ED?logo=docker&logoColor=white)](https://github.com/BlackHand133/ocrstudio/pkgs/container/ocrstudio)

A **browser-based OCR annotation tool** for building high-quality text **detection** and
**recognition** datasets — with first-class **Thai** support. It pairs a FastAPI backend
(reusing a Qt-free core) with a React + `react-konva` frontend and ships as a **single Docker
container**: no noVNC, no X server — just open one URL.

> **Web edition (v5).** A full rewrite of the original PyQt5 desktop app, redesigned to be easy to
> use, fast, and deployable anywhere. It is **100% data-compatible** with the desktop tool — the same
> `workspace.json` / `v1.json` format and PaddleOCR export — so existing workspaces open as-is.
> The legacy desktop app still lives in this repo (see [below](#legacy-desktop-app)).

---

## Quick start (Docker — recommended)

### Option A — prebuilt image (fastest, no build)

Pull the published CPU image and run — no source build, no waiting on paddle wheels:

```bash
git clone https://github.com/BlackHand133/ocrstudio.git && cd ocrstudio
cp .env.example .env          # optional — set WEB_PORT, or OCR_USER/OCR_PASS for a login
docker compose -f docker-compose.web.pull.yml up -d
# open http://localhost:8000
```

Don't want to clone? Run it directly (creates data folders in the current directory):

```bash
docker run -d --name ocrstudio -p 8000:8000 \
  -v "$PWD/workspaces:/app/workspaces" -v "$PWD/models:/app/models" \
  -v "$PWD/data:/app/data" -v "$PWD/config:/app/config" \
  -v "$PWD/output_det:/app/output_det" -v "$PWD/output_rec:/app/output_rec" \
  ghcr.io/blackhand133/ocrstudio:latest
```

### Option B — build from source

```bash
git clone https://github.com/BlackHand133/ocrstudio.git && cd ocrstudio
docker compose -f docker-compose.web.yml up --build     # http://localhost:8000
```

Pick another host port if 8000 is taken (either option):

```bash
WEB_PORT=8088 docker compose -f docker-compose.web.pull.yml up -d   # http://localhost:8088
```

**GPU (CUDA 11.8 + PaddlePaddle-GPU)** — build from source; needs the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html):

```bash
docker compose -f docker-compose.web.yml -f docker-compose.web.gpu.yml up --build
```

**Share with others / remote access.** The app is **single-user** (no per-user login) — concurrent
editors share one dataset. To let teammates on your LAN reach it, expose the port and — recommended —
enable the built-in login by setting `OCR_USER` + `OCR_PASS` in `.env`. For internet access, put it
behind a tunnel or reverse proxy with HTTPS.

Data persists in mounted host folders: `./workspaces`, `./models`, `./data`, `./output_det`,
`./output_rec`. The first OCR call downloads PaddleOCR weights (or mount pre-downloaded weights into
`./models`); manual annotation works without them.

---

## Features

| Category | Details |
|---|---|
| **Annotation tools** | Box (quad), polygon, censor/mask (solid / blur / pixelate), text transcription, difficult flag |
| **Fast labeling** | Keyboard-driven workflow, multi-select (Shift-click + **rubber-band**), copy/paste & duplicate boxes, copy from previous image, sticky draw, reading-order sort, polygon vertex insert/delete, arrow-nudge, **magnifier loupe** |
| **Auto-detection** | PaddleOCR text detection + recognition — single image or **batch** with live progress |
| **Models** | Official PaddleOCR (per-language) or custom PaddleOCR **3.x** inference models |
| **Workspaces** | Multi-workspace, JSON version control (create / switch / delete) |
| **Export** | **Step-by-step wizard** (format → split → augment → review). **Selectable formats** (PaddleOCR · ICDAR-2015 · COCO · YOLO · CSV/JSONL); split by **percentage / fixed count / stratified** with a live split bar (incl. post-augment totals), image-grouped recognition split (no leakage); PNG/JPG, mask blackout, rotation-aware, **auto text-orientation**; **augmentation** with **per-effect adjustable parameters**, randomized copies, and a **zoomable preview gallery** (see every effect on a real sample before exporting); ZIP download — background job |
| **Image handling** | Upload or mounted folder, virtualized list + thumbnails (1000s of images), search/filter, rotation 0/90/180/270, relink-missing |
| **UX** | Light/dark theme, Thai/English UI, auto-save + unsaved-changes guard |
| **Ops** | CPU + NVIDIA GPU images, container healthcheck, optional HTTP Basic-auth gate |

---

## Labeling: tools & keyboard

Tools: **Select · Box · Polygon · Censor/Mask**. Toggle the 🔒 next to the tool switch to keep a draw
tool active (draw many shapes in a row). Boxes with no transcription are outlined amber and tagged
*no text*.

| Key | Action |
|---|---|
| `V` / `D` or `Q` / `P` / `M` | Select / Box / Polygon / Mask tool |
| `PgUp` / `PgDn` | Previous / next image (auto-saves first) |
| `↑` / `↓` (no selection) | Previous / next image |
| `↑↓←→` (box selected) | Nudge 1 px (`Shift` = 10 px) |
| `Tab` / `Shift+Tab` | Next / previous box **and focus its text field** |
| `Enter` or double-click | Finish polygon |
| `Ctrl+C / X / V` · `Ctrl+D` | Copy / cut / paste · duplicate boxes |
| `Ctrl+A` | Select all · `Shift+click` adds/removes a box |
| `Delete` / `Backspace` | Delete selection |
| `Ctrl+Z` / `Ctrl+Y` · `Ctrl+S` | Undo / redo · save |
| `+` / `-` / `0` / `F` | Zoom in / out / 100% / fit |
| right-click polygon vertex · double-click edge | Delete / insert a vertex |

Panel actions: **sort by reading order**, **copy boxes from the previous image**, bulk
**mark difficult** / **delete**, and **convert any box ↔ censor**.

---

## Architecture

```
Browser (React 18 + TS, Vite, Mantine, react-konva, Zustand, TanStack Query)
   │  HTTP / JSON  (+ polling for batch jobs)
FastAPI (server/) ── serves the built SPA + /api on one port
   │  imports (reuse, no Qt)
modules/  ── workspace manager · PaddleOCR detector · config · export utils · augmentation
```

- **Single container**: Node builds the SPA → Python serves the SPA **and** the API on one port.
- **Backend** (`server/`): routers for workspaces, images, annotations, versions, detect, export,
  config, jobs; an in-memory job registry powers async batch OCR + export with progress polling.
- **Frontend** (`frontend/`): 3-pane editor (image list · canvas · annotation panel).

See **[docs/WEB.md](docs/WEB.md)** for the full run guide, API reference, and details.

### Data compatibility

The backend reads/writes through the original `WorkspaceManager`, so the on-disk format is identical
to the desktop app:

- `workspaces/<id>/workspace.json` — metadata, source folder, versions, settings
- `workspaces/<id>/v1.json` — `annotations`, `transforms` (rotation), `metadata`
- Dataset export — train/val/test split label files (PaddleOCR, plus the formats below)

> Custom recognition/detection models must be **PaddleOCR 3.x** inference models
> (`inference.json` + `inference.pdiparams` + `inference.yml`). Models exported from 2.x must be
> re-exported. Mount them under `./models`.

### Export formats

Pick a target format in the Export **wizard** (step 1). All share the same
train/val/test split, PNG/JPG output, censor-mask burn-in and rotation handling:

| Format | Kind | Output |
|---|---|---|
| **PaddleOCR** | det + rec | `labels_<split>.txt` (det) · `<split>.txt` + cropped lines (rec) |
| **ICDAR-2015** | det | `<split>/images/` + `<split>/gt/gt_<img>.txt` (`x1,y1,…,x4,y4,transcription`) |
| **COCO** | det | `<split>/images/` + `instances.json` (bbox + segmentation, single `text` category) |
| **YOLO** | det | `images/<split>/` + `labels/<split>/*.txt` (`0 cx cy w h` normalized) + `data.yaml` |
| **CSV / JSONL** | det + rec | per-split manifest (`image,text` · `{image,width,height,boxes}`) |

ICDAR / COCO / YOLO are detection-only. **Augmentation** — blur, noise,
brightness/contrast, sharpen, rotate, perspective, color, shear, random-erase,
each with adjustable parameters — applies to **every detection format** and to
recognition crops, and is added only to the target split(s). Preview each effect
(or all at once) on a real sample, zoom in, and flip between sample images before
exporting.

---

## Local development

Two processes. Backend (any env with the project + server deps):

```bash
pip install -r requirements.txt -r requirements-server.txt
uvicorn server.main:app --reload          # http://localhost:8000
```

Frontend (Vite dev server, proxies `/api` → `:8000`):

```bash
cd frontend
npm install
npm run dev                                # http://localhost:5173
```

---

## Tests & CI

```bash
# Backend — web API round-trip (FastAPI TestClient, no GPU/Qt/paddle needed)
pip install -r requirements-test.txt
pytest tests/test_api_server.py -q

# Frontend — Vitest unit tests
cd frontend && npm run test
```

CI (`.github/workflows/ci.yml`) runs on every push/PR: backend lint + core unit tests + web API
tests, frontend build + Vitest, and a CPU Docker build on push.

### Optional: password-protect the server

Set both env vars to require HTTP Basic auth on every request except `/api/health`:

```bash
OCR_USER=admin OCR_PASS=secret docker compose -f docker-compose.web.yml up -d
```

Leave either unset to keep the server open (the default for single-user local use).

---

## Legacy desktop app

The original PyQt5 desktop application is still in the repo and unchanged:

```bash
pip install -r requirements.txt
python main.py
```

A headless CLI (`python -m modules.cli`) and the noVNC Docker setup (`Dockerfile`,
`docker-compose.yml`) remain available. New work targets the web edition above.

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR engine
- [FastAPI](https://fastapi.tiangolo.com/) · [React](https://react.dev/) · [Mantine](https://mantine.dev/) · [react-konva](https://konvajs.org/docs/react/) — web stack
- [OpenCV](https://opencv.org/) — image processing
