#!/usr/bin/env python3
"""Read-only Gmarket Super Deal HTML inspection. Never writes unverified data."""
import html.parser
import json
import sys
import urllib.error
import urllib.request

URL = "https://www.gmarket.co.kr/"
MAX_BYTES = 3_000_000

class Inspector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.href = None
        self.anchor_text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.anchor_text = []
    def handle_data(self, data):
        value = " ".join(data.split())
        if value:
            self.text.append(value)
            if self.href is not None:
                self.anchor_text.append(value)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append({"text": " ".join(self.anchor_text)[:100], "href": self.href[:250]})
            self.href = None
            self.anchor_text = []

def main():
    req = urllib.request.Request(URL, headers={"User-Agent": "MarketPrice2026/0.1 (read-only verification; contact repository owner)", "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            final_url = res.geturl()
            ctype = res.headers.get("Content-Type", "")
            raw = res.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Page exceeded safety limit")
            if "html" not in ctype.lower():
                raise ValueError("Unexpected content type")
            charset = res.headers.get_content_charset() or "utf-8"
            doc = raw.decode(charset, errors="replace")
    except (urllib.error.URLError, ValueError) as exc:
        print("PROBE_UNAVAILABLE:", str(exc)[:180])
        sys.exit(1)
    parser = Inspector()
    parser.feed(doc)
    positions = [i for i, value in enumerate(parser.text) if "슈퍼딜" in value]
    report = {
        "source": URL,
        "final_url": final_url,
        "html_bytes": len(raw),
        "superdeal_mentions": len(positions),
        "sample_section_text": [" ".join(parser.text[i:i+12])[:260] for i in positions[:3]],
        "superdeal_link_candidates": [
            link for link in parser.links if "슈퍼딜" in link["text"]
        ][:5],
        "products_saved": 0,
        "status": "inspection_only",
        "note": "No rank, product price, or shipping charge is inferred from unverified HTML."
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not positions:
        sys.exit("PROBE_NO_SUPERDEAL: site may render via JavaScript or block automated access")

if __name__ == "__main__":
    main()
