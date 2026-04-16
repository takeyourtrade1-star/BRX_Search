#!/usr/bin/env python3
"""
Normalize icon-set/final/manual_review.json for DB backfill usage.

Output:
- icon-set/final/manual_review.normalized.json
- icon-set/final/manual_review.report.json
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ICON_SET_DIR = WORKSPACE_ROOT / "icon-set" / "final"
INPUT_PATH = ICON_SET_DIR / "manual_review.json"
OUTPUT_PATH = ICON_SET_DIR / "manual_review.normalized.json"
REPORT_PATH = ICON_SET_DIR / "manual_review.report.json"
ICON_DIR = ICON_SET_DIR / "icone"

REQUIRED_FIELDS = ("ebartex_id", "name", "icon", "cardtrader_id", "data")


@dataclass
class NormalizedRow:
    ebartex_id: int
    name: str
    icon: int | None
    cardtrader_id: int
    release_date: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ebartex_id": self.ebartex_id,
            "name": self.name,
            "icon": self.icon,
            "cardtrader_id": self.cardtrader_id,
            "release_date": self.release_date,
        }


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        if value.isdigit():
            return int(value)
    return None


def _parse_date(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None

    cleaned = raw.rstrip("Z")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _pick_raw_date(row: dict[str, Any]) -> Any:
    if row.get("data"):
        return row.get("data")
    if row.get("dat"):
        return row.get("dat")
    reason = row.get("reason")
    if isinstance(reason, str) and "/" in reason:
        return reason
    return None


def _pick_raw_icon(row: dict[str, Any]) -> Any:
    if row.get("icon") is not None:
        return row.get("icon")
    if row.get("iconA") is not None:
        return row.get("iconA")
    return None


def normalize_rows(raw_rows: list[dict[str, Any]]) -> tuple[list[NormalizedRow], dict[str, Any]]:
    problems: list[dict[str, Any]] = []
    normalized: list[NormalizedRow] = []

    for row in raw_rows:
        ebartex_id = _parse_int(row.get("ebartex_id"))
        cardtrader_id = _parse_int(row.get("cardtrader_id"))
        icon = _parse_int(_pick_raw_icon(row))
        release_date = _parse_date(_pick_raw_date(row))
        name = str(row.get("name") or "").strip()

        missing_required: list[str] = []
        if ebartex_id is None:
            missing_required.append("ebartex_id")
        if not name:
            missing_required.append("name")
        if cardtrader_id is None:
            missing_required.append("cardtrader_id")
        # icon/release_date can be null for unresolved rows, but we still track issues
        if icon is None:
            missing_required.append("icon")
        if release_date is None:
            missing_required.append("data")

        if ebartex_id is None or cardtrader_id is None or not name:
            problems.append(
                {
                    "severity": "error",
                    "ebartex_id": row.get("ebartex_id"),
                    "name": row.get("name"),
                    "issue": "critical_missing_fields",
                    "missing": missing_required,
                }
            )
            continue

        if icon is None or release_date is None:
            problems.append(
                {
                    "severity": "warning",
                    "ebartex_id": ebartex_id,
                    "name": name,
                    "issue": "partial_row",
                    "missing": missing_required,
                }
            )

        normalized.append(
            NormalizedRow(
                ebartex_id=ebartex_id,
                name=name,
                icon=icon,
                cardtrader_id=cardtrader_id,
                release_date=release_date,
            )
        )

    icon_files = {int(p.stem) for p in ICON_DIR.glob("*.svg") if p.stem.isdigit()}
    icons_used = {row.icon for row in normalized if row.icon is not None}
    missing_icon_files = sorted(i for i in icons_used if i not in icon_files)
    orphan_icon_files = sorted(i for i in icon_files if i not in icons_used)

    summary = {
        "input_rows": len(raw_rows),
        "normalized_rows": len(normalized),
        "problems_count": len(problems),
        "missing_icon_files_count": len(missing_icon_files),
        "orphan_icon_files_count": len(orphan_icon_files),
        "required_fields": list(REQUIRED_FIELDS),
    }

    report = {
        "summary": summary,
        "problems": problems,
        "missing_icon_files": missing_icon_files,
        "orphan_icon_files": orphan_icon_files,
    }
    return normalized, report


def main() -> None:
    raw_rows = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    normalized, report = normalize_rows(raw_rows)

    OUTPUT_PATH.write_text(
        json.dumps([row.to_dict() for row in normalized], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Normalized rows: {len(normalized)}")
    print(f"Report issues: {report['summary']['problems_count']}")
    print(f"Missing icon files: {report['summary']['missing_icon_files_count']}")
    print(f"Wrote: {OUTPUT_PATH}")
    print(f"Wrote: {REPORT_PATH}")


if __name__ == "__main__":
    main()
