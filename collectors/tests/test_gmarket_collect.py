import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gmarket_collect as c

def page(**changes):
    offer={'@type':'Offer','price':'12000','priceCurrency':'KRW','url':'https://item.gmarket.co.kr/Item?goodscode=1234&utm_source=test','shippingDetails':{'shippingRate':{'currency':'KRW','value':3000}}}
    offer.update(changes)
    return '<script type="application/ld+json">'+json.dumps({'@type':'Product','name':'테스트 상품','offers':offer})+'</script>'

class CollectionTests(unittest.TestCase):
    def extract(self, html): return c.extract(html, c.URLS[1], '2026-10-01T00:00:00+00:00')
    def test_explicit_offer(self):
        rows=self.extract(page()); self.assertEqual(rows[0]['price'],12000); self.assertEqual(rows[0]['shipping'],3000)
        self.assertEqual(rows[0]['url'],'https://item.gmarket.co.kr/Item?goodscode=1234')
    def test_unknown_shipping_skipped(self): self.assertEqual(self.extract(page(shippingDetails={})),[])
    def test_untrusted_url_skipped(self): self.assertEqual(self.extract(page(url='https://evil.example/?goodscode=1234')),[])
    def test_no_inferred_price(self): self.assertEqual(self.extract('<a href="/item?goodscode=1234">사과 1,000원</a>'),[])
    def test_aggregate_price_skipped(self): self.assertEqual(self.extract(page(**{'@type':'AggregateOffer'})),[])
    def test_duplicates_collapsed(self): self.assertEqual(len(self.extract(page()+page())),1)
    def test_conflicting_prices_fail(self):
        with self.assertRaises(ValueError): self.extract(page()+page(price='13000'))
    def test_nonfinite_skipped(self): self.assertEqual(self.extract(page(price='NaN')),[])
    def test_robots_denial_stops_before_page(self):
        with patch.object(c,'read',return_value='User-agent: *\nDisallow: /') as read:
            with self.assertRaises(ValueError): c.collect(c.URLS[1], '2026-10-01T00:00:00Z')
            self.assertEqual(read.call_count,1)
    def test_duplicate_wildcard_groups_do_not_hide_denial(self):
        rules='User-agent: *\nAllow: /\n\nUser-agent: *\nDisallow: /'
        self.assertFalse(c.robots_allowed(rules,c.URLS[1]))
    def test_403_stops_without_bypass(self):
        import urllib.error
        with patch.object(c,'read',side_effect=urllib.error.HTTPError(c.URLS[1],403,'Forbidden',{},None)) as read:
            with self.assertRaises(urllib.error.HTTPError): c.collect(c.URLS[1], '2026-10-01T00:00:00Z')
            self.assertEqual(read.call_count,1)
