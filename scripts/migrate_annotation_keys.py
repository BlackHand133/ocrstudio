#!/usr/bin/env python3
"""
Annotation Key Migration Tool
Migrates annotation keys from old format (0001_filename.jpg) to new format (filename.jpg)
"""

import json
import os
import sys
import re
from pathlib import Path

def migrate_keys(workspace_path):
    """
    Migrate annotation keys from index-based to filename-only

    Old format: 0001_filename.jpg
    New format: filename.jpg

    Args:
        workspace_path: Path to workspace directory
    """
    workspace_path = Path(workspace_path)

    # Find all version files
    version_files = list(workspace_path.glob("v*.json"))
    if not version_files:
        print("[X] No version files found")
        return False

    print(f"\n[*] Found {len(version_files)} version file(s)")

    # Pattern to match old key format: 0001_filename.jpg
    old_key_pattern = re.compile(r'^\d{4}_(.+)$')

    total_migrated = 0

    for version_file in sorted(version_files):
        print(f"\n[*] Processing {version_file.name}...")

        # Load version data
        with open(version_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        annotations = data.get('annotations', {})
        transforms = data.get('transforms', {})

        if not annotations:
            print(f"    [!] No annotations found, skipping")
            continue

        # Migrate annotation keys
        new_annotations = {}
        migrated_count = 0

        for old_key, ann_list in annotations.items():
            match = old_key_pattern.match(old_key)
            if match:
                # Extract filename part
                new_key = match.group(1)
                new_annotations[new_key] = ann_list
                migrated_count += 1
                print(f"    [OK] {old_key} -> {new_key}")
            else:
                # Already in new format or unknown format
                new_annotations[old_key] = ann_list

        # Migrate transform keys
        new_transforms = {}
        for old_key, rotation in transforms.items():
            match = old_key_pattern.match(old_key)
            if match:
                new_key = match.group(1)
                new_transforms[new_key] = rotation
            else:
                new_transforms[old_key] = rotation

        # Update data
        data['annotations'] = new_annotations
        data['transforms'] = new_transforms

        # Backup original
        backup_file = version_file.with_suffix('.json.premigration')
        print(f"    [*] Creating backup: {backup_file.name}")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                'version': data.get('version'),
                'annotations': annotations,
                'transforms': transforms
            }, f, ensure_ascii=False, indent=2)

        # Save migrated version
        print(f"    [*] Saving migrated data...")
        with open(version_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"    [OK] Migrated {migrated_count} annotation keys")
        total_migrated += migrated_count

    return total_migrated > 0, total_migrated


if __name__ == '__main__':
    import io
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("Annotation Key Migration Tool")
    print("=" * 60)

    # Pass a workspace path as the first arg, else default to a local workspace.
    workspace_path = Path(sys.argv[1] if len(sys.argv) > 1 else "workspaces/testmedicine")

    if not workspace_path.exists():
        print(f"[X] Workspace not found: {workspace_path}")
        sys.exit(1)

    print(f"\n[*] Workspace: {workspace_path.name}")
    print(f"[!] This will migrate annotation keys from old to new format:")
    print(f"    Old: 0001_filename.jpg")
    print(f"    New: filename.jpg")

    response = input("\n[?] Proceed with migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("[X] Migration cancelled")
        sys.exit(0)

    success, count = migrate_keys(workspace_path)

    if success:
        print("\n" + "=" * 60)
        print(f"[OK] SUCCESS! Migrated {count} annotation keys")
        print("=" * 60)
        print("\n[!] Next steps:")
        print("   1. Restart the application")
        print("   2. Load workspace: testmedicine")
        print("   3. Annotations will now use stable filename-based keys")
    else:
        print("\n" + "=" * 60)
        print("[X] No keys to migrate")
        print("=" * 60)
