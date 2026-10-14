#!/usr/bin/env python3
"""Query the AMSAT Live OSCAR Satellite Status API for recent activity.

https://www.amsat.org/status/  (human page)
https://www.amsat.org/status/api/docs.php  (API docs)
"""

import json
import urllib.request

from sat_naming import parse_sat_name

STATUS_API = "https://www.amsat.org/status/api/v1"

# Report values that correspond to the status page's blue "Sat/Mode Active" cells.
ACTIVE_STATUSES = {"Heard", "Crew Active"}


def fetch_summary(hours=48, timeout=15):
    """Fetch the activity summary for the last `hours` hours.

    Returns the API's 'data' list: one row per (satellite, report status)
    combination seen in the window, each with report_count and
    latest_reported_time.
    """
    url = f"{STATUS_API}/summary.php?hours={hours}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.load(response)
    return payload.get("data", [])


def active_base_designations(summary_rows):
    """Return the set of base designations (e.g. 'AO-7', 'ISS') that have
    at least one 'Heard' or 'Crew Active' report in the summary window.

    The API reports per mode (e.g. 'AO-7_[U/v]', 'ISS_[FM]'); any active
    mode counts the base satellite as active.
    """
    active = set()
    for row in summary_rows:
        if row.get("report") in ACTIVE_STATUSES:
            api_name = row.get("name", "")
            base = api_name.split("_[")[0].split("[")[0]
            if base:
                active.add(base.upper())
    return active


def is_active(sat_name, active_bases):
    """Check whether a satellites.txt-style designation (e.g. 'AO-7[B]',
    'ISS-FM', 'FO-29') is active, by comparing its base designation.
    """
    base, _ = parse_sat_name(sat_name)
    return base.upper() in active_bases
