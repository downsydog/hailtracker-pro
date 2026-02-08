"""
Dual-Polarization Hail Detection Algorithm

Uses dual-pol radar signatures to detect and characterize hail:
- ZDR (Differential Reflectivity): Low/negative values indicate hail
- CC (Correlation Coefficient): Low values (<0.95) indicate hail
- KDP (Specific Differential Phase): Can indicate hail core
- Z (Reflectivity): High values (>50 dBZ) suggest hail

Target accuracy: 75% (improved from 70% basic detection)
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import numpy as np
from enum import Enum


class HailConfidence(Enum):
    """Confidence levels for hail detection"""
    NONE = 0
    LOW = 1
    MODERATE = 2
    HIGH = 3
    VERY_HIGH = 4


@dataclass
class HailSignature:
    """Dual-pol hail signature at a point"""
    lat: float
    lon: float

    # Radar values
    reflectivity_dbz: float  # Z - Reflectivity
    zdr_db: float            # ZDR - Differential Reflectivity
    cc: float                # CC - Correlation Coefficient
    kdp: Optional[float] = None  # KDP - Specific Differential Phase

    # Computed values
    hail_probability: float = 0.0
    estimated_size_inches: float = 0.0
    confidence: HailConfidence = HailConfidence.NONE

    # Component scores (0-1)
    z_score: float = 0.0
    zdr_score: float = 0.0
    cc_score: float = 0.0
    kdp_score: float = 0.0


@dataclass
class HailDetectionResult:
    """Result of hail detection analysis"""
    is_hail: bool
    probability: float
    estimated_size_inches: float
    confidence: HailConfidence
    signatures: List[HailSignature]
    max_reflectivity: float
    min_zdr: float
    min_cc: float
    detection_count: int

    # Metadata
    analysis_method: str = "dual_pol_weighted"
    accuracy_estimate: float = 0.75  # 75% target


class DualPolHailDetector:
    """
    Dual-polarization hail detection algorithm

    Uses weighted scoring of dual-pol variables:
    - Z (Reflectivity):     30% weight
    - ZDR (Diff Refl):      40% weight (most discriminating)
    - CC (Corr Coeff):      20% weight
    - KDP (Diff Phase):     10% weight

    Detection threshold: 60% confidence
    """

    # Weights for each dual-pol variable
    WEIGHT_Z = 0.30
    WEIGHT_ZDR = 0.40
    WEIGHT_CC = 0.20
    WEIGHT_KDP = 0.10

    # Detection threshold
    DETECTION_THRESHOLD = 0.60  # 60% confidence required

    # Z (Reflectivity) thresholds
    Z_HAIL_MIN = 50.0      # Minimum Z for hail consideration
    Z_SEVERE_HAIL = 60.0   # Strong hail indicator
    Z_GIANT_HAIL = 65.0    # Giant hail indicator
    Z_MAX_SCORE = 70.0     # Maximum score threshold

    # ZDR (Differential Reflectivity) thresholds
    # Hail: ZDR near 0 or negative (spherical/tumbling)
    # Rain: ZDR > 1.5 dB (oblate drops)
    ZDR_HAIL_MAX = 0.5     # Hail signature threshold
    ZDR_STRONG_HAIL = -0.5 # Strong hail (tumbling)
    ZDR_RAIN_MIN = 1.5     # Rain threshold

    # CC (Correlation Coefficient) thresholds
    # Hail: CC < 0.95 (mixed/tumbling hydrometeors)
    # Rain: CC > 0.98 (uniform drops)
    CC_HAIL_MAX = 0.95     # Hail signature threshold
    CC_STRONG_HAIL = 0.90  # Strong hail indicator
    CC_RAIN_MIN = 0.98     # Pure rain threshold

    # KDP (Specific Differential Phase) thresholds
    # Large hail: KDP near 0 or negative
    # Heavy rain: KDP > 2 deg/km
    KDP_HAIL_MAX = 0.5
    KDP_STRONG_HAIL = 0.0

    # Size estimation constants
    # Based on empirical relationships
    SIZE_BASE = 0.75       # Base size (inches)
    SIZE_Z_FACTOR = 0.04   # Size increase per dBZ above threshold
    SIZE_ZDR_FACTOR = 0.3  # Size adjustment for ZDR
    SIZE_CC_FACTOR = 0.5   # Size adjustment for low CC

    def __init__(self):
        """Initialize the dual-pol hail detector"""
        self.detection_history: List[HailDetectionResult] = []

    def analyze_signature(
        self,
        reflectivity_dbz: float,
        zdr_db: float,
        cc: float,
        kdp: Optional[float] = None,
        lat: float = 0.0,
        lon: float = 0.0
    ) -> HailSignature:
        """
        Analyze dual-pol signature for hail probability

        Args:
            reflectivity_dbz: Reflectivity in dBZ
            zdr_db: Differential reflectivity in dB
            cc: Correlation coefficient (0-1)
            kdp: Specific differential phase (deg/km), optional
            lat: Latitude of detection point
            lon: Longitude of detection point

        Returns:
            HailSignature with probability and size estimate
        """
        signature = HailSignature(
            lat=lat,
            lon=lon,
            reflectivity_dbz=reflectivity_dbz,
            zdr_db=zdr_db,
            cc=cc,
            kdp=kdp
        )

        # Calculate component scores
        signature.z_score = self._score_reflectivity(reflectivity_dbz)
        signature.zdr_score = self._score_zdr(zdr_db)
        signature.cc_score = self._score_cc(cc)
        signature.kdp_score = self._score_kdp(kdp) if kdp is not None else 0.5

        # Calculate weighted probability
        if kdp is not None:
            signature.hail_probability = (
                self.WEIGHT_Z * signature.z_score +
                self.WEIGHT_ZDR * signature.zdr_score +
                self.WEIGHT_CC * signature.cc_score +
                self.WEIGHT_KDP * signature.kdp_score
            )
        else:
            # Redistribute KDP weight when not available
            total_weight = self.WEIGHT_Z + self.WEIGHT_ZDR + self.WEIGHT_CC
            signature.hail_probability = (
                (self.WEIGHT_Z / total_weight) * signature.z_score +
                (self.WEIGHT_ZDR / total_weight) * signature.zdr_score +
                (self.WEIGHT_CC / total_weight) * signature.cc_score
            )

        # Estimate hail size
        signature.estimated_size_inches = self._estimate_size(
            reflectivity_dbz, zdr_db, cc
        )

        # Determine confidence level
        signature.confidence = self._determine_confidence(signature.hail_probability)

        return signature

    def _score_reflectivity(self, z_dbz: float) -> float:
        """
        Score reflectivity for hail probability (0-1)

        Higher Z = higher score
        """
        if z_dbz < self.Z_HAIL_MIN:
            return 0.0
        elif z_dbz >= self.Z_MAX_SCORE:
            return 1.0
        else:
            # Linear scaling between min and max
            return (z_dbz - self.Z_HAIL_MIN) / (self.Z_MAX_SCORE - self.Z_HAIL_MIN)

    def _score_zdr(self, zdr_db: float) -> float:
        """
        Score ZDR for hail probability (0-1)

        Lower/negative ZDR = higher score (hail is spherical)
        """
        if zdr_db <= self.ZDR_STRONG_HAIL:
            return 1.0
        elif zdr_db >= self.ZDR_RAIN_MIN:
            return 0.0
        elif zdr_db <= self.ZDR_HAIL_MAX:
            # High score for low ZDR
            return 0.7 + 0.3 * (self.ZDR_HAIL_MAX - zdr_db) / (self.ZDR_HAIL_MAX - self.ZDR_STRONG_HAIL)
        else:
            # Decreasing score as ZDR approaches rain values
            return 0.7 * (self.ZDR_RAIN_MIN - zdr_db) / (self.ZDR_RAIN_MIN - self.ZDR_HAIL_MAX)

    def _score_cc(self, cc: float) -> float:
        """
        Score CC for hail probability (0-1)

        Lower CC = higher score (hail causes decorrelation)
        """
        if cc >= self.CC_RAIN_MIN:
            return 0.0
        elif cc <= self.CC_STRONG_HAIL:
            return 1.0
        elif cc <= self.CC_HAIL_MAX:
            # High score for low CC
            return 0.7 + 0.3 * (self.CC_HAIL_MAX - cc) / (self.CC_HAIL_MAX - self.CC_STRONG_HAIL)
        else:
            # Decreasing score as CC approaches rain values
            return 0.7 * (self.CC_RAIN_MIN - cc) / (self.CC_RAIN_MIN - self.CC_HAIL_MAX)

    def _score_kdp(self, kdp: float) -> float:
        """
        Score KDP for hail probability (0-1)

        Lower KDP = higher score for large hail
        """
        if kdp <= self.KDP_STRONG_HAIL:
            return 1.0
        elif kdp >= 2.0:  # Heavy rain
            return 0.0
        elif kdp <= self.KDP_HAIL_MAX:
            return 0.7 + 0.3 * (self.KDP_HAIL_MAX - kdp) / self.KDP_HAIL_MAX
        else:
            return 0.7 * (2.0 - kdp) / (2.0 - self.KDP_HAIL_MAX)

    def _estimate_size(
        self,
        z_dbz: float,
        zdr_db: float,
        cc: float
    ) -> float:
        """
        Estimate hail size from dual-pol signatures

        Uses empirical relationships:
        - Higher Z = larger hail
        - Lower ZDR = larger hail (more spherical)
        - Lower CC = larger hail (more tumbling)

        Returns size in inches
        """
        if z_dbz < self.Z_HAIL_MIN:
            return 0.0

        # Base size from reflectivity
        size = self.SIZE_BASE

        # Increase size with reflectivity
        if z_dbz > self.Z_HAIL_MIN:
            size += self.SIZE_Z_FACTOR * (z_dbz - self.Z_HAIL_MIN)

        # Adjust for ZDR (lower = larger)
        if zdr_db < self.ZDR_HAIL_MAX:
            size += self.SIZE_ZDR_FACTOR * (self.ZDR_HAIL_MAX - zdr_db)

        # Adjust for CC (lower = larger)
        if cc < self.CC_HAIL_MAX:
            size += self.SIZE_CC_FACTOR * (self.CC_HAIL_MAX - cc)

        # Cap at reasonable maximum
        return min(size, 5.0)

    def _determine_confidence(self, probability: float) -> HailConfidence:
        """Determine confidence level from probability"""
        if probability < 0.30:
            return HailConfidence.NONE
        elif probability < 0.50:
            return HailConfidence.LOW
        elif probability < 0.70:
            return HailConfidence.MODERATE
        elif probability < 0.85:
            return HailConfidence.HIGH
        else:
            return HailConfidence.VERY_HIGH

    def detect_hail(
        self,
        signatures: List[HailSignature]
    ) -> HailDetectionResult:
        """
        Analyze multiple signatures for hail detection

        Args:
            signatures: List of HailSignature objects

        Returns:
            HailDetectionResult with overall detection status
        """
        if not signatures:
            return HailDetectionResult(
                is_hail=False,
                probability=0.0,
                estimated_size_inches=0.0,
                confidence=HailConfidence.NONE,
                signatures=[],
                max_reflectivity=0.0,
                min_zdr=0.0,
                min_cc=1.0,
                detection_count=0
            )

        # Find signatures above threshold
        hail_signatures = [
            s for s in signatures
            if s.hail_probability >= self.DETECTION_THRESHOLD
        ]

        # Calculate aggregate statistics
        max_probability = max(s.hail_probability for s in signatures)
        max_size = max(s.estimated_size_inches for s in signatures)
        max_reflectivity = max(s.reflectivity_dbz for s in signatures)
        min_zdr = min(s.zdr_db for s in signatures)
        min_cc = min(s.cc for s in signatures)

        # Determine overall confidence
        if hail_signatures:
            avg_probability = sum(s.hail_probability for s in hail_signatures) / len(hail_signatures)
            confidence = self._determine_confidence(avg_probability)
        else:
            avg_probability = max_probability
            confidence = HailConfidence.LOW if max_probability > 0.3 else HailConfidence.NONE

        is_hail = len(hail_signatures) > 0 or max_probability >= self.DETECTION_THRESHOLD

        result = HailDetectionResult(
            is_hail=is_hail,
            probability=max_probability,
            estimated_size_inches=max_size,
            confidence=confidence,
            signatures=signatures,
            max_reflectivity=max_reflectivity,
            min_zdr=min_zdr,
            min_cc=min_cc,
            detection_count=len(hail_signatures)
        )

        self.detection_history.append(result)
        return result

    def analyze_radar_data(
        self,
        reflectivity: np.ndarray,
        zdr: np.ndarray,
        cc: np.ndarray,
        kdp: Optional[np.ndarray] = None,
        lats: Optional[np.ndarray] = None,
        lons: Optional[np.ndarray] = None,
        mask_threshold: float = 0.0
    ) -> HailDetectionResult:
        """
        Analyze full radar volume for hail detection

        Args:
            reflectivity: 2D array of reflectivity (dBZ)
            zdr: 2D array of differential reflectivity (dB)
            cc: 2D array of correlation coefficient
            kdp: 2D array of specific differential phase (optional)
            lats: 2D array of latitudes (optional)
            lons: 2D array of longitudes (optional)
            mask_threshold: Minimum reflectivity to analyze

        Returns:
            HailDetectionResult with all detected hail signatures
        """
        signatures = []

        # Create mask for significant returns
        mask = reflectivity >= mask_threshold

        # Get indices of significant returns
        indices = np.where(mask)

        for i, j in zip(indices[0], indices[1]):
            z = reflectivity[i, j]
            zdr_val = zdr[i, j]
            cc_val = cc[i, j]
            kdp_val = kdp[i, j] if kdp is not None else None

            lat = lats[i, j] if lats is not None else 0.0
            lon = lons[i, j] if lons is not None else 0.0

            # Skip invalid values
            if np.isnan(z) or np.isnan(zdr_val) or np.isnan(cc_val):
                continue

            signature = self.analyze_signature(
                reflectivity_dbz=z,
                zdr_db=zdr_val,
                cc=cc_val,
                kdp=kdp_val,
                lat=lat,
                lon=lon
            )

            # Only keep signatures with hail potential
            if signature.hail_probability > 0.3:
                signatures.append(signature)

        return self.detect_hail(signatures)

    def get_detection_statistics(self) -> Dict:
        """Get statistics from detection history"""
        if not self.detection_history:
            return {
                'total_analyses': 0,
                'hail_detections': 0,
                'detection_rate': 0.0,
                'avg_probability': 0.0,
                'avg_size': 0.0,
                'max_size': 0.0
            }

        hail_detections = [r for r in self.detection_history if r.is_hail]

        return {
            'total_analyses': len(self.detection_history),
            'hail_detections': len(hail_detections),
            'detection_rate': len(hail_detections) / len(self.detection_history),
            'avg_probability': sum(r.probability for r in self.detection_history) / len(self.detection_history),
            'avg_size': sum(r.estimated_size_inches for r in hail_detections) / len(hail_detections) if hail_detections else 0.0,
            'max_size': max((r.estimated_size_inches for r in self.detection_history), default=0.0)
        }

    @staticmethod
    def classify_hail_size(size_inches: float) -> str:
        """Classify hail size category"""
        if size_inches < 0.75:
            return "Pea"
        elif size_inches < 1.0:
            return "Penny/Marble"
        elif size_inches < 1.25:
            return "Quarter"
        elif size_inches < 1.5:
            return "Half Dollar"
        elif size_inches < 1.75:
            return "Golf Ball"
        elif size_inches < 2.0:
            return "Hen Egg"
        elif size_inches < 2.5:
            return "Tennis Ball"
        elif size_inches < 2.75:
            return "Baseball"
        elif size_inches < 4.0:
            return "Softball"
        else:
            return "Grapefruit+"


# Convenience function for quick analysis
def analyze_dual_pol(
    reflectivity: float,
    zdr: float,
    cc: float,
    kdp: Optional[float] = None
) -> Tuple[float, float, str]:
    """
    Quick dual-pol hail analysis

    Args:
        reflectivity: Reflectivity in dBZ
        zdr: Differential reflectivity in dB
        cc: Correlation coefficient (0-1)
        kdp: Specific differential phase (optional)

    Returns:
        Tuple of (probability, size_inches, size_category)
    """
    detector = DualPolHailDetector()
    signature = detector.analyze_signature(reflectivity, zdr, cc, kdp)
    category = DualPolHailDetector.classify_hail_size(signature.estimated_size_inches)
    return (signature.hail_probability, signature.estimated_size_inches, category)


if __name__ == '__main__':
    # Quick test
    print("Dual-Pol Hail Detector Test")
    print("=" * 40)

    detector = DualPolHailDetector()

    # Test case: Strong hail signature
    sig = detector.analyze_signature(
        reflectivity_dbz=62.0,
        zdr_db=-0.3,
        cc=0.91,
        kdp=0.2
    )

    print(f"Test: Strong hail signature")
    print(f"  Z: 62 dBZ, ZDR: -0.3 dB, CC: 0.91, KDP: 0.2")
    print(f"  Probability: {sig.hail_probability:.1%}")
    print(f"  Size: {sig.estimated_size_inches:.2f}\"")
    print(f"  Category: {DualPolHailDetector.classify_hail_size(sig.estimated_size_inches)}")
    print(f"  Confidence: {sig.confidence.name}")
