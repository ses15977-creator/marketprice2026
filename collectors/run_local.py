#!/usr/bin/env python3
"""Local PC entrypoint for the verified Gmarket collector.

The current collector enforces robots.txt, only accepts verified JSON-LD,
and writes Supabase only when the required server credentials and migration exist.
"""
import argparse
import datetime as dt
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "collectors" / "gmarket_collect.py"
LOG_DIR = ROOT / "local-logs"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the bounded MarketPrice local collector")
    parser.add_argument("--check-only", action="store_true", help="Run collector without Supabase credentials or database writes")
    args = parser.parse_args(argv)
    LOG_DIR.mkdir(exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc)
    name = now.strftime("gmarket-%Y%m%dT%H%M%SZ.log")
    env = os.environ.copy()
    if args.check_only:
        env.pop("SUPABASE_SERVICE_ROLE_KEY", None)
        env.pop("SUPABASE_URL", None)
    result = subprocess.run(
        [sys.executable, str(COLLECTOR)],
        cwd=str(ROOT), env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=300, check=False,
    )
    log = LOG_DIR / name
    # Existing collector output contains metadata/results but not secrets.
    log.write_text(result.stdout, encoding="utf-8")
    print("LOG_FILE=" + str(log))
    print("COLLECTOR_EXIT_CODE=" + str(result.returncode))
    if result.returncode:
        print("Collection did not succeed. Inspect log; do not treat this as saved product data.")
    return result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        print("Collector exceeded five-minute timeout", file=sys.stderr)
        sys.exit(3)
