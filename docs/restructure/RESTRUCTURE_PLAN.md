# 🏗️ Project Restructure Plan - Complete Overhaul

## 📊 โครงสร้างปัจจุบัน (Current - มีปัญหา)

```
Ajan/
├── main.py
├── config/
│   └── config.yaml                    # เฉพาะ OCR config
├── modules/
│   ├── detector.py                    # ❌ ปนกับ business logic
│   ├── workspace_manager.py           # ❌ ใหญ่เกินไป (675 lines)
│   ├── config_loader.py               # ❌ จัดการแค่ config.yaml
│   ├── augmentation.py                # ❌ ไม่มีหมวดหมู่
│   ├── data_splitter.py              # ❌ ไม่มีหมวดหมู่
│   ├── textline_orientation.py       # ❌ ไม่มีหมวดหมู่
│   ├── utils.py                       # ❌ ปนทุกอย่าง
│   └── gui/
│       ├── main_window.py             # ❌ ใหญ่ (564 lines)
│       ├── ui_components.py           # ❌ Factory functions
│       ├── [dialogs].py               # ✅ OK
│       ├── [items].py                 # ✅ OK
│       └── window_handler/
│           ├── export_handler.py      # ❌❌ ใหญ่มาก (1202 lines!)
│           └── [other_handlers].py    # ✅ OK
└── workspaces/                        # ❌ ไม่ควรอยู่ใน project root
```

**ปัญหาหลัก:**
- ❌ Modules ไม่มีการจัดหมวดหมู่ที่ชัดเจน
- ❌ Config กระจัดกระจาย (config.yaml, app_config.json, recent_workspaces.json)
- ❌ ไฟล์ใหญ่เกินไป (export_handler: 1202 lines, workspace_manager: 675 lines)
- ❌ Utils ปนทุกอย่าง
- ❌ Hard-coded values ทั่วทั้ง project
- ❌ Data directories (workspaces/, output*/) อยู่ใน project root

---

## 🎯 โครงสร้างใหม่ (Proposed - Production Ready)

