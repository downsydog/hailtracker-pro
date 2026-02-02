"""
ML Models API Routes
====================
RESTful API for hail detection ML models.

Endpoints:
- HailClassifier: classify hail events
- StormForecaster: forecast hail at multiple horizons
- HailSizeEstimator: estimate size from photos
- HailMLModel: raw prediction interface
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import base64
import numpy as np
from src.core.auth.decorators import login_required

ml_api_bp = Blueprint('ml_api', __name__, url_prefix='/api/ml')

# Cached model instances
_models = {}


def get_classifier():
    """Get or create HailClassifier"""
    if 'classifier' not in _models:
        try:
            from src.ml.hail_classifier import HailClassifier
            _models['classifier'] = HailClassifier(simulation_mode=True)
        except ImportError:
            return None
    return _models['classifier']


def get_forecaster():
    """Get or create StormForecaster"""
    if 'forecaster' not in _models:
        try:
            from src.ml.models.storm_forecaster import StormSeverityForecaster
            forecaster = StormSeverityForecaster()
            forecaster.load()  # Load saved model if available
            _models['forecaster'] = forecaster
        except ImportError:
            return None
    return _models['forecaster']


def get_size_estimator():
    """Get or create HailSizeEstimator"""
    if 'size_estimator' not in _models:
        try:
            from src.ml.models.hail_size_estimator import HailSizeEstimator
            estimator = HailSizeEstimator()
            estimator.load()  # Load saved model if available
            _models['size_estimator'] = estimator
        except ImportError:
            return None
    return _models['size_estimator']


def get_ml_model():
    """Get or create HailMLModel"""
    if 'ml_model' not in _models:
        try:
            from src.ml.hail_ml_model import HailMLModel
            model = HailMLModel()
            model.load()  # Load saved model if available
            _models['ml_model'] = model
        except ImportError:
            return None
    return _models['ml_model']


def get_damage_detector():
    """Get or create VehicleDamageDetector"""
    if 'damage_detector' not in _models:
        try:
            from src.ml.models.vehicle_damage_detector import VehicleDamageDetector
            detector = VehicleDamageDetector()
            detector.load()  # Load saved model if available
            _models['damage_detector'] = detector
        except ImportError:
            return None
    return _models['damage_detector']


def get_photo_validator():
    """Get or create PhotoAuthenticityValidator"""
    if 'photo_validator' not in _models:
        try:
            from src.ml.models.photo_validator import PhotoAuthenticityValidator
            validator = PhotoAuthenticityValidator()
            validator.load()  # Load saved model if available
            _models['photo_validator'] = validator
        except ImportError:
            return None
    return _models['photo_validator']


# =============================================================================
# HAIL CLASSIFIER
# =============================================================================

@ml_api_bp.route('/classify', methods=['POST'])
@login_required
def classify_hail():
    """Classify a hail event"""
    classifier = get_classifier()
    if not classifier:
        return jsonify({'error': 'Classifier not available'}), 503

    data = request.get_json()

    # Required fields
    lat = data.get('lat')
    lon = data.get('lon')

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon required'}), 400

    timestamp = data.get('timestamp')
    if timestamp:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', ''))
    else:
        timestamp = datetime.now()

    radar_data = data.get('radar_data', {})
    environmental_data = data.get('environmental_data', {})
    cell_data = data.get('cell_data', {})

    try:
        event = classifier.classify(
            lat=lat,
            lon=lon,
            timestamp=timestamp,
            radar_data=radar_data,
            environmental_data=environmental_data,
            cell_data=cell_data
        )

        return jsonify(event.to_dict())

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ml_api_bp.route('/classify-batch', methods=['POST'])
@login_required
def classify_batch():
    """Classify multiple hail events"""
    classifier = get_classifier()
    if not classifier:
        return jsonify({'error': 'Classifier not available'}), 503

    data = request.get_json()

    if 'events' not in data:
        return jsonify({'error': 'events array required'}), 400

    events = data['events']
    results = []

    for event_data in events:
        try:
            lat = event_data.get('lat')
            lon = event_data.get('lon')

            if lat is None or lon is None:
                results.append({'error': 'lat and lon required'})
                continue

            timestamp = event_data.get('timestamp')
            if timestamp and isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', ''))
            else:
                timestamp = datetime.now()

            event = classifier.classify(
                lat=lat,
                lon=lon,
                timestamp=timestamp,
                radar_data=event_data.get('radar_data', {}),
                environmental_data=event_data.get('environmental_data', {}),
                cell_data=event_data.get('cell_data', {})
            )

            results.append(event.to_dict())

        except Exception as e:
            results.append({'error': str(e)})

    return jsonify({
        'results': results,
        'count': len(results),
        'success_count': sum(1 for r in results if 'error' not in r)
    })


@ml_api_bp.route('/model-info', methods=['GET'])
@login_required
def get_model_info():
    """Get classifier model information"""
    classifier = get_classifier()
    if not classifier:
        return jsonify({'error': 'Classifier not available'}), 503

    try:
        info = classifier.get_model_info()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ml_api_bp.route('/feature-importance', methods=['GET'])
@login_required
def get_feature_importance():
    """Get feature importance rankings"""
    classifier = get_classifier()
    if not classifier:
        return jsonify({'error': 'Classifier not available'}), 503

    try:
        importance = classifier.get_feature_importance()
        return jsonify({'features': importance})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# STORM FORECASTER
# =============================================================================

@ml_api_bp.route('/forecast', methods=['POST'])
@login_required
def forecast_storm():
    """Forecast hail at multiple time horizons"""
    forecaster = get_forecaster()
    if not forecaster:
        return jsonify({'error': 'Forecaster not available'}), 503

    data = request.get_json()

    radar_trend = data.get('radar_trend', [])
    environment = data.get('environment', {})

    # Add time context if not provided
    if 'hour' not in environment:
        environment['hour'] = datetime.now().hour
    if 'month' not in environment:
        environment['month'] = datetime.now().month

    try:
        forecast = forecaster.forecast(radar_trend, environment)

        return jsonify({
            'forecast': forecast,
            'horizons': ['15min', '30min', '60min', '120min'],
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# HAIL SIZE ESTIMATOR (Photos)
# =============================================================================

@ml_api_bp.route('/estimate-size', methods=['POST'])
@login_required
def estimate_hail_size():
    """Estimate hail size from photo"""
    estimator = get_size_estimator()
    if not estimator:
        return jsonify({'error': 'Size estimator not available'}), 503

    data = request.get_json()

    # Accept base64 image or feature vector
    if 'image_base64' in data:
        try:
            image_bytes = base64.b64decode(data['image_base64'])
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            image_data = np.array(img)
        except Exception as e:
            return jsonify({'error': f'Failed to decode image: {e}'}), 400

    elif 'features' in data:
        image_data = np.array(data['features'])

    elif 'image_stats' in data:
        # Accept pre-computed image statistics
        stats = data['image_stats']
        # Generate feature vector from stats
        image_data = np.random.randint(100, 200, (100, 100, 3))  # Placeholder

    else:
        return jsonify({'error': 'image_base64, features, or image_stats required'}), 400

    try:
        result = estimator.estimate_size(image_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# VEHICLE DAMAGE DETECTOR
# =============================================================================

@ml_api_bp.route('/analyze-vehicle-damage', methods=['POST'])
@login_required
def analyze_vehicle_damage():
    """
    Analyze vehicle photo for hail damage.

    Accepts:
    - image_base64: Base64 encoded image
    - images: Array of base64 images (for multiple panels)

    Returns:
    - vehicle_detected: Whether a vehicle was detected
    - damage_detected: Whether damage was detected
    - severity: none/minor/moderate/severe/catastrophic
    - dent_count: Estimated number of dents
    - repair_cost_min: Minimum repair estimate
    - repair_cost_max: Maximum repair estimate
    - pdr_suitable: Whether PDR repair is recommended
    - panels: Per-panel damage assessment
    """
    detector = get_damage_detector()
    if not detector:
        return jsonify({'error': 'Damage detector not available'}), 503

    data = request.get_json()

    results = []

    # Handle single image or array of images
    images_b64 = data.get('images', [])
    if 'image_base64' in data:
        images_b64 = [data['image_base64']]

    if not images_b64:
        return jsonify({'error': 'image_base64 or images array required'}), 400

    for img_b64 in images_b64:
        try:
            image_bytes = base64.b64decode(img_b64)
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(image_bytes))
            image_data = np.array(img)

            result = detector.detect_damage(image_data)
            results.append(result)

        except Exception as e:
            results.append({'error': str(e)})

    # Aggregate results if multiple images
    if len(results) == 1:
        return jsonify(results[0])

    # Aggregate multiple panel assessments
    total_dents = sum(r.get('estimated_dent_count', 0) for r in results if 'error' not in r)
    severities = [r.get('severity', 'none') for r in results if 'error' not in r]
    severity_order = ['none', 'minor', 'moderate', 'severe', 'catastrophic']
    max_severity = max(severities, key=lambda s: severity_order.index(s) if s in severity_order else 0) if severities else 'none'

    costs = [(r.get('repair_cost_min', 0), r.get('repair_cost_max', 0)) for r in results if 'error' not in r]
    total_cost_min = sum(c[0] for c in costs)
    total_cost_max = sum(c[1] for c in costs)

    return jsonify({
        'panel_count': len(results),
        'total_dent_count': total_dents,
        'max_severity': max_severity,
        'repair_cost_min': total_cost_min,
        'repair_cost_max': total_cost_max,
        'pdr_suitable': max_severity in ['minor', 'moderate', 'severe'],
        'panels': results
    })


@ml_api_bp.route('/validate-photo', methods=['POST'])
@login_required
def validate_photo():
    """
    Validate photo authenticity.

    Checks for:
    - Duplicate/reposted images
    - AI-generated content
    - Metadata consistency

    Returns:
    - authentic_probability: 0-100
    - warnings: List of detected issues
    - trust_score: Overall trust score
    """
    validator = get_photo_validator()
    if not validator:
        return jsonify({'error': 'Photo validator not available'}), 503

    data = request.get_json()

    if 'image_base64' not in data:
        return jsonify({'error': 'image_base64 required'}), 400

    try:
        image_bytes = base64.b64decode(data['image_base64'])
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        image_data = np.array(img)

        # Get metadata if provided
        metadata = data.get('metadata', {})

        result = validator.validate(image_data, metadata)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# ANALYZE HAIL PHOTO (COMBINED ENDPOINT)
# =============================================================================

@ml_api_bp.route('/analyze-hail-photo', methods=['POST'])
@login_required
def analyze_hail_photo():
    """
    Full hail photo analysis combining size estimation, validation, and damage detection.

    Accepts:
    - image_base64: Base64 encoded image
    - include_validation: Whether to check authenticity (default: true)
    - include_damage: Whether to check for vehicle damage (default: false)

    Returns:
    - size: Hail size estimation results
    - validation: Photo authenticity results (if requested)
    - damage: Vehicle damage results (if requested)
    """
    data = request.get_json()

    if 'image_base64' not in data:
        return jsonify({'error': 'image_base64 required'}), 400

    try:
        image_bytes = base64.b64decode(data['image_base64'])
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes))
        image_data = np.array(img)
    except Exception as e:
        return jsonify({'error': f'Failed to decode image: {e}'}), 400

    result = {}

    # Size estimation (always run)
    estimator = get_size_estimator()
    if estimator:
        try:
            result['size'] = estimator.estimate_size(image_data)
        except Exception as e:
            result['size'] = {'error': str(e)}
    else:
        result['size'] = {'error': 'Size estimator not available'}

    # Photo validation (optional)
    if data.get('include_validation', True):
        validator = get_photo_validator()
        if validator:
            try:
                result['validation'] = validator.validate(image_data, data.get('metadata', {}))
            except Exception as e:
                result['validation'] = {'error': str(e)}

    # Damage detection (optional)
    if data.get('include_damage', False):
        detector = get_damage_detector()
        if detector:
            try:
                result['damage'] = detector.detect_damage(image_data)
            except Exception as e:
                result['damage'] = {'error': str(e)}

    return jsonify(result)


# =============================================================================
# RAW ML MODEL
# =============================================================================

@ml_api_bp.route('/predict', methods=['POST'])
@login_required
def predict_hail():
    """Raw ML prediction from features"""
    model = get_ml_model()
    if not model:
        return jsonify({'error': 'ML model not available'}), 503

    data = request.get_json()

    radar_data = data.get('radar_data', {})
    environmental_data = data.get('environmental_data', {})
    cell_data = data.get('cell_data', {})

    try:
        features = model.extract_features(radar_data, environmental_data, cell_data)
        prediction = model.predict(features, return_confidence=True)

        return jsonify({
            'hail_detected': prediction.hail_detected,
            'probability': prediction.hail_probability,
            'size_mm': prediction.estimated_size_mm,
            'size_inches': round(prediction.estimated_size_mm / 25.4, 2),
            'severity': prediction.severity,
            'confidence': prediction.confidence
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@ml_api_bp.route('/extract-features', methods=['POST'])
@login_required
def extract_features():
    """Extract features from input data"""
    model = get_ml_model()
    if not model:
        return jsonify({'error': 'ML model not available'}), 503

    data = request.get_json()

    radar_data = data.get('radar_data', {})
    environmental_data = data.get('environmental_data', {})
    cell_data = data.get('cell_data', {})

    try:
        features = model.extract_features(radar_data, environmental_data, cell_data)

        # Get feature names
        feature_names = [
            'max_reflectivity', 'avg_reflectivity', 'vil', 'mesh', 'posh',
            'echo_tops', 'zdr_min', 'zdr_avg', 'cc_min', 'kdp_max',
            'cape', 'shear_0_6km', 'freezing_level', 'wet_bulb_zero', 'lapse_rate',
            'cell_age_minutes', 'cell_velocity', 'cell_area', 'reflectivity_trend', 'mesh_trend'
        ]

        return jsonify({
            'features': features.tolist() if hasattr(features, 'tolist') else list(features),
            'feature_names': feature_names,
            'feature_count': len(features)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# MODEL STATUS
# =============================================================================

@ml_api_bp.route('/status', methods=['GET'])
@login_required
def get_ml_status():
    """Get status of all ML models"""
    status = {}

    # Check classifier
    classifier = get_classifier()
    status['classifier'] = {
        'available': classifier is not None,
        'type': 'HailClassifier'
    }
    if classifier:
        try:
            info = classifier.get_model_info()
            status['classifier']['model_info'] = info
        except:
            pass

    # Check forecaster
    forecaster = get_forecaster()
    status['forecaster'] = {
        'available': forecaster is not None,
        'type': 'StormSeverityForecaster',
        'is_fitted': forecaster.is_fitted if forecaster else False
    }

    # Check size estimator
    estimator = get_size_estimator()
    status['size_estimator'] = {
        'available': estimator is not None,
        'type': 'HailSizeEstimator',
        'is_fitted': estimator.is_fitted if estimator else False
    }

    # Check ML model
    model = get_ml_model()
    status['ml_model'] = {
        'available': model is not None,
        'type': 'HailMLModel',
        'is_fitted': model.is_fitted if model else False
    }

    return jsonify(status)


# =============================================================================
# SIZE REFERENCE
# =============================================================================

@ml_api_bp.route('/size-reference', methods=['GET'])
@login_required
def get_size_reference():
    """Get hail size reference chart"""
    return jsonify({
        'sizes': [
            {'name': 'pea', 'inches': 0.25, 'mm': 6.4, 'damage': 'minimal'},
            {'name': 'marble', 'inches': 0.5, 'mm': 12.7, 'damage': 'minor dents'},
            {'name': 'penny', 'inches': 0.75, 'mm': 19.0, 'damage': 'minor dents'},
            {'name': 'nickel', 'inches': 0.88, 'mm': 22.3, 'damage': 'visible dents'},
            {'name': 'quarter', 'inches': 1.0, 'mm': 25.4, 'damage': 'PDR repairable'},
            {'name': 'half_dollar', 'inches': 1.25, 'mm': 31.8, 'damage': 'moderate'},
            {'name': 'walnut', 'inches': 1.5, 'mm': 38.1, 'damage': 'significant'},
            {'name': 'golf_ball', 'inches': 1.75, 'mm': 44.5, 'damage': 'severe'},
            {'name': 'hen_egg', 'inches': 2.0, 'mm': 50.8, 'damage': 'severe'},
            {'name': 'tennis_ball', 'inches': 2.5, 'mm': 63.5, 'damage': 'extreme'},
            {'name': 'baseball', 'inches': 2.75, 'mm': 69.9, 'damage': 'catastrophic'},
            {'name': 'tea_cup', 'inches': 3.0, 'mm': 76.2, 'damage': 'catastrophic'},
            {'name': 'softball', 'inches': 4.0, 'mm': 101.6, 'damage': 'total loss likely'},
            {'name': 'grapefruit', 'inches': 4.5, 'mm': 114.3, 'damage': 'total loss'}
        ]
    })
