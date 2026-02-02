"""
Fleet Location Intelligence System
The PDR Goldmine - Find thousands of vehicles after hail storms

Queries OpenStreetMap for fleet locations in these categories:

HIGH VALUE TARGETS:
1. Car Dealerships - 150+ vehicles each
2. Rental Car Locations - 80+ vehicles each
3. Parking Structures - 300+ vehicles each
4. Municipal Fleets - Police, fire, city vehicles
5. Utility Companies - Service trucks

SERVICE COMPANIES (comprehensive list):
6. HVAC, Plumbing, Electrical contractors
7. Landscaping, Lawn care, Tree service
8. Roofing, Siding, Gutter, Fence contractors
9. Pest control, Pool service
10. Painting, Flooring, Concrete, Paving
11. Restoration, Septic, Portable toilets
12. Distribution, Delivery, Courier
13. Property management, Janitorial

OTHER TARGETS:
14. Delivery/Logistics warehouses
15. Body Shops
16. Golf Courses (luxury vehicles)
17. Large Apartments
18. Schools/Universities
19. Hospitals
20. Event Venues
21. Insurance Offices (partnership)
22. Taxi/Rideshare

NOTE: Hotels removed - guests are travelers, not fleet customers
"""

import sqlite3
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import requests

# Import canonical taxonomy
from src.business.category_taxonomy import (
    CATEGORY_TAXONOMY,
    normalize_category_key,
    get_category,
    get_osm_tags_for_category,
    get_keywords_for_category,
    estimate_vehicles,
    detect_category_from_tags,
)

logger = logging.getLogger('FleetLocations')


@dataclass
class FleetLocation:
    """Represents a fleet location with all intelligence data"""
    id: Optional[int] = None
    name: str = ""
    category: str = ""
    subcategory: str = ""
    brand: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "US"
    lat: float = 0.0
    lon: float = 0.0

    # Contact
    phone: str = ""
    email: str = ""
    website: str = ""
    manager_name: str = ""
    manager_title: str = ""
    fleet_manager_name: str = ""
    fleet_manager_phone: str = ""
    decision_maker: str = ""
    best_contact_method: str = "phone"
    contact_notes: str = ""

    # Vehicle data
    estimated_vehicles: int = 50
    vehicle_confidence: str = "medium"
    lot_size_sqm: int = 0
    parking_type: str = "outdoor_uncovered"
    vehicle_types: List[str] = field(default_factory=list)
    luxury_vehicles: bool = False
    average_vehicle_value: int = 35000

    # Accessibility
    accessibility: str = "public"
    requires_appointment: bool = False
    has_security_gate: bool = False
    gate_code: str = ""
    security_guard: bool = False
    can_canvas_lot: bool = True
    operating_hours: str = ""
    best_approach_time: str = ""
    access_restrictions: str = ""
    parking_fee: bool = False

    # CRM
    worked_before: bool = False
    last_visit_date: str = ""
    num_previous_visits: int = 0
    conversion_rate: float = 0.0
    avg_revenue_per_vehicle: float = 1500.0
    total_revenue_historical: float = 0.0
    customer_satisfaction: str = ""
    payment_speed: str = ""
    notes: str = ""
    internal_champion: str = ""

    # Competition
    competitors_present: List[str] = field(default_factory=list)
    competitor_last_seen: str = ""
    market_saturation: str = "low"

    # OSM data
    osm_id: str = ""
    osm_type: str = ""

    # Metadata
    data_source: str = "osm"
    verified: bool = False
    verified_date: str = ""


