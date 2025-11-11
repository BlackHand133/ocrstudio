# modules/writer.py
import os, json

class DatasetWriter:
    def __init__(self, prefix="data_detV1"):
        self.prefix = prefix

    def format_line(self, img_path, items):
        fname = os.path.basename(img_path)
        rel = os.path.join(self.prefix, fname).replace("\\", "/")
        arr = []
        for it in items:
            arr.append({
                "transcription": it['transcription'],
                "points": it['points'],
                "difficult": it.get('difficult', False)
            })
        return f"{rel}\t" + json.dumps(arr, ensure_ascii=False)
