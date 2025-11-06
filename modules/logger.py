# modules/logger.py

import os
import logging

def setup_logging(root_dir):
    """
    สร้างโฟลเดอร์ logs และตั้งค่า logging:
    - บันทึกลงไฟล์ output/app.log
    - แสดงบน console
    """
    log_dir = os.path.join(root_dir, "output", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # ถ้ามีการตั้งค่าเดิม ให้ล้างก่อน
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("TextDetGUI")
    logger.info("Logging initialized. Log file: %s", log_file)
    return logger
