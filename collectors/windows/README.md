# MarketPrice local PC collection (Windows)

**Status:** Gmarket only. No proven working auto-import at this stage.
The runner does **not** bypass Gmarket 403 or robots restrictions. A PC
running continuously does not grant permission to scrape. Stop if forbidden.

## Requirements
- Windows 10/11 PC with Python 3.10+ and outbound HTTPS.
- Clone or download the repository to a stable directory (e.g. `C:\\MarketPrice`).
- Get provider permission for automated use; verify the Gmarket source terms.
- Supabase owner must apply `database/002_atomic_observations.sql` before any writes.
- The Supabase secret key belongs only on this trusted PC, never in a committed
  file, webpage, screenshot or GitHub issue. If you don't need DB writes, leave
  credentials unset and use `--check-only`.

## 1. First, run a safe read-only check

Open PowerShell in the repository directory:

```powershell
python collectors/run_local.py --check-only
```

The result is in `local-logs\gmarket-*.log` and
`gmarket-collection-result.json`. Exit code 2 means no verified product
was saved; check the report for robots.txt denial, HTTP 403 or missing
explicit product-price-shipping data. Do not circumvent restrictions.

## 2. Enable writes only after permission and database migration

In **Windows user environment variables**, configure:
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — your Supabase server-only secret

Close and reopen PowerShell to load environment changes. Do **not** paste a
secret into a chat, scheduled-task argument, repository file, or shared log.
Test with `python collectors/run_local.py`. Check actual dashboard content
and database records: program launch alone is not confirmation of an import.

## 3. Schedule an hourly run

Run under the Windows user who set the environment variables:

```powershell
powershell -ExecutionPolicy Bypass -File .\collectors\windows\install-hourly.ps1
```

The Windows Task Scheduler entry `MarketPrice-Gmarket-Hourly` runs hourly
**only while that Windows user is signed in**. Keep the account logged in and
disable sleep (Settings > System > Power). This deliberately avoids saving
a Windows password or database secret in the scheduler.

Task logs are written to `local-logs`. Update your repository with `git pull`
when collector code changes. To remove the schedule:

```powershell
Unregister-ScheduledTask -TaskName MarketPrice-Gmarket-Hourly -Confirm:$false
```

## What works today?
- Local hourly execution and diagnostic logging are implemented.
- Automatic source extraction still requires pages to expose verified Product +
  Offer JSON-LD with both KRW price and shipping. The Gmarket mobile event
  pages have not been verified to expose this information, and 403 was seen
  from GitHub-hosted access.
- Other marketplace collectors are **not** installed. Use authorized APIs or
  permitted feeds before enabling them.
