"""
GeoJSON helper functions

Provides utilities for creating and manipulating GeoJSON objects
for swath visualization and export.
"""

import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime


class GeoJSONHelper:
    """Helper functions for creating GeoJSON"""

    @staticmethod
    def create_polygon(
        coordinates: List[List[float]],
        properties: Dict = None
    ) -> Dict:
        """
        Create a GeoJSON polygon

        Args:
            coordinates: List of [lon, lat] points (GeoJSON uses lon,lat order!)
            properties: Optional properties dict

        Returns:
            GeoJSON polygon object

        Example:
            >>> polygon = GeoJSONHelper.create_polygon(
            ...     coordinates=[
            ...         [-96.8, 32.7],
            ...         [-96.7, 32.7],
            ...         [-96.7, 32.8],
            ...         [-96.8, 32.8],
            ...         [-96.8, 32.7]  # Close the polygon
            ...     ],
            ...     properties={'name': 'Dallas Swath'}
            ... )
        """
        # Ensure polygon is closed
        if coordinates and coordinates[0] != coordinates[-1]:
            coordinates = coordinates + [coordinates[0]]

        return {
            'type': 'Polygon',
            'coordinates': [coordinates],
            'properties': properties or {}
        }

    @staticmethod
    def create_point(
        lon: float, lat: float,
        properties: Dict = None
    ) -> Dict:
        """
        Create a GeoJSON point

        Args:
            lon: Longitude
            lat: Latitude
            properties: Optional properties dict

        Returns:
            GeoJSON point object
        """
        return {
            'type': 'Point',
            'coordinates': [lon, lat],
            'properties': properties or {}
        }

    @staticmethod
    def create_line(
        coordinates: List[List[float]],
        properties: Dict = None
    ) -> Dict:
        """
        Create a GeoJSON LineString

        Args:
            coordinates: List of [lon, lat] points
            properties: Optional properties dict

        Returns:
            GeoJSON LineString object
        """
        return {
            'type': 'LineString',
            'coordinates': coordinates,
            'properties': properties or {}
        }

    @staticmethod
    def create_feature(
        geometry: Dict,
        properties: Dict = None,
        id: Optional[str] = None
    ) -> Dict:
        """
        Create a GeoJSON Feature

        Args:
            geometry: GeoJSON geometry (Point, Polygon, etc.)
            properties: Feature properties
            id: Optional feature ID

        Returns:
            GeoJSON Feature object
        """
        feature = {
            'type': 'Feature',
            'geometry': geometry,
            'properties': properties or {}
        }

        if id is not None:
            feature['id'] = id

        return feature

    @staticmethod
    def create_feature_collection(
        features: List[Dict],
        properties: Dict = None
    ) -> Dict:
        """
        Create a GeoJSON FeatureCollection

        Args:
            features: List of GeoJSON features
            properties: Optional collection-level properties

        Returns:
            GeoJSON FeatureCollection
        """
        fc = {
            'type': 'FeatureCollection',
            'features': features
        }

        if properties:
            fc['properties'] = properties

        return fc

    @staticmethod
    def points_to_polygon(
        points: List[Tuple[float, float]],
        properties: Dict = None
    ) -> Dict:
        """
        Convert list of (lat, lon) tuples to GeoJSON polygon

        Note: This converts from (lat, lon) to GeoJSON's [lon, lat] format

        Args:
            points: List of (lat, lon) tuples
            properties: Optional properties

        Returns:
            GeoJSON polygon
        """
        # Convert (lat, lon) to [lon, lat]
        coordinates = [[p[1], p[0]] for p in points]

        # Ensure closed
        if coordinates and coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])

        return GeoJSONHelper.create_polygon(coordinates, properties)

    @staticmethod
    def polygon_to_feature(
        polygon: Dict,
        additional_properties: Dict = None
    ) -> Dict:
        """
        Convert a polygon dict to a GeoJSON Feature

        Args:
            polygon: Polygon with 'coordinates' and optionally 'properties'
            additional_properties: Extra properties to merge

        Returns:
            GeoJSON Feature
        """
        geometry = {
            'type': polygon.get('type', 'Polygon'),
            'coordinates': polygon.get('coordinates', [])
        }

        properties = polygon.get('properties', {}).copy()
        if additional_properties:
            properties.update(additional_properties)

        return GeoJSONHelper.create_feature(geometry, properties)

    @staticmethod
    def save_geojson(
        geojson: Dict,
        filepath: str,
        indent: int = 2
    ):
        """
        Save GeoJSON to file

        Args:
            geojson: GeoJSON object (Feature, FeatureCollection, etc.)
            filepath: Output file path
            indent: JSON indentation (default 2)
        """
        with open(filepath, 'w') as f:
            json.dump(geojson, f, indent=indent)

    @staticmethod
    def load_geojson(filepath: str) -> Dict:
        """
        Load GeoJSON from file

        Args:
            filepath: Input file path

        Returns:
            GeoJSON object
        """
        with open(filepath, 'r') as f:
            return json.load(f)

    @staticmethod
    def create_swath_feature(
        polygon: Dict,
        hail_size: float,
        method: str,
        timestamp: str = None,
        additional_props: Dict = None
    ) -> Dict:
        """
        Create a swath feature with standard properties

        Args:
            polygon: Polygon geometry dict
            hail_size: Maximum hail size in inches
            method: Swath generation method used
            timestamp: ISO timestamp (optional)
            additional_props: Additional properties

        Returns:
            GeoJSON Feature with swath properties
        """
        properties = {
            'hail_size_inches': hail_size,
            'method': method,
            'timestamp': timestamp or datetime.now().isoformat(),
            'severity': GeoJSONHelper.get_severity(hail_size)
        }

        if additional_props:
            properties.update(additional_props)

        return GeoJSONHelper.polygon_to_feature(polygon, properties)

    @staticmethod
    def get_severity(hail_size_inches: float) -> str:
        """
        Get severity classification based on hail size

        Args:
            hail_size_inches: Hail size in inches

        Returns:
            Severity string
        """
        if hail_size_inches >= 2.5:
            return 'catastrophic'
        elif hail_size_inches >= 1.75:
            return 'severe'
        elif hail_size_inches >= 1.0:
            return 'significant'
        elif hail_size_inches >= 0.75:
            return 'moderate'
        else:
            return 'minor'

    @staticmethod
    def get_severity_color(severity: str) -> str:
        """
        Get color for severity level (for map styling)

        Args:
            severity: Severity string

        Returns:
            Hex color code
        """
        colors = {
            'catastrophic': '#8B0000',  # Dark red
            'severe': '#FF0000',         # Red
            'significant': '#FF6600',    # Orange
            'moderate': '#FFCC00',       # Yellow
            'minor': '#00CC00'           # Green
        }
        return colors.get(severity, '#808080')

    @staticmethod
    def create_styled_swath(
        polygon: Dict,
        hail_size: float,
        method: str,
        opacity: float = 0.4
    ) -> Dict:
        """
        Create a swath feature with map styling properties

        Args:
            polygon: Polygon geometry
            hail_size: Hail size in inches
            method: Generation method
            opacity: Fill opacity (0-1)

        Returns:
            GeoJSON Feature with styling properties
        """
        severity = GeoJSONHelper.get_severity(hail_size)
        color = GeoJSONHelper.get_severity_color(severity)

        properties = {
            'hail_size_inches': hail_size,
            'method': method,
            'severity': severity,
            # MapBox/Leaflet styling
            'stroke': color,
            'stroke-width': 2,
            'stroke-opacity': 0.8,
            'fill': color,
            'fill-opacity': opacity,
            # Popup content
            'description': f'{hail_size}" hail - {severity.upper()}'
        }

        return GeoJSONHelper.polygon_to_feature(polygon, properties)

    @staticmethod
    def create_detection_marker(
        lat: float, lon: float,
        hail_size: float,
        timestamp: str,
        additional_props: Dict = None
    ) -> Dict:
        """
        Create a point marker for a hail detection

        Args:
            lat: Latitude
            lon: Longitude
            hail_size: Hail size in inches
            timestamp: ISO timestamp
            additional_props: Additional properties

        Returns:
            GeoJSON Feature (Point)
        """
        severity = GeoJSONHelper.get_severity(hail_size)

        properties = {
            'hail_size_inches': hail_size,
            'timestamp': timestamp,
            'severity': severity,
            # Marker styling
            'marker-color': GeoJSONHelper.get_severity_color(severity),
            'marker-size': 'medium' if hail_size >= 1.0 else 'small',
            'marker-symbol': 'circle'
        }

        if additional_props:
            properties.update(additional_props)

        geometry = {
            'type': 'Point',
            'coordinates': [lon, lat]
        }

        return GeoJSONHelper.create_feature(geometry, properties)

    @staticmethod
    def merge_feature_collections(
        collections: List[Dict]
    ) -> Dict:
        """
        Merge multiple FeatureCollections into one

        Args:
            collections: List of FeatureCollection dicts

        Returns:
            Merged FeatureCollection
        """
        all_features = []

        for fc in collections:
            if fc.get('type') == 'FeatureCollection':
                all_features.extend(fc.get('features', []))
            elif fc.get('type') == 'Feature':
                all_features.append(fc)

        return GeoJSONHelper.create_feature_collection(all_features)

    @staticmethod
    def get_bounds(geojson: Dict) -> Tuple[float, float, float, float]:
        """
        Get bounding box of a GeoJSON object

        Args:
            geojson: Any GeoJSON object

        Returns:
            (min_lon, min_lat, max_lon, max_lat)
        """
        coords = GeoJSONHelper._extract_coordinates(geojson)

        if not coords:
            return (0, 0, 0, 0)

        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]

        return (min(lons), min(lats), max(lons), max(lats))

    @staticmethod
    def _extract_coordinates(geojson: Dict) -> List[List[float]]:
        """
        Extract all coordinates from a GeoJSON object

        Args:
            geojson: Any GeoJSON object

        Returns:
            List of [lon, lat] coordinates
        """
        coords = []
        geom_type = geojson.get('type')

        if geom_type == 'Point':
            coords.append(geojson['coordinates'])

        elif geom_type == 'LineString':
            coords.extend(geojson['coordinates'])

        elif geom_type == 'Polygon':
            for ring in geojson['coordinates']:
                coords.extend(ring)

        elif geom_type == 'MultiPolygon':
            for polygon in geojson['coordinates']:
                for ring in polygon:
                    coords.extend(ring)

        elif geom_type == 'Feature':
            coords.extend(GeoJSONHelper._extract_coordinates(geojson['geometry']))

        elif geom_type == 'FeatureCollection':
            for feature in geojson.get('features', []):
                coords.extend(GeoJSONHelper._extract_coordinates(feature))

        return coords

    @staticmethod
    def validate_geojson(geojson: Dict) -> Tuple[bool, str]:
        """
        Basic validation of GeoJSON structure

        Args:
            geojson: GeoJSON object to validate

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(geojson, dict):
            return False, "GeoJSON must be a dictionary"

        geom_type = geojson.get('type')

        if geom_type not in ['Point', 'LineString', 'Polygon', 'MultiPoint',
                             'MultiLineString', 'MultiPolygon',
                             'Feature', 'FeatureCollection', 'GeometryCollection']:
            return False, f"Invalid type: {geom_type}"

        if geom_type in ['Point', 'LineString', 'Polygon', 'MultiPoint',
                         'MultiLineString', 'MultiPolygon']:
            if 'coordinates' not in geojson:
                return False, "Geometry missing 'coordinates'"

        if geom_type == 'Feature':
            if 'geometry' not in geojson:
                return False, "Feature missing 'geometry'"

        if geom_type == 'FeatureCollection':
            if 'features' not in geojson:
                return False, "FeatureCollection missing 'features'"
            if not isinstance(geojson['features'], list):
                return False, "'features' must be a list"

        return True, "Valid"
