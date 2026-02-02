"""
Multi-Radar Fusion Engine

Combines data from multiple radar sites to:
- Cross-validate hail detections
- Improve accuracy through multiple viewing angles
- Fill coverage gaps
- Provide confidence scores based on multi-radar agreement
"""

import logging
import math
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import json

import numpy as np

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.radar.coverage import find_covering_radars, RadarCoverage, haversine_distance
except ImportError:
    from coverage import find_covering_radars, RadarCoverage, haversine_distance

logger = logging.getLogger('RadarFusion')


@dataclass
class HailCore:
    """Represents a detected hail core from a single radar."""
    radar_site: str
    timestamp: datetime
    lat: float
    lon: float
    mesh_inches: float
    reflectivity_dbz: float
    vil_kg_m2: float = 0.0
    echo_top_km: float = 0.0
    area_km2: float = 0.0
    distance_from_radar: float = 0.0
    detection_confidence: float = 1.0


@dataclass
class FusedHailDetection:
    """
    Hail detection from multi-radar fusion.

    Combines observations from multiple radars with confidence scoring.
    """
    detection_id: str
    timestamp: datetime
    lat: float
    lon: float

    # Fused estimates
    mesh_inches: float
    mesh_min: float
    mesh_max: float
    mesh_confidence: float

    reflectivity_dbz: float
    vil_kg_m2: float

    # Contributing radars
    radar_count: int
    contributing_radars: List[str]
    individual_detections: List[HailCore]

    # Quality metrics
    fusion_quality: str  # 'high', 'medium', 'low'
    agreement_score: float  # How well radars agree (0-1)
    coverage_score: float   # Quality of radar coverage (0-1)

    # Storm tracking
    storm_id: Optional[str] = None
    storm_motion_deg: Optional[float] = None
    storm_speed_mph: Optional[float] = None


