from __future__ import annotations

import argparse
from pathlib import Path

from rust_crate_count.chart import write_chart, write_rolling_chart
from rust_crate_count.crates_io import (
    DB_DUMP_URL,
    download_dump,
    monthly_rolling_counts,
    read_dump,
    write_counts_csv,
    write_rolling_csv,
    yearly_counts,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count crates.io crates over time from the official database dump."
    )
    parser.add_argument(
        "--dump-path",
        type=Path,
        default=Path(".cache/db-dump.tar.gz"),
        help="Path to crates.io db-dump.tar.gz. It will be downloaded if missing.",
    )
    parser.add_argument("--dump-url", default=DB_DUMP_URL, help="crates.io DB dump URL.")
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Download the DB dump even when --dump-path already exists.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for CSV and chart outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    download_dump(args.dump_url, args.dump_path, force=args.force_download)
    dump = read_dump(args.dump_path)
    timestamp = dump.timestamp.isoformat().replace("+00:00", "Z")

    output_stem = args.output_dir / "crates_io_yearly_crate_counts"
    rows = yearly_counts(dump.current_created, dump.deleted_crates, dump.timestamp)
    csv_path = output_stem.with_suffix(".csv")
    write_counts_csv(rows, csv_path)
    chart_paths = write_chart(rows, timestamp, output_stem)

    rolling_stem = args.output_dir / "crates_io_monthly_rolling_12m"
    rolling_csv_path = rolling_stem.with_suffix(".csv")
    rolling_rows = monthly_rolling_counts(dump)
    write_rolling_csv(rolling_rows, rolling_csv_path)
    rolling_chart_paths = write_rolling_chart(rolling_rows, timestamp, rolling_stem)

    for path in [csv_path, *chart_paths, rolling_csv_path, *rolling_chart_paths]:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
