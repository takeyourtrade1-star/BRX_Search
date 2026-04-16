#!/usr/bin/env python3
"""
Upload set icon SVG files to S3 and generate a JSON manifest.

Expected input icons:
  icon-set/final/icone/{icon_id}.svg
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
ICON_DIR = WORKSPACE_ROOT / "icon-set" / "final" / "icone"
OUTPUT_MANIFEST = WORKSPACE_ROOT / "icon-set" / "final" / "set_icons_manifest.json"


def build_public_url(cdn_base_url: str, key: str) -> str:
    base = cdn_base_url.rstrip("/")
    return f"{base}/{key}"


def collect_svg_files(icon_dir: Path) -> list[Path]:
    return sorted(icon_dir.glob("*.svg"), key=lambda p: int(p.stem) if p.stem.isdigit() else 10**12)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload set icon SVG files to S3.")
    parser.add_argument("--bucket", required=True, help="Target S3 bucket name.")
    parser.add_argument(
        "--prefix",
        default="set-icons",
        help="S3 key prefix (default: set-icons).",
    )
    parser.add_argument(
        "--cdn-base-url",
        required=True,
        help="Public CDN base URL used by frontend (e.g. https://cdn.example.com).",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Optional AWS region override.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate manifest only, no uploads.",
    )
    parser.add_argument(
        "--manifest-out",
        default=str(OUTPUT_MANIFEST),
        help="Output manifest path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    icon_files = collect_svg_files(ICON_DIR)
    if not icon_files:
        raise SystemExit(f"No SVG files found in {ICON_DIR}")

    s3_client = None
    if not args.dry_run:
        import boto3

        s3_client = boto3.client("s3", region_name=args.region)

    manifest: dict[str, str] = {}
    prefix = args.prefix.strip("/").rstrip("/")

    for icon_file in icon_files:
        icon_id = icon_file.stem
        key = f"{prefix}/{icon_id}.svg"
        public_url = build_public_url(args.cdn_base_url, key)
        manifest[icon_id] = public_url

        if s3_client is not None:
            s3_client.upload_file(
                str(icon_file),
                args.bucket,
                key,
                ExtraArgs={
                    "ContentType": "image/svg+xml",
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )

    out_path = Path(args.manifest_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    mode = "DRY RUN" if args.dry_run else "UPLOAD"
    print(f"{mode} completed. Manifest rows: {len(manifest)}")
    print(f"Manifest: {out_path}")


if __name__ == "__main__":
    main()
