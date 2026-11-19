"""CLI for the first NEXUS ALPHA SEC EDGAR data slice."""

from __future__ import annotations

import argparse
from datetime import date
import json
import os
from pathlib import Path
import sys

from .sec import SECClient, SECError, build_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="nexus-alpha", description="Fetch traceable SEC EDGAR Company Facts"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Fetch one issuer's reported US-GAAP facts")
    fetch.add_argument("ticker", help="US stock ticker, e.g. NVDA")
    fetch.add_argument("--output", default=None, help="Output JSON file")
    fetch.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)

    if args.command != "fetch":
        parser.error("Unknown command")
    try:
        client = SECClient(os.environ.get("SEC_USER_AGENT", ""))
        company = client.resolve_company(args.ticker)
        facts, url = client.get_companyfacts(company.cik)
        snapshot = build_snapshot(company, facts, url, as_of=args.as_of)
        output = Path(args.output or f"output/{company.ticker.lower()}.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {company.ticker} from SEC EDGAR to {output}")
        print(f"Metrics: {sum(v is not None for v in snapshot['metrics'].values())} present / {len(snapshot['metrics'])} total")
        if snapshot["missing_metrics"]:
            print("Unavailable concepts: " + ", ".join(snapshot["missing_metrics"]))
        return 0
    except SECError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
