"""Dataset splitting for export — percentage (default), fixed count, or
stratified by a score. Thin wrapper over the Qt-free DataSplitter."""

from __future__ import annotations

from typing import Dict, List, Optional

from modules.data.splitter import DataSplitter


def _split(
    items: List,
    splits: Dict[str, float],
    seed: Optional[int],
    *,
    mode: str = "percentage",
    counts: Optional[Dict[str, int]] = None,
    stratify_scores: Optional[Dict] = None,
    n_bins: int = 3,
) -> Dict[str, List]:
    sp = DataSplitter(seed=seed)
    if mode == "count" and counts:
        return sp.split_by_count(
            items,
            int(counts.get("train", 0)),
            int(counts.get("test", 0)),
            int(counts.get("valid", 0)),
        )
    if mode == "stratified" and stratify_scores:
        return sp.split_by_density_stratified(
            items,
            stratify_scores,
            splits.get("train", 0),
            splits.get("test", 0),
            splits.get("valid", 0),
            n_bins=n_bins,
        )
    return sp.split_by_percentage(
        items,
        train_pct=splits.get("train", 0),
        test_pct=splits.get("test", 0),
        valid_pct=splits.get("valid", 0),
    )
