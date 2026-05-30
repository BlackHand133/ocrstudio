"""
Smoke tests for MainWindow.

These tests are marked `gui` and require:
- PyQt5
- pytest-qt   (pip install pytest-qt)
- A display or QT_QPA_PLATFORM=offscreen

Run:
    QT_QPA_PLATFORM=offscreen pytest tests/unit/test_main_window_smoke.py -m gui

All tests are auto-skipped when PyQt5 or pytest-qt are not available.
"""
import pytest

pytestmark = pytest.mark.gui

# Skip entire module if PyQt5 is not importable
pytest.importorskip("PyQt5", reason="PyQt5 not installed — skipping GUI smoke tests")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def main_window(qtbot):
    """Create MainWindow and register it with qtbot for proper cleanup."""
    from modules.gui.main_window import MainWindow
    win = MainWindow()
    qtbot.addWidget(win)
    return win


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------

class TestInstantiation:
    def test_window_is_created(self, main_window):
        assert main_window is not None

    def test_window_has_title(self, main_window):
        assert len(main_window.windowTitle()) > 0

    def test_has_app_state(self, main_window):
        from modules.core.app_state import AppState
        assert isinstance(main_window._state, AppState)

    def test_has_services(self, main_window):
        from modules.core.services import Services
        assert isinstance(main_window._services, Services)


# ---------------------------------------------------------------------------
# Mode switching via AppState
# ---------------------------------------------------------------------------

class TestModeSwitching:
    def test_draw_mode_on(self, main_window):
        main_window._state.set_draw_mode(True)
        assert main_window._state.draw_mode is True

    def test_draw_mode_off(self, main_window):
        main_window._state.set_draw_mode(True)
        main_window._state.set_draw_mode(False)
        assert main_window._state.draw_mode is False

    def test_recog_mode_toggle(self, main_window):
        main_window._state.set_recog_mode(True)
        assert main_window._state.recog_mode is True
        main_window._state.set_recog_mode(False)
        assert main_window._state.recog_mode is False

    def test_annotation_type_quad_to_polygon(self, main_window):
        main_window._state.set_annotation_type("Polygon")
        assert main_window._state.annotation_type == "Polygon"

    def test_annotation_type_back_to_quad(self, main_window):
        main_window._state.set_annotation_type("Polygon")
        main_window._state.set_annotation_type("Quad")
        assert main_window._state.annotation_type == "Quad"


# ---------------------------------------------------------------------------
# Filter state
# ---------------------------------------------------------------------------

class TestFilterState:
    def test_default_filter_is_all(self, main_window):
        assert main_window._state.current_filter == "all"

    def test_set_filter_annotated(self, main_window):
        main_window._state.set_filter("annotated")
        assert main_window._state.current_filter == "annotated"

    def test_set_filter_with_search(self, main_window):
        main_window._state.set_filter("all", search_text="hello")
        assert main_window._state.search_text == "hello"


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------

class TestClose:
    def test_close_does_not_raise(self, main_window, qtbot):
        # Should complete without exception
        main_window.close()
