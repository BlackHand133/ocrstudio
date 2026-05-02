"""
Ajan OCR — Headless CLI

Provides command-line access to detection and export without Qt.

Usage:
    python -m modules.cli detect  --workspace <path> [--profile cpu|gpu]
    python -m modules.cli export  --workspace <path> --output <dir> [--format ppocr]
    python -m modules.cli version

No PyQt5 imports are allowed in this module or its callee chain.
"""

import argparse
import json
import logging
import os
import sys

logger = logging.getLogger("AjanCLI")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)

    _setup_logging(args.log_level if hasattr(args, "log_level") else "INFO")

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ajan-ocr-cli",
        description="Ajan OCR annotation tool — headless CLI",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )

    sub = parser.add_subparsers(title="commands")

    # ---- version ----
    ver = sub.add_parser("version", help="Print version and exit")
    ver.set_defaults(func=_cmd_version)

    # ---- detect ----
    det = sub.add_parser(
        "detect",
        help="Run OCR auto-detection on all images in a workspace version",
    )
    det.add_argument(
        "--workspace", required=True,
        metavar="PATH",
        help="Path to workspace directory (contains workspace.json)",
    )
    det.add_argument(
        "--version-id",
        default=None,
        metavar="ID",
        help="Version ID to update (default: latest)",
    )
    det.add_argument(
        "--profile",
        default=None,
        choices=["cpu", "gpu"],
        help="OCR profile to use (default: from config.yaml)",
    )
    det.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing annotations (default: skip annotated images)",
    )
    det.set_defaults(func=_cmd_detect)

    # ---- export ----
    exp = sub.add_parser(
        "export",
        help="Export annotations from a workspace to PaddleOCR label format",
    )
    exp.add_argument(
        "--workspace", required=True,
        metavar="PATH",
        help="Path to workspace directory",
    )
    exp.add_argument(
        "--output", required=True,
        metavar="DIR",
        help="Output directory for the exported dataset",
    )
    exp.add_argument(
        "--version-id",
        default=None,
        metavar="ID",
        help="Version ID to export (default: latest)",
    )
    exp.add_argument(
        "--format",
        default="ppocr",
        choices=["ppocr"],
        help="Export format (default: ppocr)",
    )
    exp.set_defaults(func=_cmd_export)

    return parser


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def _cmd_version(args) -> int:
    from modules.__version__ import __version__
    print(f"Ajan OCR  v{__version__}")
    return 0


def _cmd_detect(args) -> int:
    """
    Run OCR detection on every image listed in a workspace version JSON.
    Saves updated annotations back to the same version file.
    """
    workspace_path = os.path.abspath(args.workspace)
    if not os.path.isdir(workspace_path):
        logger.error(f"Workspace not found: {workspace_path}")
        return 1

    # Load workspace meta
    ws_file = os.path.join(workspace_path, "workspace.json")
    if not os.path.exists(ws_file):
        logger.error(f"workspace.json not found in {workspace_path}")
        return 1

    with open(ws_file, encoding="utf-8") as f:
        ws_meta = json.load(f)

    # Find version file
    version_file = _find_version_file(workspace_path, args.version_id)
    if version_file is None:
        logger.error("No version files found in workspace")
        return 1

    logger.info(f"Loading version: {os.path.basename(version_file)}")
    with open(version_file, encoding="utf-8") as f:
        version_data = json.load(f)

    image_items = version_data.get("image_items", [])
    annotations = version_data.get("annotations", {})

    if not image_items:
        logger.warning("No images listed in this workspace version")
        return 0

    # Load detector
    logger.info("Initialising OCR detector...")
    try:
        from modules.core.ocr.detector import TextDetector
        if args.profile:
            from modules.config import ConfigManager
            ConfigManager.instance().set_current_profile(args.profile)
        detector = TextDetector()
    except Exception as exc:
        logger.error(f"Failed to initialise detector: {exc}")
        return 1

    # Run detection
    success_count = fail_count = skip_count = 0
    total = len(image_items)

    for i, (key, full_path) in enumerate(image_items, 1):
        if not args.overwrite and annotations.get(key):
            skip_count += 1
            continue

        if not os.path.exists(full_path):
            logger.warning(f"[{i}/{total}] Image not found, skipping: {full_path}")
            fail_count += 1
            continue

        logger.info(f"[{i}/{total}] Detecting: {key}")
        try:
            results = detector.detect(full_path)
            annotations[key] = [
                {
                    "points":        r["points"],
                    "transcription": r.get("transcription", ""),
                    "difficult":     False,
                    "shape":         "Polygon",
                }
                for r in results
                if isinstance(r.get("points"), list)
            ]
            success_count += 1
        except Exception as exc:
            logger.error(f"  Detection failed: {exc}")
            fail_count += 1

    # Save updated version
    version_data["annotations"] = annotations
    with open(version_file, "w", encoding="utf-8") as f:
        json.dump(version_data, f, ensure_ascii=False, indent=2)

    logger.info(
        f"Detection complete — "
        f"processed: {success_count}, skipped: {skip_count}, failed: {fail_count}"
    )
    return 0 if fail_count == 0 else 1


