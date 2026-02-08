"""
Hail Classifier - Simplified Interface for ML-based Hail Detection

This module provides a clean, simple interface for the machine learning
hail detection system. It wraps the more complex HailMLModel and provides
easy-to-use methods for common use cases.

SWATH UPGRADE 5 - PART 12: Machine Learning Model
Final accuracy target: 85%
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from .hail_ml_model import (
    HailMLModel,
    HailFeatures,
    HailPrediction,
    TrainingExample,
    generate_synthetic_training_data,
    FEATURE_NAMES
)


@dataclass
class HailEvent:
    """
    Complete hail event with ML classification.

    Combines radar observations, environmental data, cell tracking,
    and ML predictions into a single comprehensive result.
    """

    # Event identification
    timestamp: datetime
    location: Tuple[float, float]  # lat, lon

    # Radar observations
    max_reflectivity: float = 0.0
    mesh_mm: float = 0.0
    posh: float = 0.0

    # Dual-pol signatures
    zdr_min: float = 0.0
    cc_min: float = 1.0

    # ML prediction
    hail_probability: float = 0.0
    hail_detected: bool = False
    estimated_size_mm: float = 0.0
    severity: str = 'none'
    confidence: float = 0.0

    # Cell tracking info
    cell_id: Optional[int] = None
    cell_velocity_kmh: float = 0.0
    cell_direction_deg: float = 0.0
    cell_age_minutes: float = 0.0

    # Multi-radar info
    num_radars: int = 0
    radar_agreement: float = 0.0

    # PDR relevance
    pdr_opportunity_score: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'location': {
                'lat': self.location[0],
                'lon': self.location[1]
            },
            'radar': {
                'max_reflectivity': self.max_reflectivity,
                'mesh_mm': self.mesh_mm,
                'posh': self.posh,
                'zdr_min': self.zdr_min,
                'cc_min': self.cc_min
            },
            'prediction': {
                'hail_probability': round(self.hail_probability, 1),
                'hail_detected': self.hail_detected,
                'estimated_size_mm': round(self.estimated_size_mm, 1),
                'estimated_size_inches': round(self.estimated_size_mm / 25.4, 2),
                'severity': self.severity,
                'confidence': round(self.confidence, 1)
            },
            'cell_tracking': {
                'cell_id': self.cell_id,
                'velocity_kmh': self.cell_velocity_kmh,
                'direction_deg': self.cell_direction_deg,
                'age_minutes': self.cell_age_minutes
            },
            'multi_radar': {
                'num_radars': self.num_radars,
                'agreement': round(self.radar_agreement, 1)
            },
            'pdr_score': round(self.pdr_opportunity_score, 1)
        }


class HailClassifier:
    """
    High-level hail classifier using ML model.

    This provides a simplified interface for the complete hail detection
    pipeline, integrating:
    - Multi-radar composite analysis
    - Cell tracking
    - Machine learning prediction
    - PDR opportunity scoring

    Example usage:
        >>> classifier = HailClassifier()
        >>>
        >>> # Classify from radar data
        >>> event = classifier.classify(
        ...     lat=32.7767,
        ...     lon=-96.7970,
        ...     timestamp=datetime.now(),
        ...     radar_data={
        ...         'max_reflectivity': 65,
        ...         'mesh': 40,
        ...         'posh': 80,
        ...         'zdr_min': 0.2,
        ...         'cc_min': 0.92
        ...     }
        ... )
        >>>
        >>> print(f"Hail probability: {event.hail_probability}%")
        >>> print(f"Size: {event.estimated_size_mm} mm")
    """

    # Severity classification thresholds (mm)
    SEVERITY_THRESHOLDS = {
        'catastrophic': 63.5,  # 2.5" - baseball+
        'severe': 44.5,        # 1.75" - golf ball
        'moderate': 25.4,      # 1.0" - quarter
        'light': 12.7,         # 0.5" - marble
        'none': 0
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        simulation_mode: bool = False,
        auto_train: bool = True
    ):
        """
        Initialize the classifier.

        Args:
            model_path: Path to saved model file
            simulation_mode: Use physics-based simulation instead of ML
            auto_train: Automatically train on synthetic data if no model
        """
        self.model = HailMLModel(
            model_path=model_path,
            simulation_mode=simulation_mode
        )

        self.simulation_mode = simulation_mode

        # Try to load existing model or train
        if not simulation_mode:
            if not self.model.load():
                if auto_train:
                    print("No saved model found, training on synthetic data...")
                    self._train_synthetic()
                else:
                    print("No model found, using simulation mode")
                    self.simulation_mode = True

    def _train_synthetic(self, n_samples: int = 2000):
        """Train on synthetic data for development/testing."""
        training_data = generate_synthetic_training_data(n_samples)
        results = self.model.train(training_data)

        if results.get('success'):
            self.model.save()
            print(f"Model trained. Accuracy: {results['accuracy']*100:.1f}%")

    def classify(
        self,
        lat: float,
        lon: float,
        timestamp: datetime,
        radar_data: Dict[str, Any],
        environmental_data: Optional[Dict[str, Any]] = None,
        cell_data: Optional[Dict[str, Any]] = None,
        multi_radar_data: Optional[Dict[str, Any]] = None
    ) -> HailEvent:
        """
        Classify a potential hail event.

        Args:
            lat: Event latitude
            lon: Event longitude
            timestamp: Event time
            radar_data: Radar observations including:
                - max_reflectivity (dBZ)
                - mesh (mm)
                - posh (%)
                - zdr_min (dB)
                - cc_min
                - vil (kg/m^2)
            environmental_data: Environmental conditions including:
                - freezing_level (km)
                - cape (J/kg)
                - shear_0_6km (m/s)
            cell_data: Cell tracking data including:
                - cell_id
                - velocity_kmh
                - direction_deg
                - age_minutes
                - stage
            multi_radar_data: Multi-radar composite data including:
                - num_radars
                - agreement (%)

        Returns:
            HailEvent with complete classification
        """

        # Extract features
        features = self.model.extract_features(
            radar_data=radar_data,
            environmental_data=environmental_data,
            cell_data=cell_data
        )

        # Get ML prediction
        prediction = self.model.predict(features)

        # Create event object
        event = HailEvent(
            timestamp=timestamp,
            location=(lat, lon),
            max_reflectivity=radar_data.get('max_reflectivity', 0),
            mesh_mm=radar_data.get('mesh', 0),
            posh=radar_data.get('posh', 0),
            zdr_min=radar_data.get('zdr_min', 0),
            cc_min=radar_data.get('cc_min', 1),
            hail_probability=prediction.hail_probability,
            hail_detected=prediction.hail_detected,
            estimated_size_mm=prediction.estimated_size_mm,
            severity=prediction.severity,
            confidence=prediction.confidence
        )

        # Add cell tracking info
        if cell_data:
            event.cell_id = cell_data.get('cell_id')
            event.cell_velocity_kmh = cell_data.get('velocity_kmh', 0)
            event.cell_direction_deg = cell_data.get('direction_deg', 0)
            event.cell_age_minutes = cell_data.get('age_minutes', 0)

        # Add multi-radar info
        if multi_radar_data:
            event.num_radars = multi_radar_data.get('num_radars', 0)
            event.radar_agreement = multi_radar_data.get('agreement', 0)

        # Calculate PDR opportunity score
        event.pdr_opportunity_score = self._calculate_pdr_score(event)

        return event

    def classify_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> List[HailEvent]:
        """
        Classify multiple events at once.

        Args:
            events: List of event dicts, each with:
                - lat, lon, timestamp
                - radar_data
                - environmental_data (optional)
                - cell_data (optional)

        Returns:
            List of HailEvent objects
        """
        results = []

        for event_data in events:
            event = self.classify(
                lat=event_data['lat'],
                lon=event_data['lon'],
                timestamp=event_data['timestamp'],
                radar_data=event_data.get('radar_data', {}),
                environmental_data=event_data.get('environmental_data'),
                cell_data=event_data.get('cell_data'),
                multi_radar_data=event_data.get('multi_radar_data')
            )
            results.append(event)

        return results

    def _calculate_pdr_score(self, event: HailEvent) -> float:
        """
        Calculate PDR (Paintless Dent Repair) opportunity score.

        Higher score = better PDR opportunity.

        Factors:
        - Hail size (moderate hail = best for PDR)
        - Confidence in detection
        - Multi-radar agreement
        - Cell age (established cells = more reliable)
        """
        if not event.hail_detected:
            return 0.0

        score = 0.0

        # Size score (25-50mm is ideal for PDR)
        size = event.estimated_size_mm
        if 25 <= size <= 50:
            score += 40  # Ideal range
        elif 15 <= size < 25:
            score += 30  # Good range
        elif 50 < size <= 65:
            score += 25  # Larger but still PDR-able
        elif size < 15:
            score += 10  # Too small, less damage
        else:
            score += 15  # Very large, may need body work

        # Confidence score
        score += event.confidence * 0.3

        # Probability score
        score += event.hail_probability * 0.2

        # Multi-radar agreement bonus
        if event.num_radars >= 2:
            score += event.radar_agreement * 0.1

        # Cell age bonus (more established = more reliable)
        if event.cell_age_minutes >= 20:
            score += 5

        return min(score, 100)

    def get_model_info(self) -> Dict:
        """Get information about the underlying model."""
        return self.model.get_model_info()

    def train(
        self,
        training_data: List[TrainingExample],
        save_model: bool = True
    ) -> Dict:
        """
        Train the classifier on provided data.

        Args:
            training_data: List of TrainingExample objects
            save_model: Whether to save the trained model

        Returns:
            Training results dict
        """
        results = self.model.train(training_data)

        if save_model and results.get('success'):
            self.model.save()

        return results

    def get_feature_importance(self) -> List[Tuple[str, float]]:
        """Get ranked feature importance from the model."""
        return sorted(
            self.model.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )


# ============================================================================
# Convenience Functions
# ============================================================================

def classify_hail_event(
    lat: float,
    lon: float,
    timestamp: datetime,
    max_reflectivity: float,
    mesh_mm: float = 0,
    posh: float = 0,
    zdr_min: float = 0.5,
    cc_min: float = 0.97
) -> HailEvent:
    """
    Quick convenience function for hail classification.

    Args:
        lat: Latitude
        lon: Longitude
        timestamp: Event time
        max_reflectivity: Maximum reflectivity (dBZ)
        mesh_mm: MESH value (mm)
        posh: POSH value (%)
        zdr_min: Minimum ZDR (dB)
        cc_min: Minimum correlation coefficient

    Returns:
        HailEvent with classification
    """
    classifier = HailClassifier(simulation_mode=True)

    return classifier.classify(
        lat=lat,
        lon=lon,
        timestamp=timestamp,
        radar_data={
            'max_reflectivity': max_reflectivity,
            'mesh': mesh_mm,
            'posh': posh,
            'zdr_min': zdr_min,
            'cc_min': cc_min
        }
    )


# ============================================================================
# Test
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("HAIL CLASSIFIER TEST")
    print("=" * 70)

    # Create classifier (simulation mode for quick test)
    classifier = HailClassifier(simulation_mode=True)

    print("\nClassifying test event...")

    event = classifier.classify(
        lat=32.7767,
        lon=-96.7970,
        timestamp=datetime.now(),
        radar_data={
            'max_reflectivity': 65,
            'mesh': 42,
            'posh': 85,
            'zdr_min': 0.2,
            'cc_min': 0.91
        },
        cell_data={
            'cell_id': 1,
            'velocity_kmh': 55,
            'direction_deg': 45,
            'age_minutes': 35
        },
        multi_radar_data={
            'num_radars': 3,
            'agreement': 92
        }
    )

    print(f"\nResults:")
    print(f"  Location: ({event.location[0]:.4f}, {event.location[1]:.4f})")
    print(f"  Hail Detected: {event.hail_detected}")
    print(f"  Probability: {event.hail_probability:.1f}%")
    print(f"  Size: {event.estimated_size_mm:.1f} mm ({event.estimated_size_mm/25.4:.2f}\")")
    print(f"  Severity: {event.severity}")
    print(f"  Confidence: {event.confidence:.1f}%")
    print(f"  PDR Score: {event.pdr_opportunity_score:.1f}")

    print("\n" + "=" * 70)
