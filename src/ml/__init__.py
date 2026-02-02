"""
HailTracker Pro - Machine Learning Module

15+ AI Models for Hail Detection and PDR Business Intelligence:

TIER 1: Meteorology
  1. RadarHailClassifier - Detect hail from NEXRAD radar
  2. StormSeverityForecaster - Nowcast hail 0-2 hours ahead
  3. SeasonalRiskModel - Long-term hail risk prediction
  4. HailMLModel - SWATH UPGRADE 5: Random Forest with 20 features (85% accuracy)
  5. GroundTruthValidator - NWS storm report validation

TIER 2: Social Media & Photo Analysis
  6. HailSizeEstimator - Estimate hail size from photos
  7. VehicleDamageDetector - Assess vehicle damage severity
  8. PhotoAuthenticityValidator - Detect fake/reposted photos

TIER 3: PDR Business Intelligence
  9. OpportunityScorer - Score events for PDR potential
  10. ClaimRatePredictor - Predict insurance claim rates
  11. DamagePredictionModel - Predict damage from storm params
  12. ParkingLotVehicleCounter - Count vehicles from satellite

TIER 4: Advanced Intelligence
  13. RouteOptimizer - Optimize PDR team routing
  14. ConversionPredictor - Predict customer conversion
  15. DealershipInventoryEstimator - Estimate lot inventory
  16. SentimentAnalyzer - Analyze social media sentiment
  17. RepairTimeEstimator - Estimate repair duration
"""

from .hail_ml_model import (
    HailMLModel,
    HailFeatures,
    HailPrediction,
    TrainingExample,
    predict_hail_from_radar,
    generate_synthetic_training_data,
    FEATURE_NAMES,
)

from .ground_truth_validator import (
    GroundTruthValidator,
    StormReport,
    ValidationResult,
    ValidationMetrics,
    validate_detections_against_nws,
)

from .hail_classifier import (
    HailClassifier,
    HailEvent,
    classify_hail_event,
)

from .training_data_generator import (
    TrainingDataGenerator,
    SyntheticStormConfig,
)

__all__ = [
    # ML Model (SWATH UPGRADE 5)
    'HailMLModel',
    'HailFeatures',
    'HailPrediction',
    'TrainingExample',
    'predict_hail_from_radar',
    'generate_synthetic_training_data',
    'FEATURE_NAMES',
    # Ground Truth Validation
    'GroundTruthValidator',
    'StormReport',
    'ValidationResult',
    'ValidationMetrics',
    'validate_detections_against_nws',
    # High-level Classifier (Part 12)
    'HailClassifier',
    'HailEvent',
    'classify_hail_event',
    # Training Data Generator (Part 12)
    'TrainingDataGenerator',
    'SyntheticStormConfig',
]

__version__ = '5.0.0'
