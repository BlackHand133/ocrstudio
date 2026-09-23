"""Config / profile endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from modules.core.ocr.compat import (
    PARAM_ALIASES,
    available_versions,
    capability_source,
    engine_param_error,
    engine_version,
    lang_supported,
    supported_langs,
)
from server import schemas
from server.deps import get_config, peek_detector, reset_detector

router = APIRouter(prefix="/api/config", tags=["config"])

# Language codes offered in the settings UI. 'latin', 'arabic', 'cyrillic' and
# 'devanagari' used to be listed too: they are PaddleOCR 2.x script-group codes
# that no 3.x release resolves, so choosing one built an engine that could not
# start. _offered_languages() also filters against the installed engine.
LANGUAGES = [
    "th",
    "en",
    "ch",
    "chinese_cht",
    "japan",
    "korean",
]


def _offered_languages() -> list:
    return [lang for lang in LANGUAGES if lang_supported(lang)]


def _version_languages() -> dict:
    """Languages per PP-OCR release, restricted to the codes the UI offers.

    Every release the installed engine accepts is listed, even when the list is
    empty, so the client never has to guess what an absent key means.
    """
    offered = _offered_languages()
    return {version: supported_langs(version, offered) for version in available_versions()}


def _info() -> schemas.ConfigResponse:
    cfg = get_config()
    return schemas.ConfigResponse(
        profiles=cfg.list_profiles(),
        current_profile=cfg.get_current_profile(),
        languages=_offered_languages(),
        ocr_versions=list(available_versions()),
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
        # Which answer the version/language checks are giving: the installed
        # engine's own resolver, or the static fallback when it is not importable.
        "capability_source": capability_source(),
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


def _blank(val) -> bool:
    """None or a blank string: "use the official default" for that key."""
    return val is None or (isinstance(val, str) and not val.strip())


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

    # Reject a profile PaddleOCR would refuse to build, checked against what the
    # profile will hold after this save, rather than letting detection fail
    # later with an opaque error.
    after = {k: v for k, v in {**paddle, **data}.items() if not _blank(v)}
    problem = engine_param_error(after)
    if problem:
        raise HTTPException(400, problem)

    for key in _EDITABLE:
        if key not in data:
            continue
        val = data[key]
        # None / blank string => use official default: drop the custom key so
        # PaddleOCR never receives a stale path/name (clean official<->custom switch).
        if _blank(val):
            paddle.pop(key, None)
        else:
            cfg.update_profile_setting(name, f"paddleocr.{key}", val)

    try:
        cfg.save()
    except Exception:  # noqa: BLE001 - persistence is best-effort
        pass
    reset_detector()  # reload OCR with new models/params on next detect
    return _profile_view(cfg, name)
