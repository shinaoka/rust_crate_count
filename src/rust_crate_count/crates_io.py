from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
import tarfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

DB_DUMP_URL = "https://static.crates.io/db-dump.tar.gz"


@dataclass(frozen=True)
class DeletedCrate:
    created_at: datetime
    deleted_at: datetime


@dataclass(frozen=True)
class YearlyCrateCount:
    year: int
    active_at_jan1: int
    new_crates: int
    new_current_crates: int
    new_deleted_crates: int
    partial_year: bool


@dataclass(frozen=True)
class DumpData:
    timestamp: datetime
    current_created: list[datetime]
    deleted_crates: list[DeletedCrate]


def parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    if normalized.endswith("+00"):
        normalized = normalized[:-3] + "+00:00"

    normalized = re.sub(
        r"\\.(\\d{6})\\d+([+-]\\d\\d:?\\d\\d)?$",
        lambda match: f".{match.group(1)}{match.group(2) or ''}",
        normalized,
    )
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def download_dump(url: str, path: Path, force: bool = False) -> None:
    if path.exists() and not force:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["curl", "-L", "--fail", url, "-o", str(path)], check=True)


def _dump_member(tar: tarfile.TarFile, suffix: str) -> tarfile.TarInfo:
    return next(member for member in tar.getmembers() if member.name.endswith(suffix))


def read_dump(path: Path) -> DumpData:
    csv.field_size_limit(sys.maxsize)
    current_created: list[datetime] = []
    deleted_crates: list[DeletedCrate] = []

    with tarfile.open(path, "r:gz") as tar:
        metadata_member = _dump_member(tar, "/metadata.json")
        metadata = json.loads(tar.extractfile(metadata_member).read().decode("utf-8"))
        timestamp = parse_timestamp(metadata["timestamp"])

        crates_member = _dump_member(tar, "/data/crates.csv")
        with tar.extractfile(crates_member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            for row in csv.DictReader(text):
                current_created.append(parse_timestamp(row["created_at"]))

        deleted_member = _dump_member(tar, "/data/deleted_crates.csv")
        with tar.extractfile(deleted_member) as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
            for row in csv.DictReader(text):
                deleted_crates.append(
                    DeletedCrate(
                        created_at=parse_timestamp(row["created_at"]),
                        deleted_at=parse_timestamp(row["deleted_at"]),
                    )
                )

    return DumpData(timestamp=timestamp, current_created=current_created, deleted_crates=deleted_crates)


def yearly_counts(
    current_created: Iterable[datetime],
    deleted_crates: Iterable[DeletedCrate],
    dump_timestamp: datetime,
) -> list[YearlyCrateCount]:
    current_created_list = list(current_created)
    deleted_crates_list = list(deleted_crates)
    all_created = current_created_list + [crate.created_at for crate in deleted_crates_list]

    if not all_created:
        return []

    new_by_year = Counter(created.year for created in all_created)
    current_new_by_year = Counter(created.year for created in current_created_list)
    deleted_new_by_year = Counter(crate.created_at.year for crate in deleted_crates_list)

    rows: list[YearlyCrateCount] = []
    start_year = min(new_by_year)
    end_year = dump_timestamp.year

    for year in range(start_year, end_year + 1):
        jan1 = datetime(year, 1, 1, tzinfo=timezone.utc)
        active_at_jan1 = sum(created < jan1 for created in current_created_list)
        active_at_jan1 += sum(
            crate.created_at < jan1 <= crate.deleted_at for crate in deleted_crates_list
        )
        rows.append(
            YearlyCrateCount(
                year=year,
                active_at_jan1=active_at_jan1,
                new_crates=new_by_year[year],
                new_current_crates=current_new_by_year[year],
                new_deleted_crates=deleted_new_by_year[year],
                partial_year=year == dump_timestamp.year,
            )
        )

    return rows


def write_counts_csv(rows: list[YearlyCrateCount], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "year",
                "active_at_jan1",
                "new_crates",
                "new_current_crates",
                "new_deleted_crates",
                "partial_year",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
