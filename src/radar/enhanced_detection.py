"""
Enhanced Hail Detection System

Combines dual-pol hail detection with swath generation
for a complete hail analysis pipeline.

Target accuracy: 75% with dual-pol integration
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import json

from .dualpol_hail_detector import (
    DualPolHailDetector,
    HailSignature,
    HailDetectionResult,
    HailConfidence
)
from .swath_generator import SwathGenerator, HailDetection
from .swath_database import SwathDatabase


@dataclass
class EnhancedHailEvent:
    """Complete hail event with detection and swath data"""
    event_id: Optional[int] = None
    event_name: str = ""
    event_date: str = ""

    # Detection data
    detections: List[HailDetection] = field(default_factory=list)
    detection_result: Optional[HailDetectionResult] = None

    # Swath data
    swath_polygon: Optional[Dict] = None
    swath_method: str = ""
    swath_area_sqmi: float = 0.0

    # Hail characteristics
    max_hail_size: float = 0.0
    max_probability: float = 0.0
    confidence: HailConfidence = HailConfidence.NONE

    # Radar data
    max_reflectivity: float = 0.0
    min_zdr: float = 0.0
    min_cc: float = 1.0

    # Metadata
    analysis_method: str = "enhanced_dual_pol"
    accuracy_estimate: float = 0.75


class EnhancedHailDetection:
    """
    Enhanced hail detection system combining:
    - Dual-pol radar analysis
    - Hail probability scoring
    - Size estimation
    - Swath generation
    - Database storage

    Target accuracy: 75%
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize enhanced detection system

        Args:
            db_path: Path to SQLite database (optional)
        """
        self.detector = DualPolHailDetector()
        self.db = SwathDatabase(db_path) if db_path else SwathDatabase()
        self.events: List[EnhancedHailEvent] = []

    def analyze_dual_pol_signature(
        self,
        reflectivity: float,
        zdr: float,
        cc: float,
        kdp: Optional[float] = None,
        lat: float = 0.0,
        lon: float = 0.0
    ) -> HailSignature:
        """
        Analyze a single dual-pol signature

        Args:
            reflectivity: Reflectivity in dBZ
            zdr: Differential reflectivity in dB
            cc: Correlation coefficient
            kdp: Specific differential phase (optional)
            lat: Latitude
            lon: Longitude

        Returns:
            HailSignature with probability and size estimate
        """
        return self.detector.analyze_signature(
            reflectivity_dbz=reflectivity,
            zdr_db=zdr,
            cc=cc,
            kdp=kdp,
            lat=lat,
            lon=lon
        )

    def create_detection_from_signature(
        self,
        signature: HailSignature,
        timestamp: Optional[str] = None
    ) -> HailDetection:
        """
        Convert HailSignature to HailDetection for swath generation

        Args:
            signature: Analyzed hail signature
            timestamp: Detection timestamp (ISO format)

        Returns:
            HailDetection object
        """
        return HailDetection(
            lat=signature.lat,
            lon=signature.lon,
            hail_size=signature.estimated_size_inches,
            timestamp=timestamp or datetime.now().isoformat()
        )

    def analyze_storm(
        self,
        dual_pol_data: List[Dict],
        event_name: Optional[str] = None,
        event_date: Optional[str] = None
    ) -> EnhancedHailEvent:
        """
        Analyze a complete storm with dual-pol data

        Args:
            dual_pol_data: List of dicts with keys:
                - lat, lon: Position
                - reflectivity: dBZ
                - zdr: dB
                - cc: correlation coefficient
                - kdp: deg/km (optional)
                - timestamp: ISO format (optional)
            event_name: Name for the event
            event_date: Date string (YYYY-MM-DD)

        Returns:
            EnhancedHailEvent with complete analysis
        """
        # Analyze all dual-pol signatures
        signatures = []
        for data in dual_pol_data:
            sig = self.detector.analyze_signature(
                reflectivity_dbz=data.get('reflectivity', 0),
                zdr_db=data.get('zdr', 0),
                cc=data.get('cc', 1.0),
                kdp=data.get('kdp'),
                lat=data.get('lat', 0),
                lon=data.get('lon', 0)
            )
            signatures.append(sig)

        # Get detection result
        detection_result = self.detector.detect_hail(signatures)

        # Convert to HailDetection objects for swath generation
        detections = []
        for sig, data in zip(signatures, dual_pol_data):
            if sig.hail_probability >= self.detector.DETECTION_THRESHOLD:
                det = HailDetection(
                    lat=sig.lat,
                    lon=sig.lon,
                    hail_size=sig.estimated_size_inches,
                    timestamp=data.get('timestamp', datetime.now().isoformat())
                )
                detections.append(det)

        # Generate swath if we have detections
        swath_polygon = None
        swath_method = ""
        swath_area = 0.0

        if detections:
            if len(detections) >= 3:
                # Use composite swath for multiple detections
                swath = SwathGenerator.create_composite_swath(detections)
                swath_method = "composite"
            elif len(detections) == 2:
                # Use track-based swath for two detections
                swath = SwathGenerator.create_track_swath(detections)
                swath_method = "track"
            else:
                # Use circular swath for single detection
                det = detections[0]
                swath = SwathGenerator.create_circular_swath(
                    det.lat, det.lon, det.hail_size
                )
                swath_method = "circular"

            swath_polygon = {
                'type': swath['type'],
                'coordinates': swath['coordinates']
            }
            swath_area = SwathGenerator.calculate_swath_area(swath)

        # Create event
        event = EnhancedHailEvent(
            event_name=event_name or f"Storm_{datetime.now().strftime('%Y%m%d_%H%M')}",
            event_date=event_date or datetime.now().strftime('%Y-%m-%d'),
            detections=detections,
            detection_result=detection_result,
            swath_polygon=swath_polygon,
            swath_method=swath_method,
            swath_area_sqmi=swath_area,
            max_hail_size=detection_result.estimated_size_inches,
            max_probability=detection_result.probability,
            confidence=detection_result.confidence,
            max_reflectivity=detection_result.max_reflectivity,
            min_zdr=detection_result.min_zdr,
            min_cc=detection_result.min_cc
        )

        self.events.append(event)
        return event

    def save_event_to_database(self, event: EnhancedHailEvent) -> int:
        """
        Save an enhanced hail event to the database

        Args:
            event: EnhancedHailEvent to save

        Returns:
            Database event ID
        """
        if not event.detections:
            raise ValueError("Cannot save event with no detections")

        event_id = self.db.create_event_from_detections(
            detections=event.detections,
            event_name=event.event_name,
            event_date=event.event_date,
            swath_method=event.swath_method
        )

        event.event_id = event_id
        return event_id

    def export_event_geojson(
        self,
        event: EnhancedHailEvent,
        filename: str,
        include_detections: bool = True
    ) -> None:
        """
        Export event to GeoJSON file

        Args:
            event: EnhancedHailEvent to export
            filename: Output filename
            include_detections: Include detection points
        """
        features = []

        # Add swath polygon
        if event.swath_polygon:
            color = self._get_color_by_hail_size(event.max_hail_size)
            features.append({
                'type': 'Feature',
                'geometry': event.swath_polygon,
                'properties': {
                    'name': event.event_name,
                    'date': event.event_date,
                    'max_hail': event.max_hail_size,
                    'probability': event.max_probability,
                    'confidence': event.confidence.name,
                    'area_sqmi': event.swath_area_sqmi,
                    'method': event.swath_method,
                    'fill': color,
                    'fill-opacity': 0.4,
                    'stroke': color,
                    'stroke-width': 2
                }
            })

        # Add detection points
        if include_detections and event.detections:
            for i, det in enumerate(event.detections):
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [det.lon, det.lat]
                    },
                    'properties': {
                        'name': f'Detection {i+1}',
                        'hail_size': det.hail_size,
                        'timestamp': det.timestamp,
                        'marker-color': self._get_color_by_hail_size(det.hail_size),
                        'marker-size': 'small'
                    }
                })

            # Add track line
            if len(event.detections) >= 2:
                track_coords = [[d.lon, d.lat] for d in event.detections]
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': track_coords
                    },
                    'properties': {
                        'name': 'Storm Track',
                        'stroke': '#000000',
                        'stroke-width': 2
                    }
                })

        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }

        with open(filename, 'w') as f:
            json.dump(geojson, f, indent=2)

    def _get_color_by_hail_size(self, size: float) -> str:
        """Get color based on hail size"""
        if size >= 2.5:
            return '#8B0000'  # Dark red - extreme
        elif size >= 2.0:
            return '#FF0000'  # Red - severe
        elif size >= 1.5:
            return '#FF6347'  # Tomato - significant
        elif size >= 1.0:
            return '#FFA500'  # Orange - moderate
        else:
            return '#FFD700'  # Gold - light

    def get_accuracy_report(self) -> Dict:
        """
        Get accuracy and performance report

        Returns:
            Dict with detection statistics
        """
        stats = self.detector.get_detection_statistics()

        return {
            'method': 'Enhanced Dual-Pol Detection',
            'target_accuracy': 0.75,
            'total_events': len(self.events),
            'hail_events': sum(1 for e in self.events if e.detection_result and e.detection_result.is_hail),
            'total_detections': sum(len(e.detections) for e in self.events),
            'detector_stats': stats,
            'confidence_distribution': self._get_confidence_distribution(),
            'size_distribution': self._get_size_distribution()
        }

    def _get_confidence_distribution(self) -> Dict[str, int]:
        """Get distribution of confidence levels"""
        dist = {c.name: 0 for c in HailConfidence}
        for event in self.events:
            dist[event.confidence.name] += 1
        return dist

    def _get_size_distribution(self) -> Dict[str, int]:
        """Get distribution of hail sizes"""
        dist = {
            'Small (<1.0")': 0,
            'Moderate (1.0-1.5")': 0,
            'Significant (1.5-2.0")': 0,
            'Severe (2.0-2.5")': 0,
            'Giant (>2.5")': 0
        }

        for event in self.events:
            size = event.max_hail_size
            if size < 1.0:
                dist['Small (<1.0")'] += 1
            elif size < 1.5:
                dist['Moderate (1.0-1.5")'] += 1
            elif size < 2.0:
                dist['Significant (1.5-2.0")'] += 1
            elif size < 2.5:
                dist['Severe (2.0-2.5")'] += 1
            else:
                dist['Giant (>2.5")'] += 1

        return dist


def quick_analysis(
    reflectivity: float,
    zdr: float,
    cc: float,
    kdp: Optional[float] = None
) -> Tuple[bool, float, float, str]:
    """
    Quick hail analysis from dual-pol values

    Args:
        reflectivity: dBZ
        zdr: dB
        cc: correlation coefficient
        kdp: deg/km (optional)

    Returns:
        Tuple of (is_hail, probability, size_inches, size_category)
    """
    detector = DualPolHailDetector()
    sig = detector.analyze_signature(reflectivity, zdr, cc, kdp)
    is_hail = sig.hail_probability >= detector.DETECTION_THRESHOLD
    category = detector.classify_hail_size(sig.estimated_size_inches)
    return (is_hail, sig.hail_probability, sig.estimated_size_inches, category)


if __name__ == '__main__':
    print("Enhanced Hail Detection Module")
    print("=" * 40)

    # Quick test
    is_hail, prob, size, cat = quick_analysis(62.0, -0.3, 0.91, 0.2)
    print(f"Quick analysis: Z=62, ZDR=-0.3, CC=0.91, KDP=0.2")
    print(f"  Is Hail: {is_hail}")
    print(f"  Probability: {prob:.1%}")
    print(f"  Size: {size:.2f}\" ({cat})")
