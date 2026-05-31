"""API smoke / round-trip tests for the web backend.

Verifies the FastAPI layer reads/writes the *exact* on-disk format the desktop
app uses (workspace.json + v1.json), so existing workspaces stay compatible.
"""

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    import server.deps as deps
    from modules.core.workspace.manager import WorkspaceManager

    # Point the workspace manager at a throwaway root so the test never touches
    # the real ./workspaces directory.
    monkeypatch.setattr(deps, "_workspace_manager", WorkspaceManager(str(tmp_path)))

    from server.main import app

    return TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_config(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert "cpu" in body["profiles"]
    assert "th" in body["languages"]


def test_workspace_and_annotation_roundtrip(client, tmp_path):
    # create
    r = client.post("/api/workspaces", json={"name": "Test WS", "description": "x"})
    assert r.status_code == 201, r.text
    ws_id = r.json()["id"]

    # appears in list
    r = client.get("/api/workspaces")
    assert any(w["id"] == ws_id for w in r.json())

    # save annotations (Thai text + a quad)
    key = "img001.jpg"
    payload = {
        "annotations": [
            {
                "points": [[10, 10], [100, 10], [100, 40], [10, 40]],
                "transcription": "สวัสดี",
                "difficult": False,
                "shape": "Quad",
            }
        ],
        "rotation": 0,
    }
    r = client.put(f"/api/workspaces/{ws_id}/annotations/{key}", json=payload)
    assert r.status_code == 200, r.text
    assert r.json()["annotations"][0]["transcription"] == "สวัสดี"

    # read back
    r = client.get(f"/api/workspaces/{ws_id}/annotations/{key}")
    assert r.status_code == 200
    assert len(r.json()["annotations"]) == 1

    # on-disk format matches the desktop app
    v1 = tmp_path / "workspaces" / ws_id / "v1.json"
    assert v1.exists()
    data = json.loads(v1.read_text(encoding="utf-8"))
    ann = data["annotations"][key][0]
    assert ann["points"][0] == [10, 10]
    assert ann["transcription"] == "สวัสดี"
    assert ann["shape"] == "Quad"
    assert data["metadata"]["annotated_images"] == 1
    assert data["metadata"]["total_annotations"] == 1


def test_missing_workspace_404(client):
    r = client.get("/api/workspaces/does-not-exist")
    assert r.status_code == 404


def test_settings_profile_params(client, tmp_path, monkeypatch):
    from modules.config import ConfigManager

    # Isolated config (fallback cpu/gpu profiles), so save() never touches the repo.
    cfg = ConfigManager(str(tmp_path / "cfgroot"))
    monkeypatch.setattr("server.routers.config.get_config", lambda: cfg)

    r = client.get("/api/config/profiles/cpu")
    assert r.status_code == 200
    assert "lang" in r.json()["params"]

    r = client.put("/api/config/profiles/cpu", json={"lang": "en", "det_db_box_thresh": 0.5})
    assert r.status_code == 200, r.text
    assert r.json()["params"]["lang"] == "en"
    assert r.json()["params"]["det_db_box_thresh"] == 0.5

    assert client.get("/api/config/profiles/nope").status_code == 404


def test_settings_custom_model_switch(client, tmp_path, monkeypatch):
    from modules.config import ConfigManager

    cfg = ConfigManager(str(tmp_path / "cfg2"))
    monkeypatch.setattr("server.routers.config.get_config", lambda: cfg)

    # switch to custom models
    r = client.put(
        "/api/config/profiles/cpu",
        json={
            "lang": "th",
            "text_detection_model_dir": "models/det/my",
            "text_recognition_model_dir": "models/rec/my",
        },
    )
    assert r.status_code == 200, r.text
    p = r.json()["params"]
    assert p["text_detection_model_dir"] == "models/det/my"
    assert p["text_recognition_model_dir"] == "models/rec/my"

    # switch back to official: clearing the dirs (null) must drop them
    r = client.put(
        "/api/config/profiles/cpu",
        json={
            "lang": "en",
            "ocr_version": "PP-OCRv5",
            "text_detection_model_dir": None,
            "text_recognition_model_dir": None,
        },
    )
    assert r.status_code == 200
    p = r.json()["params"]
    assert p["text_detection_model_dir"] is None
    assert p["text_recognition_model_dir"] is None
    assert p["lang"] == "en"
    assert p["ocr_version"] == "PP-OCRv5"


def test_thumbnail(client, tmp_path):
    import cv2
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "thumb ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    imwrite_unicode(str(images_dir / "big.png"), np.full((400, 600, 3), 200, dtype=np.uint8), image_format="png")

    r = client.get(f"/api/workspaces/{ws_id}/images/big.png/thumb?size=80")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    thumb = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    assert max(thumb.shape[0], thumb.shape[1]) == 80


def _export_and_wait(client, ws_id, body):
    """POST an export job and poll until it finishes; return the final job dict."""
    import time

    r = client.post(f"/api/workspaces/{ws_id}/export", json=body)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    job = {"status": "running"}
    for _ in range(300):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            break
        time.sleep(0.02)
    return job


def test_export_selected_keys(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "sel ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    box = {"points": [[5, 5], [50, 5], [50, 30], [5, 30]], "transcription": "x", "difficult": False, "shape": "Quad"}
    for name in ("a.png", "b.png"):
        imwrite_unicode(str(images_dir / name), np.full((100, 200, 3), 255, dtype=np.uint8), image_format="png")
        client.put(f"/api/workspaces/{ws_id}/annotations/{name}", json={"annotations": [box], "rotation": 0})

    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0, "selected_keys": ["a.png"]}
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 1


def _make_ws_with_image(client, tmp_path):
    """Create a workspace and drop one synthetic image into its source folder."""
    import numpy as np
    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "export ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    assert images_dir.exists()
    img = np.full((120, 320, 3), 255, dtype=np.uint8)
    assert imwrite_unicode(str(images_dir / "page1.png"), img, image_format="png")
    # listed by the API
    assert any(i["key"] == "page1.png" for i in client.get(f"/api/workspaces/{ws_id}/images").json())
    # annotate one quad with Thai text
    payload = {
        "annotations": [
            {
                "points": [[10, 10], [220, 10], [220, 70], [10, 70]],
                "transcription": "กขค",
                "difficult": False,
                "shape": "Quad",
            }
        ],
        "rotation": 0,
    }
    assert client.put(f"/api/workspaces/{ws_id}/annotations/page1.png", json=payload).status_code == 200
    return ws_id


def test_export_detection(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0, "image_format": "png"}
    )
    assert job["status"] == "done", job
    res = job["result"]
    assert res["total"] == 1 and res["splits"]["train"] == 1

    det_dir = tmp_path / "output_det" / res["folder"]
    assert (det_dir / "img" / "train" / "page1.png").exists()
    label = (det_dir / "labels_train.txt").read_text(encoding="utf-8")
    assert "กขค" in label and "page1.png" in label

    # zip download works
    dl = client.get(res["download_url"])
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/zip"


