#!/usr/bin/env python3
"""
NOAA Historical Storm Events Importer
======================================
Downloads and imports historical hail events from NOAA Storm Events Database.

Data Source: https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/

This script:
1. Downloads StormEvents_details CSV files for specified years
2. Filters for hail events (EVENT_TYPE = 'Hail')
3. Parses coordinates, hail size, dates
4. Generates swath polygons from start/end coordinates
5. Inserts into hail_events table

Usage:
    python scripts/import_noaa_historical.py --years 2020,2021,2022,2023,2024
    python scripts/import_noaa_historical.py --years 2024 --state TX
    python scripts/import_noaa_historical.py --all  # Import 2020-2024
"""

import os
import sys
import gzip
import csv
import json
import math
import tempfile
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from io import StringIO
from dataclasses import dataclass
import urllib.request
import ssl

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.database import Database


# NOAA Storm Events FTP URL
NOAA_BASE_URL = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"

# State abbreviations
STATE_ABBREVS = {
    'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
    'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
    'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI', 'IDAHO': 'ID',
    'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA', 'KANSAS': 'KS',
    'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
    'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
    'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV',
    'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY',
    'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK',
    'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
    'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT',
    'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV',
    'WISCONSIN': 'WI', 'WYOMING': 'WY', 'DISTRICT OF COLUMBIA': 'DC',
    'PUERTO RICO': 'PR', 'VIRGIN ISLANDS': 'VI', 'GUAM': 'GU'
}


@dataclass
class HailEvent:
    """Parsed hail event from NOAA data."""
    event_id: str
    episode_id: str
    state: str
    state_abbrev: str
    county: str
    begin_date: datetime
    end_date: datetime
    begin_lat: float
    begin_lon: float
    end_lat: Optional[float]
    end_lon: Optional[float]
    hail_size_inches: float
    source: str
    narrative: str
    injuries_direct: int
    injuries_indirect: int
    deaths_direct: int
    deaths_indirect: int
    damage_property: str
    damage_crops: str


def parse_damage_value(damage_str: str) -> float:
    """Parse NOAA damage string like '10K', '1.5M', '500' to float."""
    if not damage_str or damage_str.strip() == '':
        return 0.0

    damage_str = damage_str.strip().upper()

    multiplier = 1
    if damage_str.endswith('K'):
        multiplier = 1000
        damage_str = damage_str[:-1]
    elif damage_str.endswith('M'):
        multiplier = 1000000
        damage_str = damage_str[:-1]
    elif damage_str.endswith('B'):
        multiplier = 1000000000
        damage_str = damage_str[:-1]

    try:
        return float(damage_str) * multiplier
    except ValueError:
        return 0.0


