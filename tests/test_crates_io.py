from datetime import datetime, timezone

from rust_crate_count.crates_io import DeletedCrate, YearlyCrateCount, parse_timestamp, yearly_counts


def utc(year, month=1, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_parse_timestamp_accepts_dump_formats():
    assert parse_timestamp("2026-06-02T02:00:24.375042029Z").year == 2026
    assert parse_timestamp("2023-05-01 12:06:24.629411+00").year == 2023


def test_yearly_counts_include_deleted_crates_in_new_counts():
    rows = yearly_counts(
        current_created=[utc(2020, 2, 1), utc(2021, 3, 1)],
        deleted_crates=[
            DeletedCrate(created_at=utc(2020, 5, 1), deleted_at=utc(2021, 6, 1)),
            DeletedCrate(created_at=utc(2021, 7, 1), deleted_at=utc(2021, 8, 1)),
        ],
        dump_timestamp=utc(2022, 6, 1),
    )

    assert rows == [
        YearlyCrateCount(2020, 0, 2, 1, 1, False),
        YearlyCrateCount(2021, 2, 2, 1, 1, False),
        YearlyCrateCount(2022, 2, 0, 0, 0, True),
    ]


def test_deleted_crates_are_not_active_after_deleted_at():
    rows = yearly_counts(
        current_created=[],
        deleted_crates=[DeletedCrate(created_at=utc(2020, 5, 1), deleted_at=utc(2020, 12, 1))],
        dump_timestamp=utc(2022, 6, 1),
    )

    assert rows[0].active_at_jan1 == 0
    assert rows[1].active_at_jan1 == 0