def test_export_recognition(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "recognition", "train": 100, "valid": 0, "test": 0, "crop_method": "bbox"}
    )
    assert job["status"] == "done", job
    res = job["result"]
    assert res["total"] == 1

    rec_dir = tmp_path / "output_rec" / res["folder"]
    assert (rec_dir / "images" / "train" / "page1_0.png").exists()
    label = (rec_dir / "train.txt").read_text(encoding="utf-8")
    assert "กขค" in label


def test_export_recognition_auto_orient(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client,
        ws_id,
        {"kind": "recognition", "train": 100, "valid": 0, "test": 0, "crop_method": "bbox", "auto_orient": True},
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 1
    rec_dir = tmp_path / "output_rec" / job["result"]["folder"]
    assert (rec_dir / "images" / "train" / "page1_0.png").exists()


def test_export_with_augmentation(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "kind": "detection",
        "train": 100,
        "valid": 0,
        "test": 0,
        "augment": True,
        "aug_mode": "combinatorial",
        "augmentations": [
            {"type": "blur", "params": {"kernel_size": 5}},
            {"type": "grayscale", "params": {}},
        ],
        "aug_targets": ["train"],
    }
    job = _export_and_wait(client, ws_id, body)
    assert job["status"] == "done", job
    res = job["result"]
    # original + 2 augmentations
    assert res["splits"]["train"] == 3

    det_dir = tmp_path / "output_det" / res["folder"]
    files = list((det_dir / "img" / "train").glob("*.png"))
    assert len(files) == 3
    lines = (det_dir / "labels_train.txt").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3


def test_augment_preview_gallery(client, tmp_path):
    """augment-preview returns the original + one inline thumbnail per effect."""
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "kind": "detection",
        "aug_mode": "combinatorial",
        "augmentations": [
            {"type": "blur", "params": {"kernel_size": 5}},
            {"type": "grayscale", "params": {}},
        ],
    }
    r = client.post(f"/api/workspaces/{ws_id}/export/augment-preview", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sample_key"] == "page1.png"
    assert data["box_count"] == 1
    assert data["eligible_count"] == 1 and data["sample_index"] == 0
    assert [s["label"] for s in data["samples"]] == ["original", "blur", "grayscale"]
    assert all(s["image"].startswith("data:image/jpeg;base64,") for s in data["samples"])

    # sample_index wraps around the eligible images (only one here -> back to it)
    r2 = client.post(
        f"/api/workspaces/{ws_id}/export/augment-preview?sample_index=5", json=body
    )
    assert r2.status_code == 200 and r2.json()["sample_index"] == 0

    # max_size render resolution is validated (200..1200)
    assert client.post(
        f"/api/workspaces/{ws_id}/export/augment-preview?max_size=240", json=body
    ).status_code == 200
    assert client.post(
        f"/api/workspaces/{ws_id}/export/augment-preview?max_size=50", json=body
    ).status_code == 422


def test_augment_preview_sequential_adds_combined(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "kind": "detection",
        "aug_mode": "sequential",
        "augmentations": [
            {"type": "blur", "params": {"kernel_size": 5}},
            {"type": "grayscale", "params": {}},
        ],
    }
    r = client.post(f"/api/workspaces/{ws_id}/export/augment-preview", json=body)
    assert r.status_code == 200, r.text
    labels = [s["label"] for s in r.json()["samples"]]
    assert labels[0] == "original" and "combined" in labels


def test_augment_preview_requires_augs(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    r = client.post(
        f"/api/workspaces/{ws_id}/export/augment-preview",
        json={"kind": "detection", "augmentations": []},
    )
    assert r.status_code == 400


def test_preview_split_reports_aug_counts(client, tmp_path):
    """The split preview folds augmentation into the per-split totals."""
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "kind": "detection",
        "train": 100,
        "valid": 0,
        "test": 0,
        "augment": True,
        "aug_mode": "combinatorial",
        "aug_copies": 2,
        "augmentations": [
            {"type": "blur", "params": {"kernel_size": 5}},
            {"type": "grayscale", "params": {}},
        ],
        "aug_targets": ["train"],
    }
    r = client.post(f"/api/workspaces/{ws_id}/export/preview", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1 and data["splits"]["train"] == 1
    # 2 copies x 2 specs = 4 variants/item -> train 1 becomes 1 * (1 + 4) = 5
    assert data["variants_per_item"] == 4
    assert data["aug_splits"]["train"] == 5
    assert data["aug_total"] == 5


def test_preview_split_no_aug_has_no_aug_fields(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    r = client.post(
        f"/api/workspaces/{ws_id}/export/preview",
        json={"kind": "detection", "train": 100, "valid": 0, "test": 0},
    )
    assert r.status_code == 200, r.text
    assert "aug_total" not in r.json()


def test_export_augment_custom_params(client, tmp_path):
    """Custom per-effect params + the color_jitter / shear effects export cleanly."""
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "kind": "detection",
        "train": 100,
        "valid": 0,
        "test": 0,
        "augment": True,
        "aug_mode": "combinatorial",
        "augmentations": [
            {"type": "blur", "params": {"kernel_size": 9}},
            {"type": "color_jitter", "params": {"saturation": 1.5, "hue": 0.1}},
            {"type": "shear", "params": {"shear_x": 0.15, "shear_y": 0.05}},
        ],
        "aug_targets": ["train"],
    }
    job = _export_and_wait(client, ws_id, body)
    assert job["status"] == "done", job
    assert job["result"]["splits"]["train"] == 4  # original + 3 effects
    det_dir = tmp_path / "output_det" / job["result"]["folder"]
    assert len(list((det_dir / "img" / "train").glob("*.png"))) == 4


def test_augment_preview_new_effects(client, tmp_path):
    """color_jitter + shear render in the gallery with custom params."""
    ws_id = _make_ws_with_image(client, tmp_path)
    body = {
        "aug_mode": "combinatorial",
        "augmentations": [
            {"type": "shear", "params": {"shear_x": 0.2, "shear_y": 0.0}},
            {"type": "color_jitter", "params": {"saturation": 1.4, "hue": 0.1}},
        ],
    }
    r = client.post(f"/api/workspaces/{ws_id}/export/augment-preview", json=body)
    assert r.status_code == 200, r.text
    assert [s["label"] for s in r.json()["samples"]] == ["original", "shear", "color_jitter"]


def test_export_solid_mask_burned_in(client, tmp_path):
    import cv2
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "mask ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    imwrite_unicode(str(images_dir / "m.png"), np.full((100, 200, 3), 255, dtype=np.uint8), image_format="png")
    anns = [
        {"points": [[10, 10], [80, 10], [80, 40], [10, 40]], "transcription": "t", "difficult": False, "shape": "Quad"},
        {
            "points": [[100, 50], [150, 50], [150, 90], [100, 90]],
            "transcription": "###",
            "difficult": False,
            "shape": "Mask",
            "mask_color": "#ff0000",
            "mask_mode": "solid",
        },
    ]
    client.put(f"/api/workspaces/{ws_id}/annotations/m.png", json={"annotations": anns, "rotation": 0})

    job = _export_and_wait(client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0})
    assert job["status"] == "done", job
    folder = job["result"]["folder"]
    img = cv2.imread(str(tmp_path / "output_det" / folder / "img" / "train" / "m.png"))
    # mask region is burned solid red (BGR 0,0,255)
    assert tuple(int(v) for v in img[70, 125]) == (0, 0, 255)
    # the mask is excluded from detection labels (only the quad remains)
    label = (tmp_path / "output_det" / folder / "labels_train.txt").read_text(encoding="utf-8")
    assert label.count('"points"') == 1


def test_missing_images(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "miss ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    imwrite_unicode(str(images_dir / "have.png"), np.full((10, 10, 3), 255, dtype=np.uint8), image_format="png")
    box = {"points": [[0, 0], [1, 0], [1, 1], [0, 1]], "transcription": "x", "difficult": False, "shape": "Quad"}
    client.put(f"/api/workspaces/{ws_id}/annotations/have.png", json={"annotations": [box], "rotation": 0})
    client.put(f"/api/workspaces/{ws_id}/annotations/gone.png", json={"annotations": [box], "rotation": 0})

    r = client.get(f"/api/workspaces/{ws_id}/images/missing").json()
    assert r["missing"] == ["gone.png"]
    assert r["missing_count"] == 1
    assert r["present"] == 1


def test_export_empty_400(client):
    ws_id = client.post("/api/workspaces", json={"name": "empty ws"}).json()["id"]
    r = client.post(f"/api/workspaces/{ws_id}/export", json={"kind": "detection", "train": 100})
    assert r.status_code == 400


def test_batch_detect_with_fake_detector(client, tmp_path, monkeypatch):
    import time

    import numpy as np

    import server.deps as deps
    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "batch ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    img = np.full((80, 200, 3), 255, dtype=np.uint8)
    for name in ("a.png", "b.png"):
        imwrite_unicode(str(images_dir / name), img, image_format="png")

    class FakeDetector:
        def detect(self, _path):
            return [{"points": [[1, 1], [20, 1], [20, 15], [1, 15]], "transcription": "x", "score": 0.9}]

    monkeypatch.setattr(deps, "_detector", FakeDetector())

    r = client.post(f"/api/workspaces/{ws_id}/detect", json={"scope": "all"})
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    assert r.json()["total"] == 2

    job = {"status": "running"}
    for _ in range(200):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "error"):
            break
        time.sleep(0.02)
    assert job["status"] == "done", job
    assert job["result"]["processed"] == 2

    imgs = client.get(f"/api/workspaces/{ws_id}/images").json()
    assert all(i["annotation_count"] == 1 for i in imgs)


def test_image_rotation_serve_and_export(client, tmp_path):
    import cv2
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "rot ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    # 200 wide x 80 tall
    imwrite_unicode(str(images_dir / "p.png"), np.full((80, 200, 3), 255, dtype=np.uint8), image_format="png")

    # annotate + rotate 90
    client.put(
        f"/api/workspaces/{ws_id}/annotations/p.png",
        json={
            "annotations": [
                {"points": [[5, 5], [50, 5], [50, 30], [5, 30]], "transcription": "r", "difficult": False, "shape": "Quad"}
            ],
            "rotation": 90,
        },
    )
    assert client.get(f"/api/workspaces/{ws_id}/annotations/p.png").json()["rotation"] == 90

    # served file is rotated (dims swapped -> 200 tall x 80 wide)
    r = client.get(f"/api/workspaces/{ws_id}/images/p.png/file")
    assert r.status_code == 200
    served = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
    assert served.shape[0] == 200 and served.shape[1] == 80

    # exported detection image is rotated too
    job = _export_and_wait(client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0})
    assert job["status"] == "done", job
    out = tmp_path / "output_det" / job["result"]["folder"] / "img" / "train" / "p.png"
    assert out.exists()
    exported = cv2.imread(str(out))
    assert exported.shape[0] == 200 and exported.shape[1] == 80


