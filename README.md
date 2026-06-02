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

## Counting Rules

- Read the official crates.io DB dump.
- Count crate creation years from `crates.created_at`.
- Include deleted crate creation years from `deleted_crates.created_at`.
- Reconstruct `active_at_jan1` by adding deleted crates only when they existed at that Jan 1 timestamp.
- Mark the dump year as partial because the dump may be mid-year.

This is a raw crate-count metric. It intentionally does not try to filter tutorials, name reservations, generated API bindings, `*-sys` crates, or spam-like crate registrations.

## Development

```sh
uv run --group dev pytest -q
```
