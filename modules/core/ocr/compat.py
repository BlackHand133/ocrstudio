"""PaddleOCR version compatibility helpers.

PaddleOCR 3.x renamed most of the detection/recognition tuning parameters that
2.x used.  The old names are *deprecated* and — critically — the library refuses
to accept an old name and its new counterpart at the same time.  Config files
written against 2.x therefore either get ignored or blow up on 3.x.

This module is the single place that knows about those differences:

* :data:`PARAM_ALIASES` — the official 2.x -> 3.x rename table.
* :func:`normalize_params` — rewrite a profile dict to the 3.x spelling.
* :func:`available_versions` / :func:`version_supports_lang` — which PP-OCR
  release the installed engine can actually build for a given language.
* :func:`engine_param_error` — the same check PaddleOCR.__init__ makes, run
  before the engine is built so the error can name a working choice.

Usage:
    from modules.core.ocr.compat import normalize_params

    params, notes = normalize_params(profile_params)
    ocr = PaddleOCR(**params)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger("TextDetGUI")


# ===== Parameter renames (PaddleOCR 2.x -> 3.x) =====
# Source: PaddleOCR docs/version3.x/pipeline_usage/OCR.en.md ("deprecated" table).
# Old and new names must never be passed together — PaddleOCR raises if they are.
PARAM_ALIASES: Dict[str, str] = {
    "det_model_dir": "text_detection_model_dir",
    "det_limit_side_len": "text_det_limit_side_len",
    "det_limit_type": "text_det_limit_type",
    "det_db_thresh": "text_det_thresh",
    "det_db_box_thresh": "text_det_box_thresh",
    "det_db_unclip_ratio": "text_det_unclip_ratio",
    "rec_model_dir": "text_recognition_model_dir",
    "rec_batch_num": "text_recognition_batch_size",
    "use_angle_cls": "use_textline_orientation",
    "cls_model_dir": "textline_orientation_model_dir",
    "cls_batch_num": "textline_orientation_batch_size",
}

# Keys that are ours, not PaddleOCR's — strip them before constructing the
# engine or PaddleOCR will reject the unexpected keyword.
LOCAL_ONLY_KEYS = frozenset({"max_image_size"})


# ===== PP-OCR release x language capability =====
#
# Whether a (language, PP-OCR release) pair has a model is decided by
# PaddleOCR.__init__, which calls PaddleOCR._get_ocr_model_names() and raises
# "No models are available" when it returns nothing. When paddleocr is
# importable we ask that resolver directly, so the answer matches whichever
# release the image was built with — 3.6.0 has no PP-OCRv6 at all, 3.7.0 does.
#
# The table below is the fallback for environments without paddleocr (dev
# machines, CI). It is not transcribed from documentation: it is the output of
# PaddleOCR 3.7.0's own _get_ocr_model_names() run over every UI language and
# release. An earlier hand-written version treated v3-v5 as unrestricted and so
# offered Thai with PP-OCRv4/v3, neither of which has a Thai model.

# Every release PaddleOCR 3.x has shipped, newest first.
OCR_VERSIONS: Tuple[str, ...] = ("PP-OCRv6", "PP-OCRv5", "PP-OCRv4", "PP-OCRv3")

_STATIC_SUPPORT: Dict[Optional[str], frozenset] = {
    None: frozenset({"th", "en", "ch", "chinese_cht", "japan", "korean"}),
    "PP-OCRv6": frozenset({"en", "ch", "chinese_cht", "japan"}),
    "PP-OCRv5": frozenset({"th", "en", "ch", "chinese_cht", "japan", "korean"}),
    "PP-OCRv4": frozenset({"en", "ch"}),
    "PP-OCRv3": frozenset({"en", "ch", "chinese_cht", "japan", "korean"}),
}

# PaddleOCR 2.x script-group codes. 3.x resolves none of them under any release
# (checked against 3.6.0 and 3.7.0); it wants a specific language instead.
_RETIRED_LANG_CODES: Dict[str, str] = {
    "latin": "a specific Latin-script language such as 'fr', 'de', 'es' or 'pt'",
    "arabic": "a specific language such as 'ar', 'fa' or 'ur'",
    "cyrillic": "a specific language such as 'ru', 'bg' or 'kk'",
    "devanagari": "a specific language such as 'hi', 'mr' or 'ne'",
}

# Codes the static table has an opinion about. Anything else is let through in
# static mode: without the engine there is no evidence either way, and nothing
# can be detected in that environment anyway.
_STATIC_KNOWN = frozenset().union(*_STATIC_SUPPORT.values(), _RETIRED_LANG_CODES)

# When any of these is set, PaddleOCR builds from the given model and ignores
# lang and ocr_version (it only warns that it did).
CUSTOM_MODEL_KEYS: Tuple[str, ...] = (
    "text_detection_model_name",
    "text_detection_model_dir",
    "text_recognition_model_name",
    "text_recognition_model_dir",
)


def _version_key(version: str) -> int:
    digits = "".join(ch for ch in version if ch.isdigit())
    return int(digits) if digits else -1


def _static_supports(version: Optional[str], lang: str) -> bool:
    if lang not in _STATIC_KNOWN:
        return True
    return lang in _STATIC_SUPPORT.get(version, frozenset())


@lru_cache(maxsize=1)
def _capabilities() -> Tuple[Tuple[str, ...], Callable[[Optional[str], str], bool], str]:
    """Return ``(versions, supports, source)`` from the installed engine if possible.

    Uses private PaddleOCR API, so every step is guarded: if the layout changes
    in a future release we fall back to the measured table rather than break
    config loading.

    The first call imports paddleocr and with it paddlex, which takes seconds;
    the web server calls this once at startup, off the request path.
    """
    try:
        from paddleocr._pipelines import ocr as upstream

        versions = tuple(sorted(upstream._SUPPORTED_OCR_VERSIONS, key=_version_key, reverse=True))
        resolve = upstream.PaddleOCR._get_ocr_model_names
        resolve(None, "en", None)  # prove the call shape still works before trusting it

        def supports(version: Optional[str], lang: str) -> bool:
            try:
                _, rec = resolve(None, lang, version)
            except Exception:  # noqa: BLE001 - the constructor would fail the same way
                return False
            return rec is not None

        return versions, supports, f"paddleocr {engine_version()}"
    except Exception as exc:  # noqa: BLE001 - absent or changed: use the measured table
        # No paddleocr at all is normal (dev machines, CI). Anything else means
        # it is installed but its private API moved, which someone should fix.
        missing = exc.name if isinstance(exc, ModuleNotFoundError) else None
        absent = (missing or "").split(".")[0] == "paddleocr"
        (logger.debug if absent else logger.warning)(
            "Using static PP-OCR capability table: %s", exc
        )
        return OCR_VERSIONS, _static_supports, "static table (measured on paddleocr 3.7.0)"


def available_versions() -> Tuple[str, ...]:
    """PP-OCR releases the installed engine accepts, newest first."""
    return _capabilities()[0]


def capability_source() -> str:
    """Where version/language answers come from, for status output and logs."""
    return _capabilities()[2]


def normalize_params(params: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Rewrite a profile dict into PaddleOCR 3.x spelling.

    Deprecated keys are renamed to their 3.x equivalents.  If both spellings are
    present the new one wins and the old one is dropped, so PaddleOCR never sees
    the conflicting pair.  Keys that only mean something to this app (see
    :data:`LOCAL_ONLY_KEYS`) are removed.

    Args:
        params: Raw ``paddleocr`` section from a profile.

    Returns:
        ``(normalized_params, notes)`` where *notes* describes every rewrite so
        callers can log it or surface it in the UI.
    """
    out: Dict[str, Any] = {}
    notes: List[str] = []

    for key, value in params.items():
        if key in LOCAL_ONLY_KEYS:
            continue

        new_key = PARAM_ALIASES.get(key)
        if new_key is None:
            out[key] = value
            continue

        if new_key in params:
            # Caller already supplied the modern spelling — that one wins.
            notes.append(f"dropped deprecated '{key}' (superseded by '{new_key}')")
            continue

        out[new_key] = value
        notes.append(f"renamed '{key}' -> '{new_key}'")

    if notes:
        logger.info("PaddleOCR param compatibility: %s", "; ".join(notes))

    return out, notes