def test_detect_runs_on_rotated_image(client, tmp_path, monkeypatch):
    import numpy as np

    import server.deps as deps
    from modules.utils import imread_unicode, imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "rotdet"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    # 200 wide x 80 tall
    imwrite_unicode(str(images_dir / "p.png"), np.full((80, 200, 3), 255, dtype=np.uint8), image_format="png")
    client.put(
        f"/api/workspaces/{ws_id}/annotations/p.png",
        json={"annotations": [{"points": [[0, 0], [1, 0], [1, 1], [0, 1]], "transcription": "x", "difficult": False, "shape": "Quad"}], "rotation": 90},
    )

    seen = {}

    class FakeDetector:
        def detect(self, path):
            img = imread_unicode(path)
            seen["shape"] = None if img is None else tuple(img.shape[:2])
            return []

    monkeypatch.setattr(deps, "_detector", FakeDetector())
    r = client.post(f"/api/workspaces/{ws_id}/detect/p.png")
    assert r.status_code == 200
    # detector must see the rotated image (80x200 original -> 200x80 after 90deg)
    assert seen["shape"] == (200, 80)


def test_export_empty_selected_is_not_all(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)  # one annotated image
    r = client.post(
        f"/api/workspaces/{ws_id}/export",
        json={"kind": "detection", "train": 100, "valid": 0, "test": 0, "selected_keys": []},
    )
    assert r.status_code == 400  # explicit empty selection -> nothing to export


