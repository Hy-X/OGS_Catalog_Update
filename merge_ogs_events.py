#!/usr/bin/env python3
"""
merge_ogs_events.py

Merges newly queried OGS earthquake events into the master dataset file `ogs_events_all_complete.csv`.

Features:
- Initializes `ogs_events_all_complete.csv` from `wichita_ogs_ou_edu_archive/complete.csv` if it doesn't exist yet.
- Deduplicates events by event_id (or origintime/coordinates composite key for unindexed historical events).
- Updates existing records if newer/revised attributes (e.g. status, error bounds) are available.
- Sorts all events chronologically (oldest first).
- Re-indexes `objectid` sequentially starting at 1 for the oldest event up to N for the newest event.
- Performs atomic file replacement (`.tmp` -> `ogs_events_all_complete.csv`) to guarantee process/web safety.
"""

import sys
import os
import csv
import argparse

# Default master output CSV file path
MASTER_CSV_PATH = "ogs_events_all_complete.csv"

# Historical archive seed CSV file path
SEED_CSV_PATH = os.path.join("wichita_ogs_ou_edu_archive", "complete.csv")

# Standard CSV column fields matching complete.csv
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


def make_event_key(row):
    """
    Generates a unique key for deduplicating events.
    Uses event_id if present and valid; otherwise uses (origintime, latitude, longitude).
    """
    eid = row.get("event_id")
    if eid and eid != "None" and str(eid).strip():
        return ("id", str(eid).strip().lower())
    return ("composite", row.get("origintime"), str(row.get("latitude")), str(row.get("longitude")))


def load_csv_rows(filepath):
    """
    Reads CSV rows into a list of dictionaries if file exists.
    """
    if not os.path.exists(filepath):
        return []
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def merge_events(input_files=None, extra_rows=None, master_path=MASTER_CSV_PATH, seed_path=SEED_CSV_PATH, quiet=False):
    """
    Merges input events into the master dataset file.
    """
    master_path = os.path.abspath(master_path)
    seed_path = os.path.abspath(seed_path)

    # 1. Determine base dataset source
    if os.path.exists(master_path):
        if not quiet:
            print(f"[*] Loading existing master catalog: {master_path}")
        base_rows = load_csv_rows(master_path)
    elif os.path.exists(seed_path):
        if not quiet:
            print(f"[*] Initializing master catalog from seed: {seed_path}")
        base_rows = load_csv_rows(seed_path)
    else:
        if not quiet:
            print("[*] No existing master or seed catalog found. Starting fresh.")
        base_rows = []

    # 2. Build catalog dictionary indexed by event key
    catalog = {}
    for row in base_rows:
        key = make_event_key(row)
        catalog[key] = row

    initial_count = len(catalog)

    # 3. Collect new incoming rows from files or directly passed rows
    incoming_rows = []
    if input_files:
        for input_file in input_files:
            abs_input = os.path.abspath(input_file)
            if os.path.exists(abs_input):
                if not quiet:
                    print(f"[*] Reading incoming events from: {abs_input}")
                rows = load_csv_rows(abs_input)
                incoming_rows.extend(rows)

    if extra_rows:
        incoming_rows.extend(extra_rows)

    # 4. Merge incoming rows (update existing or append new)
    added_count = 0
    updated_count = 0

    for row in incoming_rows:
        key = make_event_key(row)
        if key in catalog:
            # Update non-None/valid attributes
            existing_item = catalog[key]
            for field in CSV_FIELDS:
                if field == "objectid":
                    continue
                new_val = row.get(field)
                if new_val is not None and new_val != "None" and str(new_val).strip():
                    existing_item[field] = new_val
            updated_count += 1
        else:
            catalog[key] = row
            added_count += 1

    # 5. Sort merged events chronologically (origintime ascending)
    merged_events = list(catalog.values())
    merged_events.sort(key=lambda r: r.get("origintime") or "")

    # 6. Reassign sequential objectid (1 for oldest up to N for newest)
    for idx, row in enumerate(merged_events, start=1):
        row["objectid"] = str(idx)

    # 7. Write master dataset atomically
    os.makedirs(os.path.dirname(master_path), exist_ok=True)
    temp_master = master_path + ".tmp"

    with open(temp_master, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(merged_events)

    os.replace(temp_master, master_path)

    if not quiet:
        print(f"[+] Master catalog successfully updated: {master_path}")
        print(f"    - Initial events: {initial_count}")
        print(f"    - New events added: {added_count}")
        print(f"    - Existing events updated: {updated_count}")
        print(f"    - Total events in master catalog: {len(merged_events)}")

    # Automatically update self-contained HTML page
    try:
        from build_self_contained_html import build_self_contained_html
        build_self_contained_html(quiet=quiet)
    except Exception as html_err:
        if not quiet:
            print(f"[!] Warning: Could not update self-contained HTML: {html_err}")

    return master_path


def main():
    parser = argparse.ArgumentParser(
        description="Merge new OGS earthquake events into ogs_events_all_complete.csv master dataset."
    )
    parser.add_argument(
        "--input",
        "-i",
        nargs="+",
        default=["ogs_events_past_30days.csv", "ogs_events_past_7days.csv", "ogs_events_past_1days.csv"],
        help="Input CSV file(s) to merge into master dataset.",
    )
    parser.add_argument(
        "--master",
        "-m",
        type=str,
        default=MASTER_CSV_PATH,
        help=f"Path to master output CSV file (default: {MASTER_CSV_PATH}).",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress console output messages.",
    )

    args = parser.parse_args()

    # Filter input files to only those that exist
    valid_inputs = [f for f in args.input if os.path.exists(f)]
    if not valid_inputs and not os.path.exists(args.master):
        print(f"[!] No valid input files or master catalog found.", file=sys.stderr)
        sys.exit(1)

    merge_events(input_files=valid_inputs, master_path=args.master, quiet=args.quiet)


if __name__ == "__main__":
    main()
