"""
Test script to verify stable key generation prevents annotation loss
"""

import os
import sys
import re
from pathlib import Path

# Set UTF-8 encoding for console output
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))


def simulate_old_key_generation(files, folder):
    """Simulate old index-based key generation"""
    keys = {}
    idx = 1
    for fn in sorted(files):
        key = f"{idx:04d}_{fn}"
        keys[fn] = key
        idx += 1
    return keys


def simulate_new_key_generation(files, folder):
    """Simulate new relative path-based key generation"""
    keys = {}
    for fn in sorted(files):
        # In real code, this would be relative path
        # For flat folder, it's just the filename
        key = fn
        keys[fn] = key
    return keys


def migrate_old_keys(old_annotations):
    """Simulate migration logic"""
    migrated = {}
    old_format_pattern = re.compile(r'^\d{4}_(.+)$')

    for old_key, ann_data in old_annotations.items():
        match = old_format_pattern.match(old_key)
        if match:
            new_key = match.group(1)
            migrated[new_key] = ann_data
        else:
            migrated[old_key] = ann_data

    return migrated


def test_scenario():
    print("\n" + "="*80)
    print("TEST: Annotation Stability When Adding New Images")
    print("="*80)

    # Scenario 1: Initial state
    print("\n📁 Day 1: Initial folder contents")
    initial_files = ['7.jpg', '8422.jpg', '8423.jpg']
    print(f"Files: {initial_files}")

    # Old system
    print("\n[OLD SYSTEM] Index-based keys:")
    old_keys_day1 = simulate_old_key_generation(initial_files, None)
    for fn, key in old_keys_day1.items():
        print(f"  {fn:<15} → {key}")

    # New system
    print("\n[NEW SYSTEM] Filename-based keys:")
    new_keys_day1 = simulate_new_key_generation(initial_files, None)
    for fn, key in new_keys_day1.items():
        print(f"  {fn:<15} → {key}")

    # Simulate annotations
    print("\n💾 User creates annotations:")
    old_annotations = {
        '0001_7.jpg': [{'text': 'Annotation for 7.jpg'}],
        '0002_8422.jpg': [{'text': 'Annotation for 8422.jpg'}],
        '0003_8423.jpg': [{'text': 'Annotation for 8423.jpg'}]
    }
    new_annotations = {
        '7.jpg': [{'text': 'Annotation for 7.jpg'}],
        '8422.jpg': [{'text': 'Annotation for 8422.jpg'}],
        '8423.jpg': [{'text': 'Annotation for 8423.jpg'}]
    }
    for key in old_annotations:
        print(f"  ✓ Saved annotation for: {key}")

    # Scenario 2: Add new file
    print("\n📁 Day 2: User adds new file '6.jpg'")
    new_files = ['6.jpg', '7.jpg', '8422.jpg', '8423.jpg']
    print(f"Files: {new_files}")

    # Old system
    print("\n[OLD SYSTEM] Keys after adding file:")
    old_keys_day2 = simulate_old_key_generation(new_files, None)
    for fn, key in old_keys_day2.items():
        print(f"  {fn:<15} → {key}")

    print("\n❌ OLD SYSTEM: Trying to load annotations...")
    old_lost = 0
    for fn in new_files:
        new_key = old_keys_day2[fn]
        if new_key in old_annotations:
            print(f"  ✓ Found annotation for {fn} with key {new_key}")
        else:
            print(f"  ✗ LOST annotation for {fn} (looking for {new_key}, not found)")
            old_lost += 1

    # New system
    print("\n[NEW SYSTEM] Keys after adding file:")
    new_keys_day2 = simulate_new_key_generation(new_files, None)
    for fn, key in new_keys_day2.items():
        print(f"  {fn:<15} → {key}")

    print("\n✓ NEW SYSTEM: Trying to load annotations...")
    new_lost = 0
    for fn in new_files:
        new_key = new_keys_day2[fn]
        if new_key in new_annotations:
            print(f"  ✓ Found annotation for {fn} with key {new_key}")
        else:
            # This is expected for the new file
            if fn == '6.jpg':
                print(f"  - New file {fn}, no annotation yet")
            else:
                print(f"  ✗ LOST annotation for {fn}")
                new_lost += 1

    # Test migration
    print("\n🔄 Testing Migration:")
    print("Converting old format annotations to new format...")
    migrated = migrate_old_keys(old_annotations)

    print("\nMigrated keys:")
    for new_key, ann_data in migrated.items():
        print(f"  {new_key:<15} → {ann_data[0]['text']}")

    print("\n✓ After migration, checking if annotations can be loaded:")
    migration_lost = 0
    for fn in new_files:
        if fn in migrated:
            print(f"  ✓ Found annotation for {fn}")
        else:
            if fn == '6.jpg':
                print(f"  - New file {fn}, no annotation yet")
            else:
                print(f"  ✗ LOST annotation for {fn}")
                migration_lost += 1

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    print(f"\n📊 Annotations Lost:")
    print(f"  OLD SYSTEM (index-based):     {old_lost} / 3 annotations LOST  {'❌' if old_lost > 0 else '✓'}")
    print(f"  NEW SYSTEM (filename-based):  {new_lost} / 3 annotations LOST  {'❌' if new_lost > 0 else '✓'}")
    print(f"  MIGRATION (old → new):        {migration_lost} / 3 annotations LOST  {'❌' if migration_lost > 0 else '✓'}")

    if old_lost > 0 and new_lost == 0:
        print("\n✅ SUCCESS: New system prevents annotation loss!")
    else:
        print("\n❌ FAILED: Issue detected in new system")

    if migration_lost == 0:
        print("✅ SUCCESS: Migration successfully recovers old annotations!")
    else:
        print("❌ FAILED: Migration did not recover all annotations")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_scenario()
