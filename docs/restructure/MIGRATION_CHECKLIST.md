# ✅ Migration Checklist - Safe Transition Guide

**Purpose**: Ensure safe transition to new structure
**Risk Level**: 🟢 Low (backward compatible)

---

## 🔒 Pre-Migration Safety

### Step 1: Backup Everything 💾

**Critical Data to Backup:**

```bash
# Backup workspaces
cp -r data/workspaces workspaces_backup_$(date +%Y%m%d)
# or
cp -r workspaces workspaces_backup_$(date +%Y%m%d)

# Backup outputs
cp -r output_det output_det_backup
cp -r output_rec output_rec_backup

# Backup configs
cp recent_workspaces.json recent_workspaces.json.backup
cp config.yaml config.yaml.backup 2>/dev/null || true
cp app_config.json app_config.json.backup 2>/dev/null || true
```

**Status:** [ ] Completed

---

### Step 2: Document Current State 📝

**Record:**
- [ ] List of workspaces: `ls data/workspaces/ > workspace_list.txt`
- [ ] Current settings: Screenshot settings dialog
- [ ] Recent workspace list: `cat recent_workspaces.json`
- [ ] Application works: Test before changes

**Status:** [ ] Completed

---

### Step 3: Git Commit (If Using Git) 🔄

```bash
git add .
git commit -m "Backup before applying restructure"
git tag backup-before-restructure
```

**Status:** [ ] Completed (if applicable)

---

## 📊 Current State Verification

### Check 1: Application Runs ✅

**Test:**
```bash
# Run application
python main.py

# Verify:
- [ ] Application starts
- [ ] Window opens
- [ ] No errors in console
```

**Status:** [ ] Pass

---

### Check 2: Workspace Loads ✅

**Test:**
- [ ] Open existing workspace
- [ ] Verify annotations appear
- [ ] Check images load correctly
- [ ] Test annotation editing

**Status:** [ ] Pass

---

### Check 3: Export Works ✅

**Test:**
- [ ] Export detection dataset (small test)
- [ ] Export recognition dataset (small test)
- [ ] Verify files created
- [ ] Check output quality

**Status:** [ ] Pass

---

## 🔄 Migration Steps

### Phase 1: Verify New Structure ✅

**Already Done:**
- [x] New packages created
- [x] Files organized
- [x] Backward compatibility maintained

**Verification:**
```bash
# Check new structure exists
ls modules/export/
ls modules/utils/
ls modules/gui/handlers/
ls modules/gui/dialogs/
ls modules/gui/items/
```

**Status:** [x] Completed

---

### Phase 2: Test New Imports (Optional) 🧪

**Try New Import Style:**

```python
# Test script: test_new_imports.py
try:
    # Test utils
    from modules.utils import handle_exceptions
    from modules.utils import imread_unicode, imwrite_unicode
    print("✅ Utils imports work")

    # Test export
    from modules.export import DetectionExporter, RecognitionExporter
    print("✅ Export imports work")

    # Test config
    from modules.config import ConfigManager
    print("✅ Config imports work")

    print("\n🎉 All new imports working!")

except Exception as e:
    print(f"❌ Import error: {e}")
```

**Status:** [ ] Tested

---

### Phase 3: Update Imports (When Ready) 📝

**Files to Update (Priority Order):**

1. **main.py** (Highest Priority)
   ```python
   # Old imports → New imports
   # from modules.gui.window_handler.export_handler → modules.gui.handlers.export
   ```
   Status: [ ] Updated [ ] Tested

2. **Handler files** (Medium Priority)
   - All handlers already in new location
   - Old files exist as backup
   Status: [x] Files copied [ ] Old files removed

3. **Dialog files** (Low Priority)
   - All dialogs already in new location
   - Old files exist as backup
   Status: [x] Files copied [ ] Old files removed

4. **Item files** (Low Priority)
   - All items already in new location
   - Old files exist as backup
   Status: [x] Files copied [ ] Old files removed

---

## 🧪 Testing After Updates

### Test 1: Application Startup ✅

**Procedure:**
```bash
python main.py
```

**Verify:**
- [ ] No import errors
- [ ] Window opens normally
- [ ] UI loads correctly
- [ ] Console shows no errors

**Status:** [ ] Pass [ ] Fail

---

### Test 2: Workspace Operations ✅

**Procedure:**
1. Open existing workspace
2. Create new annotation
3. Edit existing annotation
4. Save workspace
5. Switch version
6. Load different workspace

**Verify:**
- [ ] All operations work
- [ ] No data loss
- [ ] Annotations save correctly
- [ ] Versions work

**Status:** [ ] Pass [ ] Fail

---

### Test 3: Export Functions ✅

**Procedure:**
1. Export detection dataset (small sample)
2. Export recognition dataset (small sample)
3. Test with augmentation
4. Test with splits

**Verify:**
- [ ] Detection export works
- [ ] Recognition export works
- [ ] Augmentation applies
- [ ] Splits create correctly
- [ ] Label files valid

