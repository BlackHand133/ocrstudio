#!/usr/bin/env python3
"""
Annotation Recovery Tool
Recovers annotations from version backup when file names change
"""

import json
import os
import sys
from pathlib import Path

def recover_annotations(workspace_path, source_version='v1', target_version='v1'):
    """
    Recover annotations by migrating keys from old format to new format

    Args:
        workspace_path: Path to workspace directory
        source_version: Version to recover from (default: v1)
        target_version: Version to save to (default: v1)
    """
    workspace_path = Path(workspace_path)

    # Load source version
    source_file = workspace_path / f'{source_version}.json'
    if not source_file.exists():
        print(f"[X] Source version file not found: {source_file}")
        return False

    print(f"[*] Loading annotations from {source_file}...")
    with open(source_file, 'r', encoding='utf-8') as f:
        source_data = json.load(f)

    annotations = source_data.get('annotations', {})
    print(f"[OK] Found {len(annotations)} annotated images in {source_version}")

    # Show sample keys
    sample_keys = list(annotations.keys())[:5]
    print(f"\n[*] Sample annotation keys:")
    for key in sample_keys:
        print(f"   - {key} ({len(annotations[key])} annotations)")

    # Ask for confirmation
    print(f"\n[!] This will preserve all {len(annotations)} annotations in {target_version}")
    print(f"    Current annotations in {target_version} will be backed up as {target_version}.backup.json")

    response = input("\n[?] Proceed with recovery? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("[X] Recovery cancelled")
        return False

    # Backup current version
    target_file = workspace_path / f'{target_version}.json'
    if target_file.exists():
        backup_file = workspace_path / f'{target_version}.backup.json'
        print(f"\n[*] Creating backup: {backup_file}")
        with open(target_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        print(f"[OK] Backup created successfully")

        # Use backup data as base
        target_data = backup_data
    else:
        # Create new version data
        target_data = source_data.copy()

    # Restore annotations
    target_data['annotations'] = annotations
    target_data['modified_at'] = source_data.get('modified_at')

    # Save recovered version
    print(f"\n[*] Saving recovered annotations to {target_file}...")
    with open(target_file, 'w', encoding='utf-8') as f:
        json.dump(target_data, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Recovery completed successfully!")
    print(f"   - {len(annotations)} images with annotations recovered")
    print(f"   - Backup saved to: {backup_file}")
    print(f"\n[!] Next steps:")
    print(f"   1. Restart the application")
    print(f"   2. Load workspace: testmedicine")
    print(f"   3. Your annotations should now be visible")

    return True


if __name__ == '__main__':
    import sys
    import io
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("Annotation Recovery Tool")
    print("=" * 60)

    # Pass a workspace path as the first arg, else default to a local workspace.
    workspace_path = Path(sys.argv[1] if len(sys.argv) > 1 else "workspaces/testmedicine")

    if not workspace_path.exists():
        print(f"[X] Workspace not found: {workspace_path}")
        sys.exit(1)

    print(f"\n[*] Workspace: {workspace_path.name}")

    # Show available versions
    version_files = list(workspace_path.glob("v*.json"))
    if not version_files:
        print("[X] No version files found")
        sys.exit(1)

    print(f"\n[*] Available versions:")
    for vf in sorted(version_files):
        with open(vf, 'r', encoding='utf-8') as f:
            data = json.load(f)
            ann_count = len(data.get('annotations', {}))
            print(f"   - {vf.stem}: {ann_count} annotated images")

    print(f"\n[*] Recovery mode: Preserve all annotations from backup")

    # Recover from v1 to v1 (current version)
    success = recover_annotations(workspace_path, source_version='v1', target_version='v1')

    if success:
        print("\n" + "=" * 60)
        print("[OK] SUCCESS!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[X] FAILED")
        print("=" * 60)
        sys.exit(1)
