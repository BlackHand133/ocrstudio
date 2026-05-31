# Architecture

This document describes the internal structure of the Ajan OCR Annotation Tool, the reasoning
behind key design decisions, and how the major subsystems interact.

---

## Table of Contents

1. [High-level overview](#1-high-level-overview)
2. [Module structure](#2-module-structure)
3. [AppState and the signal/slot data-flow](#3-appstate-and-the-signalslot-data-flow)
4. [Handler pattern (Dependency Injection)](#4-handler-pattern-dependency-injection)
5. [Config system](#5-config-system)
6. [Workspace and version model](#6-workspace-and-version-model)
7. [Undo/Redo (Command pattern)](#7-undoredo-command-pattern)
8. [CLI entry point](#8-cli-entry-point)
9. [Docker layout](#9-docker-layout)
10. [Testing strategy](#10-testing-strategy)

---

## 1. High-level overview

```
┌─────────────────────────────────────────────────────────────┐
│  GUI layer  (modules/gui/)                                  │
│  ┌─────────────┐   ┌───────────────────┐   ┌────────────┐  │
│  │ MainWindow  │──▶│   Handlers (DI)   │──▶│  Dialogs   │  │
│  │ (coord.)    │   │  annotation       │   │  settings  │  │
│  └──────┬──────┘   │  detection        │   │  workspace │  │
│         │signals   │  clipboard, …     │   └────────────┘  │
│  ┌──────▼──────┐   └────────┬──────────┘                   │
│  │ UICoordinator│           │read/write                     │
│  └─────────────┘           │                               │
└────────────────────────────┼────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Core layer  (modules/core/)                                │
│  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ AppState │  │ Services │  │  Workspace  │  │  Undo/  │ │
│  │(QObject) │  │(dataclass│  │  Manager    │  │  Redo   │ │
│  └──────────┘  │ DI cont.)│  └─────────────┘  └─────────┘ │
│                └──────────┘                                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  OCR  (modules/core/ocr/)                            │   │
│  │  TextDetector  +  TextlineOrientationClassifier      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  Support layers                                             │
│  modules/config/    ConfigManager singleton (YAML profiles) │
│  modules/utils/     file_io, validation, image helpers      │
│  modules/export/    PaddleOCR format exporters             │
│  modules/data/      Augmentation, preprocessing            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Module structure

```
modules/
├── cli.py                   # Headless CLI — no Qt imports allowed here
├── constants.py             # All magic strings, paths, UI constants
├── __version__.py           # Single source-of-truth version string
│
├── config/
│   ├── manager.py           # ConfigManager singleton
│   └── (profiles loaded from config/profiles/*.yaml)
│
├── core/
│   ├── app_state.py         # AppState — QObject with pyqtSignals
│   ├── services.py          # Services dataclass (workspace_manager, detector, undo_manager)
│   ├── undo_redo.py         # UndoRedoManager + Command ABC
│   ├── ocr/
│   │   ├── detector.py      # TextDetector (PaddleOCR wrapper)
│   │   └── orientation.py   # TextlineOrientationClassifier (PP-LCNet)
│   └── workspace/
│       ├── storage.py       # File I/O: atomic JSON writes, path helpers
│       ├── version.py       # VersionManager: create/switch/delete versions
│       └── manager.py       # WorkspaceManager: high-level workspace CRUD
│
├── data/                    # Augmentation, image transforms
├── export/                  # Export formatters (PaddleOCR Label.txt, etc.)
│
├── gui/
│   ├── main_window.py       # Coordinator only (≤ 600 lines, no business logic)
│   ├── ui_coordinator.py    # Subscribes to AppState signals → updates widgets
│   ├── handlers/            # Event handlers — each has its own file
│   │   ├── annotation.py    # Add/delete/modify annotations
│   │   ├── detection.py     # Run PaddleOCR auto-detection
│   │   ├── clipboard.py     # Copy/paste annotations
│   │   ├── rotation.py      # Image rotation
│   │   ├── table.py         # Image-list table updates
│   │   └── image.py         # Image loading, scanning
│   ├── dialogs/             # Modal dialogs (settings, workspace, export, …)
│   └── items/               # QGraphicsItem subclasses (QuadItem, PolygonItem, …)
│
└── utils/
    ├── file_io.py           # imread_unicode, imwrite_unicode (Unicode path support)
    ├── validation.py        # sanitize_annotation, sanitize_filename
    ├── image.py             # resize, crop, colour-space helpers
    └── decorators.py        # @require_workspace, @require_image Qt decorators
```

---

## 3. AppState and the signal/slot data-flow

`AppState` (`modules/core/app_state.py`) is the single source of truth for all mutable
business data. It is a `QObject` so it can emit Qt signals.

```
 Handler mutates AppState            UICoordinator reacts
 ─────────────────────────────────   ─────────────────────────────────
 state.set_current_image(key, path)  current_image_changed → reload canvas
 state.set_annotations(key, anns)    annotations_changed   → redraw boxes
 state.set_image_items(items)        images_loaded          → repopulate table
 state.set_draw_mode(True)           mode_changed           → update toolbar
 state.set_filter("annotated")       filter_changed         → filter table rows
```

**Design rules:**

- `AppState` holds **data only** — no widgets, no I/O.
- Handlers call **setter methods** (e.g. `set_annotations`) to mutate state and emit signals.
- Direct attribute assignment (`state.annotations[key] = …`) is allowed only inside batch
  updates that are followed by an explicit signal emit.
- UI components (`UICoordinator`, dialogs) are connected to signals — they never poll.

---

## 4. Handler pattern (Dependency Injection)

All handlers follow the same constructor signature:

```python
class AnnotationHandler:
    def __init__(self, state: AppState, services: Services) -> None:
        self.state    = state
        self.services = services
```

`MainWindow` creates one instance of each handler and wires up menu/button signals.

**Benefits:**
- Handlers can be instantiated in `pytest` without a `QApplication` (the handlers themselves
  do not import `PyQt5` at module level — they receive the state and services objects).
- Business logic is isolated from widget code.
- Replacing a backend service (e.g. swapping `TextDetector` for a stub) only requires
  changing the `Services` instance passed at startup.

---

## 5. Config system

`ConfigManager` (`modules/config/manager.py`) is a thread-safe singleton.

```
ConfigManager.instance()         # always returns the same object
config.get("ocr.lang")           # dot-notation key access
config.set("ocr.lang", "th")     # dot-notation key write
config.get_profile_config()      # returns the currently active profile dict
config.get_paddleocr_params()    # convenience: profile["paddleocr"] dict
config.set_current_profile("gpu")
config.save()                    # writes back to config/config.yaml

# Cancel-safe dialog support
snap = config.snapshot()         # deep copy of full config state
# … user edits …
config.restore_snapshot(snap)    # revert on Cancel
```

Profiles live in `config/profiles/cpu.yaml` and `config/profiles/gpu.yaml`.
The active profile is set via `default_profile` in `config/config.yaml`.

---

## 6. Workspace and version model

Each workspace is a directory under `workspaces/<workspace_id>/`:

```
workspaces/
└── my_project/
    ├── workspace.json     # workspace metadata, current/available versions
    ├── v1.json            # annotation data for version v1
    ├── v2.json            # annotation data for version v2 (if created)
    └── exports.json       # export history
```

**`workspace.json` structure:**
```json
{
  "version": "3.0.0",
  "workspace": { "id": "…", "name": "…", "created_at": "…", "modified_at": "…" },
  "source":    { "folder": "/path/to/images", "total_images": 42 },
  "versions":  { "current": "v1", "available": ["v1", "v2"] },
  "settings":  { "detector": { "model": "paddleocr", "lang": "th" } }
}
```

**`v1.json` structure:**
```json
{
  "workspace_id": "my_project",
  "data_version": "v1",
  "annotations": {
    "image001.jpg": [
      { "points": [[10,10],[100,10],[100,40],[10,40]],
        "transcription": "Hello", "difficult": false,
        "shape": "Quad", "score": 0.98, "mask_color": null }
    ]
  },
  "transforms": {},
  "metadata": { "total_images": 42, "annotated_images": 10, "total_annotations": 35 }
}
```

The three-class split (`WorkspaceStorage` → `VersionManager` → `WorkspaceManager`) keeps
responsibilities clear: storage handles raw file I/O (atomic JSON writes), version handles
version-level CRUD, and manager provides the high-level API consumed by handlers.

---

## 7. Undo/Redo (Command pattern)

```
UndoRedoManager (singleton)
├── _undo_stack: List[Command]
└── _redo_stack: List[Command]

Command (ABC)
├── execute() → bool
└── undo()    → bool
```

Usage in a handler:
```python
cmd = AddAnnotationCommand(
    annotations=self.state.annotations,
    img_key=self.state.img_key,
    annotation=new_ann,
)
self.services.undo_manager.execute(cmd)
# AppState is updated inside cmd.execute(); handler does not mutate state directly.
```

History is bounded by `max_history` (default 50). Callbacks registered with
`set_change_callback()` are invoked after every execute/undo/redo to let the UI
update toolbar button states.

---

## 8. CLI entry point

`modules/cli.py` is a pure-Python entry point — **no Qt imports allowed**.

```
ajan-ocr-cli detect  --workspace <path> [--version v1]
ajan-ocr-cli export  --workspace <path> --output <dir> [--split 0.8 0.1 0.1]
ajan-ocr-cli version
```

The CLI loads workspace JSON directly and calls the same `WorkspaceManager` and
`TextDetector` classes used by the GUI — there is no separate code path.

Running headless in Docker:
```bash
docker run ajan-ocr:cpu python -m modules.cli detect --workspace /app/workspaces/p1
```

---

## 9. Docker layout

```
Dockerfile (multi-stage)
├── builder         python:3.10-slim + pip install
├── runtime-cpu     + libgl1 + Xvfb + x11vnc + fluxbox + websockify + noVNC
└── runtime-gpu     nvidia/cuda:11.8 base + paddlepaddle-gpu

docker/entrypoint.sh
├── MODE=gui        Xvfb → x11vnc → websockify → fluxbox → python main.py
└── MODE=headless   exec "$@" (pass CLI args directly)

docker-compose.yml          cpu service  (MODE=gui, port 6080)
docker-compose.gpu.yml      override with NVIDIA device reservation
```

Volumes mounted from host:
- `./workspaces:/app/workspaces` — annotation data
- `./models:/app/models` — OCR model weights
- `./config:/app/config` — editable YAML config
- `./data:/app/data` — app_config.json, recent_workspaces.json

---

## 10. Testing strategy

Tests live in `tests/unit/` and run without a display server or GPU.

| File | What it covers |
|---|---|
| `test_validation.py` | `sanitize_annotation`, `sanitize_filename` |
| `test_config_manager.py` | Singleton, profiles, get/set, snapshot/restore, save/reload |
| `test_undo_redo.py` | Command execute/undo/redo, max_history, callbacks |
| `test_workspace_manager.py` | *(planned)* create, load, save, version switch |
| `test_file_io.py` | *(planned)* imread/imwrite Unicode path round-trip |

**Markers** (defined in `pyproject.toml`):
- `unit` — pure Python, no Qt, no filesystem I/O
- `integration` — multiple modules together
- `gui` — requires `QApplication` (pytest-qt)
- `slow` — long-running, excluded from fast CI

**Headless CI trick:** `QT_QPA_PLATFORM=offscreen` allows `gui`-marked tests to run on
Linux without an X server. Handlers can be instantiated without Qt because they receive
`AppState` and `Services` objects rather than importing Qt at module level.

**Coverage target:** ≥ 35% on `modules/core/`, `modules/utils/`, `modules/config/`.
