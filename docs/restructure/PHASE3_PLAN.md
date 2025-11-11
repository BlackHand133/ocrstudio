# Phase 3: Export System Refactor - Execution Plan

## 🎯 Mission: Split export_handler.py (1202 lines!)

---

## 📊 Current Situation

**File**: `modules/gui/window_handler/export_handler.py`
- **Size**: 1202 lines
- **Status**: Monolithic - everything in one file
- **Problem**: Too large, hard to maintain

---

## 🔍 Analysis

### Methods Found (15 total):

| Method | Lines | Purpose | Category |
|--------|-------|---------|----------|
| `__init__` | ~25 | Initialize | Setup |
| `_is_mask_item` | ~16 | Check mask | Image Processing |
| `_draw_masks_on_image` | ~39 | Draw masks | Image Processing |
| `_detect_upside_down_with_model` | ~21 | Detect 180° | Image Processing |
| `_detect_upside_down_advanced` | ~108 | Advanced detect | Image Processing |
| `_select_best_orientation` | ~88 | Select orientation | Image Processing |
| `_crop_rotated_box` | ~119 | Crop rotated | Image Processing |
| `_order_points` | ~37 | Order points | Image Processing |
| `_crop_bounding_box` | ~40 | Crop bbox | Image Processing |
| `_show_crop_method_dialog` | ~89 | UI dialog | UI |
| `save_labels_detection` | ~62 | Detection entry | Detection Export |
| `_split_data` | ~43 | Split dataset | Common |
| `_export_detection_dataset` | ~169 | Detection export | Detection Export |
| `export_recognition` | ~105 | Recognition entry | Recognition Export |
| `_export_recognition_dataset` | ~188 | Recognition export | Recognition Export |

### Categories:

1. **Image Processing** (~470 lines)
   - Mask handling
   - Orientation detection
   - Image cropping utilities

2. **Detection Export** (~270 lines)
   - Dataset export for text detection
   - PaddleOCR format

3. **Recognition Export** (~290 lines)
   - Dataset export for text recognition
   - Crop images by annotations

4. **Common Utilities** (~170 lines)
   - Data splitting
   - File operations
   - UI dialogs

---

## 🏗️ Proposed Structure

```
modules/export/
├── __init__.py                  # Package exports
│
├── base.py                      # BaseExporter (abstract)
│   ├── Common methods
│   ├── Abstract methods to implement
│   └── Shared utilities
│
├── utils.py                     # Export utilities
│   ├── Image processing
│   │   ├── Mask handling
│   │   ├── Orientation detection
│   │   └── Image cropping
│   ├── Data splitting
│   └── File operations
│
├── detection.py                 # DetectionExporter
│   ├── save_labels_detection()
│   └── _export_detection_dataset()
│
├── recognition.py               # RecognitionExporter
│   ├── export_recognition()
│   └── _export_recognition_dataset()
│
└── formats/                     # Format handlers
    ├── __init__.py
    └── ppocr.py                 # PaddleOCR format

# GUI coordinator (stays in GUI)
modules/gui/handlers/
└── export.py                    # ExportHandler (coordinator)
    ├── __init__()
    ├── save_labels_detection() → DetectionExporter
    ├── export_recognition() → RecognitionExporter
    └── UI dialog methods
```

---

## 📦 Module Responsibilities

### 1. `modules/export/base.py` - BaseExporter
**Abstract base class for all exporters**

```python
class BaseExporter:
    def __init__(self, main_window):
        self.main_window = main_window
        self.workspace_handler = main_window.workspace_handler
        # ... common setup

    @abstractmethod
    def export(self, **kwargs):
        """Override in subclasses"""
        pass

    # Common utilities
    def _split_data(self, keys, config): ...
    def _get_annotations(self, key): ...
    def _save_metadata(self, path, data): ...
```

### 2. `modules/export/utils.py` - Export Utilities
**Reusable image processing utilities**

```python
# Mask operations
def is_mask_item(ann): ...
def draw_masks_on_image(img, mask_items): ...

# Orientation detection
def detect_upside_down_with_model(img, model_path): ...
def detect_upside_down_advanced(img): ...
def select_best_orientation(img, auto_orient=True): ...

# Image cropping
def crop_rotated_box(img, pts, auto_detect=True): ...
def crop_bounding_box(img, pts, auto_detect=True): ...
def order_points(pts): ...
```

### 3. `modules/export/detection.py` - DetectionExporter
**Text detection dataset export**

```python
class DetectionExporter(BaseExporter):
    def export(self, output_dir, split_config, aug_config):
        # 1. Get annotations
        # 2. Split data
        # 3. Export with augmentation
        # 4. Generate labels
        pass

    def _export_detection_dataset(self, folder, split_result, ...): ...
    def _generate_detection_labels(self, annotations): ...
```

