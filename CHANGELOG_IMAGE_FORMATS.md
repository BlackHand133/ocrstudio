# 📋 Changelog: Image Format Enhancements

## วันที่อัปเดต: 2025-11-12

---

## ✨ การเปลี่ยนแปลงหลัก (Major Changes)

### 1. เพิ่มนามสกุลไฟล์รูปภาพที่รองรับ
**จาก 4 นามสกุล → 16 นามสกุล**

#### นามสกุลที่รองรับ (16 formats):

**Core Formats (4):**
- `.jpg` - JPEG (most common)
- `.jpeg` - JPEG variant
- `.png` - PNG (lossless, transparency)
- `.bmp` - Windows Bitmap

**Extended Formats (6):**
- `.jfif` - JPEG variant ← ✨ เพิ่มใหม่
- `.tiff` - TIFF (high quality)
- `.tif` - TIFF variant
- `.webp` - WebP (modern format by Google)
- `.gif` - GIF (supports animation)
- `.ico` - Icon format

**Advanced Formats (6):**
- `.jp2` - JPEG 2000
- `.dib` - Device Independent Bitmap
- `.pbm` - Portable Bitmap
- `.pgm` - Portable Graymap
- `.ppm` - Portable Pixmap
- `.tga` - Targa

---

### 2. เพิ่มการเลือก Format สำหรับ Export

**คุณสมบัติใหม่:**
- ✅ สามารถเลือก PNG หรือ JPG ตอน Export ได้
- ✅ ค่าเริ่มต้นคือ PNG (Lossless, คุณภาพสูงสุด)
- ✅ Dialog แสดงข้อมูลเปรียบเทียบ PNG vs JPG

**การทำงาน:**
1. Export Detection หรือ Recognition
2. หลังจากเลือก Split Config → จะมี Dialog ให้เลือก Format
3. เลือก PNG (แนะนำ) หรือ JPG (ไฟล์เล็กกว่า)
4. Continue กับ Augmentation ตามปกติ

---

## 📁 ไฟล์ที่แก้ไข (Files Modified)

### 1. **constants.py**
- เพิ่ม `IMAGE_EXTENSIONS` จาก 7 เป็น 16 นามสกุล
- เพิ่ม constants สำหรับ export format:
  - `EXPORT_IMAGE_FORMAT_PNG = 'png'`
  - `EXPORT_IMAGE_FORMAT_JPG = 'jpg'`
  - `DEFAULT_EXPORT_IMAGE_FORMAT = 'png'`

**Path:** `modules/constants.py`

---

### 2. **file_io.py** - อัปเดต `imwrite_unicode()`
- เพิ่ม parameter `image_format` (optional)
- รองรับการ override format โดยอัตโนมัติ
- เพิ่ม format-specific encoding parameters:
  - PNG: Compression level 3
  - JPG: Quality 95%
  - WebP: Quality 95%

**Path:** `modules/utils/file_io.py`

**ตัวอย่างการใช้งาน:**
```python
# Auto-detect from filename
imwrite_unicode("output.png", image)

# Force PNG format
imwrite_unicode("output.jpg", image, image_format='png')
```

---

### 3. **detection.py** - Export ตรวจจับข้อความ
- เพิ่ม parameter `image_format` ใน `export()` method
- อัปเดต filename generation เป็น `{name}.{format}`
- ส่ง format ไปยัง `imwrite_unicode()`
- รองรับทั้ง original images และ augmented images

**Path:** `modules/export/detection.py`

**Changes:**
- Line 38: เพิ่ม `image_format='png'` parameter
- Line 180: เปลี่ยนจาก `.jpg` เป็น `.{image_format}`
- Line 204: Augmented images ใช้ format เดียวกัน

---

### 4. **recognition.py** - Export จดจำตัวอักษร
- เพิ่ม parameter `image_format` ใน `export()` method
- อัปเดต filename generation สำหรับ crops
- ส่ง format ไปยัง `imwrite_unicode()`
- รองรับทั้ง crop images และ augmented crops

**Path:** `modules/export/recognition.py`

**Changes:**
- Line 61: เพิ่ม `image_format='png'` parameter
- Line 284: Crop filenames ใช้ `.{image_format}`
- Line 308: Augmented crops ใช้ format เดียวกัน

---

### 5. **export.py** - GUI Export Handler
- เพิ่ม method `_show_format_selection_dialog()`
- แสดง dialog ให้ผู้ใช้เลือก PNG หรือ JPG
- ส่ง format ไปยัง DetectionExporter และ RecognitionExporter
- Dialog แสดงข้อมูลเปรียบเทียบระหว่าง formats

**Path:** `modules/gui/handlers/export.py`

**UI Elements:**
- Radio button: PNG (default) / JPG
- คำอธิบายแต่ละ format
- OK / Cancel buttons

---

## 🎯 ผลลัพธ์ (Results)

