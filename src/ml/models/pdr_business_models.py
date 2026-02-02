"""
Models 7-10: PDR Business Intelligence Models

Model 7: Opportunity Scorer - ML-based scoring of hail events
Model 8: Claim Rate Predictor - Predict insurance claim rates
Model 9: Damage Prediction Model - Predict damage from storm params
Model 10: Parking Lot Vehicle Counter - Estimate vehicles from area
"""

import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pickle
import logging

logger = logging.getLogger('PDRBusinessModels')

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ============================================================================
# Model 7: ML Opportunity Scorer
# ============================================================================

class MLOpportunityScorer:
    """
    Machine learning based PDR opportunity scoring.

    More sophisticated than rule-based scoring, learns from
    historical event outcomes.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'ml_opportunity_scorer.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, event: Dict) -> np.ndarray:
        """Extract features from hail event."""
        features = [
            event.get('max_hail_size_inches', 1.0),
            event.get('duration_minutes', 30),
            event.get('affected_area_km2', 50),
            event.get('event_age_days', 7),
            event.get('population_density', 500),
            event.get('vehicle_density', 200),
            event.get('median_income', 50000),
            event.get('num_dealerships', 5),
            event.get('competition_score', 0.5),
            event.get('radar_confidence', 0.85),
            1 if event.get('state_province') in ['TX', 'OK', 'KS', 'CO', 'NE'] else 0,
            event.get('month', 6),
        ]
        return np.array(features)

    def score_event(self, event: Dict) -> Dict:
        """Score a hail event for PDR opportunity."""
        features = self.extract_features(event)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            score = self.model.predict(features_scaled)[0]
            score = max(0, min(100, score))
        else:
            # Fallback
            score = 50 + event.get('max_hail_size_inches', 1) * 20

        if score >= 80:
            priority = 'critical'
        elif score >= 60:
            priority = 'high'
        elif score >= 40:
            priority = 'medium'
        else:
            priority = 'low'

        return {
            'score': round(score, 1),
            'priority': priority,
            'confidence': round(self._calculate_confidence(event), 1)
        }

    def _calculate_confidence(self, event: Dict) -> float:
        """Calculate confidence in score."""
        conf = 70
        if event.get('radar_confidence', 0) > 0.9:
            conf += 15
        if event.get('affected_area_km2', 0) > 50:
            conf += 10
        return min(conf, 95)

    def fit(self, X: np.ndarray, y: np.ndarray):
        """Train the model."""
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler, 'is_fitted': True}, f)

    def load(self, path: Optional[str] = None) -> bool:
        load_path = path or self.model_path
        if not Path(load_path).exists():
            return False
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.scaler = data['scaler']
        self.is_fitted = data['is_fitted']
        return True


# ============================================================================
# Model 8: Claim Rate Predictor
# ============================================================================

class ClaimRatePredictor:
    """
    Predicts insurance claim rates for hail events.

    Factors:
    - Region (claim culture varies)
    - Damage severity
    - Income levels
    - Insurance penetration
    """

    # Base claim rates by region
    BASE_RATES = {
        'US': 0.45,
        'CA': 0.50,
        'MX': 0.25,
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'claim_rate_predictor.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, event: Dict) -> np.ndarray:
        """Extract features for claim rate prediction."""
        features = [
            event.get('max_hail_size_inches', 1.0),
            event.get('median_income', 50000) / 100000,  # Normalize
            event.get('insurance_penetration', 0.85),
            event.get('population_density', 500) / 1000,
            event.get('event_age_days', 7) / 90,  # Normalize to window
            1 if event.get('country') == 'US' else 0,
            1 if event.get('country') == 'CA' else 0,
            event.get('prior_claims_in_area', 0) / 100,
            event.get('deductible_avg', 500) / 1000,
        ]
        return np.array(features)

    def predict_claim_rate(self, event: Dict) -> Dict:
        """Predict claim rate for event."""
        features = self.extract_features(event)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            rate = self.model.predict(features_scaled)[0]
            rate = max(0.05, min(0.95, rate))
        else:
            # Fallback to base rates
            country = event.get('country', 'US')
            rate = self.BASE_RATES.get(country, 0.40)

            # Adjust for severity
            size = event.get('max_hail_size_inches', 1.0)
            if size >= 2.0:
                rate += 0.15
            elif size >= 1.5:
                rate += 0.10

        return {
            'predicted_claim_rate': round(rate, 3),
            'percentage': round(rate * 100, 1),
            'unclaimed_rate': round(1 - rate, 3),
            'confidence': 75 if not self.is_fitted else 85
        }

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        self.model.fit(X_scaled, y)
        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler, 'is_fitted': True}, f)

    def load(self, path: Optional[str] = None) -> bool:
        load_path = path or self.model_path
        if not Path(load_path).exists():
            return False
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.scaler = data['scaler']
        self.is_fitted = data['is_fitted']
        return True


# ============================================================================
# Model 9: Damage Prediction Model
# ============================================================================

class DamagePredictionModel:
    """
    Predicts vehicle damage from storm parameters.

    Outputs:
    - Damage probability by severity
    - Estimated dents per vehicle
    - Repair cost distribution
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'damage_prediction.pkl'
        )
        self.prob_model = None
        self.dent_model = None
        self.cost_model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, storm: Dict) -> np.ndarray:
        """Extract storm features."""
        features = [
            storm.get('max_hail_size_inches', 1.0),
            storm.get('min_hail_size_inches', 0.5),
            storm.get('duration_minutes', 20),
            storm.get('storm_speed_mph', 30),
            storm.get('wind_speed_mph', 20),
            storm.get('coverage_percentage', 50) / 100,
            storm.get('intensity_score', 0.5),
        ]
        return np.array(features)

    def predict_damage(self, storm: Dict) -> Dict:
        """Predict damage from storm."""
        features = self.extract_features(storm)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            damage_prob = self.prob_model.predict(features_scaled)[0]
            avg_dents = max(0, self.dent_model.predict(features_scaled)[0])
            avg_cost = max(0, self.cost_model.predict(features_scaled)[0])
        else:
            # Fallback
            size = storm.get('max_hail_size_inches', 1.0)
            damage_prob = min(0.95, 0.2 + size * 0.3)
            avg_dents = max(0, (size - 0.5) * 50)
            avg_cost = avg_dents * 25

        # Severity distribution
        if damage_prob >= 0.7:
            severity_dist = {'none': 0.1, 'minor': 0.15, 'moderate': 0.35, 'severe': 0.40}
        elif damage_prob >= 0.5:
            severity_dist = {'none': 0.2, 'minor': 0.30, 'moderate': 0.35, 'severe': 0.15}
        elif damage_prob >= 0.3:
            severity_dist = {'none': 0.4, 'minor': 0.35, 'moderate': 0.20, 'severe': 0.05}
        else:
            severity_dist = {'none': 0.7, 'minor': 0.20, 'moderate': 0.08, 'severe': 0.02}

        return {
            'damage_probability': round(damage_prob, 3),
            'avg_dents_per_vehicle': round(avg_dents, 1),
            'avg_repair_cost': round(avg_cost, 2),
            'severity_distribution': severity_dist,
            'confidence': 80 if self.is_fitted else 65
        }

    def fit(self, X: np.ndarray, y_prob: np.ndarray, y_dents: np.ndarray, y_cost: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.prob_model = Ridge(alpha=1.0)
        self.prob_model.fit(X_scaled, y_prob)

        self.dent_model = GradientBoostingRegressor(n_estimators=80, max_depth=4, random_state=42)
        self.dent_model.fit(X_scaled, y_dents)

        self.cost_model = GradientBoostingRegressor(n_estimators=80, max_depth=4, random_state=42)
        self.cost_model.fit(X_scaled, y_cost)

        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({
                'prob_model': self.prob_model,
                'dent_model': self.dent_model,
                'cost_model': self.cost_model,
                'scaler': self.scaler,
                'is_fitted': True
            }, f)

    def load(self, path: Optional[str] = None) -> bool:
        load_path = path or self.model_path
        if not Path(load_path).exists():
            return False
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        self.prob_model = data['prob_model']
        self.dent_model = data['dent_model']
        self.cost_model = data['cost_model']
        self.scaler = data['scaler']
        self.is_fitted = data['is_fitted']
        return True


# ============================================================================
# Model 10: Parking Lot Vehicle Counter
# ============================================================================

class ParkingLotVehicleCounter:
    """
    Estimates vehicle counts from area characteristics.

    Uses:
    - Land use data
    - Population density
    - Business density
    - Time of day patterns
    """

    # Vehicle density by land use type (vehicles per km²)
    DENSITY_BY_TYPE = {
        'residential': 300,
        'commercial': 800,
        'industrial': 200,
        'mixed': 500,
        'rural': 50,
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'vehicle_counter.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, area: Dict) -> np.ndarray:
        """Extract area features."""
        features = [
            area.get('area_km2', 10),
            area.get('population_density', 500),
            area.get('business_count', 50),
            area.get('parking_lot_count', 10),
            area.get('dealership_count', 2),
            1 if area.get('land_use') == 'commercial' else 0,
            1 if area.get('land_use') == 'residential' else 0,
            area.get('hour_of_day', 14) / 24,
            1 if area.get('is_weekend', False) else 0,
        ]
        return np.array(features)

    def estimate_vehicles(self, area: Dict) -> Dict:
        """Estimate vehicles in affected area."""
        features = self.extract_features(area)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            total_vehicles = max(0, self.model.predict(features_scaled)[0])
        else:
            # Fallback
            land_use = area.get('land_use', 'mixed')
            base_density = self.DENSITY_BY_TYPE.get(land_use, 400)
            area_km2 = area.get('area_km2', 10)
            total_vehicles = area_km2 * base_density

            # Time adjustment
            hour = area.get('hour_of_day', 14)
            if 8 <= hour <= 18:
                total_vehicles *= 1.2
            else:
                total_vehicles *= 0.6

        # Outdoor percentage (exposed to hail)
        outdoor_pct = 0.35 if area.get('land_use') in ['commercial', 'mixed'] else 0.25

        return {
            'total_vehicles': int(total_vehicles),
            'outdoor_vehicles': int(total_vehicles * outdoor_pct),
            'outdoor_percentage': round(outdoor_pct * 100, 1),
            'by_category': {
                'residential': int(total_vehicles * 0.4),
                'commercial_parking': int(total_vehicles * 0.3),
                'dealership_inventory': int(area.get('dealership_count', 2) * 150),
                'other': int(total_vehicles * 0.2),
            },
            'confidence': 75 if self.is_fitted else 60
        }

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
        self.model.fit(X_scaled, y)
        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({'model': self.model, 'scaler': self.scaler, 'is_fitted': True}, f)

    def load(self, path: Optional[str] = None) -> bool:
        load_path = path or self.model_path
        if not Path(load_path).exists():
            return False
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        self.model = data['model']
        self.scaler = data['scaler']
        self.is_fitted = data['is_fitted']
        return True


# ============================================================================
# Training Functions
# ============================================================================

def generate_opportunity_data(n=2000):
    np.random.seed(42)
    X, y = [], []
    for _ in range(n):
        size = np.random.uniform(0.5, 3.0)
        duration = np.random.uniform(10, 90)
        area = np.random.uniform(20, 300)
        age = np.random.uniform(0, 60)
        pop_density = np.random.uniform(100, 2000)
        veh_density = pop_density * 0.4
        income = np.random.uniform(30000, 100000)
        dealers = np.random.randint(1, 20)
        competition = np.random.uniform(0.2, 0.9)
        confidence = np.random.uniform(0.6, 1.0)
        is_hail_alley = np.random.choice([0, 1])
        month = np.random.randint(1, 13)

        X.append([size, duration, area, age, pop_density, veh_density, income, dealers, competition, confidence, is_hail_alley, month])

        # Score formula
        score = 20 + size * 25 + (duration/90)*15 + (area/300)*10 - (age/60)*15 + (income/100000)*10 - competition*10
        score = max(0, min(100, score + np.random.normal(0, 5)))
        y.append(score)

    return np.array(X), np.array(y)


def generate_claim_rate_data(n=1500):
    np.random.seed(43)
    X, y = [], []
    for _ in range(n):
        size = np.random.uniform(0.5, 3.0)
        income = np.random.uniform(30000, 120000) / 100000
        insurance_pen = np.random.uniform(0.6, 0.95)
        pop_density = np.random.uniform(100, 2000) / 1000
        age = np.random.uniform(0, 90) / 90
        is_us = np.random.choice([0, 1], p=[0.3, 0.7])
        is_ca = 1 if not is_us and np.random.random() < 0.5 else 0
        prior_claims = np.random.uniform(0, 500) / 100
        deductible = np.random.uniform(250, 1000) / 1000

        X.append([size, income, insurance_pen, pop_density, age, is_us, is_ca, prior_claims, deductible])

        # Claim rate
        base = 0.35 if is_us else (0.45 if is_ca else 0.20)
        rate = base + size * 0.1 + income * 0.1 + insurance_pen * 0.15 - deductible * 0.1
        rate = max(0.1, min(0.9, rate + np.random.normal(0, 0.05)))
        y.append(rate)

    return np.array(X), np.array(y)


def generate_damage_data(n=1500):
    np.random.seed(44)
    X, y_prob, y_dents, y_cost = [], [], [], []
    for _ in range(n):
        max_size = np.random.uniform(0.5, 4.0)
        min_size = max_size * np.random.uniform(0.3, 0.8)
        duration = np.random.uniform(5, 60)
        storm_speed = np.random.uniform(15, 60)
        wind = np.random.uniform(10, 50)
        coverage = np.random.uniform(0.2, 1.0)
        intensity = np.random.uniform(0.3, 1.0)

        X.append([max_size, min_size, duration, storm_speed, wind, coverage, intensity])

        prob = min(0.95, 0.1 + max_size * 0.2 + coverage * 0.2 + intensity * 0.1)
        dents = max(0, (max_size - 0.5) * 40 + duration * 0.5 + np.random.normal(0, 10))
        cost = dents * np.random.uniform(20, 35)

        y_prob.append(prob)
        y_dents.append(dents)
        y_cost.append(cost)

    return np.array(X), np.array(y_prob), np.array(y_dents), np.array(y_cost)


def generate_vehicle_count_data(n=1500):
    np.random.seed(45)
    X, y = [], []
    for _ in range(n):
        area = np.random.uniform(1, 100)
        pop_density = np.random.uniform(50, 3000)
        businesses = np.random.uniform(0, 500)
        parking_lots = np.random.uniform(0, 50)
        dealerships = np.random.uniform(0, 10)
        is_commercial = np.random.choice([0, 1])
        is_residential = 1 - is_commercial if np.random.random() < 0.7 else 0
        hour = np.random.uniform(0, 24) / 24
        is_weekend = np.random.choice([0, 1], p=[0.7, 0.3])

        X.append([area, pop_density, businesses, parking_lots, dealerships, is_commercial, is_residential, hour, is_weekend])

        base_vehicles = area * (500 if is_commercial else 300)
        vehicles = base_vehicles + businesses * 5 + dealerships * 150 + pop_density * area * 0.1
        vehicles *= (1.2 if 0.3 < hour < 0.75 else 0.7)
        vehicles = max(0, vehicles + np.random.normal(0, vehicles * 0.1))
        y.append(vehicles)

    return np.array(X), np.array(y)


def train_pdr_business_models():
    """Train all PDR business intelligence models."""
    results = {}

    # Model 7: Opportunity Scorer
    print("\n" + "=" * 60)
    print("TRAINING: Model 7 - ML Opportunity Scorer")
    print("=" * 60)
    X, y = generate_opportunity_data(2000)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    scorer = MLOpportunityScorer()
    scorer.fit(X_train, y_train)

    y_pred = scorer.model.predict(scorer.scaler.transform(X_val))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)

    print(f"  MAE: {mae:.2f} points")
    print(f"  R²: {r2:.3f}")
    scorer.save()
    results['opportunity_scorer'] = {'mae': mae, 'r2': r2, 'status': 'SUCCESS' if r2 > 0.7 else 'BELOW_TARGET'}

    # Model 8: Claim Rate Predictor
    print("\n" + "=" * 60)
    print("TRAINING: Model 8 - Claim Rate Predictor")
    print("=" * 60)
    X, y = generate_claim_rate_data(1500)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    predictor = ClaimRatePredictor()
    predictor.fit(X_train, y_train)

    y_pred = predictor.model.predict(predictor.scaler.transform(X_val))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)

    print(f"  MAE: {mae:.3f}")
    print(f"  R²: {r2:.3f}")
    predictor.save()
    results['claim_rate_predictor'] = {'mae': mae, 'r2': r2, 'status': 'SUCCESS' if r2 > 0.6 else 'BELOW_TARGET'}

    # Model 9: Damage Prediction
    print("\n" + "=" * 60)
    print("TRAINING: Model 9 - Damage Prediction Model")
    print("=" * 60)
    X, y_prob, y_dents, y_cost = generate_damage_data(1500)
    X_train, X_val, yp_train, yp_val, yd_train, yd_val, yc_train, yc_val = train_test_split(
        X, y_prob, y_dents, y_cost, test_size=0.2, random_state=42
    )

    damage_model = DamagePredictionModel()
    damage_model.fit(X_train, yp_train, yd_train, yc_train)

    X_val_scaled = damage_model.scaler.transform(X_val)
    prob_mae = mean_absolute_error(yp_val, damage_model.prob_model.predict(X_val_scaled))
    dent_mae = mean_absolute_error(yd_val, damage_model.dent_model.predict(X_val_scaled))

    print(f"  Probability MAE: {prob_mae:.3f}")
    print(f"  Dent Count MAE: {dent_mae:.1f}")
    damage_model.save()
    results['damage_prediction'] = {'prob_mae': prob_mae, 'dent_mae': dent_mae, 'status': 'SUCCESS'}

    # Model 10: Vehicle Counter
    print("\n" + "=" * 60)
    print("TRAINING: Model 10 - Parking Lot Vehicle Counter")
    print("=" * 60)
    X, y = generate_vehicle_count_data(1500)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    counter = ParkingLotVehicleCounter()
    counter.fit(X_train, y_train)

    y_pred = counter.model.predict(counter.scaler.transform(X_val))
    mae = mean_absolute_error(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)

    print(f"  MAE: {mae:.0f} vehicles")
    print(f"  R²: {r2:.3f}")
    counter.save()
    results['vehicle_counter'] = {'mae': mae, 'r2': r2, 'status': 'SUCCESS' if r2 > 0.8 else 'BELOW_TARGET'}

    print("\n" + "=" * 60)
    print("PDR BUSINESS MODELS TRAINING COMPLETE")
    print("=" * 60)

    return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    results = train_pdr_business_models()

    print("\nSummary:")
    for model, metrics in results.items():
        print(f"  {model}: {metrics['status']}")