def test_export_jpg_format(client, tmp_path):
    """Both pipelines honour image_format=jpg."""
    ws_id = _make_ws_with_image(client, tmp_path)
    det = _export_and_wait(
        client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0, "image_format": "jpg"}
    )
    assert det["status"] == "done", det
    assert (tmp_path / "output_det" / det["result"]["folder"] / "img" / "train" / "page1.jpg").exists()

    rec = _export_and_wait(
        client, ws_id, {"kind": "recognition", "train": 100, "valid": 0, "test": 0, "image_format": "jpg"}
    )
    assert rec["status"] == "done", rec
    assert (
        tmp_path / "output_rec" / rec["result"]["folder"] / "images" / "train" / "page1_0.jpg"
    ).exists()


def test_export_recognition_rotated_crop(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "recognition", "train": 100, "valid": 0, "test": 0, "crop_method": "rotated"}
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 1
    assert (
        tmp_path / "output_rec" / job["result"]["folder"] / "images" / "train" / "page1_0.png"
    ).exists()


def test_export_recognition_augmented(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client,
        ws_id,
        {
            "kind": "recognition",
            "train": 100,
            "valid": 0,
            "test": 0,
            "augment": True,
            "aug_mode": "combinatorial",
            "augmentations": [
                {"type": "grayscale", "params": {}},
                {"type": "sharpen", "params": {"strength": 1}},
            ],
            "aug_targets": ["train"],
        },
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 3  # original crop + 2 augmented crops


def test_export_sequential_aug_mode(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client,
        ws_id,
        {
            "kind": "recognition",
            "train": 100,
            "valid": 0,
            "test": 0,
            "augment": True,
            "aug_mode": "sequential",
            "augmentations": [
                {"type": "blur", "params": {"kernel_size": 5}},
                {"type": "brightness_contrast", "params": {"brightness": 15, "contrast": 1.2}},
            ],
            "aug_targets": ["train"],
        },
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 2  # original + 1 combined (sequential) image


def test_export_multisplit(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "split ws"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    box = {"points": [[5, 5], [50, 5], [50, 30], [5, 30]], "transcription": "x", "difficult": False, "shape": "Quad"}
    for i in range(10):
        name = f"i{i}.png"
        imwrite_unicode(str(images_dir / name), np.full((60, 120, 3), 255, dtype=np.uint8), image_format="png")
        client.put(f"/api/workspaces/{ws_id}/annotations/{name}", json={"annotations": [box], "rotation": 0})

    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "train": 60, "valid": 20, "test": 20, "seed": 42}
    )
    assert job["status"] == "done", job
    s = job["result"]["splits"]
    assert s["train"] + s["valid"] + s["test"] == 10
    assert s["train"] > 0 and s["valid"] > 0 and s["test"] > 0


def test_export_blur_and_pixelate_masks(client, tmp_path):
    """Non-solid censor modes (blur / pixelate) export without error and alter the region."""
    import cv2
    import numpy as np

    from modules.utils import imwrite_unicode

    for mode in ("blur", "pixelate"):
        ws_id = client.post("/api/workspaces", json={"name": f"{mode} ws"}).json()["id"]
        images_dir = tmp_path / "workspaces" / ws_id / "images"
        rng = np.random.default_rng(0)
        noisy = rng.integers(0, 255, (100, 200, 3), dtype=np.uint8)
        imwrite_unicode(str(images_dir / "n.png"), noisy, image_format="png")
        anns = [
            {"points": [[5, 5], [60, 5], [60, 40], [5, 40]], "transcription": "t", "difficult": False, "shape": "Quad"},
            {
                "points": [[100, 50], [180, 50], [180, 95], [100, 95]],
                "transcription": "###",
                "difficult": False,
                "shape": "Mask",
                "mask_mode": mode,
            },
        ]
        client.put(f"/api/workspaces/{ws_id}/annotations/n.png", json={"annotations": anns, "rotation": 0})
        job = _export_and_wait(client, ws_id, {"kind": "detection", "train": 100, "valid": 0, "test": 0})
        assert job["status"] == "done", (mode, job)
        assert job["result"]["total"] == 1  # the mask is not a label
        out = cv2.imread(str(tmp_path / "output_det" / job["result"]["folder"] / "img" / "train" / "n.png"))
        out_region = out[60:90, 110:170]
        assert not np.array_equal(noisy[60:90, 110:170], out_region), mode  # region was censored


def test_detect_box_reocr(client, tmp_path, monkeypatch):
    import numpy as np

    import server.deps as deps
    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "box"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    imwrite_unicode(str(images_dir / "p.png"), np.full((100, 200, 3), 255, dtype=np.uint8), image_format="png")
    client.put(
        f"/api/workspaces/{ws_id}/annotations/p.png",
        json={
            "annotations": [
                {"points": [[10, 10], [100, 10], [100, 40], [10, 40]], "transcription": "old", "difficult": False, "shape": "Quad"}
            ],
            "rotation": 0,
        },
    )

    class FakeDetector:
        def detect(self, _path):
            return [{"points": [[1, 1], [50, 1], [50, 20], [1, 20]], "transcription": "NEW", "score": 0.95}]

    monkeypatch.setattr(deps, "_detector", FakeDetector())
    r = client.post(
        f"/api/workspaces/{ws_id}/detect/p.png/box",
        json={"points": [[10, 10], [100, 10], [100, 40], [10, 40]]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["transcription"] == "NEW"
    assert r.json()["score"] == 0.95


def test_export_icdar_format(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)  # page1.png 320x120, quad "กขค"
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "dataset_format": "icdar", "train": 100, "valid": 0, "test": 0}
    )
    assert job["status"] == "done", job
    d = tmp_path / "output_det" / job["result"]["folder"] / "train"
    assert (d / "images" / "page1.png").exists()
    gt = (d / "gt" / "gt_page1.txt").read_text(encoding="utf-8").strip()
    parts = gt.split(",")
    assert len(parts) == 9  # 8 coords + transcription
    assert all(p.lstrip("-").isdigit() for p in parts[:8])
    assert parts[8] == "กขค"


def test_export_coco_format(client, tmp_path):
    import json as _json

    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "dataset_format": "coco", "train": 100, "valid": 0, "test": 0}
    )
    assert job["status"] == "done", job
    d = tmp_path / "output_det" / job["result"]["folder"] / "train"
    assert (d / "images" / "page1.png").exists()
    coco = _json.loads((d / "instances.json").read_text(encoding="utf-8"))
    assert coco["categories"] == [{"id": 1, "name": "text", "supercategory": "text"}]
    assert len(coco["images"]) == 1 and len(coco["annotations"]) == 1
    a = coco["annotations"][0]
    assert a["category_id"] == 1 and len(a["bbox"]) == 4 and a["segmentation"]
    assert a["text"] == "กขค"
    assert coco["images"][0]["width"] == 320 and coco["images"][0]["height"] == 120


