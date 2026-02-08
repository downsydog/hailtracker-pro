"""
HailTracker Pro ML Inference Module

Provides unified interface for all 15 trained models.
"""

from pathlib import Path
import logging

logger = logging.getLogger('MLInference')

MODELS_DIR = Path(__file__).parent.parent / 'models' / 'saved'


class HailTrackerML:
    """
    Unified interface for all HailTracker ML models.

    Usage:
        ml = HailTrackerML()
        ml.load_all()

        # Radar analysis
        result = ml.analyze_radar(radar_data)

        # Storm forecast
        forecast = ml.forecast_storm(radar_trend, environment)

        # Photo analysis
        size = ml.estimate_hail_size(image)
        damage = ml.detect_vehicle_damage(image)
        valid = ml.validate_photo(image, metadata)

        # PDR business
        score = ml.score_opportunity(event)
        claim = ml.predict_claim_rate(event)

        # Advanced
        route = ml.optimize_route(locations)
        sentiment = ml.analyze_sentiment(text)
    """

    def __init__(self):
        self._models = {}
        self._loaded = False

    def load_all(self) -> bool:
        """Load all trained models."""
        try:
            # Import model classes
            from src.ml.models.radar_hail_classifier import RadarHailClassifier
            from src.ml.models.storm_forecaster import StormSeverityForecaster
            from src.ml.models.seasonal_risk import SeasonalRiskModel
            from src.ml.models.hail_size_estimator import HailSizeEstimator
            from src.ml.models.vehicle_damage_detector import VehicleDamageDetector
            from src.ml.models.photo_validator import PhotoAuthenticityValidator
            from src.ml.models.pdr_business_models import (
                MLOpportunityScorer, ClaimRatePredictor,
                DamagePredictionModel, ParkingLotVehicleCounter
            )
            from src.ml.models.advanced_models import (
                RouteOptimizer, ConversionPredictor,
                DealershipInventoryEstimator, SentimentAnalyzer,
                RepairTimeEstimator
            )

            # Load each model
            self._models['radar_classifier'] = RadarHailClassifier()
            self._models['radar_classifier'].load()

            self._models['storm_forecaster'] = StormSeverityForecaster()
            self._models['storm_forecaster'].load()

            self._models['seasonal_risk'] = SeasonalRiskModel()
            self._models['seasonal_risk'].load()

            self._models['size_estimator'] = HailSizeEstimator()
            self._models['size_estimator'].load()

            self._models['damage_detector'] = VehicleDamageDetector()
            self._models['damage_detector'].load()

            self._models['photo_validator'] = PhotoAuthenticityValidator()
            self._models['photo_validator'].load()

            self._models['opportunity_scorer'] = MLOpportunityScorer()
            self._models['opportunity_scorer'].load()

            self._models['claim_predictor'] = ClaimRatePredictor()
            self._models['claim_predictor'].load()

            self._models['damage_predictor'] = DamagePredictionModel()
            self._models['damage_predictor'].load()

            self._models['vehicle_counter'] = ParkingLotVehicleCounter()
            self._models['vehicle_counter'].load()

            self._models['route_optimizer'] = RouteOptimizer()
            self._models['route_optimizer'].load()

            self._models['conversion_predictor'] = ConversionPredictor()
            self._models['conversion_predictor'].load()

            self._models['inventory_estimator'] = DealershipInventoryEstimator()
            self._models['inventory_estimator'].load()

            self._models['sentiment_analyzer'] = SentimentAnalyzer()
            self._models['sentiment_analyzer'].load()

            self._models['repair_estimator'] = RepairTimeEstimator()
            self._models['repair_estimator'].load()

            self._loaded = True
            logger.info("All 15 models loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            return False

    # TIER 1: Meteorology
    def analyze_radar(self, radar_data: dict) -> dict:
        """Analyze radar data for hail detection."""
        return self._models['radar_classifier'].classify(radar_data)

    def forecast_storm(self, radar_trend: list, environment: dict) -> dict:
        """Forecast storm severity."""
        return self._models['storm_forecaster'].forecast(radar_trend, environment)

    def assess_seasonal_risk(self, lat: float, lon: float, month: int = None) -> dict:
        """Assess seasonal hail risk for location."""
        return self._models['seasonal_risk'].predict_risk(lat, lon, month)

    # TIER 2: Photo Analysis
    def estimate_hail_size(self, image) -> dict:
        """Estimate hail size from photo."""
        return self._models['size_estimator'].estimate_size(image)

    def detect_vehicle_damage(self, image) -> dict:
        """Detect vehicle damage in photo."""
        return self._models['damage_detector'].detect_damage(image)

    def validate_photo(self, image, metadata: dict = None) -> dict:
        """Validate photo authenticity."""
        return self._models['photo_validator'].validate(image, metadata)

    # TIER 3: PDR Business
    def score_opportunity(self, event: dict) -> dict:
        """Score hail event for PDR opportunity."""
        return self._models['opportunity_scorer'].score_event(event)

    def predict_claim_rate(self, event: dict) -> dict:
        """Predict insurance claim rate."""
        return self._models['claim_predictor'].predict_claim_rate(event)

    def predict_damage(self, storm: dict) -> dict:
        """Predict damage from storm parameters."""
        return self._models['damage_predictor'].predict_damage(storm)

    def estimate_vehicles(self, area: dict) -> dict:
        """Estimate vehicles in affected area."""
        return self._models['vehicle_counter'].estimate_vehicles(area)

    # TIER 4: Advanced
    def optimize_route(self, locations: list) -> dict:
        """Optimize route through locations."""
        return self._models['route_optimizer'].optimize_route(locations)

    def predict_conversion(self, lead: dict) -> dict:
        """Predict lead conversion probability."""
        return self._models['conversion_predictor'].predict_conversion(lead)

    def estimate_inventory(self, dealership: dict) -> dict:
        """Estimate dealership inventory."""
        return self._models['inventory_estimator'].estimate_inventory(dealership)

    def analyze_sentiment(self, text: str) -> dict:
        """Analyze text sentiment."""
        return self._models['sentiment_analyzer'].analyze(text)

    def estimate_repair_time(self, job: dict) -> dict:
        """Estimate repair time."""
        return self._models['repair_estimator'].estimate_time(job)

    def get_model_status(self) -> dict:
        """Get status of all models."""
        return {
            'loaded': self._loaded,
            'model_count': len(self._models),
            'models': list(self._models.keys())
        }
