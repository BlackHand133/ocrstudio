# สถานะการดูแลระบบ

โปรเจกต์นี้อยู่ในช่วงดูแล: เข้ามาเป็นรอบๆ เพื่อแก้บั๊กและตามเทคโนโลยีที่ใช้ให้ทัน ไม่มีระบบ
ticket ไฟล์นี้ใช้บันทึกสถานะแทน และอัปเดตทุกครั้งที่ปิดรอบ

**อัปเดตล่าสุด:** 2026-09-23 · ปิดรอบแล้ว · ไม่มี PR ค้าง

## ตอนนี้

| เรื่อง | สถานะ |
|---|---|
| CI บน `main` | ผ่าน 7/7: lint, unit test (Python 3.10 และ 3.12), API test, frontend, Docker image web + desktop |
| ช่องโหว่ที่รู้ | 0 (`npm audit` และ Dependabot alerts) |
| Dependabot | alerts, security updates และ version updates รายเดือน (`.github/dependabot.yml`) |

### เวอร์ชันที่ใช้ (ณ 2026-09-23)

| ส่วน | เวอร์ชัน | หมายเหตุ |
|---|---|---|
| Python ใน image CPU | 3.12 | หมดอายุ 2028-10 |
| Python ใน image GPU | 3.10 | หมดอายุ 2026-10-31 ดูงานค้างข้อ 1 |
| Node | 24 (LTS) | หมดอายุ 2028-04 |
| PaddlePaddle / PaddleOCR | 3.3.1 / 3.7.0 | ล็อก `<4` เพราะ 2→3 เปลี่ยน API ที่ `detector.py` ใช้ |
| numpy / OpenCV / Pillow / Shapely | 2.3 / 5.0 / 12.3 / 2.1 | ล็อกที่ major ถัดไป เพื่อให้รุ่นใหญ่มาเป็น PR |
| React / Vite / TypeScript | 19.3 / 8.3 / 7.0 | |
| Mantine | 9.6 | ตั้งค่าให้หน้าตาเหมือนเดิม (`frontend/src/theme.ts`, `frontend/src/main.tsx`) |

## งานค้าง

1. **image GPU ยังเป็น Python 3.10 บน CUDA 11.8** (stage GPU ใน `Dockerfile` และ `Dockerfile.web`)
   ไม่มี image CUDA 11.8 สำหรับ Ubuntu 24.04 จึงต้องย้ายไป CUDA 12 พร้อม Python 3.12
   และต้องทดสอบบนเครื่องที่มี GPU Python 3.10 หมดอายุ 2026-10-31 แต่ Ubuntu 22.04 ยัง
   patch ให้ถึง 2027-04
2. **Dependabot ยังไม่ดูแล Docker base image** เพราะตอนนี้ PR ที่มันจะเปิด (`python:3.14-slim`)
   build ไม่ได้: paddlepaddle 3.3.1 ยังไม่มี wheel สำหรับ Python 3.14 เปิดเมื่อ paddlepaddle
   รองรับแล้ว (รายละเอียดอยู่ใน `.github/dependabot.yml`)

## เช็กลิสต์รอบดูแลครั้งถัดไป

1. **PR ของ Dependabot** และ [Security → Dependabot alerts](https://github.com/BlackHand133/ocrstudio/security/dependabot)
   ตัวที่ CI เขียว merge ได้ ตัวที่แดงคืองานของรอบนั้น
2. **วันหมดอายุ runtime:** [Python](https://endoflife.date/python), [Node](https://endoflife.date/nodejs)
3. **อัปเกรดใหญ่ของ frontend** (PR แยกจาก Dependabot): CI เขียวไม่ได้แปลว่าหน้าตาเหมือนเดิม
   ต้องเปิดหน้าจอดูด้วย ตัวอย่างคือ Mantine 9 ที่เปลี่ยนมุมโค้งและสีทั้งแอปโดยที่ test ผ่านหมด
4. **คำเตือนใน CI run ล่าสุดบน `main`** เช่น action ที่ใช้ runtime เก่า
5. **PaddleOCR รุ่นใหม่:** ถ้า build image พังที่ขั้น `PP-OCR capabilities` แปลว่า resolver
   ภายในของ PaddleOCR ย้ายที่ ต้องแก้ `modules/core/ocr/compat.py` ถ้า build ผ่าน
   `GET /api/config/engine` จะบอกใน `capability_source` ว่าอ่านรุ่น × ภาษาจาก PaddleOCR รุ่นไหน
6. **เปิดหน้าจอจริง:** Settings (เลือกรุ่นกับภาษา), canvas และ export

## ประวัติรอบดูแล

### 2026-09-23

| PR | สิ่งที่ทำ |
|---|---|
| [#9](https://github.com/BlackHand133/ocrstudio/pull/9) | ตารางรุ่น × ภาษาของ PP-OCR อ่านจาก PaddleOCR ที่ติดตั้งจริง แก้บั๊ก: ภาษาไทยคู่ v4/v3, รหัสภาษาของ 2.x (`latin` ฯลฯ) และ v6 บน image ที่เป็น 3.6.0 |
| [#10](https://github.com/BlackHand133/ocrstudio/pull/10) | Python 3.12, Node 24, GitHub Actions รุ่น Node 24, ล็อก paddle `<4`, แก้ `Dockerfile` desktop ที่ลง paddle 2.6, CI build Docker ทุก PR |
| [#11](https://github.com/BlackHand133/ocrstudio/pull/11) | React 19, Vite 8, TypeScript 7, Mantine 9, zustand 5, Konva 10 และ `npm audit` เหลือ 0 |
| [#12](https://github.com/BlackHand133/ocrstudio/pull/12) | Dependabot |
| [#13](https://github.com/BlackHand133/ocrstudio/pull/13) | numpy `<3` (PR แรกจาก Dependabot) |
| [#14](https://github.com/BlackHand133/ocrstudio/pull/14) | ลบ `imgaug` ที่ไม่มีใคร import, ล็อก major ของ OpenCV / Pillow / PyYAML / Shapely, ไฟล์นี้ |

### 2026-07-27 ถึง 2026-07-29

PR #1–#8: รองรับ PaddleOCR 3.x และ PP-OCRv6, ตัววัดคุณภาพ OCR ภาษาไทยและชุดเทียบโมเดล,
export dataset ไปนอก repo, test ของ dataset splitter, เครื่องมืออ่านกล่องข้อความที่กลับหัว
และ `--review-queue`
