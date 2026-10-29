"""
Check that a GPU image really runs OCR on the GPU.

CI builds the GPU images but has no GPU, so this is the check to run by hand
on a GPU host before a GPU stage is trusted (for example before the CUDA 12.6
stage takes over the runtime-web-gpu name; see docs/MAINTENANCE.md).

Web image (it does not copy scripts/, so mount them):

    docker run --rm --gpus all -v "$PWD/scripts:/app/scripts:ro" \\
        ocrstudio-web-gpu:runtime-web-gpu-cu126 python scripts/gpu_smoke_check.py

Desktop image:

    docker run --rm --gpus all -e MODE=headless <image> \\
        python scripts/gpu_smoke_check.py

The first detection downloads the PP-OCR models, so the host needs internet
access, or mount pre-downloaded weights the same way the app does. Exits 0
when every check passes, 1 otherwise.
"""

import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

failures = []


def check(ok, what):
    print(f"  [{'PASS' if ok else 'FAIL'}] {what}")
    if not ok:
        failures.append(what)
    return ok


print("\n== PaddlePaddle ==")
import paddle  # noqa: E402

print(f"  paddle {paddle.__version__}")
cuda_build = paddle.device.is_compiled_with_cuda()
check(cuda_build, "paddle is the CUDA build")
if cuda_build:
    print(f"  built for CUDA {paddle.version.cuda()}, cuDNN {paddle.version.cudnn()}")
gpus = paddle.device.cuda.device_count() if cuda_build else 0
check(gpus > 0, f"paddle sees a GPU (count={gpus}); is the container started with --gpus?")
if failures:
    sys.exit(1)
print(f"  GPU 0: {paddle.device.cuda.get_device_name(0)}")

print("\n== paddle.utils.run_check() ==")
try:
    paddle.utils.run_check()
    check(True, "run_check")
except Exception as exc:  # noqa: BLE001 - report any failure, keep going
    check(False, f"run_check: {exc}")

print("\n== OCR through the app's detector (profile=gpu) ==")
import cv2  # noqa: E402
import numpy as np  # noqa: E402

from modules.core.ocr.detector import TextDetector  # noqa: E402

detector = TextDetector(profile="gpu")
check(detector.use_gpu, "detector configured for GPU")
device = paddle.device.get_device()
check(device.startswith("gpu"), f"paddle device is {device}")

img = np.full((400, 1000, 3), 255, np.uint8)
for i, line in enumerate(["OCR STUDIO 2026", "GPU SMOKE TEST", "TOTAL 1,250.00"]):
    cv2.putText(img, line, (40, 100 + i * 110), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4)
with tempfile.TemporaryDirectory() as tmp:
    path = str(Path(tmp) / "smoke.png")
    cv2.imwrite(path, img)
    timings = []
    for _ in range(2):  # the first run includes model load and warm-up
        start = time.perf_counter()
        results = detector.detect(path)
        timings.append(time.perf_counter() - start)

print(f"  first run {timings[0]:.2f}s, second run {timings[1]:.2f}s")
texts = [r.get("transcription", "") for r in results]
print(f"  {len(results)} boxes: {texts}")
check(len(results) >= 3, "found the three text lines")
peak = paddle.device.cuda.max_memory_allocated(0) / 2**20
check(peak > 0, f"GPU memory was used (peak {peak:.0f} MiB)")

print("\n" + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} CHECK(S) FAILED"))
sys.exit(1 if failures else 0)
