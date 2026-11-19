"""Minimal, traceable SEC EDGAR Company Facts client.

This module intentionally contains no financial forecast or investment advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_BASE = "https://data.sec.gov/api/xbrl/companyfacts"

# Priority is only used to break ties between equivalent observations.
# It does not imply that every company's taxonomy uses the same concept.
METRIC_TAGS: dict[str, tuple[str, str]] = {
    "revenue": (
        "USD",
        "RevenueFromContractWithCustomerExcludingAssessedTax|"
        "RevenueFromContractWithCustomerIncludingAssessedTax|Revenues|SalesRevenueNet",
    ),
    "gross_profit": ("USD", "GrossProfit"),
    "operating_income": ("USD", "OperatingIncomeLoss"),
    "net_income": ("USD", "NetIncomeLoss"),
    "operating_cash_flow": ("USD", "NetCashProvidedByUsedInOperatingActivities"),
    "diluted_eps": ("USD/shares", "EarningsPerShareDiluted"),
}


class SECError(RuntimeError):
    """A recoverable SEC request, decoding, or mapping error."""


@dataclass(frozen=True)
class Company:
    ticker: str
    cik: int
    name: str


class SECClient:
    """Small HTTP client with a required identifying User-Agent and retries."""

    def __init__(self, user_agent: str, *, timeout: float = 15, retries: int = 2):
        if not user_agent.strip() or "example.com" in user_agent.lower():
            raise SECError("Set SEC_USER_AGENT to a genuine name and contact email.")
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries

    def get_json(self, url: str) -> Any:
        request = Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )
        for attempt in range(self.retries + 1):
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return json.load(response)
            except HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise SECError(f"SEC returned HTTP {exc.code} for {url}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == self.retries:
                    raise SECError(f"Could not reach SEC at {url}: {exc}") from exc
            except (ValueError, UnicodeDecodeError) as exc:
                raise SECError(f"SEC returned invalid JSON at {url}") from exc
            time.sleep(0.5 * (2**attempt))
        raise SECError("SEC request failed")

    def resolve_company(self, ticker: str) -> Company:
        return resolve_company(self.get_json(TICKERS_URL), ticker)

    def get_companyfacts(self, cik: int) -> tuple[dict[str, Any], str]:
        url = f"{COMPANY_FACTS_BASE}/CIK{cik:010d}.json"
        data = self.get_json(url)
        if not isinstance(data, dict) or "facts" not in data:
            raise SECError("SEC Company Facts response is missing the facts object")
        return data, url


def resolve_company(payload: Any, ticker: str) -> Company:
    """Resolve SEC's JSON dictionary rows without relying on row indexes."""
    rows = payload.values() if isinstance(payload, dict) else payload
    if not isinstance(rows, (list, tuple)) and not hasattr(rows, "__iter__"):
        raise SECError("Unexpected SEC ticker mapping format")
    symbol = ticker.strip().upper()
    if not symbol:
        raise SECError("Ticker must not be empty")
    for row in rows:
        if isinstance(row, dict) and str(row.get("ticker", "")).upper() == symbol:
            try:
                return Company(symbol, int(row["cik_str"]), str(row["title"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise SECError("Invalid CIK mapping returned by SEC") from exc
    raise SECError(f"Ticker {symbol!r} was not found in the SEC mapping")


def latest_reported_fact(
    companyfacts: dict[str, Any], tags: str, unit: str, as_of: date | None = None
) -> dict[str, Any] | None:
    """Pick latest period-end fact, restricted to filings known by the cutoff.

    The period start/end are preserved so 10-Q year-to-date amounts are not
    accidentally described as standalone quarterly values.
    """
    taxonomy = companyfacts.get("facts", {}).get("us-gaap", {})
    matches: list[tuple[tuple[str, str, int], dict[str, Any]]] = []
    for priority, tag in enumerate(tags.split("|")):
        concept = taxonomy.get(tag, {})
        records = concept.get("units", {}).get(unit, [])
        for row in records:
            if row.get("form") not in ("10-K", "10-Q"):
                continue
            if not all(k in row for k in ("val", "end", "filed", "accn")):
                continue
            try:
                filed = date.fromisoformat(row["filed"])
                end = date.fromisoformat(row["end"])
                if "start" in row:
                    date.fromisoformat(row["start"])
            except (TypeError, ValueError):
                continue
            if as_of is not None and filed > as_of:
                continue
            if not isinstance(row["val"], (int, float)) or isinstance(row["val"], bool):
                continue
            output = {
                "value": row["val"],
                "unit": unit,
                "concept": f"us-gaap:{tag}",
                "period_start": row.get("start"),
                "period_end": end.isoformat(),
                "filed": filed.isoformat(),
                "form": row["form"],
                "fiscal_year": row.get("fy"),
                "fiscal_period": row.get("fp"),
                "accession": row["accn"],
                "frame": row.get("frame"),
            }
            matches.append(((end.isoformat(), filed.isoformat(), -priority), output))
    return max(matches, key=lambda item: item[0])[1] if matches else None


def build_snapshot(
    company: Company,
    companyfacts: dict[str, Any],
    source_url: str,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Generate a research-ready, explicitly sourced JSON snapshot."""
    metrics = {
        name: latest_reported_fact(companyfacts, tags, unit, as_of)
        for name, (unit, tags) in METRIC_TAGS.items()
    }
    return {
        "schema_version": "0.1.0",
        "ticker": company.ticker,
        "cik": f"{company.cik:010d}",
        "company_name": companyfacts.get("entityName", company.name),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": as_of.isoformat() if as_of else None,
        "is_demo": False,
        "source": {
            "provider": "SEC EDGAR",
            "kind": "companyfacts",
            "url": source_url,
            "ticker_mapping_url": TICKERS_URL,
        },
        "metrics": metrics,
        "missing_metrics": [name for name, record in metrics.items() if record is None],
        "warnings": [
            "SEC US-GAAP taxonomy varies across issuers.",
            "10-Q metrics may contain year-to-date periods; inspect start/end dates.",
            "No investment recommendation or growth inference is produced.",
        ],
    }
