"""Offline tests use synthetic facts; they do not represent Nvidia financials."""

from datetime import date
import io
import json
import unittest
from unittest.mock import patch

from nexus_alpha.sec import (
    Company,
    SECClient,
    SECError,
    build_snapshot,
    latest_reported_fact,
    resolve_company,
)


FAKE_COMPANYFACTS = {
    "entityName": "Example Chip Company (synthetic fixture)",
    "facts": {
        "us-gaap": {
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "units": {
                    "USD": [
                        {
                            "val": 100,
                            "start": "2024-01-01",
                            "end": "2024-12-31",
                            "filed": "2025-02-10",
                            "form": "10-K",
                            "accn": "0000000000-25-000001",
                            "fy": 2024,
                            "fp": "FY",
                        },
                        {
                            "val": 40,
                            "start": "2025-01-01",
                            "end": "2025-03-31",
                            "filed": "2025-05-10",
                            "form": "10-Q",
                            "accn": "0000000000-25-000002",
                            "fy": 2025,
                            "fp": "Q1",
                        },
                        {
                            "val": 41,
                            "start": "2025-01-01",
                            "end": "2025-03-31",
                            "filed": "2025-06-10",
                            "form": "10-Q",
                            "accn": "0000000000-25-000003",
                        },
                    ]
                }
            },
            "GrossProfit": {
                "units": {
                    "USD": [
                        {
                            "val": 15,
                            "start": "2025-01-01",
                            "end": "2025-03-31",
                            "filed": "2025-05-10",
                            "form": "10-Q",
                            "accn": "0000000000-25-000002",
                        }
                    ]
                }
            },
        }
    },
}


class TestSECNormalization(unittest.TestCase):
    def test_resolve_symbol_case_insensitive(self):
        company = resolve_company({"0": {"ticker": "NVDA", "cik_str": 1045810, "title": "NVIDIA"}}, "nvda")
        self.assertEqual(company.cik, 1045810)
        self.assertEqual(company.ticker, "NVDA")

    def test_unknown_ticker(self):
        with self.assertRaisesRegex(SECError, "not found"):
            resolve_company([], "unknown")

    def test_most_recent_filing_for_same_period(self):
        latest = latest_reported_fact(
            FAKE_COMPANYFACTS,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
        )
        self.assertEqual(latest["value"], 41)
        self.assertEqual(latest["accession"], "0000000000-25-000003")
        self.assertEqual(latest["period_start"], "2025-01-01")

    def test_as_of_filters_future_disclosures(self):
        old = latest_reported_fact(
            FAKE_COMPANYFACTS,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            as_of=date(2025, 2, 12),
        )
        self.assertEqual(old["value"], 100)
        newer = latest_reported_fact(
            FAKE_COMPANYFACTS,
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "USD",
            as_of=date(2025, 5, 11),
        )
        self.assertEqual(newer["value"], 40)

    def test_snapshot_has_provenance_and_explicit_nulls(self):
        snapshot = build_snapshot(
            Company("EXMP", 999, "Example"),
            FAKE_COMPANYFACTS,
            "https://data.sec.gov/example.json",
        )
        self.assertEqual(snapshot["source"]["provider"], "SEC EDGAR")
        self.assertEqual(snapshot["metrics"]["gross_profit"]["unit"], "USD")
        self.assertIsNone(snapshot["metrics"]["net_income"])
        self.assertIn("net_income", snapshot["missing_metrics"])
        self.assertFalse(snapshot["is_demo"])

    def test_invalid_example_user_agent_is_rejected(self):
        with self.assertRaisesRegex(SECError, "genuine"):
            SECClient("NexusAlpha somebody@example.com")

    def test_http_json_client_passes_identifying_header(self):
        class FakeResponse(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        fake = FakeResponse(json.dumps({"ok": True}).encode("utf-8"))
        with patch("nexus_alpha.sec.urlopen", return_value=fake) as urlopen_mock:
            client = SECClient("NexusAlpha Jane jane@valid.test")
            self.assertEqual(client.get_json("https://data.sec.gov/test"), {"ok": True})
            request = urlopen_mock.call_args.args[0]
            self.assertIn("Jane", request.get_header("User-agent"))


if __name__ == "__main__":
    unittest.main()
