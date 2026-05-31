# โครงสร้างโปรเจค (Project Structure)

## ภาพรวมโปรเจค
โปรเจคนี้เป็นแอปพลิเคชัน PyQt5 สำหรับการทำ OCR (Optical Character Recognition) และ annotation ของข้อความภาษาไทย โดยใช้ PaddleOCR

---

## โครงสร้างไฟล์และโฟลเดอร์

```
Ajan/
│
├── 📄 main.py                          # ไฟล์หลักในการรันแอปพลิเคชัน
├── 📄 migrate_to_workspace.py          # ไฟล์สำหรับ migrate ข้อมูลไปยัง workspace
├── 📄 app_config.json                  # ไฟล์ config ของแอปพลิเคชัน
├── 📄 recent_workspaces.json           # เก็บ workspace ที่เพิ่งใช้งาน
├── 📄 requirements.txt                 # รายการ dependencies ของโปรเจค
├── 📄 new_stricture.txt                # เอกสารโครงสร้างใหม่
├── 📄 CHANGELOG_workspace_improvements.md  # บันทึกการเปลี่ยนแปลงของ workspace
│
├── 📁 config/                          # โฟลเดอร์ configuration
│   └── config.yaml                     # ไฟล์ config หลัก (CPU/GPU profiles, PaddleOCR settings)
│
├── 📁 models/                          # โฟลเดอร์เก็บ ML models
│   └── textline_orientation/           # Model สำหรับจัดตำแหน่งข้อความ
│       ├── inference.json
│       ├── inference.pdiparams
│       └── inference.yml
│
├── 📁 modules/                         # โฟลเดอร์ modules หลักของแอปพลิเคชัน
│   ├── __init__.py
│   ├── augmentation.py                 # Data augmentation
│   ├── config_loader.py                # โหลด configuration
│   ├── data_splitter.py                # แบ่งข้อมูล train/val/test
│   ├── detector.py                     # ตรวจจับข้อความ (OCR detection)
│   ├── logger.py                       # ระบบ logging
│   ├── textline_orientation.py         # จัดการการหมุนข้อความ
│   ├── utils.py                        # ฟังก์ชันช่วยเหลือทั่วไป
│   ├── workspace_manager.py            # จัดการ workspace
│   ├── writer.py                       # เขียนข้อมูล output
│   │
│   └── 📁 gui/                         # โฟลเดอร์ GUI components
│       ├── main_window.py              # หน้าต่างหลักของแอปพลิเคชัน
│       ├── ui_components.py            # UI components ทั่วไป
│       ├── augmentation_dialog.py      # Dialog สำหรับ augmentation
│       ├── base_annotation_item.py     # Base class สำหรับ annotation items
│       ├── box_item.py                 # Bounding box annotation
│       ├── canvas_view.py              # Canvas สำหรับแสดงภาพและ annotations
│       ├── mask_handler.py             # จัดการ mask annotations
│       ├── mask_item.py                # Mask annotation item
│       ├── polygon_item.py             # Polygon annotation item
│       ├── split_config_dialog.py      # Dialog สำหรับแบ่งข้อมูล
│       ├── version_manager_dialog.py   # Dialog สำหรับจัดการเวอร์ชัน
│       ├── workspace_selector_dialog.py # Dialog เลือก workspace
│       │
│       └── 📁 window_handler/          # โฟลเดอร์จัดการ handlers ต่างๆ
│           ├── __init__.py
│           ├── annotation_handler.py   # จัดการ annotations
│           ├── cache_handler.py        # จัดการ cache
│           ├── detection_handler.py    # จัดการการตรวจจับข้อความ
│           ├── export_handler.py       # Export ข้อมูล
│           ├── image_handler.py        # จัดการภาพ
│           ├── rotation_handler.py     # จัดการการหมุนภาพ
│           ├── table_handler.py        # จัดการตาราง annotations
│           ├── ui_handler.py           # จัดการ UI events
│           └── workspace_handler.py    # จัดการ workspace operations
│
├── 📁 output/                          # โฟลเดอร์ output ต่างๆ
│   └── logs/                           # โฟลเดอร์เก็บ log files
│       └── app.log                     # Application log file
│
└── 📁 workspaces/                      # โฟลเดอร์เก็บ workspaces
    ├── default/                        # Default workspace
    │   ├── workspace.json
    │   ├── exports.json
    │   └── v1.json
    │
    └── dataset/                        # Dataset workspace
        ├── workspace.json
        ├── exports.json
        ├── v1.json
        └── v4.json
```