**Status:** [ ] Pass [ ] Fail

---

### Test 4: Settings & Config ✅

**Procedure:**
1. Open settings dialog
2. Change profile (CPU ↔ GPU)
3. Modify settings
4. Save and reload
5. Verify settings persist

**Verify:**
- [ ] Settings dialog opens
- [ ] Profile switching works
- [ ] Settings save
- [ ] Settings load correctly

**Status:** [ ] Pass [ ] Fail

---

### Test 5: Version Management ✅

**Procedure:**
1. Create new version
2. Switch between versions
3. Delete old version
4. Verify version data

**Verify:**
- [ ] Version creation works
- [ ] Version switching works
- [ ] Version deletion works
- [ ] Data integrity maintained

**Status:** [ ] Pass [ ] Fail

---

## 🧹 Cleanup (Optional)

### Step 1: Remove Old Files (After Testing) ⚠️

**Only after all tests pass!**

```bash
# Backup first!
mkdir old_files_backup
cp -r modules/gui/window_handler old_files_backup/

# Remove old handler files
rm -rf modules/gui/window_handler/

# Remove old dialog files (from gui root)
rm modules/gui/augmentation_dialog.py
rm modules/gui/split_config_dialog.py
rm modules/gui/settings_dialog.py
rm modules/gui/version_manager_dialog.py
rm modules/gui/workspace_selector_dialog.py

# Remove old item files
rm modules/gui/box_item.py
rm modules/gui/polygon_item.py
rm modules/gui/mask_item.py
rm modules/gui/base_annotation_item.py

# Remove old utils.py (optional - keep for safety)
# mv modules/utils.py modules/utils.py.backup
```

**Status:** [ ] Completed (only after thorough testing!)

---

### Step 2: Clear Python Cache 🗑️

```bash
# Clear __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Clear .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null || true
```

**Status:** [ ] Completed

---

## 🔙 Rollback Procedure

### If Issues Occur:

**Step 1: Stop Application**
- Close application immediately
- Note the error message

**Step 2: Restore from Backup**
```bash
# Restore workspaces
rm -rf data/workspaces
cp -r workspaces_backup_YYYYMMDD data/workspaces

# Restore configs
cp recent_workspaces.json.backup recent_workspaces.json
cp config.yaml.backup config.yaml 2>/dev/null || true
```

**Step 3: Revert Code (If Git)**
```bash
git reset --hard backup-before-restructure
```

**Step 4: Test Baseline**
- Run original application
- Verify everything works
- Investigate issue before retry

---

## ✅ Success Criteria

### Migration Successful When:

- [x] New structure created
- [ ] Application runs without errors
- [ ] All workspaces load correctly
- [ ] Annotations work properly
- [ ] Export functions work
- [ ] Settings persist
- [ ] Version management works
- [ ] No data loss
- [ ] Performance same or better

---

## 📊 Progress Tracking

### Overall Progress:

| Phase | Status | Date |
|-------|--------|------|
| Pre-Migration Safety | [ ] | |
| Current State Verification | [ ] | |
| Structure Verification | [x] | Today |
| Import Testing | [ ] | |
| Import Updates | [ ] | |
| Post-Update Testing | [ ] | |
| Cleanup | [ ] | |

---

## 🎯 Recommendations

### Best Practices:

1. **Go Slow** ⏱️
   - Test each change
   - Don't rush cleanup
   - Verify before proceeding

2. **Keep Backups** 💾
   - Multiple backup points
   - Keep old files temporarily
   - Document changes

3. **Test Thoroughly** 🧪
   - Test all features
   - Use real workspaces
   - Check edge cases

4. **Rollback Ready** 🔙
   - Know how to revert
   - Keep backups accessible
   - Document issues

---

## 🆘 Troubleshooting

### Common Issues:

**Issue 1: Import Errors**
```
Solution: Clear Python cache
Command: find . -name __pycache__ -type d -rm -rf {} +
```

**Issue 2: Workspace Won't Load**
```
Solution: Check workspace.json validity
Command: python -m json.tool data/workspaces/xxx/workspace.json
```

**Issue 3: Export Fails**
```
Solution: Check output directory permissions
Command: ls -la output_det output_rec
```

---

## 📞 Support Checklist

### Before Asking for Help:

- [ ] Checked DATA_SAFETY_GUIDE.md
- [ ] Checked FINAL_RESTRUCTURE_REPORT.md
- [ ] Tried clearing Python cache
- [ ] Verified backups exist
- [ ] Documented error messages
- [ ] Noted steps to reproduce

---

## 🏆 Completion

### When All Checks Pass:

**Congratulations! Migration Complete! 🎉**

You now have:
- ✅ Professional code structure
- ✅ Maintained all data
- ✅ Working application
- ✅ Better organization
- ✅ Easier maintenance

---

**Generated**: Today
**Purpose**: Safe Migration Guide
**Status**: Ready to Use
**Risk Level**: 🟢 Low (backward compatible)
**Success Rate**: High (with proper testing)
