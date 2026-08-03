#!/usr/bin/env python3
"""
query_ogs_event_past_7days.py

Fetches Oklahoma Geological Survey (OGS) earthquake events for the past 7 days (or custom time window)
from the USGS / OGS FDSN WS event web services based on the logic in OGS_Moni_Dev_USGS-hotpatch.html.

Exports the queried events into CSV format matching wichita_ogs_ou_edu_archive/complete.csv,
specifically filtering for event IDs matching the ogs****???? pattern (e.g. ogs2024ahys).
"""

import sys
import os
import re
import csv
import json
import argparse
import urllib.request
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

# Default Oklahoma geographical bounding box used by OGS dashboards
OK_MIN_LAT = 33.5
OK_MAX_LAT = 37.1
OK_MIN_LNG = -103.1
OK_MAX_LNG = -94.3

# USGS / OGS FDSN Event Web Service API URL
FDSN_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# CSV Column headers matching complete.csv format
CSV_FIELDS = [
    "objectid",
    "event_id",
    "origintime",
    "magnitude",
    "magnitude_source",
    "max_mmi",
    "latitude",
    "longitude",
    "depth_km",
    "err_lat",
    "err_lon",
    "err_depth",
    "err_origintime",
    "state",
    "county",
    "status",
]


def parse_place(place_str):
    """
    Parses state and county/location from USGS place description string.
    Example: '5 km SSE of Amber, Oklahoma' -> state='Oklahoma', county='Amber'
    """
    state = "Oklahoma"
    county = "None"
    if not place_str:
        return state, county

    parts = [p.strip() for p in place_str.split(",")]
    if len(parts) >= 2:
        state = parts[-1]
        location_part = parts[0]
        if " of " in location_part:
            county = location_part.split(" of ")[-1].strip()
        else:
            county = location_part.strip()
    else:
        state = place_str.strip()

    return state, county


