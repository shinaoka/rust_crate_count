import io
import json
import tarfile
from datetime import datetime, timezone

from rust_crate_count.crates_io import (
    DeletedCrate,
    DumpData,
    YearlyCrateCount,
    monthly_rolling_counts,
    parse_timestamp,
    read_dump,
    yearly_counts,
)


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


def test_monthly_rolling_counts_use_trailing_12_months():
    dump = DumpData(
        timestamp=utc(2022, 3, 5),
        current_created=[utc(2020, 1, 15), utc(2021, 6, 1)],
        deleted_crates=[],
        releases_by_crate={
            1: [utc(2020, 1, 15), utc(2021, 12, 1)],
            2: [utc(2021, 1, 1)],
        },
    )

    rows = monthly_rolling_counts(dump)

    assert (rows[0].month, rows[-1].month) == (utc(2020, 1, 1), utc(2022, 3, 1))
    assert len(rows) == 27
    by_month = {row.month: row for row in rows}
    assert by_month[utc(2021, 12, 1)].released_last_12m == 2
    assert by_month[utc(2021, 12, 1)].registered == 2
    # the 2021-01-01 release of crate 2 leaves the window at the 2022-01-01 month start
    assert by_month[utc(2022, 1, 1)].released_last_12m == 1
    assert by_month[utc(2022, 3, 1)].released_last_12m == 1


def test_monthly_rolling_counts_count_each_crate_once_per_month():
    dump = DumpData(
        timestamp=utc(2022, 3, 5),
        current_created=[utc(2020, 1, 1)],
        deleted_crates=[],
        releases_by_crate={1: [utc(2021, 5, 1), utc(2021, 6, 1), utc(2021, 7, 1)]},
    )

    rows = {row.month: row for row in monthly_rolling_counts(dump)}

    assert rows[utc(2021, 6, 1)].released_last_12m == 1
    assert rows[utc(2021, 10, 1)].released_last_12m == 1


def test_monthly_rolling_counts_use_earlier_releases_for_past_months():
    # A crate released before and after a month start must count for the earlier month too:
    # the 2024-06-01 release is inside (2024-01-01, 2025-01-01] even though the latest
    # release of the crate is 2026-06-01.
    dump = DumpData(
        timestamp=utc(2026, 7, 1),
        current_created=[utc(2024, 5, 1)],
        deleted_crates=[],
        releases_by_crate={1: [utc(2024, 6, 1), utc(2026, 6, 1)]},
    )

    rows = {row.month: row for row in monthly_rolling_counts(dump)}

    assert rows[utc(2025, 1, 1)].released_last_12m == 1
    assert rows[utc(2025, 7, 1)].released_last_12m == 0
    assert rows[utc(2026, 6, 1)].released_last_12m == 1


def test_monthly_rolling_counts_handle_empty_dump():
    dump = DumpData(
        timestamp=utc(2022, 3, 5),
        current_created=[],
        deleted_crates=[],
        releases_by_crate={},
    )

    assert monthly_rolling_counts(dump) == []


def test_read_dump_keeps_all_releases_of_current_crates(tmp_path):
    dump_path = _write_dump(
        tmp_path / "db-dump.tar.gz",
        timestamp="2026-07-01 00:00:00+00",
        crates=[(1, "2024-05-01 00:00:00+00"), (2, "2026-01-01 00:00:00+00")],
        deleted=[(3, "2020-01-01 00:00:00+00", "2021-01-01 00:00:00+00")],
        versions=[
            (1, "2024-06-01 00:00:00+00"),
            (1, "2026-06-01 00:00:00+00"),
            (2, "2026-06-15 00:00:00+00"),
            (3, "2020-02-01 00:00:00+00"),
        ],
    )

    dump = read_dump(dump_path)
    rows = {row.month: row for row in monthly_rolling_counts(dump)}

    assert sorted(dump.releases_by_crate) == [1, 2]
    assert dump.releases_by_crate[1] == [utc(2024, 6, 1), utc(2026, 6, 1)]
    assert rows[utc(2025, 1, 1)].released_last_12m == 1
    assert rows[utc(2026, 6, 1)].released_last_12m == 1
    assert rows[utc(2026, 7, 1)].released_last_12m == 2
    assert rows[utc(2026, 7, 1)].registered == 2


def _write_dump(path, timestamp, crates, deleted, versions):
    """Write a minimal crates.io-shaped dump with only the columns read_dump needs."""
    root = "2026-07-01-000000"
    files = {
        "metadata.json": json.dumps({"timestamp": timestamp}),
        "data/crates.csv": "created_at,id\n"
        + "".join(f"{created},{crate_id}\n" for crate_id, created in crates),
        "data/deleted_crates.csv": "created_at,deleted_at\n"
        + "".join(f"{created},{deleted_at}\n" for _, created, deleted_at in deleted),
        "data/versions.csv": "bin_names,crate_id,created_at\n"
        + "".join(f"{{}},{crate_id},{created}\n" for crate_id, created in versions),
    }

    with tarfile.open(path, "w:gz") as tar:
        for name, text in files.items():
            data = text.encode("utf-8")
            info = tarfile.TarInfo(f"{root}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path