```
Ajan/                                   # Project Root
│
├── 📄 main.py                          # Application entry point
├── 📄 setup.py                         # Package setup
├── 📄 requirements.txt                 # Dependencies
├── 📄 README.md                        # Documentation
├── 📄 .env.example                     # Environment variables example
├── 📄 .gitignore                       # Git ignore rules
│
├── 📁 config/                          # ⭐ Configuration Directory
│   ├── default.yaml                    # Default configuration
│   ├── profiles/                       # Config profiles
│   │   ├── cpu.yaml                    # CPU profile
│   │   ├── gpu.yaml                    # GPU profile
│   │   └── production.yaml             # Production settings
│   ├── logging.yaml                    # Logging configuration
│   └── paths.yaml                      # Path configurations
│
├── 📁 data/                            # ⭐ Data Directory (user data)
│   ├── workspaces/                     # User workspaces
│   ├── models/                         # ML models
│   │   └── textline_orientation/
│   ├── output/                         # General output
│   ├── output_det/                     # Detection output
│   ├── output_rec/                     # Recognition output
│   ├── logs/                           # Application logs
│   └── cache/                          # Cache files
│
├── 📁 modules/                         # ⭐ Main Application Package
│   │
│   ├── 📄 __init__.py                  # Package init (exports)
│   ├── 📄 __version__.py               # Version info
│   ├── 📄 constants.py                 # Global constants
│   │
│   ├── 📁 config/                      # ⭐ Configuration Management
│   │   ├── __init__.py                 # Exports: ConfigManager
│   │   ├── manager.py                  # ConfigManager (unified)
│   │   ├── loader.py                   # Config file loaders
│   │   ├── validator.py                # Config validation
│   │   ├── profiles.py                 # Profile management
│   │   └── defaults.py                 # Default values
│   │
│   ├── 📁 core/                        # ⭐ Core Business Logic
│   │   ├── __init__.py
│   │   ├── 📁 ocr/                     # OCR related
│   │   │   ├── __init__.py
│   │   │   ├── detector.py             # Text detector
│   │   │   ├── recognizer.py           # Text recognizer (future)
│   │   │   └── orientation.py          # Text orientation
│   │   │
│   │   ├── 📁 workspace/               # Workspace system
│   │   │   ├── __init__.py
│   │   │   ├── manager.py              # Workspace manager
│   │   │   ├── version.py              # Version control
│   │   │   ├── metadata.py             # Workspace metadata
│   │   │   └── storage.py              # Storage operations
│   │   │
│   │   └── 📁 annotation/              # Annotation system
│   │       ├── __init__.py
│   │       ├── base.py                 # Base annotation
│   │       ├── box.py                  # Box annotations
│   │       ├── polygon.py              # Polygon annotations
│   │       └── mask.py                 # Mask annotations
│   │
│   ├── 📁 data/                        # ⭐ Data Processing
│   │   ├── __init__.py
│   │   ├── augmentation.py             # Data augmentation
│   │   ├── splitter.py                 # Dataset splitting
│   │   ├── loader.py                   # Data loading
│   │   └── writer.py                   # Data writing
│   │
│   ├── 📁 export/                      # ⭐ Export System
│   │   ├── __init__.py
│   │   ├── base.py                     # Base exporter
│   │   ├── detection.py                # Detection export
│   │   ├── recognition.py              # Recognition export
│   │   ├── augmentation.py             # Augmentation export
│   │   └── formats/                    # Export formats
│   │       ├── __init__.py
│   │       ├── ppocr.py                # PaddleOCR format
│   │       ├── yolo.py                 # YOLO format (future)
│   │       └── coco.py                 # COCO format (future)
│   │
│   ├── 📁 utils/                       # ⭐ Utilities (Organized)
│   │   ├── __init__.py
│   │   ├── file.py                     # File operations
│   │   ├── image.py                    # Image operations
│   │   ├── path.py                     # Path operations
│   │   ├── geometry.py                 # Geometry operations
│   │   ├── validation.py               # Validation helpers
│   │   └── logger.py                   # Logging setup
│   │
│   ├── 📁 services/                    # ⭐ Service Layer (Business Services)
│   │   ├── __init__.py
│   │   ├── workspace_service.py        # Workspace operations
│   │   ├── annotation_service.py       # Annotation operations
│   │   ├── detection_service.py        # Detection operations
│   │   ├── export_service.py           # Export operations
│   │   └── cache_service.py            # Cache management
│   │
│   └── 📁 gui/                         # ⭐ GUI Package
│       ├── __init__.py
│       │
│       ├── 📁 app/                     # Application level
│       │   ├── __init__.py
│       │   ├── main_window.py          # Main window (simplified)
│       │   └── application.py          # Application class
│       │
│       ├── 📁 widgets/                 # Custom widgets
│       │   ├── __init__.py
│       │   ├── canvas.py               # Canvas view
│       │   ├── image_list.py           # Image list widget
│       │   ├── annotation_table.py     # Annotation table
│       │   └── toolbar.py              # Toolbar widgets
│       │
│       ├── 📁 dialogs/                 # All dialogs
│       │   ├── __init__.py
│       │   ├── base.py                 # Base dialog
│       │   ├── settings.py             # Settings dialog
│       │   ├── workspace_selector.py   # Workspace selector
│       │   ├── version_manager.py      # Version manager
│       │   ├── augmentation.py         # Augmentation dialog
│       │   └── split_config.py         # Split config dialog
│       │
│       ├── 📁 items/                   # Graphics items
│       │   ├── __init__.py
│       │   ├── base.py                 # Base item
│       │   ├── box_item.py             # Box item
│       │   ├── polygon_item.py         # Polygon item
│       │   └── mask_item.py            # Mask item
│       │
│       ├── 📁 handlers/                # Event handlers
│       │   ├── __init__.py
│       │   ├── base.py                 # Base handler
│       │   ├── workspace.py            # Workspace handler
│       │   ├── image.py                # Image handler
│       │   ├── annotation.py           # Annotation handler
│       │   ├── detection.py            # Detection handler
│       │   ├── export.py               # Export coordinator
│       │   ├── rotation.py             # Rotation handler
│       │   ├── table.py                # Table handler
│       │   ├── ui.py                   # UI handler
│       │   ├── mask.py                 # Mask handler
│       │   └── cache.py                # Cache handler
│       │
│       └── 📁 resources/               # GUI resources
│           ├── __init__.py
│           ├── icons/                  # Icons
│           ├── styles/                 # QSS stylesheets
│           └── i18n/                   # Translations (future)
│
├── 📁 tests/                           # ⭐ Tests
│   ├── __init__.py
│   ├── conftest.py                     # Pytest config
│   ├── 📁 unit/                        # Unit tests
│   │   ├── test_config.py
│   │   ├── test_workspace.py
│   │   ├── test_detector.py
│   │   └── test_export.py
│   ├── 📁 integration/                 # Integration tests
│   │   └── test_export_flow.py
│   └── 📁 fixtures/                    # Test fixtures
│       ├── sample_images/
│       └── sample_annotations/
│
├── 📁 docs/                            # ⭐ Documentation
│   ├── index.md
│   ├── user_guide.md
│   ├── developer_guide.md
│   ├── api_reference.md
│   └── architecture.md
│
└── 📁 scripts/                         # ⭐ Utility scripts
    ├── migrate_workspace.py            # Migration script
    ├── backup.py                       # Backup script
    ├── cleanup.py                      # Cleanup script
    └── setup_dev.py                    # Development setup
```

