# PaddleOCR Configuration Guide

**Version**: 2.4.0
**Date**: 2025-11-11
**Purpose**: Complete guide for PaddleOCR configuration with custom models

---

## 📋 Overview

The enhanced configuration system now supports **all PaddleOCR 3.0 parameters** with an easy-to-use GUI featuring checkboxes for custom model paths.

### Key Features:

✅ **Checkbox-based control** - Enable/disable custom settings easily
✅ **Custom model paths** - Use your own trained models
✅ **Advanced parameters** - Fine-tune detection and recognition
✅ **Profile-based** - Separate settings for CPU and GPU
✅ **Default fallback** - Unchecked = use PaddleOCR defaults

---

## 🎯 Quick Start

### Basic Usage (Default Models):

1. Open the application
2. Go to **Settings** → **PaddleOCR Advanced Settings**
3. All checkboxes unchecked = **using default PaddleOCR models** ✅
4. Adjust thresholds if needed (sliders available)

### Using Custom Models:

1. Place your model in `models/` folder:
   ```
   models/
   ├── det/
   │   └── my_detection_model/
   │       ├── inference.pdmodel
   │       ├── inference.pdiparams
   │       └── inference.pdiparams.info
   └── rec/
       └── my_recognition_model/
           ├── inference.pdmodel
           └── ...
   ```

2. Open **PaddleOCR Advanced Settings**
3. Go to **Custom Models** tab
4. ✅ Check "Use custom detection model"
5. Enter:
   - Model Name: `my_detection_model`
   - Model Directory: `models/det/my_detection_model` (or browse)
6. Click **OK**

---

## 📁 Configuration Files

### Location:
```
config/
├── default.yaml              # Main config (which profile to use)
├── paths.yaml                # Path configurations
└── profiles/
    ├── cpu.yaml              # CPU profile settings
    └── gpu.yaml              # GPU profile settings
```

### Profile Structure (cpu.yaml / gpu.yaml):

```yaml
paddleocr:
  # ===== Basic Settings =====
  lang: "th"                  # Language (th, en, ch, etc.)
  device: "cpu"               # Device: cpu or gpu

  # ===== Custom Models =====
  # Detection Model (uncomment to use custom)
  # use_custom_detection_model: true
  # text_detection_model_name: "my_det_model"
  # text_detection_model_dir: "models/det/my_det_model"

  # Recognition Model (uncomment to use custom)
  # use_custom_recognition_model: true
  # text_recognition_model_name: "my_rec_model"
  # text_recognition_model_dir: "models/rec/my_rec_model"

  # ===== Detection Parameters =====
  det_db_box_thresh: 0.7      # Higher = stricter (0.5-0.9)
  det_db_unclip_ratio: 1.5    # Higher = larger boxes (1.0-2.5)

  # ===== Recognition Parameters =====
  rec_batch_num: 6            # Batch size
  drop_score: 0.5             # Min confidence (0.0-1.0)

  # ===== Features =====
  use_angle_cls: true         # 180° rotation detection
  use_doc_orientation_classify: false
  use_doc_unwarping: false
  use_textline_orientation: false
```

---

## 🖥️ GUI Settings Dialog

### File: `modules/gui/dialogs/paddleocr_settings_dialog.py`

### Usage in Application:

```python
from modules.gui.dialogs.paddleocr_settings_dialog import PaddleOCRSettingsDialog

# Create and show dialog
dialog = PaddleOCRSettingsDialog(parent=main_window)
dialog.settings_changed.connect(on_settings_changed)
dialog.exec_()
```

### Dialog Tabs:

1. **Custom Models** 📦
   - Detection model checkbox + path
   - Recognition model checkbox + path
   - Browse button for easy selection

2. **Detection** 🔍
   - Box threshold slider
   - Unclip ratio slider
   - Advanced parameters (optional)

3. **Recognition** 📝
   - Batch size
   - Score threshold slider

4. **Features** ⚙️
   - Angle classification checkbox
   - Document orientation checkbox
   - Document unwarping checkbox
   - Text line orientation checkbox

5. **Performance** ⚡
   - CPU: MKL-DNN, threads
   - GPU: TensorRT, precision (fp32/fp16)

---

## 📚 Complete Parameter Reference

### Detection Model Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_detection_model_name` | str | null | Model name |
| `text_detection_model_dir` | str | null | Path to model directory |
| `det_db_box_thresh` | float | 0.7 | Box confidence threshold (0.5-0.9) |
| `det_db_unclip_ratio` | float | 1.5 | Box expansion ratio (1.0-2.5) |
| `text_det_thresh` | float | null | Pixel threshold |
| `text_det_limit_side_len` | int | null | Max image side length |
| `text_det_limit_type` | str | null | "min" or "max" |

### Recognition Model Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_recognition_model_name` | str | null | Model name |
| `text_recognition_model_dir` | str | null | Path to model directory |
| `rec_batch_num` | int | 6 | Batch size for inference |
| `drop_score` | float | 0.5 | Min confidence score (0.0-1.0) |
| `text_rec_score_thresh` | float | null | Alternative score threshold |

### Advanced Features:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_angle_cls` | bool | true | Enable 180° rotation detection |
| `use_doc_orientation_classify` | bool | false | Document orientation (0°/90°/180°/270°) |
| `use_doc_unwarping` | bool | false | Curved text correction |
| `use_textline_orientation` | bool | false | Text line orientation |