def generate_swath_polygon(
    begin_lat: float, begin_lon: float,
    end_lat: Optional[float], end_lon: Optional[float],
    hail_size_inches: float
) -> dict:
    """
    Generate a swath polygon from start/end coordinates.

    Swath width is based on hail size:
    - Small hail (<1"): 3km width
    - Medium hail (1-2"): 5km width
    - Large hail (2-3"): 8km width
    - Giant hail (>3"): 12km width
    """
    # Determine swath width based on hail size
    if hail_size_inches < 1.0:
        width_km = 3.0
    elif hail_size_inches < 2.0:
        width_km = 5.0
    elif hail_size_inches < 3.0:
        width_km = 8.0
    else:
        width_km = 12.0

    # If no end coordinates, create a circular swath
    if end_lat is None or end_lon is None or (end_lat == begin_lat and end_lon == begin_lon):
        # Create a circular polygon around the point
        radius_km = width_km / 2
        lat_per_km = 1 / 111.0
        lon_per_km = 1 / (111.0 * math.cos(math.radians(begin_lat)))

        coords = []
        for i in range(16):
            angle = 2 * math.pi * i / 16
            lat = begin_lat + radius_km * lat_per_km * math.sin(angle)
            lon = begin_lon + radius_km * lon_per_km * math.cos(angle)
            coords.append([round(lon, 6), round(lat, 6)])
        coords.append(coords[0])  # Close polygon

        return {
            "type": "Polygon",
            "coordinates": [coords]
        }

    # Calculate direction from start to end
    delta_lat = end_lat - begin_lat
    delta_lon = end_lon - begin_lon

    # Track length
    lat_per_km = 1 / 111.0
    lon_per_km = 1 / (111.0 * math.cos(math.radians((begin_lat + end_lat) / 2)))

    track_length_km = math.sqrt(
        (delta_lat / lat_per_km) ** 2 +
        (delta_lon / lon_per_km) ** 2
    )

    if track_length_km < 0.5:
        # Too short, treat as point
        return generate_swath_polygon(begin_lat, begin_lon, None, None, hail_size_inches)

    # Direction angle
    direction = math.atan2(delta_lon * lon_per_km, delta_lat * lat_per_km)
    perp_direction = direction + math.pi / 2

    # Half width offset
    half_width = width_km / 2
    offset_lat = half_width * lat_per_km * math.sin(perp_direction)
    offset_lon = half_width * lon_per_km * math.cos(perp_direction)

    # Create polygon corners
    coords = [
        [round(begin_lon - offset_lon, 6), round(begin_lat - offset_lat, 6)],
        [round(begin_lon + offset_lon, 6), round(begin_lat + offset_lat, 6)],
        [round(end_lon + offset_lon, 6), round(end_lat + offset_lat, 6)],
        [round(end_lon - offset_lon, 6), round(end_lat - offset_lat, 6)],
    ]
    coords.append(coords[0])  # Close polygon

    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def calculate_swath_area(polygon: dict) -> float:
    """Calculate approximate area of polygon in square miles."""
    coords = polygon.get('coordinates', [[]])[0]
    if len(coords) < 4:
        return 0.0

    # Shoelace formula for polygon area (approximate for small areas)
    n = len(coords) - 1  # Exclude closing point
    area = 0.0

    avg_lat = sum(c[1] for c in coords[:-1]) / n
    lat_to_miles = 69.0
    lon_to_miles = 69.0 * math.cos(math.radians(avg_lat))

    for i in range(n):
        j = (i + 1) % n
        # Convert to miles
        x1 = coords[i][0] * lon_to_miles
        y1 = coords[i][1] * lat_to_miles
        x2 = coords[j][0] * lon_to_miles
        y2 = coords[j][1] * lat_to_miles
        area += x1 * y2
        area -= x2 * y1

    return abs(area) / 2


def classify_severity(hail_size_inches: float) -> str:
    """Classify hail severity based on size."""
    if hail_size_inches < 1.0:
        return 'MINOR'
    elif hail_size_inches < 1.5:
        return 'MODERATE'
    elif hail_size_inches < 2.0:
        return 'SEVERE'
    else:
        return 'CATASTROPHIC'


