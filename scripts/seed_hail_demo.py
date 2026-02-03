#!/usr/bin/env python3
"""
Seed Demo Hail Data
===================
Seeds realistic hail events across hail alley with GeoJSON swaths,
starts the storm monitor, and runs a storm simulation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math
import random
from datetime import datetime, date, timedelta

from src.db.database import Database
from src.crm.models.schema import DatabaseSchema


def generate_swath_polygon(center_lat: float, center_lon: float,
                           length_km: float = 30, width_km: float = 8,
                           direction_deg: float = 45) -> dict:
    """
    Generate a realistic elongated swath polygon (not a circle!)

    Hail swaths are typically elongated in the direction of storm movement.
    This creates a realistic pill-shaped polygon.
    """
    # Convert to radians
    dir_rad = math.radians(direction_deg)

    # Calculate deltas for movement (roughly)
    # 1 degree latitude = 111 km
    # 1 degree longitude = 111 * cos(lat) km
    lat_per_km = 1 / 111.0
    lon_per_km = 1 / (111.0 * math.cos(math.radians(center_lat)))

    # Half dimensions
    half_length = length_km / 2
    half_width = width_km / 2

    # Generate points along the swath
    # Start and end points (along direction)
    start_lat = center_lat - half_length * lat_per_km * math.cos(dir_rad)
    start_lon = center_lon - half_length * lon_per_km * math.sin(dir_rad)
    end_lat = center_lat + half_length * lat_per_km * math.cos(dir_rad)
    end_lon = center_lon + half_length * lon_per_km * math.sin(dir_rad)

    # Perpendicular direction for width
    perp_rad = dir_rad + math.pi / 2

    # Create polygon points (capsule shape)
    coords = []

    # Number of points for rounded ends
    n_cap = 8

    # Right side of swath (start to end)
    for i in range(n_cap):
        angle = perp_rad - math.pi/2 + (math.pi * i / (n_cap - 1))
        lat = start_lat + half_width * lat_per_km * math.cos(angle)
        lon = start_lon + half_width * lon_per_km * math.sin(angle)
        coords.append([round(lon, 6), round(lat, 6)])

    # End cap
    for i in range(n_cap):
        angle = perp_rad + math.pi/2 - (math.pi * i / (n_cap - 1))
        lat = end_lat + half_width * lat_per_km * math.cos(angle)
        lon = end_lon + half_width * lon_per_km * math.sin(angle)
        coords.append([round(lon, 6), round(lat, 6)])

    # Close the polygon
    coords.append(coords[0])

    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def generate_zip_codes(state: str, city: str, count: int = 5) -> list:
    """Generate plausible ZIP codes for a city"""
    zip_prefixes = {
        'TX': {'Dallas': '752', 'Fort Worth': '761', 'San Antonio': '782', 'Austin': '787', 'Houston': '770', 'Amarillo': '791', 'Lubbock': '794', 'Wichita Falls': '763'},
        'OK': {'Oklahoma City': '731', 'Tulsa': '741', 'Norman': '730', 'Lawton': '735', 'Edmond': '730'},
        'KS': {'Wichita': '672', 'Topeka': '666', 'Kansas City': '661', 'Salina': '674', 'Dodge City': '678'},
        'CO': {'Denver': '802', 'Colorado Springs': '809', 'Fort Collins': '805', 'Aurora': '800', 'Pueblo': '810'},
        'NE': {'Omaha': '681', 'Lincoln': '685', 'Grand Island': '688'},
    }

    prefix = zip_prefixes.get(state, {}).get(city, '750')
    return [f"{prefix}{str(i).zfill(2)}" for i in random.sample(range(100), min(count, 100))]


# Hail alley cities with coordinates
HAIL_ALLEY_CITIES = [
    # Texas
    {'city': 'Dallas', 'state': 'TX', 'lat': 32.7767, 'lon': -96.7970},
    {'city': 'Fort Worth', 'state': 'TX', 'lat': 32.7555, 'lon': -97.3308},
    {'city': 'San Antonio', 'state': 'TX', 'lat': 29.4241, 'lon': -98.4936},
    {'city': 'Amarillo', 'state': 'TX', 'lat': 35.2220, 'lon': -101.8313},
    {'city': 'Lubbock', 'state': 'TX', 'lat': 33.5779, 'lon': -101.8552},
    {'city': 'Wichita Falls', 'state': 'TX', 'lat': 33.9137, 'lon': -98.4934},
    # Oklahoma
    {'city': 'Oklahoma City', 'state': 'OK', 'lat': 35.4676, 'lon': -97.5164},
    {'city': 'Tulsa', 'state': 'OK', 'lat': 36.1540, 'lon': -95.9928},
    {'city': 'Norman', 'state': 'OK', 'lat': 35.2226, 'lon': -97.4395},
    # Kansas
    {'city': 'Wichita', 'state': 'KS', 'lat': 37.6872, 'lon': -97.3301},
    {'city': 'Topeka', 'state': 'KS', 'lat': 39.0473, 'lon': -95.6752},
    {'city': 'Dodge City', 'state': 'KS', 'lat': 37.7528, 'lon': -100.0171},
    # Colorado
    {'city': 'Denver', 'state': 'CO', 'lat': 39.7392, 'lon': -104.9903},
    {'city': 'Colorado Springs', 'state': 'CO', 'lat': 38.8339, 'lon': -104.8214},
    # Nebraska
    {'city': 'Omaha', 'state': 'NE', 'lat': 41.2565, 'lon': -95.9345},
]


def seed_hail_events(db_path: str = 'hailtracker.db'):
    """Seed 15 realistic hail events across hail alley"""
    # Initialize database schema if needed
    import os
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        print("\n[INFO] Initializing database schema...")
        DatabaseSchema.create_all_tables(db_path)
    else:
        print(f"\n[INFO] Using existing database: {db_path}")

    db = Database(db_path)

    print("\n" + "=" * 70)
    print("SEEDING HAIL EVENTS")
    print("=" * 70)

    # Severities with weights
    severities = [
        ('MINOR', 0.75, 15, 8, 8000),
        ('MODERATE', 1.25, 25, 12, 15000),
        ('SEVERE', 1.75, 40, 18, 25000),
        ('CATASTROPHIC', 2.5, 60, 25, 40000),
    ]

    events_created = []

    for i in range(15):
        # Pick a random city
        city_info = random.choice(HAIL_ALLEY_CITIES)

        # Random date in last 30 days
        days_ago = random.randint(1, 30)
        event_date = date.today() - timedelta(days=days_ago)

        # Random severity (weighted towards moderate/severe)
        severity, hail_size_base, length_km, width_km, base_vehicles = random.choices(
            severities,
            weights=[0.15, 0.35, 0.35, 0.15]
        )[0]

        # Add some randomness to hail size
        hail_size = round(hail_size_base + random.uniform(-0.25, 0.25), 2)

        # Random storm direction (typically NE in hail alley)
        direction = random.uniform(30, 75)

        # Generate swath with some randomness
        swath_length = length_km + random.uniform(-5, 10)
        swath_width = width_km + random.uniform(-2, 4)

        # Offset center slightly from city center
        center_lat = city_info['lat'] + random.uniform(-0.2, 0.2)
        center_lon = city_info['lon'] + random.uniform(-0.2, 0.2)

        swath_geojson = generate_swath_polygon(
            center_lat, center_lon,
            length_km=swath_length,
            width_km=swath_width,
            direction_deg=direction
        )

        # Calculate affected area (rough ellipse)
        affected_area = math.pi * (swath_length / 2) * (swath_width / 2) * 0.386  # sq miles

        # Estimated vehicles (with some randomness)
        estimated_vehicles = int(base_vehicles * random.uniform(0.7, 1.5))

        # Potential revenue at 5% capture
        revenue_per_vehicle = {
            'MINOR': 500, 'MODERATE': 1500, 'SEVERE': 3000, 'CATASTROPHIC': 5000
        }[severity]
        potential_revenue = estimated_vehicles * revenue_per_vehicle * 0.05

        # ZIP codes
        zip_codes = generate_zip_codes(city_info['state'], city_info['city'], random.randint(3, 8))

        # Event name
        event_name = f"{city_info['city']} {severity.title()} Hail Storm"
        if days_ago <= 7:
            event_name = f"{city_info['city']} {severity.title()} Hail - {event_date.strftime('%b %d')}"

        # Build metadata
        metadata = {
            '_meta': {
                'city': city_info['city'],
                'state': city_info['state'],
                'severity': severity,
                'affected_zip_codes': zip_codes,
                'estimated_radius_miles': round(swath_length / 2 * 0.621, 1),
                'insurance_storm_code': f"INS-{event_date.strftime('%Y%m%d')}-{i+1:03d}",
                'noaa_event_id': f"NOAA-{random.randint(100000, 999999)}",
                'status': 'ACTIVE' if days_ago <= 14 else 'CLOSED'
            },
            'notes': f"Storm moved {direction:.0f}° (NE). Peak hail {hail_size}\"."
        }

        # Insert into database
        now = datetime.now().isoformat()

        # Try CRM schema first (swath_polygon, center_lat, center_lon)
        # Falls back to simpler schema (location_name, swath_geojson)
        try:
            event_id = db.execute("""
                INSERT INTO hail_events (
                    event_name, event_date, center_lat, center_lon,
                    swath_polygon, swath_area_sqmi, max_hail_size,
                    estimated_vehicles, storm_motion_dir, storm_motion_speed,
                    swath_method, data_source, confidence_score,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_name,
                event_date.isoformat(),
                center_lat,
                center_lon,
                json.dumps(swath_geojson),
                round(affected_area, 2),
                hail_size,
                estimated_vehicles,
                direction,
                55.0,  # avg storm speed km/h
                'SIMULATION',  # swath_method
                'DEMO_SEED',   # data_source
                0.85,          # confidence_score
                now
            ))
        except Exception:
            # Fallback to alternate schema
            event_id = db.execute("""
                INSERT INTO hail_events (
                    event_name, event_date, location_name,
                    affected_area_sq_miles, swath_geojson, max_hail_size,
                    estimated_vehicles, potential_revenue, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_name,
                event_date.isoformat(),
                f"{city_info['city']}, {city_info['state']}",
                round(affected_area, 2),
                json.dumps(swath_geojson),
                hail_size,
                estimated_vehicles,
                potential_revenue,
                json.dumps(metadata),
                now
            ))

        print(f"\n[{i+1:2d}] {event_name}")
        print(f"     Date: {event_date} | Severity: {severity} | Hail: {hail_size}\"")
        print(f"     Location: {city_info['city']}, {city_info['state']}")
        print(f"     Swath: {swath_length:.0f}km x {swath_width:.0f}km | Area: {affected_area:.1f} sq mi")
        print(f"     Vehicles: {estimated_vehicles:,} | Potential: ${potential_revenue:,.0f}")

        events_created.append({
            'id': event_id,
            'name': event_name,
            'city': city_info['city'],
            'state': city_info['state'],
            'severity': severity
        })

    print("\n" + "-" * 70)
    print(f"Created {len(events_created)} hail events with GeoJSON swaths")

    return events_created


def start_storm_monitor(cookies_path: str = 'cookies.txt'):
    """Start the storm monitor via API"""
    import subprocess

    print("\n" + "=" * 70)
    print("STARTING STORM MONITOR")
    print("=" * 70)

    # Start monitor with hail alley radar sites
    config = {
        "radar_ids": ["KFWS", "KTLX", "KICT", "KDDC", "KFTG"],  # Dallas, OKC, Wichita, Dodge City, Denver
        "scan_interval_seconds": 300,
        "min_mesh_mm": 25,
        "coverage_regions": ["TX", "OK", "KS", "CO"],
        "auto_select_radars": True
    }

    cmd = [
        'curl', '-s', '-X', 'POST',
        '-b', cookies_path,
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(config),
        'http://localhost:5000/api/storm-monitor/start'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            print(f"\nMonitor started: {response.get('message', 'OK')}")
            if 'radars' in response:
                print(f"Active radars: {', '.join(response['radars'])}")
        except:
            print(f"Response: {result.stdout}")
    else:
        print(f"Error: {result.stderr}")

    # Check status
    cmd = ['curl', '-s', '-b', cookies_path, 'http://localhost:5000/api/storm-monitor/status']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            status = json.loads(result.stdout)
            print(f"\nMonitor Status:")
            print(f"  Running: {status.get('running', False)}")
            print(f"  Initialized: {status.get('initialized', False)}")
            if status.get('radars'):
                print(f"  Radars: {status['radars']}")
        except:
            print(f"Status: {result.stdout}")

    return True


def run_storm_simulation(cookies_path: str = 'cookies.txt'):
    """Run a storm simulation across Oklahoma"""
    import subprocess

    print("\n" + "=" * 70)
    print("RUNNING STORM SIMULATION")
    print("=" * 70)

    # Simulate storm moving NE across Oklahoma
    simulation_params = {
        "start_lat": 35.0,      # Southern Oklahoma
        "start_lon": -98.0,     # Central Oklahoma
        "direction": 45,        # Northeast
        "speed": 55,            # 55 km/h
        "duration": 90,         # 90 minutes
        "peak_reflectivity": 62 # Strong storm
    }

    print(f"\nSimulation Parameters:")
    print(f"  Start: ({simulation_params['start_lat']}, {simulation_params['start_lon']})")
    print(f"  Direction: {simulation_params['direction']}° (NE)")
    print(f"  Speed: {simulation_params['speed']} km/h")
    print(f"  Duration: {simulation_params['duration']} minutes")
    print(f"  Peak Reflectivity: {simulation_params['peak_reflectivity']} dBZ")

    cmd = [
        'curl', '-s', '-X', 'POST',
        '-b', cookies_path,
        '-H', 'Content-Type: application/json',
        '-d', json.dumps(simulation_params),
        'http://localhost:5000/api/storm-cells/simulate'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        try:
            response = json.loads(result.stdout)
            print(f"\nSimulation Results:")
            print(f"  Cells created: {response.get('cells_created', 0)}")
            print(f"  Tracks: {response.get('tracks', 0)}")

            swaths = response.get('swaths', {})
            if swaths and 'features' in swaths:
                print(f"  Swaths generated: {len(swaths['features'])}")
                for feature in swaths['features']:
                    props = feature.get('properties', {})
                    print(f"    - Cell {props.get('cell_id')}: {props.get('max_mesh_mm', 0):.0f}mm, {props.get('duration_minutes', 0):.0f} min")

            stats = response.get('statistics', {})
            if stats:
                print(f"\nTracking Statistics:")
                print(f"  Total cells: {stats.get('total_cells', 0)}")
                print(f"  Active cells: {stats.get('active_cells', 0)}")
                print(f"  Max MESH: {stats.get('max_mesh_mm', 0):.0f}mm")
        except Exception as e:
            print(f"Response: {result.stdout[:500]}")
            print(f"Parse error: {e}")
    else:
        print(f"Error: {result.stderr}")

    return True


def verify_system(cookies_path: str = 'cookies.txt', db_path: str = 'hailtracker.db'):
    """Verify the hail system is operational"""
    import subprocess

    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    db = Database(db_path)

    # 1. Count hail events
    events = db.execute("SELECT COUNT(*) as count FROM hail_events")
    event_count = events[0]['count'] if events else 0
    print(f"\n1. Hail Events in Database: {event_count}")

    # Show recent events
    recent = db.execute("""
        SELECT event_name, event_date, max_hail_size, estimated_vehicles
        FROM hail_events
        ORDER BY created_at DESC
        LIMIT 5
    """)
    if recent:
        print("   Recent events:")
        for e in recent:
            print(f"   - {e['event_name']}: {e['max_hail_size']}\" hail, {e['estimated_vehicles']:,} vehicles")

    # 2. Check storm monitor status
    cmd = ['curl', '-s', '-b', cookies_path, 'http://localhost:5000/api/storm-monitor/status']
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        status = json.loads(result.stdout)
        print(f"\n2. Storm Monitor Status:")
        print(f"   Running: {status.get('running', False)}")
        print(f"   Initialized: {status.get('initialized', False)}")
    except:
        print(f"\n2. Storm Monitor: Unable to get status")

    # 3. Check active storm cells
    cmd = ['curl', '-s', '-b', cookies_path, 'http://localhost:5000/api/storm-cells/active']
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        cells = json.loads(result.stdout)
        print(f"\n3. Active Storm Cells: {cells.get('count', 0)}")
        if cells.get('active_cells'):
            for cell in cells['active_cells'][:3]:
                print(f"   - Cell {cell['cell_id']}: {cell['mesh_inches']}\" hail at ({cell['lat']:.2f}, {cell['lon']:.2f})")
    except:
        print(f"\n3. Active Storm Cells: Unable to get data")

    # 4. Check swaths
    cmd = ['curl', '-s', '-b', cookies_path, 'http://localhost:5000/api/storm-cells/swaths']
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        swaths = json.loads(result.stdout)
        print(f"\n4. GeoJSON Swaths: {swaths.get('count', 0)} features")
    except:
        print(f"\n4. GeoJSON Swaths: Unable to get data")

    # 5. Check hail events via API
    cmd = ['curl', '-s', '-b', cookies_path, 'http://localhost:5000/api/hail-events?days=30']
    result = subprocess.run(cmd, capture_output=True, text=True)

    try:
        events_api = json.loads(result.stdout)
        print(f"\n5. Hail Events via API: {events_api.get('count', 0)}")
        stats = events_api.get('stats', {})
        if stats:
            print(f"   Total vehicles affected: {stats.get('total_estimated_vehicles', 0):,}")
            print(f"   Active storms: {stats.get('active_storms', 0)}")
            by_sev = stats.get('by_severity', {})
            if by_sev:
                sev_str = ', '.join(f"{k}:{v['count']}" for k, v in by_sev.items())
                print(f"   By severity: {sev_str}")
    except:
        print(f"\n5. Hail Events via API: Unable to get data")

    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

    if event_count > 0:
        print("\n[SUCCESS] Hail system is operational!")
        print("   Open the hail-map page in browser to see the data.")
    else:
        print("\n[WARNING] Some data may be missing. Check the API endpoints.")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Seed hail demo data')
    parser.add_argument('--db', default='hailtracker.db', help='Database path')
    parser.add_argument('--cookies', default='cookies.txt', help='Cookies file for API auth')
    parser.add_argument('--skip-seed', action='store_true', help='Skip seeding events')
    parser.add_argument('--skip-monitor', action='store_true', help='Skip starting monitor')
    parser.add_argument('--skip-simulate', action='store_true', help='Skip simulation')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("HAIL SYSTEM INITIALIZATION")
    print("=" * 70)

    # 1. Seed historical events
    if not args.skip_seed:
        seed_hail_events(args.db)

    # 2. Start storm monitor
    if not args.skip_monitor:
        start_storm_monitor(args.cookies)

    # 3. Run simulation
    if not args.skip_simulate:
        run_storm_simulation(args.cookies)

    # 4. Verify
    verify_system(args.cookies, args.db)
