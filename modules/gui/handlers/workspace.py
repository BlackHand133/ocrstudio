# modules/gui/window_handler/workspace_handler.py

import logging
from typing import Optional, Dict
from modules.utils import sanitize_annotations

logger = logging.getLogger("TextDetGUI")


class WorkspaceHandler:
    """
    จัดการ Workspace และ Version สำหรับ MainWindow
    แทนที่ CacheHandler เดิม
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
        self.current_workspace_id = None
        self.current_version = None
        self.version_data = None
    
    def load_workspace(self, workspace_id: str, version: Optional[str] = None):
        """
        โหลด workspace และ version
        
        Args:
            workspace_id: workspace id
            version: version name (None = ใช้ current version)
        """
        try:
            # โหลด workspace
            workspace_data = self.main_window.workspace_manager.load_workspace(workspace_id)
            if not workspace_data:
                logger.error(f"Failed to load workspace: {workspace_id}")
                return False
            
            # ใช้ current version ถ้าไม่ระบุ
            if version is None:
                version = workspace_data["versions"]["current"]
            
            # โหลด version data
            version_data = self.main_window.workspace_manager.load_version(workspace_id, version)
            if not version_data:
                logger.error(f"Failed to load version: {version}")
                return False
            
            # เก็บข้อมูล
            self.current_workspace_id = workspace_id
            self.current_version = version
            self.version_data = version_data
            
            # โหลดข้อมูลเข้า MainWindow
            self.main_window.annotations = version_data.get("annotations", {})
            self.main_window.image_rotations = version_data.get("transforms", {})
            
            # อัปเดต app config
            self.main_window.workspace_manager.app_config["current_workspace"] = workspace_id
            self.main_window.workspace_manager.save_app_config()
            
            # เพิ่มเข้า recent list
            self.main_window.workspace_manager.add_recent_workspace(workspace_id)
            
            logger.info(f"Loaded workspace: {workspace_id}, version: {version}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to load workspace: {e}")
            return False
    
    def save_workspace(self):
        """บันทึก workspace ปัจจุบัน"""
        if not self.current_workspace_id or not self.current_version:
            logger.warning("No workspace loaded")
            return False
        
        try:
            # Sanitize annotations
            sanitized_annotations = {}
            for key, anns in self.main_window.annotations.items():
                sanitized_annotations[key] = sanitize_annotations(anns)
            
            # อัปเดต version data
            self.version_data["annotations"] = sanitized_annotations
            self.version_data["transforms"] = self.main_window.image_rotations
            
            # บันทึก
            success = self.main_window.workspace_manager.save_version(
                self.current_workspace_id,
                self.current_version,
                self.version_data
            )
            
            if success:
                logger.debug(f"Saved workspace: {self.current_workspace_id}")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}")
            return False
    
    def create_new_version(self, new_version: str, base_version: Optional[str] = None, 
                          description: str = "") -> bool:
        """
        สร้าง version ใหม่
        
        Args:
            new_version: ชื่อ version ใหม่ เช่น "v2"
            base_version: version ที่จะคัดลอกมา (None = คัดลอกจาก current)
            description: คำอธิบาย
        """
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False
        
        # บันทึก current version ก่อน
        self.save_workspace()
        
        # ใช้ current version เป็น base ถ้าไม่ระบุ
        if base_version is None:
            base_version = self.current_version
        
        # สร้าง version ใหม่
        success = self.main_window.workspace_manager.create_version(
            self.current_workspace_id,
            new_version,
            base_version,
            description
        )
        
        if success:
            # สลับไป version ใหม่
            self.switch_version(new_version)
        
        return success
    
    def switch_version(self, version: str) -> bool:
        """สลับไป version อื่น"""
        if not self.current_workspace_id:
            logger.error("No workspace loaded")
            return False
        
        # บันทึก current version ก่อน
        self.save_workspace()
        
        # โหลด version ใหม่
        return self.load_workspace(self.current_workspace_id, version)
    
    def get_workspace_info(self) -> Dict:
        """ดึงข้อมูล workspace ปัจจุบัน"""
        if not self.current_workspace_id:
            return {}
        
        workspace_data = self.main_window.workspace_manager.load_workspace(
            self.current_workspace_id
        )
        
        if not workspace_data:
            return {}
        
        return {
            "id": self.current_workspace_id,
            "name": workspace_data["workspace"]["name"],
            "description": workspace_data["workspace"].get("description", ""),
            "source_folder": workspace_data["source"]["folder"],
            "current_version": self.current_version,
            "available_versions": workspace_data["versions"]["available"]
        }
    
    def get_version_stats(self) -> Dict:
        """ดึงสถิติของ version ปัจจุบัน"""
        if not self.version_data:
            return {}

        return self.version_data.get("metadata", {})

    def delete_version(self, version: str) -> tuple:
        """
        ลบ version

        Args:
            version: version ที่จะลบ

        Returns:
            (success: bool, message: str)
        """
        if not self.current_workspace_id:
            return False, "No workspace loaded"

        # เรียก delete_version จาก workspace_manager
        success, message = self.main_window.workspace_manager.delete_version(
            self.current_workspace_id,
            version
        )

        return success, message

    def get_version_list(self):
        """
        ดึงรายการ version ทั้งหมดใน workspace ปัจจุบัน

        Returns:
            List of version info dicts
        """
        if not self.current_workspace_id:
            return []

        return self.main_window.workspace_manager.get_version_list(
            self.current_workspace_id
        )

    def rename_workspace(self, new_name: str) -> tuple:
        """
        เปลี่ยนชื่อ workspace ปัจจุบัน

        Args:
            new_name: ชื่อใหม่

        Returns:
            (success: bool, message: str)
        """
        if not self.current_workspace_id:
            return False, "No workspace loaded"

        # เรียก rename_workspace จาก workspace_manager
        success, message = self.main_window.workspace_manager.rename_workspace(
            self.current_workspace_id,
            new_name
        )

        return success, message

    def delete_workspace(self, workspace_id: str = None) -> bool:
        """
        ลบ workspace

        Args:
            workspace_id: workspace id ที่จะลบ (None = ลบ workspace ปัจจุบัน)

        Returns:
            success: bool
        """
        if workspace_id is None:
            workspace_id = self.current_workspace_id

        if not workspace_id:
            logger.error("No workspace specified")
            return False

        # ถ้าลบ workspace ที่กำลังเปิดอยู่ ให้ clear state
        if workspace_id == self.current_workspace_id:
            self.current_workspace_id = None
            self.current_version = None
            self.version_data = None
            self.main_window.annotations = {}
            self.main_window.image_rotations = {}

        # เรียก delete_workspace จาก workspace_manager
        return self.main_window.workspace_manager.delete_workspace(workspace_id)