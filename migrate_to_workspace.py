# migrate_to_workspace.py

"""
Migration tool: แปลง cache.json เดิม → workspace structure ใหม่
"""

import os
import json
import shutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Migration")


def migrate_old_cache_to_workspace(root_dir: str):
    """
    แปลง output/cache.json เดิม → workspaces/default/
    
    Args:
        root_dir: project root directory
    """
    old_cache_path = os.path.join(root_dir, "output", "cache.json")
    
    # ตรวจสอบว่ามี cache เดิมหรือไม่
    if not os.path.exists(old_cache_path):
        logger.info("No old cache.json found. Nothing to migrate.")
        return False
    
    logger.info("Found old cache.json. Starting migration...")
    
    try:
        # โหลด cache เดิม
        with open(old_cache_path, 'r', encoding='utf-8') as f:
            old_cache = json.load(f)
        
        # ตรวจสอบ format
        if isinstance(old_cache, dict) and "annotations" in old_cache:
            # Format ใหม่ที่มี rotations
            annotations = old_cache.get("annotations", {})
            rotations = old_cache.get("rotations", {})
        else:
            # Format เก่ามาก (แค่ annotations)
            annotations = old_cache
            rotations = {}
        
        logger.info(f"Found {len(annotations)} images with annotations")
        
        # สร้างโฟลเดอร์ workspaces
        workspaces_dir = os.path.join(root_dir, "workspaces")
        os.makedirs(workspaces_dir, exist_ok=True)
        
        # สร้าง workspace "default"
        default_ws_dir = os.path.join(workspaces_dir, "default")
        os.makedirs(default_ws_dir, exist_ok=True)
        
        # สร้าง workspace.json
        workspace_data = {
            "version": "2.0.0",
            "workspace": {
                "id": "default",
                "name": "Default Workspace",
                "description": "Migrated from old cache.json",
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat()
            },
            "source": {
                "folder": "",
                "total_images": len(annotations),
                "last_scan": None
            },
            "versions": {
                "current": "v1",
                "available": ["v1"]
            },
            "settings": {
                "detector": {
                    "model": "paddleocr",
                    "lang": "th"
                }
            }
        }
        
        workspace_file = os.path.join(default_ws_dir, "workspace.json")
        with open(workspace_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_data, f, ensure_ascii=False, indent=2)
        
        logger.info("Created workspace.json")
        
        # สร้าง v1.json
        v1_data = {
            "version": "2.0.0",
            "workspace_id": "default",
            "data_version": "v1",
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "description": "Migrated from old cache",
            "annotations": annotations,
            "transforms": rotations,
            "metadata": {
                "total_images": len(annotations),
                "annotated_images": len([k for k, v in annotations.items() if v]),
                "total_annotations": sum(len(v) for v in annotations.values())
            }
        }
        
        v1_file = os.path.join(default_ws_dir, "v1.json")
        with open(v1_file, 'w', encoding='utf-8') as f:
            json.dump(v1_data, f, ensure_ascii=False, indent=2)
        
        logger.info("Created v1.json")
        
        # สร้าง exports.json เปล่า
        exports_data = {
            "version": "2.0.0",
            "workspace_id": "default",
            "exports": []
        }
        
        exports_file = os.path.join(default_ws_dir, "exports.json")
        with open(exports_file, 'w', encoding='utf-8') as f:
            json.dump(exports_data, f, ensure_ascii=False, indent=2)
        
        logger.info("Created exports.json")
        
        # Backup cache.json เดิม
        backup_path = old_cache_path + ".backup"
        shutil.copy2(old_cache_path, backup_path)
        logger.info(f"Backed up old cache to {backup_path}")
        
        # ลบ cache.json เดิม (optional)
        # os.remove(old_cache_path)
        # logger.info("Removed old cache.json")
        
        logger.info("✅ Migration completed successfully!")
        logger.info(f"Your data is now in: {default_ws_dir}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    
    # ถ้ารันจาก project root
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("="*60)
    print("Cache Migration Tool")
    print("="*60)
    print()
    print("This will migrate your old cache.json to the new workspace structure.")
    print(f"Project root: {root_dir}")
    print()
    
    answer = input("Continue? (y/n): ").strip().lower()
    
    if answer == 'y':
        migrate_old_cache_to_workspace(root_dir)
    else:
        print("Migration cancelled.")