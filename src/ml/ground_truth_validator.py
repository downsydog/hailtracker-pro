"""
SWATH UPGRADE 5: Ground Truth Validator

Validates hail detections against NWS Storm Prediction Center reports.

Data sources:
- NWS Storm Reports (https://www.spc.noaa.gov/climo/reports/)
- Local Spotter Network reports
- ASOS/AWOS automated observations
- mPING crowd-sourced reports

Validation metrics:
- True Positives: ML predicted hail, NWS confirmed hail
- False Positives: ML predicted hail, no NWS report
- False Negatives: No ML prediction, NWS reported hail
- True Negatives: No ML prediction, no hail

Ground truth matching:
- Spatial: Within 10km radius of detection
- Temporal: Within 30 minutes of radar scan
- Size verification: Compare predicted vs reported size
"""

import math
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

import numpy as np

logger = logging.getLogger('GroundTruthValidator')


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class StormReport:
    """NWS storm report data."""

    report_id: str
    report_time: datetime
    latitude: float
    longitude: float

    # Hail specifics
    hail_size_inches: float
    hail_size_mm: float

    # Report metadata
    source: str  # 'trained_spotter', 'public', 'official', 'automated'
    location_name: str
    state: str
    county: str

    # Reliability score (0-100)
    reliability: float = 80.0

    # Additional info
    remarks: str = ""
    property_damage: bool = False
    injuries: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'report_id': self.report_id,
            'report_time': self.report_time.isoformat(),
            'latitude': self.latitude,
            'longitude': self.longitude,
            'hail_size_inches': self.hail_size_inches,
            'hail_size_mm': self.hail_size_mm,
            'source': self.source,
            'location_name': self.location_name,
            'state': self.state,
            'county': self.county,
            'reliability': self.reliability,
            'remarks': self.remarks
        }


@dataclass
class ValidationResult:
    """Result of validating a detection against ground truth."""

    detection_lat: float
    detection_lon: float
    detection_time: datetime
    predicted_size_mm: float

    # Match info
    matched: bool
    match_distance_km: Optional[float] = None
    match_time_diff_minutes: Optional[float] = None
    matched_report: Optional[StormReport] = None

    # Size comparison
    size_error_mm: Optional[float] = None
    size_error_inches: Optional[float] = None

    # Classification
    classification: str = 'unknown'  # true_positive, false_positive, false_negative

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'detection_lat': self.detection_lat,
            'detection_lon': self.detection_lon,
            'detection_time': self.detection_time.isoformat(),
            'predicted_size_mm': self.predicted_size_mm,
            'matched': self.matched,
            'match_distance_km': self.match_distance_km,
            'match_time_diff_minutes': self.match_time_diff_minutes,
            'size_error_mm': self.size_error_mm,
            'classification': self.classification
        }


@dataclass
class ValidationMetrics:
    """Aggregate validation metrics."""

    total_detections: int = 0
    total_reports: int = 0

    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    # Calculated metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # Size estimation metrics
    size_mae_mm: float = 0.0  # Mean Absolute Error
    size_rmse_mm: float = 0.0  # Root Mean Square Error
    size_bias_mm: float = 0.0  # Systematic bias

    def calculate_metrics(self):
        """Calculate derived metrics."""
        total = self.true_positives + self.false_positives + self.false_negatives + self.true_negatives

        if total > 0:
            self.accuracy = (self.true_positives + self.true_negatives) / total

        if self.true_positives + self.false_positives > 0:
            self.precision = self.true_positives / (self.true_positives + self.false_positives)

        if self.true_positives + self.false_negatives > 0:
            self.recall = self.true_positives / (self.true_positives + self.false_negatives)

        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_detections': self.total_detections,
            'total_reports': self.total_reports,
            'true_positives': self.true_positives,
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'true_negatives': self.true_negatives,
            'accuracy': round(self.accuracy * 100, 1),
            'precision': round(self.precision * 100, 1),
            'recall': round(self.recall * 100, 1),
            'f1_score': round(self.f1_score * 100, 1),
            'size_mae_mm': round(self.size_mae_mm, 1),
            'size_rmse_mm': round(self.size_rmse_mm, 1),
            'size_bias_mm': round(self.size_bias_mm, 1)
        }


# ============================================================================
# Ground Truth Validator
# ============================================================================