---

## 📦 Key Improvements (การปรับปรุงหลัก)

### 1. **Config Management** 🔧
**Before:**
```python
# กระจัดกระจาย 4 ที่
config/config.yaml           # OCR only
app_config.json              # App state
recent_workspaces.json       # Recent workspaces
workspaces/*/workspace.json  # Workspace config
```

**After:**
```python
# รวมศูนย์ใน modules/config/
from modules.config import ConfigManager

config = ConfigManager.instance()
config.get('ocr.device')              # OCR settings
config.get('app.auto_save')           # App settings
config.get('paths.output_det')        # Path settings
config.get('workspace.current')       # Workspace info
```

### 2. **Module Organization** 📚
**Before:**
```python
# ปนกันหมด
modules/
├── detector.py              # OCR
├── workspace_manager.py     # Workspace
├── augmentation.py          # Data
├── utils.py                 # Everything!
```

**After:**
```python
# แบ่งตามหมวดหมู่ชัดเจน
modules/
├── core/ocr/detector.py           # OCR-related
├── core/workspace/manager.py      # Workspace-related
├── data/augmentation.py           # Data processing
├── utils/file.py                  # File utilities
├── utils/image.py                 # Image utilities
```

### 3. **Export System** 📤
**Before:**
```python
# ไฟล์เดียว 1202 บรรทัด!
modules/gui/window_handler/export_handler.py
```

**After:**
```python
# แยกตามความรับผิดชอบ
modules/export/
├── base.py                 # Base exporter (abstract)
├── detection.py            # Detection export logic
├── recognition.py          # Recognition export logic
├── augmentation.py         # Augmentation export logic
└── formats/
    ├── ppocr.py            # PaddleOCR format
    ├── yolo.py             # YOLO format (future)
    └── coco.py             # COCO format (future)
```

### 4. **Service Layer** 🛠️
**Before:**
```python
# GUI handlers เรียก business logic ตรงๆ
class DetectionHandler:
    def auto_label_all(self):
        # Business logic ใน GUI handler (ไม่ดี)
        detector = TextDetector()
        for image in images:
            result = detector.detect(image)
            self.annotations[key] = result
```

**After:**
```python
# GUI handlers เรียกผ่าน services
from modules.services import DetectionService

class DetectionHandler:
    def __init__(self):
        self.service = DetectionService()

    def auto_label_all(self):
        # Business logic อยู่ใน service
        self.service.detect_all(self.images)
```

### 5. **Constants & Configuration** 📋
**Before:**
```python
# Hard-coded ทั่ว project
"2.0.0"                    # Version
"<no_label>"               # Placeholder
"###"                      # Mask text
"output_det"               # Path
```

**After:**
```python
# modules/constants.py
APP_VERSION = "2.0.0"
PLACEHOLDER_TEXT = "<no_label>"
MASK_TEXT = "###"

# config/paths.yaml
paths:
  output_det: "data/output_det"
  output_rec: "data/output_rec"
  workspaces: "data/workspaces"
```

### 6. **Data Directory** 📂
**Before:**
```python
Ajan/
├── workspaces/           # User data ปนกับ source code
├── output_det/
├── output_rec/
└── models/
```

**After:**
```python
Ajan/
├── modules/              # Source code เท่านั้น
└── data/                 # User data แยกออกมา
    ├── workspaces/
    ├── output_det/
    ├── output_rec/
    ├── models/
    ├── logs/
    └── cache/
```

### 7. **GUI Structure** 🖼️
**Before:**
```python
gui/
├── main_window.py              # 564 lines (ใหญ่)
├── ui_components.py            # Factory functions
├── [items].py                  # ปนกัน
├── [dialogs].py                # ปนกัน
└── window_handler/             # Handlers ดี แต่ยังไม่เพียงพอ
```

