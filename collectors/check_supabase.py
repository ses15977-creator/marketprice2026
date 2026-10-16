#!/usr/bin/env python3
"""Read-only database connectivity test using private Actions secrets."""
import json
import os
import sys
import urllib.error
import urllib.request

def main():
    base = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base.startswith("https://") or not key:
        sys.exit("MISSING_SECRETS: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    url = base + "/rest/v1/platforms?select=id,name&order=id.asc&limit=5"
    # Supabase sb_secret_* tokens are API keys, not JWTs. The apikey header
    # suffices; an Authorization: Bearer header is only set for legacy JWT keys.
    headers = {"apikey": key, "Accept": "application/json"}
    if key.startswith("eyJ"):
        headers["Authorization"] = "Bearer " + key
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as res:
            response = json.load(res)
    except urllib.error.HTTPError as err:
        sys.exit("SUPABASE_HTTP_ERROR: " + str(err.code))
    except (urllib.error.URLError, ValueError) as err:
        sys.exit("SUPABASE_CONNECTION_ERROR: " + type(err).__name__)
    if not isinstance(response, list) or not any(p.get("name") == "G마켓" for p in response):
        sys.exit("UNEXPECTED_DB_DATA: Gmarket platform not found")
    print("SUPABASE_READ_OK: found", len(response), "configured platforms")
    print("NO_WRITES: verified read permissions only")

if __name__ == "__main__":
    main()
