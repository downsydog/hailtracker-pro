"""
Model 3: Seasonal Hail Risk Model

Predicts long-term hail risk for any location and month in North America.

Input:
- Location (lat/lon)
- Month of year
- Historical climate data

Output:
- Monthly hail probability
- Expected events per year
- Peak season months
- Average hail size
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pickle
import logging

logger = logging.getLogger('SeasonalRiskModel')

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class SeasonalRiskModel:
    """
    Predicts seasonal hail risk based on location and time of year.

    Uses historical hail frequency data to model risk patterns
    across North America.
    """

    # Known high-risk regions (approximate centers)
    HIGH_RISK_REGIONS = {
        'tornado_alley': {'lat': 35.5, 'lon': -98.0, 'radius': 5.0, 'peak_months': [5, 6], 'base_risk': 0.8},
        'texas_panhandle': {'lat': 35.2, 'lon': -101.8, 'radius': 3.0, 'peak_months': [5, 6], 'base_risk': 0.75},
        'denver_corridor': {'lat': 39.7, 'lon': -104.9, 'radius': 2.0, 'peak_months': [5, 6, 7], 'base_risk': 0.7},
        'kansas': {'lat': 38.5, 'lon': -98.0, 'radius': 3.0, 'peak_months': [5, 6], 'base_risk': 0.75},
        'nebraska': {'lat': 41.5, 'lon': -99.5, 'radius': 3.0, 'peak_months': [5, 6, 7], 'base_risk': 0.65},
        'alberta': {'lat': 51.5, 'lon': -114.0, 'radius': 3.0, 'peak_months': [6, 7], 'base_risk': 0.55},
        'dakota': {'lat': 44.0, 'lon': -100.0, 'radius': 4.0, 'peak_months': [6, 7], 'base_risk': 0.6},
    }

    # Month names for output
    MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'seasonal_risk.pkl'
        )

        self.frequency_model = None
        self.size_model = None
        self.scaler = None
        self.is_fitted = False

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate approximate distance in degrees."""
        return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2)

    def extract_features(self, lat: float, lon: float, month: int) -> np.ndarray:
        """
        Extract features for risk prediction.

        Args:
            lat: Latitude
            lon: Longitude
            month: Month (1-12)

        Returns:
            Feature vector
        """
        features = []

        # Basic location features
        features.extend([lat, lon])

        # Month as cyclic features
        features.extend([
            np.sin(2 * np.pi * month / 12),
            np.cos(2 * np.pi * month / 12),
        ])

        # Distance to high-risk regions
        for region_name, region in self.HIGH_RISK_REGIONS.items():
            dist = self._calculate_distance(lat, lon, region['lat'], region['lon'])
            features.append(dist)

            # In peak season for this region?
            in_peak = 1 if month in region['peak_months'] else 0
            features.append(in_peak)

        # Latitude-based features (hail corridor roughly 30-50N)
        in_hail_belt = 1 if 30 <= lat <= 50 else 0
        features.append(in_hail_belt)

        # Longitude-based (Great Plains roughly -105 to -90)
        in_plains = 1 if -105 <= lon <= -90 else 0
        features.append(in_plains)

        # Season features
        is_spring = 1 if month in [3, 4, 5] else 0
        is_summer = 1 if month in [6, 7, 8] else 0
        features.extend([is_spring, is_summer])

        return np.array(features)

    def predict_risk(self, lat: float, lon: float, month: Optional[int] = None) -> Dict:
        """
        Predict hail risk for a location.

        Args:
            lat: Latitude
            lon: Longitude
            month: Specific month (1-12) or None for all months

        Returns:
            Risk assessment dict
        """
        if month is not None:
            # Single month prediction
            return self._predict_single_month(lat, lon, month)
        else:
            # Full year prediction
            return self._predict_full_year(lat, lon)

    def _predict_single_month(self, lat: float, lon: float, month: int) -> Dict:
        """Predict for a single month."""
        features = self.extract_features(lat, lon, month)

        if self.is_fitted and self.scaler is not None:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            frequency = self.frequency_model.predict(features_scaled)[0]
            avg_size = self.size_model.predict(features_scaled)[0]
        else:
            frequency, avg_size = self._rule_based_prediction(lat, lon, month)

        # Calculate probability from frequency
        probability = min(0.99, 1 - np.exp(-frequency / 5))

        return {
            'month': self.MONTH_NAMES[month - 1],
            'hail_probability': round(probability * 100, 1),
            'expected_events': round(max(0, frequency), 1),
            'avg_hail_size_inches': round(max(0.25, avg_size), 2),
            'risk_level': self._get_risk_level(probability)
        }

    def _predict_full_year(self, lat: float, lon: float) -> Dict:
        """Predict for full year."""
        monthly_data = []
        total_events = 0
        peak_months = []
        max_prob = 0

        for month in range(1, 13):
            result = self._predict_single_month(lat, lon, month)
            monthly_data.append(result)
            total_events += result['expected_events']

            if result['hail_probability'] > max_prob:
                max_prob = result['hail_probability']

            if result['hail_probability'] >= 30:
                peak_months.append(month)

        # Determine season
        if peak_months:
            season_start = min(peak_months)
            season_end = max(peak_months)
        else:
            season_start = 5
            season_end = 7

        return {
            'location': {'lat': lat, 'lon': lon},
            'monthly_risk': monthly_data,
            'annual_summary': {
                'total_expected_events': round(total_events, 1),
                'peak_probability': round(max_prob, 1),
                'peak_months': [self.MONTH_NAMES[m-1] for m in peak_months] if peak_months else ['May', 'Jun'],
                'season_start': self.MONTH_NAMES[season_start - 1],
                'season_end': self.MONTH_NAMES[season_end - 1],
                'overall_risk': self._get_risk_level(max_prob / 100)
            }
        }

    def _rule_based_prediction(self, lat: float, lon: float, month: int) -> Tuple[float, float]:
        """
        Rule-based prediction when ML model not available.
        """
        # Base risk from proximity to high-risk regions
        max_risk = 0.05
        for region in self.HIGH_RISK_REGIONS.values():
            dist = self._calculate_distance(lat, lon, region['lat'], region['lon'])
            if dist < region['radius']:
                proximity_factor = 1 - (dist / region['radius'])
                month_factor = 1.5 if month in region['peak_months'] else 0.3
                risk = region['base_risk'] * proximity_factor * month_factor
                max_risk = max(max_risk, risk)

        # Latitude adjustment
        if not (25 <= lat <= 55):
            max_risk *= 0.3

        # Convert to expected frequency (0-20 events/month scale)
        frequency = max_risk * 15

        # Size estimation
        if max_risk >= 0.6:
            avg_size = 1.5
        elif max_risk >= 0.4:
            avg_size = 1.25
        elif max_risk >= 0.2:
            avg_size = 1.0
        else:
            avg_size = 0.75

        return frequency, avg_size

    def _get_risk_level(self, probability: float) -> str:
        """Convert probability to risk level."""
        if probability >= 0.6:
            return 'VERY HIGH'
        elif probability >= 0.4:
            return 'HIGH'
        elif probability >= 0.2:
            return 'MODERATE'
        elif probability >= 0.1:
            return 'LOW'
        else:
            return 'MINIMAL'

    def fit(self, X: np.ndarray, y_frequency: np.ndarray, y_size: np.ndarray):
        """Train the model."""
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.frequency_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.frequency_model.fit(X_scaled, y_frequency)

        self.size_model = RandomForestRegressor(
            n_estimators=100,
            max_depth=8,
            random_state=42
        )
        self.size_model.fit(X_scaled, y_size)

        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        """Save model."""
        save_path = path or self.model_path

        model_data = {
            'frequency_model': self.frequency_model,
            'size_model': self.size_model,
            'scaler': self.scaler,
            'is_fitted': self.is_fitted,
            'version': '1.0.0'
        }

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[str] = None) -> bool:
        """Load model."""
        load_path = path or self.model_path

        if not Path(load_path).exists():
            return False

        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)

        self.frequency_model = model_data['frequency_model']
        self.size_model = model_data['size_model']
        self.scaler = model_data['scaler']
        self.is_fitted = model_data['is_fitted']

        return True