class MultiRadarFusion:
    """
    Fuses hail detections from multiple radar sources.

    The fusion algorithm:
    1. Collects detections from all covering radars
    2. Clusters nearby detections (spatial matching)
    3. Combines estimates using weighted averaging
    4. Calculates confidence based on agreement
    """

    def __init__(
        self,
        spatial_tolerance_km: float = 15.0,
        temporal_tolerance_min: float = 10.0,
        min_confidence_threshold: float = 0.5
    ):
        """
        Initialize fusion engine.

        Args:
            spatial_tolerance_km: Max distance to consider detections as same storm
            temporal_tolerance_min: Max time difference to consider
            min_confidence_threshold: Minimum confidence to report detection
        """
        self.spatial_tolerance = spatial_tolerance_km
        self.temporal_tolerance = timedelta(minutes=temporal_tolerance_min)
        self.min_confidence = min_confidence_threshold

    def fuse_detections(
        self,
        detections: List[HailCore],
        location: Tuple[float, float] = None
    ) -> List[FusedHailDetection]:
        """
        Fuse hail detections from multiple radars.

        Args:
            detections: List of HailCore detections from different radars
            location: Optional (lat, lon) to focus on

        Returns:
            List of FusedHailDetection objects
        """
        if not detections:
            return []

        # Group detections by spatial proximity
        clusters = self._cluster_detections(detections)

        # Fuse each cluster
        fused = []
        for i, cluster in enumerate(clusters):
            fused_detection = self._fuse_cluster(cluster, f"FUSED_{i:04d}")
            if fused_detection and fused_detection.mesh_confidence >= self.min_confidence:
                fused.append(fused_detection)

        # Sort by MESH (descending)
        fused.sort(key=lambda x: x.mesh_inches, reverse=True)

        return fused

    def _cluster_detections(self, detections: List[HailCore]) -> List[List[HailCore]]:
        """
        Cluster detections by spatial and temporal proximity.

        Uses simple agglomerative clustering.
        """
        if not detections:
            return []

        # Sort by time
        sorted_detections = sorted(detections, key=lambda x: x.timestamp)

        clusters = []
        assigned = set()

        for i, det in enumerate(sorted_detections):
            if i in assigned:
                continue

            # Start new cluster
            cluster = [det]
            assigned.add(i)

            # Find nearby detections
            for j, other in enumerate(sorted_detections):
                if j in assigned:
                    continue

                # Check temporal proximity
                time_diff = abs((other.timestamp - det.timestamp).total_seconds())
                if time_diff > self.temporal_tolerance.total_seconds():
                    continue

                # Check spatial proximity
                dist = haversine_distance(det.lat, det.lon, other.lat, other.lon)
                if dist <= self.spatial_tolerance:
                    cluster.append(other)
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _fuse_cluster(
        self,
        cluster: List[HailCore],
        detection_id: str
    ) -> Optional[FusedHailDetection]:
        """
        Fuse a cluster of detections into a single estimate.
        """
        if not cluster:
            return None

        # Calculate weights based on radar distance and data quality
        weights = []
        for det in cluster:
            # Weight decreases with distance from radar (beam height issues)
            dist_weight = 1.0 / (1.0 + det.distance_from_radar / 100.0)
            # Weight by detection confidence
            conf_weight = det.detection_confidence
            weights.append(dist_weight * conf_weight)

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            weights = [1.0 / len(cluster)] * len(cluster)
        else:
            weights = [w / total_weight for w in weights]

        # Weighted average position
        lat = sum(det.lat * w for det, w in zip(cluster, weights))
        lon = sum(det.lon * w for det, w in zip(cluster, weights))

        # MESH statistics
        mesh_values = [det.mesh_inches for det in cluster]
        mesh_weighted = sum(det.mesh_inches * w for det, w in zip(cluster, weights))
        mesh_min = min(mesh_values)
        mesh_max = max(mesh_values)
        mesh_std = np.std(mesh_values) if len(mesh_values) > 1 else 0

        # Calculate agreement score (lower std = higher agreement)
        if mesh_max > 0:
            agreement = 1.0 - (mesh_std / mesh_max)
            agreement = max(0, min(1, agreement))
        else:
            agreement = 1.0

        # Reflectivity and VIL (weighted average)
        refl_weighted = sum(det.reflectivity_dbz * w for det, w in zip(cluster, weights))
        vil_values = [det.vil_kg_m2 for det in cluster if det.vil_kg_m2 > 0]
        vil_weighted = np.mean(vil_values) if vil_values else 0

        # Get unique radars
        contributing_radars = list(set(det.radar_site for det in cluster))
        radar_count = len(contributing_radars)

        # Calculate confidence
        # Higher with more radars, better agreement, and higher MESH
        radar_factor = min(radar_count / 3.0, 1.0)  # Max boost at 3 radars
        mesh_factor = min(mesh_weighted / 2.0, 1.0)  # Max at 2" hail
        confidence = (agreement * 0.4 + radar_factor * 0.4 + mesh_factor * 0.2)

        # Determine coverage score (based on average radar distance)
        avg_dist = np.mean([det.distance_from_radar for det in cluster])
        if avg_dist < 100:
            coverage = 'excellent'
            coverage_score = 1.0
        elif avg_dist < 150:
            coverage = 'good'
            coverage_score = 0.8
        elif avg_dist < 200:
            coverage = 'marginal'
            coverage_score = 0.6
        else:
            coverage = 'poor'
            coverage_score = 0.4

        # Fusion quality based on radar count and agreement
        if radar_count >= 3 and agreement >= 0.8:
            fusion_quality = 'high'
        elif radar_count >= 2 and agreement >= 0.6:
            fusion_quality = 'medium'
        else:
            fusion_quality = 'low'

        # Use average timestamp
        avg_timestamp = cluster[0].timestamp  # Simplified - could do proper averaging

        return FusedHailDetection(
            detection_id=detection_id,
            timestamp=avg_timestamp,
            lat=lat,
            lon=lon,
            mesh_inches=round(mesh_weighted, 2),
            mesh_min=round(mesh_min, 2),
            mesh_max=round(mesh_max, 2),
            mesh_confidence=round(confidence, 3),
            reflectivity_dbz=round(refl_weighted, 1),
            vil_kg_m2=round(vil_weighted, 1),
            radar_count=radar_count,
            contributing_radars=contributing_radars,
            individual_detections=cluster,
            fusion_quality=fusion_quality,
            agreement_score=round(agreement, 3),
            coverage_score=round(coverage_score, 3)
        )

    def cross_validate(
        self,
        primary_detection: HailCore,
        secondary_detections: List[HailCore]
    ) -> Dict:
        """
        Cross-validate a primary detection against secondary radar observations.

        Args:
            primary_detection: Main detection to validate
            secondary_detections: Supporting detections from other radars

        Returns:
            Validation result with confidence metrics
        """
        if not secondary_detections:
            return {
                'validated': False,
                'reason': 'no_secondary_data',
                'confidence': 0.5,
                'primary_mesh': primary_detection.mesh_inches
            }

        # Find matching secondary detections
        matches = []
        for sec in secondary_detections:
            dist = haversine_distance(
                primary_detection.lat, primary_detection.lon,
                sec.lat, sec.lon
            )
            time_diff = abs((sec.timestamp - primary_detection.timestamp).total_seconds())

            if dist <= self.spatial_tolerance and time_diff <= self.temporal_tolerance.total_seconds():
                matches.append({
                    'detection': sec,
                    'distance_km': dist,
                    'time_diff_sec': time_diff
                })

        if not matches:
            return {
                'validated': False,
                'reason': 'no_matching_detections',
                'confidence': 0.5,
                'primary_mesh': primary_detection.mesh_inches
            }

        # Calculate agreement
        mesh_values = [primary_detection.mesh_inches] + [m['detection'].mesh_inches for m in matches]
        mesh_std = np.std(mesh_values)
        mesh_mean = np.mean(mesh_values)

        if mesh_mean > 0:
            agreement = 1.0 - (mesh_std / mesh_mean)
            agreement = max(0, min(1, agreement))
        else:
            agreement = 0

        # Validation criteria
        validated = len(matches) >= 1 and agreement >= 0.5

        return {
            'validated': validated,
            'reason': 'multi_radar_agreement' if validated else 'low_agreement',
            'confidence': round(agreement, 3),
            'primary_mesh': primary_detection.mesh_inches,
            'match_count': len(matches),
            'mesh_range': [min(mesh_values), max(mesh_values)],
            'mesh_mean': round(mesh_mean, 2)
        }


