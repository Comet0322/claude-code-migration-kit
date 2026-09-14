"""Tests for SpcAnalyzer. See boogie-sdk-api.md (this skill's library doc) section 5.3
(deviceio).

Standard X-bar 3-sigma control limits, with the following conventions
invented and pinned down here (the implementer must match them exactly):

- **`center`** = arithmetic mean of all samples added so far.
- **Spread = population standard deviation** (divide by N, *not* N-1) of all
  samples added so far. `upper`/`lower` = `center ± 3 * population_stdev`.
- **`is_out_of_control()`** evaluates the *most recently added* sample
  against control limits computed from **all samples added so far,
  including that most recent sample itself** (not limits computed from
  prior samples only — that is a defensible alternative, but this fake
  picks "include the current sample" and documents it here).
- A sample exactly equal to `upper` or `lower` counts as **in control**
  (boundary is inclusive of the control limits; only strictly outside
  counts as out of control).
- **Zero samples**: both `control_limits()` and `is_out_of_control()` raise
  `ValidationError` — there is no meaningful center/spread with no data.
- **One sample**: `control_limits()` returns a degenerate result where
  `center == upper == lower == that sample's value` (population stdev of a
  single value is 0). `is_out_of_control()` is `False` in this case since
  the single sample sits exactly on (not outside) its own limits.
"""

from __future__ import annotations

import pytest

from boogie_sdk.core.errors import ValidationError
from boogie_sdk.deviceio.spc_analyzer import ControlLimits, SpcAnalyzer


@pytest.fixture
def analyzer() -> SpcAnalyzer:
    return SpcAnalyzer()


# -- zero / one sample edge cases ---------------------------------------------


def test_control_limits_with_zero_samples_raises_validation_error(
    analyzer: SpcAnalyzer,
) -> None:
    with pytest.raises(ValidationError):
        analyzer.control_limits()


def test_is_out_of_control_with_zero_samples_raises_validation_error(
    analyzer: SpcAnalyzer,
) -> None:
    with pytest.raises(ValidationError):
        analyzer.is_out_of_control()


def test_control_limits_with_one_sample_is_degenerate(analyzer: SpcAnalyzer) -> None:
    analyzer.add_sample(7.0)

    limits = analyzer.control_limits()

    assert isinstance(limits, ControlLimits)
    assert limits.center == pytest.approx(7.0)
    assert limits.upper == pytest.approx(7.0)
    assert limits.lower == pytest.approx(7.0)


def test_is_out_of_control_with_one_sample_is_false(analyzer: SpcAnalyzer) -> None:
    analyzer.add_sample(7.0)
    assert analyzer.is_out_of_control() is False


# -- control_limits: known dataset --------------------------------------------


def test_control_limits_for_classic_population_stdev_dataset(
    analyzer: SpcAnalyzer,
) -> None:
    # Dataset [2, 4, 4, 4, 5, 5, 7, 9]: mean = 5, population stdev = 2
    # (a well-known textbook example that gives exact integers).
    for value in (2, 4, 4, 4, 5, 5, 7, 9):
        analyzer.add_sample(value)

    limits = analyzer.control_limits()

    assert limits.center == pytest.approx(5.0)
    assert limits.upper == pytest.approx(11.0)
    assert limits.lower == pytest.approx(-1.0)


def test_control_limits_update_as_samples_are_added(analyzer: SpcAnalyzer) -> None:
    analyzer.add_sample(10.0)
    analyzer.add_sample(10.0)
    first_limits = analyzer.control_limits()
    assert first_limits.center == pytest.approx(10.0)
    assert first_limits.upper == pytest.approx(10.0)
    assert first_limits.lower == pytest.approx(10.0)

    analyzer.add_sample(20.0)
    second_limits = analyzer.control_limits()
    # Adding a different value changes the center and widens the spread.
    assert second_limits.center == pytest.approx(40.0 / 3.0)
    assert second_limits.upper != first_limits.upper


# -- is_out_of_control ---------------------------------------------------------


def test_is_out_of_control_false_for_identical_samples(analyzer: SpcAnalyzer) -> None:
    for _ in range(5):
        analyzer.add_sample(100.0)

    assert analyzer.is_out_of_control() is False


def test_is_out_of_control_true_for_clear_outlier_among_stable_baseline(
    analyzer: SpcAnalyzer,
) -> None:
    # Ten identical baseline samples, then one outlier. With population
    # stdev computed over all 11 samples (including the outlier itself),
    # this specific baseline size/outlier combination is large enough that
    # the outlier still falls outside its own 3-sigma limits — verified by
    # hand below (mean ~= 104.545, stdev ~= 14.374, upper ~= 147.667).
    for _ in range(10):
        analyzer.add_sample(100.0)
    analyzer.add_sample(150.0)

    limits = analyzer.control_limits()
    assert limits.center == pytest.approx(104.545454545, rel=1e-6)
    assert limits.upper == pytest.approx(147.667364, rel=1e-5)

    assert analyzer.is_out_of_control() is True


def test_is_out_of_control_only_reflects_most_recently_added_sample(
    analyzer: SpcAnalyzer,
) -> None:
    # After adding the outlier, add one more in-baseline sample: the
    # analyzer should now report False again, because the *latest* sample
    # (back to baseline) is what's being judged, not the earlier outlier.
    for _ in range(10):
        analyzer.add_sample(100.0)
    analyzer.add_sample(150.0)
    assert analyzer.is_out_of_control() is True

    analyzer.add_sample(100.0)
    assert analyzer.is_out_of_control() is False
