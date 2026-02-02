"""
Radar Coverage Finder

Find all radars that cover a given location with distance calculations
and multi-radar fusion support.
"""

import sqlite3
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / 'database' / 'hailtracker_pro.db'


@dataclass
class RadarSite:
    """Represents a radar site."""
    site_code: str
    name: str
    country: str
    state_province: str
    latitude: float
    longitude: float
    elevation_m: float
    coverage_radius_km: float
    timezone: str
    data_source: str
    data_url: str
    is_active: bool


@dataclass
class RadarCoverage:
    """Radar coverage for a specific location."""
    radar: RadarSite
    distance_km: float
    bearing_deg: float
    is_primary: bool
    coverage_quality: str  # 'excellent', 'good', 'marginal', 'poor'


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two points in kilometers.
    """
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing from point 1 to point 2 in degrees.
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(lat2_rad)
    y = (math.cos(lat1_rad) * math.sin(lat2_rad) -
         math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon))

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def get_coverage_quality(distance_km: float, max_range_km: float = 230) -> str:
    """
    Determine coverage quality based on distance from radar.

    NEXRAD has ~230km range but quality degrades with distance:
    - < 100km: Excellent (good low-level coverage)
    - 100-150km: Good
    - 150-200km: Marginal (beam height issues)
    - > 200km: Poor (significant beam overshoot)
    """
    if distance_km < 100:
        return 'excellent'
    elif distance_km < 150:
        return 'good'
    elif distance_km < 200:
        return 'marginal'
    else:
        return 'poor'


def get_all_radars() -> List[RadarSite]:
    """Load all radar sites from database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT site_code, name, country, state_province, latitude, longitude,
               elevation_m, coverage_radius_km, timezone, data_source, data_url, is_active
        FROM radar_sites
        WHERE is_active = 1
    """)

    radars = []
    for row in cursor.fetchall():
        radars.append(RadarSite(
            site_code=row['site_code'],
            name=row['name'],
            country=row['country'],
            state_province=row['state_province'] or '',
            latitude=row['latitude'],
            longitude=row['longitude'],
            elevation_m=row['elevation_m'] or 0,
            coverage_radius_km=row['coverage_radius_km'] or 230,
            timezone=row['timezone'] or 'UTC',
            data_source=row['data_source'] or '',
            data_url=row['data_url'] or '',
            is_active=bool(row['is_active'])
        ))

    conn.close()
    return radars


def find_covering_radars(
    lat: float,
    lon: float,
    max_distance_km: float = 230,
    min_radars: int = 1,
    max_radars: int = 5,
    country_filter: List[str] = None
) -> List[RadarCoverage]:
    """
    Find all radars that cover a given location.

    Args:
        lat: Latitude of location
        lon: Longitude of location
        max_distance_km: Maximum distance to consider
        min_radars: Minimum number of radars to return (may extend search)
        max_radars: Maximum number of radars to return
        country_filter: Optional list of countries ['US', 'CA', 'MX']

    Returns:
        List of RadarCoverage objects sorted by distance
    """
    radars = get_all_radars()

    coverages = []
    for radar in radars:
        # Apply country filter
        if country_filter and radar.country not in country_filter:
            continue

        distance = haversine_distance(lat, lon, radar.latitude, radar.longitude)

        # Skip if too far
        if distance > max_distance_km * 1.5:  # Allow some margin for min_radars
            continue

        bearing = calculate_bearing(radar.latitude, radar.longitude, lat, lon)
        quality = get_coverage_quality(distance, radar.coverage_radius_km)

        coverages.append(RadarCoverage(
            radar=radar,
            distance_km=distance,
            bearing_deg=bearing,
            is_primary=False,
            coverage_quality=quality
        ))

    # Sort by distance
    coverages.sort(key=lambda x: x.distance_km)

    # Mark primary radar
    if coverages:
        coverages[0].is_primary = True

    # Filter to max distance (but ensure min_radars)
    filtered = [c for c in coverages if c.distance_km <= max_distance_km]
    if len(filtered) < min_radars and len(coverages) >= min_radars:
        filtered = coverages[:min_radars]

    return filtered[:max_radars]


def find_nearest_radar(lat: float, lon: float, country_filter: List[str] = None) -> Optional[RadarSite]:
    """
    Find the single nearest radar to a location.

    Args:
        lat: Latitude
        lon: Longitude
        country_filter: Optional list of countries

    Returns:
        Nearest RadarSite or None
    """
    coverages = find_covering_radars(
        lat, lon,
        max_distance_km=500,
        min_radars=1,
        max_radars=1,
        country_filter=country_filter
    )
    return coverages[0].radar if coverages else None


def find_radars_by_state(state_province: str) -> List[RadarSite]:
    """Find all radars in a state/province."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT site_code, name, country, state_province, latitude, longitude,
               elevation_m, coverage_radius_km, timezone, data_source, data_url, is_active
        FROM radar_sites
        WHERE state_province = ? AND is_active = 1
    """, (state_province,))

    radars = []
    for row in cursor.fetchall():
        radars.append(RadarSite(
            site_code=row['site_code'],
            name=row['name'],
            country=row['country'],
            state_province=row['state_province'] or '',
            latitude=row['latitude'],
            longitude=row['longitude'],
            elevation_m=row['elevation_m'] or 0,
            coverage_radius_km=row['coverage_radius_km'] or 230,
            timezone=row['timezone'] or 'UTC',
            data_source=row['data_source'] or '',
            data_url=row['data_url'] or '',
            is_active=bool(row['is_active'])
        ))

    conn.close()
    return radars


def get_radar_by_code(site_code: str) -> Optional[RadarSite]:
    """Get a specific radar by its site code."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT site_code, name, country, state_province, latitude, longitude,
               elevation_m, coverage_radius_km, timezone, data_source, data_url, is_active
        FROM radar_sites
        WHERE site_code = ?
    """, (site_code,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return RadarSite(
        site_code=row['site_code'],
        name=row['name'],
        country=row['country'],
        state_province=row['state_province'] or '',
        latitude=row['latitude'],
        longitude=row['longitude'],
        elevation_m=row['elevation_m'] or 0,
        coverage_radius_km=row['coverage_radius_km'] or 230,
        timezone=row['timezone'] or 'UTC',
        data_source=row['data_source'] or '',
        data_url=row['data_url'] or '',
        is_active=bool(row['is_active'])
    )


def get_multi_radar_coverage(
    lat: float,
    lon: float,
    min_overlap: int = 2
) -> Dict:
    """
    Find location with multi-radar coverage for cross-validation.

    Locations covered by multiple radars provide higher confidence
    hail detection through data fusion.

    Args:
        lat: Latitude
        lon: Longitude
        min_overlap: Minimum number of radars required

    Returns:
        Dict with coverage info and radar list
    """
    coverages = find_covering_radars(lat, lon, max_distance_km=200, max_radars=10)

    # Count radars with good coverage
    good_coverage = [c for c in coverages if c.coverage_quality in ('excellent', 'good')]

    return {
        'location': {'lat': lat, 'lon': lon},
        'total_radars_in_range': len(coverages),
        'radars_with_good_coverage': len(good_coverage),
        'meets_multi_radar_threshold': len(good_coverage) >= min_overlap,
        'primary_radar': coverages[0].radar.site_code if coverages else None,
        'coverage_details': [
            {
                'site_code': c.radar.site_code,
                'name': c.radar.name,
                'country': c.radar.country,
                'distance_km': round(c.distance_km, 1),
                'bearing_deg': round(c.bearing_deg, 1),
                'quality': c.coverage_quality,
                'data_source': c.radar.data_source
            }
            for c in coverages
        ]
    }


def get_tornado_alley_radars() -> List[RadarSite]:
    """Get all radars in Tornado Alley (priority 1 hail region)."""
    tornado_alley_states = ['OK', 'KS', 'NE', 'TX', 'CO']
    radars = []
    for state in tornado_alley_states:
        radars.extend(find_radars_by_state(state))
    return radars


def get_canadian_prairie_radars() -> List[RadarSite]:
    """Get all radars in Canadian Prairies (priority 1 hail region)."""
    prairie_provinces = ['AB', 'SK', 'MB']
    radars = []
    for province in prairie_provinces:
        radars.extend(find_radars_by_state(province))
    return radars


# Test function
if __name__ == '__main__':
    print("=" * 60)
    print("RADAR COVERAGE FINDER TEST")
    print("=" * 60)

    # Test locations
    test_locations = [
        ("Denver, CO", 39.7392, -104.9903),
        ("Oklahoma City, OK", 35.4676, -97.5164),
        ("Calgary, AB", 51.0447, -114.0719),
        ("Mexico City, MX", 19.4326, -99.1332),
        ("Goodland, KS", 39.3508, -101.7100),
    ]

    for name, lat, lon in test_locations:
        print(f"\n{name} ({lat}, {lon})")
        print("-" * 40)

        coverages = find_covering_radars(lat, lon, max_radars=3)

        if coverages:
            for c in coverages:
                primary = " [PRIMARY]" if c.is_primary else ""
                print(f"  {c.radar.site_code} ({c.radar.country}): "
                      f"{c.distance_km:.1f}km, {c.coverage_quality}{primary}")
        else:
            print("  No radar coverage found")

    # Test multi-radar coverage
    print("\n" + "=" * 60)
    print("MULTI-RADAR COVERAGE TEST")
    print("=" * 60)

    multi = get_multi_radar_coverage(35.4676, -97.5164)  # OKC
    print(f"\nOklahoma City multi-radar coverage:")
    print(f"  Total radars in range: {multi['total_radars_in_range']}")
    print(f"  Good coverage radars: {multi['radars_with_good_coverage']}")
    print(f"  Primary radar: {multi['primary_radar']}")

    # Test Tornado Alley radars
    print("\n" + "=" * 60)
    print("TORNADO ALLEY RADARS")
    print("=" * 60)

    ta_radars = get_tornado_alley_radars()
    print(f"\nTotal Tornado Alley radars: {len(ta_radars)}")
    by_state = {}
    for r in ta_radars:
        by_state[r.state_province] = by_state.get(r.state_province, 0) + 1
    for state, count in sorted(by_state.items()):
        print(f"  {state}: {count}")

    print("\nRadar coverage finder ready!")
