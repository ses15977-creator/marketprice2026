import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import import_csv

def sample():
    return dict(platform="G마켓", product_name="Verified test product",
        listing_url="https://item.gmarket.co.kr/item?goodscode=123",
        seller_price="10000", shipping_fee="0",
        observed_at="2026-10-01T00:00:00+09:00",
        source_url="https://item.gmarket.co.kr/item?goodscode=123",
        rank="", is_deal="true", seller_name="Test seller")

class ImportValidationTests(unittest.TestCase):
    def test_valid(self):
        record = import_csv.validate(sample(), 2)
        self.assertEqual(record["price"], 10000)
        self.assertTrue(record["is_deal"])

    def test_missing_product_name(self):
        row=sample(); row["product_name"]=""
        with self.assertRaises(ValueError): import_csv.validate(row, 2)

    def test_negative_price(self):
        row=sample(); row["seller_price"]="-1"
        with self.assertRaises(ValueError): import_csv.validate(row, 2)

    def test_non_http_url(self):
        row=sample(); row["listing_url"]="javascript:alert(1)"
        with self.assertRaises(ValueError): import_csv.validate(row, 2)

    def test_rank_out_of_range(self):
        row=sample(); row["rank"]="11"
        with self.assertRaises(ValueError): import_csv.validate(row, 2)

    def test_no_db_writes_for_existing_observation(self):
        row=import_csv.validate(sample(), 2)
        responses=[[{"id":17}],[{"id":99}]]
        with patch.object(import_csv, "request", side_effect=responses) as mock:
            import_csv.import_records([row])
        self.assertEqual(mock.call_count, 2)

if __name__ == "__main__":
    unittest.main()
