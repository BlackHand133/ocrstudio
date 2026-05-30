"""
Unit tests for imread_unicode / imwrite_unicode (Unicode path support).

Requires cv2 and numpy.  All tests are skipped automatically if cv2 is not
installed (e.g., base test environment without OpenCV).
"""
import pytest

# Skip the entire module if cv2 or numpy are not available
cv2 = pytest.importorskip("cv2", reason="cv2 not installed — skipping file_io tests")
np  = pytest.importorskip("numpy", reason="numpy not installed — skipping file_io tests")

from modules.utils.file_io import imread_unicode, imwrite_unicode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_bgr():
    """A small BGR image (20×30, black) for round-trip tests."""
    return np.zeros((20, 30, 3), dtype=np.uint8)


@pytest.fixture
def tiny_color():
    """A BGR image with distinct pixel values so round-trips can be validated."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[0, 0] = [255, 0, 0]   # Blue pixel at (0,0)
    img[5, 5] = [0, 255, 0]   # Green pixel at (5,5)
    return img


# ---------------------------------------------------------------------------
# imwrite_unicode
# ---------------------------------------------------------------------------

class TestImwriteUnicode:
    def test_write_jpg_creates_file(self, tiny_bgr, tmp_path):
        path = tmp_path / "test.jpg"
        assert imwrite_unicode(str(path), tiny_bgr) is True
        assert path.exists()
        assert path.stat().st_size > 0

    def test_write_png_creates_file(self, tiny_bgr, tmp_path):
        path = tmp_path / "test.png"
        assert imwrite_unicode(str(path), tiny_bgr) is True
        assert path.exists()

    def test_write_with_unicode_directory(self, tiny_bgr, tmp_path):
        uni_dir = tmp_path / "ภาษาไทย"
        uni_dir.mkdir()
        path = uni_dir / "test.png"
        assert imwrite_unicode(str(path), tiny_bgr) is True
        assert path.exists()

    def test_write_with_unicode_filename(self, tiny_bgr, tmp_path):
        path = tmp_path / "รูปภาพ.jpg"
        assert imwrite_unicode(str(path), tiny_bgr) is True
        assert path.exists()

    def test_write_png_via_format_override(self, tiny_bgr, tmp_path):
        # File has .jpg extension but we force PNG encoding
        path = tmp_path / "forced.jpg"
        result = imwrite_unicode(str(path), tiny_bgr, image_format="png")
        assert result is True

    def test_write_returns_false_on_invalid_image(self, tmp_path):
        bad = np.array([], dtype=np.uint8)
        result = imwrite_unicode(str(tmp_path / "bad.jpg"), bad)
        assert result is False


# ---------------------------------------------------------------------------
# imread_unicode
# ---------------------------------------------------------------------------

class TestImreadUnicode:
    def test_roundtrip_jpg_shape(self, tiny_bgr, tmp_path):
        path = str(tmp_path / "rt.jpg")
        imwrite_unicode(path, tiny_bgr)
        loaded = imread_unicode(path)
        assert loaded is not None
        # JPEG is lossy so we only check dimensions, not pixel values
        assert loaded.shape[0] == tiny_bgr.shape[0]
        assert loaded.shape[1] == tiny_bgr.shape[1]
        assert loaded.shape[2] == 3

    def test_roundtrip_png_exact(self, tiny_bgr, tmp_path):
        path = str(tmp_path / "rt.png")
        imwrite_unicode(path, tiny_bgr)
        loaded = imread_unicode(path)
        assert loaded is not None
        assert np.array_equal(loaded, tiny_bgr)

    def test_roundtrip_unicode_path(self, tiny_bgr, tmp_path):
        uni_dir = tmp_path / "中文路径"
        uni_dir.mkdir()
        path = str(uni_dir / "img.png")
        imwrite_unicode(path, tiny_bgr)
        loaded = imread_unicode(path)
        assert loaded is not None
        assert loaded.shape == tiny_bgr.shape

    def test_missing_file_returns_none(self, tmp_path):
        result = imread_unicode(str(tmp_path / "nonexistent.jpg"))
        assert result is None

    def test_returns_ndarray(self, tiny_bgr, tmp_path):
        path = str(tmp_path / "arr.png")
        imwrite_unicode(path, tiny_bgr)
        loaded = imread_unicode(path)
        assert isinstance(loaded, np.ndarray)

    def test_three_channel_output(self, tiny_bgr, tmp_path):
        path = str(tmp_path / "ch.png")
        imwrite_unicode(path, tiny_bgr)
        loaded = imread_unicode(path)
        assert loaded.ndim == 3
        assert loaded.shape[2] == 3
