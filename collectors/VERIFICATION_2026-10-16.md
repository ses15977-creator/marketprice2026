# Gmarket collection verification — 2026-10-16

## Actual outcomes

- Previous mobile probe run 38870241288: both URLs HTTP 403.
- Updated collection run 38870935555: both requests HTTP 403, saved=0,
  run_log_saved=false. Report artifact uploaded despite failed execution.
- Runner environment shows SUPABASE_URL configured but
  SUPABASE_SERVICE_ROLE_KEY empty. No credentials were disclosed or changed.
- Local probe can retrieve HTML, but that does not establish collection permission
  or product extraction. The local robots.txt response contains duplicate wildcard
  groups including Disallow: /. The collector stops on the restrictive group.
- 22 offline unit tests passed locally and on GitHub. They use synthetic fixtures;
  they do not prove live product extraction or database idempotence.
- Public Supabase REST read succeeded; offers, observations and collection_runs
  were empty at verification. No sample products were inserted.
- Pages deployment 38870935631 succeeded. Duplicate deployment workflow removed.

## Implemented, not live-verified

- Public Product/Offer JSON-LD extraction of name, KRW price, canonical goodscode
  URL and explicit delivery fee. Unknown delivery fees and conflicting prices
  are rejected; aggregate prices and arbitrary text are not treated as offers.
- Hourly Actions workflow, bounded requests, conservative robots handling,
  HTTP 403 stop, failure report artifacts and optional database run logging.
- Transactional server-only RPC migration with advisory lock and UTC-hour
  idempotence. Migration is committed, NOT applied to the production database.
- Website collection-status explanation and latest-first history queries.

## Remaining blockers

1. A permitted Gmarket source/feed/API or explicit collection permission is needed.
   Do not bypass HTTP 403 or impersonate a crawler with special access.
2. Configure the server-side Actions secret SUPABASE_SERVICE_ROLE_KEY using an
   authorized server key; never place it in browser code or commit it.
3. Apply database/002_atomic_observations.sql as database owner.
4. Once a permitted source yields actual verified products, test insertion,
   repeat the same observation and concurrently invoke the RPC, checking that
   only one offer/observation is created. Legacy CSV writers use a different
   write path and are outside the RPC locking guarantee.
5. Verify scheduled-event execution after its first actual hourly trigger.
   Push-triggered execution has been verified; a future schedule has not.

Automatic collection has NOT succeeded. Real products saved: 0.