class FusionProcessor:
    """
    High-level processor for multi-radar fusion workflow.
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize fusion processor.

        Args:
            data_dir: Directory for intermediate data
        """
        self.data_dir = Path(data_dir) if data_dir else Path('data/fusion')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.fusion_engine = MultiRadarFusion()

    def process_event(
        self,
        lat: float,
        lon: float,
        timestamp: datetime,
        mesh_data: Dict[str, np.ndarray],
        radar_metadata: Dict[str, Dict]
    ) -> List[FusedHailDetection]:
        """
        Process a potential hail event with multi-radar fusion.

        Args:
            lat: Event latitude
            lon: Event longitude
            timestamp: Event time
            mesh_data: Dict of radar_site -> MESH array
            radar_metadata: Dict of radar_site -> metadata (lat, lon, etc.)

        Returns:
            List of fused hail detections
        """
        # Extract hail cores from each radar's MESH data
        all_detections = []

        for site, mesh in mesh_data.items():
            if mesh is None or site not in radar_metadata:
                continue

            meta = radar_metadata[site]
            cores = self._extract_hail_cores(
                mesh,
                site,
                timestamp,
                meta.get('lat', 0),
                meta.get('lon', 0),
                meta.get('range_km', 230)
            )
            all_detections.extend(cores)

        # Fuse detections
        fused = self.fusion_engine.fuse_detections(all_detections, (lat, lon))

        return fused

    def _extract_hail_cores(
        self,
        mesh: np.ndarray,
        radar_site: str,
        timestamp: datetime,
        radar_lat: float,
        radar_lon: float,
        range_km: float
    ) -> List[HailCore]:
        """
        Extract hail cores from a MESH array.
        """
        from scipy import ndimage

        cores = []

        # Threshold for significant hail (0.75 inches)
        threshold = 0.75
        hail_mask = mesh > threshold

        if not np.any(hail_mask):
            return cores

        # Label connected regions
        labeled, num_features = ndimage.label(hail_mask)

        for i in range(1, num_features + 1):
            core_mask = labeled == i
            core_mesh = mesh[core_mask]

            if len(core_mesh) == 0:
                continue

            max_mesh = float(np.max(core_mesh))
            mean_mesh = float(np.mean(core_mesh))

            # Get centroid position
            positions = np.where(core_mask)
            if len(positions[0]) == 0:
                continue

            center_y = int(np.mean(positions[0]))
            center_x = int(np.mean(positions[1]))

            # Convert to lat/lon
            grid_size = mesh.shape[0]
            dy = (center_y - grid_size // 2) * (range_km * 2 / grid_size)
            dx = (center_x - grid_size // 2) * (range_km * 2 / grid_size)

            core_lat = radar_lat + dy / 111.0
            core_lon = radar_lon + dx / (111.0 * math.cos(math.radians(radar_lat)))

            # Distance from radar
            distance = haversine_distance(radar_lat, radar_lon, core_lat, core_lon)

            # Calculate area
            pixel_size_km = (range_km * 2) / grid_size
            area = np.sum(core_mask) * (pixel_size_km ** 2)

            # Detection confidence (decreases with distance)
            confidence = 1.0 / (1.0 + distance / 150.0)

            cores.append(HailCore(
                radar_site=radar_site,
                timestamp=timestamp,
                lat=core_lat,
                lon=core_lon,
                mesh_inches=max_mesh,
                reflectivity_dbz=0,  # Would need reflectivity data
                distance_from_radar=distance,
                area_km2=area,
                detection_confidence=confidence
            ))

        return cores

    def save_fusion_result(self, detection: FusedHailDetection) -> str:
        """
        Save fusion result to file.

        Args:
            detection: FusedHailDetection to save

        Returns:
            Path to saved file
        """
        date_str = detection.timestamp.strftime('%Y%m%d')
        output_dir = self.data_dir / date_str
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{detection.detection_id}_{detection.timestamp.strftime('%H%M%S')}.json"
        output_path = output_dir / filename

        # Convert to serializable dict
        data = {
            'detection_id': detection.detection_id,
            'timestamp': detection.timestamp.isoformat(),
            'lat': detection.lat,
            'lon': detection.lon,
            'mesh_inches': detection.mesh_inches,
            'mesh_min': detection.mesh_min,
            'mesh_max': detection.mesh_max,
            'mesh_confidence': detection.mesh_confidence,
            'reflectivity_dbz': detection.reflectivity_dbz,
            'vil_kg_m2': detection.vil_kg_m2,
            'radar_count': detection.radar_count,
            'contributing_radars': detection.contributing_radars,
            'fusion_quality': detection.fusion_quality,
            'agreement_score': detection.agreement_score,
            'coverage_score': detection.coverage_score,
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        return str(output_path)


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("MULTI-RADAR FUSION ENGINE TEST")
    print("=" * 60)

    # Create test detections from multiple radars
    timestamp = datetime.utcnow()

    test_detections = [
        HailCore(
            radar_site='KTLX',
            timestamp=timestamp,
            lat=35.50,
            lon=-97.50,
            mesh_inches=1.75,
            reflectivity_dbz=65,
            distance_from_radar=50,
            detection_confidence=0.95
        ),
        HailCore(
            radar_site='KVNX',
            timestamp=timestamp + timedelta(minutes=2),
            lat=35.52,
            lon=-97.48,
            mesh_inches=1.50,
            reflectivity_dbz=63,
            distance_from_radar=120,
            detection_confidence=0.8
        ),
        HailCore(
            radar_site='KINX',
            timestamp=timestamp + timedelta(minutes=3),
            lat=35.48,
            lon=-97.51,
            mesh_inches=1.85,
            reflectivity_dbz=66,
            distance_from_radar=90,
            detection_confidence=0.85
        ),
    ]

    # Test fusion
    print("\nTest detections:")
    for det in test_detections:
        print(f"  {det.radar_site}: {det.mesh_inches}\" at ({det.lat:.2f}, {det.lon:.2f})")

    fusion = MultiRadarFusion()
    fused = fusion.fuse_detections(test_detections)

    print(f"\nFused results: {len(fused)} detection(s)")
    for f in fused:
        print(f"\n  Detection: {f.detection_id}")
        print(f"  Location: ({f.lat:.3f}, {f.lon:.3f})")
        print(f"  MESH: {f.mesh_inches}\" (range: {f.mesh_min}\" - {f.mesh_max}\")")
        print(f"  Confidence: {f.mesh_confidence:.2f}")
        print(f"  Quality: {f.fusion_quality}")
        print(f"  Radars: {f.contributing_radars}")
        print(f"  Agreement: {f.agreement_score:.2f}")

    # Test cross-validation
    print("\n" + "=" * 60)
    print("CROSS-VALIDATION TEST")
    print("=" * 60)

    primary = test_detections[0]
    secondary = test_detections[1:]

    validation = fusion.cross_validate(primary, secondary)
    print(f"\nPrimary detection ({primary.radar_site}): {primary.mesh_inches}\"")
    print(f"Validation result:")
    print(f"  Validated: {validation['validated']}")
    print(f"  Confidence: {validation['confidence']}")
    print(f"  Match count: {validation['match_count']}")
    print(f"  MESH range: {validation['mesh_range']}")

    print("\nMulti-radar fusion engine ready!")
