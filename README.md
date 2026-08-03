# OGS Earthquake Catalog Update & Automation Suite

An automated workflow and Python toolkit for fetching, filtering, deduplicating, and maintaining the **Oklahoma Geological Survey (OGS)** earthquake catalog via the **USGS / OGS FDSN Web Services API**.

---

## 📌 Overview

This suite maintains up-to-date seismic event datasets for Oklahoma by interacting directly with the USGS/OGS FDSN Event Web Service (`https://earthquake.usgs.gov/fdsnws/event/1/query`). It queries events within the geographical boundaries of Oklahoma, isolates official OGS seismic event records, enriches events with origin detail metrics, and atomically updates the master catalog.

### Key Features

- **Automated FDSN WS API Integration**: Fetches real-time seismic event data within the Oklahoma bounding box ($\text{Lat: } 33.5^\circ \text{ to } 37.1^\circ$, $\text{Lon: } -103.1^\circ \text{ to } -94.3^\circ$).
- **Strict OGS Event Identification**: Filters features matching official OGS ID patterns (`ogs****????`, e.g., `ogs2024ahys`).
- **Robust Merging & Deduplication**:
  - Primary key matching by `event_id` (or spatial-temporal composite keys for unindexed events).
  - Updates existing records with revised parameters (e.g., status, origin error bounds).
  - Maintains strict chronological ordering (oldest event first).
  - Sequential re-indexing of `objectid` starting at `1` for the oldest event up to $N$ for the newest event.
- **Threaded Origin Details Retrieval**: Utilizes concurrent workers (`ThreadPoolExecutor`) to extract location errors (`err_lat`, `err_lon`, `err_depth`, `err_origintime`), origin source, and event status.
- **Process & Web Safety**: Uses atomic file operations (writes to `.tmp` files before renaming) to eliminate race conditions during concurrent web client downloads or scheduled updates.
- **Flexible Execution Modes**: Supports standalone single window queries (1-day, 7-day, 30-day) or automated bulk updates across all timeframes.

---

## 📂 Repository Structure

| File / Directory | Description |
| :--- | :--- |
| [query_ogs_events_automatic.py](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/query_ogs_events_automatic.py) | **Primary Automated CLI Tool**: Queries USGS API, parses details, filters OGS events, and auto-merges outputs. |
| [merge_ogs_events.py](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/merge_ogs_events.py) | **Master Catalog Merger**: Merges newly queried CSV files into the master dataset with deduplication and re-indexing. |
| [query_ogs_event_past_1day.py](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/query_ogs_event_past_1day.py) | Queries and updates the 24-hour dataset ([ogs_events_past_1days.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_past_1days.csv)). |
| [query_ogs_event_past_7days.py](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/query_ogs_event_past_7days.py) | Queries and updates the 7-day dataset ([ogs_events_past_7days.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_past_7days.csv)). |
| [query_ogs_event_past_30days.py](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/query_ogs_event_past_30days.py) | Queries and updates the 30-day dataset ([ogs_events_past_30days.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_past_30days.csv)). |
| [ogs_events_all_complete.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_all_complete.csv) | **Master Catalog Dataset**: Complete, chronologically sorted, deduplicated historical OGS event database. |
| [wichita_ogs_ou_edu_archive/](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/wichita_ogs_ou_edu_archive) | Historical seed archive containing seed catalog data (`complete.csv`), HTML interfaces, and legacy scripts. |

---

## 📊 Catalog CSV Data Schema

All CSV files follow the standard schema matching the historical `complete.csv` catalog:

