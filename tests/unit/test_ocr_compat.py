"""Tests for the PaddleOCR 2.x/3.x compatibility layer.

The stakes here are quiet failure: PaddleOCR 3.x refuses a deprecated parameter
alongside its replacement, so a leftover ``det_db_*`` key means a user's tuned
detection threshold never reaches the engine while the UI still reports "saved".
"""

import pytest

from modules.core.ocr.compat import (
    OCR_VERSIONS,
    PARAM_ALIASES,
    engine_version,
    explain_unsupported,
    normalize_params,
    supported_langs,
    version_supports_lang,
    versions_for_lang,
)


class TestNormalizeParams:

    def test_renames_every_deprecated_key(self):
        raw = {old: 1 for old in PARAM_ALIASES}
        out, notes = normalize_params(raw)

        for old, new in PARAM_ALIASES.items():
            assert old not in out, f"deprecated {old!r} must not survive"
            assert out[new] == 1
        assert len(notes) == len(PARAM_ALIASES)

    def test_renames_the_three_keys_this_repo_shipped(self):
        out, _ = normalize_params(
            {
                "lang": "th",
                "det_db_box_thresh": 0.7,
                "det_db_unclip_ratio": 1.5,
                "rec_batch_num": 6,
            }
        )
        assert out == {
            "lang": "th",
            "text_det_box_thresh": 0.7,
            "text_det_unclip_ratio": 1.5,
            "text_recognition_batch_size": 6,
        }

    def test_never_emits_both_spellings(self):
        # Passing both is exactly what makes PaddleOCR raise.
        out, notes = normalize_params(
            {"det_db_box_thresh": 0.7, "text_det_box_thresh": 0.9}
        )
        assert out == {"text_det_box_thresh": 0.9}
        assert "det_db_box_thresh" in notes[0]

    def test_passes_unknown_keys_through_untouched(self):
        out, notes = normalize_params({"cpu_threads": 8, "enable_mkldnn": False})
        assert out == {"cpu_threads": 8, "enable_mkldnn": False}
        assert notes == []

    def test_strips_app_only_keys(self):
        # max_image_size is ours; PaddleOCR rejects unexpected keyword arguments.
        out, _ = normalize_params({"lang": "th", "max_image_size": 4000})
        assert out == {"lang": "th"}

    def test_empty_input_is_a_no_op(self):
        assert normalize_params({}) == ({}, [])


class TestVersionLanguageMatrix:

    def test_v6_has_no_thai_model(self):
        assert version_supports_lang("PP-OCRv6", "th") is False

    @pytest.mark.parametrize("lang", ["en", "ch", "japan", "latin"])
    def test_v6_accepts_the_languages_it_ships(self, lang):
        assert version_supports_lang("PP-OCRv6", lang) is True

    @pytest.mark.parametrize("version", ["PP-OCRv5", "PP-OCRv4", "PP-OCRv3"])
    def test_unrestricted_versions_accept_thai(self, version):
        assert version_supports_lang(version, "th") is True

    def test_unknown_inputs_stay_permissive(self):
        # Blocking a pair we have no evidence against would be worse than
        # allowing it: the user simply could not select a working combination.
        assert version_supports_lang("PP-OCRv9", "th") is True
        assert version_supports_lang(None, "th") is True
        assert version_supports_lang("PP-OCRv6", None) is True

    def test_versions_for_lang_drops_only_the_impossible_one(self):
        assert versions_for_lang("th") == ["PP-OCRv5", "PP-OCRv4", "PP-OCRv3"]
        assert versions_for_lang("en") == list(OCR_VERSIONS)

    def test_supported_langs_reports_none_when_unrestricted(self):
        assert supported_langs("PP-OCRv5") is None
        assert "th" not in (supported_langs("PP-OCRv6") or [])


class TestExplainUnsupported:

    def test_names_a_version_that_works(self):
        msg = explain_unsupported("PP-OCRv6", "th")
        assert "PP-OCRv5" in msg
        assert "th" in msg

    def test_message_is_ascii_safe(self):
        # This string gets logged; a Windows console on a Thai codepage raises
        # UnicodeEncodeError on characters like an em dash.
        explain_unsupported("PP-OCRv6", "th").encode("ascii")


def test_engine_version_never_raises():
    """Reporting must degrade to 'unknown' rather than break the caller when
    PaddleOCR is not installed (e.g. the web image builds before models land)."""
    assert isinstance(engine_version(), str)
