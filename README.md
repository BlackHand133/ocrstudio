# Ajan OCR Annotation Tool

[![CI](https://github.com/BlackHand133/ocrstudio/actions/workflows/ci.yml/badge.svg)](https://github.com/BlackHand133/ocrstudio/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-2.6%2B-green.svg)](https://github.com/PaddlePaddle/PaddleOCR)

A desktop OCR annotation tool built with PyQt5 and PaddleOCR, designed for creating high-quality
text-detection and recognition datasets — with first-class Thai language support.

---

## Quick Start (Docker — recommended)

No local Python setup needed. The app runs in your browser via noVNC.

```bash
# 1. Clone
git clone https://github.com/BlackHand133/ocrstudio.git
cd ocrstudio

# 2. Start
docker compose up

# 3. Open http://localhost:6080 in your browser
```

Annotations are saved to `./workspaces/` on your host machine and survive container restarts.

**GPU acceleration:**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

---

## Local Installation

```bash
# Python 3.10+ required
git clone https://github.com/BlackHand133/ocrstudio.git
cd ocrstudio

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

---

## CLI (Headless / Automation)

```bash
# Detect text in all images in a workspace (no GUI)
ajan-ocr-cli detect --workspace ./workspaces/my_project

# Export annotations to PaddleOCR format
ajan-ocr-cli export --workspace ./workspaces/my_project --output ./dataset

# Print version
ajan-ocr-cli version
```

Or without installing as a package:
```bash
python -m modules.cli detect --workspace ./workspaces/my_project
```

---

## Features

| Category | Details |
|---|---|
| **Annotation** | Quad boxes, polygons, mask regions, text transcription |
| **Auto-detection** | PaddleOCR text detection + recognition |
| **Languages** | Thai, English, Chinese, Japanese, and more |
| **Workspaces** | Multi-workspace, JSON-based version control |
| **Export** | PaddleOCR format (Label.txt + fileState.txt), train/val/test split |
| **Image formats** | PNG, JPG, BMP, TIFF, WebP, JFIF, and 10 more |
| **Hardware** | CPU (default) and NVIDIA GPU |
| **Container** | Docker + noVNC browser GUI (port 6080) |

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | New workspace |
| `Ctrl+O` | Open workspace |
| `Ctrl+S` | Save annotations |
| `Ctrl+Z` / `Ctrl+Y` | Undo / Redo |
| `Delete` | Delete selected annotation |
| `Ctrl+D` | Run auto-detection |
| `Ctrl+E` | Export dataset |
| `Space` / `Backspace` | Next / previous image |
| `+` / `-` | Zoom in / out |
| `Ctrl+Wheel` | Zoom |
| `F11` | Fullscreen |

---

## Configuration

| File | Purpose |
|---|---|
| `config/config.yaml` | Active profile, app-level settings |
| `config/profiles/cpu.yaml` | PaddleOCR params for CPU |
| `config/profiles/gpu.yaml` | PaddleOCR params for GPU |
| `data/app_config.json` | Window state, last workspace |
| `data/recent_workspaces.json` | Recent-workspace list |

Change the active profile from **Settings → Profile** in the GUI, or set
`default_profile: gpu` in `config/config.yaml`.

---

## Development

### Setup

```bash
pip install -e .[dev]
pip install pre-commit
pre-commit install       # installs git hooks: black, isort, flake8, file-hygiene
```

### Tests

```bash
# Fast unit tests (no Qt, no GPU)
pytest tests/unit/ -m "not gui and not slow"

# All tests with coverage report
pytest tests/unit/ --cov=modules/core --cov=modules/utils --cov=modules/config --cov-report=term-missing
```

### Type-checking & formatting

```bash
mypy modules/core/ modules/utils/ modules/config/ --ignore-missing-imports
black modules/ tests/
isort modules/ tests/
flake8 modules/ --max-line-length=100 --extend-ignore=E203,W503 --exclude=modules/gui/
```

### Project layout

```
ocrstudio/
├── main.py                    # GUI entry point
├── modules/
│   ├── cli.py                 # Headless CLI entry point (no Qt)
│   ├── config/                # ConfigManager singleton + YAML profiles
│   ├── core/
│   │   ├── app_state.py       # Centralised mutable state (QObject + signals)
│   │   ├── services.py        # Backend services dataclass (DI container)
│   │   ├── undo_redo.py       # Command-pattern undo/redo stack
│   │   ├── ocr/               # PaddleOCR detector + orientation classifier
│   │   └── workspace/         # Storage, version management, workspace manager
│   ├── data/                  # Data-processing utilities
│   ├── export/                # Export formatters
│   ├── gui/
│   │   ├── main_window.py     # Coordinator — widget refs only, no business logic
│   │   ├── handlers/          # Event handlers (DI: AppState + Services)
│   │   ├── dialogs/           # Settings, workspace, export dialogs
│   │   └── items/             # QGraphicsItem annotation shapes
│   └── utils/                 # file_io, validation, image helpers
├── config/                    # YAML configuration files
├── data/                      # Runtime JSON state (gitignored)
├── models/                    # OCR models (gitignored)
├── workspaces/                # User workspaces (gitignored)
├── tests/
│   ├── conftest.py
│   └── unit/                  # 87 Qt-free unit tests
├── docker/
│   └── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
├── docker-compose.gpu.yml
├── .pre-commit-config.yaml
├── pyproject.toml
└── requirements.txt
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a detailed description of the module structure,
data-flow, and design decisions.

---

## Troubleshooting

**`ModuleNotFoundError: PyQt5`**
```bash
pip install PyQt5
```

**PaddleOCR models not found**
- Set paths in **Settings → PaddleOCR Settings**
- Models are not bundled; download them separately

**GPU not detected in Docker**
- Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- Use `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`

**Application crashes on startup**
- Check `logs/` directory for the full traceback
- Delete `data/app_config.json` to reset window state

---

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — OCR engine
- [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) — GUI framework
- [OpenCV](https://opencv.org/) — Image processing
- [noVNC](https://novnc.com/) — Browser-based VNC client
