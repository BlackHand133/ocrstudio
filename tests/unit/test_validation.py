"""
Unit tests for modules.utils.validation

Tests cover:
- sanitize_annotation: numpy type conversion
- sanitize_annotations: list processing
- sanitize_filename: special-character handling
"""
import pytest
import numpy as np

from modules.utils.validation import (
    sanitize_annotation,
    sanitize_annotations,
    sanitize_filename,
)


# ===========================================================================
# sanitize_annotation
# ===========================================================================

class TestSanitizeAnnotation:

    def test_plain_dict_passes_through(self):
        ann = {"points": [[1, 2], [3, 4]], "transcription": "hello"}
        result = sanitize_annotation(ann)
        assert result == ann
        assert isinstance(result["points"][0][0], int)

    def test_numpy_integer_converted(self):
        ann = {"x": np.int32(42), "y": np.int64(99)}
        result = sanitize_annotation(ann)
        assert result["x"] == 42
        assert isinstance(result["x"], int)
        assert result["y"] == 99
        assert isinstance(result["y"], int)

    def test_numpy_float_converted(self):
        ann = {"score": np.float32(0.95), "ratio": np.float64(1.5)}
        result = sanitize_annotation(ann)
        assert abs(result["score"] - 0.95) < 1e-4
        assert isinstance(result["score"], float)

    def test_numpy_array_converted_to_list(self):
        pts = np.array([[10, 20], [30, 40], [50, 60], [70, 80]])
        ann = {"points": pts}
        result = sanitize_annotation(ann)
        assert isinstance(result["points"], list)
        assert result["points"][0] == [10, 20]

    def test_nested_numpy_types(self):
        ann = {
            "points": [[np.int32(1), np.int32(2)], [np.int32(3), np.int32(4)]],
            "score": np.float32(0.9),
        }
        result = sanitize_annotation(ann)
        assert all(isinstance(v, int) for row in result["points"] for v in row)
        assert isinstance(result["score"], float)

    def test_object_with_to_dict_is_converted(self):
        class Fake:
            def to_dict(self):
                return {"transcription": "text", "score": np.float32(0.8)}

        result = sanitize_annotation(Fake())
        assert result["transcription"] == "text"
        assert isinstance(result["score"], float)

    def test_string_values_untouched(self):
        ann = {"transcription": "สวัสดี", "shape": "Quad"}
        result = sanitize_annotation(ann)
        assert result["transcription"] == "สวัสดี"
        assert result["shape"] == "Quad"

    def test_boolean_untouched(self):
        ann = {"difficult": False}
        result = sanitize_annotation(ann)
        assert result["difficult"] is False

    def test_none_value_untouched(self):
        ann = {"mask_color": None}
        result = sanitize_annotation(ann)
        assert result["mask_color"] is None

    def test_mixed_list_converted(self):
        ann = {"values": [np.int32(1), 2, np.float32(3.0), "four"]}
        result = sanitize_annotation(ann)
        assert result["values"] == [1, 2, 3.0, "four"]
        assert isinstance(result["values"][0], int)
        assert isinstance(result["values"][2], float)


# ===========================================================================
# sanitize_annotations
# ===========================================================================

class TestSanitizeAnnotations:

    def test_empty_list(self):
        assert sanitize_annotations([]) == []

    def test_single_annotation(self):
        ann = [{"points": np.array([[1, 2], [3, 4], [5, 6], [7, 8]])}]
        result = sanitize_annotations(ann)
        assert len(result) == 1
        assert isinstance(result[0]["points"], list)

    def test_multiple_annotations(self):
        anns = [
            {"x": np.int32(i), "text": f"word_{i}"}
            for i in range(5)
        ]
        result = sanitize_annotations(anns)
        assert len(result) == 5
        for i, r in enumerate(result):
            assert r["x"] == i
            assert isinstance(r["x"], int)

    def test_returns_new_list(self):
        """sanitize_annotations must not modify the original list."""
        orig = [{"x": np.int32(1)}]
        result = sanitize_annotations(orig)
        assert result is not orig


# ===========================================================================
# sanitize_filename
# ===========================================================================

class TestSanitizeFilename:

    def test_no_change_needed(self):
        assert sanitize_filename("image_001.jpg") == "image_001.jpg"

    def test_spaces_replaced(self):
        assert sanitize_filename("my file.jpg") == "my_file.jpg"

    def test_special_chars_replaced(self):
        result = sanitize_filename("test+demo.jpg")
        assert "+" not in result
        assert result.endswith(".jpg")

    def test_duplicate_underscores_collapsed(self):
        result = sanitize_filename("a  b  c.png")
        assert "__" not in result

    def test_leading_trailing_underscores_stripped(self):
        result = sanitize_filename("  leading.jpg")
        assert not result.startswith("_")

    def test_unicode_thai_preserved(self):
        result = sanitize_filename("ภาพที่_1.jpg")
        assert "ภาพ" in result
        assert result.endswith(".jpg")

    def test_no_extension(self):
        result = sanitize_filename("filename_no_ext")
        assert "_" not in result or result.startswith("filename")

    def test_parentheses_replaced(self):
        result = sanitize_filename("image (1).png")
        assert "(" not in result
        assert ")" not in result

    def test_extension_preserved(self):
        for ext in ["jpg", "png", "jpeg", "bmp"]:
            result = sanitize_filename(f"test file.{ext}")
            assert result.endswith(f".{ext}")

    def test_custom_replacement_char(self):
        result = sanitize_filename("a b c.jpg", replacement="-")
        assert " " not in result
