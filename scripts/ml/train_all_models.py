"""
Master Training Script for HailTracker Pro ML Models

Trains all 15 AI models in sequence:
- TIER 1: Meteorology (1-3)
- TIER 2: Social Media & Photos (4-6)
- TIER 3: PDR Business Intelligence (7-10)
- TIER 4: Advanced Intelligence (11-15)
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import training functions
from src.ml.models.radar_hail_classifier import train_radar_hail_classifier
from src.ml.models.storm_forecaster import train_storm_forecaster
from src.ml.models.seasonal_risk import train_seasonal_risk_model
from src.ml.models.hail_size_estimator import train_hail_size_estimator
from src.ml.models.vehicle_damage_detector import train_vehicle_damage_detector
from src.ml.models.photo_validator import train_photo_validator
from src.ml.models.pdr_business_models import train_pdr_business_models
from src.ml.models.advanced_models import train_advanced_models


def print_banner():
    """Print training banner."""
    print("""
================================================================================
    _   _       _ _ _____               _             ____  ____   ___
   | | | | __ _(_) |_   _| __ __ _  ___| | _____ _ __|  _ \|  _ \ / _ \
   | |_| |/ _` | | | | || '__/ _` |/ __| |/ / _ \ '__| |_) | |_) | | | |
   |  _  | (_| | | | | || | | (_| | (__|   <  __/ |  |  __/|  _ <| |_| |
   |_| |_|\__,_|_|_| |_||_|  \__,_|\___|_|\_\___|_|  |_|   |_| \_\\___/

                    ML MODEL TRAINING PIPELINE v1.0
================================================================================

    15 AI Models for Hail Detection & PDR Business Intelligence

    TIER 1: Meteorology
      1. Radar Hail Classifier
      2. Storm Severity Forecaster
      3. Seasonal Risk Model

    TIER 2: Social Media & Photos
      4. Hail Size Estimator
      5. Vehicle Damage Detector
      6. Photo Authenticity Validator

    TIER 3: PDR Business Intelligence
      7. ML Opportunity Scorer
      8. Claim Rate Predictor
      9. Damage Prediction Model
      10. Parking Lot Vehicle Counter

    TIER 4: Advanced Intelligence
      11. Route Optimizer
      12. Conversion Predictor
      13. Dealership Inventory Estimator
      14. Sentiment Analyzer
      15. Repair Time Estimator

================================================================================
""")


def train_all_models():
    """
    Train all 15 ML models.

    Returns:
        Dict with all training results
    """
    print_banner()

    start_time = datetime.now()
    all_results = {}

    # =========================================================================
    # TIER 1: Meteorology Models
    # =========================================================================
    print("\n" + "=" * 80)
    print(" TIER 1: METEOROLOGY MODELS")
    print("=" * 80)

    print("\n[1/15] Radar Hail Classifier...")
    all_results['1_radar_hail_classifier'] = train_radar_hail_classifier()

    print("\n[2/15] Storm Severity Forecaster...")
    all_results['2_storm_forecaster'] = train_storm_forecaster()

    print("\n[3/15] Seasonal Risk Model...")
    all_results['3_seasonal_risk'] = train_seasonal_risk_model()

    # =========================================================================
    # TIER 2: Social Media & Photos
    # =========================================================================
    print("\n" + "=" * 80)
    print(" TIER 2: SOCIAL MEDIA & PHOTO ANALYSIS")
    print("=" * 80)

    print("\n[4/15] Hail Size Estimator...")
    all_results['4_hail_size_estimator'] = train_hail_size_estimator()

    print("\n[5/15] Vehicle Damage Detector...")
    all_results['5_vehicle_damage_detector'] = train_vehicle_damage_detector()

    print("\n[6/15] Photo Authenticity Validator...")
    all_results['6_photo_validator'] = train_photo_validator()

    # =========================================================================
    # TIER 3: PDR Business Intelligence
    # =========================================================================
    print("\n" + "=" * 80)
    print(" TIER 3: PDR BUSINESS INTELLIGENCE")
    print("=" * 80)

    print("\n[7-10/15] PDR Business Models...")
    pdr_results = train_pdr_business_models()
    all_results['7_opportunity_scorer'] = pdr_results.get('opportunity_scorer', {})
    all_results['8_claim_rate_predictor'] = pdr_results.get('claim_rate_predictor', {})
    all_results['9_damage_prediction'] = pdr_results.get('damage_prediction', {})
    all_results['10_vehicle_counter'] = pdr_results.get('vehicle_counter', {})

    # =========================================================================
    # TIER 4: Advanced Intelligence
    # =========================================================================
    print("\n" + "=" * 80)
    print(" TIER 4: ADVANCED INTELLIGENCE")
    print("=" * 80)

    print("\n[11-15/15] Advanced Models...")
    adv_results = train_advanced_models()
    all_results['11_route_optimizer'] = adv_results.get('route_optimizer', {})
    all_results['12_conversion_predictor'] = adv_results.get('conversion_predictor', {})
    all_results['13_inventory_estimator'] = adv_results.get('inventory_estimator', {})
    all_results['14_sentiment_analyzer'] = adv_results.get('sentiment_analyzer', {})
    all_results['15_repair_time_estimator'] = adv_results.get('repair_time_estimator', {})

    # =========================================================================
    # Summary
    # =========================================================================
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 80)
    print(" TRAINING COMPLETE")
    print("=" * 80)

    print(f"\n  Total Training Time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"\n  Models Trained: 15")

    # Count successes
    success_count = sum(1 for r in all_results.values() if r.get('status') == 'SUCCESS')
    below_target = sum(1 for r in all_results.values() if r.get('status') == 'BELOW_TARGET')

    print(f"  Successful: {success_count}")
    print(f"  Below Target: {below_target}")

    print("\n  Model Status:")
    for name, result in sorted(all_results.items()):
        status = result.get('status', 'UNKNOWN')
        emoji = '[OK]' if status == 'SUCCESS' else '[!!]'
        print(f"    {emoji} {name}: {status}")

    # Save results
    results_path = PROJECT_ROOT / 'src' / 'ml' / 'models' / 'saved' / 'training_results.txt'
    with open(results_path, 'w') as f:
        f.write(f"HailTracker Pro ML Training Results\n")
        f.write(f"Date: {end_time.isoformat()}\n")
        f.write(f"Duration: {duration:.1f} seconds\n\n")
        for name, result in sorted(all_results.items()):
            f.write(f"{name}: {result}\n")

    print(f"\n  Results saved to: {results_path}")

    print("\n" + "=" * 80)
    print(" ALL 15 MODELS TRAINED AND SAVED")
    print("=" * 80)

    return all_results


if __name__ == '__main__':
    logging.basicConfig(level=logging.WARNING)  # Suppress info logs
    results = train_all_models()
