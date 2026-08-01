#!/usr/bin/env python3
"""
Trigger a pipeline run against the deployed API.

Written for Render's Cron Job service. The backend image is python:3.12-slim,
which ships with neither curl nor wget, so this uses the standard library
rather than requiring an extra apt layer for a single HTTP call.

Environment:
    API_URL         base URL of the deployed API, e.g.
                    https://job-market-pulse.onrender.com/api/v1
    PIPELINE_TOKEN  shared secret; sent as the X-Pipeline-Token header

Exit codes:
    0  pipeline completed
    1  request failed, or the run reported a dead source
"""

import json
import os
import sys
import urllib.error
import urllib.request

# A full run scrapes 19 boards and takes ~4.5 minutes. On the free tier the
# service may also be spun down, adding a 30-50s cold start before the first
# byte, so the timeout has to cover both with room to spare.
TIMEOUT_SECONDS = 900


def main() -> int:
    base = os.environ.get("API_URL", "").rstrip("/")
    token = os.environ.get("PIPELINE_TOKEN", "")

    if not base:
        print("ERROR: API_URL is not set", file=sys.stderr)
        return 1
    if not token:
        print("ERROR: PIPELINE_TOKEN is not set", file=sys.stderr)
        return 1

    url = f"{base}/pipeline/run"
    request = urllib.request.Request(
        url,
        method="POST",
        headers={"X-Pipeline-Token": token, "Content-Length": "0"},
    )

    print(f"POST {url}")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 401 here almost always means the cron job's token drifted from the
        # web service's after one of them was rotated.
        print(f"ERROR: HTTP {e.code} — {e.read().decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    stats = payload.get("stats", {})
    print(
        f"scraped={stats.get('scraped')} new={stats.get('new_jobs')} "
        f"updated={stats.get('updated')} skills_linked={stats.get('skills_linked')}"
    )
    for source, summary in (stats.get("sources") or {}).items():
        failed = summary.get("companies_failed") or []
        note = f" FAILED: {failed}" if failed else ""
        print(f"  {source}: {summary.get('jobs')} jobs{note}")

    # Surface coverage rot as a failed cron run rather than a silent success.
    failed_sources = stats.get("sources_failed") or []
    if failed_sources:
        print(f"ERROR: source(s) returned nothing: {failed_sources}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