def test_export_yolo_format(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "dataset_format": "yolo", "train": 100, "valid": 0, "test": 0}
    )
    assert job["status"] == "done", job
    base = tmp_path / "output_det" / job["result"]["folder"]
    assert (base / "images" / "train" / "page1.png").exists()
    nums = (base / "labels" / "train" / "page1.txt").read_text(encoding="utf-8").strip().split()
    assert len(nums) == 5 and nums[0] == "0"
    assert all(0.0 <= float(v) <= 1.0 for v in nums[1:])
    yaml = (base / "data.yaml").read_text(encoding="utf-8")
    assert "nc: 1" in yaml and "text" in yaml and "train: images/train" in yaml


def test_export_csv_recognition(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "recognition", "dataset_format": "csv", "train": 100, "valid": 0, "test": 0}
    )
    assert job["status"] == "done", job
    d = tmp_path / "output_rec" / job["result"]["folder"]
    rows = (d / "train.csv").read_text(encoding="utf-8").strip().splitlines()
    assert rows[0] == "image,text"
    assert "กขค" in rows[1] and "images/train/page1_0.png" in rows[1]
    assert (d / "images" / "train" / "page1_0.png").exists()


def test_export_jsonl_detection(client, tmp_path):
    import json as _json

    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "dataset_format": "jsonl", "train": 100, "valid": 0, "test": 0}
    )
    assert job["status"] == "done", job
    d = tmp_path / "output_det" / job["result"]["folder"]
    rec = _json.loads((d / "train.jsonl").read_text(encoding="utf-8").strip().splitlines()[0])
    assert rec["image"] == "img/train/page1.png"
    assert rec["width"] == 320 and rec["height"] == 120
    assert len(rec["boxes"]) == 1 and rec["boxes"][0]["transcription"] == "กขค"
    assert len(rec["boxes"][0]["points"]) == 4
    assert (d / "img" / "train" / "page1.png").exists()


