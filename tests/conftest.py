"""
Shared pytest fixtures for the Ajan OCR test suite.

Fixtures here are available to every test file automatically.
"""
import os
import json
import shutil
import tempfile
import pytest


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir(tmp_path):
    """
    Yield a temporary directory and clean up afterwards.
    Uses pytest's built-in tmp_path for automatic cleanup.
    """
    yield tmp_path


@pytest.fixture
def project_root():
    """Absolute path to the project root (one level above tests/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_config_yaml(tmp_path):
    """
    Write a minimal config.yaml to a temp directory and return its path.

    Structure mirrors the real config/config.yaml used in production.
    """
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"

    import yaml
    config = {
        "default_profile": "cpu",
        "profiles": {
            "cpu": {
                "device": {"type": "cpu"},
                "paddleocr": {
                    "lang": "th",
                    "use_doc_orientation_classify": False,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": False,
                    "device": "cpu",
                    "det_db_box_thresh": 0.7,
                    "det_db_unclip_ratio": 1.5,
                },
            },
            "gpu": {
                "device": {"type": "gpu", "gpu_id": 0, "gpu_mem": 8000},
                "paddleocr": {
                    "lang": "th",
                    "use_doc_orientation_classify": True,
                    "use_doc_unwarping": False,
                    "use_textline_orientation": True,
                    "device": "gpu",
                    "det_db_box_thresh": 0.6,
                    "det_db_unclip_ratio": 2.0,
                },
            },
        },
        "app": {
            "auto_save": True,
            "cache_annotations": True,
        },
    }
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f, allow_unicode=True)

    return tmp_path  # Return root so ConfigManager can find config/ sub-dir


@pytest.fixture
def config_manager(minimal_config_yaml):
    """
    Yield a fresh ConfigManager instance backed by a temp config file.
    Resets the singleton after the test so other tests get a clean slate.
    """
    from modules.config.manager import ConfigManager

    ConfigManager.reset_instance()
    mgr = ConfigManager.instance(root_dir=str(minimal_config_yaml))
    yield mgr
    ConfigManager.reset_instance()


# ---------------------------------------------------------------------------
# Annotation / workspace fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_annotations():
    """
    Return a list of sample annotation dicts covering Quad, Polygon, and Mask
    shapes with Python-native types (no numpy).
    """
    return [
        {
            "points": [[10, 10], [100, 10], [100, 50], [10, 50]],
            "transcription": "Hello",
            "difficult": False,
            "shape": "Quad",
        },
        {
            "points": [[200, 20], [300, 20], [320, 60], [280, 80], [190, 60]],
            "transcription": "World",
            "difficult": False,
            "shape": "Polygon",
        },
        {
            "points": [[0, 0], [50, 0], [50, 50], [0, 50]],
            "transcription": "###",
            "difficult": False,
            "shape": "MaskQuad",
            "mask_color": "#000000",
        },
    ]


@pytest.fixture
def temp_workspace(tmp_path):
    """
    Create a minimal workspace directory structure and return its path.
    Matches the structure expected by WorkspaceManager.
    """
    ws_dir = tmp_path / "workspaces" / "test_ws"
    ws_dir.mkdir(parents=True)
    (ws_dir / "versions").mkdir()
    meta = {
        "id": "test_ws",
        "name": "Test Workspace",
        "description": "Fixture workspace",
        "created_at": "2025-01-01T00:00:00",
        "version": "3.0",
    }
    with open(ws_dir / "workspace.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return ws_dir


# ---------------------------------------------------------------------------
# AppState fixture (no Qt required — QObject works without a QApplication
# as long as we only access plain Python attributes)
# ---------------------------------------------------------------------------

@pytest.fixture
def app_state():
    """
    Yield a fresh AppState instance.

    NOTE: AppState is a QObject.  Instantiating it without a QApplication is
    allowed in newer Qt/PyQt5 builds, but signal emission will raise a
    RuntimeError.  Tests that need signals should use the `qt_app` fixture
    (pytest-qt) or mock the signals.
    """
    try:
        from modules.core.app_state import AppState
        state = AppState()
        yield state
    except Exception as exc:
        pytest.skip(f"AppState requires Qt: {exc}")