**After:**
```python
gui/
├── app/                        # Application level
│   └── main_window.py          # Simplified (< 200 lines)
├── widgets/                    # Reusable widgets
├── dialogs/                    # All dialogs
├── items/                      # Graphics items
├── handlers/                   # Event handlers
└── resources/                  # Icons, styles, i18n
```

---

## 🔄 Migration Strategy (ขั้นตอนการย้าย)

### **Phase 1: Foundation** (1 วัน)
1. ✅ สร้างโครงสร้างโฟลเดอร์ใหม่
2. ✅ สร้าง `modules/constants.py`
3. ✅ สร้าง `modules/__version__.py`
4. ✅ สร้าง `modules/config/manager.py`
5. ✅ ย้าย config files ไป `config/profiles/`

### **Phase 2: Core Modules** (2-3 วัน)
6. ✅ ย้าย detector → `modules/core/ocr/detector.py`
7. ✅ ย้าย textline_orientation → `modules/core/ocr/orientation.py`
8. ✅ แยก workspace_manager → `modules/core/workspace/`
9. ✅ ย้าย data processing → `modules/data/`
10. ✅ แยก utils → `modules/utils/[file|image|path|...].py`

### **Phase 3: Export System** (2 วัน)
11. ✅ สร้าง `modules/export/base.py`
12. ✅ แยก export_handler → `modules/export/[detection|recognition|augmentation].py`
13. ✅ สร้าง format handlers → `modules/export/formats/`

### **Phase 4: Services** (1-2 วัน)
14. ✅ สร้าง service layer → `modules/services/`
15. ✅ ย้าย business logic จาก handlers → services

### **Phase 5: GUI Restructure** (3-4 วัน)
16. ✅ จัดระเบียบ GUI structure
17. ✅ แยก widgets, dialogs, items, handlers
18. ✅ สร้าง base classes
19. ✅ Simplify main_window.py

### **Phase 6: Data & Paths** (1 วัน)
20. ✅ สร้าง `data/` directory
21. ✅ ย้าย workspaces/, output*/, models/
22. ✅ ปรับ path configurations

### **Phase 7: Testing & Documentation** (2-3 วัน)
23. ✅ สร้าง test structure
24. ✅ เขียน unit tests
25. ✅ สร้าง documentation
26. ✅ ทดสอบระบบทั้งหมด

**Total Time: 2-3 สัปดาห์**

---

## 📝 Import Changes (ตัวอย่างการเปลี่ยน imports)

### **Before:**
```python
from modules.detector import TextDetector
from modules.workspace_manager import WorkspaceManager
from modules.utils import load_image, save_json
from modules.config_loader import get_loader
```

### **After:**
```python
from modules.core.ocr import TextDetector
from modules.core.workspace import WorkspaceManager
from modules.utils.image import load_image
from modules.utils.file import save_json
from modules.config import ConfigManager
```

---

## ✅ Benefits (ประโยชน์ที่ได้รับ)

1. ✅ **ง่ายต่อการหา modules** - แบ่งหมวดหมู่ชัดเจน
2. ✅ **ง่ายต่อการพัฒนา** - แต่ละ module มีหน้าที่ชัดเจน
3. ✅ **ง่ายต่อการเทส** - มี test structure
4. ✅ **ง่ายต่อการบำรุงรักษา** - Code สั้น อ่านง่าย
5. ✅ **Scalable** - เพิ่ม feature ใหม่ได้ง่าย
6. ✅ **Professional** - ตรงมาตรฐาน Python project
7. ✅ **แยก source code กับ user data** - ปลอดภัยกว่า
8. ✅ **Config เป็นระบบ** - จัดการง่าย
9. ✅ **Reusable components** - ใช้ซ้ำได้
10. ✅ **Team collaboration** - เหมาะกับการทำงานเป็นทีม

---

## 🚀 Next Steps

**คุณต้องการให้ฉันเริ่มทำการ restructure เลยไหม?**

ฉันจะทำแบบ **incremental migration** คือ:
1. สร้างโครงสร้างใหม่ควบคู่กับของเก่า
2. ย้ายทีละ module
3. ปรับ imports ทีละส่วน
4. ทดสอบระหว่างทาง
5. ลบของเก่าเมื่อแน่ใจว่าใหม่ใช้งานได้

**วิธีนี้ปลอดภัย ไม่เสี่ยงทำระบบพัง และสามารถ rollback ได้ตลอด**

พร้อมเริ่มเลยไหม? 🎯
