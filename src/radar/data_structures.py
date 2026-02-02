"""
Data structures for hail detection and swath generation

This module provides the core data structures used throughout the radar module.
It re-exports from swath_generator for backwards compatibility while providing
a clean import path.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime


@dataclass
class HailDetection:
    """
    Single hail detection point from radar

    Attributes:
        lat: Latitude (decimal degrees)
        lon: Longitude (decimal degrees)
        hail_size: Hail size in inches
        timestamp: ISO format timestamp (e.g. "2024-11-15T14:30:00")
        reflectivity: Radar reflectivity in dBZ (optional)
        storm_motion_dir: Storm direction in degrees, 0=North (optional)
        storm_motion_speed: Storm speed in mph (optional)

        # Dual-polarization variables
        zdr: Differential reflectivity (dB) - low = spherical hail (optional)
        cc: Correlation coefficient - low = tumbling hail (optional)
        kdp: Specific differential phase (deg/km) (optional)
        hail_probability: 0-1 probability from dual-pol analysis (optional)

    Example:
        >>> detection = HailDetection(
        ...     lat=32.7767,
        ...     lon=-96.7970,
        ...     hail_size=1.75,
        ...     timestamp='2024-11-15T14:30:00'
        ... )
    """
    lat: float
    lon: float
    hail_size: float  # inches
    timestamp: str

    # Optional radar data
    reflectivity: Optional[float] = None  # dBZ
    storm_motion_dir: Optional[float] = None  # degrees (0=North)
    storm_motion_speed: Optional[float] = None  # mph

    # Dual-polarization variables (for improved accuracy)
    zdr: Optional[float] = None  # Differential reflectivity (dB)
    cc: Optional[float] = None   # Correlation coefficient
    kdp: Optional[float] = None  # Specific differential phase (deg/km)
    hail_probability: Optional[float] = None  # 0-1 probability

    def __repr__(self):
        return f"HailDetection({self.lat:.4f}, {self.lon:.4f}, {self.hail_size}\" at {self.timestamp})"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'lat': self.lat,
            'lon': self.lon,
            'hail_size': self.hail_size,
            'timestamp': self.timestamp,
            'reflectivity': self.reflectivity,
            'storm_motion_dir': self.storm_motion_dir,
            'storm_motion_speed': self.storm_motion_speed,
            'zdr': self.zdr,
            'cc': self.cc,
            'kdp': self.kdp,
            'hail_probability': self.hail_probability
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'HailDetection':
        """Create from dictionary."""
        return cls(
            lat=data['lat'],
            lon=data['lon'],
            hail_size=data['hail_size'],
            timestamp=data['timestamp'],
            reflectivity=data.get('reflectivity'),
            storm_motion_dir=data.get('storm_motion_dir'),
            storm_motion_speed=data.get('storm_motion_speed'),
            zdr=data.get('zdr'),
            cc=data.get('cc'),
            kdp=data.get('kdp'),
            hail_probability=data.get('hail_probability')
        )


@dataclass
class StormTrack:
    """
    Storm tracking information with start and end points

    Attributes:
        start_lat: Starting latitude
        start_lon: Starting longitude
        end_lat: Ending latitude
        end_lon: Ending longitude
        start_time: ISO format start timestamp
        end_time: ISO format end timestamp
        motion_dir: Direction in degrees (calculated from start/end)
        motion_speed: Speed in mph (calculated from distance/time)
        max_hail: Maximum hail size in inches

    Example:
        >>> track = StormTrack(
        ...     start_lat=32.7, start_lon=-97.0,
        ...     end_lat=32.9, end_lon=-96.8,
        ...     start_time='2024-11-15T14:00:00',
        ...     end_time='2024-11-15T14:30:00',
        ...     motion_dir=45, motion_speed=40,
        ...     max_hail=1.75
        ... )
    """
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_time: str  # ISO format timestamp
    end_time: str
    motion_dir: float  # degrees (calculated from start/end)
    motion_speed: float  # mph (calculated from distance/time)
    max_hail: float  # inches

    def __repr__(self):
        return f"StormTrack({self.start_lat:.4f},{self.start_lon:.4f} -> {self.end_lat:.4f},{self.end_lon:.4f})"

    @property
    def duration_minutes(self) -> float:
        """Calculate duration in minutes."""
        start_dt = datetime.fromisoformat(self.start_time)
        end_dt = datetime.fromisoformat(self.end_time)
        return (end_dt - start_dt).total_seconds() / 60

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'start_lat': self.start_lat,
            'start_lon': self.start_lon,
            'end_lat': self.end_lat,
            'end_lon': self.end_lon,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'motion_dir': self.motion_dir,
            'motion_speed': self.motion_speed,
            'max_hail': self.max_hail
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StormTrack':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class RadarScan:
    """
    Single radar volume scan metadata

    Attributes:
        radar_id: Radar site identifier (e.g., 'KFWS')
        scan_time: ISO format timestamp
        elevation_angle: Elevation angle in degrees
        max_range_km: Maximum range in kilometers
        detections: List of HailDetection objects from this scan
    """
    radar_id: str
    scan_time: str
    elevation_angle: float = 0.5
    max_range_km: float = 230.0
    detections: List[HailDetection] = None

    def __post_init__(self):
        if self.detections is None:
            self.detections = []

    def add_detection(self, detection: HailDetection):
        """Add a detection to this scan."""
        self.detections.append(detection)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'radar_id': self.radar_id,
            'scan_time': self.scan_time,
            'elevation_angle': self.elevation_angle,
            'max_range_km': self.max_range_km,
            'detections': [d.to_dict() for d in self.detections]
        }


@dataclass
class SwathResult:
    """
    Result from swath generation

    Attributes:
        polygon: GeoJSON polygon dictionary
        method: Method used ('circular', 'elliptical', 'track', 'composite', etc.)
        area_sq_miles: Approximate area in square miles
        center: (lat, lon) tuple of swath center
        max_hail_size: Maximum hail size in the swath
        properties: Additional properties dictionary
    """
    polygon: dict
    method: str
    area_sq_miles: float
    center: Tuple[float, float]
    max_hail_size: float
    properties: dict = None

    def __post_init__(self):
        if self.properties is None:
            self.properties = {}

    def to_geojson_feature(self) -> dict:
        """Convert to GeoJSON Feature format."""
        return {
            'type': 'Feature',
            'geometry': {
                'type': self.polygon.get('type', 'Polygon'),
                'coordinates': self.polygon.get('coordinates', [])
            },
            'properties': {
                'method': self.method,
                'area_sq_miles': self.area_sq_miles,
                'center_lat': self.center[0],
                'center_lon': self.center[1],
                'max_hail_size': self.max_hail_size,
                **self.properties
            }
        }


# Size reference constants
HAIL_SIZE_REFERENCE = {
    'pea': 0.25,
    'marble': 0.50,
    'dime': 0.70,
    'penny': 0.75,
    'nickel': 0.88,
    'quarter': 1.00,
    'half_dollar': 1.25,
    'walnut': 1.50,
    'ping_pong': 1.50,
    'golf_ball': 1.75,
    'hen_egg': 2.00,
    'tennis_ball': 2.50,
    'baseball': 2.75,
    'tea_cup': 3.00,
    'apple': 3.00,
    'softball': 4.00,
    'grapefruit': 4.50,
    'cd': 4.75
}


def size_to_name(inches: float) -> str:
    """Convert hail size in inches to descriptive name."""
    closest = min(HAIL_SIZE_REFERENCE.items(),
                  key=lambda x: abs(x[1] - inches))
    return closest[0].replace('_', ' ')


def name_to_size(name: str) -> float:
    """Convert descriptive name to size in inches."""
    key = name.lower().replace(' ', '_')
    return HAIL_SIZE_REFERENCE.get(key, 1.0)