def fetch_event_detail(item, quiet=False):
    """
    Fetches origin product details for an individual feature to get detailed
    location errors, origin source, and status if available.
    """
    object_id, event_id, feature = item
    props = feature.get("properties", {})
    geom = feature.get("geometry", {})
    coords = geom.get("coordinates", [None, None, None])

    # Origin time formatted as YYYY-MM-DD HH:MM:SS in UTC
    time_ms = props.get("time")
    if time_ms is not None:
        dt = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
        origintime = dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        origintime = "None"

    # Magnitude
    mag = props.get("mag")
    magnitude = str(mag) if mag is not None else "None"

    # Magnitude Source & Net Code
    net_code = str(props.get("net", "")).lower()
    mag_source = "OGS" if net_code in ("ok", "ogs") else props.get("magSource", "OGS").upper()

    # MMI (intensity)
    mmi = props.get("mmi")
    max_mmi = str(mmi) if mmi is not None else "None"

    # Coordinates
    longitude = str(coords[0]) if coords[0] is not None else "None"
    latitude = str(coords[1]) if coords[1] is not None else "None"
    depth_km = str(coords[2]) if len(coords) > 2 and coords[2] is not None else "None"

    err_lat = "None"
    err_lon = "None"
    err_depth = "None"
    err_origintime = "None"

    raw_status = props.get("status", "reviewed")
    status = raw_status.capitalize() if isinstance(raw_status, str) else "None"

    # Detailed origin query if detail link exists
    detail_url = props.get("detail")
    if detail_url:
        try:
            req = urllib.request.Request(detail_url, headers={"User-Agent": "OGS-Python-Query/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                detail_data = json.loads(resp.read().decode("utf-8"))
                products = detail_data.get("properties", {}).get("products", {})
                origins = products.get("origin", [])
                if origins:
                    o_props = origins[0].get("properties", {})
                    if o_props.get("latitude-error"):
                        err_lat = str(round(float(o_props["latitude-error"]), 4))
                    if o_props.get("longitude-error"):
                        err_lon = str(round(float(o_props["longitude-error"]), 4))
                    if o_props.get("vertical-error"):
                        err_depth = str(round(float(o_props["vertical-error"]), 4))
                    if o_props.get("time-error"):
                        err_origintime = str(round(float(o_props["time-error"]), 4))
                    if o_props.get("magnitude-source"):
                        ms = str(o_props["magnitude-source"]).upper()
                        mag_source = "OGS" if ms in ("OK", "OGS") else ms
                    if o_props.get("review-status"):
                        status = str(o_props["review-status"]).capitalize()
        except Exception:
            pass  # Fall back to standard GeoJSON properties on detail fetch error

    place = props.get("place", "")
    state, county = parse_place(place)

    return {
        "objectid": str(object_id),
        "event_id": event_id,
        "origintime": origintime,
        "magnitude": magnitude,
        "magnitude_source": mag_source,
        "max_mmi": max_mmi,
        "latitude": latitude,
        "longitude": longitude,
        "depth_km": depth_km,
        "err_lat": err_lat,
        "err_lon": err_lon,
        "err_depth": err_depth,
        "err_origintime": err_origintime,
        "state": state,
        "county": county,
        "status": status,
    }


def query_ogs_events(days=7, start_str=None, end_str=None, min_mag=None, max_mag=None, output_file="ogs_events_past_7days.csv", quiet=False):
    """
    Queries FDSN WS API for Oklahoma events and writes matching ogs****???? records to CSV.
    """
    if not end_str:
        end_dt = datetime.now(timezone.utc)
        end_str = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    if not start_str:
        end_dt = datetime.strptime(end_str.split(".")[0], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

    # Build FDSN API request URL
    params = [
        "format=geojson",
        f"starttime={start_str}",
        f"endtime={end_str}",
        f"minlatitude={OK_MIN_LAT}",
        f"maxlatitude={OK_MAX_LAT}",
        f"minlongitude={OK_MIN_LNG}",
        f"maxlongitude={OK_MAX_LNG}",
    ]
    if min_mag is not None:
        params.append(f"minmagnitude={min_mag}")
    if max_mag is not None:
        params.append(f"maxmagnitude={max_mag}")

    query_url = f"{FDSN_API_URL}?{'&'.join(params)}"

    if not quiet:
        print(f"[*] Querying OGS event API: {query_url}")

    req = urllib.request.Request(query_url, headers={"User-Agent": "OGS-Python-Query/1.0"})
    try:
        with urllib.request.urlopen(req) as resp:
            geojson_data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[!] Error querying FDSN API: {e}", file=sys.stderr)
        sys.exit(1)

    features = geojson_data.get("features", [])
    if not quiet:
        print(f"[*] Total earthquake features retrieved from API: {len(features)}")

    # Filter for ogs****???? ID format (e.g. ogs2024ahys)
    # USGS IDs use net code 'ok' (e.g., ok2024ahys), which map 1-to-1 to OGS IDs (ogs2024ahys)
    ogs_pattern = re.compile(r"^ogs\d{4}[a-zA-Z0-9]{4}$", re.IGNORECASE)
    matched_items = []

    for index, f in enumerate(features, start=1):
        props = f.get("properties", {})
        raw_id = f.get("id") or props.get("event_id") or props.get("id") or ""
        if not raw_id:
            continue

        # Map 'ok' prefix to 'ogs' prefix for Oklahoma catalog events
        if raw_id.lower().startswith("ok"):
            formatted_id = "ogs" + raw_id[2:]
        else:
            formatted_id = raw_id

        if ogs_pattern.match(formatted_id):
            matched_items.append((index, formatted_id, f))

    if not quiet:
        print(f"[*] Filtered {len(matched_items)} events matching ogs****???? format.")

    if not matched_items:
        print("[!] No events found matching the target criteria.")

    # Fetch origin product details concurrently for accuracy
    if not quiet:
        print("[*] Processing event detail attributes...")

    with ThreadPoolExecutor(max_workers=10) as executor:
        event_rows = list(executor.map(lambda item: fetch_event_detail(item, quiet), matched_items))

    # Sort events by origintime ascending (oldest first)
    event_rows.sort(key=lambda r: r["origintime"])

    # Reassign sequential objectid starting at 1 for the oldest event
    for idx, r in enumerate(event_rows, start=1):
        r["objectid"] = str(idx)

    # Write output to CSV file matching complete.csv structure
    output_path = os.path.abspath(output_file)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(event_rows)

    if not quiet:
        print(f"[+] Successfully exported {len(event_rows)} events to '{output_path}'.")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Query OGS earthquake events for the past 7 days and export to complete.csv formatted CSV."
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=7,
        help="Number of past days to query (default: 7).",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start time ISO string (e.g. 2026-07-27T00:00:00). Overrides --days.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End time ISO string (e.g. 2026-08-03T23:59:59). Default: current time UTC.",
    )
    parser.add_argument(
        "--minmag",
        type=float,
        default=None,
        help="Minimum magnitude filter.",
    )
    parser.add_argument(
        "--maxmag",
        type=float,
        default=None,
        help="Maximum magnitude filter.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="ogs_events_past_7days.csv",
        help="Output CSV filename (default: ogs_events_past_7days.csv).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output messages.",
    )

    args = parser.parse_args()

    query_ogs_events(
        days=args.days,
        start_str=args.start,
        end_str=args.end,
        min_mag=args.minmag,
        max_mag=args.maxmag,
        output_file=args.output,
        quiet=args.quiet,
    )


if __name__ == "__main__":
    main()
