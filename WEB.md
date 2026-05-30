# OCR Studio — Web Edition (FastAPI + React)

A browser-based rewrite of the desktop annotation tool. It reuses the existing
Qt-free core (`modules/`) behind a FastAPI backend and a React + react-konva
frontend, and ships as a **single Docker container** — no noVNC, no X server.

It is **100% data-compatible** with the desktop app: same `workspace.json` /
`v1.json` format and PaddleOCR export. Existing workspaces under `./workspaces`
open as-is.

> Status: **Phases 1–4.** Working: workspaces (create + image upload), image
> list (virtualized, thumbnails, search/filter, **per-image export selection**),
> canvas with **Box / Polygon / Mask** tools (select /
> move / corner-resize / zoom-pan), editable transcription + difficult flag,
> client-side undo/redo, **image rotation (0/90/180/270)**, save + auto-save,
> **OCR (single + batch with progress)**, **version control**
> (create / switch / delete), and **dataset export** in **selectable formats**
> (PaddleOCR det/rec · ICDAR-2015 · COCO · YOLO · CSV/JSONL) — train/val/test
> split, png/jpg, mask blackout, rotation-aware, **augmentation**, **auto
> text-orientation**, zip download, **background job with progress**), plus a
> **GPU Docker image**, light/dark
> **theme** + **Thai/English** UI, an optional **Basic-auth gate**, and a
> container **healthcheck**. Planned next: multi-user auth (future). See the
> plan file for the full roadmap.

## Run with Docker (recommended)

```bash
docker compose -f docker-compose.web.yml up --build
# open http://localhost:8000
```

If port 8000 is taken, pick another host port:

```bash
WEB_PORT=8088 docker compose -f docker-compose.web.yml up --build   # open http://localhost:8088
```

**GPU (CUDA 11.8 + PaddlePaddle-GPU)** — needs the NVIDIA Container Toolkit:

```bash
docker compose -f docker-compose.web.yml -f docker-compose.web.gpu.yml up --build
```

Data persists in the mounted host folders: `./workspaces`, `./models`, `./data`,
`./output_det`, `./output_rec`.

> First OCR call downloads PaddleOCR model weights (needs internet, or mount
> pre-downloaded weights into `./models`). Manual annotation works without them.

## Run locally for development

Two processes. Backend (any env with the project deps + the server deps):

```bash
pip install -r requirements.txt -r requirements-server.txt
uvicorn server.main:app --reload          # http://localhost:8000
```

Frontend (Vite dev server, proxies /api → :8000):

```bash
cd frontend
npm install
npm run dev                                # http://localhost:5173
```

Open **http://localhost:5173** during development.

## Run locally, production-like (no Docker)

```bash
cd frontend && npm run build               # outputs frontend/dist
# copy the build to where FastAPI serves it:
#   cp -r frontend/dist ../server/static    (Linux/macOS)
#   Copy-Item -Recurse frontend/dist ..\server\static   (PowerShell)
uvicorn server.main:app --host 0.0.0.0 --port 8000
# open http://localhost:8000  (FastAPI serves the SPA + /api on one port)
```

`server/main.py` serves `server/static/` automatically when it exists.

## Labeling: tools & keyboard

Tools: **Select · Box · Polygon · Censor/Mask** (solid / blur / pixelate). Toggle
the 🔒 next to the tool switch to keep a draw tool active (draw many shapes in a
row). Boxes with no transcription are outlined amber and tagged *no text*.

| Key | Action |
|---|---|
| `V` / `D` or `Q` / `P` / `M` | Select / Box / Polygon / Mask tool |
| `PgUp` / `PgDn` | Previous / next image (auto-saves first) |
| `↑` / `↓` (no selection) | Previous / next image |
| `↑↓←→` (box selected) | Nudge 1 px (`Shift` = 10 px) |
| `Tab` / `Shift+Tab` | Next / previous box **and focus its text field** |
| `Enter` or double-click | Finish polygon |
| `Ctrl+C / X / V` | Copy / cut / paste boxes |
| `Ctrl+D` | Duplicate selection |
| `Ctrl+A` | Select all boxes |
| `Shift+click` | Add / remove a box from the selection (bulk ops) |
| `Delete` / `Backspace` | Delete selection |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo |
| `Ctrl+S` | Save |
| `+` / `-` / `0` / `F` | Zoom in / out / 100% / fit |
| right-click polygon vertex | Delete that vertex |
| double-click polygon edge | Insert a vertex |

