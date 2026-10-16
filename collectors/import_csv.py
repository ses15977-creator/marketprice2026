#!/usr/bin/env python3
"""Import verified offer observations from a trusted CSV file into Supabase.

Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the runner environment.
Never use this service-role key in browser code or commit it to Git.
"""
import csv
import datetime as dt
import json
import math
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

PLATFORMS = {"G마켓": 1, "옥션": 2, "11번가": 3, "쿠팡": 4, "카카오쇼핑": 5}
REQUIRED = {"platform", "product_name", "listing_url", "seller_price", "shipping_fee", "observed_at", "source_url"}
BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
FILE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "collectors/observations.csv")


def request(table, method="GET", body=None, query=""):
    url = BASE + "/rest/v1/" + table + query
    headers = {"apikey": KEY, "Content-Type": "application/json", "Prefer": "return=representation"}
    if KEY.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + KEY
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def parse_time(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must contain a timezone offset")
    if parsed > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        raise ValueError("future observation time")
    return parsed.isoformat()


def validate(row, line):
    missing = [k for k in REQUIRED if not row.get(k, "").strip()]
    if missing:
        raise ValueError(f"line {line}: missing {', '.join(missing)}")
    platform = row["platform"].strip()
    if platform not in PLATFORMS:
        raise ValueError(f"line {line}: unknown platform")
    for field in ("listing_url", "source_url"):
        u = urllib.parse.urlsplit(row[field].strip())
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            raise ValueError(f"line {line}: invalid {field}")
    price = float(row["seller_price"])
    shipping = float(row["shipping_fee"])
    if not (math.isfinite(price) and math.isfinite(shipping) and 0 <= price <= 1000000000 and 0 <= shipping <= 1000000000):
        raise ValueError(f"line {line}: invalid price")
    rank = row.get("rank", "").strip()
    if rank and (not rank.isdecimal() or not 1 <= int(rank) <= 10):
        raise ValueError(f"line {line}: rank must be 1-10")
    return {"platform_id": PLATFORMS[platform], "name": row["product_name"].strip(),
            "url": row["listing_url"].strip(), "seller": row.get("seller_name", "").strip(),
            "price": price, "shipping": shipping, "observed_at": parse_time(row["observed_at"].strip()),
            "source_url": row["source_url"].strip(), "rank": int(rank) if rank else None,
            "is_deal": row.get("is_deal", "").strip().lower() in ("1", "true", "yes")}


def main():
    if not BASE.startswith("https://") or not KEY:
        sys.exit("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY (GitHub Actions secrets)")
    if not FILE.is_file():
        sys.exit(f"CSV not found: {FILE}")
    with FILE.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not REQUIRED.issubset(reader.fieldnames or []):
            sys.exit("CSV is missing required headers")
        records = [validate(row, n) for n, row in enumerate(reader, 2)]
    if not records:
        print("No rows to import; no observations created")
        return
    import_records(records)


def import_records(records):
    """Save pre-validated observations; exact timestamps are idempotent."""
    for rec in records:
        query = "?platform_id=eq." + str(rec["platform_id"]) + "&url=eq." + urllib.parse.quote(rec["url"], safe="") + "&select=id&limit=1"
        matches = request("offers", query=query)
        if matches:
            offer_id = matches[0]["id"]
        else:
            product_id = request("products", "POST", {"name": rec["name"]})[0]["id"]
            offer_id = request("offers", "POST", {"platform_id": rec["platform_id"],
                "product_id": product_id, "listing_title": rec["name"],
                "seller_name": rec["seller"], "url": rec["url"], "is_deal": rec["is_deal"]})[0]["id"]
        stamp = urllib.parse.quote(rec["observed_at"], safe="")
        existing = request("observations", query=f"?offer_id=eq.{offer_id}&observed_at=eq.{stamp}&select=id&limit=1")
        if existing:
            print("Skipped existing observation", offer_id, rec["observed_at"])
            continue
        request("observations", "POST", {"offer_id": offer_id, "seller_price": rec["price"],
            "shipping_fee": rec["shipping"], "observed_at": rec["observed_at"],
            "source_url": rec["source_url"]})
        if rec["rank"] is not None:
            request("rank_observations", "POST", {"offer_id": offer_id,
                "rank": rec["rank"], "observed_at": rec["observed_at"]})
        print("Imported verified observation", offer_id, rec["observed_at"])

if __name__ == "__main__":
    try:
        main()
    except (ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        sys.exit(f"Import failed: {exc}")
