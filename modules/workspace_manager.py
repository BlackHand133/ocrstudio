# modules/workspace_manager.py

import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("TextDetGUI")


class WorkspaceManager:
    """
    จัดการ Workspaces และ Versions
    """
    
    def __init__(self, root_dir: str):
        """
        Args:
            root_dir: project root directory
        """
        self.root_dir = root_dir
        self.workspaces_dir = os.path.join(root_dir, "workspaces")
        self.app_config_path = os.path.join(root_dir, "app_config.json")
        self.recent_workspaces_path = os.path.join(root_dir, "recent_workspaces.json")
        
        # สร้างโฟลเดอร์
        os.makedirs(self.workspaces_dir, exist_ok=True)
        
        # โหลด config
        self.app_config = self._load_app_config()
        self.recent_workspaces = self._load_recent_workspaces()
    
    # ===== Workspace Management =====
    
    def create_workspace(self, workspace_id: str, name: str, 
                        source_folder: str, description: str = "") -> bool:
        """
        สร้าง workspace ใหม่
        
        Returns:
            True ถ้าสำเร็จ
        """
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            
            if os.path.exists(workspace_path):
                logger.error(f"Workspace {workspace_id} already exists")
                return False
            
            os.makedirs(workspace_path, exist_ok=True)
            
            # สร้าง workspace.json
            workspace_data = {
                "version": "2.0.0",
                "workspace": {
                    "id": workspace_id,
                    "name": name,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat()
                },
                "source": {
                    "folder": source_folder,
                    "total_images": 0,
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
            
            workspace_file = os.path.join(workspace_path, "workspace.json")
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(workspace_data, f, ensure_ascii=False, indent=2)
            
            # สร้าง v1.json เปล่า
            v1_data = {
                "version": "2.0.0",
                "workspace_id": workspace_id,
                "data_version": "v1",
                "created_at": datetime.now().isoformat(),
                "modified_at": datetime.now().isoformat(),
                "description": "Initial version",
                "annotations": {},
                "transforms": {},
                "metadata": {
                    "total_images": 0,
                    "annotated_images": 0,
                    "total_annotations": 0
                }
            }
            
            v1_file = os.path.join(workspace_path, "v1.json")
            with open(v1_file, 'w', encoding='utf-8') as f:
                json.dump(v1_data, f, ensure_ascii=False, indent=2)
            
            # สร้าง exports.json เปล่า
            exports_data = {
                "version": "2.0.0",
                "workspace_id": workspace_id,
                "exports": []
            }
            
            exports_file = os.path.join(workspace_path, "exports.json")
            with open(exports_file, 'w', encoding='utf-8') as f:
                json.dump(exports_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created workspace: {workspace_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            return False
    
    def get_workspace_list(self) -> List[Dict]:
        """
        ดึงรายการ workspace ทั้งหมด
        
        Returns:
            List of workspace info dicts
        """
        workspaces = []
        
        if not os.path.exists(self.workspaces_dir):
            return workspaces
        
        for item in os.listdir(self.workspaces_dir):
            workspace_path = os.path.join(self.workspaces_dir, item)
            workspace_file = os.path.join(workspace_path, "workspace.json")
            
            if os.path.isdir(workspace_path) and os.path.exists(workspace_file):
                try:
                    with open(workspace_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    workspaces.append({
                        "id": item,
                        "name": data["workspace"]["name"],
                        "description": data["workspace"].get("description", ""),
                        "source_folder": data["source"]["folder"],
                        "current_version": data["versions"]["current"],
                        "modified_at": data["workspace"]["modified_at"]
                    })
                except Exception as e:
                    logger.error(f"Failed to load workspace {item}: {e}")
        
        return workspaces
    
    def load_workspace(self, workspace_id: str) -> Optional[Dict]:
        """
        โหลด workspace

        Returns:
            workspace data หรือ None
        """
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            workspace_file = os.path.join(workspace_path, "workspace.json")

            if not os.path.exists(workspace_file):
                logger.error(f"Workspace not found: {workspace_id}")
                return None

            with open(workspace_file, 'r', encoding='utf-8') as f:
                workspace_data = json.load(f)

            # ตรวจสอบและซ่อมแซม version list
            workspace_data = self._validate_and_repair_workspace(workspace_id, workspace_data)

            return workspace_data

        except Exception as e:
            logger.error(f"Failed to load workspace: {e}")
            return None

    def _validate_and_repair_workspace(self, workspace_id: str, workspace_data: Dict) -> Dict:
        """
        ตรวจสอบและซ่อมแซม workspace data
        - ตรวจสอบว่า version ที่อยู่ใน available list มีไฟล์จริงหรือไม่
        - ลบ version ที่ไม่มีไฟล์ออกจาก list
        - ตรวจสอบ current version ว่ายังมีอยู่หรือไม่
        """
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            available_versions = workspace_data.get("versions", {}).get("available", [])
            current_version = workspace_data.get("versions", {}).get("current", "v1")

            # ตรวจสอบว่า version ไหนมีไฟล์จริง
            valid_versions = []
            for version in available_versions:
                version_file = os.path.join(workspace_path, f"{version}.json")
                if os.path.exists(version_file):
                    valid_versions.append(version)
                else:
                    logger.warning(f"Version file not found: {version}.json - removing from list")

            # ถ้ามีการเปลี่ยนแปลง ให้อัพเดต
            if valid_versions != available_versions:
                workspace_data["versions"]["available"] = valid_versions

                # ตรวจสอบ current version
                if current_version not in valid_versions:
                    if valid_versions:
                        # เปลี่ยน current เป็น version แรกที่มีอยู่
                        workspace_data["versions"]["current"] = valid_versions[0]
                        logger.warning(f"Current version {current_version} not found, changed to {valid_versions[0]}")
                    else:
                        logger.error(f"No valid versions found in workspace {workspace_id}")

                # บันทึกการเปลี่ยนแปลง
                workspace_file = os.path.join(workspace_path, "workspace.json")
                with open(workspace_file, 'w', encoding='utf-8') as f:
                    json.dump(workspace_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Repaired workspace {workspace_id}: removed {len(available_versions) - len(valid_versions)} invalid version(s)")

            return workspace_data

        except Exception as e:
            logger.error(f"Failed to validate workspace: {e}")
            return workspace_data
    
    def save_workspace(self, workspace_id: str, data: Dict) -> bool:
        """บันทึก workspace metadata"""
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            workspace_file = os.path.join(workspace_path, "workspace.json")
            
            data["workspace"]["modified_at"] = datetime.now().isoformat()
            
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to save workspace: {e}")
            return False
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """ลบ workspace"""
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)

            if os.path.exists(workspace_path):
                shutil.rmtree(workspace_path)
                logger.info(f"Deleted workspace: {workspace_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete workspace: {e}")
            return False

    def repair_workspace(self, workspace_id: str) -> Tuple[bool, str]:
        """
        ซ่อมแซม workspace โดยตรวจสอบและแก้ไขข้อมูลที่ไม่ตรงกัน

        Returns:
            (success: bool, message: str)
        """
        try:
            workspace_data = self.load_workspace(workspace_id)
            if not workspace_data:
                return False, "Workspace not found"

            workspace_path = os.path.join(self.workspaces_dir, workspace_id)

            # หา version files ที่มีจริง
            actual_version_files = []
            for file in os.listdir(workspace_path):
                if file.startswith('v') and file.endswith('.json'):
                    version_name = file[:-5]  # ตัด .json
                    actual_version_files.append(version_name)

            # เรียงตาม version number
            actual_version_files.sort(key=lambda v: int(v[1:]) if v[1:].isdigit() else 0)

            # เปรียบเทียบกับ available list
            available_versions = workspace_data.get("versions", {}).get("available", [])
            current_version = workspace_data.get("versions", {}).get("current", "v1")

            removed_versions = [v for v in available_versions if v not in actual_version_files]
            missing_versions = [v for v in actual_version_files if v not in available_versions]

            changes = []

            # อัพเดต available list
            if actual_version_files != available_versions:
                workspace_data["versions"]["available"] = actual_version_files
                changes.append(f"Updated available versions: {actual_version_files}")

            # ตรวจสอบ current version
            if current_version not in actual_version_files:
                if actual_version_files:
                    workspace_data["versions"]["current"] = actual_version_files[0]
                    changes.append(f"Changed current version from '{current_version}' to '{actual_version_files[0]}'")
                else:
                    return False, "No valid version files found"

            # บันทึก
            if changes:
                self.save_workspace(workspace_id, workspace_data)
                message = "Workspace repaired:\n"
                if removed_versions:
                    message += f"  - Removed invalid versions: {', '.join(removed_versions)}\n"
                if missing_versions:
                    message += f"  - Added missing versions: {', '.join(missing_versions)}\n"
                message += f"\n".join(f"  - {change}" for change in changes)
                return True, message
            else:
                return True, "Workspace is already valid, no repairs needed"

        except Exception as e:
            error_msg = f"Failed to repair workspace: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    # ===== Version Management =====
    
    def load_version(self, workspace_id: str, version: str) -> Optional[Dict]:
        """
        โหลด version data
        
        Returns:
            version data หรือ None
        """
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            version_file = os.path.join(workspace_path, f"{version}.json")
            
            if not os.path.exists(version_file):
                logger.error(f"Version not found: {version}")
                return None
            
            with open(version_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        except Exception as e:
            logger.error(f"Failed to load version: {e}")
            return None
    
    def save_version(self, workspace_id: str, version: str, data: Dict) -> bool:
        """บันทึก version data"""
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            version_file = os.path.join(workspace_path, f"{version}.json")
            
            data["modified_at"] = datetime.now().isoformat()
            
            # อัปเดต metadata
            data["metadata"] = {
                "total_images": len(data.get("annotations", {})),
                "annotated_images": len([k for k, v in data.get("annotations", {}).items() if v]),
                "total_annotations": sum(len(v) for v in data.get("annotations", {}).values())
            }
            
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to save version: {e}")
            return False
    
    def create_version(self, workspace_id: str, new_version: str, 
                      base_version: Optional[str] = None, 
                      description: str = "") -> bool:
        """
        สร้าง version ใหม่
        
        Args:
            workspace_id: workspace id
            new_version: version ใหม่ เช่น "v2"
            base_version: version ที่จะคัดลอกมา (None = สร้างเปล่า)
            description: คำอธิบาย
        """
        try:
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            new_version_file = os.path.join(workspace_path, f"{new_version}.json")
            
            if os.path.exists(new_version_file):
                logger.error(f"Version {new_version} already exists")
                return False
            
            # ถ้ามี base_version ให้คัดลอกมา
            if base_version:
                base_data = self.load_version(workspace_id, base_version)
                if not base_data:
                    return False
                
                new_data = base_data.copy()
                new_data["data_version"] = new_version
                new_data["created_at"] = datetime.now().isoformat()
                new_data["description"] = description
                new_data["parent_version"] = base_version
            else:
                # สร้างเปล่า
                new_data = {
                    "version": "2.0.0",
                    "workspace_id": workspace_id,
                    "data_version": new_version,
                    "created_at": datetime.now().isoformat(),
                    "modified_at": datetime.now().isoformat(),
                    "description": description,
                    "annotations": {},
                    "transforms": {},
                    "metadata": {
                        "total_images": 0,
                        "annotated_images": 0,
                        "total_annotations": 0
                    }
                }
            
            # บันทึก
            with open(new_version_file, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            
            # อัปเดต workspace.json
            workspace_data = self.load_workspace(workspace_id)
            if workspace_data:
                workspace_data["versions"]["available"].append(new_version)
                self.save_workspace(workspace_id, workspace_data)
            
            logger.info(f"Created version: {new_version}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create version: {e}")
            return False
    
    def switch_version(self, workspace_id: str, version: str) -> bool:
        """สลับไป version อื่น"""
        try:
            workspace_data = self.load_workspace(workspace_id)
            if not workspace_data:
                return False

            if version not in workspace_data["versions"]["available"]:
                logger.error(f"Version {version} not found")
                return False

            workspace_data["versions"]["current"] = version
            return self.save_workspace(workspace_id, workspace_data)

        except Exception as e:
            logger.error(f"Failed to switch version: {e}")
            return False

    def delete_version(self, workspace_id: str, version: str) -> Tuple[bool, str]:
        """
        ลบ version

        Args:
            workspace_id: workspace id
            version: version ที่จะลบ เช่น "v2"

        Returns:
            (success: bool, message: str)
        """
        try:
            # ตรวจสอบว่า workspace มีอยู่
            workspace_data = self.load_workspace(workspace_id)
            if not workspace_data:
                return False, "Workspace not found"

            # ตรวจสอบว่า version มีอยู่
            available_versions = workspace_data["versions"]["available"]
            if version not in available_versions:
                return False, f"Version {version} not found"

            # ป้องกันการลบ version สุดท้าย
            if len(available_versions) == 1:
                return False, "Cannot delete the last version. At least one version must remain."

            # ป้องกันการลบ version ที่กำลังใช้งาน
            current_version = workspace_data["versions"]["current"]
            if version == current_version:
                return False, f"Cannot delete the current version ({version}). Please switch to another version first."

            # ลบไฟล์ version
            workspace_path = os.path.join(self.workspaces_dir, workspace_id)
            version_file = os.path.join(workspace_path, f"{version}.json")

            if os.path.exists(version_file):
                os.remove(version_file)
                logger.info(f"Deleted version file: {version_file}")

            # อัปเดต workspace.json
            available_versions.remove(version)
            workspace_data["versions"]["available"] = available_versions
            self.save_workspace(workspace_id, workspace_data)

            logger.info(f"Deleted version: {version} from workspace: {workspace_id}")
            return True, f"Version {version} deleted successfully"

        except Exception as e:
            error_msg = f"Failed to delete version: {e}"
            logger.error(error_msg)
            return False, error_msg

    def get_version_list(self, workspace_id: str) -> List[Dict]:
        """
        ดึงรายการ version ทั้งหมดใน workspace

        Returns:
            List of version info dicts
        """
        versions = []

        try:
            workspace_data = self.load_workspace(workspace_id)
            if not workspace_data:
                return versions

            current_version = workspace_data["versions"]["current"]
            available_versions = workspace_data["versions"]["available"]

            for version in available_versions:
                version_data = self.load_version(workspace_id, version)
                if version_data:
                    versions.append({
                        "version": version,
                        "description": version_data.get("description", ""),
                        "created_at": version_data.get("created_at", ""),
                        "modified_at": version_data.get("modified_at", ""),
                        "is_current": version == current_version,
                        "metadata": version_data.get("metadata", {})
                    })

        except Exception as e:
            logger.error(f"Failed to get version list: {e}")

        return versions

    def rename_workspace(self, workspace_id: str, new_name: str) -> Tuple[bool, str]:
        """
        เปลี่ยนชื่อ workspace (เปลี่ยนเฉพาะชื่อที่แสดง ไม่เปลี่ยน workspace_id)

        Args:
            workspace_id: workspace id
            new_name: ชื่อใหม่

        Returns:
            (success: bool, message: str)
        """
        try:
            # ตรวจสอบว่าชื่อใหม่ไม่ว่าง
            if not new_name or not new_name.strip():
                return False, "Workspace name cannot be empty"

            new_name = new_name.strip()

            # โหลด workspace data
            workspace_data = self.load_workspace(workspace_id)
            if not workspace_data:
                return False, "Workspace not found"

            # อัปเดตชื่อ
            old_name = workspace_data["workspace"]["name"]
            workspace_data["workspace"]["name"] = new_name

            # บันทึก
            if self.save_workspace(workspace_id, workspace_data):
                logger.info(f"Renamed workspace {workspace_id}: '{old_name}' -> '{new_name}'")

                # อัปเดต recent_workspaces ถ้ามี
                self._update_recent_workspace_name(workspace_id, new_name)

                return True, f"Workspace renamed to '{new_name}' successfully"
            else:
                return False, "Failed to save workspace"

        except Exception as e:
            error_msg = f"Failed to rename workspace: {e}"
            logger.error(error_msg)
            return False, error_msg

    def _update_recent_workspace_name(self, workspace_id: str, new_name: str):
        """อัปเดตชื่อใน recent_workspaces.json"""
        try:
            workspaces = self.recent_workspaces.get("workspaces", [])

            for workspace in workspaces:
                if workspace.get("id") == workspace_id:
                    workspace["name"] = new_name

            self.recent_workspaces["workspaces"] = workspaces

            with open(self.recent_workspaces_path, 'w', encoding='utf-8') as f:
                json.dump(self.recent_workspaces, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"Failed to update recent workspace name: {e}")
    
    # ===== App Config =====
    
    def _load_app_config(self) -> Dict:
        """โหลด app config"""
        if os.path.exists(self.app_config_path):
            try:
                with open(self.app_config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default config
        return {
            "version": "2.0.0",
            "current_workspace": None,
            "ui_state": {
                "window_size": [1400, 900]
            }
        }
    
    def save_app_config(self) -> bool:
        """บันทึก app config"""
        try:
            with open(self.app_config_path, 'w', encoding='utf-8') as f:
                json.dump(self.app_config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save app config: {e}")
            return False
    
    def _load_recent_workspaces(self) -> Dict:
        """โหลด recent workspaces"""
        if os.path.exists(self.recent_workspaces_path):
            try:
                with open(self.recent_workspaces_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "version": "2.0.0",
            "workspaces": []
        }
    
    def add_recent_workspace(self, workspace_id: str):
        """เพิ่ม workspace เข้า recent list"""
        workspaces = self.recent_workspaces.get("workspaces", [])
        
        # ลบถ้ามีอยู่แล้ว
        workspaces = [w for w in workspaces if w.get("id") != workspace_id]
        
        # เพิ่มที่ด้านบน
        workspace_data = self.load_workspace(workspace_id)
        if workspace_data:
            workspaces.insert(0, {
                "id": workspace_id,
                "name": workspace_data["workspace"]["name"],
                "last_opened": datetime.now().isoformat()
            })
        
        # เก็บแค่ 10 รายการล่าสุด
        workspaces = workspaces[:10]
        
        self.recent_workspaces["workspaces"] = workspaces
        
        try:
            with open(self.recent_workspaces_path, 'w', encoding='utf-8') as f:
                json.dump(self.recent_workspaces, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save recent workspaces: {e}")