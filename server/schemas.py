"""Pydantic request/response models.

The ``Annotation`` shape mirrors the on-disk format exactly (see
``modules/core/workspace`` and ARCHITECTURE.md) so the API stays 100%
compatible with workspaces created by the desktop app.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Annotation(BaseModel):
    points: List[List[float]]
    transcription: str = ""
    difficult: bool = False
    shape: str = "Quad"  # "Quad" | "Polygon" | "Mask"
    score: Optional[float] = None
    mask_color: Optional[str] = None
    mask_mode: Optional[str] = None  # censor mode: "solid" | "blur" | "pixelate"


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    source_folder: str = ""
    created_at: str = ""
    modified_at: str = ""
    current_version: str = "v1"
    available_versions: List[str] = Field(default_factory=list)


class WorkspaceDetail(WorkspaceSummary):
    image_count: int = 0
    annotated_count: int = 0


class CreateWorkspaceRequest(BaseModel):
    name: str
    description: str = ""
    # If given, use an existing (e.g. volume-mounted) folder of images.
    # If omitted, an internal images/ dir is created and used (portable).
    source_folder: Optional[str] = None


class CreateWorkspaceResponse(BaseModel):
    id: str


class ImageInfo(BaseModel):
    key: str
    has_annotations: bool = False
    annotation_count: int = 0


class AnnotationsResponse(BaseModel):
    key: str
    rotation: int = 0
    annotations: List[Annotation] = Field(default_factory=list)


class SaveAnnotationsRequest(BaseModel):
    annotations: List[Annotation] = Field(default_factory=list)
    rotation: int = 0


class DetectResponse(BaseModel):
    key: str
    annotations: List[Annotation] = Field(default_factory=list)


class BatchDetectRequest(BaseModel):
    scope: str = "empty"  # "empty" | "all" | "selected"
    keys: Optional[List[str]] = None
    overwrite: bool = False


class BatchDetectResponse(BaseModel):
    job_id: str
    total: int


class VersionInfo(BaseModel):
    name: str
    is_current: bool = False
    description: str = ""
    created_at: str = ""
    modified_at: str = ""
    metadata: dict = Field(default_factory=dict)


class CreateVersionRequest(BaseModel):
    name: str
    base: Optional[str] = None  # copy from this version (default: current)
    description: str = ""


class ConfigResponse(BaseModel):
    profiles: List[str]
    current_profile: str
    languages: List[str]


class MessageResponse(BaseModel):
    ok: bool = True
    message: str = ""


class AugSpec(BaseModel):
    type: str
    params: dict = Field(default_factory=dict)


class ExportRequest(BaseModel):
    kind: str = "detection"  # "detection" | "recognition"
    # Output format. "paddleocr" supports both kinds; icdar/coco/yolo are
    # detection-only; csv/jsonl are generic manifests for either kind.
    dataset_format: str = "paddleocr"  # paddleocr | icdar | coco | yolo | csv | jsonl
    train: float = 80
    valid: float = 10
    test: float = 10
    seed: Optional[int] = None
    image_format: str = "png"  # "png" | "jpg"
    crop_method: str = "bbox"  # recognition only: "bbox" | "rotated"
    auto_orient: bool = False  # recognition only: rotate crops upright
    selected_keys: Optional[List[str]] = None  # None = all annotated images
    # Augmentation (applied to target splits only)
    augment: bool = False
    aug_mode: str = "combinatorial"  # "combinatorial" (1 img/aug) | "sequential"
    augmentations: List[AugSpec] = Field(default_factory=list)
    aug_targets: List[str] = Field(default_factory=lambda: ["train"])


class ExportResult(BaseModel):
    kind: str
    folder: str
    splits: Dict[str, int]
    total: int
    download_url: str


class ExportJobResponse(BaseModel):
    job_id: str
