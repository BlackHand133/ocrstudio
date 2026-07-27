#!/usr/bin/env python3
"""
Thai OCR Text Quality Metrics

Scores Thai transcriptions for the two failure modes that matter on this
corpus, and audits a workspace's saved annotations. Needs no OCR engine — it
reads the JSON the app already wrote, so it runs anywhere.

    python scripts/thai_quality.py                       # every workspace
    python scripts/thai_quality.py --workspace dataset   # just one
    python scripts/thai_quality.py --samples 20          # show more examples

The metrics
-----------
orphan_marks
    A Thai vowel or tone mark whose preceding character is not Thai. It has no
    base to attach to, so it renders as a floating diacritic. This is the
    headline number: it is unambiguous.

latin_next_to_thai
    A Latin letter directly beside a Thai character. High values suggest the
    recognizer is emitting Latin lookalikes for Thai consonants (th->n, s->s,
    o->o, ph->w, ch->D). Treat it as a *weak* signal: Thai drug-bag text
    legitimately mixes in English drug names, and those count here too.

thai_chars
    Absolute count of Thai characters. Always read this next to the rates. A
    model that outputs no Thai at all scores a perfect 0.00 on both rates above
    while being completely broken — the denominator vanished, not the errors.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

def force_utf8_output():
    """Print Thai on a Windows console without UnicodeEncodeError.

    reconfigure() rather than wrapping sys.stdout: wrapping is not idempotent,
    and this module gets imported by other scripts that have already done it —
    the second wrapper then fails looking for a .buffer the first one hides.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # already a plain stream, or redirected; nothing to do


force_utf8_output()

REPO_ROOT = Path(__file__).resolve().parent.parent

# Thai combining marks: above/below vowels (U+0E34-U+0E3A), MAI HAN AKAT
# (U+0E31), and the tone/diacritic block (U+0E47-U+0E4E).
MARKS = {0x0E31} | set(range(0x0E34, 0x0E3B)) | set(range(0x0E47, 0x0E4F))
LATIN = re.compile(r"[A-Za-z]")
DOTTED_CIRCLE = "◌"


def is_thai(ch):
    """True for anything in the Thai Unicode block."""
    return "฀" <= ch <= "๿"


def find_orphan_marks(text):
    """Return [(index, mark)] for marks with no Thai character in front."""
    out = []
    for i, ch in enumerate(text):
        if ord(ch) in MARKS:
            prev = text[i - 1] if i > 0 else ""
            if not prev or not is_thai(prev):
                out.append((i, ch))
    return out


def score(texts):
    """Aggregate quality counters over a list of transcriptions."""
    stats = {
        "lines": 0,
        "chars": 0,
        "thai_chars": 0,
        "latin_chars": 0,
        "marks": 0,
        "orphan_marks": 0,
        "latin_next_to_thai": 0,
        "dotted_circles": 0,
    }
    for t in texts:
        if not t:
            continue
        stats["lines"] += 1
        stats["chars"] += len(t)
        stats["dotted_circles"] += t.count(DOTTED_CIRCLE)
        for ch in t:
            if is_thai(ch):
                stats["thai_chars"] += 1
            elif LATIN.match(ch):
                stats["latin_chars"] += 1
            if ord(ch) in MARKS:
                stats["marks"] += 1
        stats["orphan_marks"] += len(find_orphan_marks(t))
        for m in LATIN.finditer(t):
            i = m.start()
            prev = t[i - 1] if i > 0 else ""
            nxt = t[i + 1] if i + 1 < len(t) else ""
            if is_thai(prev) or is_thai(nxt):
                stats["latin_next_to_thai"] += 1
    return stats


def per_1000(stats, key):
    """Rate per 1000 characters, or None when there is nothing to divide by."""
    return (stats[key] / stats["chars"] * 1000) if stats["chars"] else None


def format_row(label, stats, width=13):
    orphan = per_1000(stats, "orphan_marks")
    latin = per_1000(stats, "latin_next_to_thai")
    fmt = lambda v: f"{v:7.2f}" if v is not None else "      -"  # noqa: E731
    return (
        f"{label:<{width}}{stats['lines']:>7}{stats['chars']:>8}"
        f"{stats['thai_chars']:>7}{stats['orphan_marks']:>8}"
        f"{fmt(orphan)}{stats['latin_next_to_thai']:>7}{fmt(latin)}"
    )


