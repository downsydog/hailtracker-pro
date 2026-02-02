"""
Model 6: Photo Authenticity Validator

Detects fake, AI-generated, or reposted photos.

Input: Photo + metadata
Output:
- Authentic probability
- Warnings
- Trust score
"""

import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pickle
import logging
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger('PhotoValidator')

try:
    from sklearn.ensemble import RandomForestClassifier, IsolationForest
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class PhotoAuthenticityValidator:
    """
    Validates authenticity of photos for hail damage verification.

    Checks for:
    1. Duplicate/reposted images (perceptual hashing)
    2. AI-generated content (statistical anomalies)
    3. EXIF metadata consistency
    4. Temporal plausibility
    """

    # Known suspicious patterns
    SUSPICIOUS_PATTERNS = {
        'too_perfect': 'Image appears artificially perfect',
        'metadata_mismatch': 'Metadata inconsistent with claimed date/location',
        'known_duplicate': 'Image matches known duplicate in database',
        'ai_artifacts': 'Patterns consistent with AI generation detected',
        'impossible_lighting': 'Lighting inconsistent with claimed time',
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or str(
            Path(__file__).parent / 'saved' / 'photo_validator.pkl'
        )

        self.authenticity_classifier = None
        self.anomaly_detector = None
        self.scaler = None
        self.hash_database = {}  # In production, would be persistent
        self.is_fitted = False

    def compute_image_hash(self, image_data: np.ndarray) -> str:
        """
        Compute perceptual hash of image.

        Simple implementation - in production would use imagehash library.
        """
        if image_data.ndim == 3:
            # Convert to grayscale
            gray = np.mean(image_data, axis=-1)
        else:
            gray = image_data

        # Resize to 8x8
        if gray.shape[0] > 8 and gray.shape[1] > 8:
            step_h = gray.shape[0] // 8
            step_w = gray.shape[1] // 8
            resized = gray[::step_h, ::step_w][:8, :8]
        else:
            resized = np.zeros((8, 8))
            resized[:min(8, gray.shape[0]), :min(8, gray.shape[1])] = gray[:8, :8]

        # Compute difference hash
        mean_val = np.mean(resized)
        hash_bits = (resized > mean_val).flatten()
        hash_bytes = np.packbits(hash_bits)

        return hashlib.md5(hash_bytes.tobytes()).hexdigest()[:16]

    def extract_features(self, image_data: np.ndarray, metadata: Optional[Dict] = None) -> np.ndarray:
        """
        Extract features for authenticity analysis.

        Args:
            image_data: Image array
            metadata: Optional EXIF/post metadata

        Returns:
            Feature vector
        """
        features = []

        if image_data.ndim == 1:
            return image_data

        if image_data.ndim == 2:
            image_data = np.stack([image_data] * 3, axis=-1)

        # Statistical features that detect AI artifacts
        for c in range(min(3, image_data.shape[-1])):
            channel = image_data[:, :, c].flatten()

            # Basic stats
            features.extend([
                np.mean(channel),
                np.std(channel),
                np.min(channel),
                np.max(channel),
            ])

            # Distribution features
            features.extend([
                np.percentile(channel, 1),
                np.percentile(channel, 99),
                np.median(channel),
            ])

            # Uniqueness (AI tends to have fewer unique values)
            unique_ratio = len(np.unique(channel)) / len(channel)
            features.append(unique_ratio)

        # Noise analysis (AI images have different noise patterns)
        gray = np.mean(image_data, axis=-1)

        if gray.shape[0] > 4 and gray.shape[1] > 4:
            # High-frequency noise
            noise = gray[:-1, :-1] - gray[1:, 1:]
            features.extend([
                np.mean(np.abs(noise)),
                np.std(noise),
                np.percentile(np.abs(noise), 95),
            ])

            # Local correlation (AI often has unnatural smoothness)
            if gray.shape[0] > 8 and gray.shape[1] > 8:
                correlations = []
                step = gray.shape[0] // 4
                for i in range(0, gray.shape[0] - step, step):
                    for j in range(0, gray.shape[1] - step, step):
                        patch = gray[i:i+step, j:j+step]
                        if patch.size > 1:
                            correlations.append(np.corrcoef(patch.flatten()[:-1], patch.flatten()[1:])[0, 1])

                correlations = [c for c in correlations if not np.isnan(c)]
                if correlations:
                    features.extend([
                        np.mean(correlations),
                        np.std(correlations),
                    ])
                else:
                    features.extend([0, 0])
            else:
                features.extend([0, 0])
        else:
            features.extend([0, 0, 0, 0, 0])

        # Histogram smoothness (AI often has unnaturally smooth histograms)
        hist, _ = np.histogram(gray.flatten(), bins=32, range=(0, 255))
        hist = hist / (hist.sum() + 1e-6)
        hist_diff = np.diff(hist)
        features.extend([
            np.mean(np.abs(hist_diff)),
            np.std(hist_diff),
            np.max(np.abs(hist_diff)),
        ])

        # Metadata features if available
        if metadata:
            # Has EXIF
            features.append(1 if metadata.get('has_exif', False) else 0)

            # Camera model present
            features.append(1 if metadata.get('camera_model') else 0)

            # GPS present
            features.append(1 if metadata.get('gps_lat') else 0)

            # Time consistency (photo taken within claimed timeframe)
            features.append(1 if metadata.get('time_consistent', True) else 0)
        else:
            features.extend([0, 0, 0, 1])

        return np.array(features)

    def validate(self, image_data: np.ndarray, metadata: Optional[Dict] = None,
                 claimed_date: Optional[datetime] = None,
                 claimed_location: Optional[Tuple[float, float]] = None) -> Dict:
        """
        Validate photo authenticity.

        Args:
            image_data: Image array
            metadata: EXIF/post metadata
            claimed_date: Claimed date of photo
            claimed_location: Claimed lat/lon

        Returns:
            Validation results
        """
        warnings = []
        trust_factors = []

        # Check for duplicates
        img_hash = self.compute_image_hash(image_data)
        if img_hash in self.hash_database:
            warnings.append(self.SUSPICIOUS_PATTERNS['known_duplicate'])
            trust_factors.append(0.3)
        else:
            trust_factors.append(1.0)

        # ML-based authenticity check
        features = self.extract_features(image_data, metadata)

        if self.is_fitted and self.scaler is not None:
            features_scaled = self.scaler.transform(features.reshape(1, -1))

            # Authenticity prediction
            auth_prob = self.authenticity_classifier.predict_proba(features_scaled)[0, 1]

            # Anomaly detection
            anomaly_score = self.anomaly_detector.decision_function(features_scaled)[0]
            is_anomaly = anomaly_score < 0

            if is_anomaly:
                warnings.append(self.SUSPICIOUS_PATTERNS['ai_artifacts'])
                trust_factors.append(0.5)
            else:
                trust_factors.append(1.0)
        else:
            auth_prob = 0.7
            trust_factors.append(0.8)

        # Metadata validation
        if metadata:
            if not metadata.get('has_exif', False):
                warnings.append('No EXIF data found')
                trust_factors.append(0.7)
            else:
                trust_factors.append(1.0)

            # Check time consistency
            if claimed_date and metadata.get('photo_date'):
                photo_date = metadata['photo_date']
                if abs((photo_date - claimed_date).days) > 3:
                    warnings.append(self.SUSPICIOUS_PATTERNS['metadata_mismatch'])
                    trust_factors.append(0.4)
        else:
            trust_factors.append(0.8)

        # Calculate final trust score
        trust_score = np.prod(trust_factors) * auth_prob * 100

        # Determine verdict
        if trust_score >= 70:
            verdict = 'LIKELY_AUTHENTIC'
        elif trust_score >= 40:
            verdict = 'UNCERTAIN'
        else:
            verdict = 'SUSPICIOUS'

        return {
            'authentic_probability': round(auth_prob * 100, 1),
            'trust_score': round(trust_score, 1),
            'verdict': verdict,
            'warnings': warnings,
            'image_hash': img_hash,
            'analysis': {
                'duplicate_check': 'PASS' if img_hash not in self.hash_database else 'FAIL',
                'anomaly_check': 'PASS' if len([w for w in warnings if 'artifact' in w.lower()]) == 0 else 'WARNING',
                'metadata_check': 'PASS' if not any('metadata' in w.lower() for w in warnings) else 'WARNING',
            }
        }

    def add_to_hash_database(self, image_data: np.ndarray, source: str = 'unknown'):
        """Add image hash to duplicate database."""
        img_hash = self.compute_image_hash(image_data)
        self.hash_database[img_hash] = {
            'added': datetime.now().isoformat(),
            'source': source
        }

    def fit(self, X: np.ndarray, y_authentic: np.ndarray):
        """Train the model."""
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Authenticity classifier
        self.authenticity_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.authenticity_classifier.fit(X_scaled, y_authentic)

        # Anomaly detector (trained on authentic samples)
        authentic_samples = X_scaled[y_authentic == 1]
        self.anomaly_detector = IsolationForest(
            n_estimators=100,
            contamination=0.1,
            random_state=42
        )
        self.anomaly_detector.fit(authentic_samples)

        self.is_fitted = True

    def save(self, path: Optional[str] = None):
        """Save model."""
        save_path = path or self.model_path

        model_data = {
            'authenticity_classifier': self.authenticity_classifier,
            'anomaly_detector': self.anomaly_detector,
            'scaler': self.scaler,
            'hash_database': self.hash_database,
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

        self.authenticity_classifier = model_data['authenticity_classifier']
        self.anomaly_detector = model_data['anomaly_detector']
        self.scaler = model_data['scaler']
        self.hash_database = model_data.get('hash_database', {})
        self.is_fitted = model_data['is_fitted']

        return True


def generate_synthetic_authenticity_data(n_samples: int = 2000) -> Tuple[np.ndarray, np.ndarray]:
    """Generate synthetic data for authenticity model."""
    np.random.seed(42)

    X = []
    y = []

    for _ in range(n_samples):
        is_authentic = np.random.random() < 0.7  # 70% authentic

        features = []

        if is_authentic:
            # Real photo characteristics
            for c in range(3):
                mean_val = np.random.uniform(100, 180)
                std_val = np.random.uniform(30, 60)
                features.extend([
                    mean_val,
                    std_val,
                    max(0, mean_val - 2.5*std_val),
                    min(255, mean_val + 2.5*std_val),
                    max(0, mean_val - 2*std_val),
                    min(255, mean_val + 2*std_val),
                    mean_val + np.random.normal(0, 5),
                    np.random.uniform(0.3, 0.8),  # Higher unique ratio for real
                ])

            # Real noise patterns
            features.extend([
                np.random.uniform(5, 25),  # Natural noise
                np.random.uniform(10, 40),
                np.random.uniform(20, 80),
                np.random.uniform(0.3, 0.8),  # Natural correlation
                np.random.uniform(0.1, 0.3),
            ])

            # Real histogram patterns
            features.extend([
                np.random.uniform(0.02, 0.08),
                np.random.uniform(0.02, 0.06),
                np.random.uniform(0.05, 0.15),
            ])

            # Metadata (real photos more likely to have)
            features.extend([
                np.random.choice([0, 1], p=[0.2, 0.8]),  # Has EXIF
                np.random.choice([0, 1], p=[0.3, 0.7]),  # Camera
                np.random.choice([0, 1], p=[0.6, 0.4]),  # GPS
                np.random.choice([0, 1], p=[0.1, 0.9]),  # Time consistent
            ])
        else:
            # AI/fake photo characteristics
            for c in range(3):
                mean_val = np.random.uniform(110, 170)
                std_val = np.random.uniform(20, 45)  # Less variance
                features.extend([
                    mean_val,
                    std_val,
                    max(0, mean_val - 2*std_val),
                    min(255, mean_val + 2*std_val),
                    max(0, mean_val - 1.5*std_val),
                    min(255, mean_val + 1.5*std_val),
                    mean_val + np.random.normal(0, 2),
                    np.random.uniform(0.1, 0.4),  # Lower unique ratio for AI
                ])

            # AI noise patterns (unnaturally smooth)
            features.extend([
                np.random.uniform(1, 10),  # Less noise
                np.random.uniform(3, 15),
                np.random.uniform(5, 25),
                np.random.uniform(0.7, 0.95),  # Higher correlation (too smooth)
                np.random.uniform(0.02, 0.1),
            ])

            # AI histogram patterns (too smooth)
            features.extend([
                np.random.uniform(0.005, 0.03),  # Very smooth
                np.random.uniform(0.005, 0.02),
                np.random.uniform(0.01, 0.05),
            ])

            # Metadata (AI often lacks)
            features.extend([
                np.random.choice([0, 1], p=[0.7, 0.3]),  # Less likely EXIF
                np.random.choice([0, 1], p=[0.8, 0.2]),
                np.random.choice([0, 1], p=[0.9, 0.1]),
                np.random.choice([0, 1], p=[0.4, 0.6]),
            ])

        # Add noise
        features = np.array(features) + np.random.normal(0, 0.5, len(features))

        X.append(features)
        y.append(1 if is_authentic else 0)

    return np.array(X), np.array(y)


def train_photo_validator(save_path: Optional[str] = None) -> Dict:
    """Train the photo authenticity validator."""
    print("\n" + "=" * 60)
    print("TRAINING: Photo Authenticity Validator")
    print("=" * 60)

    # Generate data
    print("\n[1/4] Generating training data...")
    X, y = generate_synthetic_authenticity_data(n_samples=2500)
    print(f"  Generated {len(X)} samples")
    print(f"  Authentic: {y.sum()} ({y.mean()*100:.1f}%)")

    # Split
    print("\n[2/4] Splitting train/validation...")
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Training: {len(X_train)} samples")
    print(f"  Validation: {len(X_val)} samples")

    # Train
    print("\n[3/4] Training model...")
    validator = PhotoAuthenticityValidator()
    validator.fit(X_train, y_train)
    print("  Model trained successfully")

    # Validate
    print("\n[4/4] Validating...")
    X_val_scaled = validator.scaler.transform(X_val)

    y_pred = validator.authenticity_classifier.predict(X_val_scaled)
    accuracy = accuracy_score(y_val, y_pred)
    precision = precision_score(y_val, y_pred)
    recall = recall_score(y_val, y_pred)

    print(f"  Accuracy: {accuracy*100:.1f}%")
    print(f"  Precision: {precision*100:.1f}%")
    print(f"  Recall: {recall*100:.1f}%")

    # Save
    if save_path is None:
        save_path = str(Path(__file__).parent / 'saved' / 'photo_validator.pkl')

    validator.save(save_path)
    print(f"\n  Model saved to: {save_path}")

    return {
        'model': 'PhotoAuthenticityValidator',
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'model_path': save_path,
        'status': 'SUCCESS' if accuracy >= 0.80 else 'BELOW_TARGET'
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    results = train_photo_validator()

    # Test inference
    print("\n" + "=" * 60)
    print("TESTING: Inference")
    print("=" * 60)

    validator = PhotoAuthenticityValidator()
    validator.load()

    # Test images
    authentic_img = np.random.randint(80, 200, (200, 300, 3)).astype(np.uint8)
    fake_img = np.random.randint(120, 170, (200, 300, 3)).astype(np.uint8)

    print("\nTest 1 (Authentic-like image):")
    result = validator.validate(
        authentic_img,
        metadata={'has_exif': True, 'camera_model': 'iPhone 14'},
        claimed_date=datetime.now()
    )
    print(f"  Trust Score: {result['trust_score']}%")
    print(f"  Verdict: {result['verdict']}")
    print(f"  Warnings: {result['warnings']}")

    print("\nTest 2 (Suspicious image):")
    result = validator.validate(
        fake_img,
        metadata={'has_exif': False}
    )
    print(f"  Trust Score: {result['trust_score']}%")
    print(f"  Verdict: {result['verdict']}")
    print(f"  Warnings: {result['warnings']}")
