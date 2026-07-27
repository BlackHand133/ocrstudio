"""Config / profile endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.core.ocr.compat import (
    OCR_VERSIONS,
    PARAM_ALIASES,
    engine_version,
    explain_unsupported,
    supported_langs,
    version_supports_lang,
)
from server import schemas
from server.deps import get_config, peek_detector, reset_detector

router = APIRouter(prefix="/api/config", tags=["config"])

# Common PaddleOCR language codes (not exhaustive — UI lets you pick).
LANGUAGES = [
    "th",
    "en",
    "ch",
    "chinese_cht",
    "japan",
    "korean",
    "latin",
    "arabic",
    "cyrillic",
    "devanagari",
]


def _version_languages() -> dict:
    """Languages per PP-OCR release, restricted to the codes the UI offers.

    Versions with no documented restriction are omitted entirely — the client
    treats a missing key as "all languages allowed" rather than as an empty set.
    """
    out = {}
    for version in OCR_VERSIONS:
        allowed = supported_langs(version)
        if allowed is None:
            continue
        out[version] = [lang for lang in LANGUAGES if lang in allowed]
    return out


def _info() -> schemas.ConfigResponse:
    cfg = get_config()
    return schemas.ConfigResponse(
        profiles=cfg.list_profiles(),
        current_profile=cfg.get_current_profile(),
        languages=LANGUAGES,
        ocr_versions=list(OCR_VERSIONS),
        version_languages=_version_languages(),
    )


@router.get("", response_model=schemas.ConfigResponse)
def get_config_info() -> schemas.ConfigResponse:
    return _info()


@router.get("/engine")
def get_engine_status() -> dict:
    """What the OCR engine is actually running right now.

    Reports the *loaded* detector rather than the saved config, so the settings
    UI can show real state instead of the user's last-saved intent. Never
    raises: an engine that has not been built yet (or failed to build) is a
    normal state to display, not an error.
    """
    detector = peek_detector()

    status: dict = {
        "engine": "PaddleOCR",
        "engine_version": engine_version(),
        "loaded": detector is not None,
    }

    if detector is not None:
        try:
            status.update(detector.get_model_info())
        except Exception as exc:  # noqa: BLE001 - status must never 500
            status["error"] = str(exc)

    cfg = get_config()
    profile = cfg.get_current_profile()
    params = cfg.get_paddleocr_params(profile)
    status["pending"] = {
        "profile": profile,
        "lang": params.get("lang"),
        "ocr_version": params.get("ocr_version"),
    }
    status["config_warnings"] = cfg.validate()
    return status


class SetProfileRequest(BaseModel):
    profile: str


@router.put("/profile", response_model=schemas.ConfigResponse)
def set_profile(req: SetProfileRequest) -> schemas.ConfigResponse:
    cfg = get_config()
    try:
        cfg.set_current_profile(req.profile)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    reset_detector()  # reload OCR with the newly selected profile
    return _info()


class ProfileParams(BaseModel):
    """Editable slice of a profile.

    Fields use PaddleOCR 3.x names. The ``det_db_*`` aliases are still accepted
    so older clients and scripts keep working; they are rewritten to the 3.x
    spelling before anything is stored.
    """

    lang: Optional[str] = None
    ocr_version: Optional[str] = None
    text_detection_model_name: Optional[str] = None
    text_recognition_model_name: Optional[str] = None
    text_detection_model_dir: Optional[str] = None
    text_recognition_model_dir: Optional[str] = None
    text_det_box_thresh: Optional[float] = None
    text_det_unclip_ratio: Optional[float] = None
    text_det_limit_side_len: Optional[int] = None
    max_image_size: Optional[int] = None
    use_textline_orientation: Optional[bool] = None

    # Deprecated 2.x aliases (accepted on input, never returned).
    det_db_box_thresh: Optional[float] = None
    det_db_unclip_ratio: Optional[float] = None


_EDITABLE = (
    "lang",
    "ocr_version",
    "text_detection_model_name",
    "text_recognition_model_name",
    "text_detection_model_dir",
    "text_recognition_model_dir",
    "text_det_box_thresh",
    "text_det_unclip_ratio",
    "text_det_limit_side_len",
    "max_image_size",
    "use_textline_orientation",
)


def _profile_view(cfg, name: str) -> dict:
    params = cfg.get_paddleocr_params(name)
    return {"name": name, "params": {k: params.get(k) for k in _EDITABLE}}


@router.get("/profiles/{name}")
def get_profile_params(name: str) -> dict:
    cfg = get_config()
    if name not in cfg.list_profiles():
        raise HTTPException(404, "Profile not found")
    return _profile_view(cfg, name)


@router.put("/profiles/{name}")
def update_profile_params(name: str, body: ProfileParams) -> dict:
    cfg = get_config()
    if name not in cfg.list_profiles():
        raise HTTPException(404, "Profile not found")

    paddle = cfg.get_profile_config(name).setdefault("paddleocr", {})
    data = body.model_dump(exclude_unset=True)

    # Fold deprecated 2.x aliases into their 3.x names. An explicit new-style
    # value always wins; storing both would make PaddleOCR raise on startup.
    for old_key, new_key in PARAM_ALIASES.items():
        if old_key not in data:
            continue
        val = data.pop(old_key)
        if val is not None and data.get(new_key) is None:
            data[new_key] = val

    # Reject combinations that have no model behind them, rather than letting
    # detection fail later with an opaque PaddleOCR error.
    version = data.get("ocr_version", paddle.get("ocr_version"))
    lang = data.get("lang", paddle.get("lang"))
    if version and lang and not version_supports_lang(version, lang):
        raise HTTPException(400, explain_unsupported(version, lang))

    for key in _EDITABLE:
        if key not in data:
            continue
        val = data[key]
        # None / blank string => use official default: drop the custom key so
        # PaddleOCR never receives a stale path/name (clean official<->custom switch).
        if val is None or (isinstance(val, str) and not val.strip()):
            paddle.pop(key, None)
        else:
            cfg.update_profile_setting(name, f"paddleocr.{key}", val)

    try:
        cfg.save()
    except Exception:  # noqa: BLE001 - persistence is best-effort
        pass
    reset_detector()  # reload OCR with new models/params on next detect
    return _profile_view(cfg, name)
