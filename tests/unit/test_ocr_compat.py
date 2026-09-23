"""Tests for the PaddleOCR 2.x/3.x compatibility layer.

The stakes here are quiet failure: PaddleOCR 3.x refuses a deprecated parameter
alongside its replacement, so a leftover ``det_db_*`` key means a user's tuned
detection threshold never reaches the engine while the UI still reports "saved".

The version x language answers are checked two ways. The static table must
match what PaddleOCR 3.7.0's own resolver returns — the expected values below
were produced by running that resolver, not read from its docs. And when a
paddleocr module is importable, the answers must come from it rather than from
the table, because the image may have been built against a different release.
"""

import sys
import types

import pytest

from modules.core.ocr import compat
from modules.core.ocr.compat import (
    CUSTOM_MODEL_KEYS,
    OCR_VERSIONS,
    PARAM_ALIASES,
    available_versions,
    capability_source,
    engine_param_error,
    engine_version,
    explain_unsupported,
    lang_supported,
    normalize_params,
    supported_langs,
    version_supports_lang,
    versions_for_lang,
)


@pytest.fixture(autouse=True)
def fresh_capabilities():
    """The capability probe is cached per process; tests that swap the engine
    need a clean slate before and after."""
    compat._capabilities.cache_clear()
    yield
    compat._capabilities.cache_clear()


@pytest.fixture
def no_paddleocr(monkeypatch):
    """Force the static table, even on a machine that has paddleocr installed.

    A None entry in sys.modules makes the import raise, including for the
    submodule the probe imports directly.
    """
    for name in ("paddleocr", "paddleocr._pipelines", "paddleocr._pipelines.ocr"):
        monkeypatch.setitem(sys.modules, name, None)


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


# Output of PaddleOCR 3.7.0's PaddleOCR._get_ocr_model_names(lang, version)
# for every language the settings UI has offered; True = a recognizer resolves.
UPSTREAM_370 = {
    #                default  v6     v5     v4     v3
    "th":          (True,  False, True,  False, False),
    "en":          (True,  True,  True,  True,  True),
    "ch":          (True,  True,  True,  True,  True),
    "chinese_cht": (True,  True,  True,  False, True),
    "japan":       (True,  True,  True,  False, True),
    "korean":      (True,  False, True,  False, True),
    "latin":       (False, False, False, False, False),
    "arabic":      (False, False, False, False, False),
    "cyrillic":    (False, False, False, False, False),
    "devanagari":  (False, False, False, False, False),
}
UPSTREAM_COLUMNS = (None, "PP-OCRv6", "PP-OCRv5", "PP-OCRv4", "PP-OCRv3")


@pytest.mark.usefixtures("no_paddleocr")
class TestStaticTable:
    """Without paddleocr installed (CI, dev machines) the fallback table answers."""

    def test_reports_that_it_is_the_fallback(self):
        assert capability_source().startswith("static table")

    @pytest.mark.parametrize("lang", sorted(UPSTREAM_370))
    def test_matches_upstream_resolver_for_every_ui_language(self, lang):
        got = tuple(version_supports_lang(v, lang) for v in UPSTREAM_COLUMNS)
        assert got == UPSTREAM_370[lang]

    def test_thai_works_only_on_v5(self):
        # The earlier hand-written table allowed Thai on v4 and v3.
        assert versions_for_lang("th") == ["PP-OCRv5"]

    def test_retired_script_group_codes_resolve_nowhere(self):
        for code in ("latin", "arabic", "cyrillic", "devanagari"):
            assert not lang_supported(code)
            assert versions_for_lang(code) == []

    def test_unknown_language_is_not_blocked_without_evidence(self):
        # e.g. 'fr' is outside the table; without the engine we cannot say.
        assert version_supports_lang("PP-OCRv6", "fr") is True

    def test_unknown_release_is_rejected(self):
        # PaddleOCR checks the release name before looking at the language.
        assert version_supports_lang("PP-OCRv9", "en") is False

    def test_supported_langs_filters_the_given_candidates(self):
        assert supported_langs("PP-OCRv6", ["th", "en", "korean", "japan"]) == ["en", "japan"]


def _fake_paddleocr(monkeypatch, versions, table):
    """Install a stand-in paddleocr whose resolver answers from *table*."""

    class FakePaddleOCR:
        def _get_ocr_model_names(self, lang, ppocr_version):
            if (lang, ppocr_version) in table:
                return "det", "rec"
            return None, None

    pipelines = types.ModuleType("paddleocr._pipelines")
    ocr = types.ModuleType("paddleocr._pipelines.ocr")
    ocr._SUPPORTED_OCR_VERSIONS = list(versions)
    ocr.PaddleOCR = FakePaddleOCR
    pipelines.ocr = ocr
    root = types.ModuleType("paddleocr")
    root.__version__ = "9.9.9-test"
    root._pipelines = pipelines
    monkeypatch.setitem(sys.modules, "paddleocr", root)
    monkeypatch.setitem(sys.modules, "paddleocr._pipelines", pipelines)
    monkeypatch.setitem(sys.modules, "paddleocr._pipelines.ocr", ocr)


