#!/usr/bin/env python3
"""
Backfill MTG set metadata (release_date + set_icon_uri) into MySQL sets table.

Inputs:
- icon-set/final/manual_review.normalized.json
- icon-set/final/set_icons_manifest.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pymysql


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NORMALIZED = WORKSPACE_ROOT / "icon-set" / "final" / "manual_review.normalized.json"
DEFAULT_MANIFEST = WORKSPACE_ROOT / "icon-set" / "final" / "set_icons_manifest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill set release date and icon uri for MTG sets.")
    parser.add_argument("--normalized", default=str(DEFAULT_NORMALIZED), help="Path to normalized metadata JSON.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Path to icon manifest JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB.")
    return parser.parse_args()


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_connection() -> pymysql.Connection:
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DATABASE"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def main() -> None:
    args = parse_args()
    rows: list[dict[str, Any]] = load_json(args.normalized)
    icon_manifest: dict[str, str] = load_json(args.manifest)

    updates: list[tuple[str | None, str | None, int]] = []
    for row in rows:
        ct_id = row.get("cardtrader_id")
        if not isinstance(ct_id, int):
            continue
        release_date = row.get("release_date")
        icon_id = row.get("icon")
        icon_url = icon_manifest.get(str(icon_id)) if isinstance(icon_id, int) else None
        updates.append((release_date, icon_url, ct_id))

    print(f"Prepared updates: {len(updates)}")
    if args.dry_run:
        print("Dry run mode enabled; no DB writes.")
        return

    conn = get_connection()
    updated_rows = 0
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM games WHERE slug = %s LIMIT 1", ("mtg",))
            game_row = cur.fetchone()
            if not game_row:
                raise RuntimeError("Game slug 'mtg' not found in games table.")
            mtg_game_id = int(game_row["id"])

            query = """
                UPDATE sets
                SET release_date = COALESCE(%s, release_date),
                    set_icon_uri = COALESCE(%s, set_icon_uri)
                WHERE cardtrader_id = %s
                  AND game_id = %s
            """
            for release_date, icon_url, ct_id in updates:
                cur.execute(query, (release_date, icon_url, ct_id, mtg_game_id))
                updated_rows += cur.rowcount
        conn.commit()
    finally:
        conn.close()

    print(f"Updated set rows: {updated_rows}")


if __name__ == "__main__":
    main()