HEADER = (
    f"{'run':<13}{'lines':>7}{'chars':>8}{'thai':>7}"
    f"{'orphan':>8}{'/1k':>7}{'lat~th':>7}{'/1k':>7}"
)


def warn_if_no_thai(label, stats):
    """A zero rate means nothing if the model stopped producing Thai."""
    if stats["lines"] and stats["thai_chars"] == 0:
        print(
            f"  !! {label}: 0 Thai characters in {stats['lines']} lines. Its 0.00"
            f" rates are meaningless — it is not reading Thai at all."
        )
        return True
    return False


def iter_versions(workspace_dir):
    """Yield version JSON paths, skipping backups."""
    for path in sorted(workspace_dir.glob("v*.json")):
        if "backup" in path.name:
            continue
        yield path


def audit(workspaces_root, only=None, n_samples=10):
    roots = [d for d in sorted(workspaces_root.iterdir()) if d.is_dir()]
    if only:
        roots = [d for d in roots if d.name == only]
    if not roots:
        print(f"No workspaces found under {workspaces_root}")
        return 1

    overall = Counter()
    samples = []
    per_ws = {}

    for ws in roots:
        texts = []
        for path in iter_versions(ws):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  skipping {path.name}: {exc}")
                continue
            for key, anns in (data.get("annotations") or {}).items():
                for a in anns or []:
                    t = (a.get("transcription") or "").strip()
                    if not t:
                        continue
                    texts.append(t)
                    if find_orphan_marks(t) and len(samples) < n_samples:
                        marks = "".join(c for _, c in find_orphan_marks(t))
                        samples.append((ws.name, key, t[:48], marks))
        stats = score(texts)
        per_ws[ws.name] = stats
        for k, v in stats.items():
            overall[k] += v

    print("=" * len(HEADER))
    print("SAVED ANNOTATION QUALITY")
    print("=" * len(HEADER))
    print(HEADER)
    print("-" * len(HEADER))
    for name, stats in per_ws.items():
        if stats["lines"]:
            print(format_row(name[:12], stats))
    print("-" * len(HEADER))
    print(format_row("TOTAL", dict(overall)))

    for name, stats in per_ws.items():
        warn_if_no_thai(name, stats)

    if overall["dotted_circles"]:
        print(f"\n  {overall['dotted_circles']} dotted circle(s) U+25CC — "
              f"a certain sign of an orphan mark reaching the UI.")

    if samples:
        print("\nlines containing an orphan mark:")
        for ws, key, text, marks in samples:
            print(f"  [{ws}/{key}] {text!r}  orphan={marks!r}")

        print("\nwhat precedes each orphan mark tells you the cause:")
        counts = Counter()
        for ws in roots:
            for path in iter_versions(ws):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                for anns in (data.get("annotations") or {}).values():
                    for a in anns or []:
                        t = a.get("transcription") or ""
                        for i, _ in find_orphan_marks(t):
                            prev = t[i - 1] if i > 0 else ""
                            if not prev:
                                counts["<start of line>"] += 1
                            elif LATIN.match(prev):
                                counts[f"Latin {prev!r}"] += 1
                            else:
                                counts[repr(prev)] += 1
        total = sum(counts.values())
        latin_share = sum(v for k, v in counts.items() if k.startswith("Latin"))
        for what, n in counts.most_common(8):
            print(f"    {what:<20} {n}")
        if total:
            pct = latin_share / total * 100
            print(f"\n  {latin_share}/{total} ({pct:.0f}%) follow a Latin letter.")
            if pct > 50:
                print("  => The marks are not being dropped; their Thai base is being")
                print("     recognised as a Latin lookalike. Fix the recognition model")
                print("     or its dictionary, not the detection thresholds.")
    else:
        print("\nNo orphan marks found.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspaces", default=str(REPO_ROOT / "workspaces"),
                    help="workspaces root (default: ./workspaces)")
    ap.add_argument("--workspace", help="audit only this workspace")
    ap.add_argument("--samples", type=int, default=10,
                    help="how many offending lines to print (default: 10)")
    args = ap.parse_args()

    root = Path(args.workspaces)
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 1
    return audit(root, only=args.workspace, n_samples=args.samples)


if __name__ == "__main__":
    sys.exit(main())