---

## คำอธิบายส่วนประกอบหลัก

### 1. Core Files
- **main.py**: Entry point ของแอปพลิเคชัน เรียกใช้ PyQt5 และเปิดหน้าต่างหลัก
- **config/config.yaml**: กำหนดค่า CPU/GPU profiles และพารามิเตอร์ของ PaddleOCR

### 2. Modules
- **detector.py**: ใช้ PaddleOCR ในการตรวจจับข้อความจากภาพ
- **workspace_manager.py**: จัดการ workspaces หลายๆ ตัว พร้อม version control
- **augmentation.py**: ทำ data augmentation สำหรับ training data
- **data_splitter.py**: แบ่งข้อมูลเป็น train/validation/test sets

### 3. GUI Components
- **main_window.py**: หน้าต่างหลักที่รวม canvas, toolbar, และ annotation table
- **canvas_view.py**: แสดงภาพและให้ผู้ใช้สร้าง annotations
- **box_item.py, polygon_item.py, mask_item.py**: รูปแบบ annotation ต่างๆ

### 4. Window Handlers
แยกความรับผิดชอบของ UI ออกเป็นหลาย handlers:
- **annotation_handler**: จัดการการสร้าง/แก้ไข/ลบ annotations
- **detection_handler**: เรียกใช้ OCR detection
- **export_handler**: Export annotations เป็นรูปแบบต่างๆ
- **workspace_handler**: สลับและจัดการ workspaces

### 5. Workspaces
ระบบ workspace ช่วยให้แยก projects ต่างๆ ได้ โดยแต่ละ workspace มี:
- **workspace.json**: ข้อมูล workspace และ settings
- **v*.json**: เวอร์ชันต่างๆ ของ annotations
- **exports.json**: ข้อมูล exports

---

## Dependencies หลัก

- **PyQt5**: GUI framework
- **PaddleOCR**: OCR engine สำหรับภาษาไทย
- **PaddlePaddle**: Deep learning framework
- **OpenCV**: การประมวลผลภาพ
- **Pillow**: จัดการภาพ
- **NumPy**: การคำนวณเชิงตัวเลข
- **PyYAML**: อ่าน/เขียนไฟล์ YAML
- **Shapely**: การคำนวณทางเรขาคณิต
- **imgaug**: Data augmentation

---

## โฟลเดอร์ที่ไม่อยู่ในระบบ Version Control

โฟลเดอร์ต่อไปนี้ถูกยกเว้นจากเอกสารนี้:
- `back-up/` - โฟลเดอร์ backup
- `output_rec/` - Output จาก recognition
- `output_det/` - Output จาก detection
- `ซองยา-up/` - โฟลเดอร์ backup
- `__pycache__/` - Python cache files

---

## วิธีการใช้งาน

1. **รันแอปพลิเคชัน**:
   ```bash
   python main.py
   ```

2. **เลือก Profile (CPU/GPU)**:
   - แก้ไข `config/config.yaml`
   - เปลี่ยน `default_profile` เป็น `"cpu"` หรือ `"gpu"`

3. **จัดการ Workspace**:
   - ใช้ GUI เพื่อสร้าง/เปิด/สลับ workspaces
   - แต่ละ workspace เก็บ annotations แยกกัน

---

*เอกสารนี้สร้างขึ้นเมื่อ: 2025-11-06*
