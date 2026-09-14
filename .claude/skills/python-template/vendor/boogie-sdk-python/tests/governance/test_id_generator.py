"""Tests for IdGenerator. See boogie-sdk-api.md (this skill's library doc) section 5.5
(governance).

The design doc only documents `next_id() -> int` with a "Snowflake-style"
comment and no bit-layout or formatting spec. Since there is no real
distributed-id service behind this fake and no format is mandated, this
test file deliberately does NOT assert on bit-width, timestamp encoding,
or any particular numeric range. It only pins down the properties a
Snowflake-style generator must have to be useful as an id source:

- every returned id is a non-negative `int`.
- many calls in a row never collide (uniqueness), checked across a
  moderately large batch (1000 calls) to catch a naive `random.random()`
  or a poorly-seeded counter without making the test slow.
- ids are non-decreasing across successive calls (`next_id() >=
  previous next_id()`), which is the one ordering guarantee "Snowflake-
  style" implies, without assuming strict monotonic increase (a real
  Snowflake id can repeat within the same clock tick and only strictly
  increases across ticks).
"""

from __future__ import annotations

import pytest

from boogie_sdk.governance.id_generator import IdGenerator


@pytest.fixture
def generator() -> IdGenerator:
    return IdGenerator()


def test_next_id_returns_an_int(generator: IdGenerator) -> None:
    assert isinstance(generator.next_id(), int)


def test_next_id_returns_non_negative_value(generator: IdGenerator) -> None:
    assert generator.next_id() >= 0


def test_many_calls_return_distinct_ids(generator: IdGenerator) -> None:
    ids = [generator.next_id() for _ in range(1000)]
    assert len(set(ids)) == len(ids)


def test_many_calls_are_all_non_negative(generator: IdGenerator) -> None:
    ids = [generator.next_id() for _ in range(1000)]
    assert all(value >= 0 for value in ids)


def test_ids_are_non_decreasing_across_successive_calls(
    generator: IdGenerator,
) -> None:
    previous = generator.next_id()
    for _ in range(1000):
        current = generator.next_id()
        assert current >= previous
        previous = current


def test_two_separate_generators_do_not_need_to_coordinate(
    generator: IdGenerator,
) -> None:
    # Two independent generator instances are still each internally
    # consistent (own ids stay unique) even though nothing requires them
    # to interleave in any particular order relative to each other.
    other = IdGenerator()

    ids_a = [generator.next_id() for _ in range(50)]
    ids_b = [other.next_id() for _ in range(50)]

    assert len(set(ids_a)) == len(ids_a)
    assert len(set(ids_b)) == len(ids_b)
