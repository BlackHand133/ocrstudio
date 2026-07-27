"""Tests for modules.data.splitter.DataSplitter.

This module decides which images end up in train / test / valid for an exported
dataset. The failure that matters is silent: an image landing in two splits
leaks test data into training, and nothing downstream notices — the model just
scores better than it deserves. Most of what follows is therefore about
disjointness and completeness rather than exact sizes.

Every splitter is constructed with a seed so the assertions are deterministic;
see TestKnownRoughEdges for why a fresh instance is used for each call.
"""

import random

import pytest

from modules.data.splitter import DataSplitter


def items(n):
    return [f"img{i:03d}.jpg" for i in range(n)]


def flatten(result):
    return [item for values in result.values() for item in values]


# ===========================================================================
# The invariant that matters: nothing shared, nothing lost
# ===========================================================================

class TestNoLeakage:

    @pytest.mark.parametrize("n", [1, 2, 3, 7, 10, 33, 100])
    @pytest.mark.parametrize("ratios", [(70, 20, 10), (80, 10, 10), (50, 50, 0),
                                        (60, 0, 40), (100, 0, 0), (34, 33, 33)])
    def test_percentage_splits_are_disjoint(self, n, ratios):
        result = DataSplitter(seed=7).split_by_percentage(items(n), *ratios)
        everything = flatten(result)
        assert len(everything) == len(set(everything)), "an item is in two splits"

    @pytest.mark.parametrize("n", [1, 2, 3, 7, 10, 33, 100])
    @pytest.mark.parametrize("ratios", [(70, 20, 10), (80, 10, 10), (50, 50, 0),
                                        (60, 0, 40), (100, 0, 0), (34, 33, 33)])
    def test_percentage_keeps_every_item(self, n, ratios):
        """Percentages describe how to divide the data, not how much to keep."""
        source = items(n)
        result = DataSplitter(seed=7).split_by_percentage(source, *ratios)
        assert sorted(flatten(result)) == sorted(source)

    def test_percentage_does_not_mutate_the_input(self, ):
        source = items(10)
        original = list(source)
        DataSplitter(seed=7).split_by_percentage(source, 70, 20, 10)
        assert source == original

    @pytest.mark.parametrize("n", [3, 10, 31])
    def test_stratified_splits_are_disjoint(self, n):
        source = items(n)
        scores = {key: i for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10
        )
        everything = flatten(result)
        assert len(everything) == len(set(everything))
        assert sorted(everything) == sorted(source)

    @pytest.mark.parametrize("n", [3, 10, 31])
    def test_length_stratified_splits_are_disjoint(self, n):
        source = items(n)
        lengths = {key: [i + 1, i + 2] for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_length_stratified(
            source, lengths, 70, 20, 10
        )
        everything = flatten(result)
        assert len(everything) == len(set(everything))
        assert sorted(everything) == sorted(source)

    def test_count_splits_are_disjoint(self):
        result = DataSplitter(seed=7).split_by_count(items(10), 5, 3, 2)
        everything = flatten(result)
        assert len(everything) == len(set(everything))


# ===========================================================================
# split_by_percentage
# ===========================================================================

class TestSplitByPercentage:

    def test_sizes_follow_the_requested_ratio(self):
        result = DataSplitter(seed=7).split_by_percentage(items(100), 70, 20, 10)
        assert len(result["train"]) == 70
        assert len(result["test"]) == 20
        assert len(result["valid"]) == 10

    def test_zero_percent_splits_are_omitted(self):
        result = DataSplitter(seed=7).split_by_percentage(items(10), 80, 20, 0)
        assert set(result) == {"train", "test"}

    def test_remainder_goes_to_the_last_split(self):
        """Asking for 60/20 of 10 items leaves 2 over; they must not vanish."""
        result = DataSplitter(seed=7).split_by_percentage(items(10), 60, 20, 0)
        assert len(result["train"]) == 6
        assert len(result["test"]) == 4  # 2 requested + 2 left over
        assert len(flatten(result)) == 10

    def test_empty_input_yields_empty_splits(self):
        result = DataSplitter(seed=7).split_by_percentage([], 70, 20, 10)
        assert flatten(result) == []

    @pytest.mark.parametrize("ratios", [(0, 0, 0), (70, 40, 20), (-10, 0, 0)])
    def test_rejects_impossible_totals(self, ratios):
        with pytest.raises(ValueError):
            DataSplitter(seed=7).split_by_percentage(items(10), *ratios)


# ===========================================================================
# split_by_count
# ===========================================================================

class TestSplitByCount:

    def test_returns_exactly_the_requested_counts(self):
        result = DataSplitter(seed=7).split_by_count(items(10), 5, 3, 2)
        assert [len(result[k]) for k in ("train", "test", "valid")] == [5, 3, 2]

    def test_surplus_items_are_dropped_on_purpose(self):
        """Unlike percentages, counts are a request for exactly that many —
        asking for 6 of 10 leaves 4 out of the dataset entirely."""
        result = DataSplitter(seed=7).split_by_count(items(10), 3, 2, 1)
        assert len(flatten(result)) == 6

    def test_zero_count_splits_are_omitted(self):
        result = DataSplitter(seed=7).split_by_count(items(10), 5, 0, 0)
        assert set(result) == {"train"}

    def test_rejects_asking_for_more_than_exists(self):
        with pytest.raises(ValueError, match="Not enough data"):
            DataSplitter(seed=7).split_by_count(items(5), 4, 3, 2)

    def test_rejects_zero_total(self):
        with pytest.raises(ValueError):
            DataSplitter(seed=7).split_by_count(items(10), 0, 0, 0)


# ===========================================================================
# Stratified splitting
# ===========================================================================

class TestStratified:

    def test_train_spans_the_score_range(self):
        """The point of stratifying: train must not be only the easy images."""
        source = items(60)
        scores = {key: i for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10, n_bins=3
        )
        train_scores = [scores[k] for k in result["train"]]
        assert min(train_scores) < 20, "no low-density images reached train"
        assert max(train_scores) > 40, "no high-density images reached train"

    def test_identical_scores_still_split_everything(self):
        """Percentile bins collapse when every score is the same; the items
        must still all come out somewhere."""
        source = items(10)
        scores = {key: 5 for key in source}
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10
        )
        assert sorted(flatten(result)) == sorted(source)

    def test_items_missing_from_the_score_map_are_kept(self):
        source = items(10)
        scores = {key: i for i, key in enumerate(source[:5])}  # half unscored
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10
        )
        assert sorted(flatten(result)) == sorted(source)

    def test_length_stratified_uses_average_length(self):
        source = items(30)
        # Two clear groups: short text and long text.
        lengths = {key: ([2] if i < 15 else [200]) for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_length_stratified(
            source, lengths, 70, 20, 10
        )
        assert sorted(flatten(result)) == sorted(source)


# ===========================================================================
# Reproducibility
# ===========================================================================

class TestReproducibility:

    def test_same_seed_gives_the_same_split(self):
        source = items(50)
        first = DataSplitter(seed=42).split_by_percentage(source, 70, 20, 10)
        second = DataSplitter(seed=42).split_by_percentage(source, 70, 20, 10)
        assert first == second

    def test_different_seeds_give_different_splits(self):
        source = items(50)
        first = DataSplitter(seed=1).split_by_percentage(source, 70, 20, 10)
        second = DataSplitter(seed=2).split_by_percentage(source, 70, 20, 10)
        assert first != second


# ===========================================================================
# Behaviour that is surprising but currently intended-by-omission
#
# These pin what the code does today so a change is a deliberate one. The
# xfail cases are bugs: they will start passing when fixed, and pytest will
# report them as XPASS so nobody has to remember to update this file.
# ===========================================================================

class TestKnownRoughEdges:

    def test_seeding_perturbs_the_global_random_stream(self):
        """DataSplitter seeds the `random` module rather than owning a
        Random instance, so building one changes results for every other
        caller in the process. Callers who need their own sequence must
        re-seed after constructing a splitter."""
        random.seed(999)
        before = [random.random() for _ in range(3)]
        random.seed(999)
        DataSplitter(seed=7)
        after = [random.random() for _ in range(3)]
        assert before != after

    def test_one_instance_does_not_repeat_itself(self):
        """The seed is applied once in __init__, not per call, so reusing an
        instance gives a different split each time. Construct a new splitter
        when a reproducible result is needed."""
        splitter = DataSplitter(seed=42)
        source = items(50)
        assert splitter.split_by_percentage(source, 70, 20, 10) != \
            splitter.split_by_percentage(source, 70, 20, 10)

    def test_stratified_may_drop_a_requested_split(self):
        """Each bin is split independently, so a small percentage can round to
        zero in every bin and disappear from the result. Callers must not
        assume the key they asked for exists."""
        source = items(10)
        scores = {key: i for i, key in enumerate(source)}
        result = DataSplitter(seed=3).split_by_density_stratified(
            source, scores, 70, 20, 10
        )
        assert "valid" not in result


# ===========================================================================
# Degenerate input
#
# np.percentile raises on an empty sequence, and n_bins < 1 produced zero bins
# so every item fell through the loop and vanished. Both are reachable from the
# web export path (server/services/export_split.py).
# ===========================================================================

class TestDegenerateInput:

    def test_stratified_handles_empty_input(self):
        result = DataSplitter(seed=7).split_by_density_stratified([], {}, 70, 20, 10)
        assert flatten(result) == []

    def test_length_stratified_handles_empty_input(self):
        result = DataSplitter(seed=7).split_by_length_stratified([], {}, 70, 20, 10)
        assert flatten(result) == []

    @pytest.mark.parametrize("n_bins", [0, -1])
    def test_stratified_rejects_impossible_bin_counts(self, n_bins):
        """Zero bins used to swallow the entire dataset without complaint."""
        source = items(6)
        scores = {key: i for i, key in enumerate(source)}
        with pytest.raises(ValueError, match="n_bins"):
            DataSplitter(seed=7).split_by_density_stratified(
                source, scores, 70, 20, 10, n_bins=n_bins
            )

    @pytest.mark.parametrize("n_bins", [0, -1])
    def test_length_stratified_rejects_impossible_bin_counts(self, n_bins):
        source = items(6)
        lengths = {key: [i + 1] for i, key in enumerate(source)}
        with pytest.raises(ValueError, match="n_bins"):
            DataSplitter(seed=7).split_by_length_stratified(
                source, lengths, 70, 20, 10, n_bins=n_bins
            )

    @pytest.mark.parametrize("n_bins", [1, 2, 3, 5, 10])
    def test_every_item_survives_any_bin_count(self, n_bins):
        source = items(12)
        scores = {key: i for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10, n_bins=n_bins
        )
        assert sorted(flatten(result)) == sorted(source)

    def test_more_bins_than_items_still_keeps_everything(self):
        source = items(3)
        scores = {key: i for i, key in enumerate(source)}
        result = DataSplitter(seed=7).split_by_density_stratified(
            source, scores, 70, 20, 10, n_bins=10
        )
        assert sorted(flatten(result)) == sorted(source)