def _cmd_export(args) -> int:
    """
    Export annotations to PaddleOCR detection label format:

        output/
          images/          ← copied image files
          Label.txt        ← one line per image: path\tJSON_annotations
          fileState.txt    ← one line per image: path\t1
    """
    workspace_path = os.path.abspath(args.workspace)
    output_dir = os.path.abspath(args.output)

    if not os.path.isdir(workspace_path):
        logger.error(f"Workspace not found: {workspace_path}")
        return 1

    version_file = _find_version_file(workspace_path, args.version_id)
    if version_file is None:
        logger.error("No version files found in workspace")
        return 1

    with open(version_file, encoding="utf-8") as f:
        version_data = json.load(f)

    image_items  = version_data.get("image_items", [])
    annotations  = version_data.get("annotations", {})

    # Only export images that have annotations
    to_export = [
        (key, full) for key, full in image_items
        if annotations.get(key)
    ]

    if not to_export:
        logger.warning("No annotated images found — nothing to export")
        return 0

    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    import shutil
    label_lines      = []
    filestate_lines  = []
    success = fail = 0

    for key, full_path in to_export:
        if not os.path.exists(full_path):
            logger.warning(f"Image not found, skipping: {full_path}")
            fail += 1
            continue

        # Copy image
        dst = os.path.join(images_dir, key)
        shutil.copy2(full_path, dst)

        # Build PaddleOCR annotation list
        anns = annotations[key]
        ppocr_anns = []
        for ann in anns:
            pts = ann.get("points", [])
            if len(pts) < 4:
                continue
            ppocr_anns.append({
                "transcription": ann.get("transcription", ""),
                "points":        [[int(x), int(y)] for x, y in pts],
                "difficult":     ann.get("difficult", False),
            })

        rel_path = os.path.join("images", key).replace("\\", "/")
        label_lines.append(f"{rel_path}\t{json.dumps(ppocr_anns, ensure_ascii=False)}")
        filestate_lines.append(f"{rel_path}\t1")
        success += 1

    # Write label files
    with open(os.path.join(output_dir, "Label.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(label_lines) + "\n")

    with open(os.path.join(output_dir, "fileState.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(filestate_lines) + "\n")

    logger.info(
        f"Export complete — {success} images exported to {output_dir}"
        + (f", {fail} failed" if fail else "")
    )
    return 0 if fail == 0 else 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_version_file(workspace_path: str, version_id: str | None) -> str | None:
    """Return path to the requested (or latest) version JSON file."""
    versions_dir = os.path.join(workspace_path, "versions")
    if not os.path.isdir(versions_dir):
        return None

    files = sorted(
        [f for f in os.listdir(versions_dir) if f.endswith(".json")],
        reverse=True,  # lexicographic desc — latest version last alphabetically
    )
    if not files:
        return None

    if version_id:
        # Match by filename prefix or id field inside JSON
        for fn in files:
            if version_id in fn:
                return os.path.join(versions_dir, fn)
        logger.warning(f"Version '{version_id}' not found, using latest")

    return os.path.join(versions_dir, files[0])


def _setup_logging(level: str) -> None:
    """Configure CLI logging.

    Emits JSON lines when the ``LOG_FORMAT`` environment variable is set to
    ``"json"`` (e.g. inside a Docker headless container); otherwise uses a
    human-readable format.

    Args:
        level: Log level string (``"DEBUG"``, ``"INFO"``, ``"WARNING"``, ``"ERROR"``).
    """
    use_json = os.environ.get("LOG_FORMAT", "").lower() == "json"

    if use_json:
        import json as _json
        import datetime

        class _JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                obj = {
                    "ts":     datetime.datetime.utcfromtimestamp(record.created).isoformat() + "Z",
                    "level":  record.levelname,
                    "logger": record.name,
                    "msg":    record.getMessage(),
                }
                if record.exc_info:
                    obj["exc"] = self.formatException(record.exc_info)
                return _json.dumps(obj, ensure_ascii=False)

        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logging.root.setLevel(getattr(logging, level, logging.INFO))
        logging.root.addHandler(handler)
    else:
        logging.basicConfig(
            level=getattr(logging, level, logging.INFO),
            format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )


# ---------------------------------------------------------------------------
# __main__ support: python -m modules.cli
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main() or 0)