class TestInstalledEngineWins:
    """With paddleocr importable, its resolver decides — whatever release it is."""

    def test_source_names_the_installed_version(self, monkeypatch):
        _fake_paddleocr(monkeypatch, ["PP-OCRv5"], {("en", None)})
        assert capability_source() == "paddleocr 9.9.9-test"

    def test_versions_come_from_the_engine_newest_first(self, monkeypatch):
        # A 3.6.0 image knows no PP-OCRv6; the UI must not offer it there.
        _fake_paddleocr(monkeypatch, ["PP-OCRv3", "PP-OCRv4", "PP-OCRv5"], {("en", None)})
        assert available_versions() == ("PP-OCRv5", "PP-OCRv4", "PP-OCRv3")
        assert version_supports_lang("PP-OCRv6", "en") is False

    def test_engine_answer_overrides_the_static_table(self, monkeypatch):
        # Pretend a future release adds a Thai model to v6. The table says no;
        # the engine says yes, and the engine is what will actually run.
        _fake_paddleocr(
            monkeypatch,
            ["PP-OCRv5", "PP-OCRv6"],
            {("en", None), ("th", "PP-OCRv6"), ("th", None)},
        )
        assert version_supports_lang("PP-OCRv6", "th") is True

    def test_resolver_that_raises_counts_as_unsupported(self, monkeypatch):
        _fake_paddleocr(monkeypatch, ["PP-OCRv5"], {("en", None)})
        ocr = sys.modules["paddleocr._pipelines.ocr"]

        def boom(self, lang, ppocr_version):
            if lang == "en":
                return "det", "rec"
            raise KeyError(lang)

        monkeypatch.setattr(ocr.PaddleOCR, "_get_ocr_model_names", boom)
        assert version_supports_lang("PP-OCRv5", "th") is False

    def test_changed_private_api_falls_back_to_the_table(self, monkeypatch):
        _fake_paddleocr(monkeypatch, ["PP-OCRv5"], {("en", None)})
        monkeypatch.delattr(sys.modules["paddleocr._pipelines.ocr"], "_SUPPORTED_OCR_VERSIONS")
        assert capability_source().startswith("static table")
        assert available_versions() == OCR_VERSIONS


def test_static_table_agrees_with_the_installed_engine():
    """Drift check for wherever the real engine is installed (the web image).

    Compares every release both sides know, so a 3.6.0 image checks v3-v5 and a
    3.7.0 image checks v3-v6. Fails, rather than skips, when paddleocr imports
    but cannot be probed: that means its private resolver moved and the app is
    silently running on the table.
    """
    pytest.importorskip("paddleocr")
    versions, supports, source = compat._capabilities()
    assert source.startswith("paddleocr"), f"probe fell back to {source!r}"

    shared = [None] + [v for v in versions if v in OCR_VERSIONS]
    mismatches = [
        (version, lang, supports(version, lang))
        for version in shared
        for lang in UPSTREAM_370
        if supports(version, lang) != compat._static_supports(version, lang)
    ]
    assert mismatches == [], f"engine disagrees with the table on {source}"


@pytest.mark.usefixtures("no_paddleocr")
class TestEngineParamError:
    """Same checks, same order, as PaddleOCR 3.7.0's __init__."""

    def test_buildable_profile_passes(self):
        assert engine_param_error({"lang": "th", "ocr_version": "PP-OCRv5"}) is None

    def test_shipped_profile_shape_passes(self):
        # config/profiles/*.yaml pin a language but no release.
        assert engine_param_error({"lang": "th"}) is None

    def test_unpinned_release_is_checked_too(self):
        # The previous check only ran when ocr_version was set, so 'latin' slipped through.
        assert "2.x" in engine_param_error({"lang": "latin"})

    def test_missing_lang_uses_a_model_every_release_has(self):
        # PaddleOCR substitutes 'ch' for an unset lang.
        assert engine_param_error({"ocr_version": "PP-OCRv4"}) is None

    @pytest.mark.parametrize("key", CUSTOM_MODEL_KEYS)
    def test_custom_model_makes_lang_irrelevant(self, key):
        params = {"lang": "th", "ocr_version": "PP-OCRv4", key: "models/rec/mine"}
        assert engine_param_error(params) is None

    def test_unknown_release_fails_even_with_a_custom_model(self):
        # PaddleOCR validates the release name before it looks at the models.
        problem = engine_param_error(
            {"ocr_version": "PP-OCRv9", "text_recognition_model_dir": "models/rec/mine"}
        )
        assert problem and "PP-OCRv9" in problem

    def test_blank_custom_model_is_not_a_custom_model(self):
        # The settings API stores a cleared field as absent; "" must not exempt.
        assert engine_param_error({"lang": "latin", "text_detection_model_dir": ""})


@pytest.mark.usefixtures("no_paddleocr")
class TestExplainUnsupported:

    def test_names_the_release_that_works(self):
        msg = explain_unsupported("PP-OCRv6", "th")
        assert "PP-OCRv5" in msg and "th" in msg

    def test_retired_code_suggests_a_real_language(self):
        msg = explain_unsupported(None, "latin")
        assert "2.x" in msg and "'fr'" in msg

    def test_unavailable_release_lists_the_ones_that_exist(self):
        msg = explain_unsupported("PP-OCRv9", "en")
        assert "PP-OCRv9" in msg and "PP-OCRv5" in msg

    @pytest.mark.parametrize("version,lang", [
        ("PP-OCRv6", "th"), (None, "latin"), ("PP-OCRv9", "en"), ("PP-OCRv4", "japan"),
    ])
    def test_message_is_ascii_safe(self, version, lang):
        # This string gets logged; a Windows console on a Thai codepage raises
        # UnicodeEncodeError on characters like an em dash.
        explain_unsupported(version, lang).encode("ascii")


def test_engine_version_never_raises():
    """Reporting must degrade to 'unknown' rather than break the caller when
    PaddleOCR is not installed (e.g. the web image builds before models land)."""
    assert isinstance(engine_version(), str)