class GroundTruthValidator:
    """
    Validates ML hail detections against NWS storm reports.

    Matching criteria:
    - Spatial: Detection within 10km of report
    - Temporal: Detection within 30 minutes of report
    - Both criteria must be met for a match
    """

    # Matching thresholds
    MAX_DISTANCE_KM = 10.0
    MAX_TIME_DIFF_MINUTES = 30.0

    # Source reliability weights
    SOURCE_RELIABILITY = {
        'official': 95,  # NWS official
        'trained_spotter': 90,
        'emergency_manager': 88,
        'law_enforcement': 85,
        'automated': 75,  # ASOS/AWOS
        'public': 60,
        'mping': 55,
        'unknown': 50
    }

    def __init__(self, simulation_mode: bool = False):
        """
        Initialize validator.

        Args:
            simulation_mode: If True, use simulated reports
        """
        self.simulation_mode = simulation_mode

        # Cache for fetched reports
        self.reports_cache: Dict[str, List[StormReport]] = {}

        # Validation history
        self.validation_history: List[ValidationResult] = []

    def fetch_nws_reports(
        self,
        start_time: datetime,
        end_time: datetime,
        bounds: Optional[Tuple[float, float, float, float]] = None
    ) -> List[StormReport]:
        """
        Fetch NWS storm reports for a time period.

        Args:
            start_time: Start of time window
            end_time: End of time window
            bounds: Optional (min_lat, max_lat, min_lon, max_lon)

        Returns:
            List of StormReport objects
        """
        if self.simulation_mode:
            return self._generate_simulated_reports(start_time, end_time, bounds)

        # In production, this would fetch from NWS SPC API
        # Example API: https://www.spc.noaa.gov/climo/reports/
        #
        # For now, return empty list (production would implement actual fetch)
        logger.warning("Production NWS API not implemented - use simulation_mode=True")
        return []

    def _generate_simulated_reports(
        self,
        start_time: datetime,
        end_time: datetime,
        bounds: Optional[Tuple[float, float, float, float]] = None
    ) -> List[StormReport]:
        """
        Generate simulated storm reports for testing.
        """
        np.random.seed(int(start_time.timestamp()) % 10000)

        reports = []

        # Default bounds to Tornado Alley
        if bounds is None:
            bounds = (30.0, 40.0, -102.0, -94.0)

        min_lat, max_lat, min_lon, max_lon = bounds

        # Generate 5-20 reports
        n_reports = np.random.randint(5, 21)

        duration_hours = (end_time - start_time).total_seconds() / 3600

        for i in range(n_reports):
            # Random location within bounds
            lat = np.random.uniform(min_lat, max_lat)
            lon = np.random.uniform(min_lon, max_lon)

            # Random time within window
            offset_hours = np.random.uniform(0, duration_hours)
            report_time = start_time + timedelta(hours=offset_hours)

            # Hail size (log-normal distribution, typical sizes)
            size_inches = np.random.lognormal(0.0, 0.5)  # Centered around 1"
            size_inches = min(max(size_inches, 0.75), 4.5)  # Clamp to realistic range

            # Source type
            source = np.random.choice(
                ['trained_spotter', 'public', 'official', 'emergency_manager'],
                p=[0.4, 0.3, 0.2, 0.1]
            )

            # State/county (simplified)
            states = ['TX', 'OK', 'KS', 'NE', 'CO']
            state = np.random.choice(states)

            report = StormReport(
                report_id=f"SIM-{i+1:04d}",
                report_time=report_time,
                latitude=lat,
                longitude=lon,
                hail_size_inches=round(size_inches, 2),
                hail_size_mm=round(size_inches * 25.4, 1),
                source=source,
                location_name=f"Simulated Location {i+1}",
                state=state,
                county=f"{state} County",
                reliability=self.SOURCE_RELIABILITY.get(source, 70)
            )

            reports.append(report)

        return reports

    def validate_detection(
        self,
        detection_lat: float,
        detection_lon: float,
        detection_time: datetime,
        predicted_size_mm: float,
        reports: List[StormReport]
    ) -> ValidationResult:
        """
        Validate a single detection against storm reports.

        Args:
            detection_lat: Detection latitude
            detection_lon: Detection longitude
            detection_time: Detection timestamp
            predicted_size_mm: Predicted hail size
            reports: Available storm reports

        Returns:
            ValidationResult
        """
        result = ValidationResult(
            detection_lat=detection_lat,
            detection_lon=detection_lon,
            detection_time=detection_time,
            predicted_size_mm=predicted_size_mm,
            matched=False
        )

        best_match = None
        best_score = 0

        for report in reports:
            # Calculate distance
            distance = self._calculate_distance(
                detection_lat, detection_lon,
                report.latitude, report.longitude
            )

            # Check spatial criteria
            if distance > self.MAX_DISTANCE_KM:
                continue

            # Calculate time difference
            time_diff = abs((detection_time - report.report_time).total_seconds() / 60)

            # Check temporal criteria
            if time_diff > self.MAX_TIME_DIFF_MINUTES:
                continue

            # Calculate match score (closer = better)
            distance_score = 1 - (distance / self.MAX_DISTANCE_KM)
            time_score = 1 - (time_diff / self.MAX_TIME_DIFF_MINUTES)
            reliability_score = report.reliability / 100

            match_score = (distance_score * 0.4 + time_score * 0.4 + reliability_score * 0.2)

            if match_score > best_score:
                best_score = match_score
                best_match = (report, distance, time_diff)

        if best_match:
            report, distance, time_diff = best_match

            result.matched = True
            result.match_distance_km = distance
            result.match_time_diff_minutes = time_diff
            result.matched_report = report

            # Size comparison
            result.size_error_mm = predicted_size_mm - report.hail_size_mm
            result.size_error_inches = (predicted_size_mm - report.hail_size_mm) / 25.4

            # Classification: True Positive (predicted hail, confirmed hail)
            result.classification = 'true_positive'
        else:
            # No matching report - could be false positive
            # (But could also be under-reported - hail doesn't always get reported)
            result.classification = 'false_positive'

        self.validation_history.append(result)
        return result

    def validate_event(
        self,
        detections: List[Dict],
        event_time: datetime,
        event_bounds: Tuple[float, float, float, float]
    ) -> Dict:
        """
        Validate all detections for a hail event.

        Args:
            detections: List of detection dicts with lat, lon, time, size
            event_time: Approximate event time
            event_bounds: (min_lat, max_lat, min_lon, max_lon)

        Returns:
            Dict with validation results and metrics
        """
        # Fetch reports for the time window
        start_time = event_time - timedelta(hours=1)
        end_time = event_time + timedelta(hours=2)

        reports = self.fetch_nws_reports(start_time, end_time, event_bounds)

        results = []
        matched_reports = set()

        # Validate each detection
        for det in detections:
            det_time = det.get('time', event_time)
            if isinstance(det_time, str):
                det_time = datetime.fromisoformat(det_time)

            result = self.validate_detection(
                detection_lat=det['lat'],
                detection_lon=det['lon'],
                detection_time=det_time,
                predicted_size_mm=det.get('size_mm', 25.0),
                reports=reports
            )

            results.append(result)

            if result.matched and result.matched_report:
                matched_reports.add(result.matched_report.report_id)

        # Find unmatched reports (false negatives)
        unmatched_reports = [r for r in reports if r.report_id not in matched_reports]

        # Calculate metrics
        metrics = self._calculate_metrics(results, len(unmatched_reports))

        return {
            'event_time': event_time.isoformat(),
            'event_bounds': event_bounds,
            'total_detections': len(detections),
            'total_reports': len(reports),
            'matched_detections': sum(1 for r in results if r.matched),
            'unmatched_reports': len(unmatched_reports),
            'metrics': metrics.to_dict(),
            'validation_results': [r.to_dict() for r in results],
            'reports': [r.to_dict() for r in reports]
        }

    def _calculate_metrics(
        self,
        results: List[ValidationResult],
        false_negatives: int
    ) -> ValidationMetrics:
        """
        Calculate aggregate validation metrics.
        """
        metrics = ValidationMetrics()

        metrics.total_detections = len(results)

        # Count by classification
        for result in results:
            if result.classification == 'true_positive':
                metrics.true_positives += 1
            elif result.classification == 'false_positive':
                metrics.false_positives += 1

        metrics.false_negatives = false_negatives

        # Calculate accuracy, precision, recall
        metrics.calculate_metrics()

        # Size estimation errors (for matched detections)
        matched = [r for r in results if r.matched and r.size_error_mm is not None]

        if matched:
            errors = [r.size_error_mm for r in matched]
            metrics.size_mae_mm = float(np.mean(np.abs(errors)))
            metrics.size_rmse_mm = float(np.sqrt(np.mean(np.array(errors) ** 2)))
            metrics.size_bias_mm = float(np.mean(errors))

        return metrics

    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in km using Haversine formula."""
        R = 6371  # Earth radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def get_validation_summary(self) -> Dict:
        """
        Get summary of all validations performed.
        """
        if not self.validation_history:
            return {'total_validations': 0}

        true_positives = sum(1 for r in self.validation_history if r.classification == 'true_positive')
        false_positives = sum(1 for r in self.validation_history if r.classification == 'false_positive')

        matched = [r for r in self.validation_history if r.matched]

        avg_distance = np.mean([r.match_distance_km for r in matched]) if matched else 0
        avg_time_diff = np.mean([r.match_time_diff_minutes for r in matched]) if matched else 0

        return {
            'total_validations': len(self.validation_history),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'match_rate': round(true_positives / len(self.validation_history) * 100, 1) if self.validation_history else 0,
            'avg_match_distance_km': round(avg_distance, 1),
            'avg_match_time_diff_min': round(avg_time_diff, 1)
        }

    def clear_history(self):
        """Clear validation history."""
        self.validation_history = []


# ============================================================================
# NWS Report Parser
# ============================================================================

class NWSReportParser:
    """
    Parser for NWS Storm Prediction Center CSV reports.

    Format: https://www.spc.noaa.gov/climo/reports/
    """

    # Size conversion (text to inches)
    SIZE_DESCRIPTIONS = {
        'penny': 0.75,
        'nickel': 0.88,
        'quarter': 1.00,
        'half dollar': 1.25,
        'ping pong': 1.50,
        'golf ball': 1.75,
        'hen egg': 2.00,
        'tennis ball': 2.50,
        'baseball': 2.75,
        'tea cup': 3.00,
        'softball': 4.00,
        'grapefruit': 4.50
    }

    @classmethod
    def parse_csv_line(cls, line: str) -> Optional[StormReport]:
        """
        Parse a single line from NWS CSV report.

        Expected format (simplified):
        time,size,location,county,state,lat,lon,comments

        Returns:
            StormReport or None if parse fails
        """
        try:
            parts = line.strip().split(',')

            if len(parts) < 7:
                return None

            # Parse time (format: HHMM)
            time_str = parts[0].strip()
            # Would need date from filename

            # Parse size
            size_str = parts[1].strip().lower()

            # Try numeric first
            try:
                size_inches = float(size_str)
            except ValueError:
                # Try text description
                size_inches = cls.SIZE_DESCRIPTIONS.get(size_str, 1.0)

            # Parse location
            location = parts[2].strip()
            county = parts[3].strip()
            state = parts[4].strip()

            # Parse coordinates
            lat = float(parts[5].strip())
            lon = float(parts[6].strip())

            # Comments if present
            comments = parts[7].strip() if len(parts) > 7 else ""

            return StormReport(
                report_id=f"NWS-{hash(line) % 100000:05d}",
                report_time=datetime.now(),  # Would come from context
                latitude=lat,
                longitude=lon,
                hail_size_inches=size_inches,
                hail_size_mm=size_inches * 25.4,
                source='official',
                location_name=location,
                state=state,
                county=county,
                reliability=90,
                remarks=comments
            )

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse line: {e}")
            return None

    @classmethod
    def parse_csv_file(cls, filepath: str, date: datetime) -> List[StormReport]:
        """
        Parse entire NWS CSV file.

        Args:
            filepath: Path to CSV file
            date: Date of reports

        Returns:
            List of StormReport objects
        """
        reports = []

        try:
            with open(filepath, 'r') as f:
                # Skip header
                next(f, None)

                for line in f:
                    if line.strip():
                        report = cls.parse_csv_line(line)
                        if report:
                            # Set date from context
                            report.report_time = date.replace(
                                hour=int(report.report_time.strftime('%H')),
                                minute=int(report.report_time.strftime('%M'))
                            )
                            reports.append(report)

        except FileNotFoundError:
            logger.error(f"File not found: {filepath}")
        except Exception as e:
            logger.error(f"Error parsing file: {e}")

        return reports


# ============================================================================
# Convenience Functions
# ============================================================================

def validate_detections_against_nws(
    detections: List[Dict],
    event_time: datetime,
    event_center: Tuple[float, float],
    radius_km: float = 100.0,
    simulation_mode: bool = True
) -> Dict:
    """
    Convenience function to validate detections.

    Args:
        detections: List of detection dicts
        event_time: Event timestamp
        event_center: (lat, lon) center of event
        radius_km: Search radius
        simulation_mode: Use simulated reports

    Returns:
        Validation results dict
    """
    validator = GroundTruthValidator(simulation_mode=simulation_mode)

    # Calculate bounds from center and radius
    lat, lon = event_center
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    bounds = (
        lat - lat_delta,
        lat + lat_delta,
        lon - lon_delta,
        lon + lon_delta
    )

    return validator.validate_event(detections, event_time, bounds)


def calculate_model_accuracy_with_ground_truth(
    predictions: List[Dict],
    reports: List[StormReport]
) -> Dict:
    """
    Calculate model accuracy against ground truth reports.

    Args:
        predictions: List of ML predictions with lat, lon, time, predicted_hail
        reports: List of NWS storm reports

    Returns:
        Accuracy metrics dict
    """
    validator = GroundTruthValidator(simulation_mode=False)

    # Convert predictions to detections (only positive predictions)
    detections = [
        {
            'lat': p['lat'],
            'lon': p['lon'],
            'time': p.get('time', datetime.now()),
            'size_mm': p.get('predicted_size_mm', 25.0)
        }
        for p in predictions
        if p.get('predicted_hail', False)
    ]

    results = []
    matched_reports = set()

    for det in detections:
        det_time = det['time']
        if isinstance(det_time, str):
            det_time = datetime.fromisoformat(det_time)

        result = validator.validate_detection(
            det['lat'], det['lon'], det_time, det['size_mm'], reports
        )
        results.append(result)

        if result.matched and result.matched_report:
            matched_reports.add(result.matched_report.report_id)

    # False negatives: reports with no matching detection
    false_negatives = len(reports) - len(matched_reports)

    metrics = validator._calculate_metrics(results, false_negatives)

    return {
        'total_predictions': len(predictions),
        'positive_predictions': len(detections),
        'total_reports': len(reports),
        'metrics': metrics.to_dict()
    }


# ============================================================================
# Test
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("GROUND TRUTH VALIDATOR - SWATH UPGRADE 5")
    print("=" * 70)

    validator = GroundTruthValidator(simulation_mode=True)

    # Test fetching simulated reports
    print("\n[1/4] Fetching simulated NWS reports...")
    event_time = datetime(2024, 5, 20, 18, 30)
    reports = validator.fetch_nws_reports(
        start_time=event_time - timedelta(hours=1),
        end_time=event_time + timedelta(hours=2),
        bounds=(32.0, 35.0, -98.0, -95.0)
    )

    print(f"  Fetched {len(reports)} simulated reports")
    print()

    for report in reports[:3]:
        print(f"  Report {report.report_id}:")
        print(f"    Time: {report.report_time.strftime('%H:%M')}")
        print(f"    Location: ({report.latitude:.4f}, {report.longitude:.4f})")
        print(f"    Size: {report.hail_size_inches}\" ({report.hail_size_mm}mm)")
        print(f"    Source: {report.source}")
        print()

    # Test validation
    print("[2/4] Validating simulated detections...")

    # Create some detections near the reports
    detections = []

    for i, report in enumerate(reports[:5]):
        # Create a detection near each report (some exact, some offset)
        lat_offset = np.random.uniform(-0.05, 0.05)
        lon_offset = np.random.uniform(-0.05, 0.05)
        time_offset = np.random.uniform(-20, 20)

        detections.append({
            'lat': report.latitude + lat_offset,
            'lon': report.longitude + lon_offset,
            'time': report.report_time + timedelta(minutes=time_offset),
            'size_mm': report.hail_size_mm * np.random.uniform(0.8, 1.2)
        })

    # Add some false positives (no matching report)
    for i in range(3):
        detections.append({
            'lat': 33.5 + np.random.uniform(-0.5, 0.5),
            'lon': -96.5 + np.random.uniform(-0.5, 0.5),
            'time': event_time + timedelta(minutes=np.random.uniform(-30, 30)),
            'size_mm': np.random.uniform(20, 40)
        })

    print(f"  Validating {len(detections)} detections against {len(reports)} reports...")
    print()

    validation_results = validator.validate_event(
        detections=detections,
        event_time=event_time,
        event_bounds=(32.0, 35.0, -98.0, -95.0)
    )

    print("[3/4] Validation Results:")
    metrics = validation_results['metrics']
    print(f"  True Positives: {metrics['true_positives']}")
    print(f"  False Positives: {metrics['false_positives']}")
    print(f"  False Negatives: {metrics['false_negatives']}")
    print()
    print(f"  Accuracy: {metrics['accuracy']}%")
    print(f"  Precision: {metrics['precision']}%")
    print(f"  Recall: {metrics['recall']}%")
    print(f"  F1 Score: {metrics['f1_score']}%")
    print()
    print(f"  Size MAE: {metrics['size_mae_mm']} mm")
    print(f"  Size Bias: {metrics['size_bias_mm']} mm")

    # Test summary
    print("\n[4/4] Validation Summary:")
    summary = validator.get_validation_summary()
    print(f"  Total validations: {summary['total_validations']}")
    print(f"  Match rate: {summary['match_rate']}%")
    print(f"  Avg match distance: {summary['avg_match_distance_km']} km")
    print(f"  Avg time difference: {summary['avg_match_time_diff_min']} min")

    print("\n" + "=" * 70)
    print("GROUND TRUTH VALIDATION COMPLETE")
    print("=" * 70)
