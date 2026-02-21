# MRMS MESH Historical Backfill

Fills the ~90-day gap between delayed NOAA Storm Events and real-time
NEXRAD detections by fetching historical MRMS MESH grids from the Iowa
State Mesonet archive.

## Quick Start

```bash
# Inside the container (or with the conda env active):
python -m src.cli.mrms_backfill --days 90
```

## How It Works

1. **Fetch** — Downloads MRMS MESH grib2 files from the Iowa State
   Mesonet archive (`mtarchive.geol.iastate.edu`) for each time step.
2. **Extract** — Thresholds the CONUS grid at 15 mm (configurable) and
   uses `scipy.ndimage.label()` to find contiguous hail blobs.
3. **Track** — Stitches blobs across time into storm tracks using
   centroid-distance matching (60 km gate for 10-min ticks).
4. **Persist** — Writes tracks as `hail_events` rows with
   `data_source='MRMS_BACKFILL'`, `status='CONFIRMED'`,
   `evidence_mrms=1`, and full swath polygons + MRMS core polygons.
5. **Dedupe** — Skips events that overlap existing NEXRAD_REALTIME or
   NOAA_HAIL events (centroid distance + polygon IOU).

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--days N` | 90 | Backfill last N days from today |
| `--start-date` | — | Explicit start (YYYY-MM-DD) |
| `--end-date` | today | Explicit end (YYYY-MM-DD) |
| `--min-mesh-mm` | 15 | MESH threshold in mm |
| `--min-core-km2` | 5 | Minimum blob area in km² |
| `--tick-minutes` | 10 | Time step between fetches |
| `--workers` | 6 | Parallel download workers |
| `--no-dedupe` | off | Skip de-duplication |
| `--dedupe-distance-km` | 30 | Centroid distance for dedup |
| `--dedupe-overlap` | 0.25 | Polygon IOU threshold for dedup |
| `--dry-run` | off | Extract + track but no DB writes |
| `--cache-dir` | data/mrms_cache | Grib2 disk cache directory |
| `--verbose` | off | DEBUG-level logging |

## Examples

```bash
# Dry run — 7 days, no DB writes
python -m src.cli.mrms_backfill --days 7 --dry-run --verbose

# Specific date range
python -m src.cli.mrms_backfill --start-date 2026-01-01 --end-date 2026-02-01

# Higher threshold, fewer workers
python -m src.cli.mrms_backfill --days 90 --min-mesh-mm 25 --workers 4

# Inside Docker
docker exec -it hailpro-hailtracker-1 \
  /opt/conda/envs/hail/bin/python -m src.cli.mrms_backfill --days 30
```

## Environment Variables

The backfill reads `DATABASE_URL` to connect to the hail_events
database. No other env vars are required.

| Variable | Used By | Default |
|----------|---------|---------|
| `DATABASE_URL` | DB connection | sqlite:///database/hailtracker_pro.db |

## Output

Events are written with:
- `data_source = 'MRMS_BACKFILL'`
- `status = 'CONFIRMED'`
- `evidence_mrms = 1`
- `swath_polygon` — GeoJSON of the union of all blob polygons
- `mrms_core_15/25/40_geojson` — Multi-threshold core polygons
- `severity` — MINOR / MODERATE / SEVERE / CATASTROPHIC

## Idempotency

Re-running the same date range is safe. Events are UPSERTed on
`(event_name) WHERE data_source = 'MRMS_BACKFILL'` — existing records
are updated, never duplicated. The `GREATEST()` function ensures
max_hail_size and evidence flags never decrease.

## Disk Cache

Downloaded grib2.gz files are cached in `data/mrms_cache/YYYYMMDD/`.
Cached files are reused on subsequent runs. To clear the cache:

```bash
rm -rf data/mrms_cache/
```

## Architecture

```
Iowa State Archive (grib2.gz)
    ↓ IowaArchiveFetcher (parallel, disk-cached)
CONUS MESH grid (numpy 2D array)
    ↓ extract_conus_blobs() — scipy.ndimage.label
HailBlob list (centroid, polygon, peak MESH, area)
    ↓ OfflineTracker — greedy centroid matching
Track list (multi-tick union polygons)
    ↓ dedupe_against_existing()
    ↓ persist_tracks() — UPSERT
hail_events table
```
