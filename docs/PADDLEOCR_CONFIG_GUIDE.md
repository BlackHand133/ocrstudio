# PaddleOCR Configuration Guide

How OCR Studio configures PaddleOCR, which knobs matter, and how to tune
detection for Thai.

Applies to **PaddleOCR 3.x** (`paddleocr>=3.0.0`). The detector uses the 3.x API
(`predict()` / `rec_polys`); 2.x will not work.

---

## Where configuration lives

| File | Purpose |
|------|---------|
| `config/config.yaml` | The file that matters. Profiles (`cpu` / `gpu`), app settings, paths. |
| `data/app_config.json` | Runtime app state (current workspace, window size). |

> **`config/config.yaml` is regenerated whenever settings are saved from the UI.**
> It is written with `yaml.safe_dump`, which does not round-trip comments — any
> you add are lost on the next save. Keep notes in this document instead.

`config/profiles/*.yaml` is a legacy fallback, read only when `config.yaml` has
no `profiles` section. New setups should ignore it.

---

## Parameter names: 2.x → 3.x

PaddleOCR 3.x renamed the tuning parameters, and **refuses to start when a
deprecated name and its replacement are both supplied**. Configs written for 2.x
therefore stop taking effect silently — the slider moves, the value saves, and
nothing reaches the engine.

OCR Studio migrates them automatically on load (see
`modules/core/ocr/compat.py`) and rewrites `config.yaml` once, so old configs
keep working. The full rename table:

| Deprecated (2.x) | Current (3.x) |
|------------------|---------------|
| `det_model_dir` | `text_detection_model_dir` |
| `det_limit_side_len` | `text_det_limit_side_len` |
| `det_limit_type` | `text_det_limit_type` |
| `det_db_thresh` | `text_det_thresh` |
| `det_db_box_thresh` | `text_det_box_thresh` |
| `det_db_unclip_ratio` | `text_det_unclip_ratio` |
| `rec_model_dir` | `text_recognition_model_dir` |
| `rec_batch_num` | `text_recognition_batch_size` |
| `use_angle_cls` | `use_textline_orientation` |
| `cls_model_dir` | `textline_orientation_model_dir` |
| `cls_batch_num` | `textline_orientation_batch_size` |

The REST API still accepts the old names on input, but always stores and returns
the new ones.

---

## PP-OCR version × language

`ocr_version` accepts `PP-OCRv6`, `PP-OCRv5`, `PP-OCRv4`, `PP-OCRv3`. Leave it
unset to let PaddleOCR pick its own default.

> **PP-OCRv6 has no Thai model.** Its unified model covers Chinese, English,
> Japanese and Latin-script languages only. Pairing it with `lang: "th"` produces
> an engine that cannot read the text.

The settings UI greys out impossible combinations, and the API rejects them with
HTTP 400 rather than letting detection fail later with an opaque error.

**For Thai, use `PP-OCRv5`** — it is the release that ships a Thai recognition
model.

---

## Tuning detection for Thai

Thai stacks up to four levels on one base consonant (tone mark, upper vowel,
consonant, lower vowel). Tone marks are one or two pixels thick, so they are the
first thing lost to a tight detection box or a downscale — which is what produces
"floating vowels": a mark rendered with no consonant under it.

The three settings that matter, in the order worth trying:

### 1. `max_image_size` (OCR Studio, not PaddleOCR)

Longest side an image is resized to before detection. **`0` disables the resize.**

Downscaling a high-resolution scan blurs thin marks into the glyph body. If marks
vanish on large images, raise this or set it to `0`.

```yaml
max_image_size: 0      # never resize; slowest, but loses nothing
```

### 2. `text_det_unclip_ratio`

How far the detection box is expanded past the detected text region. The default
hugs the consonant body and crops the marks above and below it.

```yaml
text_det_unclip_ratio: 2.2    # default 1.5 — raise until marks stay inside the box
```

### 3. `text_det_box_thresh`

Confidence needed to keep a box. Lower it so faint, thin marks are not discarded.

