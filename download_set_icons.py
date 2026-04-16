#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
import logging
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("requests library required. Install with: pip install requests")
    sys.exit(1)

BASE_API = "https://api.cardtrader.it/api/v2"

def safe_filename(s):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)

def download_file(url, dest_path, session, max_retries=3):
    for attempt in range(1, max_retries+1):
        try:
            r = session.get(url, timeout=30)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                return True, r.headers.get("Content-Type")
            else:
                logging.debug("Download failed %s -> %s (status %s)", url, dest_path, r.status_code)
        except Exception as e:
            logging.debug("Exception downloading %s: %s", url, e)
        time.sleep(0.5 * attempt)
    return False, None

def find_icon_in_obj(obj):
    # common keys to check
    keys = ["icon", "icon_url", "icon_svg", "logo", "image", "images", "assets"]
    for k in keys:
        if k in obj and obj[k]:
            return obj[k]
    return None

def maybe_extract_url(value):
    # value might be a string url or a dict with url fields
    if not value:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # try common subkeys
        for k in ("url", "href", "svg", "png"):
            if k in value and value[k]:
                return value[k]
        # maybe nested assets
        for v in value.values():
            if isinstance(v, str) and v.startswith("http"):
                return v
    return None

def ensure_dir(d):
    os.makedirs(d, exist_ok=True)

def main():
    p = argparse.ArgumentParser(description="Download set icons from CardTrader expansions JSON and (optionally) per-expansion endpoint")
    p.add_argument("--expansions", default="sets_da_cardtrader.json", help="Expansions JSON file (default: sets_da_cardtrader.json)")
    p.add_argument("--out", default="output/set-data/icons", help="Output directory for icons")
    p.add_argument("--map", default="output/set-data/icons_map.json", help="Output JSON map file")
    p.add_argument("--token", default=os.environ.get("CARDTRADER_TOKEN"), help="CardTrader API token (or set CARDTRADER_TOKEN env var)")
    p.add_argument("--per-expansion", action="store_true", help="If no icon field in list, fetch per-expansion endpoint to try to find icons")
    p.add_argument("--dry-run", action="store_true", help="Inspect expansions and report what would be downloaded (no network) when icon URL present) ")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not os.path.exists(args.expansions):
        logging.error("Expansions file not found: %s", args.expansions)
        sys.exit(1)

    with open(args.expansions, "r", encoding="utf-8") as f:
        exps = json.load(f)

    ensure_dir(args.out)

    session = requests.Session()
    if args.token:
        session.headers.update({"Authorization": f"Bearer {args.token}"})

    icons_map = {}
    found = 0
    to_download = []

    for e in exps:
        ct_id = e.get("id")
        code = e.get("code") or ""
        name = e.get("name") or ""

        icon_field = find_icon_in_obj(e)
        url = maybe_extract_url(icon_field)

        if url:
            found += 1
            to_download.append((ct_id, code, name, url))
            continue

        if args.per_expansion:
            # try per-expansion endpoint
            url_ep = f"{BASE_API}/expansions/{ct_id}"
            try:
                r = session.get(url_ep, timeout=20)
                if r.status_code == 200:
                    obj = r.json()
                    icon_field = find_icon_in_obj(obj)
                    url2 = maybe_extract_url(icon_field)
                    if url2:
                        to_download.append((ct_id, code, name, url2))
                        found += 1
                        continue
                else:
                    logging.debug("Per-expansion %s returned %s", url_ep, r.status_code)
            except Exception as ex:
                logging.debug("Error fetching per-expansion %s: %s", url_ep, ex)

    logging.info("Expansions total: %d, with direct/endpoint icons found: %d", len(exps), found)

    if args.dry_run:
        # write a preview map but do not download
        for ct_id, code, name, url in to_download:
            icons_map[str(ct_id)] = {"code": code, "name": name, "source": url, "local": None}
        ensure_dir(os.path.dirname(args.map) or ".")
        with open(args.map, "w", encoding="utf-8") as f:
            json.dump(icons_map, f, indent=2, ensure_ascii=False)
        logging.info("Wrote preview map: %s", args.map)
        return

    # actual download
    success = 0
    for ct_id, code, name, url in to_download:
        parsed = urlparse(url)
        ext = os.path.splitext(parsed.path)[1] or ".png"
        fname = f"{ct_id}_{safe_filename(code or name)}{ext}"
        dest = os.path.join(args.out, fname)
        ok, ctype = download_file(url, dest, session)
        if ok:
            icons_map[str(ct_id)] = {"code": code, "name": name, "source": url, "local": os.path.relpath(dest)}
            success += 1
            logging.info("Downloaded %s -> %s", url, dest)
        else:
            icons_map[str(ct_id)] = {"code": code, "name": name, "source": url, "local": None}
            logging.warning("Failed to download: %s", url)
        time.sleep(0.1)

    with open(args.map, "w", encoding="utf-8") as f:
        json.dump(icons_map, f, indent=2, ensure_ascii=False)

    logging.info("Downloaded %d/%d icons. Map saved to %s", success, len(to_download), args.map)

if __name__ == '__main__':
    main()
