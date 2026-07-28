#!/usr/bin/env python3
"""
Collapse near-duplicate transcriptions onto one canonical string

The same printed text photographed many times comes back spelled several ways —
'DEGAS Simethicone 80 mg.', 'DEGAS Sinalhicone 80 mg.', 'EGAS Simethicone
80 mg.', 'DEGAS 80 mg. Simethicone'. Each is a plausible reading; together they
teach a model that one image has several right answers, which is worse for
training than leaving the text obviously broken.

    # see what would change
    python scripts/normalize_labels.py --version v6 \
        --match "GAS.*imethicone|GAS.*80 ?mg" --to "DEGAS Simethicone 80 mg."

    # write it to a new version
    python scripts/normalize_labels.py --version v6 \
        --match "..." --to "..." --write

Reports by default. --write always creates a new version file; the source is
never modified, and only the transcription field is touched — geometry, shape
and '###' ignore-markers are left alone.

Check the matches in the report before writing. A regex that is too loose will
quietly flatten distinct labels into one, which is the same disease this is
meant to cure.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from thai_quality import force_utf8_output  # noqa: E402
from workspace_versions import next_version_path, stamp_version  # noqa: E402

force_utf8_output()

IGNORE_MARKER = "###"




def main():
    ap = argparse.ArgumentParser(
        description="Collapse near-duplicate transcriptions onto one string",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--workspace", default="dataset")
    ap.add_argument("--version", required=True, help="version file to read")
    ap.add_argument("--match", required=True,
                    help="regex; boxes whose transcription matches are rewritten")
    ap.add_argument("--to", required=True, help="the canonical transcription")
    ap.add_argument("--images", nargs="+",
                    help="restrict to these image keys (default: all)")
    ap.add_argument("--write", action="store_true",
                    help="save to a new version file (default: report only)")
    args = ap.parse_args()

    ws = REPO_ROOT / "workspaces" / args.workspace
    version_file = ws / f"{args.version}.json"
    if not version_file.exists():
        print(f"No such version: {version_file}")
        return 1

    try:
        pattern = re.compile(args.match)
    except re.error as exc:
        print(f"Bad regex: {exc}")
        return 1

    data = json.loads(version_file.read_text(encoding="utf-8"))
    annotations = data.get("annotations") or {}
    keys = args.images or sorted(annotations)

    hits, already = [], 0
    for key in keys:
        for i, ann in enumerate(annotations.get(key) or []):
            text = (ann.get("transcription") or "").strip()
            if not text or text == IGNORE_MARKER:
                continue
            if not pattern.search(text):
                continue
            if text == args.to:
                already += 1
                continue
            hits.append((key, i, text, ann))

    print(f"pattern: {args.match!r}")
    print(f"canonical: {args.to!r}\n")
    if already:
        print(f"{already} box(es) already match the canonical form\n")
    if not hits:
        print("Nothing to rewrite.")
        return 0

    by_text = {}
    for key, i, text, _ in hits:
        by_text.setdefault(text, []).append(f"{key}#{i}")
    print(f"{len(hits)} box(es) would be rewritten:")
    for text, where in sorted(by_text.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(where):2}x  {text!r}")
        print(f"       {', '.join(where)}")

    if not args.write:
        print("\nReport only. Re-run with --write to save to a new version.")
        return 0

    for _, _, _, ann in hits:
        ann["transcription"] = args.to
        ann["normalized"] = True

    out = next_version_path(ws)
    stamp_version(
        data, args.version,
        f"{args.version} with {len(hits)} label(s) normalized to "
        f"{args.to!r} (scripts/normalize_labels.py)",
        normalized_boxes=len(hits),
    )
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nWrote {out.name}. {version_file.name} is unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
