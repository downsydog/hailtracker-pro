"""
Geographic utility functions for swath calculations
"""

import math
from typing import Dict, Optional, Tuple, List


class GeoUtils:
    """Geographic calculation utilities"""

    # Earth constants
    MILES_PER_DEGREE_LAT = 69.0  # Approximately constant everywhere
    KM_PER_DEGREE_LAT = 111.0
    EARTH_RADIUS_KM = 6371.0
    EARTH_RADIUS_MILES = 3959.0

    @staticmethod
    def calculate_distance_miles(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula

        Args:
            lat1, lon1: First point
            lat2, lon2: Second point

        Returns:
            Distance in miles

        Example:
            >>> # Distance from Dallas to Fort Worth
            >>> distance = GeoUtils.calculate_distance_miles(
            ...     32.7767, -96.7970,  # Dallas
            ...     32.7555, -97.3308   # Fort Worth
            ... )
            >>> print(f"{distance:.1f} miles")
            30.2 miles
        """
        R = GeoUtils.EARTH_RADIUS_MILES

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        # Haversine formula
        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    @staticmethod
    def calculate_distance_km(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate distance between two points in kilometers

        Args:
            lat1, lon1: First point
            lat2, lon2: Second point

        Returns:
            Distance in kilometers
        """
        R = GeoUtils.EARTH_RADIUS_KM

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    @staticmethod
    def calculate_bearing(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Calculate bearing from point 1 to point 2

        Args:
            lat1, lon1: Starting point
            lat2, lon2: Ending point

        Returns:
            Bearing in degrees (0=North, 90=East, 180=South, 270=West)

        Example:
            >>> # Bearing from Dallas to Oklahoma City
            >>> bearing = GeoUtils.calculate_bearing(
            ...     32.7767, -96.7970,  # Dallas
            ...     35.4676, -97.5164   # OKC
            ... )
            >>> print(f"Direction: {bearing:.0f}° (North)")
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) -
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad))

        bearing = math.degrees(math.atan2(y, x))

        # Normalize to 0-360
        return (bearing + 360) % 360

    @staticmethod
    def offset_position(
        lat: float, lon: float,
        distance_miles: float,
        bearing_deg: float
    ) -> Tuple[float, float]:
        """
        Calculate new position given distance and bearing

        Args:
            lat, lon: Starting position
            distance_miles: Distance to move (miles)
            bearing_deg: Direction to move (degrees, 0=North)

        Returns:
            (new_lat, new_lon) tuple

        Example:
            >>> # 10 miles north of Dallas
            >>> new_lat, new_lon = GeoUtils.offset_position(
            ...     32.7767, -96.7970,
            ...     distance_miles=10,
            ...     bearing_deg=0  # North
            ... )
        """
        R = GeoUtils.EARTH_RADIUS_MILES

        bearing_rad = math.radians(bearing_deg)
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        # Calculate new position
        lat2 = math.asin(
            math.sin(lat_rad) * math.cos(distance_miles / R) +
            math.cos(lat_rad) * math.sin(distance_miles / R) * math.cos(bearing_rad)
        )

        lon2 = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_miles / R) * math.cos(lat_rad),
            math.cos(distance_miles / R) - math.sin(lat_rad) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    @staticmethod
    def offset_position_km(
        lat: float, lon: float,
        distance_km: float,
        bearing_deg: float
    ) -> Tuple[float, float]:
        """
        Calculate new position given distance in km and bearing

        Args:
            lat, lon: Starting position
            distance_km: Distance to move (kilometers)
            bearing_deg: Direction to move (degrees, 0=North)

        Returns:
            (new_lat, new_lon) tuple
        """
        R = GeoUtils.EARTH_RADIUS_KM

        bearing_rad = math.radians(bearing_deg)
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)

        lat2 = math.asin(
            math.sin(lat_rad) * math.cos(distance_km / R) +
            math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(bearing_rad)
        )

        lon2 = lon_rad + math.atan2(
            math.sin(bearing_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
            math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    @staticmethod
    def miles_to_degrees_lat(miles: float) -> float:
        """
        Convert miles to degrees latitude

        Simple conversion (latitude degrees are constant everywhere)
        """
        return miles / GeoUtils.MILES_PER_DEGREE_LAT

    @staticmethod
    def miles_to_degrees_lon(miles: float, at_latitude: float) -> float:
        """
        Convert miles to degrees longitude at given latitude

        Longitude degrees vary by latitude (smaller near poles)
        """
        return miles / (GeoUtils.MILES_PER_DEGREE_LAT * math.cos(math.radians(at_latitude)))

    @staticmethod
    def km_to_degrees_lat(km: float) -> float:
        """Convert kilometers to degrees latitude."""
        return km / GeoUtils.KM_PER_DEGREE_LAT

    @staticmethod
    def km_to_degrees_lon(km: float, at_latitude: float) -> float:
        """Convert kilometers to degrees longitude at given latitude."""
        return km / (GeoUtils.KM_PER_DEGREE_LAT * math.cos(math.radians(at_latitude)))

    @staticmethod
    def degrees_to_miles_lat(degrees: float) -> float:
        """Convert degrees latitude to miles."""
        return degrees * GeoUtils.MILES_PER_DEGREE_LAT

    @staticmethod
    def degrees_to_km_lat(degrees: float) -> float:
        """Convert degrees latitude to kilometers."""
        return degrees * GeoUtils.KM_PER_DEGREE_LAT

    @staticmethod
    def create_circle_points(
        center_lat: float, center_lon: float,
        radius_miles: float,
        num_points: int = 32
    ) -> List[Tuple[float, float]]:
        """
        Create points forming a circle around a center point

        Args:
            center_lat, center_lon: Circle center
            radius_miles: Circle radius in miles
            num_points: Number of points to generate

        Returns:
            List of (lat, lon) tuples
        """
        points = []

        radius_deg_lat = radius_miles / GeoUtils.MILES_PER_DEGREE_LAT
        radius_deg_lon = radius_miles / (
            GeoUtils.MILES_PER_DEGREE_LAT * math.cos(math.radians(center_lat))
        )

        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi

            point_lat = center_lat + radius_deg_lat * math.sin(angle)
            point_lon = center_lon + radius_deg_lon * math.cos(angle)

            points.append((point_lat, point_lon))

        return points

    @staticmethod
    def create_ellipse_points(
        center_lat: float, center_lon: float,
        major_axis_miles: float,
        minor_axis_miles: float,
        rotation_deg: float = 0,
        num_points: int = 48
    ) -> List[Tuple[float, float]]:
        """
        Create points forming an ellipse

        Args:
            center_lat, center_lon: Ellipse center
            major_axis_miles: Major axis length (miles)
            minor_axis_miles: Minor axis length (miles)
            rotation_deg: Rotation angle (degrees, 0=aligned N-S)
            num_points: Number of points to generate

        Returns:
            List of (lat, lon) tuples
        """
        points = []

        # Convert rotation to radians (convert from meteorological to mathematical)
        bearing_rad = math.radians(90 - rotation_deg)

        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi

            # Local coordinates
            x_local = (major_axis_miles / 2) * math.cos(angle)
            y_local = (minor_axis_miles / 2) * math.sin(angle)

            # Rotate
            x_rotated = x_local * math.cos(bearing_rad) - y_local * math.sin(bearing_rad)
            y_rotated = x_local * math.sin(bearing_rad) + y_local * math.cos(bearing_rad)

            # Convert to degrees
            lat_offset = y_rotated / GeoUtils.MILES_PER_DEGREE_LAT
            lon_offset = x_rotated / (
                GeoUtils.MILES_PER_DEGREE_LAT * math.cos(math.radians(center_lat))
            )

            points.append((center_lat + lat_offset, center_lon + lon_offset))

        return points

    @staticmethod
    def point_in_polygon(
        lat: float, lon: float,
        polygon_points: List[Tuple[float, float]]
    ) -> bool:
        """
        Check if a point is inside a polygon using ray casting

        Args:
            lat, lon: Point to check
            polygon_points: List of (lat, lon) tuples defining polygon

        Returns:
            True if point is inside polygon
        """
        n = len(polygon_points)
        inside = False

        j = n - 1
        for i in range(n):
            yi, xi = polygon_points[i]  # lat, lon
            yj, xj = polygon_points[j]

            if ((yi > lat) != (yj > lat)) and \
               (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    @staticmethod
    def calculate_polygon_area_sq_miles(
        points: List[Tuple[float, float]]
    ) -> float:
        """
        Calculate approximate area of polygon in square miles

        Uses Shoelace formula with lat/lon to miles conversion

        Args:
            points: List of (lat, lon) tuples

        Returns:
            Area in square miles (approximate)
        """
        if len(points) < 3:
            return 0.0

        # Get centroid for lon conversion
        avg_lat = sum(p[0] for p in points) / len(points)

        # Convert to local coordinates (miles from first point)
        miles_points = []
        for lat, lon in points:
            y = (lat - points[0][0]) * GeoUtils.MILES_PER_DEGREE_LAT
            x = (lon - points[0][1]) * GeoUtils.MILES_PER_DEGREE_LAT * math.cos(math.radians(avg_lat))
            miles_points.append((x, y))

        # Shoelace formula
        n = len(miles_points)
        area = 0.0

        for i in range(n):
            j = (i + 1) % n
            area += miles_points[i][0] * miles_points[j][1]
            area -= miles_points[j][0] * miles_points[i][1]

        return abs(area) / 2.0

    @staticmethod
    def get_bounding_box(
        points: List[Tuple[float, float]]
    ) -> Tuple[float, float, float, float]:
        """
        Get bounding box of a set of points

        Args:
            points: List of (lat, lon) tuples

        Returns:
            (min_lat, max_lat, min_lon, max_lon)
        """
        lats = [p[0] for p in points]
        lons = [p[1] for p in points]

        return (min(lats), max(lats), min(lons), max(lons))

    @staticmethod
    def get_centroid(
        points: List[Tuple[float, float]]
    ) -> Tuple[float, float]:
        """
        Get centroid of a set of points

        Args:
            points: List of (lat, lon) tuples

        Returns:
            (lat, lon) of centroid
        """
        avg_lat = sum(p[0] for p in points) / len(points)
        avg_lon = sum(p[1] for p in points) / len(points)
        return (avg_lat, avg_lon)

    @staticmethod
    def bearing_to_cardinal(bearing: float) -> str:
        """
        Convert bearing in degrees to cardinal direction

        Args:
            bearing: Bearing in degrees (0-360)

        Returns:
            Cardinal direction string (N, NE, E, etc.)
        """
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        index = round(bearing / 22.5) % 16
        return directions[index]

    @staticmethod
    def meters_to_feet(meters: float) -> float:
        """Convert meters to feet."""
        return meters * 3.28084

    @staticmethod
    def feet_to_meters(feet: float) -> float:
        """Convert feet to meters."""
        return feet / 3.28084

    @staticmethod
    def km_to_miles(km: float) -> float:
        """Convert kilometers to miles."""
        return km * 0.621371

    @staticmethod
    def miles_to_km(miles: float) -> float:
        """Convert miles to kilometers."""
        return miles * 1.60934


def compute_bbox_from_geojson(
    geojson: dict,
    *,
    fallback_center: Optional[Tuple[float, float]] = None,
    fallback_radius_miles: float = 10.0,
) -> Dict[str, object]:
    """
    Compute bounding box from a GeoJSON object with fallback radius for points.

    Supports FeatureCollection, Feature, and bare Geometry objects.
    Supported geometry types: Point, MultiPoint, LineString, MultiLineString,
    Polygon, MultiPolygon.

    For Point/MultiPoint with a single point (or when coordinates produce a
    zero-span bbox), applies fallback_radius_miles to create a real bbox so
    calendar/map fitBounds works.

    Args:
        geojson: GeoJSON dict (Feature, FeatureCollection, or Geometry)
        fallback_center: (lat, lon) to use when no coordinates found
        fallback_radius_miles: radius for point/fallback bbox (default 10mi)

    Returns:
        dict with keys: bbox_min_lat, bbox_max_lat, bbox_min_lon, bbox_max_lon,
                        bbox_source ("geojson", "point_fallback", "center_fallback")
    """

    def _extract_coords(obj: dict) -> List[Tuple[float, float]]:
        """Extract all [lon, lat] coordinate pairs from a GeoJSON object."""
        gtype = obj.get('type', '')

        if gtype == 'FeatureCollection':
            coords = []
            for feat in obj.get('features', []):
                coords.extend(_extract_coords(feat))
            return coords

        if gtype == 'Feature':
            geom = obj.get('geometry')
            return _extract_coords(geom) if geom else []

        raw = obj.get('coordinates')
        if raw is None:
            return []

        if gtype == 'Point':
            return [tuple(raw)]
        elif gtype == 'MultiPoint':
            return [tuple(c) for c in raw]
        elif gtype == 'LineString':
            return [tuple(c) for c in raw]
        elif gtype == 'MultiLineString':
            out = []
            for line in raw:
                out.extend(tuple(c) for c in line)
            return out
        elif gtype == 'Polygon':
            out = []
            for ring in raw:
                out.extend(tuple(c) for c in ring)
            return out
        elif gtype == 'MultiPolygon':
            out = []
            for poly in raw:
                for ring in poly:
                    out.extend(tuple(c) for c in ring)
            return out
        return []

    def _apply_radius(lat: float, lon: float, radius_miles: float, source: str) -> Dict[str, object]:
        lat_deg = radius_miles / 69.0
        cos_lat = math.cos(math.radians(lat))
        lon_deg = radius_miles / (69.0 * cos_lat) if cos_lat > 0.01 else radius_miles / 69.0
        return {
            'bbox_min_lat': lat - lat_deg,
            'bbox_max_lat': lat + lat_deg,
            'bbox_min_lon': lon - lon_deg,
            'bbox_max_lon': lon + lon_deg,
            'bbox_source': source,
        }

    # Extract all coordinates
    coords = _extract_coords(geojson)

    if not coords:
        # No coordinates at all — use fallback center
        if fallback_center:
            return _apply_radius(fallback_center[0], fallback_center[1],
                                 fallback_radius_miles, 'center_fallback')
        return {
            'bbox_min_lat': 0.0, 'bbox_max_lat': 0.0,
            'bbox_min_lon': 0.0, 'bbox_max_lon': 0.0,
            'bbox_source': 'none',
        }

    # GeoJSON is [lon, lat]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    # If bbox collapses to a point (single coord or all coords identical)
    if max_lat - min_lat < 1e-6 and max_lon - min_lon < 1e-6:
        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2
        return _apply_radius(center_lat, center_lon,
                             fallback_radius_miles, 'point_fallback')

    return {
        'bbox_min_lat': min_lat,
        'bbox_max_lat': max_lat,
        'bbox_min_lon': min_lon,
        'bbox_max_lon': max_lon,
        'bbox_source': 'geojson',
    }
