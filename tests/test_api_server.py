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
