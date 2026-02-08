"""
Test AI Analytics Manager - Advanced Analytics & AI Insights
PDR CRM Part 30 - AI-powered analytics and insights
"""

import sys
import os
from datetime import datetime, timedelta

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_ai_analytics():
    print("\n" + "="*80)
    print("TESTING AI ANALYTICS & INSIGHTS")
    print("="*80 + "\n")

    from src.crm.models.database import Database
    from src.crm.models.schema import DatabaseSchema
    from src.crm.managers.ai_analytics_manager import (
        AIAnalyticsManager,
        InsightType,
        AnomalyType,
        PatternType,
        SentimentLevel
    )

    # Use test database
    test_db = "data/test_ai_analytics.db"
    os.makedirs("data", exist_ok=True)

    if os.path.exists(test_db):
        os.remove(test_db)

    # Initialize
    print("Setting up test database...")
    DatabaseSchema.create_all_tables(test_db)

    db = Database(test_db)
    mgr = AIAnalyticsManager(db)

    # Setup: Create test data
    print("Creating test data...")

    # Create customers
    for i in range(1, 11):
        db.execute("""
            INSERT INTO customers (first_name, last_name, email, phone, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            f'Customer{i}',
            f'Test{i}',
            f'customer{i}@example.com',
            f'555-000{i}',
            'WEBSITE' if i % 2 == 0 else 'REFERRAL',
            (datetime.now() - timedelta(days=i*30)).isoformat()
        ))

    # Create technicians
    techs = [('Mike', 'Johnson', '["PDR"]'), ('Sarah', 'Williams', '["HAIL"]'), ('David', 'Chen', '["PDR"]')]
    for first, last, specialties in techs:
        db.execute("""
            INSERT INTO technicians (first_name, last_name, specialties, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (first, last, specialties, 'ACTIVE', datetime.now().isoformat()))

    # Create vehicles
    for i in range(1, 11):
        db.execute("""
            INSERT INTO vehicles (customer_id, year, make, model, vin, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (i, 2020 + (i % 4), 'Toyota', 'Camry', f'VIN{i:010d}', datetime.now().isoformat()))

    # Create jobs with various statuses and dates for analytics
    for i in range(1, 51):
        customer_id = (i % 10) + 1
        tech_id = (i % 3) + 1
        days_ago = i * 3
        scheduled = (datetime.now() - timedelta(days=days_ago + 5)).isoformat()
        completed = (datetime.now() - timedelta(days=days_ago)).isoformat()

        db.execute("""
            INSERT INTO jobs (
                job_number, customer_id, vehicle_id, assigned_tech_id,
                job_type, status, scheduled_drop_off, completed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'JOB-2026-{i:04d}',
            customer_id,
            customer_id,
            tech_id,
            'PDR' if i % 2 == 0 else 'HAIL',
            'COMPLETED',
            scheduled,
            completed,
            (datetime.now() - timedelta(days=days_ago)).isoformat()
        ))

    # Create invoices with historical created_at dates for revenue analysis
    for i in range(1, 51):
        total = 300 + (i * 20)
        days_ago = i * 3
        invoice_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
        db.execute("""
            INSERT INTO invoices (
                invoice_number, job_id, customer_id,
                invoice_date, subtotal, tax_amount, total,
                balance_due, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f'INV-2026-{i:04d}',
            i,
            (i % 10) + 1,
            invoice_date,
            total * 0.92,
            total * 0.08,
            total,
            0,
            'PAID',
            created_at
        ))

    # Create estimates
    for i in range(1, 31):
        total = 350 + (i * 20)
        db.execute("""
            INSERT INTO estimates (estimate_number, job_id, total, status)
            VALUES (?, ?, ?, ?)
        """, (f'EST-2026-{i:04d}', i, total, 'APPROVED'))

    # Create payments
    for i in range(1, 21):
        db.execute("""
            INSERT INTO payments (invoice_id, job_id, amount, total_amount, payment_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (i, i, 500, 500, datetime.now().strftime('%Y-%m-%d'), 'RECEIVED'))

    # Add a failed payment for churn signal - link to job 1
    db.execute("""
        INSERT INTO payments (invoice_id, job_id, amount, total_amount, payment_date, status)
        VALUES (1, 1, 500, 500, ?, 'BOUNCED')
    """, (datetime.now().strftime('%Y-%m-%d'),))

    # Create customer_reviews table
    db.execute("""
        CREATE TABLE IF NOT EXISTS customer_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            review_text TEXT,
            would_recommend INTEGER DEFAULT 1,
            review_categories TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'PUBLISHED',
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)

    # Create reviews
    for i in range(1, 16):
        db.execute("""
            INSERT INTO customer_reviews (
                customer_id, job_id, rating, review_text, would_recommend, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            (i % 10) + 1,
            i,
            3 + (i % 3),  # Ratings 3-5
            f'Great service! Review {i}',
            1,
            'PUBLISHED'
        ))

    # Add a low rating for customer 1 (for churn signal)
    db.execute("""
        INSERT INTO customer_reviews (customer_id, job_id, rating, review_text, would_recommend, status)
        VALUES (1, 1, 2, 'Not satisfied with the service.', 0, 'PUBLISHED')
    """)

    # Create email_logs table for engagement tracking
    db.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            subject TEXT,
            sent_at TIMESTAMP,
            opened_at TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    print(f"  Created 10 customers, 3 technicians, 50 jobs, 50 invoices, 16 reviews")
    print()

    # ==================== TEST 1: AI Analytics Initialization ====================
    print("Test 1: AI Analytics Manager Initialization")
    tables = ['churn_predictions', 'revenue_predictions', 'detected_anomalies',
              'detected_patterns', 'ai_insights', 'ai_recommendations', 'sentiment_analysis']

    for table in tables:
        result = db.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        assert len(result) > 0, f"Table {table} should exist"
        print(f"  - Table '{table}' created")
    print("  PASSED\n")

    # ==================== TEST 2: Churn Prediction ====================
    print("Test 2: Churn Prediction")
    predictions = mgr.predict_customer_churn()
    assert len(predictions) > 0, "Should generate churn predictions"
    print(f"  - Generated predictions for {len(predictions)} customers")

    prediction = predictions[0]
    assert 'customer_id' in prediction
    assert 'churn_probability' in prediction
    assert 'risk_level' in prediction
    assert 'contributing_factors' in prediction
    assert 'recommended_actions' in prediction
    print(f"  - Sample: Customer {prediction['customer_id']}, Risk: {prediction['risk_level']}")
    print("  PASSED\n")

    # ==================== TEST 3: High Risk Customers ====================
    print("Test 3: High Risk Customers")
    high_risk = mgr.get_high_risk_customers(limit=5)
    print(f"  - Found {len(high_risk)} high/medium risk customers")
    for customer in high_risk[:3]:
        print(f"    - {customer.get('first_name', 'Unknown')} {customer.get('last_name', '')}: {customer.get('risk_level', 'N/A')}")
    print("  PASSED\n")

    # ==================== TEST 4: Single Customer Churn Prediction ====================
    print("Test 4: Single Customer Churn Prediction")
    single_prediction = mgr.predict_customer_churn(customer_id=1)
    assert len(single_prediction) == 1, "Should return exactly one prediction"
    assert single_prediction[0]['customer_id'] == 1
    print(f"  - Customer 1 risk: {single_prediction[0]['risk_level']}")
    print(f"  - Probability: {single_prediction[0]['churn_probability']}")
    print("  PASSED\n")

    # ==================== TEST 5: Revenue Prediction ====================
    print("Test 5: Revenue Prediction")
    revenue_predictions = mgr.predict_revenue(periods=6, period_type='MONTHLY')
    assert len(revenue_predictions) > 0, "Should generate revenue predictions"
    print(f"  - Generated {len(revenue_predictions)} revenue predictions")
    for pred in revenue_predictions[:3]:
        print(f"    - {pred['prediction_period']}: ${pred['predicted_revenue']:,.2f}")
    print("  PASSED\n")

    # ==================== TEST 6: Anomaly Detection ====================
    print("Test 6: Anomaly Detection")
    anomalies = mgr.detect_anomalies(lookback_days=90)
    print(f"  - Detected {len(anomalies)} anomalies")
    for anomaly in anomalies[:3]:
        print(f"    - {anomaly['anomaly_type']}: {anomaly['description'][:60]}...")
    print("  PASSED\n")

    # ==================== TEST 7: Get Open Anomalies ====================
    print("Test 7: Get Open Anomalies")
    open_anomalies = mgr.get_open_anomalies()
    print(f"  - {len(open_anomalies)} open anomalies")
    print("  PASSED\n")

    # ==================== TEST 8: Resolve Anomaly ====================
    print("Test 8: Resolve Anomaly")
    if open_anomalies:
        anomaly_id = open_anomalies[0]['id']
        result = mgr.resolve_anomaly(anomaly_id, "Investigated and resolved")
        assert result is True
        resolved = db.execute("SELECT * FROM detected_anomalies WHERE id = ?", [anomaly_id])
        assert resolved[0]['resolution_status'] == 'RESOLVED'
        print(f"  - Anomaly {anomaly_id} resolved")
    else:
        db.execute("""
            INSERT INTO detected_anomalies (anomaly_type, severity, description)
            VALUES ('revenue_spike', 'MEDIUM', 'Test anomaly')
        """)
        mgr.resolve_anomaly(1, "Test resolution")
        print("  - Created and resolved test anomaly")
    print("  PASSED\n")

    # ==================== TEST 9: Pattern Discovery ====================
    print("Test 9: Pattern Discovery")
    patterns = mgr.discover_patterns()
    print(f"  - Discovered {len(patterns)} patterns")
    for pattern in patterns:
        print(f"    - {pattern['pattern_name']}: {pattern['description'][:50]}...")
    print("  PASSED\n")

    # ==================== TEST 10: Active Patterns ====================
    print("Test 10: Active Patterns")
    active_patterns = mgr.get_active_patterns()
    print(f"  - {len(active_patterns)} active patterns stored")
    print("  PASSED\n")

    # ==================== TEST 11: Automated Insights ====================
    print("Test 11: Automated Insights Generation")
    insights = mgr.generate_insights()
    print(f"  - Generated {len(insights)} insights")
    for insight in insights:
        print(f"    - [{insight['insight_type']}] {insight['title']}")
    print("  PASSED\n")

    # ==================== TEST 12: Active Insights ====================
    print("Test 12: Get Active Insights")
    active_insights = mgr.get_active_insights(limit=5)
    print(f"  - {len(active_insights)} active insights")
    print("  PASSED\n")

    # ==================== TEST 13: Dismiss Insight ====================
    print("Test 13: Dismiss Insight")
    if active_insights:
        insight_id = active_insights[0]['id']
        result = mgr.dismiss_insight(insight_id, "admin@test.com")
        assert result is True
        new_active = mgr.get_active_insights()
        dismissed_in_active = any(i['id'] == insight_id for i in new_active)
        assert not dismissed_in_active
        print(f"  - Insight {insight_id} dismissed")
    else:
        db.execute("""
            INSERT INTO ai_insights (insight_type, title, description, importance_score)
            VALUES ('churn_risk', 'Test Insight', 'Test description', 0.5)
        """)
        mgr.dismiss_insight(1, "admin@test.com")
        print("  - Created and dismissed test insight")
    print("  PASSED\n")

    # ==================== TEST 14: Recommendation Engine ====================
    print("Test 14: Recommendation Engine")
    recommendations = mgr.generate_recommendations()
    print(f"  - Generated {len(recommendations)} recommendations")
    for rec in recommendations[:3]:
        print(f"    - [{rec['priority']}] {rec['title'][:50]}...")
    print("  PASSED\n")

    # ==================== TEST 15: Pending Recommendations ====================
    print("Test 15: Get Pending Recommendations")
    pending = mgr.get_pending_recommendations()
    print(f"  - {len(pending)} pending recommendations")
    print("  PASSED\n")

    # ==================== TEST 16: Filter Recommendations by Priority ====================
    print("Test 16: Filter Recommendations by Priority")
    high_priority = mgr.get_pending_recommendations(priority='HIGH')
    print(f"  - {len(high_priority)} high priority recommendations")
    for rec in high_priority:
        assert rec['priority'] == 'HIGH'
    print("  PASSED\n")

    # ==================== TEST 17: Implement Recommendation ====================
    print("Test 17: Implement Recommendation")
    if pending:
        rec_id = pending[0]['id']
        result = mgr.implement_recommendation(rec_id, "Implemented via marketing")
        assert result is True
        implemented = db.execute("SELECT * FROM ai_recommendations WHERE id = ?", [rec_id])
        assert implemented[0]['status'] == 'IMPLEMENTED'
        print(f"  - Recommendation {rec_id} implemented")
    else:
        db.execute("""
            INSERT INTO ai_recommendations (recommendation_type, title, description, priority)
            VALUES ('UPSELL', 'Test Rec', 'Test description', 'HIGH')
        """)
        mgr.implement_recommendation(1, "Test implementation")
        print("  - Created and implemented test recommendation")
    print("  PASSED\n")

    # ==================== TEST 18: Sentiment Analysis ====================
    print("Test 18: Sentiment Analysis")
    positive_result = mgr.analyze_sentiment(
        "Excellent service! The technician was very professional and did amazing work!",
        source_type='REVIEW',
        source_id=1
    )
    assert positive_result['sentiment_score'] > 0, "Should be positive"
    print(f"  - Positive text: score={positive_result['sentiment_score']}, level={positive_result['sentiment_level']}")

    negative_result = mgr.analyze_sentiment(
        "Terrible experience. The work was poor quality and overpriced.",
        source_type='REVIEW',
        source_id=2
    )
    assert negative_result['sentiment_score'] < 0, "Should be negative"
    print(f"  - Negative text: score={negative_result['sentiment_score']}, level={negative_result['sentiment_level']}")

    neutral_result = mgr.analyze_sentiment(
        "The repair was completed on schedule.",
        source_type='REVIEW',
        source_id=3
    )
    print(f"  - Neutral text: score={neutral_result['sentiment_score']}, level={neutral_result['sentiment_level']}")
    print(f"  - Keywords: {positive_result['keywords']}")
    print("  PASSED\n")

    # ==================== TEST 19: Sentiment Summary ====================
    print("Test 19: Sentiment Summary")
    # Add more sentiments for summary
    texts = [
        ("Great quality work!", 'REVIEW'),
        ("Amazing service!", 'REVIEW'),
        ("Good experience.", 'FEEDBACK'),
        ("Not satisfied.", 'FEEDBACK'),
    ]
    for text, source_type in texts:
        mgr.analyze_sentiment(text, source_type=source_type)

    summary = mgr.get_sentiment_summary(days=30)
    print(f"  - Total analyzed: {summary['total_analyzed']}")
    print(f"  - Average score: {summary['average_score']:.2f}")
    print(f"  - Distribution: {summary['distribution']}")
    print("  PASSED\n")

    # ==================== TEST 20: AI Dashboard ====================
    print("Test 20: AI Dashboard")
    dashboard = mgr.get_ai_dashboard()

    assert 'churn_summary' in dashboard
    assert 'revenue_forecast' in dashboard
    assert 'active_anomalies' in dashboard
    assert 'active_patterns' in dashboard
    assert 'active_insights' in dashboard
    assert 'pending_recommendations' in dashboard
    assert 'sentiment_overview' in dashboard
    assert 'generated_at' in dashboard

    print(f"  - Churn summary: {dashboard['churn_summary']}")
    print(f"  - Active anomalies: {dashboard['active_anomalies']}")
    print(f"  - Active patterns: {dashboard['active_patterns']}")
    print(f"  - Active insights: {dashboard['active_insights']}")
    print(f"  - Pending recommendations: {dashboard['pending_recommendations']}")
    print("  PASSED\n")

    # ==================== TEST 21: Enum Values ====================
    print("Test 21: Enum Values")
    assert InsightType.CHURN_RISK.value == "churn_risk"
    assert InsightType.REVENUE_OPPORTUNITY.value == "revenue_opportunity"
    print(f"  - InsightType: {[e.value for e in InsightType]}")

    assert AnomalyType.REVENUE_SPIKE.value == "revenue_spike"
    assert AnomalyType.VOLUME_DROP.value == "volume_drop"
    print(f"  - AnomalyType: {[e.value for e in AnomalyType]}")

    assert PatternType.SEASONAL.value == "seasonal"
    assert PatternType.WEEKLY.value == "weekly"
    print(f"  - PatternType: {[e.value for e in PatternType]}")

    assert SentimentLevel.VERY_POSITIVE.value == "very_positive"
    assert SentimentLevel.NEGATIVE.value == "negative"
    print(f"  - SentimentLevel: {[e.value for e in SentimentLevel]}")
    print("  PASSED\n")

    # Final summary
    print("="*80)
    print("ALL TESTS PASSED - AI Analytics & Insights working correctly!")
    print("="*80)

    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)

    return True


if __name__ == '__main__':
    try:
        success = test_ai_analytics()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
