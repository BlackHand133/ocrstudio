"""Config / profile endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server import schemas
from server.deps import get_config, reset_detector

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


def _info() -> schemas.ConfigResponse:
    cfg = get_config()
    return schemas.ConfigResponse(
        profiles=cfg.list_profiles(),
        current_profile=cfg.get_current_profile(),
        languages=LANGUAGES,
    )


@router.get("", response_model=schemas.ConfigResponse)
def get_config_info() -> schemas.ConfigResponse:
    return _info()


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
    lang: Optional[str] = None
    ocr_version: Optional[str] = None
    text_detection_model_name: Optional[str] = None
    text_recognition_model_name: Optional[str] = None
    text_detection_model_dir: Optional[str] = None
    text_recognition_model_dir: Optional[str] = None
    det_db_box_thresh: Optional[float] = None
    det_db_unclip_ratio: Optional[float] = None
    use_textline_orientation: Optional[bool] = None


_EDITABLE = (
    "lang",
    "ocr_version",
    "text_detection_model_name",
    "text_recognition_model_name",
    "text_detection_model_dir",
    "text_recognition_model_dir",
    "det_db_box_thresh",
    "det_db_unclip_ratio",
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
    data = body.model_dump()
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