def test_export_icdar_recognition_rejected(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    r = client.post(
        f"/api/workspaces/{ws_id}/export",
        json={"kind": "recognition", "dataset_format": "icdar", "train": 100},
    )
    assert r.status_code == 400


def test_export_split_no_item_dropped(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "nodrop"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    box = {"points": [[5, 5], [50, 5], [50, 30], [5, 30]], "transcription": "x", "difficult": False, "shape": "Quad"}
    for i in range(10):
        imwrite_unicode(str(images_dir / f"i{i}.png"), np.full((60, 120, 3), 255, dtype=np.uint8), image_format="png")
        client.put(f"/api/workspaces/{ws_id}/annotations/i{i}.png", json={"annotations": [box], "rotation": 0})
    # percentages sum to 80 with valid=0 — the 2 leftover images must NOT vanish
    job = _export_and_wait(
        client, ws_id, {"kind": "detection", "train": 70, "valid": 0, "test": 10, "seed": 1}
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 10  # no image silently dropped


def test_export_split_by_count(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "cnt"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    box = {"points": [[5, 5], [50, 5], [50, 30], [5, 30]], "transcription": "x", "difficult": False, "shape": "Quad"}
    for i in range(10):
        imwrite_unicode(str(images_dir / f"i{i}.png"), np.full((60, 120, 3), 255, dtype=np.uint8), image_format="png")
        client.put(f"/api/workspaces/{ws_id}/annotations/i{i}.png", json={"annotations": [box], "rotation": 0})
    job = _export_and_wait(
        client,
        ws_id,
        {"kind": "detection", "split_mode": "count", "train_count": 6, "valid_count": 2, "test_count": 2, "seed": 1},
    )
    assert job["status"] == "done", job
    s = job["result"]["splits"]
    assert s.get("train") == 6 and s.get("valid") == 2 and s.get("test") == 2


def test_export_stratified(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "strat"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    for i in range(9):
        imwrite_unicode(str(images_dir / f"s{i}.png"), np.full((80, 200, 3), 255, dtype=np.uint8), image_format="png")
        nb = 1 if i % 3 == 0 else 3  # vary box density across images
        boxes = [
            {"points": [[5 + 30 * j, 5], [25 + 30 * j, 5], [25 + 30 * j, 25], [5 + 30 * j, 25]], "transcription": "x", "difficult": False, "shape": "Quad"}
            for j in range(nb)
        ]
        client.put(f"/api/workspaces/{ws_id}/annotations/s{i}.png", json={"annotations": boxes, "rotation": 0})
    job = _export_and_wait(
        client,
        ws_id,
        {"kind": "detection", "split_mode": "stratified", "train": 60, "valid": 20, "test": 20, "n_bins": 2, "seed": 3},
    )
    assert job["status"] == "done", job
    assert sum(job["result"]["splits"].values()) == 9  # no image lost


def test_export_aug_copies(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client,
        ws_id,
        {
            "kind": "detection",
            "train": 100,
            "valid": 0,
            "test": 0,
            "augment": True,
            "aug_mode": "combinatorial",
            "aug_copies": 3,
            "augmentations": [{"type": "rotation", "params": {"angle": 3}}],
            "aug_targets": ["train"],
            "seed": 7,
        },
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 4  # original + 3 randomized copies


def test_export_icdar_augmented(client, tmp_path):
    import os as _os

    ws_id = _make_ws_with_image(client, tmp_path)
    job = _export_and_wait(
        client,
        ws_id,
        {
            "kind": "detection",
            "dataset_format": "icdar",
            "train": 100,
            "valid": 0,
            "test": 0,
            "augment": True,
            "aug_mode": "combinatorial",
            "augmentations": [{"type": "blur", "params": {"kernel_size": 5}}, {"type": "grayscale", "params": {}}],
            "aug_targets": ["train"],
        },
    )
    assert job["status"] == "done", job
    assert job["result"]["total"] == 3  # augmentation now works for ICDAR too
    imgs = tmp_path / "output_det" / job["result"]["folder"] / "train" / "images"
    assert len(_os.listdir(imgs)) == 3


def test_export_recognition_group_by_image(client, tmp_path):
    import numpy as np

    from modules.utils import imwrite_unicode

    ws_id = client.post("/api/workspaces", json={"name": "grp"}).json()["id"]
    images_dir = tmp_path / "workspaces" / ws_id / "images"
    for i in range(4):
        imwrite_unicode(str(images_dir / f"g{i}.png"), np.full((60, 200, 3), 255, dtype=np.uint8), image_format="png")
        boxes = [
            {"points": [[5, 5], [40, 5], [40, 30], [5, 30]], "transcription": "a", "difficult": False, "shape": "Quad"},
            {"points": [[50, 5], [90, 5], [90, 30], [50, 30]], "transcription": "b", "difficult": False, "shape": "Quad"},
        ]
        client.put(f"/api/workspaces/{ws_id}/annotations/g{i}.png", json={"annotations": boxes, "rotation": 0})
    job = _export_and_wait(
        client,
        ws_id,
        {"kind": "recognition", "train": 50, "valid": 0, "test": 50, "group_by_image": True, "seed": 2},
    )
    assert job["status"] == "done", job
    s = job["result"]["splits"]
    assert sum(s.values()) == 8  # 4 images x 2 crops
    assert all(v % 2 == 0 for v in s.values()), s  # whole images stay together (no leakage)


def test_export_preview(client, tmp_path):
    ws_id = _make_ws_with_image(client, tmp_path)
    r = client.post(
        f"/api/workspaces/{ws_id}/export/preview",
        json={"kind": "detection", "train": 100, "valid": 0, "test": 0},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unit"] == "images" and body["total"] == 1
    assert body["splits"]["train"] == 1


def test_versioning_crud(client):
    ws_id = client.post("/api/workspaces", json={"name": "ver ws"}).json()["id"]

    vers = client.get(f"/api/workspaces/{ws_id}/versions").json()
    assert [v["name"] for v in vers] == ["v1"]
    assert vers[0]["is_current"]

    # annotate v1
    client.put(
        f"/api/workspaces/{ws_id}/annotations/x.png",
        json={
            "annotations": [
                {"points": [[0, 0], [1, 0], [1, 1], [0, 1]], "transcription": "a", "difficult": False, "shape": "Quad"}
            ],
            "rotation": 0,
        },
    )

    # create v2 from v1 -> becomes current and copies annotations
    assert client.post(f"/api/workspaces/{ws_id}/versions", json={"name": "v2"}).status_code == 201
    assert client.get(f"/api/workspaces/{ws_id}").json()["current_version"] == "v2"
    assert len(client.get(f"/api/workspaces/{ws_id}/annotations/x.png").json()["annotations"]) == 1

    # switch back, then deletion rules
    assert client.post(f"/api/workspaces/{ws_id}/versions/v1/switch").status_code == 200
    assert client.get(f"/api/workspaces/{ws_id}").json()["current_version"] == "v1"
    assert client.delete(f"/api/workspaces/{ws_id}/versions/v1").status_code == 400  # current
    assert client.delete(f"/api/workspaces/{ws_id}/versions/v2").status_code == 200
    assert [v["name"] for v in client.get(f"/api/workspaces/{ws_id}/versions").json()] == ["v1"]