def version_supports_lang(version: Optional[str], lang: Optional[str]) -> bool:
    """Return whether the engine can build a recognizer for *lang* at *version*.

    ``version=None`` asks about the engine's default choice, which is what runs
    when a profile leaves ``ocr_version`` unset. A release the installed engine
    does not know is unsupported: PaddleOCR rejects it before looking at *lang*.
    """
    if not lang:
        return True
    versions, supports, _ = _capabilities()
    if version and version not in versions:
        return False
    return supports(version or None, lang)


def lang_supported(lang: Optional[str]) -> bool:
    """Whether *lang* resolves at all when no release is pinned."""
    return version_supports_lang(None, lang)


def versions_for_lang(lang: Optional[str]) -> List[str]:
    """List the PP-OCR releases that can handle *lang*, newest first."""
    return [v for v in available_versions() if version_supports_lang(v, lang)]


def supported_langs(version: str, candidates: Iterable[str]) -> List[str]:
    """Filter *candidates* down to the languages *version* can recognize."""
    return [lang for lang in candidates if version_supports_lang(version, lang)]


def engine_param_error(params: Dict[str, Any]) -> Optional[str]:
    """Why PaddleOCR would refuse to build from *params*, or None if it would build.

    *params* uses 3.x names (the output of :func:`normalize_params`). The checks
    run in the order PaddleOCR.__init__ runs them: the release name first, even
    when a custom model is given; then, if a custom model is given, nothing else,
    because lang and ocr_version stop mattering; otherwise the (lang, release)
    pair must resolve to a recognizer. An unset lang is fine: the engine falls
    back to 'ch', which every release has.
    """
    version = params.get("ocr_version") or None
    lang = params.get("lang") or None
    if version and version not in available_versions():
        return explain_unsupported(version, lang)
    if any(params.get(key) for key in CUSTOM_MODEL_KEYS):
        return None
    if not version_supports_lang(version, lang):
        return explain_unsupported(version, lang)
    return None


def explain_unsupported(version: Optional[str], lang: Optional[str]) -> str:
    """Human-readable reason why *lang* cannot be used, naming what can.

    ASCII only: this string is logged, and a Windows console on a Thai codepage
    raises UnicodeEncodeError on characters like an em dash.
    """
    if version and version not in available_versions():
        return (
            f"{version} is not available in the installed engine "
            f"({capability_source()}); choose one of {', '.join(available_versions())}."
        )
    if lang in _RETIRED_LANG_CODES and not lang_supported(lang):
        return (
            f"'{lang}' is a PaddleOCR 2.x script-group code that 3.x does not "
            f"recognize; choose {_RETIRED_LANG_CODES[lang]}."
        )
    working = versions_for_lang(lang)
    reason = f"{version or 'The default release'} has no '{lang}' recognition model"
    if working:
        return f"{reason}. Use {working[0]} instead."
    return f"{reason}, and no release in {capability_source()} has one."


def engine_version() -> str:
    """Report the installed PaddleOCR version, or ``'unknown'`` if unavailable."""
    try:
        import paddleocr

        return str(getattr(paddleocr, "__version__", "unknown"))
    except Exception:  # noqa: BLE001 - reporting must never break the caller
        return "unknown"
