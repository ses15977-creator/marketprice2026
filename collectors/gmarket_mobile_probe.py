#!/usr/bin/env python3
"""Read-only, bounded inspection of user-supplied Gmarket mobile promotion URLs.

Never bypass access controls, infer product prices, or save observations.
"""
import html.parser
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

URLS = (
    "https://m.gmarket.co.kr/?sectionSeq=2&pageTypeSeq=7001",
    "https://m.gmarket.co.kr/n/superdeal",
)
MAX_SIZE = 2_000_000


class LinkScanner(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            self.current = [attrs.get("href", ""), []]
    def handle_data(self, data):
        if self.current is not None:
            self.current[1].append(data)
        if data.strip():
            self.text.append(data.strip())
    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            href, parts = self.current
            text = " ".join(" ".join(parts).split())
            self.links.append((href, text))
            self.current = None


def inspect(url, fetcher=urllib.request.urlopen):
    request = urllib.request.Request(url, headers={
        "User-Agent": "MarketPrice2026-Verification/1.0",
        "Accept": "text/html",
    })
    try:
        with fetcher(request, timeout=20) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return {"url": url, "status": "unsupported_content_type"}
            raw = response.read(MAX_SIZE + 1)
            if len(raw) > MAX_SIZE:
                return {"url": url, "status": "oversize"}
            encoding = response.headers.get_content_charset() or "utf-8"
            body = raw.decode(encoding, errors="replace")
    except urllib.error.HTTPError as exc:
        return {"url": url, "status": "http_error", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"url": url, "status": "network_error", "error_type": type(exc).__name__}
    scan = LinkScanner()
    scan.feed(body)
    # We deliberately do not equate arbitrary won amounts with a verified
    # product price, or webpage order with an official marketplace rank.
    product_links = {
        urllib.parse.urljoin(url, href) for href, _ in scan.links
        if ("goodscode=" in href.lower() or "/item/" in href.lower())
        and urllib.parse.urlsplit(urllib.parse.urljoin(url, href)).hostname
        in ("m.gmarket.co.kr", "item.gmarket.co.kr", "www.gmarket.co.kr")
    }
    return {
        "url": url,
        "status": "html_accessible",
        "html_bytes": len(raw),
        "link_count": len(scan.links),
        "product_link_candidates": len(product_links),
        "superdeal_word_present": "슈퍼딜" in body,
        "extractable_verified_products": 0,
        "note": "Candidate links alone do not verify name, total price, shipping or deal rank.",
    }


def main():
    results = [inspect(url) for url in URLS]
    accessible = any(x["status"] == "html_accessible" for x in results)
    summary = {
        "state": "html_accessible_needs_price_verification" if accessible else "access_unavailable",
        "results": results,
        "verified_products_saved": 0,
        "automated_product_collection_ready": False,
    }
    report_path = pathlib.Path(os.environ.get("GMARKET_REPORT_PATH", "gmarket-probe-result.json"))
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("REPORT_PATH=" + str(report_path))
    if not accessible:
        print("ACCESS_UNAVAILABLE: Cannot inspect page HTML; automatic collection is NOT running.")
        return 2
    print("ACCESSIBLE_ONLY: HTML access does NOT prove product and price extraction.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
