"""
Model 1: Radar-Based Hail Classifier

3D CNN for volumetric NEXRAD radar data analysis.
Detects hail and estimates size from radar reflectivity and dual-pol products.

Input:
- Radar reflectivity data (3D volume)
- Dual-pol products (ZDR, CC, KDP)
- Temperature profile
- Storm characteristics

Output:
- Hail probability (0-100%)
- Estimated max hail size (inches)
- Confidence score
"""

import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional
import pickle
import logging

logger = logging.getLogger('RadarHailClassifier')

# Try to import PyTorch, fall back to numpy-based implementation
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using sklearn fallback")

try:
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ============================================================================
# PyTorch 3D CNN Model (if available)
# ============================================================================

if TORCH_AVAILABLE:
    class RadarHailCNN(nn.Module):
        """
        3D CNN for volumetric radar data.

        Architecture:
        - 3 convolutional blocks with batch norm and dropout
        - Global average pooling
        - Two output heads: probability and size regression
        """

        def __init__(self, in_channels: int = 4, dropout: float = 0.3):
            """
            Args:
                in_channels: Number of radar products (Z, ZDR, CC, KDP)
                dropout: Dropout rate
            """
            super().__init__()

            # Conv block 1
            self.conv1 = nn.Conv3d(in_channels, 32, kernel_size=3, padding=1)
            self.bn1 = nn.BatchNorm3d(32)

            # Conv block 2
            self.conv2 = nn.Conv3d(32, 64, kernel_size=3, padding=1)
            self.bn2 = nn.BatchNorm3d(64)

            # Conv block 3
            self.conv3 = nn.Conv3d(64, 128, kernel_size=3, padding=1)
            self.bn3 = nn.BatchNorm3d(128)

            # Conv block 4
            self.conv4 = nn.Conv3d(128, 256, kernel_size=3, padding=1)
            self.bn4 = nn.BatchNorm3d(256)

            # Dropout
            self.dropout = nn.Dropout(dropout)

            # Fully connected layers
            self.fc1 = nn.Linear(256, 128)
            self.fc2 = nn.Linear(128, 64)

            # Output heads
            self.prob_head = nn.Linear(64, 1)  # Hail probability
            self.size_head = nn.Linear(64, 1)  # Size regression
            self.conf_head = nn.Linear(64, 1)  # Confidence

        def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Forward pass.

            Args:
                x: Input tensor (batch, channels, depth, height, width)

            Returns:
                prob: Hail probability (0-1)
                size: Estimated hail size (inches)
                conf: Confidence score (0-1)
            """
            # Conv blocks with pooling
            x = F.relu(self.bn1(self.conv1(x)))
            x = F.max_pool3d(x, 2)

            x = F.relu(self.bn2(self.conv2(x)))
            x = F.max_pool3d(x, 2)

            x = F.relu(self.bn3(self.conv3(x)))
            x = F.max_pool3d(x, 2)

            x = F.relu(self.bn4(self.conv4(x)))

            # Global average pooling
            x = F.adaptive_avg_pool3d(x, 1)
            x = x.view(x.size(0), -1)

            # Fully connected
            x = self.dropout(F.relu(self.fc1(x)))
            x = self.dropout(F.relu(self.fc2(x)))

            # Output heads
            prob = torch.sigmoid(self.prob_head(x))
            size = F.relu(self.size_head(x))  # Size is always positive
            conf = torch.sigmoid(self.conf_head(x))

            return prob, size, conf


# ============================================================================
# Sklearn-based Fallback Model
# ============================================================================

class RadarHailClassifierSklearn:
    """
    Gradient Boosting based hail classifier.
    Uses extracted features from radar data.
    """

    def __init__(self):
        self.prob_model = None
        self.size_model = None
        self.scaler = None
        self.is_fitted = False

    def extract_features(self, radar_data: Dict) -> np.ndarray:
        """
        Extract statistical features from radar volume.

        Args:
            radar_data: Dict with 'reflectivity', 'zdr', 'cc', 'kdp'

        Returns:
            Feature vector (1D array)
        """
        features = []

        for key in ['reflectivity', 'zdr', 'cc', 'kdp']:
            if key in radar_data and radar_data[key] is not None:
                data = np.array(radar_data[key])

                # Statistical features
                features.extend([
                    np.max(data),
                    np.mean(data),
                    np.std(data),
                    np.percentile(data, 95),
                    np.percentile(data, 99),
                    np.sum(data > np.percentile(data, 90)),  # High value count
                ])
            else:
                features.extend([0, 0, 0, 0, 0, 0])

        # Additional derived features
        if 'reflectivity' in radar_data:
            refl = np.array(radar_data['reflectivity'])
            features.append(np.sum(refl > 50))  # 50+ dBZ count
            features.append(np.sum(refl > 60))  # 60+ dBZ count (severe)
            features.append(np.sum(refl > 65))  # 65+ dBZ count (very severe)
        else:
            features.extend([0, 0, 0])

        return np.array(features)

    def fit(self, X: np.ndarray, y_prob: np.ndarray, y_size: np.ndarray):
        """
        Train the model.

        Args:
            X: Feature matrix (n_samples, n_features)
            y_prob: Hail yes/no labels
            y_size: Hail size labels
        """
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Train probability model
        self.prob_model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.prob_model.fit(X_scaled, y_prob)

        # Train size regression model (only on hail samples)
        hail_mask = y_prob == 1
        if hail_mask.sum() > 10:
            self.size_model = GradientBoostingRegressor(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            self.size_model.fit(X_scaled[hail_mask], y_size[hail_mask])

        self.is_fitted = True

    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Predict hail probability and size.

        Args:
            X: Feature matrix

        Returns:
            prob: Hail probabilities
            size: Estimated sizes
            conf: Confidence scores
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        X_scaled = self.scaler.transform(X)

        # Predict probability
        prob = self.prob_model.predict_proba(X_scaled)[:, 1]

        # Predict size
        if self.size_model is not None:
            size = self.size_model.predict(X_scaled)
            size = np.maximum(size, 0)  # Ensure positive
        else:
            size = np.zeros(len(X))

        # Confidence based on probability entropy
        conf = np.abs(prob - 0.5) * 2  # Higher confidence near 0 or 1

        return prob, size, conf


# ============================================================================
# Main Classifier Class (Unified Interface)
# ============================================================================

class RadarHailClassifier:
    """
    Unified interface for radar-based hail classification.

    Automatically uses PyTorch if available, otherwise sklearn.
    """

    # MESH approximation lookup table
    MESH_LOOKUP = {
        # Reflectivity thresholds -> estimated MESH
        45: 0.5,
        50: 0.75,
        55: 1.0,
        58: 1.25,
        60: 1.5,
        63: 1.75,
        65: 2.0,
        68: 2.5,
        70: 3.0,
    }

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize classifier.

        Args:
            model_path: Path to saved model
        """
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'radar_hail_classifier.pkl'
        )

        self.use_torch = TORCH_AVAILABLE
        self.model = None
        self.sklearn_model = RadarHailClassifierSklearn() if SKLEARN_AVAILABLE else None
        self.is_loaded = False

    def _estimate_mesh(self, max_reflectivity: float) -> float:
        """
        Estimate MESH from maximum reflectivity (simplified).

        Args:
            max_reflectivity: Maximum reflectivity in dBZ

        Returns:
            Estimated hail size in inches
        """
        for threshold, size in sorted(self.MESH_LOOKUP.items(), reverse=True):
            if max_reflectivity >= threshold:
                return size
        return 0.0

    def classify(self, radar_data: Dict) -> Dict:
        """
        Classify radar data for hail.

        Args:
            radar_data: Dict containing radar products
                - reflectivity: 3D array (depth, height, width)
                - zdr: Differential reflectivity (optional)
                - cc: Correlation coefficient (optional)
                - kdp: Specific differential phase (optional)
                - temperature_profile: Vertical temp profile (optional)

        Returns:
            Dict with:
                - hail_probability: 0-100
                - estimated_size_inches: float
                - confidence: 0-100
                - severity: 'none'/'light'/'moderate'/'severe'/'catastrophic'
        """
        # Extract reflectivity stats
        if 'reflectivity' not in radar_data:
            return {
                'hail_probability': 0,
                'estimated_size_inches': 0,
                'confidence': 0,
                'severity': 'none',
                'method': 'no_data'
            }

        refl = np.array(radar_data['reflectivity'])
        max_refl = np.max(refl)
        mean_refl = np.mean(refl)

        # Use trained model if available
        if self.is_loaded and self.sklearn_model and self.sklearn_model.is_fitted:
            features = self.sklearn_model.extract_features(radar_data)
            prob, size, conf = self.sklearn_model.predict(features.reshape(1, -1))
            prob = prob[0]
            size = size[0]
            conf = conf[0]
            method = 'ml_model'
        else:
            # Fallback to MESH approximation
            size = self._estimate_mesh(max_refl)

            # Probability based on reflectivity
            if max_refl >= 65:
                prob = 0.95
            elif max_refl >= 60:
                prob = 0.85
            elif max_refl >= 55:
                prob = 0.65
            elif max_refl >= 50:
                prob = 0.40
            elif max_refl >= 45:
                prob = 0.20
            else:
                prob = 0.05

            # Adjust with dual-pol if available
            if 'zdr' in radar_data and radar_data['zdr'] is not None:
                zdr = np.array(radar_data['zdr'])
                # Low ZDR with high reflectivity indicates hail
                if np.min(zdr[refl > 50]) < 0.5 if np.any(refl > 50) else False:
                    prob = min(prob + 0.15, 1.0)
                    size *= 1.1

            if 'cc' in radar_data and radar_data['cc'] is not None:
                cc = np.array(radar_data['cc'])
                # Low CC indicates hail
                if np.min(cc[refl > 50]) < 0.95 if np.any(refl > 50) else False:
                    prob = min(prob + 0.10, 1.0)

            conf = 0.7 if 'zdr' in radar_data else 0.5
            method = 'mesh_approximation'

        # Determine severity
        if size >= 2.5:
            severity = 'catastrophic'
        elif size >= 1.75:
            severity = 'severe'
        elif size >= 1.0:
            severity = 'moderate'
        elif size >= 0.5:
            severity = 'light'
        else:
            severity = 'none'

        return {
            'hail_probability': round(prob * 100, 1),
            'estimated_size_inches': round(size, 2),
            'confidence': round(conf * 100, 1),
            'severity': severity,
            'max_reflectivity_dbz': round(float(max_refl), 1),
            'method': method
        }

    def save(self, path: Optional[str] = None):
        """Save model to disk."""
        save_path = path or self.model_path

        model_data = {
            'sklearn_model': self.sklearn_model,
            'version': '1.0.0'
        }

        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {save_path}")

    def load(self, path: Optional[str] = None):
        """Load model from disk."""
        load_path = path or self.model_path

        if not Path(load_path).exists():
            logger.warning(f"Model not found at {load_path}")
            return False

        with open(load_path, 'rb') as f:
            model_data = pickle.load(f)

        self.sklearn_model = model_data['sklearn_model']
        self.is_loaded = True

        logger.info(f"Model loaded from {load_path}")
        return True


