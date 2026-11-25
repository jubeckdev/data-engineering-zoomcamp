"""Check failure modes that could silently lose or duplicate API rows."""
import json
import unittest
from decimal import Decimal

from taxi_pipeline import pages, typed_record


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.content = json.dumps(payload).encode()

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.pages = []

    def get(self, url, params, timeout):
        self.pages.append(params["page"])
        return Response(next(self.responses))


class PaginationTests(unittest.TestCase):
    def test_short_nonempty_page_does_not_terminate(self):
        client = Client([[{"id": 1}], [{"id": 2}], []])
        manifest = []
        self.assertEqual(list(pages(client, manifest)), [[{"id": 1}], [{"id": 2}]])
        self.assertEqual(client.pages, [1, 2, 3])
        self.assertEqual(manifest[-1]["rows"], 0)

    def test_empty_first_page_fails(self):
        with self.assertRaisesRegex(ValueError, "first page"):
            list(pages(Client([[]]), []))

    def test_repeated_page_fails(self):
        with self.assertRaisesRegex(ValueError, "Repeated page"):
            list(pages(Client([[{"id": 1}], [{"id": 1}]]), []))

    def test_unexpected_response_shape_fails(self):
        with self.assertRaisesRegex(ValueError, "not a list"):
            list(pages(Client([{"error": "maintenance"}]), []))

    def test_safety_bound_does_not_claim_complete_snapshot(self):
        with self.assertRaisesRegex(ValueError, "without the required empty"):
            list(pages(Client([[{"id": 1}]]), [], max_pages=1))

    def test_money_is_exact_decimal(self):
        row = typed_record({"Tip_Amt": 0.1, "mta_tax": None,
                            "Trip_Pickup_DateTime": "2009-06-01 00:00:00"})
        self.assertEqual(row["tip_amt"], Decimal("0.1"))
        self.assertIsNone(row["mta_tax"])
        self.assertEqual(row["trip_pickup_datetime"].year, 2009)


if __name__ == "__main__":
    unittest.main()
