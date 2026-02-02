"""
Geographic Filtering for HailTracker Pro

Filter alerts by coverage area using various methods:
- Bounding box (rectangle)
- Radius from center point
- Named regions (states, metro areas)
- Custom polygons
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Union
from enum import Enum


class FilterType(Enum):
    """Types of geographic filters."""
    BOUNDING_BOX = "bounding_box"
    RADIUS = "radius"
    POLYGON = "polygon"
    NAMED_REGION = "named_region"
    COMPOSITE = "composite"


# Pre-defined regions for common coverage areas
NAMED_REGIONS = {
    # US States (approximate bounding boxes)
    'texas': {'lat_min': 25.84, 'lat_max': 36.50, 'lon_min': -106.65, 'lon_max': -93.51},
    'oklahoma': {'lat_min': 33.62, 'lat_max': 37.00, 'lon_min': -103.00, 'lon_max': -94.43},
    'kansas': {'lat_min': 36.99, 'lat_max': 40.00, 'lon_min': -102.05, 'lon_max': -94.59},
    'nebraska': {'lat_min': 40.00, 'lat_max': 43.00, 'lon_min': -104.05, 'lon_max': -95.31},
    'colorado': {'lat_min': 36.99, 'lat_max': 41.00, 'lon_min': -109.05, 'lon_max': -102.04},
    'missouri': {'lat_min': 35.99, 'lat_max': 40.61, 'lon_min': -95.77, 'lon_max': -89.10},
    'iowa': {'lat_min': 40.38, 'lat_max': 43.50, 'lon_min': -96.64, 'lon_max': -90.14},
    'arkansas': {'lat_min': 33.00, 'lat_max': 36.50, 'lon_min': -94.62, 'lon_max': -89.64},
    'louisiana': {'lat_min': 28.93, 'lat_max': 33.02, 'lon_min': -94.04, 'lon_max': -88.82},
    'minnesota': {'lat_min': 43.50, 'lat_max': 49.38, 'lon_min': -97.24, 'lon_max': -89.49},
    'south_dakota': {'lat_min': 42.48, 'lat_max': 45.95, 'lon_min': -104.06, 'lon_max': -96.44},
    'north_dakota': {'lat_min': 45.94, 'lat_max': 49.00, 'lon_min': -104.05, 'lon_max': -96.55},
    'wyoming': {'lat_min': 40.99, 'lat_max': 45.01, 'lon_min': -111.06, 'lon_max': -104.05},
    'montana': {'lat_min': 44.36, 'lat_max': 49.00, 'lon_min': -116.05, 'lon_max': -104.04},
    'new_mexico': {'lat_min': 31.33, 'lat_max': 37.00, 'lon_min': -109.05, 'lon_max': -103.00},
    'alabama': {'lat_min': 30.22, 'lat_max': 35.01, 'lon_min': -88.47, 'lon_max': -84.89},
    'georgia': {'lat_min': 30.36, 'lat_max': 35.00, 'lon_min': -85.61, 'lon_max': -80.84},
    'tennessee': {'lat_min': 34.98, 'lat_max': 36.68, 'lon_min': -90.31, 'lon_max': -81.65},
    'mississippi': {'lat_min': 30.17, 'lat_max': 35.00, 'lon_min': -91.66, 'lon_max': -88.10},
    'illinois': {'lat_min': 36.97, 'lat_max': 42.51, 'lon_min': -91.51, 'lon_max': -87.02},
    'indiana': {'lat_min': 37.77, 'lat_max': 41.76, 'lon_min': -88.10, 'lon_max': -84.78},
    'ohio': {'lat_min': 38.40, 'lat_max': 42.33, 'lon_min': -84.82, 'lon_max': -80.52},

    # Major Metro Areas (50-mile radius equivalent boxes)
    'dallas_fort_worth': {'lat_min': 32.20, 'lat_max': 33.40, 'lon_min': -97.80, 'lon_max': -96.30},
    'oklahoma_city': {'lat_min': 34.90, 'lat_max': 35.90, 'lon_min': -98.10, 'lon_max': -97.00},
    'denver': {'lat_min': 39.30, 'lat_max': 40.20, 'lon_min': -105.30, 'lon_max': -104.50},
    'kansas_city': {'lat_min': 38.70, 'lat_max': 39.50, 'lon_min': -95.10, 'lon_max': -94.20},
    'omaha': {'lat_min': 40.90, 'lat_max': 41.50, 'lon_min': -96.40, 'lon_max': -95.70},
    'minneapolis': {'lat_min': 44.60, 'lat_max': 45.30, 'lon_min': -93.70, 'lon_max': -92.90},
    'san_antonio': {'lat_min': 29.00, 'lat_max': 29.90, 'lon_min': -99.00, 'lon_max': -98.00},
    'austin': {'lat_min': 29.90, 'lat_max': 30.70, 'lon_min': -98.20, 'lon_max': -97.40},
    'houston': {'lat_min': 29.30, 'lat_max': 30.30, 'lon_min': -96.00, 'lon_max': -94.80},
    'tulsa': {'lat_min': 35.80, 'lat_max': 36.40, 'lon_min': -96.30, 'lon_max': -95.60},
    'wichita': {'lat_min': 37.40, 'lat_max': 38.00, 'lon_min': -97.70, 'lon_max': -97.00},
    'des_moines': {'lat_min': 41.30, 'lat_max': 41.90, 'lon_min': -94.00, 'lon_max': -93.30},
    'st_louis': {'lat_min': 38.30, 'lat_max': 39.00, 'lon_min': -90.70, 'lon_max': -89.90},
    'atlanta': {'lat_min': 33.40, 'lat_max': 34.20, 'lon_min': -84.80, 'lon_max': -83.90},
    'nashville': {'lat_min': 35.80, 'lat_max': 36.50, 'lon_min': -87.20, 'lon_max': -86.40},
    'memphis': {'lat_min': 34.80, 'lat_max': 35.50, 'lon_min': -90.40, 'lon_max': -89.60},
    'chicago': {'lat_min': 41.50, 'lat_max': 42.20, 'lon_min': -88.30, 'lon_max': -87.30},
    'indianapolis': {'lat_min': 39.50, 'lat_max': 40.10, 'lon_min': -86.50, 'lon_max': -85.80},
    'detroit': {'lat_min': 42.10, 'lat_max': 42.70, 'lon_min': -83.50, 'lon_max': -82.80},
    'columbus': {'lat_min': 39.70, 'lat_max': 40.30, 'lon_min': -83.30, 'lon_max': -82.60},

    # Hail Alley regions
    'hail_alley_core': {'lat_min': 33.00, 'lat_max': 42.00, 'lon_min': -104.00, 'lon_max': -95.00},
    'tornado_alley': {'lat_min': 30.00, 'lat_max': 45.00, 'lon_min': -105.00, 'lon_max': -90.00},
    'dixie_alley': {'lat_min': 30.00, 'lat_max': 37.00, 'lon_min': -95.00, 'lon_max': -82.00},
}


@dataclass
class GeoFilter:
    """
    Geographic filter for alert coverage areas.

    Supports multiple filter types:
    - Bounding box: Rectangle defined by lat/lon bounds
    - Radius: Circle defined by center point and radius in miles
    - Named region: Pre-defined state or metro area
    - Polygon: Custom polygon defined by list of vertices
    - Composite: Multiple filters combined with AND/OR logic

    Example:
        # Filter by 50-mile radius from shop location
        filter = GeoFilter.from_radius(32.7767, -96.7970, 50)

        # Filter by named region
        filter = GeoFilter.from_named_region('dallas_fort_worth')

        # Filter by bounding box
        filter = GeoFilter.from_bounds(32.0, 34.0, -98.0, -96.0)

        # Composite filter (multiple regions)
        filter = GeoFilter.composite([
            GeoFilter.from_named_region('dallas_fort_worth'),
            GeoFilter.from_named_region('oklahoma_city')
        ], operator='OR')
    """

    filter_type: FilterType
    name: str = "Custom"

    # Bounding box parameters
    lat_min: Optional[float] = None
    lat_max: Optional[float] = None
    lon_min: Optional[float] = None
    lon_max: Optional[float] = None

    # Radius parameters
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    radius_miles: Optional[float] = None

    # Polygon parameters (list of (lat, lon) tuples)
    polygon_vertices: List[Tuple[float, float]] = field(default_factory=list)

    # Composite parameters
    sub_filters: List['GeoFilter'] = field(default_factory=list)
    composite_operator: str = 'OR'  # 'AND' or 'OR'

    def contains(self, lat: float, lon: float) -> bool:
        """
        Check if a point is within the coverage area.

        Args:
            lat: Latitude of the point
            lon: Longitude of the point

        Returns:
            True if point is within coverage area
        """
        if self.filter_type == FilterType.BOUNDING_BOX:
            return self._check_bounding_box(lat, lon)
        elif self.filter_type == FilterType.RADIUS:
            return self._check_radius(lat, lon)
        elif self.filter_type == FilterType.POLYGON:
            return self._check_polygon(lat, lon)
        elif self.filter_type == FilterType.NAMED_REGION:
            return self._check_bounding_box(lat, lon)
        elif self.filter_type == FilterType.COMPOSITE:
            return self._check_composite(lat, lon)
        return True

    def _check_bounding_box(self, lat: float, lon: float) -> bool:
        """Check if point is within bounding box."""
        if self.lat_min is not None and lat < self.lat_min:
            return False
        if self.lat_max is not None and lat > self.lat_max:
            return False
        if self.lon_min is not None and lon < self.lon_min:
            return False
        if self.lon_max is not None and lon > self.lon_max:
            return False
        return True

    def _check_radius(self, lat: float, lon: float) -> bool:
        """Check if point is within radius."""
        if self.center_lat is None or self.center_lon is None or self.radius_miles is None:
            return True

        distance = self._haversine_distance(
            self.center_lat, self.center_lon,
            lat, lon
        )
        return distance <= self.radius_miles

    def _check_polygon(self, lat: float, lon: float) -> bool:
        """Check if point is within polygon using ray casting."""
        if not self.polygon_vertices or len(self.polygon_vertices) < 3:
            return True

        n = len(self.polygon_vertices)
        inside = False

        p1_lat, p1_lon = self.polygon_vertices[0]
        for i in range(1, n + 1):
            p2_lat, p2_lon = self.polygon_vertices[i % n]

            if lat > min(p1_lat, p2_lat):
                if lat <= max(p1_lat, p2_lat):
                    if lon <= max(p1_lon, p2_lon):
                        if p1_lat != p2_lat:
                            lon_intersect = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                        if p1_lon == p2_lon or lon <= lon_intersect:
                            inside = not inside

            p1_lat, p1_lon = p2_lat, p2_lon

        return inside

    def _check_composite(self, lat: float, lon: float) -> bool:
        """Check composite filter with AND/OR logic."""
        if not self.sub_filters:
            return True

        if self.composite_operator == 'AND':
            return all(f.contains(lat, lon) for f in self.sub_filters)
        else:  # OR
            return any(f.contains(lat, lon) for f in self.sub_filters)

    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles."""
        R = 3959  # Earth's radius in miles

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_bounds(self) -> Optional[Dict[str, float]]:
        """Get bounding box that encompasses the filter area."""
        if self.filter_type == FilterType.BOUNDING_BOX or self.filter_type == FilterType.NAMED_REGION:
            return {
                'lat_min': self.lat_min,
                'lat_max': self.lat_max,
                'lon_min': self.lon_min,
                'lon_max': self.lon_max
            }
        elif self.filter_type == FilterType.RADIUS:
            # Approximate bounding box for radius
            if self.center_lat and self.center_lon and self.radius_miles:
                lat_delta = self.radius_miles / 69.0  # ~69 miles per degree latitude
                lon_delta = self.radius_miles / (69.0 * math.cos(math.radians(self.center_lat)))
                return {
                    'lat_min': self.center_lat - lat_delta,
                    'lat_max': self.center_lat + lat_delta,
                    'lon_min': self.center_lon - lon_delta,
                    'lon_max': self.center_lon + lon_delta
                }
        elif self.filter_type == FilterType.POLYGON and self.polygon_vertices:
            lats = [v[0] for v in self.polygon_vertices]
            lons = [v[1] for v in self.polygon_vertices]
            return {
                'lat_min': min(lats),
                'lat_max': max(lats),
                'lon_min': min(lons),
                'lon_max': max(lons)
            }
        elif self.filter_type == FilterType.COMPOSITE and self.sub_filters:
            # Get union of all sub-filter bounds
            all_bounds = [f.get_bounds() for f in self.sub_filters if f.get_bounds()]
            if all_bounds:
                return {
                    'lat_min': min(b['lat_min'] for b in all_bounds),
                    'lat_max': max(b['lat_max'] for b in all_bounds),
                    'lon_min': min(b['lon_min'] for b in all_bounds),
                    'lon_max': max(b['lon_max'] for b in all_bounds)
                }
        return None

    def describe(self) -> str:
        """Get human-readable description of the filter."""
        if self.filter_type == FilterType.BOUNDING_BOX:
            return f"Bounding box: {self.lat_min:.2f} to {self.lat_max:.2f}N, {self.lon_min:.2f} to {self.lon_max:.2f}W"
        elif self.filter_type == FilterType.RADIUS:
            return f"{self.radius_miles:.0f}-mile radius from ({self.center_lat:.4f}, {self.center_lon:.4f})"
        elif self.filter_type == FilterType.NAMED_REGION:
            return f"Region: {self.name}"
        elif self.filter_type == FilterType.POLYGON:
            return f"Custom polygon with {len(self.polygon_vertices)} vertices"
        elif self.filter_type == FilterType.COMPOSITE:
            sub_desc = [f.name for f in self.sub_filters]
            return f"Composite ({self.composite_operator}): {', '.join(sub_desc)}"
        return "Unknown filter"

    # Factory methods

    @classmethod
    def from_bounds(cls, lat_min: float, lat_max: float,
                    lon_min: float, lon_max: float,
                    name: str = "Custom Bounds") -> 'GeoFilter':
        """Create filter from bounding box coordinates."""
        return cls(
            filter_type=FilterType.BOUNDING_BOX,
            name=name,
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max
        )

    @classmethod
    def from_radius(cls, center_lat: float, center_lon: float,
                    radius_miles: float, name: str = None) -> 'GeoFilter':
        """Create filter from center point and radius."""
        if name is None:
            name = f"{radius_miles:.0f}mi radius"
        return cls(
            filter_type=FilterType.RADIUS,
            name=name,
            center_lat=center_lat,
            center_lon=center_lon,
            radius_miles=radius_miles
        )

    @classmethod
    def from_named_region(cls, region_name: str) -> 'GeoFilter':
        """Create filter from pre-defined region name."""
        region_key = region_name.lower().replace(' ', '_').replace('-', '_')

        if region_key not in NAMED_REGIONS:
            available = ', '.join(sorted(NAMED_REGIONS.keys()))
            raise ValueError(f"Unknown region '{region_name}'. Available: {available}")

        bounds = NAMED_REGIONS[region_key]
        return cls(
            filter_type=FilterType.NAMED_REGION,
            name=region_name.replace('_', ' ').title(),
            lat_min=bounds['lat_min'],
            lat_max=bounds['lat_max'],
            lon_min=bounds['lon_min'],
            lon_max=bounds['lon_max']
        )

    @classmethod
    def from_polygon(cls, vertices: List[Tuple[float, float]],
                     name: str = "Custom Polygon") -> 'GeoFilter':
        """Create filter from polygon vertices (lat, lon tuples)."""
        if len(vertices) < 3:
            raise ValueError("Polygon must have at least 3 vertices")
        return cls(
            filter_type=FilterType.POLYGON,
            name=name,
            polygon_vertices=vertices
        )

    @classmethod
    def composite(cls, filters: List['GeoFilter'],
                  operator: str = 'OR',
                  name: str = "Composite") -> 'GeoFilter':
        """Create composite filter from multiple filters."""
        if operator not in ('AND', 'OR'):
            raise ValueError("Operator must be 'AND' or 'OR'")
        return cls(
            filter_type=FilterType.COMPOSITE,
            name=name,
            sub_filters=filters,
            composite_operator=operator
        )

    @classmethod
    def from_config(cls, config: Union[str, Dict]) -> 'GeoFilter':
        """
        Create filter from configuration string or dict.

        String formats:
            "region:texas" - Named region
            "radius:32.7,-96.8,50" - Lat,lon,miles
            "bounds:32,34,-98,-96" - lat_min,lat_max,lon_min,lon_max

        Dict format:
            {"type": "radius", "lat": 32.7, "lon": -96.8, "miles": 50}
            {"type": "region", "name": "texas"}
            {"type": "bounds", "lat_min": 32, "lat_max": 34, ...}
        """
        if isinstance(config, str):
            return cls._parse_config_string(config)
        elif isinstance(config, dict):
            return cls._parse_config_dict(config)
        else:
            raise ValueError(f"Config must be string or dict, got {type(config)}")

    @classmethod
    def _parse_config_string(cls, config: str) -> 'GeoFilter':
        """Parse configuration string."""
        if ':' not in config:
            # Assume it's a region name
            return cls.from_named_region(config)

        filter_type, params = config.split(':', 1)
        filter_type = filter_type.lower().strip()

        if filter_type == 'region':
            return cls.from_named_region(params.strip())

        elif filter_type == 'radius':
            parts = [float(p.strip()) for p in params.split(',')]
            if len(parts) != 3:
                raise ValueError("Radius format: radius:lat,lon,miles")
            return cls.from_radius(parts[0], parts[1], parts[2])

        elif filter_type == 'bounds':
            parts = [float(p.strip()) for p in params.split(',')]
            if len(parts) != 4:
                raise ValueError("Bounds format: bounds:lat_min,lat_max,lon_min,lon_max")
            return cls.from_bounds(parts[0], parts[1], parts[2], parts[3])

        else:
            raise ValueError(f"Unknown filter type: {filter_type}")

    @classmethod
    def _parse_config_dict(cls, config: Dict) -> 'GeoFilter':
        """Parse configuration dictionary."""
        filter_type = config.get('type', 'bounds').lower()

        if filter_type == 'region':
            return cls.from_named_region(config['name'])

        elif filter_type == 'radius':
            return cls.from_radius(
                config['lat'],
                config['lon'],
                config['miles'],
                config.get('name')
            )

        elif filter_type == 'bounds':
            return cls.from_bounds(
                config['lat_min'],
                config['lat_max'],
                config['lon_min'],
                config['lon_max'],
                config.get('name', 'Custom Bounds')
            )

        elif filter_type == 'polygon':
            return cls.from_polygon(
                config['vertices'],
                config.get('name', 'Custom Polygon')
            )

        else:
            raise ValueError(f"Unknown filter type: {filter_type}")

    def to_dict(self) -> Dict:
        """Convert filter to dictionary for serialization."""
        result = {
            'type': self.filter_type.value,
            'name': self.name
        }

        if self.filter_type == FilterType.BOUNDING_BOX or self.filter_type == FilterType.NAMED_REGION:
            result.update({
                'lat_min': self.lat_min,
                'lat_max': self.lat_max,
                'lon_min': self.lon_min,
                'lon_max': self.lon_max
            })
        elif self.filter_type == FilterType.RADIUS:
            result.update({
                'lat': self.center_lat,
                'lon': self.center_lon,
                'miles': self.radius_miles
            })
        elif self.filter_type == FilterType.POLYGON:
            result['vertices'] = self.polygon_vertices
        elif self.filter_type == FilterType.COMPOSITE:
            result.update({
                'operator': self.composite_operator,
                'filters': [f.to_dict() for f in self.sub_filters]
            })

        return result