Panel actions: **sort by reading order** (top→bottom, left→right), **copy boxes
from the previous image** (repeated layouts), bulk **mark difficult** / **delete**
when multiple boxes are selected, and **convert any box ↔ censor**.

## Export formats

Choose a target format in the Export dialog (`dataset_format` in the API). All share
the same train/val/test split, PNG/JPG output, censor-mask burn-in and rotation:

| Format | Kind | Layout |
|---|---|---|
| `paddleocr` | det + rec | `labels_<split>.txt` (det) · `<split>.txt` + `images/<split>/*` crops (rec) |
| `icdar` | det | `<split>/images/` + `<split>/gt/gt_<img>.txt` — `x1,y1,…,x4,y4,transcription` (`###` = ignore) |
| `coco` | det | `<split>/images/` + `<split>/instances.json` — bbox + segmentation, single `text` category |
| `yolo` | det | `images/<split>/` + `labels/<split>/*.txt` (`0 cx cy w h` normalized) + `data.yaml` |
| `csv` | det + rec | `<split>.csv` — rec: `image,text` · det: `image,points,transcription,difficult` |
| `jsonl` | det + rec | `<split>.jsonl` — rec: `{image,text}` · det: `{image,width,height,boxes[]}` |

`icdar` / `coco` / `yolo` are detection-only (the API returns 400 for recognition, and the
UI disables it).

**Splitting** — percentage, fixed **count**, or **stratified** (balanced by box density for
detection / text length for recognition). Recognition can keep an image's crops in one split
(no train/val leakage). A **preview** (`POST .../export/preview`) returns per-split counts
before exporting.

**Augmentation** (works for every format) — pick augmentations + a mode (separate / combined)
and the number of randomized **copies per image**; parameters are jittered within ranges and
reproducible via the export `seed`. Geometric augments clamp boxes to the image bounds.

## Tests

Backend — web API round-trip (FastAPI `TestClient`, no GPU/Qt/paddle needed):

```bash
pip install -r requirements-test.txt       # lightweight: no paddle, no PyQt5
pytest tests/test_api_server.py -q
```

Frontend — Vitest unit tests (mask helpers, editor store undo/redo + selection
clamp, i18n `translate`):

```bash
cd frontend
npm run test                               # vitest run
```

CI runs all of the above on every push/PR via `.github/workflows/ci.yml`
(lint → core unit tests → web API tests → frontend build+test → CPU Docker
build on push).

## Optional: password-protect the server

For a shared/exposed deployment, set both env vars to require HTTP Basic auth on
every request except `/api/health` (the browser shows a native login prompt):

```bash
OCR_USER=admin OCR_PASS=secret \
  docker compose -f docker-compose.web.yml up -d
```

Leave either unset to keep the server open (the default, single-user local use).

## API (selected)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/config` | profiles (cpu/gpu) + languages |
| GET/POST | `/api/workspaces` | list / create |
| GET/DELETE | `/api/workspaces/{id}` | detail / delete |
| GET | `/api/workspaces/{id}/images` | list images (key, annotation count) |
| GET | `/api/workspaces/{id}/images/{key}/file` | serve image bytes |
| POST | `/api/workspaces/{id}/images/upload` | upload images |
| GET/PUT | `/api/workspaces/{id}/annotations/{key}` | load / save annotations |
| POST | `/api/workspaces/{id}/detect/{key}` | OCR a single image |
| POST | `/api/workspaces/{id}/detect` | batch OCR (scope empty/all/selected) → job |
| GET | `/api/jobs/{job_id}` | poll a background job's progress |
| GET/POST | `/api/workspaces/{id}/versions` | list / create version |
| POST | `/api/workspaces/{id}/versions/{name}/switch` | switch current version |
| DELETE | `/api/workspaces/{id}/versions/{name}` | delete a version |
| POST | `/api/workspaces/{id}/export` | export dataset (`kind` + `dataset_format`: paddleocr/icdar/coco/yolo/csv/jsonl) |
| GET | `/api/workspaces/{id}/export/{folder}/download` | download exported dataset as .zip |

Interactive docs at `/docs` (Swagger) when the server is running.
