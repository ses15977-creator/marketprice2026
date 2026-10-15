# MarketPrice 2026 — 상품 데이터 수집 현황

## 확인된 사실 (2026-10-16)
- GitHub Actions CSV importer exists: `collectors/import_csv.py` and `collectors/observations.csv`.
- CSV currently contains only its header; no real products have been imported.
- GitHub-hosted read-only Gmarket homepage probe returned HTTP 403. Do not retry with evasion, proxy rotation, or disguised headers.
- Gmarket's official ESM Trading API exists: https://etapi.gmarket.com/ and seller goods search endpoint https://sa2.esmplus.com/item/v1/goods/search (https://etapi.gmarket.com/160).
- **Important**: This is a seller-facing API for registered seller goods. It is NOT a verified public Super Deal catalog/ranking API. Do not connect it as though it provided marketplace-wide rankings.
- Gmarket seller terms warn against unauthorized scraping (https://signin-partner.esmplus.com/login).

## Next integration gate
Obtain written permission or documented approved product/deal feed from Gmarket or an authorized partner, including coverage (Super Deal products, price, shipping, rank), authentication, reuse/display rights, and rate limits. Until then, keep the collector disabled and do not invent prices or ranking data.

## Authorized manual CSV route
With permission and independently verified source data, populate `collectors/observations.csv` following its existing header. The existing importer runs via `.github/workflows/import-observations.yml`. GitHub Actions secrets are configured separately and must never be committed.

## Safety
No credential values in source, no bypass of access restrictions, and no fabricated TOP 10.