class OSMQueryBuilder:
    """Build Overpass API queries for fleet locations"""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    @property
    def CATEGORY_QUERIES(self) -> Dict:
        """
        Backwards-compatible property that returns category configs in legacy format.
        Maps from canonical taxonomy to the old CATEGORY_QUERIES structure.
        """
        result = {}
        for key, config in CATEGORY_TAXONOMY.items():
            # Handle osm_tags - can be dict or list of dicts
            osm_tags = config.get('osm_tags', {})
            if isinstance(osm_tags, dict):
                tags = [osm_tags] if osm_tags else []
            else:
                tags = osm_tags  # Already a list

            # Handle keywords/tags field (new taxonomy uses 'tags' for keywords)
            keywords = config.get('keywords', []) or config.get('tags', [])

            result[key] = {
                'tags': tags,
                'name_filters': keywords,
                'vehicle_estimate': config.get('est_vehicles', 10) or config.get('min_vehicles', 10),
            }
            # Copy any extra fields
            if config.get('airport_multiplier'):
                result[key]['airport_multiplier'] = config['airport_multiplier']
            if config.get('capacity_field'):
                result[key]['capacity_field'] = config['capacity_field']
            if config.get('filter_parking_types'):
                result[key]['filter_parking_types'] = config['filter_parking_types']
            if config.get('subcategories'):
                result[key]['subcategories'] = config['subcategories']
            if config.get('luxury_likely'):
                result[key]['luxury_likely'] = config['luxury_likely']
            if config.get('min_for_interest'):
                result[key]['min_for_interest'] = config['min_for_interest']
        return result

    # Legacy CATEGORY_QUERIES dict removed - now uses taxonomy via property above

    def build_query(self, category: str, bbox: Tuple[float, float, float, float],
                   timeout: int = 60) -> str:
        """
        Build Overpass QL query for a category

        Args:
            category: Fleet category
            bbox: (south, west, north, east) bounding box
            timeout: Query timeout in seconds
        """
        # Normalize category key to handle legacy keys
        category = normalize_category_key(category)
        south, west, north, east = bbox

        config = self.CATEGORY_QUERIES.get(category, {})
        tags = config.get('tags', [])

        if not tags:
            return ""

        # Build query parts
        query_parts = []
        for tag_set in tags:
            for key, value in tag_set.items():
                if value == '*':
                    query_parts.append(f'  node["{key}"]({south},{west},{north},{east});')
                    query_parts.append(f'  way["{key}"]({south},{west},{north},{east});')
                else:
                    query_parts.append(f'  node["{key}"="{value}"]({south},{west},{north},{east});')
                    query_parts.append(f'  way["{key}"="{value}"]({south},{west},{north},{east});')

        query = f"""
[out:json][timeout:{timeout}];
(
{chr(10).join(query_parts)}
);
out center meta;
"""
        return query

    def build_radius_query(self, categories: List[str],
                           lat: float, lon: float,
                           radius_meters: int,
                           timeout: int = 60) -> str:
        """
        Build Overpass QL query for radius search.

        Uses 'around' syntax: node["tag"](around:radius,lat,lon)

        Args:
            categories: List of category names (e.g., ['car_dealership', 'car_rental'])
            lat: Center latitude
            lon: Center longitude
            radius_meters: Search radius in meters
            timeout: Query timeout in seconds

        Returns:
            Overpass QL query string
        """
        # Normalize all category keys
        categories = [normalize_category_key(c) for c in categories]

        parts = [f'[out:json][timeout:{timeout}];', '(']

        for category in categories:
            if category not in self.CATEGORY_QUERIES:
                continue
            cat_config = self.CATEGORY_QUERIES[category]
            for tag_dict in cat_config.get('tags', []):
                for tag_key, tag_value in tag_dict.items():
                    if tag_value == '*':
                        parts.append(
                            f'  node["{tag_key}"](around:{radius_meters},{lat},{lon});'
                        )
                        parts.append(
                            f'  way["{tag_key}"](around:{radius_meters},{lat},{lon});'
                        )
                    else:
                        parts.append(
                            f'  node["{tag_key}"="{tag_value}"](around:{radius_meters},{lat},{lon});'
                        )
                        parts.append(
                            f'  way["{tag_key}"="{tag_value}"](around:{radius_meters},{lat},{lon});'
                        )

        parts.append(');')
        parts.append('out center meta;')
        return '\n'.join(parts)

    def execute_query(self, query: str) -> Dict:
        """Execute Overpass API query"""
        try:
            response = requests.post(
                self.OVERPASS_URL,
                data={'data': query},
                timeout=120
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Overpass API error: {e}")
            return {'elements': []}


class FleetLocationManager:
    """Manage fleet locations database and queries"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.osm = OSMQueryBuilder()
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent.parent.parent / 'database' / 'schema_fleet_locations.sql'

        if schema_path.exists():
            with sqlite3.connect(self.db_path) as conn:
                with open(schema_path, encoding='utf-8') as f:
                    conn.executescript(f.read())
                conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def query_osm_for_category(self, category: str, city: str, state: str,
                                bbox: Tuple[float, float, float, float] = None) -> List[FleetLocation]:
        """
        Query OSM for fleet locations in a category

        Args:
            category: Fleet category (car_dealership, car_rental, etc.)
            city: City name for address
            state: State abbreviation
            bbox: Optional bounding box, otherwise use city defaults
        """
        # Normalize category key to handle legacy keys (e.g., rental_car -> car_rental)
        category = normalize_category_key(category)

        # Default bounding boxes for major cities
        CITY_BOXES = {
            'oklahoma city': (35.30, -97.70, 35.60, -97.35),
            'dallas': (32.60, -97.00, 33.00, -96.50),
            'denver': (39.60, -105.10, 39.90, -104.80),
            'wichita': (37.55, -97.50, 37.80, -97.20),
            'tulsa': (35.95, -96.10, 36.25, -95.80),
            'amarillo': (35.15, -101.95, 35.30, -101.75),
            'lubbock': (33.45, -101.95, 33.65, -101.75),
            'san antonio': (29.30, -98.70, 29.60, -98.30),
            'houston': (29.55, -95.60, 30.00, -95.10),
            'austin': (30.15, -97.90, 30.45, -97.55),
        }

        if bbox is None:
            city_key = city.lower().strip()
            bbox = CITY_BOXES.get(city_key, (35.30, -97.70, 35.60, -97.35))

        logger.info(f"Querying OSM for {category} in {city}, {state}")

        # Build and execute query
        query = self.osm.build_query(category, bbox)
        if not query:
            logger.warning(f"No query configured for category: {category}")
            return []

        result = self.osm.execute_query(query)
        elements = result.get('elements', [])

        logger.info(f"Found {len(elements)} raw OSM elements for {category}")

        # Convert to FleetLocation objects
        locations = []
        config = self.osm.CATEGORY_QUERIES.get(category, {})
        name_filters = [f.lower() for f in config.get('name_filters', [])]
        vehicle_estimate = config.get('vehicle_estimate', 50)

        for elem in elements:
            tags = elem.get('tags', {})
            name = tags.get('name', '')

            # Skip if no name
            if not name:
                continue

            # Get coordinates
            if elem.get('type') == 'way':
                lat = elem.get('center', {}).get('lat', 0)
                lon = elem.get('center', {}).get('lon', 0)
            else:
                lat = elem.get('lat', 0)
                lon = elem.get('lon', 0)

            if not lat or not lon:
                continue

            # Estimate vehicles based on capacity or default
            vehicles = vehicle_estimate
            if 'capacity' in tags:
                try:
                    vehicles = int(tags['capacity'])
                except:
                    pass

            # Check for luxury brands
            name_lower = name.lower()
            luxury = any(lux in name_lower for lux in
                        ['bmw', 'mercedes', 'audi', 'lexus', 'porsche', 'jaguar', 'tesla', 'maserati', 'ferrari', 'lamborghini'])

            # Determine subcategory
            subcategory = ""
            if category == 'car_dealership':
                if luxury:
                    subcategory = "luxury"
                elif any(t in name_lower for t in ['used', 'pre-owned']):
                    subcategory = "used"
                else:
                    subcategory = "new"

            # Extract brand
            brand = ""
            brands = ['chevrolet', 'ford', 'toyota', 'honda', 'nissan', 'hyundai', 'kia',
                     'bmw', 'mercedes', 'audi', 'lexus', 'volkswagen', 'subaru', 'mazda']
            for b in brands:
                if b in name_lower:
                    brand = b.title()
                    break

            # Build address
            addr_parts = []
            if tags.get('addr:housenumber'):
                addr_parts.append(tags['addr:housenumber'])
            if tags.get('addr:street'):
                addr_parts.append(tags['addr:street'])
            address = ' '.join(addr_parts) if addr_parts else ""

            addr_city = tags.get('addr:city', city)
            addr_state = tags.get('addr:state', state)
            zip_code = tags.get('addr:postcode', '')

            # Create location
            location = FleetLocation(
                name=name,
                category=category,
                subcategory=subcategory,
                brand=brand,
                address=address,
                city=addr_city,
                state=addr_state,
                zip_code=zip_code,
                lat=lat,
                lon=lon,
                phone=tags.get('phone', tags.get('contact:phone', '')),
                email=tags.get('email', tags.get('contact:email', '')),
                website=tags.get('website', tags.get('contact:website', '')),
                estimated_vehicles=vehicles,
                luxury_vehicles=luxury,
                operating_hours=tags.get('opening_hours', ''),
                osm_id=str(elem.get('id', '')),
                osm_type=elem.get('type', ''),
                data_source='osm'
            )

            # Set accessibility based on category
            if category in ['car_dealership', 'car_rental', 'body_shop']:
                location.accessibility = 'public'
                location.can_canvas_lot = True
            elif category in ['municipal', 'utility']:
                location.accessibility = 'private_open'
                location.can_canvas_lot = False
            elif category in ['golf_course']:
                location.accessibility = 'private_gated'
                location.can_canvas_lot = False
                location.luxury_vehicles = True
            elif category in ['apartment']:
                location.accessibility = 'private_open'
                location.can_canvas_lot = True

            # Set average revenue
            if luxury:
                location.avg_revenue_per_vehicle = 2500
                location.average_vehicle_value = 65000
            elif category in ['golf_course', 'car_dealership']:
                location.avg_revenue_per_vehicle = 2000
            elif category == 'car_rental':
                location.avg_revenue_per_vehicle = 1800

            locations.append(location)

        logger.info(f"Processed {len(locations)} valid locations for {category}")
        return locations

    def save_locations(self, locations: List[FleetLocation]) -> int:
        """Save locations to database, return count of new records"""
        saved = 0

        with self._get_conn() as conn:
            for loc in locations:
                # Check if exists by OSM ID
                existing = conn.execute(
                    "SELECT id FROM fleet_locations WHERE osm_id = ? AND osm_type = ?",
                    (loc.osm_id, loc.osm_type)
                ).fetchone()

                if existing:
                    continue

                # Insert new location
                conn.execute("""
                    INSERT INTO fleet_locations (
                        name, category, subcategory, brand, address, city, state,
                        zip_code, country, lat, lon, phone, email, website,
                        manager_name, manager_title, fleet_manager_name, fleet_manager_phone,
                        decision_maker, best_contact_method, contact_notes,
                        estimated_vehicles, vehicle_confidence, lot_size_sqm, parking_type,
                        vehicle_types, luxury_vehicles, average_vehicle_value,
                        accessibility, requires_appointment, has_security_gate, gate_code,
                        security_guard, can_canvas_lot, operating_hours, best_approach_time,
                        access_restrictions, parking_fee,
                        worked_before, num_previous_visits, avg_revenue_per_vehicle,
                        market_saturation, osm_id, osm_type, data_source, verified
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?
                    )
                """, (
                    loc.name, loc.category, loc.subcategory, loc.brand, loc.address,
                    loc.city, loc.state, loc.zip_code, loc.country, loc.lat, loc.lon,
                    loc.phone, loc.email, loc.website, loc.manager_name, loc.manager_title,
                    loc.fleet_manager_name, loc.fleet_manager_phone, loc.decision_maker,
                    loc.best_contact_method, loc.contact_notes,
                    loc.estimated_vehicles, loc.vehicle_confidence, loc.lot_size_sqm,
                    loc.parking_type, json.dumps(loc.vehicle_types), loc.luxury_vehicles,
                    loc.average_vehicle_value, loc.accessibility, loc.requires_appointment,
                    loc.has_security_gate, loc.gate_code, loc.security_guard, loc.can_canvas_lot,
                    loc.operating_hours, loc.best_approach_time, loc.access_restrictions,
                    loc.parking_fee, loc.worked_before, loc.num_previous_visits,
                    loc.avg_revenue_per_vehicle, loc.market_saturation,
                    loc.osm_id, loc.osm_type, loc.data_source, loc.verified
                ))
                saved += 1

            conn.commit()

        return saved

    def seed_city(self, city: str, state: str,
                  bbox: Tuple[float, float, float, float] = None,
                  categories: List[str] = None) -> Dict[str, int]:
        """
        Seed database with all fleet locations for a city

        Args:
            city: City name
            state: State abbreviation
            bbox: Bounding box (south, west, north, east)
            categories: List of categories to query, or None for all
        """
        if categories is None:
            categories = list(self.osm.CATEGORY_QUERIES.keys())

        results = {}
        total_saved = 0

        for category in categories:
            logger.info(f"Seeding {category} for {city}, {state}...")

            # Query OSM
            locations = self.query_osm_for_category(category, city, state, bbox)

            # Save to database
            saved = self.save_locations(locations)
            results[category] = saved
            total_saved += saved

            logger.info(f"  Saved {saved} new {category} locations")

            # Rate limit to be nice to OSM
            time.sleep(1)

        results['total'] = total_saved
        return results

    def get_locations_in_bbox(self, south: float, west: float, north: float, east: float,
                             categories: List[str] = None) -> List[Dict]:
        """Get all locations within a bounding box"""
        with self._get_conn() as conn:
            query = """
                SELECT fl.*, fc.icon, fc.color, fc.tier
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                WHERE fl.lat BETWEEN ? AND ?
                  AND fl.lon BETWEEN ? AND ?
            """
            params = [south, north, west, east]

            if categories:
                placeholders = ','.join('?' * len(categories))
                query += f" AND fl.category IN ({placeholders})"
                params.extend(categories)

            query += " ORDER BY fc.tier, fl.estimated_vehicles DESC"

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_locations_near_point(self, lat: float, lon: float, radius_km: float = 50,
                                 categories: List[str] = None,
                                 min_vehicles: int = 0) -> List[Dict]:
        """Get locations within radius of a point"""
        import math

        # Approximate bounding box
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * 0.85)

        with self._get_conn() as conn:
            query = """
                SELECT fl.*, fc.icon, fc.color, fc.tier
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                WHERE fl.lat BETWEEN ? AND ?
                  AND fl.lon BETWEEN ? AND ?
                  AND fl.estimated_vehicles >= ?
            """
            params = [
                lat - lat_delta, lat + lat_delta,
                lon - lon_delta, lon + lon_delta,
                min_vehicles
            ]

            if categories:
                placeholders = ','.join('?' * len(categories))
                query += f" AND fl.category IN ({placeholders})"
                params.extend(categories)

            query += " ORDER BY fc.tier, fl.estimated_vehicles DESC LIMIT 1000"

            rows = conn.execute(query, params).fetchall()

            # Calculate actual distance and filter
            results = []
            for row in rows:
                loc = dict(row)
                # Haversine distance
                lat1, lon1 = math.radians(lat), math.radians(lon)
                lat2, lon2 = math.radians(loc['lat']), math.radians(loc['lon'])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance = 6371 * c  # km

                if distance <= radius_km:
                    loc['distance_km'] = round(distance, 2)
                    results.append(loc)

            # Sort by tier then distance
            results.sort(key=lambda x: (x.get('tier', 2), x['distance_km']))
            return results[:500]

    def get_category_summary(self) -> List[Dict]:
        """Get summary of locations by category"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT
                    fl.category,
                    fc.display_name,
                    fc.icon,
                    fc.color,
                    fc.tier,
                    COUNT(fl.id) as location_count,
                    SUM(fl.estimated_vehicles) as total_vehicles,
                    ROUND(AVG(fl.estimated_vehicles), 0) as avg_vehicles,
                    ROUND(SUM(fl.estimated_vehicles * fl.avg_revenue_per_vehicle), 0) as potential_revenue
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                GROUP BY fl.category
                ORDER BY fc.tier, location_count DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def get_location_count(self) -> int:
        """Get total location count"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) FROM fleet_locations").fetchone()
            return row[0] if row else 0

    def search_locations(self, query: str, limit: int = 50) -> List[Dict]:
        """Search locations by name, address, or category"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT fl.*, fc.icon, fc.color
                FROM fleet_locations fl
                LEFT JOIN fleet_categories fc ON fl.category = fc.category
                WHERE fl.name LIKE ?
                   OR fl.address LIKE ?
                   OR fl.city LIKE ?
                   OR fl.category LIKE ?
                ORDER BY fl.estimated_vehicles DESC
                LIMIT ?
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%', limit)).fetchall()
            return [dict(row) for row in rows]


def seed_oklahoma_city():
    """Seed Oklahoma City with fleet locations"""
    from pathlib import Path

    db_path = Path(__file__).parent.parent.parent / 'database' / 'hailtracker_pro.db'
    manager = FleetLocationManager(str(db_path))

    # Oklahoma City bounding box (expanded)
    okc_bbox = (35.25, -97.75, 35.65, -97.30)

    print("Seeding Oklahoma City fleet locations...")
    print("=" * 50)

    results = manager.seed_city(
        city="Oklahoma City",
        state="OK",
        bbox=okc_bbox
    )

    print("\nResults by category:")
    for category, count in results.items():
        if category != 'total':
            print(f"  {category}: {count}")

    print(f"\nTotal new locations: {results['total']}")
    print(f"Total in database: {manager.get_location_count()}")

    # Show category summary
    print("\nCategory Summary:")
    for cat in manager.get_category_summary():
        print(f"  {cat['icon']} {cat['display_name']}: {cat['location_count']} locations, "
              f"~{cat['total_vehicles']:,} vehicles, ${cat['potential_revenue']:,.0f} potential")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    seed_oklahoma_city()
