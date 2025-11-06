# modules/gui/window_handler/table_handler.py

import logging
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from modules.utils import handle_exceptions, sanitize_annotations

logger = logging.getLogger("TextDetGUI")
PLACEHOLDER_TEXT = "<no_label>"


class TableHandler:
    """
    จัดการตาราง Recognition: แสดง, แก้ไข transcription
    """
    
    def __init__(self, main_window):
        """
        Args:
            main_window: reference ไปยัง MainWindow instance
        """
        self.main_window = main_window
    
    def _get_annotation_items_with_transcription(self):
        """
        กรองเฉพาะ annotation items ที่มี transcription (ไม่ใช่ mask items)
        
        Returns:
            list: [(index, box_item), ...] ของ items ที่มี get_transcription method
        """
        items_with_transcription = []
        for idx, box in enumerate(self.main_window.box_items):
            # เช็คว่ามี method get_transcription หรือไม่
            if hasattr(box, 'get_transcription') and callable(getattr(box, 'get_transcription')):
                items_with_transcription.append((idx, box))
        return items_with_transcription
    
    def populate_table(self):
        """เติมข้อมูลในตาราง - เฉพาะ items ที่มี transcription"""
        table = self.main_window.table
        
        # Block signals เพื่อไม่ให้ trigger on_table_item_changed
        table.blockSignals(True)
        
        # ล้างตาราง
        table.clearContents()
        
        # กรองเฉพาะ items ที่มี transcription (ไม่ใช่ mask items)
        items_with_transcription = self._get_annotation_items_with_transcription()
        
        # ตั้งจำนวนแถวตามจำนวน items ที่มี transcription
        table.setRowCount(len(items_with_transcription))
        
        # เติมข้อมูล
        for table_row, (original_idx, box) in enumerate(items_with_transcription):
            # คอลัมน์ ID (ไม่สามารถแก้ไขได้) - แสดง index เดิมใน box_items
            item_id = QtWidgets.QTableWidgetItem(str(original_idx))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            # เก็บ original index ไว้ใน data เพื่อใช้ในการอัปเดต
            item_id.setData(Qt.UserRole, original_idx)
            table.setItem(table_row, 0, item_id)
            
            # คอลัมน์ Transcription (แก้ไขได้)
            txt = box.get_transcription() or PLACEHOLDER_TEXT
            transcription_item = QtWidgets.QTableWidgetItem(txt)
            # เก็บ original index ไว้ใน data เพื่อใช้ในการอัปเดต
            transcription_item.setData(Qt.UserRole, original_idx)
            table.setItem(table_row, 1, transcription_item)
        
        table.blockSignals(False)
        logger.debug(f"Populated table with {len(items_with_transcription)} annotation items (filtered from {len(self.main_window.box_items)} total items)")
    
    @handle_exceptions
    def on_table_item_changed(self, item):
        """
        เมื่อแก้ไขข้อมูลในตาราง
        
        Args:
            item: QTableWidgetItem ที่ถูกแก้ไข
        """
        col = item.column()
        
        # แก้ไขได้เฉพาะคอลัมน์ Transcription (col=1)
        if col == 1:
            # ดึง original index จาก data
            original_idx = item.data(Qt.UserRole)
            
            if original_idx is not None and 0 <= original_idx < len(self.main_window.box_items):
                box = self.main_window.box_items[original_idx]
                
                # เช็คว่า box มี method set_transcription หรือไม่
                if hasattr(box, 'set_transcription') and callable(getattr(box, 'set_transcription')):
                    new_txt = item.text().strip() or PLACEHOLDER_TEXT
                    
                    # อัปเดต transcription
                    box.set_transcription(new_txt)
                    
                    # บันทึก
                    annotations = [b.to_dict() for b in self.main_window.box_items]
                    self.main_window.annotations[self.main_window.img_key] = sanitize_annotations(annotations)
                    self.main_window.workspace_handler.save_workspace()
                    
                    logger.debug(f"Updated transcription for box {original_idx}: {new_txt[:20]}")
                else:
                    logger.warning(f"Box at index {original_idx} does not have set_transcription method")
    
    def on_table_selection_changed(self):
        """เมื่อเลือกแถวในตาราง"""
        # ยกเลิกการเลือกทั้งหมดก่อน
        for box in self.main_window.box_items:
            box.setSelected(False)
        
        # เลือก box ที่ตรงกับแถว
        sel = self.main_window.table.selectedIndexes()
        if not sel:
            return
        
        # ดึง original index จาก data
        item = self.main_window.table.item(sel[0].row(), 0)  # ใช้คอลัมน์ ID
        if item:
            original_idx = item.data(Qt.UserRole)
            
            if original_idx is not None and 0 <= original_idx < len(self.main_window.box_items):
                box = self.main_window.box_items[original_idx]
                box.setSelected(True)
                
                # เลื่อน view ไปที่ box
                self.main_window.view.centerOn(box)
                
                logger.debug(f"Selected box {original_idx} from table")