def list_named_regions() -> Dict[str, Dict]:
    """Get all available named regions with their bounds."""
    return {
        name: {
            'bounds': bounds,
            'description': name.replace('_', ' ').title()
        }
        for name, bounds in NAMED_REGIONS.items()
    }


def get_suggested_radars(geo_filter: GeoFilter) -> List[str]:
    """
    Suggest NEXRAD radars that cover the filter area.

    Returns list of radar IDs that may provide coverage for the filtered area.
    """
    # NEXRAD radar locations (partial list - main hail belt radars)
    RADAR_LOCATIONS = {
        'KFWS': (32.573, -97.303),  # Dallas-Fort Worth
        'KDFW': (32.939, -96.987),  # Dallas
        'KTLX': (35.333, -97.277),  # Oklahoma City
        'KVNX': (36.741, -98.128),  # Vance AFB, OK
        'KINX': (36.175, -95.565),  # Tulsa
        'KICT': (37.654, -97.442),  # Wichita
        'KDDC': (37.761, -99.968),  # Dodge City
        'KGLD': (39.367, -101.700), # Goodland
        'KOAX': (41.320, -96.367),  # Omaha
        'KUEX': (40.321, -98.442),  # Hastings
        'KLNX': (41.958, -100.576), # North Platte
        'KAMA': (35.233, -101.709), # Amarillo
        'KLBB': (33.654, -101.814), # Lubbock
        'KMAF': (31.943, -102.189), # Midland
        'KSJT': (31.371, -100.493), # San Angelo
        'KEWX': (29.704, -98.028),  # Austin/San Antonio
        'KHGX': (29.472, -95.079),  # Houston
        'KSHV': (32.451, -93.841),  # Shreveport
        'KLZK': (34.836, -92.262),  # Little Rock
        'KSGF': (37.235, -93.400),  # Springfield, MO
        'KEAX': (38.810, -94.264),  # Kansas City
        'KDMX': (41.731, -93.723),  # Des Moines
        'KMPX': (44.849, -93.565),  # Minneapolis
        'KFSD': (43.588, -96.729),  # Sioux Falls
        'KABR': (45.456, -98.413),  # Aberdeen
        'KBIS': (46.771, -100.760), # Bismarck
        'KUDX': (44.125, -102.829), # Rapid City
        'KCYS': (41.152, -104.806), # Cheyenne
        'KFTG': (39.787, -104.546), # Denver
        'KPUX': (38.460, -104.181), # Pueblo
        'KABX': (35.150, -106.823), # Albuquerque
        'KBMX': (33.172, -86.770),  # Birmingham
        'KHTX': (34.931, -86.084),  # Huntsville
        'KOHX': (36.247, -86.563),  # Nashville
        'KNQA': (35.345, -89.873),  # Memphis
        'KJAN': (32.318, -90.080),  # Jackson, MS
        'KLOT': (41.605, -88.085),  # Chicago
        'KILX': (40.150, -89.337),  # Lincoln, IL
        'KIND': (39.707, -86.280),  # Indianapolis
        'KILN': (39.420, -83.822),  # Wilmington, OH
        'KCLE': (41.413, -81.860),  # Cleveland
        'KDTX': (42.700, -83.472),  # Detroit
    }

    bounds = geo_filter.get_bounds()
    if not bounds:
        return []

    suggested = []
    buffer_deg = 2.5  # Radar range ~150mi, buffer for edge coverage

    for radar_id, (lat, lon) in RADAR_LOCATIONS.items():
        # Check if radar is within or near the filter bounds
        if (bounds['lat_min'] - buffer_deg <= lat <= bounds['lat_max'] + buffer_deg and
            bounds['lon_min'] - buffer_deg <= lon <= bounds['lon_max'] + buffer_deg):
            suggested.append(radar_id)

    return sorted(suggested)