```yaml
text_det_box_thresh: 0.5      # default 0.7
```

The settings dialog has a **Thai (preserve tone marks)** preset that applies all
three at once.

### Diagnosing which stage is at fault

Crop the detection boxes and look at them before changing anything:

- Mark is **outside** the crop → detection problem; use the settings above.
- Mark is **inside** the crop but missing from the text → recognition problem.
  More unclip will not help; you need a better recognition model.

---

## Using custom models

Point a profile at your own trained models:

```yaml
profiles:
  cpu:
    paddleocr:
      text_detection_model_dir: "models/det/my_det_model"
      text_recognition_model_dir: "models/rec/my_rec_model"
```

Paths are relative to the repo root. Setting either one switches the settings UI
to "Custom model" mode; clearing both returns to the official models.
`ocr_version` is ignored while custom directories are set.

Model directories must contain the PaddleOCR inference files
(`inference.pdmodel`, `inference.pdiparams`, ...). Startup validation warns about
paths that do not exist.

---

## Parameter reference

### Model selection

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lang` | str | `"th"` | Recognition language |
| `ocr_version` | str | unset | `PP-OCRv6` / `v5` / `v4` / `v3` |
| `device` | str | `"cpu"` | `"cpu"` or `"gpu"` |
| `text_detection_model_name` | str | unset | Official model name |
| `text_detection_model_dir` | str | unset | Custom detection model path |
| `text_recognition_model_name` | str | unset | Official model name |
| `text_recognition_model_dir` | str | unset | Custom recognition model path |

### Detection

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_det_box_thresh` | float | 0.7 | Box confidence threshold (0–1) |
| `text_det_unclip_ratio` | float | 1.5 | Box expansion ratio (1–5) |
| `text_det_thresh` | float | unset | Pixel confidence threshold |
| `text_det_limit_side_len` | int | unset | Max side length PaddleOCR resizes to |
| `text_det_limit_type` | str | unset | `"min"` or `"max"` |
| `text_detection_batch_size` | int | unset | Detection batch size |

### Recognition

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_recognition_batch_size` | int | 6 (CPU) / 12 (GPU) | Recognition batch size |
| `text_rec_score_thresh` | float | unset | Minimum score to keep a result (0–1) |

### Features

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_textline_orientation` | bool | true | Text-line orientation (0° vs 180°) |
| `use_doc_orientation_classify` | bool | false | Page orientation (0/90/180/270°) |
| `use_doc_unwarping` | bool | false | Curved-page correction |

### Performance

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_mkldnn` | bool | false | MKL-DNN CPU acceleration |
| `mkldnn_cache_capacity` | int | 10 | MKL-DNN cache size |
| `cpu_threads` | int | 8 | CPU thread count |
| `use_tensorrt` | bool | false | TensorRT GPU acceleration |
| `precision` | str | `"fp32"` | `"fp32"` or `"fp16"` |

> `enable_mkldnn` is **off** by default on purpose: PaddlePaddle 3.x crashes
> during detection with oneDNN + PIR enabled.

### OCR Studio pre-processing

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_image_size` | int | 2500 | Longest side before OCR; `0` disables resizing |

This one is ours, not PaddleOCR's — it is stripped from the parameters before the
engine is constructed.

---

## Checking what is actually running

```
GET /api/config/engine
```

Reports the installed PaddleOCR version, the loaded PP-OCR release, the device,
any parameter rewrites applied at load time, and configuration warnings. It never
builds the engine, so it is safe to call at any time.

The settings dialog shows the same information at the top.

---

## Profiles

`cpu` and `gpu` are separate parameter sets; `default_profile` selects the active
one. Switching profiles in the UI reloads the engine on the next detection.

Set `OCR_PROFILE=gpu` in the environment to force a profile (the GPU container
image does this).

---

## Related

- [PaddleOCR OCR pipeline docs](https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/OCR.html)
- [PaddleOCR model list](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/model_list.en.md)
- `modules/core/ocr/compat.py` — rename table and version/language matrix in code
