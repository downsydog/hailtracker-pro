"""
Tile-Based Swath Discovery System
=================================
Breaks hail swaths into small geographic tiles for efficient, complete searching.

Why tiles are better than center + radius:
- Swaths are irregular shapes, not circles
- Center + radius misses corners/edges
- Large radius = hits API limits (Google: 60 results max)
- Tiles ensure complete coverage of actual swath shape

Tile sizes:
- 0.25 miles = very precise, more API calls
- 0.5 miles = good balance (RECOMMENDED)
- 1.0 miles = fewer calls, might hit limits
"""

import math
import json
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Tile:
    """Represents a geographic tile."""
    tile_id: str
    center_lat: float
    center_lon: float
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float
    search_radius_miles: float

    def to_dict(self) -> dict:
        return {
            'tile_id': self.tile_id,
            'center_lat': self.center_lat,
            'center_lon': self.center_lon,
            'bounds': {
                'min_lat': self.min_lat,
                'min_lon': self.min_lon,
                'max_lat': self.max_lat,
                'max_lon': self.max_lon,
            },
            'search_radius_miles': self.search_radius_miles,
        }


class SwathTileSystem:
    """
    Break hail swaths into small geographic tiles for efficient searching.

    Usage:
        ts = SwathTileSystem(tile_size_miles=0.5)
        tiles = ts.generate_tiles_for_swath(swath_geojson)

        for tile in tiles:
            results = search_api(tile['center_lat'], tile['center_lon'], tile['search_radius_miles'])
    """

    # Approximate miles per degree at US latitudes (~35°N)
    MILES_PER_DEG_LAT = 69.0
    MILES_PER_DEG_LON = 54.6  # Varies by latitude

    def __init__(self, tile_size_miles: float = 0.5):
        """
        Initialize tile system.

        Args:
            tile_size_miles: Size of each tile in miles (0.25, 0.5, or 1.0 recommended)
        """
        self.tile_size_miles = tile_size_miles
        self.tile_size_lat = tile_size_miles / self.MILES_PER_DEG_LAT
        self.tile_size_lon = tile_size_miles / self.MILES_PER_DEG_LON

    def generate_tiles_for_swath(self, swath_geojson: dict) -> List[Tile]:
        """
        Generate tiles that cover a swath polygon.

        Args:
            swath_geojson: GeoJSON polygon of the hail swath

        Returns:
            List of Tile objects that intersect the swath
        """
        # Parse swath polygon
        coords = self._extract_coordinates(swath_geojson)

        if not coords or len(coords) < 3:
            return []

        # Get bounding box of swath
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)

        # Generate grid of tiles covering the bounding box
        tiles = []

        lat = min_lat
        while lat < max_lat + self.tile_size_lat:
            lon = min_lon
            while lon < max_lon + self.tile_size_lon:
                # Create tile bounds
                tile_min_lat = lat
                tile_min_lon = lon
                tile_max_lat = lat + self.tile_size_lat
                tile_max_lon = lon + self.tile_size_lon

                # Check if tile intersects the swath polygon
                if self._tile_intersects_polygon(
                    tile_min_lat, tile_min_lon,
                    tile_max_lat, tile_max_lon,
                    coords
                ):
                    center_lat = (tile_min_lat + tile_max_lat) / 2
                    center_lon = (tile_min_lon + tile_max_lon) / 2

                    # Use geographically unique tile ID based on center coordinates
                    # This ensures consistent caching across different swath queries
                    geo_tile_id = f"tile_{center_lat:.4f}_{center_lon:.4f}"

                    tiles.append(Tile(
                        tile_id=geo_tile_id,
                        center_lat=center_lat,
                        center_lon=center_lon,
                        min_lat=tile_min_lat,
                        min_lon=tile_min_lon,
                        max_lat=tile_max_lat,
                        max_lon=tile_max_lon,
                        search_radius_miles=self.tile_size_miles * 0.75,  # Overlap slightly
                    ))

                lon += self.tile_size_lon
            lat += self.tile_size_lat

        return tiles

    def generate_tiles_for_multiple_swaths(self, swaths: List[dict]) -> List[Tile]:
        """
        Generate tiles for multiple swaths, deduplicating overlapping tiles.

        Args:
            swaths: List of GeoJSON swath polygons

        Returns:
            Deduplicated list of tiles covering all swaths
        """
        all_tiles = []
        seen_centers = set()

        for swath in swaths:
            tiles = self.generate_tiles_for_swath(swath)

            for tile in tiles:
                # Dedupe by center point (rounded to avoid float issues)
                center_key = (
                    round(tile.center_lat, 4),
                    round(tile.center_lon, 4)
                )

                if center_key not in seen_centers:
                    seen_centers.add(center_key)
                    all_tiles.append(tile)

        return all_tiles

    def _extract_coordinates(self, geojson: dict) -> Optional[List[List[float]]]:
        """Extract coordinates from various GeoJSON formats."""
        try:
            if isinstance(geojson, str):
                geojson = json.loads(geojson)

            if geojson.get('type') == 'Polygon':
                return geojson['coordinates'][0]
            elif geojson.get('type') == 'Feature':
                return geojson['geometry']['coordinates'][0]
            elif geojson.get('type') == 'MultiPolygon':
                return geojson['coordinates'][0][0]

        except Exception as e:
            print(f"Error parsing GeoJSON: {e}")

        return None

    def _tile_intersects_polygon(
        self,
        tile_min_lat: float,
        tile_min_lon: float,
        tile_max_lat: float,
        tile_max_lon: float,
        polygon_coords: List[List[float]]
    ) -> bool:
        """
        Check if a tile intersects a polygon using a simple approach.

        Checks:
        1. Tile center is inside polygon
        2. Any polygon vertex is inside tile
        3. Tile corners are inside polygon
        """
        # Check 1: Tile center inside polygon
        center_lat = (tile_min_lat + tile_max_lat) / 2
        center_lon = (tile_min_lon + tile_max_lon) / 2
        if self._point_in_polygon(center_lat, center_lon, polygon_coords):
            return True

        # Check 2: Any polygon vertex inside tile
        for coord in polygon_coords:
            lon, lat = coord[0], coord[1]
            if (tile_min_lat <= lat <= tile_max_lat and
                tile_min_lon <= lon <= tile_max_lon):
                return True

        # Check 3: Tile corners inside polygon
        corners = [
            (tile_min_lat, tile_min_lon),
            (tile_min_lat, tile_max_lon),
            (tile_max_lat, tile_min_lon),
            (tile_max_lat, tile_max_lon),
        ]
        for lat, lon in corners:
            if self._point_in_polygon(lat, lon, polygon_coords):
                return True

        # Check 4: Polygon edges cross tile (for thin swaths)
        # This catches cases where the swath passes through the tile
        # but no vertices are inside
        for i in range(len(polygon_coords) - 1):
            lon1, lat1 = polygon_coords[i]
            lon2, lat2 = polygon_coords[i + 1]
            if self._line_intersects_box(
                lat1, lon1, lat2, lon2,
                tile_min_lat, tile_min_lon, tile_max_lat, tile_max_lon
            ):
                return True

        return False

    def _point_in_polygon(self, lat: float, lon: float, coords: List[List[float]]) -> bool:
        """Ray casting algorithm for point-in-polygon test."""
        n = len(coords)
        inside = False

        p1_lon, p1_lat = coords[0]
        for i in range(1, n + 1):
            p2_lon, p2_lat = coords[i % n]
            if lat > min(p1_lat, p2_lat):
                if lat <= max(p1_lat, p2_lat):
                    if lon <= max(p1_lon, p2_lon):
                        if p1_lat != p2_lat:
                            xinters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                        if p1_lon == p2_lon or lon <= xinters:
                            inside = not inside
            p1_lon, p1_lat = p2_lon, p2_lat

        return inside

    def _line_intersects_box(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        box_min_lat: float, box_min_lon: float,
        box_max_lat: float, box_max_lon: float
    ) -> bool:
        """Check if a line segment intersects a bounding box."""
        # Check if line's bounding box intersects tile box
        line_min_lat = min(lat1, lat2)
        line_max_lat = max(lat1, lat2)
        line_min_lon = min(lon1, lon2)
        line_max_lon = max(lon1, lon2)

        # No intersection if bounding boxes don't overlap
        if (line_max_lat < box_min_lat or line_min_lat > box_max_lat or
            line_max_lon < box_min_lon or line_min_lon > box_max_lon):
            return False

        return True

    def get_tile_stats(self, tiles: List[Tile]) -> Dict:
        """Get statistics about generated tiles."""
        if not tiles:
            return {
                'count': 0,
                'tile_size_miles': self.tile_size_miles,
            }

        lats = [t.center_lat for t in tiles]
        lons = [t.center_lon for t in tiles]

        return {
            'count': len(tiles),
            'tile_size_miles': self.tile_size_miles,
            'bounds': {
                'min_lat': min(lats),
                'max_lat': max(lats),
                'min_lon': min(lons),
                'max_lon': max(lons),
            },
            'estimated_area_sq_miles': len(tiles) * (self.tile_size_miles ** 2),
            'search_radius_per_tile': self.tile_size_miles * 0.75,
        }

    def tiles_to_geojson(self, tiles: List[Tile]) -> dict:
        """Convert tiles to GeoJSON FeatureCollection for visualization."""
        features = []

        for tile in tiles:
            feature = {
                'type': 'Feature',
                'properties': {
                    'tile_id': tile.tile_id,
                    'center_lat': tile.center_lat,
                    'center_lon': tile.center_lon,
                },
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': [[
                        [tile.min_lon, tile.min_lat],
                        [tile.max_lon, tile.min_lat],
                        [tile.max_lon, tile.max_lat],
                        [tile.min_lon, tile.max_lat],
                        [tile.min_lon, tile.min_lat],
                    ]]
                }
            }
            features.append(feature)

        return {
            'type': 'FeatureCollection',
            'features': features,
        }


# Convenience function
def generate_tiles_for_polygon(
    polygon_geojson: dict,
    tile_size_miles: float = 0.5
) -> List[Dict]:
    """
    Generate tiles for a polygon.

    Args:
        polygon_geojson: GeoJSON polygon
        tile_size_miles: Size of each tile

    Returns:
        List of tile dictionaries
    """
    ts = SwathTileSystem(tile_size_miles)
    tiles = ts.generate_tiles_for_swath(polygon_geojson)
    return [t.to_dict() for t in tiles]
