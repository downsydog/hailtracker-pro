"""
Model 2: Storm Severity Forecaster (Nowcasting)

LSTM-based model for predicting hail likelihood 0-2 hours ahead.

Input:
- Current radar trends (last 30 min)
- Environmental parameters (CAPE, shear, freezing level)
- Storm motion vectors

Output:
- Hail probability at 15, 30, 60, 120 minutes
- Expected max size
- Confidence scores
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pickle
import logging
from datetime import datetime, timedelta

logger = logging.getLogger('StormForecaster')

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class StormSeverityForecaster:
    """
    Nowcasting model for hail prediction at multiple time horizons.

    Uses radar trends and environmental data to predict hail likelihood
    at 15, 30, 60, and 120 minute lead times.
    """

    # Environmental parameter thresholds for severe weather
    SEVERE_THRESHOLDS = {
        'cape': 2000,       # J/kg - Convective Available Potential Energy
        'shear': 40,        # knots - 0-6km wind shear
        'freezing_level': 3000,  # meters - lower = larger hail
        'lapse_rate': 7.0,  # C/km - steeper = more unstable
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'storm_forecaster.pkl'
        )

        # Models for each time horizon
        self.models = {
            '15min': {'prob': None, 'size': None},
            '30min': {'prob': None, 'size': None},
            '60min': {'prob': None, 'size': None},
            '120min': {'prob': None, 'size': None},
        }

        self.scaler = None
        self.is_fitted = False

    def extract_features(self, radar_trend: List[Dict], environment: Dict) -> np.ndarray:
        """
        Extract features for forecasting.

        Args:
            radar_trend: List of radar observations (chronological)
            environment: Environmental parameters

        Returns:
            Feature vector
        """
        features = []

        # Radar trend features
        if radar_trend:
            max_refs = [obs.get('max_reflectivity', 40) for obs in radar_trend]
            features.extend([
                max_refs[-1],  # Current max reflectivity
                np.mean(max_refs),  # Mean over trend
                max_refs[-1] - max_refs[0] if len(max_refs) > 1 else 0,  # Trend
                np.max(max_refs),  # Peak during period
                np.std(max_refs) if len(max_refs) > 1 else 0,  # Variability
            ])

            # Storm motion
            if len(radar_trend) >= 2:
                features.append(radar_trend[-1].get('storm_speed', 30))
                features.append(radar_trend[-1].get('storm_direction', 270))
            else:
                features.extend([30, 270])

            # VIL trend
            vils = [obs.get('vil', 30) for obs in radar_trend]
            features.extend([
                vils[-1],
                vils[-1] - vils[0] if len(vils) > 1 else 0,
            ])
        else:
            features.extend([40, 40, 0, 40, 0, 30, 270, 30, 0])

        # Environmental features
        features.extend([
            environment.get('cape', 1500),
            environment.get('cin', -50),
            environment.get('shear_0_6km', 30),
            environment.get('shear_0_1km', 15),
            environment.get('freezing_level', 3500),
            environment.get('wet_bulb_zero', 3000),
            environment.get('lapse_rate', 6.5),
            environment.get('precipitable_water', 30),
            environment.get('lifted_index', -4),
            environment.get('k_index', 35),
        ])

        # Time of day features (UTC hour as cyclic)
        hour = environment.get('hour', 18)
        features.extend([
            np.sin(2 * np.pi * hour / 24),
            np.cos(2 * np.pi * hour / 24),
        ])

        # Month features (for seasonality)
        month = environment.get('month', 6)
        features.extend([
            np.sin(2 * np.pi * month / 12),
            np.cos(2 * np.pi * month / 12),
        ])

        return np.array(features)

    def forecast(self, radar_trend: List[Dict], environment: Dict) -> Dict:
        """
        Generate hail forecast for multiple time horizons.

        Args:
            radar_trend: List of recent radar observations
            environment: Environmental parameters

        Returns:
            Dict with forecasts for each time horizon
        """
        features = self.extract_features(radar_trend, environment)

        if self.is_fitted and self.scaler is not None:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
        else:
            features_scaled = features.reshape(1, -1)

        results = {}

        for horizon in ['15min', '30min', '60min', '120min']:
            if self.is_fitted and self.models[horizon]['prob'] is not None:
                prob = self.models[horizon]['prob'].predict_proba(features_scaled)[0, 1]
                size = self.models[horizon]['size'].predict(features_scaled)[0]
            else:
                # Fallback to rule-based estimation
                prob, size = self._rule_based_forecast(radar_trend, environment, horizon)

            results[horizon] = {
                'hail_probability': round(prob * 100, 1),
                'estimated_size': round(max(0, size), 2),
                'confidence': self._calculate_confidence(radar_trend, environment, horizon)
            }

        return results

    def _rule_based_forecast(self, radar_trend: List[Dict], environment: Dict,
                             horizon: str) -> Tuple[float, float]:
        """
        Rule-based forecast when ML model not available.
        """
        # Base probability from current reflectivity
        if radar_trend:
            max_refl = radar_trend[-1].get('max_reflectivity', 40)
        else:
            max_refl = 40

        if max_refl >= 65:
            base_prob = 0.9
        elif max_refl >= 60:
            base_prob = 0.7
        elif max_refl >= 55:
            base_prob = 0.5
        elif max_refl >= 50:
            base_prob = 0.3
        else:
            base_prob = 0.1

        # Adjust for environment
        cape = environment.get('cape', 1500)
        if cape >= 3000:
            base_prob = min(base_prob + 0.2, 1.0)
        elif cape >= 2000:
            base_prob = min(base_prob + 0.1, 1.0)

        # Decay with forecast horizon
        horizon_decay = {'15min': 1.0, '30min': 0.9, '60min': 0.75, '120min': 0.5}
        prob = base_prob * horizon_decay.get(horizon, 0.5)

        # Size estimation
        if max_refl >= 65:
            size = 2.0
        elif max_refl >= 60:
            size = 1.5
        elif max_refl >= 55:
            size = 1.0
        else:
            size = 0.5

        return prob, size

    def _calculate_confidence(self, radar_trend: List[Dict], environment: Dict,
                              horizon: str) -> float:
        """Calculate forecast confidence."""
        confidence = 70  # Base confidence

        # Higher confidence with more data
        if len(radar_trend) >= 6:
            confidence += 10
        elif len(radar_trend) >= 3:
            confidence += 5

        # Lower confidence for longer horizons
        horizon_penalty = {'15min': 0, '30min': 5, '60min': 15, '120min': 25}
        confidence -= horizon_penalty.get(horizon, 25)

        # Higher confidence in well-understood environments
        cape = environment.get('cape', 1500)
        if 1500 <= cape <= 4000:
            confidence += 5

        return min(max(confidence, 30), 95)

    def fit(self, X: np.ndarray, y_dict: Dict):
        """
        Train models for all time horizons.

        Args:
            X: Feature matrix
            y_dict: Dict of labels for each horizon
        """
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        for horizon in ['15min', '30min', '60min', '120min']:
            if horizon not in y_dict:
                continue

            y_prob = y_dict[horizon]['prob']
            y_size = y_dict[horizon]['size']

            # Probability classifier
            self.models[horizon]['prob'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            self.models[horizon]['prob'].fit(X_scaled, y_prob)

            # Size regressor
            self.models[horizon]['size'] = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                random_state=42
            )
            self.models[horizon]['size'].fit(X_scaled, y_size)

        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        """Save model to disk."""
        save_path = path or self.model_path

        model_data = {
            'models': self.models,
            'scaler': self.scaler,
            'is_fitted': self.is_fitted,
            'version': '1.0.0'
        }

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[str] = None) -> bool:
        """Load model from disk."""
        load_path = path or self.model_path

        if not Path(load_path).exists():
            logger.warning(f"Model not found at {load_path}")
            return False

        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)

        self.models = model_data['models']
        self.scaler = model_data['scaler']
        self.is_fitted = model_data['is_fitted']

        logger.info(f"Model loaded from {load_path}")
        return True


def generate_synthetic_forecast_data(n_samples: int = 1500) -> Tuple[np.ndarray, Dict]:
    """
    Generate synthetic training data for forecaster.
    """
    np.random.seed(42)

    X = []
    y_dict = {
        '15min': {'prob': [], 'size': []},
        '30min': {'prob': [], 'size': []},
        '60min': {'prob': [], 'size': []},
        '120min': {'prob': [], 'size': []},
    }

    for _ in range(n_samples):
        # Generate storm parameters
        is_severe = np.random.random() < 0.35

        # Radar trend
        if is_severe:
            base_refl = np.random.uniform(55, 70)
            refl_trend = np.random.uniform(-2, 5)  # Intensifying
            cape = np.random.uniform(2000, 4500)
            shear = np.random.uniform(35, 60)
        else:
            base_refl = np.random.uniform(35, 55)
            refl_trend = np.random.uniform(-3, 2)
            cape = np.random.uniform(500, 2500)
            shear = np.random.uniform(15, 40)

        # Build feature vector
        features = [
            base_refl,
            base_refl - 5 + np.random.normal(0, 2),
            refl_trend,
            base_refl + abs(refl_trend),
            np.random.uniform(2, 8),
            np.random.uniform(20, 50),
            np.random.uniform(200, 320),
            np.random.uniform(20, 60),
            refl_trend * 0.8,
            cape,
            np.random.uniform(-100, 0),
            shear,
            shear * 0.4,
            np.random.uniform(2500, 4500),
            np.random.uniform(2000, 4000),
            np.random.uniform(5, 8),
            np.random.uniform(20, 50),
            np.random.uniform(-8, 2),
            np.random.uniform(25, 45),
            np.random.uniform(-1, 1),
            np.random.uniform(-1, 1),
            np.random.uniform(-1, 1),
            np.random.uniform(-1, 1),
        ]

        X.append(features)

        # Generate labels for each horizon
        base_hail_prob = 0.8 if is_severe and base_refl >= 55 else 0.2
        base_size = np.random.uniform(1.0, 2.5) if is_severe else np.random.uniform(0, 0.5)

        for horizon, decay in [('15min', 0.95), ('30min', 0.85), ('60min', 0.70), ('120min', 0.50)]:
            # Add randomness
            prob = base_hail_prob * decay + np.random.normal(0, 0.1)
            prob = max(0, min(1, prob))

            y_dict[horizon]['prob'].append(1 if prob > 0.5 else 0)
            y_dict[horizon]['size'].append(max(0, base_size * decay + np.random.normal(0, 0.2)))

    # Convert to arrays
    for horizon in y_dict:
        y_dict[horizon]['prob'] = np.array(y_dict[horizon]['prob'])
        y_dict[horizon]['size'] = np.array(y_dict[horizon]['size'])

    return np.array(X), y_dict


def train_storm_forecaster(save_path: Optional[str] = None) -> Dict:
    """
    Train the storm severity forecaster.
    """
    print("\n" + "=" * 60)
    print("TRAINING: Storm Severity Forecaster")
    print("=" * 60)

    # Generate data
    print("\n[1/4] Generating training data...")
    X, y_dict = generate_synthetic_forecast_data(n_samples=2000)
    print(f"  Generated {len(X)} samples")

    # Split
    print("\n[2/4] Splitting train/validation...")
    indices = np.arange(len(X))
    train_idx, val_idx = train_test_split(indices, test_size=0.2, random_state=42)

    X_train, X_val = X[train_idx], X[val_idx]

    y_train = {}
    y_val = {}
    for horizon in y_dict:
        y_train[horizon] = {
            'prob': y_dict[horizon]['prob'][train_idx],
            'size': y_dict[horizon]['size'][train_idx]
        }
        y_val[horizon] = {
            'prob': y_dict[horizon]['prob'][val_idx],
            'size': y_dict[horizon]['size'][val_idx]
        }

    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")

    # Train
    print("\n[3/4] Training models for each horizon...")
    forecaster = StormSeverityForecaster()
    forecaster.fit(X_train, y_train)
    print("  Models trained successfully")

    # Validate
    print("\n[4/4] Validating...")
    X_val_scaled = forecaster.scaler.transform(X_val)

    results_by_horizon = {}
    for horizon in ['15min', '30min', '60min', '120min']:
        prob_pred = forecaster.models[horizon]['prob'].predict(X_val_scaled)
        size_pred = forecaster.models[horizon]['size'].predict(X_val_scaled)

        acc = accuracy_score(y_val[horizon]['prob'], prob_pred)
        mae = mean_absolute_error(y_val[horizon]['size'], size_pred)

        results_by_horizon[horizon] = {'accuracy': acc, 'size_mae': mae}
        print(f"  {horizon}: Accuracy={acc*100:.1f}%, Size MAE={mae:.2f}\"")

    # Save
    if save_path is None:
        save_path = str(Path(__file__).parent / 'saved' / 'storm_forecaster.pkl')

    forecaster.save(save_path)
    print(f"\n  Model saved to: {save_path}")

    avg_accuracy = np.mean([r['accuracy'] for r in results_by_horizon.values()])

    return {
        'model': 'StormSeverityForecaster',
        'accuracy_by_horizon': results_by_horizon,
        'avg_accuracy': avg_accuracy,
        'model_path': save_path,
        'status': 'SUCCESS' if avg_accuracy >= 0.70 else 'BELOW_TARGET'
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    results = train_storm_forecaster()

    # Test inference
    print("\n" + "=" * 60)
    print("TESTING: Inference")
    print("=" * 60)

    forecaster = StormSeverityForecaster()
    forecaster.load()

    # Test data
    radar_trend = [
        {'max_reflectivity': 55, 'vil': 35, 'storm_speed': 35, 'storm_direction': 260},
        {'max_reflectivity': 58, 'vil': 40, 'storm_speed': 38, 'storm_direction': 265},
        {'max_reflectivity': 62, 'vil': 48, 'storm_speed': 40, 'storm_direction': 270},
    ]

    environment = {
        'cape': 2500,
        'cin': -30,
        'shear_0_6km': 45,
        'shear_0_1km': 20,
        'freezing_level': 3200,
        'wet_bulb_zero': 2800,
        'lapse_rate': 7.2,
        'precipitable_water': 35,
        'lifted_index': -5,
        'k_index': 38,
        'hour': 20,
        'month': 5,
    }

    forecast = forecaster.forecast(radar_trend, environment)

    print("\nStorm Forecast:")
    for horizon, data in forecast.items():
        print(f"  {horizon}: {data['hail_probability']}% prob, {data['estimated_size']}\" size, {data['confidence']}% conf")
