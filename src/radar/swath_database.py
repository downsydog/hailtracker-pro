"""
Swath Database Manager
Handles storage and retrieval of hail swaths and detections
"""

import sqlite3
import json
import os
from typing import List, Dict, Optional
from datetime import datetime

from src.radar.swath_generator import SwathGenerator, HailDetection


class SwathDatabase:
    """Manage hail swath data in database"""

    def __init__(self, db_path='data/hailtracker_crm.db'):
        """
        Initialize swath database

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create swath tables if they don't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        schema_path = 'src/db/swath_schema.sql'
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema = f.read()

            conn = sqlite3.connect(self.db_path)
            conn.executescript(schema)
            conn.commit()
            conn.close()

            print(f"Swath database initialized: {self.db_path}")
        else:
            print(f"Warning: Schema file not found: {schema_path}")

    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ========================================================================
    # CREATE EVENTS
    # ========================================================================

    def create_event_from_detections(
        self,
        detections: List[HailDetection],
        event_name: str = None,
        data_source: str = 'NEXRAD'
    ) -> int:
        """
        Create hail event from detection data

        Args:
            detections: List of HailDetection objects
            event_name: Optional event name (auto-generated if None)
            data_source: Data source ('NEXRAD', 'Social Media', etc.)

        Returns:
            Event ID

        Example:
            >>> detections = [
            ...     HailDetection(32.7, -96.8, 1.75, '2024-11-15T14:00:00'),
            ...     HailDetection(32.8, -96.7, 2.00, '2024-11-15T14:10:00'),
            ... ]
            >>> event_id = db.create_event_from_detections(detections)
            >>> print(f"Created event #{event_id}")
        """

        if not detections:
            raise ValueError("No detections provided")

        # Sort by time
        sorted_detections = sorted(detections, key=lambda x: x.timestamp)

        # Extract event characteristics
        start_time = sorted_detections[0].timestamp
        end_time = sorted_detections[-1].timestamp
        event_date = datetime.fromisoformat(start_time).date().isoformat()

        # Calculate center (weighted by hail size)
        total_weight = sum(d.hail_size for d in detections)
        center_lat = sum(d.lat * d.hail_size for d in detections) / total_weight
        center_lon = sum(d.lon * d.hail_size for d in detections) / total_weight

        # Hail statistics
        max_hail = max(d.hail_size for d in detections)
        avg_hail = sum(d.hail_size for d in detections) / len(detections)

        # Reflectivity statistics
        reflectivities = [d.reflectivity for d in detections if d.reflectivity is not None]
        max_reflectivity = max(reflectivities) if reflectivities else None
        avg_reflectivity = sum(reflectivities) / len(reflectivities) if reflectivities else None

        # Storm motion (average of all detections)
        motions_dir = [d.storm_motion_dir for d in detections if d.storm_motion_dir is not None]
        motions_speed = [d.storm_motion_speed for d in detections if d.storm_motion_speed is not None]

        storm_motion_dir = sum(motions_dir) / len(motions_dir) if motions_dir else None
        storm_motion_speed = sum(motions_speed) / len(motions_speed) if motions_speed else None

        # Generate swath using auto-selection
        swath = SwathGenerator.auto_generate_swath(detections=detections)
        swath_area = SwathGenerator.calculate_swath_area(swath)
        swath_method = swath['properties']['method']

        # Store swath as GeoJSON
        swath_json = json.dumps({
            'type': swath['type'],
            'coordinates': swath['coordinates']
        })

        # Generate event name if not provided
        if not event_name:
            location = self._get_location_name(center_lat, center_lon)
            date_str = datetime.fromisoformat(start_time).strftime('%b %d %Y')
            event_name = f"{location} - {date_str}"

        # Insert event
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hail_events (
                event_name, event_date, start_time, end_time,
                center_lat, center_lon, swath_polygon, swath_area_sqmi,
                max_hail_size, avg_hail_size, max_reflectivity, avg_reflectivity,
                storm_motion_dir, storm_motion_speed,
                swath_method, num_detections, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_name, event_date, start_time, end_time,
            center_lat, center_lon, swath_json, swath_area,
            max_hail, avg_hail, max_reflectivity, avg_reflectivity,
            storm_motion_dir, storm_motion_speed,
            swath_method, len(detections), data_source
        ))

        event_id = cursor.lastrowid

        # Insert individual detections
        for detection in detections:
            cursor.execute("""
                INSERT INTO hail_detections (
                    event_id, detection_time, lat, lon,
                    hail_size, reflectivity,
                    storm_motion_dir, storm_motion_speed,
                    data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id, detection.timestamp, detection.lat, detection.lon,
                detection.hail_size, detection.reflectivity,
                detection.storm_motion_dir, detection.storm_motion_speed,
                data_source
            ))

        conn.commit()
        conn.close()

        print(f"Created hail event #{event_id}: {event_name}")
        print(f"   - {len(detections)} detections")
        print(f"   - Swath area: {swath_area} sq mi")
        print(f"   - Method: {swath_method}")

        return event_id

    def create_event_manual(
        self,
        event_name: str,
        event_date: str,
        center_lat: float,
        center_lon: float,
        max_hail_size: float,
        swath_polygon: Dict = None,
        storm_motion_dir: float = None,
        storm_motion_speed: float = None,
        duration_minutes: float = None,
        data_source: str = 'Manual'
    ) -> int:
        """
        Create hail event manually (without radar detections)

        Args:
            event_name: Event name
            event_date: Date (YYYY-MM-DD)
            center_lat: Center latitude
            center_lon: Center longitude
            max_hail_size: Maximum hail size (inches)
            swath_polygon: Optional pre-generated swath polygon
            storm_motion_dir: Storm direction (degrees)
            storm_motion_speed: Storm speed (mph)
            duration_minutes: Storm duration
            data_source: Data source

        Returns:
            Event ID
        """

        # Generate swath if not provided
        if swath_polygon is None:
            swath_polygon = SwathGenerator.auto_generate_swath(
                center_lat=center_lat,
                center_lon=center_lon,
                hail_size=max_hail_size,
                storm_motion_dir=storm_motion_dir,
                storm_motion_speed=storm_motion_speed,
                duration_minutes=duration_minutes
            )

        swath_area = SwathGenerator.calculate_swath_area(swath_polygon)
        swath_method = swath_polygon.get('properties', {}).get('method', 'circular')

        swath_json = json.dumps({
            'type': swath_polygon['type'],
            'coordinates': swath_polygon['coordinates']
        })

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hail_events (
                event_name, event_date, center_lat, center_lon,
                swath_polygon, swath_area_sqmi, max_hail_size,
                storm_motion_dir, storm_motion_speed,
                swath_method, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_name, event_date, center_lat, center_lon,
            swath_json, swath_area, max_hail_size,
            storm_motion_dir, storm_motion_speed,
            swath_method, data_source
        ))

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"Created manual event #{event_id}: {event_name}")

        return event_id

    # ========================================================================
    # RETRIEVE EVENTS
    # ========================================================================

    def get_event_by_id(self, event_id: int) -> Optional[Dict]:
        """
        Get hail event by ID

        Args:
            event_id: Event ID

        Returns:
            Event dict with parsed swath polygon
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM hail_events WHERE id = ?", (event_id,))
        event = cursor.fetchone()
        conn.close()

        if not event:
            return None

        event_dict = dict(event)

        # Parse swath polygon JSON
        if event_dict['swath_polygon']:
            event_dict['swath_polygon'] = json.loads(event_dict['swath_polygon'])

        return event_dict

    def get_all_events(self, limit: int = 100) -> List[Dict]:
        """
        Get all hail events

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dicts
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hail_events
            ORDER BY event_date DESC, start_time DESC
            LIMIT ?
        """, (limit,))

        events = cursor.fetchall()
        conn.close()

        result = []
        for event in events:
            event_dict = dict(event)
            if event_dict['swath_polygon']:
                event_dict['swath_polygon'] = json.loads(event_dict['swath_polygon'])
            result.append(event_dict)

        return result

    def get_events_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get events within date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of event dicts
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hail_events
            WHERE event_date BETWEEN ? AND ?
            ORDER BY event_date DESC, start_time DESC
        """, (start_date, end_date))

        events = cursor.fetchall()
        conn.close()

        result = []
        for event in events:
            event_dict = dict(event)
            if event_dict['swath_polygon']:
                event_dict['swath_polygon'] = json.loads(event_dict['swath_polygon'])
            result.append(event_dict)

        return result

    def get_event_detections(self, event_id: int) -> List[Dict]:
        """
        Get all detections for an event

        Args:
            event_id: Event ID

        Returns:
            List of detection dicts
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hail_detections
            WHERE event_id = ?
            ORDER BY detection_time
        """, (event_id,))

        detections = cursor.fetchall()
        conn.close()

        return [dict(d) for d in detections]

    def get_events_by_location(self, lat: float, lon: float, radius_miles: float = 50) -> List[Dict]:
        """
        Get events near a location

        Args:
            lat: Latitude
            lon: Longitude
            radius_miles: Search radius in miles

        Returns:
            List of event dicts within radius
        """

        # Convert radius to degrees (rough approximation)
        radius_deg = radius_miles / 69.0

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM hail_events
            WHERE ABS(center_lat - ?) < ? AND ABS(center_lon - ?) < ?
            ORDER BY event_date DESC
        """, (lat, radius_deg, lon, radius_deg))

        events = cursor.fetchall()
        conn.close()

        result = []
        for event in events:
            event_dict = dict(event)
            if event_dict['swath_polygon']:
                event_dict['swath_polygon'] = json.loads(event_dict['swath_polygon'])
            result.append(event_dict)

        return result

    def get_events_by_hail_size(self, min_size: float, max_size: float = None) -> List[Dict]:
        """
        Get events by hail size range

        Args:
            min_size: Minimum hail size (inches)
            max_size: Maximum hail size (optional)

        Returns:
            List of event dicts
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        if max_size:
            cursor.execute("""
                SELECT * FROM hail_events
                WHERE max_hail_size BETWEEN ? AND ?
                ORDER BY max_hail_size DESC
            """, (min_size, max_size))
        else:
            cursor.execute("""
                SELECT * FROM hail_events
                WHERE max_hail_size >= ?
                ORDER BY max_hail_size DESC
            """, (min_size,))

        events = cursor.fetchall()
        conn.close()

        result = []
        for event in events:
            event_dict = dict(event)
            if event_dict['swath_polygon']:
                event_dict['swath_polygon'] = json.loads(event_dict['swath_polygon'])
            result.append(event_dict)

        return result

    # ========================================================================
    # UPDATE EVENTS
    # ========================================================================

    def update_event_affected_counts(self, event_id: int, locations: int, vehicles: int):
        """
        Update affected location and vehicle counts

        Args:
            event_id: Event ID
            locations: Number of affected locations
            vehicles: Number of affected vehicles
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE hail_events
            SET affected_locations = ?, estimated_vehicles = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (locations, vehicles, event_id))

        conn.commit()
        conn.close()

    def delete_event(self, event_id: int) -> bool:
        """
        Delete a hail event and its detections

        Args:
            event_id: Event ID

        Returns:
            True if deleted, False if not found
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM hail_events WHERE id = ?", (event_id,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_event_statistics(self) -> Dict:
        """
        Get overall statistics about hail events

        Returns:
            Statistics dict with counts and extremes
        """

        conn = self.get_connection()
        cursor = conn.cursor()

        # Total events
        cursor.execute("SELECT COUNT(*) as count FROM hail_events")
        total_events = cursor.fetchone()['count']

        # Total detections
        cursor.execute("SELECT COUNT(*) as count FROM hail_detections")
        total_detections = cursor.fetchone()['count']

        # Total area affected
        cursor.execute("SELECT SUM(swath_area_sqmi) as total FROM hail_events")
        total_area = cursor.fetchone()['total'] or 0

        # Largest event
        cursor.execute("""
            SELECT event_name, swath_area_sqmi, max_hail_size, event_date
            FROM hail_events
            ORDER BY swath_area_sqmi DESC
            LIMIT 1
        """)
        largest = cursor.fetchone()

        # Most intense (highest reflectivity)
        cursor.execute("""
            SELECT event_name, max_reflectivity, max_hail_size, event_date
            FROM hail_events
            WHERE max_reflectivity IS NOT NULL
            ORDER BY max_reflectivity DESC
            LIMIT 1
        """)
        most_intense = cursor.fetchone()

        # Largest hail
        cursor.execute("""
            SELECT event_name, max_hail_size, event_date
            FROM hail_events
            ORDER BY max_hail_size DESC
            LIMIT 1
        """)
        largest_hail = cursor.fetchone()

        # Events by method
        cursor.execute("""
            SELECT swath_method, COUNT(*) as count
            FROM hail_events
            GROUP BY swath_method
        """)
        by_method = {row['swath_method']: row['count'] for row in cursor.fetchall()}

        # Events by month
        cursor.execute("""
            SELECT strftime('%Y-%m', event_date) as month, COUNT(*) as count
            FROM hail_events
            GROUP BY month
            ORDER BY month DESC
            LIMIT 12
        """)
        by_month = {row['month']: row['count'] for row in cursor.fetchall()}

        # Recent events
        cursor.execute("""
            SELECT event_name, event_date, max_hail_size, swath_area_sqmi
            FROM hail_events
            ORDER BY event_date DESC
            LIMIT 5
        """)
        recent = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'total_events': total_events,
            'total_detections': total_detections,
            'total_area_sqmi': round(total_area, 2),
            'largest_event': dict(largest) if largest else None,
            'most_intense_event': dict(most_intense) if most_intense else None,
            'largest_hail_event': dict(largest_hail) if largest_hail else None,
            'events_by_method': by_method,
            'events_by_month': by_month,
            'recent_events': recent
        }

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_event_geojson(self, event_id: int, filename: str):
        """
        Export event as GeoJSON file

        Args:
            event_id: Event ID
            filename: Output filename
        """

        event = self.get_event_by_id(event_id)
        if not event:
            print(f"Event {event_id} not found")
            return

        detections = self.get_event_detections(event_id)

        # Create features
        features = [
            {
                'type': 'Feature',
                'geometry': event['swath_polygon'],
                'properties': {
                    'name': event['event_name'],
                    'date': event['event_date'],
                    'max_hail': event['max_hail_size'],
                    'area_sqmi': event['swath_area_sqmi'],
                    'method': event['swath_method'],
                    'fill': '#ff6600',
                    'fill-opacity': 0.3,
                    'stroke': '#ff6600',
                    'stroke-width': 2
                }
            }
        ]

        # Add detection points
        for i, detection in enumerate(detections):
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [detection['lon'], detection['lat']]
                },
                'properties': {
                    'name': f"Detection {i+1}",
                    'time': detection['detection_time'],
                    'hail_size': detection['hail_size'],
                    'reflectivity': detection['reflectivity'],
                    'marker-color': '#ff0000',
                    'marker-size': 'small'
                }
            })

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(geojson, f, indent=2)

        print(f"Exported event to {filename}")

    def export_all_events_geojson(self, filename: str, limit: int = 100):
        """
        Export all events as single GeoJSON file

        Args:
            filename: Output filename
            limit: Maximum number of events
        """

        events = self.get_all_events(limit=limit)

        features = []

        # Color scale based on hail size
        def get_color(hail_size):
            if hail_size >= 3.0:
                return '#ff0000'  # Red - severe
            elif hail_size >= 2.0:
                return '#ff6600'  # Orange - large
            elif hail_size >= 1.5:
                return '#ffcc00'  # Yellow - significant
            else:
                return '#00cc00'  # Green - moderate

        for event in events:
            color = get_color(event['max_hail_size'] or 1.0)
            features.append({
                'type': 'Feature',
                'geometry': event['swath_polygon'],
                'properties': {
                    'id': event['id'],
                    'name': event['event_name'],
                    'date': event['event_date'],
                    'max_hail': event['max_hail_size'],
                    'area_sqmi': event['swath_area_sqmi'],
                    'fill': color,
                    'fill-opacity': 0.3,
                    'stroke': color,
                    'stroke-width': 2
                }
            })

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(geojson, f, indent=2)

        print(f"Exported {len(events)} events to {filename}")

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def _get_location_name(self, lat: float, lon: float) -> str:
        """
        Get approximate location name from coordinates

        Simple reverse geocoding based on major cities

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Location name string
        """

        # Major cities in hail-prone areas
        cities = {
            'Dallas': (32.7767, -96.7970),
            'Fort Worth': (32.7555, -97.3308),
            'Oklahoma City': (35.4676, -97.5164),
            'Tulsa': (36.1540, -95.9928),
            'Austin': (30.2672, -97.7431),
            'Houston': (29.7604, -95.3698),
            'San Antonio': (29.4241, -98.4936),
            'Wichita': (37.6872, -97.3301),
            'Kansas City': (39.0997, -94.5786),
            'Denver': (39.7392, -104.9903),
            'Amarillo': (35.2220, -101.8313),
            'Lubbock': (33.5779, -101.8552),
            'Midland': (31.9973, -102.0779),
            'Abilene': (32.4487, -99.7331),
            'Omaha': (41.2565, -95.9345),
            'Des Moines': (41.5868, -93.6250),
            'Minneapolis': (44.9778, -93.2650),
            'St. Louis': (38.6270, -90.1994),
            'Chicago': (41.8781, -87.6298),
            'Nashville': (36.1627, -86.7816),
        }

        min_dist = float('inf')
        closest_city = 'Unknown Location'

        for city, (city_lat, city_lon) in cities.items():
            # Euclidean distance (rough)
            dist = ((lat - city_lat)**2 + (lon - city_lon)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_city = city

        # If very close (< 0.5 degrees ~ 35 miles), use city name
        if min_dist < 0.5:
            return closest_city
        else:
            return f"Near {closest_city}"

    def check_point_in_event(self, event_id: int, lat: float, lon: float) -> bool:
        """
        Check if a point is within an event's swath

        Args:
            event_id: Event ID
            lat: Point latitude
            lon: Point longitude

        Returns:
            True if point is inside swath
        """

        event = self.get_event_by_id(event_id)
        if not event or not event['swath_polygon']:
            return False

        return SwathGenerator.point_in_swath(lat, lon, event['swath_polygon'])

    def find_events_affecting_point(self, lat: float, lon: float) -> List[Dict]:
        """
        Find all events whose swaths contain a given point

        Args:
            lat: Point latitude
            lon: Point longitude

        Returns:
            List of events containing the point
        """

        # First get events near the point (quick filter)
        nearby_events = self.get_events_by_location(lat, lon, radius_miles=100)

        # Then check actual polygon containment
        affecting_events = []
        for event in nearby_events:
            if event['swath_polygon']:
                if SwathGenerator.point_in_swath(lat, lon, event['swath_polygon']):
                    affecting_events.append(event)

        return affecting_events
