"""PaddleOCR version compatibility helpers.

PaddleOCR 3.x renamed most of the detection/recognition tuning parameters that
2.x used.  The old names are *deprecated* and — critically — the library refuses
to accept an old name and its new counterpart at the same time.  Config files
written against 2.x therefore either get ignored or blow up on 3.x.

This module is the single place that knows about those differences:

* :data:`PARAM_ALIASES` — the official 2.x -> 3.x rename table.
* :func:`normalize_params` — rewrite a profile dict to the 3.x spelling.
* :data:`OCR_VERSIONS` / :func:`version_supports_lang` — which PP-OCR release
  can actually handle a given language.

Usage:
    from modules.core.ocr.compat import normalize_params

    params, notes = normalize_params(profile_params)
    ocr = PaddleOCR(**params)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

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


# ===== PP-OCR releases =====
# Newest first: this is the order the settings UI shows.
OCR_VERSIONS: Tuple[str, ...] = ("PP-OCRv6", "PP-OCRv5", "PP-OCRv4", "PP-OCRv3")

# Which languages each release can handle.
#
# ``None`` means "no documented restriction" — we allow the combination rather
# than guess.  Only PP-OCRv6 has a hard allow-list: its unified model covers
# Chinese, English, Japanese and 46 *Latin-script* languages, so non-Latin
# scripts (Thai, Korean, Arabic, Cyrillic, Devanagari...) are out of scope.
_VERSION_LANGS: Dict[str, Optional[frozenset]] = {
    "PP-OCRv6": frozenset({"ch", "en", "japan", "latin"}),
    "PP-OCRv5": None,
    "PP-OCRv4": None,
    "PP-OCRv3": None,
}

# Where a language has a clearly better home, point users at it.
PREFERRED_VERSION: Dict[str, str] = {
    "th": "PP-OCRv5",
    "korean": "PP-OCRv5",
    "chinese_cht": "PP-OCRv5",
    "arabic": "PP-OCRv3",
    "cyrillic": "PP-OCRv3",
    "devanagari": "PP-OCRv3",
}


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
    """Return whether *version* can recognize *lang*.

    Unknown versions and languages are treated as supported — we only block
    combinations we have documented evidence against.
    """
    if not version or not lang:
        return True
    allowed = _VERSION_LANGS.get(version)
    if allowed is None:
        return True
    return lang in allowed


def versions_for_lang(lang: Optional[str]) -> List[str]:
    """List the PP-OCR releases that can handle *lang*, newest first."""
    return [v for v in OCR_VERSIONS if version_supports_lang(v, lang)]


def supported_langs(version: str) -> Optional[List[str]]:
    """Languages a version is documented to support, or ``None`` if unrestricted."""
    allowed = _VERSION_LANGS.get(version)
    return sorted(allowed) if allowed is not None else None


def explain_unsupported(version: str, lang: str) -> str:
    """Human-readable reason why *version* cannot be used with *lang*."""
    suggestion = PREFERRED_VERSION.get(lang) or next(iter(versions_for_lang(lang)), None)
    reason = f"{version} does not include a '{lang}' recognition model"
    if version == "PP-OCRv6":
        # ASCII only: this string is logged, and a Windows console on a Thai
        # codepage raises UnicodeEncodeError on characters like an em dash.
        reason = (
            f"{version} ships one unified model covering Chinese, English, Japanese "
            f"and Latin-script languages; '{lang}' is not among them"
        )
    if suggestion:
        return f"{reason}. Use {suggestion} instead."
    return reason + "."


def engine_version() -> str:
    """Report the installed PaddleOCR version, or ``'unknown'`` if unavailable."""
    try:
        import paddleocr

        return str(getattr(paddleocr, "__version__", "unknown"))
    except Exception:  # noqa: BLE001 - reporting must never break the caller
        return "unknown"
