"""
Models 11-15: Advanced Intelligence Models

Model 11: Route Optimizer - Optimize PDR team routing
Model 12: Conversion Predictor - Predict customer conversion
Model 13: Dealership Inventory Estimator - Estimate lot inventory
Model 14: Sentiment Analyzer - Analyze social media sentiment
Model 15: Repair Time Estimator - Estimate repair duration
"""

import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import pickle
import logging
import re

logger = logging.getLogger('AdvancedModels')

try:
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ============================================================================
# Model 11: Route Optimizer
# ============================================================================

class RouteOptimizer:
    """
    Optimizes routing for PDR teams between hail events.

    Uses ML to predict:
    - Travel time between locations
    - Optimal visit order
    - Expected revenue per route
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'route_optimizer.pkl'
        )
        self.travel_model = None
        self.revenue_model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, route: Dict) -> np.ndarray:
        """Extract features from route."""
        features = [
            route.get('distance_km', 50),
            route.get('num_stops', 3),
            route.get('total_vehicles', 100),
            route.get('avg_damage_severity', 2),
            route.get('traffic_factor', 1.0),
            route.get('is_highway', 0),
            route.get('time_of_day', 12) / 24,
        ]
        return np.array(features)

    def optimize_route(self, locations: List[Dict]) -> Dict:
        """
        Optimize route through multiple locations.

        Simple greedy nearest-neighbor for now.
        """
        if not locations:
            return {'optimal_order': [], 'total_distance': 0, 'estimated_revenue': 0}

        # Start from first location
        unvisited = list(range(1, len(locations)))
        order = [0]
        total_distance = 0

        current = 0
        while unvisited:
            # Find nearest unvisited
            min_dist = float('inf')
            nearest = unvisited[0]

            for loc_idx in unvisited:
                dist = self._calculate_distance(
                    locations[current]['lat'], locations[current]['lon'],
                    locations[loc_idx]['lat'], locations[loc_idx]['lon']
                )
                if dist < min_dist:
                    min_dist = dist
                    nearest = loc_idx

            order.append(nearest)
            total_distance += min_dist
            unvisited.remove(nearest)
            current = nearest

        # Estimate revenue
        total_revenue = sum(loc.get('estimated_revenue', 1000) for loc in locations)

        return {
            'optimal_order': order,
            'location_sequence': [locations[i] for i in order],
            'total_distance_km': round(total_distance, 1),
            'estimated_travel_time_hours': round(total_distance / 60, 1),
            'estimated_revenue': total_revenue,
            'efficiency_score': round(total_revenue / max(total_distance, 1), 2)
        }

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Approximate distance in km."""
        lat_diff = abs(lat1 - lat2) * 111
        lon_diff = abs(lon1 - lon2) * 85  # Approximate at mid-latitudes
        return np.sqrt(lat_diff**2 + lon_diff**2)

    def fit(self, X: np.ndarray, y_time: np.ndarray, y_revenue: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.travel_model = GradientBoostingRegressor(n_estimators=80, max_depth=4, random_state=42)
        self.travel_model.fit(X_scaled, y_time)

        self.revenue_model = GradientBoostingRegressor(n_estimators=80, max_depth=4, random_state=42)
        self.revenue_model.fit(X_scaled, y_revenue)

        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        save_path = path or self.model_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump({
                'travel_model': self.travel_model,
                'revenue_model': self.revenue_model,
                'scaler': self.scaler,
                'is_fitted': True
            }, f)

    def load(self, path: Optional[str] = None) -> bool:
        load_path = path or self.model_path
        if not Path(load_path).exists():
            return False
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
        self.travel_model = data['travel_model']
        self.revenue_model = data['revenue_model']
        self.scaler = data['scaler']
        self.is_fitted = data['is_fitted']
        return True


# ============================================================================
# Model 12: Conversion Predictor
# ============================================================================

class ConversionPredictor:
    """
    Predicts customer conversion probability.

    Factors:
    - Lead source
    - Response time
    - Damage severity
    - Competition presence
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'conversion_predictor.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, lead: Dict) -> np.ndarray:
        """Extract lead features."""
        features = [
            lead.get('damage_severity', 2),
            lead.get('response_time_hours', 24),
            lead.get('quote_amount', 1000) / 5000,
            lead.get('competitor_quotes', 1),
            lead.get('income_bracket', 3),
            lead.get('insurance_claim', 1),
            lead.get('event_age_days', 7),
            1 if lead.get('source') == 'referral' else 0,
            1 if lead.get('source') == 'door_knock' else 0,
            1 if lead.get('source') == 'online' else 0,
        ]
        return np.array(features)

    def predict_conversion(self, lead: Dict) -> Dict:
        """Predict conversion probability."""
        features = self.extract_features(lead)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            prob = self.model.predict_proba(features_scaled)[0, 1]
        else:
            # Fallback
            severity = lead.get('damage_severity', 2)
            response = lead.get('response_time_hours', 24)
            prob = 0.4 + severity * 0.1 - response * 0.005

        prob = max(0.05, min(0.95, prob))

        return {
            'conversion_probability': round(prob, 3),
            'percentage': round(prob * 100, 1),
            'recommendation': self._get_recommendation(prob, lead),
            'priority': 'HIGH' if prob >= 0.6 else ('MEDIUM' if prob >= 0.3 else 'LOW')
        }

    def _get_recommendation(self, prob: float, lead: Dict) -> str:
        if prob >= 0.7:
            return "High conversion potential - prioritize follow-up"
        elif prob >= 0.5:
            return "Good potential - standard follow-up"
        elif prob >= 0.3:
            return "Moderate potential - may need incentive"
        else:
            return "Low potential - consider cost of pursuit"

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model = LogisticRegression(random_state=42, max_iter=1000)
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
# Model 13: Dealership Inventory Estimator
# ============================================================================

class DealershipInventoryEstimator:
    """
    Estimates vehicle inventory at dealerships.

    Uses dealership characteristics to predict lot size.
    """

    # Average inventory by dealership type
    BASE_INVENTORY = {
        'new_franchise': 200,
        'used_independent': 80,
        'luxury': 100,
        'commercial': 50,
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'inventory_estimator.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, dealership: Dict) -> np.ndarray:
        """Extract dealership features."""
        features = [
            dealership.get('lot_size_sqft', 50000) / 100000,
            dealership.get('num_employees', 20),
            dealership.get('annual_sales', 500),
            dealership.get('years_in_business', 10),
            1 if dealership.get('type') == 'new_franchise' else 0,
            1 if dealership.get('type') == 'used_independent' else 0,
            1 if dealership.get('is_luxury', False) else 0,
            dealership.get('num_brands', 1),
        ]
        return np.array(features)

    def estimate_inventory(self, dealership: Dict) -> Dict:
        """Estimate dealership inventory."""
        features = self.extract_features(dealership)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            inventory = max(10, self.model.predict(features_scaled)[0])
        else:
            dealer_type = dealership.get('type', 'new_franchise')
            inventory = self.BASE_INVENTORY.get(dealer_type, 100)
            inventory *= dealership.get('lot_size_sqft', 50000) / 50000

        # Breakdown
        new_pct = 0.6 if dealership.get('type') == 'new_franchise' else 0.2
        used_pct = 1 - new_pct

        return {
            'total_inventory': int(inventory),
            'new_vehicles': int(inventory * new_pct),
            'used_vehicles': int(inventory * used_pct),
            'estimated_value': int(inventory * 35000),
            'potential_damage_value': int(inventory * 1500),  # Avg repair cost
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
# Model 14: Sentiment Analyzer
# ============================================================================

class SentimentAnalyzer:
    """
    Analyzes sentiment in social media posts about hail/storms.

    Classifies posts as:
    - Positive/Negative/Neutral
    - Urgency level
    - Damage report vs general discussion
    """

    # Keyword patterns
    NEGATIVE_WORDS = ['damage', 'destroyed', 'totaled', 'ruined', 'devastated', 'crushed', 'smashed']
    POSITIVE_WORDS = ['survived', 'safe', 'lucky', 'minor', 'okay', 'fine', 'protected']
    URGENCY_WORDS = ['help', 'emergency', 'need', 'asap', 'urgent', 'now', 'immediately']
    DAMAGE_WORDS = ['dent', 'hail', 'damage', 'broken', 'cracked', 'windshield', 'roof', 'hood']

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'sentiment_analyzer.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, text: str) -> np.ndarray:
        """Extract text features."""
        text_lower = text.lower()
        words = re.findall(r'\w+', text_lower)

        features = [
            len(words),
            len([w for w in words if w in self.NEGATIVE_WORDS]),
            len([w for w in words if w in self.POSITIVE_WORDS]),
            len([w for w in words if w in self.URGENCY_WORDS]),
            len([w for w in words if w in self.DAMAGE_WORDS]),
            text.count('!'),
            text.count('?'),
            1 if any(w.isupper() and len(w) > 2 for w in text.split()) else 0,
            len([w for w in words if w.startswith('#')]),
            1 if '$' in text or 'insurance' in text_lower else 0,
        ]
        return np.array(features)

    def analyze(self, text: str) -> Dict:
        """Analyze sentiment of text."""
        features = self.extract_features(text)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            sentiment_pred = self.model.predict(features_scaled)[0]
            sentiment_probs = self.model.predict_proba(features_scaled)[0]
        else:
            # Rule-based fallback
            text_lower = text.lower()
            neg_count = sum(1 for w in self.NEGATIVE_WORDS if w in text_lower)
            pos_count = sum(1 for w in self.POSITIVE_WORDS if w in text_lower)

            if neg_count > pos_count:
                sentiment_pred = 0  # Negative
            elif pos_count > neg_count:
                sentiment_pred = 2  # Positive
            else:
                sentiment_pred = 1  # Neutral

            sentiment_probs = [0.33, 0.34, 0.33]

        sentiment_labels = ['negative', 'neutral', 'positive']
        sentiment = sentiment_labels[sentiment_pred]

        # Urgency detection
        urgency_count = sum(1 for w in self.URGENCY_WORDS if w in text.lower())
        urgency = 'high' if urgency_count >= 2 else ('medium' if urgency_count == 1 else 'low')

        # Is damage report?
        damage_count = sum(1 for w in self.DAMAGE_WORDS if w in text.lower())
        is_damage_report = damage_count >= 2

        return {
            'sentiment': sentiment,
            'sentiment_scores': {
                'negative': round(sentiment_probs[0], 3),
                'neutral': round(sentiment_probs[1], 3),
                'positive': round(sentiment_probs[2], 3),
            },
            'urgency': urgency,
            'is_damage_report': is_damage_report,
            'actionable': is_damage_report and sentiment == 'negative',
            'confidence': round(max(sentiment_probs) * 100, 1)
        }

    def fit(self, X: np.ndarray, y: np.ndarray):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
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
# Model 15: Repair Time Estimator
# ============================================================================

class RepairTimeEstimator:
    """
    Estimates repair time for hail damage.

    Factors:
    - Dent count
    - Panel locations
    - Damage severity
    - Vehicle type
    """

    # Base times per panel (hours)
    PANEL_TIMES = {
        'hood': 1.5,
        'roof': 2.0,
        'trunk': 1.0,
        'fender': 1.0,
        'door': 0.75,
        'quarter_panel': 1.5,
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'repair_time_estimator.pkl'
        )
        self.model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, job: Dict) -> np.ndarray:
        """Extract job features."""
        features = [
            job.get('dent_count', 50),
            job.get('num_panels', 4),
            job.get('severity_score', 2),
            job.get('avg_dent_size_mm', 15),
            1 if job.get('has_body_lines', True) else 0,
            1 if job.get('aluminum_panels', False) else 0,
            job.get('vehicle_age_years', 5),
            1 if job.get('vehicle_type') == 'truck' else 0,
            1 if job.get('vehicle_type') == 'suv' else 0,
        ]
        return np.array(features)

    def estimate_time(self, job: Dict) -> Dict:
        """Estimate repair time."""
        features = self.extract_features(job)

        if self.is_fitted:
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            hours = max(0.5, self.model.predict(features_scaled)[0])
        else:
            # Rule-based
            dents = job.get('dent_count', 50)
            panels = job.get('num_panels', 4)
            severity = job.get('severity_score', 2)

            # Base time: ~3 minutes per dent
            hours = dents * 0.05 + panels * 0.5 + severity * 0.5

            # Adjustments
            if job.get('aluminum_panels', False):
                hours *= 1.3
            if job.get('has_body_lines', True):
                hours *= 1.1

        # Breakdown
        labor_rate = 75  # per hour
        total_cost = hours * labor_rate

        return {
            'estimated_hours': round(hours, 1),
            'estimated_cost': round(total_cost, 2),
            'work_days': round(hours / 8, 1),
            'breakdown': {
                'panel_work': round(hours * 0.6, 1),
                'finishing': round(hours * 0.25, 1),
                'quality_check': round(hours * 0.15, 1),
            },
            'confidence': 80 if self.is_fitted else 65
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
# Training Functions
# ============================================================================

def generate_route_data(n=1000):
    np.random.seed(46)
    X, y_time, y_revenue = [], [], []
    for _ in range(n):
        dist = np.random.uniform(10, 200)
        stops = np.random.randint(1, 10)
        vehicles = np.random.uniform(10, 500)
        severity = np.random.uniform(1, 4)
        traffic = np.random.uniform(0.8, 1.5)
        highway = np.random.choice([0, 1])
        tod = np.random.uniform(0, 1)

        X.append([dist, stops, vehicles, severity, traffic, highway, tod])

        time = dist / (highway * 80 + (1-highway) * 40) * traffic + stops * 0.5
        revenue = vehicles * severity * 200 + np.random.normal(0, 500)

        y_time.append(time)
        y_revenue.append(max(0, revenue))

    return np.array(X), np.array(y_time), np.array(y_revenue)


def generate_conversion_data(n=1500):
    np.random.seed(47)
    X, y = [], []
    for _ in range(n):
        severity = np.random.randint(1, 5)
        response = np.random.uniform(1, 72)
        quote = np.random.uniform(200, 5000) / 5000
        competitors = np.random.randint(0, 5)
        income = np.random.randint(1, 6)
        insurance = np.random.choice([0, 1], p=[0.3, 0.7])
        age = np.random.uniform(1, 60)
        referral = np.random.choice([0, 1], p=[0.8, 0.2])
        door_knock = np.random.choice([0, 1], p=[0.7, 0.3])
        online = 1 if not referral and not door_knock else 0

        X.append([severity, response, quote, competitors, income, insurance, age, referral, door_knock, online])

        # Conversion probability
        prob = 0.3 + severity * 0.08 - response * 0.003 - competitors * 0.05 + insurance * 0.1 + referral * 0.15
        converted = 1 if np.random.random() < prob else 0
        y.append(converted)

    return np.array(X), np.array(y)


def generate_inventory_data(n=1000):
    np.random.seed(48)
    X, y = [], []
    for _ in range(n):
        lot_size = np.random.uniform(10000, 200000) / 100000
        employees = np.random.uniform(5, 100)
        sales = np.random.uniform(100, 2000)
        years = np.random.uniform(1, 50)
        is_new = np.random.choice([0, 1])
        is_used = 1 if not is_new and np.random.random() < 0.5 else 0
        luxury = np.random.choice([0, 1], p=[0.85, 0.15])
        brands = np.random.randint(1, 6)

        X.append([lot_size, employees, sales, years, is_new, is_used, luxury, brands])

        inventory = lot_size * 100000 / 250 + employees * 3 + sales * 0.2 + brands * 20
        if is_new:
            inventory *= 1.5
        if luxury:
            inventory *= 0.6
        inventory = max(20, inventory + np.random.normal(0, 20))
        y.append(inventory)

    return np.array(X), np.array(y)


def generate_sentiment_data(n=1500):
    np.random.seed(49)

    templates = {
        'negative': [
            "My car got destroyed by hail! Need help!",
            "Massive damage to my vehicle from the storm",
            "Totaled! The hail ruined everything",
            "So much damage, my car is crushed",
        ],
        'neutral': [
            "There was a hail storm today",
            "Anyone else see the hail?",
            "Hail season is here",
            "Weather report says hail possible",
        ],
        'positive': [
            "My car survived the hail storm!",
            "Lucky - only minor damage",
            "Garage saved my car from hail",
            "Safe and sound after the storm",
        ]
    }

    analyzer = SentimentAnalyzer()
    X, y = [], []

    for _ in range(n):
        sentiment_idx = np.random.choice([0, 1, 2], p=[0.4, 0.35, 0.25])
        sentiment = ['negative', 'neutral', 'positive'][sentiment_idx]

        text = np.random.choice(templates[sentiment])
        # Add some variation
        if np.random.random() < 0.3:
            text += " " + np.random.choice(["!!!", "?", "#hail", "$$$"])

        features = analyzer.extract_features(text)
        X.append(features)
        y.append(sentiment_idx)

    return np.array(X), np.array(y)


def generate_repair_time_data(n=1500):
    np.random.seed(50)
    X, y = [], []
    for _ in range(n):
        dents = np.random.uniform(5, 300)
        panels = np.random.randint(1, 9)
        severity = np.random.uniform(1, 4)
        dent_size = np.random.uniform(5, 40)
        body_lines = np.random.choice([0, 1], p=[0.3, 0.7])
        aluminum = np.random.choice([0, 1], p=[0.85, 0.15])
        age = np.random.uniform(0, 15)
        truck = np.random.choice([0, 1], p=[0.7, 0.3])
        suv = 1 if not truck and np.random.random() < 0.4 else 0

        X.append([dents, panels, severity, dent_size, body_lines, aluminum, age, truck, suv])

        # Time estimation
        time = dents * 0.04 + panels * 0.4 + severity * 0.3 + dent_size * 0.02
        if aluminum:
            time *= 1.25
        if body_lines:
            time *= 1.1
        time = max(0.5, time + np.random.normal(0, 0.5))
        y.append(time)

    return np.array(X), np.array(y)


def train_advanced_models():
    """Train all advanced intelligence models."""
    results = {}

    # Model 11: Route Optimizer
    print("\n" + "=" * 60)
    print("TRAINING: Model 11 - Route Optimizer")
    print("=" * 60)
    X, y_time, y_revenue = generate_route_data(1000)
    X_train, X_val, yt_train, yt_val, yr_train, yr_val = train_test_split(
        X, y_time, y_revenue, test_size=0.2, random_state=42
    )

    optimizer = RouteOptimizer()
    optimizer.fit(X_train, yt_train, yr_train)

    time_mae = mean_absolute_error(yt_val, optimizer.travel_model.predict(optimizer.scaler.transform(X_val)))
    print(f"  Travel Time MAE: {time_mae:.2f} hours")
    optimizer.save()
    results['route_optimizer'] = {'time_mae': time_mae, 'status': 'SUCCESS'}

    # Model 12: Conversion Predictor
    print("\n" + "=" * 60)
    print("TRAINING: Model 12 - Conversion Predictor")
    print("=" * 60)
    X, y = generate_conversion_data(1500)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    predictor = ConversionPredictor()
    predictor.fit(X_train, y_train)

    accuracy = accuracy_score(y_val, predictor.model.predict(predictor.scaler.transform(X_val)))
    print(f"  Accuracy: {accuracy*100:.1f}%")
    predictor.save()
    results['conversion_predictor'] = {'accuracy': accuracy, 'status': 'SUCCESS' if accuracy > 0.65 else 'BELOW_TARGET'}

    # Model 13: Inventory Estimator
    print("\n" + "=" * 60)
    print("TRAINING: Model 13 - Dealership Inventory Estimator")
    print("=" * 60)
    X, y = generate_inventory_data(1000)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    estimator = DealershipInventoryEstimator()
    estimator.fit(X_train, y_train)

    mae = mean_absolute_error(y_val, estimator.model.predict(estimator.scaler.transform(X_val)))
    r2 = r2_score(y_val, estimator.model.predict(estimator.scaler.transform(X_val)))
    print(f"  MAE: {mae:.1f} vehicles")
    print(f"  R²: {r2:.3f}")
    estimator.save()
    results['inventory_estimator'] = {'mae': mae, 'r2': r2, 'status': 'SUCCESS' if r2 > 0.7 else 'BELOW_TARGET'}

    # Model 14: Sentiment Analyzer
    print("\n" + "=" * 60)
    print("TRAINING: Model 14 - Sentiment Analyzer")
    print("=" * 60)
    X, y = generate_sentiment_data(1500)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    analyzer = SentimentAnalyzer()
    analyzer.fit(X_train, y_train)

    accuracy = accuracy_score(y_val, analyzer.model.predict(analyzer.scaler.transform(X_val)))
    print(f"  Accuracy: {accuracy*100:.1f}%")
    analyzer.save()
    results['sentiment_analyzer'] = {'accuracy': accuracy, 'status': 'SUCCESS' if accuracy > 0.70 else 'BELOW_TARGET'}

    # Model 15: Repair Time Estimator
    print("\n" + "=" * 60)
    print("TRAINING: Model 15 - Repair Time Estimator")
    print("=" * 60)
    X, y = generate_repair_time_data(1500)
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    time_estimator = RepairTimeEstimator()
    time_estimator.fit(X_train, y_train)

    mae = mean_absolute_error(y_val, time_estimator.model.predict(time_estimator.scaler.transform(X_val)))
    r2 = r2_score(y_val, time_estimator.model.predict(time_estimator.scaler.transform(X_val)))
    print(f"  MAE: {mae:.2f} hours")
    print(f"  R²: {r2:.3f}")
    time_estimator.save()
    results['repair_time_estimator'] = {'mae': mae, 'r2': r2, 'status': 'SUCCESS' if r2 > 0.8 else 'BELOW_TARGET'}

    print("\n" + "=" * 60)
    print("ADVANCED MODELS TRAINING COMPLETE")
    print("=" * 60)

    return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    results = train_advanced_models()

    print("\nSummary:")
    for model, metrics in results.items():
        print(f"  {model}: {metrics['status']}")