| Column Name | Type | Description |
| :--- | :--- | :--- |
| `objectid` | Integer | Sequential index starting from `1` (oldest event) to $N$ (newest event). |
| `event_id` | String | Official OGS / USGS Event Identifier (e.g., `ogs2024ahys`). |
| `origintime` | String | Event origin UTC timestamp formatted as `YYYY-MM-DD HH:MM:SS`. |
| `magnitude` | Float | Event magnitude value. |
| `magnitude_source` | String | Network code / source of magnitude calculation (e.g., `ok`, `us`). |
| `max_mmi` | Float / String | Maximum Modified Mercalli Intensity. |
| `latitude` | Float | Event epicenter latitude (decimal degrees). |
| `longitude` | Float | Event epicenter longitude (decimal degrees). |
| `depth_km` | Float | Event focal depth in kilometers. |
| `err_lat` | Float | Estimated latitude uncertainty (km / degrees). |
| `err_lon` | Float | Estimated longitude uncertainty (km / degrees). |
| `err_depth` | Float | Estimated focal depth uncertainty (km). |
| `err_origintime` | Float | Estimated origin time uncertainty (seconds). |
| `state` | String | State name (`Oklahoma`). |
| `county` | String | Nearest county / location parsed from place description. |
| `status` | String | Review status (`reviewed`, `automatic`). |

---

## 🚀 Getting Started & Usage

### 1. Requirements

- Python 3.7+
- Standard library modules (`urllib`, `json`, `csv`, `re`, `argparse`, `concurrent.futures`) — no third-party dependencies required.

### 2. Automated Full Update

To update all timeframe datasets (1-day, 7-day, 30-day) and automatically merge new events into the master dataset [ogs_events_all_complete.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_all_complete.csv):

```bash
python3 query_ogs_events_automatic.py --all
```

### 3. Querying Specific Time Ranges

Query events for a custom number of past days (e.g., past 14 days):

```bash
python3 query_ogs_events_automatic.py --days 14 --output ogs_events_past_14days.csv
```

Query events for a specific UTC date range:

```bash
python3 query_ogs_events_automatic.py --start 2024-01-01 --end 2024-06-01 --output custom_range.csv
```

### 4. Merging Incoming Datasets

To merge any external or queried CSV file into the master catalog manually:

```bash
python3 merge_ogs_events.py --input custom_range.csv
```

To initialize or rebuild [ogs_events_all_complete.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/ogs_events_all_complete.csv) directly from the seed catalog in [wichita_ogs_ou_edu_archive/complete.csv](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/wichita_ogs_ou_edu_archive/complete.csv):

```bash
python3 merge_ogs_events.py
```

### 5. Timeframe Queries

Run individual dedicated querying scripts for web services or scheduled cron jobs:

```bash
python3 query_ogs_event_past_1day.py    # Generates ogs_events_past_1days.csv
python3 query_ogs_event_past_7days.py   # Generates ogs_events_past_7days.csv
python3 query_ogs_event_past_30days.py  # Generates ogs_events_past_30days.csv
```

---

## 🤖 GitHub / Gitea Actions Workflow

The repository includes an automated workflow defined in [.github/workflows/update_catalog.yml](file:///Users/hongyuxiao/Hongyu_File/Gitea_Archive/OGS_Catalog_Update/.github/workflows/update_catalog.yml):

- **Schedule**: Automatically runs every 6 hours (`0 */6 * * *`).
- **Manual Trigger**: Can be manually triggered via `workflow_dispatch`.
- **Action**: Executes `python3 query_ogs_events_automatic.py --all`, detects changes in catalog CSV files, and commits/pushes updates automatically back to the repository.

---

## ⚙️ Cron Automation (Production Server Deployment)

To keep the catalog continuously updated on a local server, set up a cron job:

```cron
# Run catalog update every hour
0 * * * * cd /path/to/OGS_Catalog_Update && python3 query_ogs_events_automatic.py --all > /dev/null 2>&1
```

---

## 📁 Historical Archive

The `wichita_ogs_ou_edu_archive/` directory contains legacy data and original archive files used as baseline seeds:
- `complete.csv`: Baseline seed catalog containing historical OGS events.
- `events.html`: Reference HTML monitoring dashboard page.
- `resultsfile.csv`: Raw query results archive.
- `stations_updated.csv` & `updated_stations.csv`: Historical seismic station metadata references.

