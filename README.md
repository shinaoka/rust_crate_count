# rust-crate-count

Count crates.io crates over time from the official database dump, then generate CSV and chart artifacts.

The checked-in `output/` directory includes generated CSV, PNG, PDF, and SVG artifacts.

## Usage

```sh
uv run rust-crate-count
```

By default this downloads `https://static.crates.io/db-dump.tar.gz` into `.cache/` and writes outputs under `output/`.

To reproduce the committed artifacts with an existing dump:

```sh
uv run rust-crate-count --dump-path /path/to/db-dump.tar.gz --output-dir output
```

## Outputs

- `output/crates_io_yearly_crate_counts.csv`
- `output/crates_io_yearly_crate_counts.png`
- `output/crates_io_yearly_crate_counts.pdf`
- `output/crates_io_yearly_crate_counts.svg`
- `output/crates_io_monthly_rolling_12m.csv`
- `output/crates_io_monthly_rolling_12m.png`
- `output/crates_io_monthly_rolling_12m.pdf`
- `output/crates_io_monthly_rolling_12m.svg`

## Counting Rules

- Read the official crates.io DB dump.
- Count crate creation years from `crates.created_at`.
- Include deleted crate creation years from `deleted_crates.created_at`.
- Reconstruct `active_at_jan1` by adding deleted crates only when they existed at that Jan 1 timestamp.
- Mark the dump year as partial because the dump may be mid-year.

This is a raw crate-count metric. It intentionally does not try to filter tutorials, name reservations, generated API bindings, `*-sys` crates, or spam-like crate registrations.

### Rolling release counts

The monthly series answers a different question: how many packages were updated in the
previous 12 months, as a function of time. A crate counts at a month start when at least one
of its `versions.created_at` values falls in the previous 365 days, so a crate with several
releases inside the window still counts once. `registered` is the cumulative number of current
crates at that month start, so the ratio is the share of registered crates that were released
in the past year.

Deleted crates are excluded from this series, and the final point is the start of the dump
month, so its window ends slightly before the dump timestamp.

## Development

```sh
uv run --group dev pytest -q
```