### 4. `modules/export/recognition.py` - RecognitionExporter
**Text recognition dataset export**

```python
class RecognitionExporter(BaseExporter):
    def export(self, output_dir, split_config, aug_config, crop_method):
        # 1. Get annotations
        # 2. Split data
        # 3. Crop images
        # 4. Export with augmentation
        # 5. Generate labels
        pass

    def _export_recognition_dataset(self, folder, split_result, ...): ...
    def _crop_and_save(self, img, annotation, output_path): ...
```

### 5. `modules/export/formats/ppocr.py` - Format Handlers
**PaddleOCR specific format handling**

```python
def format_detection_label(annotation): ...
def format_recognition_label(text): ...
def write_label_file(path, labels): ...
```

### 6. `modules/gui/handlers/export.py` - ExportHandler (Coordinator)
**GUI-level coordinator (stays in GUI layer)**

```python
class ExportHandler:
    """Thin wrapper that coordinates exports from GUI"""

    def __init__(self, main_window):
        self.main_window = main_window

        # Create exporters
        from modules.export import DetectionExporter, RecognitionExporter
        self.detection_exporter = DetectionExporter(main_window)
        self.recognition_exporter = RecognitionExporter(main_window)

    def save_labels_detection(self):
        """Show dialog and delegate to DetectionExporter"""
        config = self._get_detection_config()
        if config:
            self.detection_exporter.export(**config)

    def export_recognition(self):
        """Show dialog and delegate to RecognitionExporter"""
        config = self._get_recognition_config()
        if config:
            self.recognition_exporter.export(**config)

    # UI methods stay here
    def _show_crop_method_dialog(self): ...
    def _get_detection_config(self): ...
    def _get_recognition_config(self): ...
```

---

## 🔄 Migration Strategy

### Step 1: Create Base Infrastructure
1. ✅ Create `modules/export/` directory
2. ✅ Create `modules/export/__init__.py`
3. ✅ Create `modules/export/base.py` - BaseExporter
4. ✅ Create `modules/export/utils.py` - Image utilities

### Step 2: Extract Image Processing
5. ✅ Move mask methods → `utils.py`
6. ✅ Move orientation methods → `utils.py`
7. ✅ Move cropping methods → `utils.py`

### Step 3: Create Exporters
8. ✅ Create `detection.py` - DetectionExporter
9. ✅ Create `recognition.py` - RecognitionExporter
10. ✅ Move detection logic → DetectionExporter
11. ✅ Move recognition logic → RecognitionExporter

### Step 4: Format Handlers
12. ✅ Create `formats/` directory
13. ✅ Create `ppocr.py` format handler
14. ✅ Extract format-specific logic

### Step 5: Create GUI Coordinator
15. ✅ Create new `export.py` in `gui/handlers/`
16. ✅ Implement thin wrapper
17. ✅ Keep UI dialogs in GUI layer

### Step 6: Integration & Testing
18. ✅ Update imports in main_window
19. ✅ Test detection export
20. ✅ Test recognition export
21. ✅ Test with augmentation
22. ✅ Cleanup old export_handler

---

## 📊 Expected Results

### Before:
```
export_handler.py: 1202 lines (monolithic)
```

### After:
```
modules/export/
├── base.py           (~150 lines)
├── utils.py          (~400 lines)
├── detection.py      (~250 lines)
├── recognition.py    (~280 lines)
└── formats/
    └── ppocr.py      (~80 lines)

modules/gui/handlers/
└── export.py         (~100 lines)  # Coordinator only
```

**Total**: ~1260 lines (slightly more due to structure, but much better organized!)

---

## ✅ Benefits

1. ✅ **Separation of Concerns**
   - Business logic (export) separated from UI (GUI)
   - Image processing utilities reusable
   - Format handlers pluggable

2. ✅ **Easier Testing**
   - Test exporters without GUI
   - Mock image utilities
   - Test formats independently

3. ✅ **Better Maintainability**
   - Each file has clear purpose
   - Easier to find and fix bugs
   - Easier to add new export formats

4. ✅ **Reusability**
   - Image utils can be used elsewhere
   - Exporters can be used in CLI tools
   - Format handlers shareable

5. ✅ **Scalability**
   - Easy to add new export formats (YOLO, COCO, etc.)
   - Easy to add new exporters
   - Easy to extend functionality

---

## ⏭️ Next Steps

**Ready to start?**

1. Create base infrastructure (base.py, utils.py)
2. Extract image processing utilities
3. Create detection exporter
4. Create recognition exporter
5. Create GUI coordinator
6. Test and integrate

**Estimated Time**: 3-4 hours

**Let's do this!** 💪🚀

---

## 📝 Notes

- Keep backward compatibility during migration
- Test incrementally after each extraction
- Document all public APIs
- Add type hints throughout
- Keep UI logic in GUI layer only