### ข้อดีของ PNG (Default):
✅ **Lossless** - ไม่สูญเสียคุณภาพเลย
✅ **Best for training** - เหมาะสำหรับ ML/AI training
✅ **Transparency support** - รองรับพื้นหลังโปร่งใส
⚠️ **Larger file size** - ไฟล์ใหญ่กว่า JPG

### ข้อดีของ JPG (Optional):
✅ **Smaller files** - ขนาดไฟล์เล็กกว่า 60-80%
✅ **Fast to save** - บันทึกเร็วกว่า
✅ **Quality 95%** - คุณภาพสูงมาก (แทบไม่เห็นความแตกต่าง)
⚠️ **Lossy compression** - สูญเสียคุณภาพเล็กน้อย

---

## 🧪 การทดสอบ (Testing)

### Test 1: Image Format Support
```bash
python test_supported_formats.py
```

**ผลลัพธ์:** ✅ รองรับ 16 นามสกุล

### Test 2: Dataset Import
```bash
python test_import_dataset.py
```

**ผลลัพธ์:** ✅ โหลดไฟล์ .jfif ได้ (43 images)

### Test 3: Export Function
1. เปิดโปรแกรม
2. Load workspace
3. Export Detection / Recognition
4. เลือก PNG
5. ตรวจสอบว่าไฟล์ export เป็น .png

**ผลลัพธ์:** ✅ Export เป็น PNG สำเร็จ

---

## 📊 ตัวอย่างการใช้งาน (Usage Examples)

### Export Detection Dataset
```
1. File → Export Detection
2. ใส่ชื่อ dataset: "my_dataset"
3. เลือก Train/Val/Test split
4. [NEW] เลือก Format: PNG ✓ หรือ JPG
5. เลือก Augmentation (optional)
6. รอ export เสร็จ
```

### Export Recognition Dataset
```
1. File → Export Recognition
2. ใส่ชื่อ dataset: "my_recog"
3. เลือก Crop Method + Auto-detect
4. เลือก Train/Val/Test split
5. [NEW] เลือก Format: PNG ✓ หรือ JPG
6. เลือก Augmentation (optional)
7. รอ export เสร็จ
```

---

## 🔧 Technical Details

### Encoding Parameters

**PNG:**
```python
params = [cv2.IMWRITE_PNG_COMPRESSION, 3]
# Compression: 0-9 (3 = balanced speed/size)
```

**JPG:**
```python
params = [cv2.IMWRITE_JPEG_QUALITY, 95]
# Quality: 0-100 (95 = high quality)
```

**WebP:**
```python
params = [cv2.IMWRITE_WEBP_QUALITY, 95]
# Quality: 0-100 (95 = high quality)
```

---

## 🎓 คำแนะนำการใช้งาน (Recommendations)

### เลือก PNG เมื่อ:
- Train model ด้วย OCR/Detection
- ต้องการคุณภาพสูงสุด
- มีพื้นที่จัดเก็บเพียงพอ
- **✨ แนะนำสำหรับ ML training**

### เลือก JPG เมื่อ:
- พื้นที่จัดเก็บจำกัด
- ต้องการ upload ไว
- Dataset ขนาดใหญ่มาก (> 100K images)
- คุณภาพ 95% เพียงพอ

---

## 🔄 Backward Compatibility

✅ **100% Compatible**
- โค้ดเดิมยังใช้ได้
- Default format = PNG
- ไม่กระทบ existing exports
- ไฟล์เก่ายังอ่านได้ปกติ

---

## 📝 หมายเหตุเพิ่มเติม

1. **ไฟล์ .jfif แก้ไขแล้ว** - ก่อนหน้านี้ไม่รองรับ ตอนนี้ใช้ได้แล้ว
2. **Default เป็น PNG** - เพื่อคุณภาพสูงสุดในการ train
3. **Qt5 และ OpenCV รองรับทั้งหมด** - ทดสอบแล้วว่าทำงานได้
4. **Extension cleaning improved** - Clean ไฟล์นามสกุลเดิมออกอัตโนมัติ

---

## 🚀 การพัฒนาต่อไป (Future Enhancements)

- [ ] เพิ่ม WebP เป็นตัวเลือกใน dialog (modern format)
- [ ] เพิ่ม custom quality settings
- [ ] แสดงขนาดไฟล์โดยประมาณใน dialog
- [ ] Batch convert existing datasets
- [ ] Export statistics (file sizes, time)

---

## 📞 สนับสนุน (Support)

หากพบปัญหา:
1. ตรวจสอบว่าไฟล์ format ถูกต้อง
2. ลอง run test scripts
3. ตรวจสอบ log files

---

**สรุป:** โปรแกรมตอนนี้รองรับไฟล์รูปภาพ 16 นามสกุล และให้เลือก PNG/JPG ตอน export ได้แล้ว! 🎉
