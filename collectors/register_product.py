#!/usr/bin/env python3
"""Register ONE independently verified product through private GitHub Actions inputs.

Reads fields from environment, validates them with the existing CSV importer, and
writes through server-side Supabase credentials. No service key goes to the website.
"""
import datetime as dt
import os
import sys
import urllib.error

import import_csv

FIELD_MAP = {
    "platform": "PRODUCT_PLATFORM",
    "product_name": "PRODUCT_NAME",
    "listing_url": "PRODUCT_URL",
    "seller_price": "PRODUCT_PRICE",
    "shipping_fee": "PRODUCT_SHIPPING",
    "source_url": "PRODUCT_SOURCE_URL",
    "seller_name": "PRODUCT_SELLER",
    "is_deal": "PRODUCT_IS_DEAL",
}

def main():
    if not import_csv.BASE.startswith("https://") or not import_csv.KEY:
        sys.exit("Supabase credentials missing; nothing registered")
    row = {field: os.environ.get(var, "").strip() for field, var in FIELD_MAP.items()}
    # Timestamp recorded by the trusted runner, not fabricated historical history.
    row["observed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    row["rank"] = ""  # Never invent a marketplace ranking.
    rec = import_csv.validate(row, 1)
    if not rec["name"] or len(rec["name"]) > 200:
        raise ValueError("Product name must be 1-200 characters")
    if rec["price"] <= 0:
        raise ValueError("Product price must be above zero")
    import_csv.import_records([rec])
    print("Registration request completed. Verify the dashboard for saved data.")

if __name__ == "__main__":
    try:
        main()
    except (ValueError, urllib.error.URLError) as exc:
        sys.exit(f"Registration failed: {exc}")