def generate_synthetic_seasonal_data(n_samples: int = 3000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic training data for seasonal model."""
    np.random.seed(42)

    X = []
    y_frequency = []
    y_size = []

    model = SeasonalRiskModel()

    for _ in range(n_samples):
        # Random location in North America
        lat = np.random.uniform(25, 55)
        lon = np.random.uniform(-120, -70)
        month = np.random.randint(1, 13)

        features = model.extract_features(lat, lon, month)
        X.append(features)

        # Generate labels based on known patterns
        freq, size = model._rule_based_prediction(lat, lon, month)

        # Add noise
        freq = max(0, freq + np.random.normal(0, freq * 0.2))
        size = max(0.25, size + np.random.normal(0, 0.2))

        y_frequency.append(freq)
        y_size.append(size)

    return np.array(X), np.array(y_frequency), np.array(y_size)


def train_seasonal_risk_model(save_path: Optional[str] = None) -> Dict:
    """Train the seasonal risk model."""
    print("\n" + "=" * 60)
    print("TRAINING: Seasonal Hail Risk Model")
    print("=" * 60)

    # Generate data
    print("\n[1/4] Generating training data...")
    X, y_freq, y_size = generate_synthetic_seasonal_data(n_samples=3000)
    print(f"  Generated {len(X)} samples")

    # Split
    print("\n[2/4] Splitting train/validation...")
    X_train, X_val, y_freq_train, y_freq_val, y_size_train, y_size_val = train_test_split(
        X, y_freq, y_size, test_size=0.2, random_state=42
    )
    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")

    # Train
    print("\n[3/4] Training model...")
    model = SeasonalRiskModel()
    model.fit(X_train, y_freq_train, y_size_train)
    print("  Model trained successfully")

    # Validate
    print("\n[4/4] Validating...")
    X_val_scaled = model.scaler.transform(X_val)

    freq_pred = model.frequency_model.predict(X_val_scaled)
    size_pred = model.size_model.predict(X_val_scaled)

    freq_mae = mean_absolute_error(y_freq_val, freq_pred)
    freq_r2 = r2_score(y_freq_val, freq_pred)
    size_mae = mean_absolute_error(y_size_val, size_pred)

    print(f"  Frequency MAE: {freq_mae:.2f} events")
    print(f"  Frequency R²: {freq_r2:.3f}")
    print(f"  Size MAE: {size_mae:.2f} inches")

    # Save
    if save_path is None:
        save_path = str(Path(__file__).parent / 'saved' / 'seasonal_risk.pkl')

    model.save(save_path)
    print(f"\n  Model saved to: {save_path}")

    return {
        'model': 'SeasonalRiskModel',
        'frequency_mae': freq_mae,
        'frequency_r2': freq_r2,
        'size_mae': size_mae,
        'model_path': save_path,
        'status': 'SUCCESS' if freq_r2 >= 0.5 else 'BELOW_TARGET'
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    results = train_seasonal_risk_model()

    # Test inference
    print("\n" + "=" * 60)
    print("TESTING: Location Risk Assessment")
    print("=" * 60)

    model = SeasonalRiskModel()
    model.load()

    # Test locations
    test_locations = [
        ('Oklahoma City, OK', 35.47, -97.52),
        ('Denver, CO', 39.74, -104.99),
        ('Calgary, AB', 51.04, -114.07),
        ('Miami, FL', 25.76, -80.19),
    ]

    for name, lat, lon in test_locations:
        risk = model.predict_risk(lat, lon)
        summary = risk['annual_summary']

        print(f"\n{name}:")
        print(f"  Annual Events: {summary['total_expected_events']}")
        print(f"  Peak Months: {', '.join(summary['peak_months'])}")
        print(f"  Peak Probability: {summary['peak_probability']}%")
        print(f"  Overall Risk: {summary['overall_risk']}")