def download_noaa_file(year: int, temp_dir: str) -> Optional[str]:
    """
    Download NOAA Storm Events file for a specific year.

    Returns path to downloaded file or None if failed.
    """
    # Try to find the file with pattern matching
    # Files are named: StormEvents_details-ftp_v1.0_dYYYY_cYYYYMMDD.csv.gz

    # Create SSL context that doesn't verify (NOAA cert issues sometimes)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    print(f"\n[{year}] Looking for Storm Events file...")

    # First, get the directory listing to find the exact filename
    try:
        req = urllib.request.Request(
            NOAA_BASE_URL,
            headers={'User-Agent': 'HailTracker-NOAA-Import/1.0'}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=30) as response:
            html = response.read().decode('utf-8')
    except Exception as e:
        print(f"[{year}] Failed to list directory: {e}")
        return None

    # Find the file for this year
    import re
    pattern = rf'StormEvents_details-ftp_v1\.0_d{year}_c\d{{8}}\.csv\.gz'
    matches = re.findall(pattern, html)

    if not matches:
        print(f"[{year}] No Storm Events file found for year {year}")
        return None

    # Use the most recent file (highest date code)
    filename = sorted(matches)[-1]
    file_url = NOAA_BASE_URL + filename
    local_path = os.path.join(temp_dir, filename)

    print(f"[{year}] Downloading {filename}...")

    try:
        req = urllib.request.Request(
            file_url,
            headers={'User-Agent': 'HailTracker-NOAA-Import/1.0'}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=120) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunks

            with open(local_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        pct = (downloaded / total_size) * 100
                        print(f"\r[{year}] Downloaded {downloaded / 1024 / 1024:.1f} MB ({pct:.0f}%)", end='', flush=True)
            print()  # Newline after progress

        print(f"[{year}] Download complete: {local_path}")
        return local_path

    except Exception as e:
        print(f"[{year}] Download failed: {e}")
        return None


def parse_noaa_csv(filepath: str, state_filter: Optional[str] = None) -> List[HailEvent]:
    """
    Parse NOAA Storm Events CSV file and extract hail events.

    Args:
        filepath: Path to gzipped CSV file
        state_filter: Optional state abbreviation to filter (e.g., 'TX')

    Returns:
        List of HailEvent objects
    """
    events = []

    print(f"Parsing {os.path.basename(filepath)}...")

    with gzip.open(filepath, 'rt', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)

        row_count = 0
        hail_count = 0

        for row in reader:
            row_count += 1

            # Filter for hail events only
            event_type = row.get('EVENT_TYPE', '').strip().upper()
            if event_type != 'HAIL':
                continue

            hail_count += 1

            # Get state
            state_full = row.get('STATE', '').strip().upper()
            state_abbrev = STATE_ABBREVS.get(state_full, state_full[:2] if len(state_full) >= 2 else 'XX')

            # Apply state filter if specified
            if state_filter and state_abbrev != state_filter.upper():
                continue

            # Parse coordinates
            try:
                begin_lat = float(row.get('BEGIN_LAT', 0) or 0)
                begin_lon = float(row.get('BEGIN_LON', 0) or 0)
            except (ValueError, TypeError):
                continue

            # Skip if no valid coordinates
            if begin_lat == 0 or begin_lon == 0:
                continue

            # Parse end coordinates (optional)
            try:
                end_lat = float(row.get('END_LAT', 0) or 0) or None
                end_lon = float(row.get('END_LON', 0) or 0) or None
                if end_lat == 0:
                    end_lat = None
                if end_lon == 0:
                    end_lon = None
            except (ValueError, TypeError):
                end_lat = None
                end_lon = None

            # Parse hail size (MAGNITUDE field, in inches)
            try:
                hail_size = float(row.get('MAGNITUDE', 0) or 0)
            except (ValueError, TypeError):
                hail_size = 0.75  # Default to dime size

            if hail_size <= 0:
                hail_size = 0.75

            # Parse dates
            try:
                # Format: DD-MON-YY HH:MM:SS or similar
                begin_str = row.get('BEGIN_DATE_TIME', '')
                end_str = row.get('END_DATE_TIME', '')

                # Try multiple date formats
                for fmt in ['%d-%b-%y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M']:
                    try:
                        begin_date = datetime.strptime(begin_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue  # Skip if no format works

                for fmt in ['%d-%b-%y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %H:%M']:
                    try:
                        end_date = datetime.strptime(end_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    end_date = begin_date + timedelta(minutes=30)

            except Exception:
                continue

            # Parse other fields
            event = HailEvent(
                event_id=row.get('EVENT_ID', ''),
                episode_id=row.get('EPISODE_ID', ''),
                state=state_full,
                state_abbrev=state_abbrev,
                county=row.get('CZ_NAME', '').title(),
                begin_date=begin_date,
                end_date=end_date,
                begin_lat=begin_lat,
                begin_lon=begin_lon,
                end_lat=end_lat,
                end_lon=end_lon,
                hail_size_inches=hail_size,
                source=row.get('SOURCE', 'NOAA'),
                narrative=row.get('EVENT_NARRATIVE', '')[:500],  # Truncate
                injuries_direct=int(row.get('INJURIES_DIRECT', 0) or 0),
                injuries_indirect=int(row.get('INJURIES_INDIRECT', 0) or 0),
                deaths_direct=int(row.get('DEATHS_DIRECT', 0) or 0),
                deaths_indirect=int(row.get('DEATHS_INDIRECT', 0) or 0),
                damage_property=row.get('DAMAGE_PROPERTY', ''),
                damage_crops=row.get('DAMAGE_CROPS', '')
            )

            events.append(event)

    print(f"  Total rows: {row_count:,}")
    print(f"  Hail events: {hail_count:,}")
    print(f"  After filtering: {len(events):,}")

    return events


def insert_events(db: Database, events: List[HailEvent], year: int) -> int:
    """
    Insert hail events into database.

    Returns count of events inserted.
    """
    inserted = 0
    skipped = 0

    print(f"\nInserting {len(events)} events into database...")

    for i, event in enumerate(events):
        # Generate swath polygon
        swath = generate_swath_polygon(
            event.begin_lat, event.begin_lon,
            event.end_lat, event.end_lon,
            event.hail_size_inches
        )

        # Calculate area
        area_sqmi = calculate_swath_area(swath)

        # Determine severity
        severity = classify_severity(event.hail_size_inches)

        # Estimate vehicles (rough estimate: 50 vehicles per sq mile affected)
        estimated_vehicles = int(area_sqmi * 50)

        # Create event name
        event_name = f"{event.county}, {event.state_abbrev} - {event.begin_date.strftime('%b %d, %Y')}"

        # Check if event already exists (by NOAA event_id)
        existing = db.execute("""
            SELECT id FROM hail_events
            WHERE data_source = 'NOAA_HISTORICAL'
            AND event_name LIKE ?
            AND event_date = ?
        """, (f"%{event.event_id}%", event.begin_date.date().isoformat()))

        if existing:
            skipped += 1
            continue

        # Calculate center point
        if event.end_lat and event.end_lon:
            center_lat = (event.begin_lat + event.end_lat) / 2
            center_lon = (event.begin_lon + event.end_lon) / 2
        else:
            center_lat = event.begin_lat
            center_lon = event.begin_lon

        # Calculate storm motion if we have end coordinates
        if event.end_lat and event.end_lon:
            delta_lat = event.end_lat - event.begin_lat
            delta_lon = event.end_lon - event.begin_lon
            motion_dir = math.degrees(math.atan2(delta_lon, delta_lat)) % 360

            duration = (event.end_date - event.begin_date).total_seconds() / 3600  # hours
            lat_km = delta_lat * 111
            lon_km = delta_lon * 111 * math.cos(math.radians(center_lat))
            distance_km = math.sqrt(lat_km**2 + lon_km**2)
            motion_speed = distance_km / max(duration, 0.1)  # km/h
        else:
            motion_dir = 45  # Default NE
            motion_speed = 40  # Default 40 km/h

        # Extended event name with NOAA ID
        full_event_name = f"{event_name} [NOAA:{event.event_id}]"

        try:
            db.execute("""
                INSERT INTO hail_events (
                    event_name, event_date, center_lat, center_lon,
                    swath_polygon, swath_area_sqmi, max_hail_size,
                    estimated_vehicles, storm_motion_dir, storm_motion_speed,
                    swath_method, data_source, confidence_score,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                full_event_name,
                event.begin_date.date().isoformat(),
                center_lat,
                center_lon,
                json.dumps(swath),
                round(area_sqmi, 2),
                event.hail_size_inches,
                estimated_vehicles,
                motion_dir,
                motion_speed,
                'NOAA_REPORT',
                'NOAA_HISTORICAL',
                0.95,  # High confidence for official reports
                datetime.now().isoformat()
            ))
            inserted += 1

        except Exception as e:
            print(f"  Error inserting event {event.event_id}: {e}")
            continue

        # Progress update
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1:,} / {len(events):,} events ({inserted:,} inserted, {skipped:,} skipped)")

    print(f"\n  Total inserted: {inserted:,}")
    print(f"  Total skipped (duplicates): {skipped:,}")

    return inserted


def main():
    parser = argparse.ArgumentParser(
        description='Import NOAA historical hail events',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/import_noaa_historical.py --years 2024
    python scripts/import_noaa_historical.py --years 2023,2024 --state TX
    python scripts/import_noaa_historical.py --all
    python scripts/import_noaa_historical.py --all --state OK
        """
    )

    parser.add_argument('--years', type=str,
                       help='Comma-separated list of years (e.g., 2023,2024)')
    parser.add_argument('--all', action='store_true',
                       help='Import all years 2020-2024')
    parser.add_argument('--state', type=str,
                       help='Filter by state abbreviation (e.g., TX, OK)')
    parser.add_argument('--db', type=str, default='data/hailtracker_crm.db',
                       help='Database path (default: data/hailtracker_crm.db)')
    parser.add_argument('--keep-downloads', action='store_true',
                       help='Keep downloaded files instead of cleaning up')

    args = parser.parse_args()

    # Determine years to import
    if args.all:
        years = [2020, 2021, 2022, 2023, 2024]
    elif args.years:
        years = [int(y.strip()) for y in args.years.split(',')]
    else:
        print("Error: Specify --years or --all")
        parser.print_help()
        return 1

    print("=" * 70)
    print("NOAA HISTORICAL HAIL EVENTS IMPORTER")
    print("=" * 70)
    print(f"\nYears to import: {years}")
    if args.state:
        print(f"State filter: {args.state}")
    print(f"Database: {args.db}")
    print()

    # Initialize database
    db = Database(args.db)

    # Create temp directory for downloads
    temp_dir = tempfile.mkdtemp(prefix='noaa_hail_')
    print(f"Download directory: {temp_dir}")

    total_events = 0
    total_inserted = 0

    try:
        for year in years:
            print("\n" + "=" * 50)
            print(f"PROCESSING YEAR {year}")
            print("=" * 50)

            # Download file
            filepath = download_noaa_file(year, temp_dir)
            if not filepath:
                print(f"[{year}] Skipping - download failed")
                continue

            # Parse events
            events = parse_noaa_csv(filepath, args.state)
            total_events += len(events)

            if not events:
                print(f"[{year}] No events found after filtering")
                continue

            # Insert into database
            inserted = insert_events(db, events, year)
            total_inserted += inserted

            # Clean up if not keeping downloads
            if not args.keep_downloads:
                os.remove(filepath)

        print("\n" + "=" * 70)
        print("IMPORT COMPLETE")
        print("=" * 70)
        print(f"\nTotal hail events found: {total_events:,}")
        print(f"Total events inserted: {total_inserted:,}")

        # Show database stats
        count = db.execute("SELECT COUNT(*) as count FROM hail_events WHERE data_source = 'NOAA_HISTORICAL'")
        print(f"\nTotal NOAA historical events in database: {count[0]['count']:,}")

        # Show by state
        by_state = db.execute("""
            SELECT
                substr(event_name, instr(event_name, ',') + 2, 2) as state,
                COUNT(*) as count
            FROM hail_events
            WHERE data_source = 'NOAA_HISTORICAL'
            GROUP BY state
            ORDER BY count DESC
            LIMIT 10
        """)

        if by_state:
            print("\nTop 10 states by hail events:")
            for row in by_state:
                print(f"  {row['state']}: {row['count']:,} events")

    finally:
        # Clean up temp directory
        if not args.keep_downloads:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    return 0


if __name__ == '__main__':
    sys.exit(main())
