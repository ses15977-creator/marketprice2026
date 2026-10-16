import io
import pathlib
import sys
import unittest
from email.message import Message
from unittest.mock import Mock
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gmarket_mobile_probe as probe

class Response:
    def __init__(self, content, content_type="text/html; charset=utf-8"):
        self.content=content.encode("utf-8")
        self.headers=Message()
        self.headers["Content-Type"]=content_type
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.content[:n]

class ProbeTests(unittest.TestCase):
    def test_product_link_not_mistaken_for_verified_price(self):
        html='<a href="/item?goodscode=1234">사과 5,000원</a> 슈퍼딜'
        result=probe.inspect(probe.URLS[0], lambda *_a, **_kw: Response(html))
        self.assertEqual(result["product_link_candidates"], 1)
        self.assertEqual(result["extractable_verified_products"], 0)
    def test_empty_page_has_no_product_candidates(self):
        result=probe.inspect(probe.URLS[0], lambda *_a, **_kw: Response("<html></html>"))
        self.assertEqual(result["product_link_candidates"], 0)
    def test_non_html_response_is_rejected(self):
        result=probe.inspect(probe.URLS[0], lambda *_a, **_kw: Response("{}", "application/json"))
        self.assertEqual(result["status"], "unsupported_content_type")

if __name__ == "__main__":
    unittest.main()