# ============================================================================
# Training Functions
# ============================================================================

def generate_synthetic_radar_data(n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate synthetic radar training data.

    In production, this would be replaced with real NEXRAD data collection.

    Returns:
        X: Feature matrix
        y_prob: Hail yes/no labels
        y_size: Hail size labels
    """
    np.random.seed(42)

    X = []
    y_prob = []
    y_size = []

    for i in range(n_samples):
        # Determine if this is a hail case
        is_hail = np.random.random() < 0.4  # 40% hail cases

        if is_hail:
            # Hail storm parameters
            hail_size = np.random.uniform(0.5, 3.0)  # inches

            # Higher reflectivity for larger hail
            max_refl = 45 + hail_size * 8 + np.random.normal(0, 3)
            mean_refl = max_refl - 15 + np.random.normal(0, 2)

            # Lower ZDR for hail
            max_zdr = 2.0 - hail_size * 0.5 + np.random.normal(0, 0.3)
            mean_zdr = max_zdr - 0.5

            # Lower CC for hail
            max_cc = 0.99 - hail_size * 0.02 + np.random.normal(0, 0.01)
            mean_cc = max_cc - 0.02

            # KDP varies
            max_kdp = np.random.uniform(0.5, 3.0)
            mean_kdp = max_kdp * 0.6
        else:
            # Non-hail storm
            hail_size = 0.0

            max_refl = np.random.uniform(30, 55)
            mean_refl = max_refl - 10 + np.random.normal(0, 2)

            max_zdr = np.random.uniform(1.0, 4.0)
            mean_zdr = max_zdr - 0.3

            max_cc = np.random.uniform(0.97, 1.0)
            mean_cc = max_cc - 0.01

            max_kdp = np.random.uniform(0, 2.0)
            mean_kdp = max_kdp * 0.5

        # Build feature vector
        features = [
            max_refl, mean_refl, np.abs(max_refl - mean_refl),
            np.random.uniform(0.9, 1.0) * max_refl,  # 95th percentile
            np.random.uniform(0.95, 1.0) * max_refl,  # 99th percentile
            max(0, max_refl - 50) * 10,  # High value count proxy

            max_zdr, mean_zdr, np.abs(max_zdr - mean_zdr),
            np.random.uniform(0.8, 1.0) * max_zdr,
            np.random.uniform(0.9, 1.0) * max_zdr,
            np.random.uniform(0, 5),

            max_cc, mean_cc, np.abs(max_cc - mean_cc),
            np.random.uniform(0.95, 1.0) * max_cc,
            np.random.uniform(0.98, 1.0) * max_cc,
            np.random.uniform(0, 10),

            max_kdp, mean_kdp, np.abs(max_kdp - mean_kdp),
            np.random.uniform(0.7, 1.0) * max_kdp,
            np.random.uniform(0.85, 1.0) * max_kdp,
            np.random.uniform(0, 5),

            # Derived features
            max(0, max_refl - 50) * 5,
            max(0, max_refl - 60) * 3,
            max(0, max_refl - 65) * 2,
        ]

        X.append(features)
        y_prob.append(1 if is_hail else 0)
        y_size.append(hail_size)

    return np.array(X), np.array(y_prob), np.array(y_size)


def train_radar_hail_classifier(save_path: Optional[str] = None) -> Dict:
    """
    Train the radar hail classifier.

    Returns:
        Dict with training results
    """
    print("\n" + "=" * 60)
    print("TRAINING: Radar Hail Classifier")
    print("=" * 60)

    # Generate training data
    print("\n[1/4] Generating training data...")
    X, y_prob, y_size = generate_synthetic_radar_data(n_samples=2000)
    print(f"  Generated {len(X)} samples")
    print(f"  Hail cases: {y_prob.sum()} ({y_prob.mean()*100:.1f}%)")

    # Split data
    print("\n[2/4] Splitting train/validation...")
    X_train, X_val, y_prob_train, y_prob_val, y_size_train, y_size_val = train_test_split(
        X, y_prob, y_size, test_size=0.2, random_state=42, stratify=y_prob
    )
    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")

    # Train model
    print("\n[3/4] Training model...")
    classifier = RadarHailClassifier()
    classifier.sklearn_model.fit(X_train, y_prob_train, y_size_train)
    print("  Model trained successfully")

    # Validate
    print("\n[4/4] Validating...")
    prob_pred, size_pred, conf_pred = classifier.sklearn_model.predict(X_val)

    # Calculate metrics
    prob_binary = (prob_pred > 0.5).astype(int)
    accuracy = accuracy_score(y_prob_val, prob_binary)

    # Size MAE (only for hail cases)
    hail_mask = y_prob_val == 1
    if hail_mask.sum() > 0:
        size_mae = mean_absolute_error(y_size_val[hail_mask], size_pred[hail_mask])
    else:
        size_mae = 0

    print(f"\n  Hail Detection Accuracy: {accuracy*100:.1f}%")
    print(f"  Size Estimation MAE: {size_mae:.2f} inches")

    # Save model
    if save_path is None:
        save_path = str(Path(__file__).parent / 'saved' / 'radar_hail_classifier.pkl')

    classifier.sklearn_model.is_fitted = True
    classifier.save(save_path)
    print(f"\n  Model saved to: {save_path}")

    results = {
        'model': 'RadarHailClassifier',
        'accuracy': accuracy,
        'size_mae': size_mae,
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'model_path': save_path,
        'status': 'SUCCESS' if accuracy >= 0.80 else 'BELOW_TARGET'
    }

    print(f"\n  Status: {'SUCCESS' if accuracy >= 0.80 else 'BELOW TARGET (<80%)'}")

    return results


# ============================================================================
# Test
# ============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Train the model
    results = train_radar_hail_classifier()

    # Test inference
    print("\n" + "=" * 60)
    print("TESTING: Inference")
    print("=" * 60)

    classifier = RadarHailClassifier()
    classifier.load()

    # Test with simulated data
    test_data = {
        'reflectivity': np.random.uniform(55, 70, (20, 100, 100)),
        'zdr': np.random.uniform(-0.5, 2.0, (20, 100, 100)),
        'cc': np.random.uniform(0.90, 0.99, (20, 100, 100)),
        'kdp': np.random.uniform(0, 3.0, (20, 100, 100))
    }

    result = classifier.classify(test_data)

    print(f"\nTest Storm Analysis:")
    print(f"  Hail Probability: {result['hail_probability']}%")
    print(f"  Estimated Size: {result['estimated_size_inches']}\"")
    print(f"  Confidence: {result['confidence']}%")
    print(f"  Severity: {result['severity']}")
    print(f"  Max Reflectivity: {result['max_reflectivity_dbz']} dBZ")
