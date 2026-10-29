# สถานะการดูแลระบบ

โปรเจกต์นี้อยู่ในช่วงดูแล: เข้ามาเป็นรอบๆ เพื่อแก้บั๊กและตามเทคโนโลยีที่ใช้ให้ทัน ไม่มีระบบ
ticket ไฟล์นี้ใช้บันทึกสถานะแทน และอัปเดตทุกครั้งที่ปิดรอบ

**อัปเดตล่าสุด:** 2026-10-29 · ปิดรอบแล้ว · ไม่มี PR ค้าง

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
   patch ให้ถึง 2027-04 (2026-10-29: ยังไม่ได้ย้าย รอเครื่อง GPU สำหรับทดสอบ)
2. **Dependabot ยังไม่ดูแล Docker base image** เพราะตอนนี้ PR ที่มันจะเปิด (`python:3.14-slim`)
   build ไม่ได้: paddlepaddle 3.3.1 ยังไม่มี wheel สำหรับ Python 3.14 เปิดเมื่อ paddlepaddle
   รองรับแล้ว (รายละเอียดอยู่ใน `.github/dependabot.yml`) ณ 2026-10-15 รุ่นล่าสุดบน PyPI
   ยังเป็น 3.3.1 มี wheel ถึง cp313

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

### 2026-10-29

| PR | สิ่งที่ทำ |
|---|---|
| [#19](https://github.com/BlackHand133/ocrstudio/pull/19) | vite 8.3.4 แก้ช่องโหว่ของ vite และ `launch-editor` (high) ที่ `npm audit` เจอ ใช้ตอน dev/build เท่านั้น |
| [#20](https://github.com/BlackHand133/ocrstudio/pull/20) | vitest / `@vitest/mocker` 5.0.5 แก้ GHSA-qxg6-89mg-rqv8 และ GHSA-xp26-3454-mjgp (moderate) ใช้ตอน test เท่านั้น |

ปิด [#18](https://github.com/BlackHand133/ocrstudio/pull/18) เพราะซ้ำกับ #17 ที่ merge ไปแล้ว

### 2026-10-15

| PR | สิ่งที่ทำ |
|---|---|
| [#15](https://github.com/BlackHand133/ocrstudio/pull/15) | konva 10.7.0, vite 8.3.1 (Dependabot) |
| [#17](https://github.com/BlackHand133/ocrstudio/pull/17) | source-map-js 1.2.2 แก้ Dependabot alert #1 (high, GHSA-68fv-2mgg-jv7q) มาจาก `postcss` ใช้ตอน build เท่านั้น |

ตรวจแล้วไม่ต้องแก้: PaddlePaddle / PaddleOCR ไม่มีรุ่นใหม่ (3.3.1 / 3.7.0), runner `ubuntu-latest` ที่จะย้ายไป Ubuntu 26 ตั้งแต่ 2026-10-19 มี Python 3.10 และ 3.12
ให้ `setup-python` ครบ และ CI ไม่มีขั้นตอนที่ใช้ `apt` บน runner build image web บนเครื่อง
แล้ว OCR ทำงานบน Python 3.12

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