### Performance Parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_mkldnn` | bool | true | MKL-DNN CPU acceleration |
| `cpu_threads` | int | 8 | Number of CPU threads |
| `use_tensorrt` | bool | false | TensorRT GPU acceleration |
| `precision` | str | "fp32" | Computation precision (fp32/fp16) |

---

## 💡 Best Practices

### 1. **Start with Defaults**
- Leave all checkboxes unchecked initially
- Use default PaddleOCR models (they're very good!)
- Only customize if you have specific needs

### 2. **Custom Models**
- Train your own models using [PaddleOCR Training Guide](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/training_en.md)
- Place models in organized folders: `models/det/`, `models/rec/`
- Use relative paths in config

### 3. **Parameter Tuning**
- **Box Threshold** (0.7):
  - Lower (0.5) = more boxes, less strict
  - Higher (0.9) = fewer boxes, very strict
- **Unclip Ratio** (1.5):
  - Lower (1.0) = tight boxes
  - Higher (2.5) = loose boxes
- **Drop Score** (0.5):
  - Lower = keep more low-confidence text
  - Higher = only high-confidence text

### 4. **Profile Selection**
- **CPU Profile**: Stable, compatible, slower
- **GPU Profile**: Fast, requires CUDA, more memory

---

## 🔧 Troubleshooting

### Custom Model Not Loading?

**Check**:
1. ✅ Checkbox is checked
2. ✅ Model directory path is correct
3. ✅ Model files exist: `inference.pdmodel`, `inference.pdiparams`
4. ✅ Path is relative to project root

**Example**:
```
✅ Correct: models/det/my_model
❌ Wrong: d:\full\path\to\models\det\my_model
```

### Settings Not Taking Effect?

**Solution**:
1. Click **OK** or **Apply** in dialog
2. **Restart OCR detection** (reload detector)
3. Check config file was updated: `config/profiles/cpu.yaml`

### Default Models Download Failed?

**Cause**: No internet or firewall blocking

**Solution**:
1. Download models manually from [PaddleOCR Model Zoo](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/models_list_en.md)
2. Place in `models/` folder
3. Enable custom model checkbox and set path

---

## 📖 Examples

### Example 1: Using Custom Thai Detection Model

```yaml
# config/profiles/cpu.yaml
paddleocr:
  lang: "th"
  device: "cpu"

  # Enable custom detection
  use_custom_detection_model: true
  text_detection_model_name: "thai_det_v4"
  text_detection_model_dir: "models/det/thai_det_v4"

  # Keep default recognition
  det_db_box_thresh: 0.7
  det_db_unclip_ratio: 1.5
```

### Example 2: High-Precision Mode

```yaml
paddleocr:
  lang: "th"
  device: "cpu"

  # Stricter thresholds
  det_db_box_thresh: 0.85     # Very strict
  det_db_unclip_ratio: 1.2    # Tighter boxes
  drop_score: 0.7             # High confidence only

  # Enable all features
  use_angle_cls: true
  use_doc_orientation_classify: true
  use_textline_orientation: true
```

### Example 3: Fast Mode (GPU)

```yaml
# config/profiles/gpu.yaml
paddleocr:
  lang: "th"
  device: "gpu"

  # Relaxed thresholds for speed
  det_db_box_thresh: 0.6
  drop_score: 0.4

  # Large batch for GPU
  rec_batch_num: 16

  # Enable TensorRT
  use_tensorrt: true
  precision: "fp16"           # Faster but less accurate
```

---

## 🎨 GUI Integration

### Add Menu Item to Main Window:

```python
# In main_window.py

def create_menu_bar(self):
    menu_bar = self.menuBar()

    # Settings menu
    settings_menu = menu_bar.addMenu("Settings")

    # Add PaddleOCR settings
    paddleocr_action = QtWidgets.QAction("PaddleOCR Settings...", self)
    paddleocr_action.triggered.connect(self.open_paddleocr_settings)
    settings_menu.addAction(paddleocr_action)

def open_paddleocr_settings(self):
    from modules.gui.dialogs.paddleocr_settings_dialog import PaddleOCRSettingsDialog

    dialog = PaddleOCRSettingsDialog(self)
    dialog.settings_changed.connect(self.on_ocr_settings_changed)
    dialog.exec_()

def on_ocr_settings_changed(self):
    # Reload OCR detector with new settings
    reply = QtWidgets.QMessageBox.question(
        self,
        "Reload OCR",
        "Settings changed. Reload OCR detector now?",
        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
    )

    if reply == QtWidgets.QMessageBox.Yes:
        self.reload_detector()
```

---

## ✅ Summary

### What Changed:

1. ✅ **Enhanced YAML configs** - All PaddleOCR 3.0 parameters supported
2. ✅ **Checkbox controls** - Easy enable/disable of custom settings
3. ✅ **GUI dialog** - User-friendly interface with tabs and sliders
4. ✅ **Custom model support** - Use your own trained models
5. ✅ **Profile-based** - Separate CPU and GPU settings
6. ✅ **Backward compatible** - Old configs still work

### What Stays Same:

- Default behavior: Uses PaddleOCR default models
- Existing `detector.py` works without changes
- ConfigManager handles everything automatically

---

## 🔗 Related Documentation

- [PaddleOCR Official Docs](https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html)
- [PaddleOCR Model Zoo](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/models_list_en.md)
- [PaddleOCR Training Guide](https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/training_en.md)
- Project: [README_RESTRUCTURE.md](../README_RESTRUCTURE.md)

---

**Generated**: 2025-11-11
**Version**: 2.4.0
**Author**: Ajan Project
**License**: Same as PaddleOCR (Apache 2.0)
