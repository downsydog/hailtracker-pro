"""
AI Analytics Manager - Advanced Analytics & AI Insights
Provides churn prediction, revenue forecasting, anomaly detection, pattern recognition,
automated insights, recommendations, and sentiment analysis for PDR CRM
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import math
import re
from collections import defaultdict
from enum import Enum


class InsightType(Enum):
    CHURN_RISK = "churn_risk"
    REVENUE_OPPORTUNITY = "revenue_opportunity"
    EFFICIENCY_IMPROVEMENT = "efficiency_improvement"
    CUSTOMER_BEHAVIOR = "customer_behavior"
    SEASONAL_TREND = "seasonal_trend"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"


class AnomalyType(Enum):
    REVENUE_SPIKE = "revenue_spike"
    REVENUE_DROP = "revenue_drop"
    VOLUME_SPIKE = "volume_spike"
    VOLUME_DROP = "volume_drop"
    UNUSUAL_PATTERN = "unusual_pattern"
    OUTLIER = "outlier"


class PatternType(Enum):
    SEASONAL = "seasonal"
    WEEKLY = "weekly"
    DAILY = "daily"
    CUSTOMER_BEHAVIOR = "customer_behavior"
    TECHNICIAN_PERFORMANCE = "technician_performance"
    GEOGRAPHIC = "geographic"


class SentimentLevel(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class AIAnalyticsManager:
    """Advanced analytics and AI-powered insights for PDR business intelligence"""

    def __init__(self, db):
        self.db = db
        self._ensure_ai_analytics_tables()

    def _ensure_ai_analytics_tables(self):
        """Ensure AI analytics tables exist"""
        # Churn predictions table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS churn_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                churn_probability REAL NOT NULL,
                risk_level TEXT NOT NULL,
                contributing_factors TEXT,
                recommended_actions TEXT,
                prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_version TEXT DEFAULT '1.0',
                is_current INTEGER DEFAULT 1,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Revenue predictions table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS revenue_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_period TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                predicted_revenue REAL NOT NULL,
                confidence_lower REAL,
                confidence_upper REAL,
                confidence_level REAL DEFAULT 0.95,
                contributing_factors TEXT,
                prediction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_version TEXT DEFAULT '1.0',
                actual_revenue REAL,
                accuracy_score REAL
            )
        """)

        # Anomalies table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS detected_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anomaly_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                affected_entity TEXT,
                affected_entity_id INTEGER,
                detected_value REAL,
                expected_value REAL,
                deviation_percent REAL,
                detection_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolution_status TEXT DEFAULT 'OPEN',
                resolution_notes TEXT,
                resolved_date TIMESTAMP
            )
        """)

        # Patterns table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS detected_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                description TEXT,
                strength REAL,
                data_points TEXT,
                discovery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                business_impact TEXT,
                recommendations TEXT
            )
        """)

        # AI Insights table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ai_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                importance_score REAL DEFAULT 0.5,
                affected_metrics TEXT,
                recommended_actions TEXT,
                supporting_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_dismissed INTEGER DEFAULT 0,
                dismissed_by TEXT,
                dismissed_at TIMESTAMP
            )
        """)

        # Recommendations table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_type TEXT NOT NULL,
                target_entity TEXT,
                target_entity_id INTEGER,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                expected_impact TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                implemented_at TIMESTAMP,
                implementation_notes TEXT,
                outcome TEXT
            )
        """)

        # Sentiment analysis table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id INTEGER,
                text_content TEXT NOT NULL,
                sentiment_score REAL NOT NULL,
                sentiment_level TEXT NOT NULL,
                keywords TEXT,
                topics TEXT,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # ==================== CHURN PREDICTION ====================

    def predict_customer_churn(self, customer_id: Optional[int] = None) -> List[Dict]:
        """Predict churn probability for customers"""
        if customer_id:
            customers = self.db.execute(
                "SELECT * FROM customers WHERE id = ?",
                [customer_id]
            )
        else:
            customers = self.db.execute("SELECT * FROM customers WHERE status = 'ACTIVE'")

        predictions = []
        for customer in customers:
            prediction = self._calculate_churn_prediction(customer)
            predictions.append(prediction)

            # Store prediction
            self._store_churn_prediction(customer['id'], prediction)

        return predictions

    def _calculate_churn_prediction(self, customer: Dict) -> Dict:
        """Calculate churn probability for a single customer"""
        customer_id = customer['id']
        factors = []
        risk_score = 0.0

        # Factor 1: Recency - Days since last job
        last_job = self.db.execute("""
            SELECT MAX(completed_at) as last_date
            FROM jobs
            WHERE customer_id = ? AND status = 'COMPLETED'
        """, [customer_id])

        days_since_last = 365  # Default to a year
        if last_job and last_job[0].get('last_date'):
            try:
                last_date = datetime.strptime(str(last_job[0]['last_date'])[:10], '%Y-%m-%d')
                days_since_last = (datetime.now() - last_date).days
            except:
                pass

        if days_since_last > 365:
            risk_score += 0.3
            factors.append({"factor": "inactivity", "value": days_since_last, "impact": "high"})
        elif days_since_last > 180:
            risk_score += 0.15
            factors.append({"factor": "inactivity", "value": days_since_last, "impact": "medium"})

        # Factor 2: Frequency - Number of jobs
        job_count = self.db.execute("""
            SELECT COUNT(*) as count FROM jobs WHERE customer_id = ?
        """, [customer_id])
        total_jobs = job_count[0]['count'] if job_count else 0

        if total_jobs <= 1:
            risk_score += 0.2
            factors.append({"factor": "low_engagement", "value": total_jobs, "impact": "medium"})

        # Factor 3: Payment history (check for bounced payments via jobs)
        payment_issues = self.db.execute("""
            SELECT COUNT(*) as count FROM payments p
            JOIN jobs j ON p.job_id = j.id
            WHERE j.customer_id = ? AND p.status = 'BOUNCED'
        """, [customer_id])
        failed_payments = payment_issues[0]['count'] if payment_issues else 0

        if failed_payments > 0:
            risk_score += min(0.25, failed_payments * 0.1)
            factors.append({"factor": "payment_issues", "value": failed_payments, "impact": "high"})

        # Factor 4: Review sentiment (if exists)
        try:
            reviews = self.db.execute("""
                SELECT AVG(rating) as avg_rating FROM customer_reviews
                WHERE customer_id = ?
            """, [customer_id])
            if reviews and reviews[0].get('avg_rating'):
                avg_rating = reviews[0]['avg_rating']
                if avg_rating < 3:
                    risk_score += 0.25
                    factors.append({"factor": "low_satisfaction", "value": avg_rating, "impact": "high"})
                elif avg_rating < 4:
                    risk_score += 0.1
                    factors.append({"factor": "moderate_satisfaction", "value": avg_rating, "impact": "medium"})
        except:
            pass

        # Factor 5: Communication engagement
        try:
            email_engagement = self.db.execute("""
                SELECT
                    COUNT(CASE WHEN opened_at IS NOT NULL THEN 1 END) as opened,
                    COUNT(*) as total
                FROM email_logs WHERE customer_id = ?
            """, [customer_id])
            if email_engagement and email_engagement[0]['total'] > 0:
                open_rate = email_engagement[0]['opened'] / email_engagement[0]['total']
                if open_rate < 0.1:
                    risk_score += 0.1
                    factors.append({"factor": "low_email_engagement", "value": open_rate, "impact": "low"})
        except:
            pass

        # Normalize risk score
        churn_probability = min(1.0, max(0.0, risk_score))

        # Determine risk level
        if churn_probability >= 0.7:
            risk_level = "HIGH"
        elif churn_probability >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Generate recommended actions
        actions = self._generate_churn_prevention_actions(factors, risk_level)

        return {
            "customer_id": customer_id,
            "customer_name": f"{customer.get('first_name', '')} {customer.get('last_name', '')}",
            "churn_probability": round(churn_probability, 3),
            "risk_level": risk_level,
            "contributing_factors": factors,
            "recommended_actions": actions,
            "prediction_date": datetime.now().isoformat()
        }

    def _generate_churn_prevention_actions(self, factors: List[Dict], risk_level: str) -> List[str]:
        """Generate recommended actions to prevent churn"""
        actions = []

        factor_types = {f['factor'] for f in factors}

        if 'inactivity' in factor_types:
            actions.append("Send re-engagement email with special offer")
            actions.append("Schedule follow-up call to check on vehicle condition")

        if 'low_engagement' in factor_types:
            actions.append("Enroll in loyalty program with incentives")
            actions.append("Send educational content about PDR benefits")

        if 'payment_issues' in factor_types:
            actions.append("Offer flexible payment plan options")
            actions.append("Review account for payment method updates")

        if 'low_satisfaction' in factor_types:
            actions.append("Personal outreach from manager to address concerns")
            actions.append("Offer complimentary service to rebuild trust")

        if 'low_email_engagement' in factor_types:
            actions.append("Try alternative communication channels (SMS)")
            actions.append("Update email preferences")

        if risk_level == "HIGH" and not actions:
            actions.append("Immediate personal outreach required")
            actions.append("Assign dedicated account manager")

        return actions

    def _store_churn_prediction(self, customer_id: int, prediction: Dict) -> int:
        """Store churn prediction in database"""
        # Mark previous predictions as not current
        self.db.execute("""
            UPDATE churn_predictions SET is_current = 0 WHERE customer_id = ?
        """, [customer_id])

        result = self.db.execute("""
            INSERT INTO churn_predictions
            (customer_id, churn_probability, risk_level, contributing_factors, recommended_actions)
            VALUES (?, ?, ?, ?, ?)
        """, [
            customer_id,
            prediction['churn_probability'],
            prediction['risk_level'],
            json.dumps(prediction['contributing_factors']),
            json.dumps(prediction['recommended_actions'])
        ])

        return result[0]['id']

    def get_high_risk_customers(self, limit: int = 20) -> List[Dict]:
        """Get customers with highest churn risk"""
        results = self.db.execute("""
            SELECT
                cp.*,
                c.first_name,
                c.last_name,
                c.email,
                c.phone
            FROM churn_predictions cp
            JOIN customers c ON cp.customer_id = c.id
            WHERE cp.is_current = 1 AND cp.risk_level IN ('HIGH', 'MEDIUM')
            ORDER BY cp.churn_probability DESC
            LIMIT ?
        """, [limit])

        return results

    # ==================== REVENUE PREDICTION ====================

    def predict_revenue(self, periods: int = 6, period_type: str = 'MONTHLY') -> List[Dict]:
        """Predict future revenue using time series analysis"""
        # Get historical revenue data
        historical = self._get_historical_revenue(period_type, 24)  # Last 24 periods

        if len(historical) < 3:
            return []

        predictions = []

        for i in range(periods):
            prediction = self._calculate_revenue_prediction(historical, i, period_type)
            predictions.append(prediction)

            # Store prediction
            self._store_revenue_prediction(prediction)

        return predictions

    def _get_historical_revenue(self, period_type: str, periods: int) -> List[Dict]:
        """Get historical revenue by period"""
        if period_type == 'MONTHLY':
            date_format = '%Y-%m'
            interval = 'month'
        elif period_type == 'WEEKLY':
            date_format = '%Y-%W'
            interval = 'week'
        else:  # DAILY
            date_format = '%Y-%m-%d'
            interval = 'day'

        results = self.db.execute("""
            SELECT
                strftime(?, created_at) as period,
                SUM(total) as revenue,
                COUNT(*) as transaction_count
            FROM invoices
            WHERE status IN ('PAID', 'SENT')
            GROUP BY period
            ORDER BY period DESC
            LIMIT ?
        """, [date_format, periods])

        return list(reversed(results)) if results else []

    def _calculate_revenue_prediction(self, historical: List[Dict],
                                       future_period: int, period_type: str) -> Dict:
        """Calculate revenue prediction using simple moving average with trend"""
        revenues = [h['revenue'] or 0 for h in historical]

        # Calculate moving average
        window = min(6, len(revenues))
        recent_avg = sum(revenues[-window:]) / window

        # Calculate trend
        if len(revenues) >= 2:
            old_avg = sum(revenues[:window]) / window if len(revenues) >= window * 2 else revenues[0]
            trend = (recent_avg - old_avg) / max(1, len(revenues) - window)
        else:
            trend = 0

        # Apply seasonality adjustment (simplified)
        seasonality_factor = 1.0
        current_month = datetime.now().month
        target_month = (current_month + future_period) % 12 or 12

        # Hail season boost (spring/summer)
        if target_month in [4, 5, 6, 7, 8]:
            seasonality_factor = 1.2
        elif target_month in [11, 12, 1, 2]:
            seasonality_factor = 0.85

        # Calculate prediction
        predicted = (recent_avg + (trend * future_period)) * seasonality_factor
        predicted = max(0, predicted)

        # Calculate confidence interval
        std_dev = self._calculate_std_dev(revenues)
        confidence_margin = std_dev * 1.96 * (1 + future_period * 0.1)  # Wider for further predictions

        # Calculate dates
        if period_type == 'MONTHLY':
            start_date = datetime.now().replace(day=1) + timedelta(days=32 * future_period)
            start_date = start_date.replace(day=1)
            end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        elif period_type == 'WEEKLY':
            start_date = datetime.now() + timedelta(weeks=future_period)
            start_date = start_date - timedelta(days=start_date.weekday())
            end_date = start_date + timedelta(days=6)
        else:  # DAILY
            start_date = datetime.now() + timedelta(days=future_period)
            end_date = start_date

        return {
            "prediction_period": f"{period_type}_{future_period + 1}",
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "predicted_revenue": round(predicted, 2),
            "confidence_lower": round(max(0, predicted - confidence_margin), 2),
            "confidence_upper": round(predicted + confidence_margin, 2),
            "confidence_level": 0.95,
            "contributing_factors": {
                "trend": round(trend, 2),
                "seasonality": seasonality_factor,
                "base_average": round(recent_avg, 2)
            }
        }

    def _calculate_std_dev(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def _store_revenue_prediction(self, prediction: Dict) -> int:
        """Store revenue prediction"""
        result = self.db.execute("""
            INSERT INTO revenue_predictions
            (prediction_period, start_date, end_date, predicted_revenue,
             confidence_lower, confidence_upper, confidence_level, contributing_factors)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            prediction['prediction_period'],
            prediction['start_date'],
            prediction['end_date'],
            prediction['predicted_revenue'],
            prediction['confidence_lower'],
            prediction['confidence_upper'],
            prediction['confidence_level'],
            json.dumps(prediction['contributing_factors'])
        ])

        return result[0]['id']

    # ==================== ANOMALY DETECTION ====================

    def detect_anomalies(self, lookback_days: int = 30) -> List[Dict]:
        """Detect anomalies in business metrics"""
        anomalies = []

        # Detect revenue anomalies
        revenue_anomalies = self._detect_revenue_anomalies(lookback_days)
        anomalies.extend(revenue_anomalies)

        # Detect volume anomalies
        volume_anomalies = self._detect_volume_anomalies(lookback_days)
        anomalies.extend(volume_anomalies)

        # Detect technician performance anomalies
        tech_anomalies = self._detect_technician_anomalies(lookback_days)
        anomalies.extend(tech_anomalies)

        # Store detected anomalies
        for anomaly in anomalies:
            self._store_anomaly(anomaly)

        return anomalies

    def _detect_revenue_anomalies(self, lookback_days: int) -> List[Dict]:
        """Detect revenue anomalies"""
        anomalies = []

        # Get daily revenue for lookback period
        results = self.db.execute("""
            SELECT
                DATE(created_at) as date,
                SUM(total) as revenue
            FROM invoices
            WHERE created_at >= DATE('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, [f'-{lookback_days} days'])

        if len(results) < 7:
            return anomalies

        revenues = [r['revenue'] or 0 for r in results]
        mean = sum(revenues) / len(revenues)
        std_dev = self._calculate_std_dev(revenues)

        # Check last 7 days for anomalies
        for i, r in enumerate(results[-7:], start=len(results)-7):
            revenue = r['revenue'] or 0
            if std_dev > 0:
                z_score = (revenue - mean) / std_dev

                if abs(z_score) > 2:
                    anomaly_type = AnomalyType.REVENUE_SPIKE if z_score > 0 else AnomalyType.REVENUE_DROP
                    severity = "HIGH" if abs(z_score) > 3 else "MEDIUM"

                    anomalies.append({
                        "anomaly_type": anomaly_type.value,
                        "severity": severity,
                        "description": f"{'Unusually high' if z_score > 0 else 'Unusually low'} revenue on {r['date']}",
                        "affected_entity": "daily_revenue",
                        "affected_entity_id": None,
                        "detected_value": revenue,
                        "expected_value": mean,
                        "deviation_percent": round((revenue - mean) / mean * 100, 1) if mean > 0 else 0,
                        "detection_date": datetime.now().isoformat()
                    })

        return anomalies

    def _detect_volume_anomalies(self, lookback_days: int) -> List[Dict]:
        """Detect job volume anomalies"""
        anomalies = []

        results = self.db.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as job_count
            FROM jobs
            WHERE created_at >= DATE('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY date
        """, [f'-{lookback_days} days'])

        if len(results) < 7:
            return anomalies

        counts = [r['job_count'] for r in results]
        mean = sum(counts) / len(counts)
        std_dev = self._calculate_std_dev(counts)

        for r in results[-7:]:
            count = r['job_count']
            if std_dev > 0:
                z_score = (count - mean) / std_dev

                if abs(z_score) > 2:
                    anomaly_type = AnomalyType.VOLUME_SPIKE if z_score > 0 else AnomalyType.VOLUME_DROP
                    severity = "HIGH" if abs(z_score) > 3 else "MEDIUM"

                    anomalies.append({
                        "anomaly_type": anomaly_type.value,
                        "severity": severity,
                        "description": f"{'Unusually high' if z_score > 0 else 'Unusually low'} job volume on {r['date']}",
                        "affected_entity": "daily_jobs",
                        "affected_entity_id": None,
                        "detected_value": count,
                        "expected_value": mean,
                        "deviation_percent": round((count - mean) / mean * 100, 1) if mean > 0 else 0,
                        "detection_date": datetime.now().isoformat()
                    })

        return anomalies

    def _detect_technician_anomalies(self, lookback_days: int) -> List[Dict]:
        """Detect technician performance anomalies"""
        anomalies = []

        # Get technician performance
        results = self.db.execute("""
            SELECT
                t.id,
                t.first_name,
                t.last_name,
                COUNT(j.id) as jobs_completed,
                AVG(JULIANDAY(j.completed_at) - JULIANDAY(j.scheduled_drop_off)) as avg_completion_time
            FROM technicians t
            LEFT JOIN jobs j ON t.id = j.assigned_tech_id
                AND j.status = 'COMPLETED'
                AND j.completed_at >= DATE('now', ?)
            GROUP BY t.id
            HAVING jobs_completed > 0
        """, [f'-{lookback_days} days'])

        if len(results) < 2:
            return anomalies

        completion_times = [r['avg_completion_time'] or 0 for r in results if r['avg_completion_time']]
        if not completion_times:
            return anomalies

        mean = sum(completion_times) / len(completion_times)
        std_dev = self._calculate_std_dev(completion_times)

        for r in results:
            if r['avg_completion_time'] and std_dev > 0:
                z_score = (r['avg_completion_time'] - mean) / std_dev

                if z_score > 2:  # Taking much longer than average
                    anomalies.append({
                        "anomaly_type": AnomalyType.UNUSUAL_PATTERN.value,
                        "severity": "MEDIUM",
                        "description": f"Technician {r['first_name']} {r['last_name']} has unusually long completion times",
                        "affected_entity": "technician",
                        "affected_entity_id": r['id'],
                        "detected_value": r['avg_completion_time'],
                        "expected_value": mean,
                        "deviation_percent": round((r['avg_completion_time'] - mean) / mean * 100, 1) if mean > 0 else 0,
                        "detection_date": datetime.now().isoformat()
                    })

        return anomalies

    def _store_anomaly(self, anomaly: Dict) -> int:
        """Store detected anomaly"""
        result = self.db.execute("""
            INSERT INTO detected_anomalies
            (anomaly_type, severity, description, affected_entity, affected_entity_id,
             detected_value, expected_value, deviation_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            anomaly['anomaly_type'],
            anomaly['severity'],
            anomaly['description'],
            anomaly.get('affected_entity'),
            anomaly.get('affected_entity_id'),
            anomaly.get('detected_value'),
            anomaly.get('expected_value'),
            anomaly.get('deviation_percent')
        ])

        return result[0]['id']

    def get_open_anomalies(self) -> List[Dict]:
        """Get all unresolved anomalies"""
        return self.db.execute("""
            SELECT * FROM detected_anomalies
            WHERE resolution_status = 'OPEN'
            ORDER BY
                CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                detection_date DESC
        """)

    def resolve_anomaly(self, anomaly_id: int, resolution_notes: str) -> bool:
        """Mark an anomaly as resolved"""
        self.db.execute("""
            UPDATE detected_anomalies
            SET resolution_status = 'RESOLVED',
                resolution_notes = ?,
                resolved_date = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [resolution_notes, anomaly_id])

        return True

    # ==================== PATTERN RECOGNITION ====================

    def discover_patterns(self) -> List[Dict]:
        """Discover patterns in business data"""
        patterns = []

        # Discover seasonal patterns
        seasonal = self._discover_seasonal_patterns()
        patterns.extend(seasonal)

        # Discover weekly patterns
        weekly = self._discover_weekly_patterns()
        patterns.extend(weekly)

        # Discover customer behavior patterns
        customer = self._discover_customer_patterns()
        patterns.extend(customer)

        # Store patterns
        for pattern in patterns:
            self._store_pattern(pattern)

        return patterns

    def _discover_seasonal_patterns(self) -> List[Dict]:
        """Discover seasonal revenue patterns"""
        patterns = []

        results = self.db.execute("""
            SELECT
                strftime('%m', created_at) as month,
                SUM(total) as revenue,
                COUNT(*) as job_count
            FROM invoices
            WHERE created_at >= DATE('now', '-2 years')
            GROUP BY month
            ORDER BY month
        """)

        if len(results) < 6:
            return patterns

        # Find peak and low months
        month_data = {r['month']: r for r in results}
        revenues = [(r['month'], r['revenue'] or 0) for r in results]
        revenues.sort(key=lambda x: x[1], reverse=True)

        if revenues:
            peak_months = [r[0] for r in revenues[:3]]
            low_months = [r[0] for r in revenues[-3:]]

            month_names = {
                '01': 'January', '02': 'February', '03': 'March', '04': 'April',
                '05': 'May', '06': 'June', '07': 'July', '08': 'August',
                '09': 'September', '10': 'October', '11': 'November', '12': 'December'
            }

            patterns.append({
                "pattern_type": PatternType.SEASONAL.value,
                "pattern_name": "Peak Season Pattern",
                "description": f"Highest revenue months: {', '.join(month_names.get(m, m) for m in peak_months)}",
                "strength": 0.8,
                "data_points": {"peak_months": peak_months, "low_months": low_months},
                "business_impact": "HIGH",
                "recommendations": [
                    "Increase marketing spend before peak months",
                    "Ensure adequate staffing during peak season",
                    "Consider off-season promotions to balance revenue"
                ]
            })

        return patterns

    def _discover_weekly_patterns(self) -> List[Dict]:
        """Discover weekly patterns"""
        patterns = []

        results = self.db.execute("""
            SELECT
                CAST(strftime('%w', j.created_at) AS INTEGER) as day_of_week,
                COUNT(*) as job_count,
                SUM(i.total) as revenue
            FROM jobs j
            LEFT JOIN invoices i ON j.id = i.job_id
            WHERE j.created_at >= DATE('now', '-6 months')
            GROUP BY day_of_week
            ORDER BY day_of_week
        """)

        if len(results) < 5:
            return patterns

        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        jobs_by_day = {r['day_of_week']: r['job_count'] for r in results}

        # Find busiest and slowest days
        sorted_days = sorted(results, key=lambda x: x['job_count'], reverse=True)

        if sorted_days:
            busiest = sorted_days[0]
            slowest = sorted_days[-1]

            patterns.append({
                "pattern_type": PatternType.WEEKLY.value,
                "pattern_name": "Weekly Activity Pattern",
                "description": f"Busiest day: {day_names[busiest['day_of_week']]} ({busiest['job_count']} jobs avg), Slowest: {day_names[slowest['day_of_week']]}",
                "strength": 0.7,
                "data_points": {"jobs_by_day": jobs_by_day},
                "business_impact": "MEDIUM",
                "recommendations": [
                    f"Schedule more staff on {day_names[busiest['day_of_week']]}s",
                    f"Consider promotions for {day_names[slowest['day_of_week']]}s",
                    "Optimize scheduling around peak days"
                ]
            })

        return patterns

    def _discover_customer_patterns(self) -> List[Dict]:
        """Discover customer behavior patterns"""
        patterns = []

        # Repeat customer pattern
        repeat_data = self.db.execute("""
            SELECT
                j.customer_id,
                COUNT(*) as job_count,
                SUM(i.total) as total_revenue
            FROM jobs j
            LEFT JOIN invoices i ON j.id = i.job_id
            WHERE j.status = 'COMPLETED'
            GROUP BY j.customer_id
            HAVING job_count > 1
        """)

        total_customers = self.db.execute("SELECT COUNT(*) as count FROM customers")
        total_count = total_customers[0]['count'] if total_customers else 1

        repeat_count = len(repeat_data)
        repeat_percentage = (repeat_count / total_count * 100) if total_count > 0 else 0

        patterns.append({
            "pattern_type": PatternType.CUSTOMER_BEHAVIOR.value,
            "pattern_name": "Customer Retention Pattern",
            "description": f"{repeat_percentage:.1f}% of customers have used services multiple times",
            "strength": 0.6,
            "data_points": {
                "repeat_customers": repeat_count,
                "total_customers": total_count,
                "repeat_percentage": round(repeat_percentage, 1)
            },
            "business_impact": "HIGH",
            "recommendations": [
                "Implement loyalty program if not already in place",
                "Focus on first-visit experience to drive retention",
                "Create referral incentives for repeat customers"
            ]
        })

        return patterns

    def _store_pattern(self, pattern: Dict) -> int:
        """Store discovered pattern"""
        result = self.db.execute("""
            INSERT INTO detected_patterns
            (pattern_type, pattern_name, description, strength, data_points,
             business_impact, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            pattern['pattern_type'],
            pattern['pattern_name'],
            pattern['description'],
            pattern['strength'],
            json.dumps(pattern.get('data_points', {})),
            pattern.get('business_impact', 'MEDIUM'),
            json.dumps(pattern.get('recommendations', []))
        ])

        return result[0]['id']

    def get_active_patterns(self) -> List[Dict]:
        """Get all active discovered patterns"""
        results = self.db.execute("""
            SELECT * FROM detected_patterns
            WHERE is_active = 1
            ORDER BY strength DESC
        """)

        for r in results:
            if r.get('data_points'):
                try:
                    r['data_points'] = json.loads(r['data_points'])
                except:
                    pass
            if r.get('recommendations'):
                try:
                    r['recommendations'] = json.loads(r['recommendations'])
                except:
                    pass

        return results

    # ==================== AUTOMATED INSIGHTS ====================

    def generate_insights(self) -> List[Dict]:
        """Generate automated business insights"""
        insights = []

        # Revenue insights
        revenue_insights = self._generate_revenue_insights()
        insights.extend(revenue_insights)

        # Customer insights
        customer_insights = self._generate_customer_insights()
        insights.extend(customer_insights)

        # Efficiency insights
        efficiency_insights = self._generate_efficiency_insights()
        insights.extend(efficiency_insights)

        # Store insights
        for insight in insights:
            self._store_insight(insight)

        return insights

    def _generate_revenue_insights(self) -> List[Dict]:
        """Generate revenue-related insights"""
        insights = []

        # Compare current month to previous month
        current = self.db.execute("""
            SELECT SUM(total) as revenue
            FROM invoices
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
        """)

        previous = self.db.execute("""
            SELECT SUM(total) as revenue
            FROM invoices
            WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', '-1 month')
        """)

        current_revenue = current[0]['revenue'] or 0 if current else 0
        previous_revenue = previous[0]['revenue'] or 0 if previous else 0

        if previous_revenue > 0:
            change = ((current_revenue - previous_revenue) / previous_revenue) * 100

            if abs(change) > 10:
                direction = "up" if change > 0 else "down"
                insights.append({
                    "insight_type": InsightType.REVENUE_OPPORTUNITY.value,
                    "title": f"Revenue Trending {direction.title()}",
                    "description": f"Month-over-month revenue is {direction} {abs(change):.1f}% compared to last month",
                    "importance_score": min(0.9, abs(change) / 100 + 0.5),
                    "affected_metrics": ["revenue", "growth"],
                    "recommended_actions": [
                        "Review top revenue drivers" if change > 0 else "Analyze revenue decline causes",
                        "Adjust marketing spend accordingly"
                    ],
                    "supporting_data": {
                        "current_month": current_revenue,
                        "previous_month": previous_revenue,
                        "change_percent": round(change, 1)
                    }
                })

        return insights

    def _generate_customer_insights(self) -> List[Dict]:
        """Generate customer-related insights"""
        insights = []

        # New customer acquisition
        new_customers = self.db.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE created_at >= DATE('now', '-30 days')
        """)

        previous_new = self.db.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE created_at >= DATE('now', '-60 days')
            AND created_at < DATE('now', '-30 days')
        """)

        new_count = new_customers[0]['count'] if new_customers else 0
        prev_count = previous_new[0]['count'] if previous_new else 0

        if prev_count > 0:
            change = ((new_count - prev_count) / prev_count) * 100

            if abs(change) > 15:
                direction = "increased" if change > 0 else "decreased"
                insights.append({
                    "insight_type": InsightType.CUSTOMER_BEHAVIOR.value,
                    "title": f"Customer Acquisition {direction.title()}",
                    "description": f"New customer signups have {direction} by {abs(change):.1f}% in the last 30 days",
                    "importance_score": 0.7,
                    "affected_metrics": ["customer_acquisition", "growth"],
                    "recommended_actions": [
                        "Expand marketing efforts" if change > 0 else "Review marketing effectiveness",
                        "Analyze acquisition channels"
                    ],
                    "supporting_data": {
                        "new_customers_30d": new_count,
                        "new_customers_prev_30d": prev_count,
                        "change_percent": round(change, 1)
                    }
                })

        return insights

    def _generate_efficiency_insights(self) -> List[Dict]:
        """Generate efficiency-related insights"""
        insights = []

        # Average job completion time
        completion_time = self.db.execute("""
            SELECT
                AVG(JULIANDAY(completed_at) - JULIANDAY(scheduled_drop_off)) as avg_days
            FROM jobs
            WHERE status = 'COMPLETED'
            AND completed_at >= DATE('now', '-30 days')
        """)

        avg_days = completion_time[0]['avg_days'] if completion_time and completion_time[0]['avg_days'] else None

        if avg_days is not None:
            if avg_days > 3:
                insights.append({
                    "insight_type": InsightType.EFFICIENCY_IMPROVEMENT.value,
                    "title": "Job Completion Time Alert",
                    "description": f"Average job completion time is {avg_days:.1f} days, which may indicate scheduling bottlenecks",
                    "importance_score": 0.75,
                    "affected_metrics": ["efficiency", "customer_satisfaction"],
                    "recommended_actions": [
                        "Review scheduling process",
                        "Identify bottlenecks in workflow",
                        "Consider adding technician capacity"
                    ],
                    "supporting_data": {
                        "avg_completion_days": round(avg_days, 2)
                    }
                })

        return insights

    def _store_insight(self, insight: Dict) -> int:
        """Store generated insight"""
        result = self.db.execute("""
            INSERT INTO ai_insights
            (insight_type, title, description, importance_score,
             affected_metrics, recommended_actions, supporting_data,
             expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, DATE('now', '+7 days'))
        """, [
            insight['insight_type'],
            insight['title'],
            insight['description'],
            insight.get('importance_score', 0.5),
            json.dumps(insight.get('affected_metrics', [])),
            json.dumps(insight.get('recommended_actions', [])),
            json.dumps(insight.get('supporting_data', {}))
        ])

        return result[0]['id']

    def get_active_insights(self, limit: int = 10) -> List[Dict]:
        """Get active (non-dismissed, non-expired) insights"""
        results = self.db.execute("""
            SELECT * FROM ai_insights
            WHERE is_dismissed = 0
            AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY importance_score DESC
            LIMIT ?
        """, [limit])

        for r in results:
            for field in ['affected_metrics', 'recommended_actions', 'supporting_data']:
                if r.get(field):
                    try:
                        r[field] = json.loads(r[field])
                    except:
                        pass

        return results

    def dismiss_insight(self, insight_id: int, dismissed_by: str) -> bool:
        """Dismiss an insight"""
        self.db.execute("""
            UPDATE ai_insights
            SET is_dismissed = 1,
                dismissed_by = ?,
                dismissed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [dismissed_by, insight_id])

        return True

    # ==================== RECOMMENDATION ENGINE ====================

    def generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations"""
        recommendations = []

        # Customer recommendations
        customer_recs = self._generate_customer_recommendations()
        recommendations.extend(customer_recs)

        # Operational recommendations
        operational_recs = self._generate_operational_recommendations()
        recommendations.extend(operational_recs)

        # Revenue recommendations
        revenue_recs = self._generate_revenue_recommendations()
        recommendations.extend(revenue_recs)

        # Store recommendations
        for rec in recommendations:
            self._store_recommendation(rec)

        return recommendations

    def _generate_customer_recommendations(self) -> List[Dict]:
        """Generate customer-related recommendations"""
        recommendations = []

        # Find customers who might benefit from upsell
        high_value = self.db.execute("""
            SELECT
                c.id,
                c.first_name,
                c.last_name,
                COUNT(j.id) as job_count,
                SUM(i.total) as total_spent
            FROM customers c
            JOIN jobs j ON c.id = j.customer_id
            LEFT JOIN invoices i ON j.id = i.job_id
            WHERE j.status = 'COMPLETED'
            GROUP BY c.id
            HAVING job_count >= 2 AND total_spent > 1000
            ORDER BY total_spent DESC
            LIMIT 10
        """)

        for customer in high_value:
            recommendations.append({
                "recommendation_type": "UPSELL",
                "target_entity": "customer",
                "target_entity_id": customer['id'],
                "title": f"Premium Service Opportunity: {customer['first_name']} {customer['last_name']}",
                "description": f"This customer has spent ${customer['total_spent']:.2f} across {customer['job_count']} jobs. Consider offering premium services or maintenance packages.",
                "expected_impact": "Potential 20-30% increase in customer lifetime value",
                "priority": "HIGH"
            })

        return recommendations

    def _generate_operational_recommendations(self) -> List[Dict]:
        """Generate operational recommendations"""
        recommendations = []

        # Check technician workload balance
        workload = self.db.execute("""
            SELECT
                t.id,
                t.first_name,
                t.last_name,
                COUNT(j.id) as active_jobs
            FROM technicians t
            LEFT JOIN jobs j ON t.id = j.assigned_tech_id
                AND j.status IN ('IN_PROGRESS', 'SCHEDULED')
            WHERE t.status = 'ACTIVE'
            GROUP BY t.id
        """)

        if workload:
            jobs_counts = [w['active_jobs'] for w in workload]
            avg_load = sum(jobs_counts) / len(jobs_counts) if jobs_counts else 0

            for w in workload:
                if w['active_jobs'] > avg_load * 1.5:
                    recommendations.append({
                        "recommendation_type": "WORKLOAD_BALANCE",
                        "target_entity": "technician",
                        "target_entity_id": w['id'],
                        "title": f"Workload Imbalance: {w['first_name']} {w['last_name']}",
                        "description": f"This technician has {w['active_jobs']} active jobs while average is {avg_load:.1f}. Consider redistributing work.",
                        "expected_impact": "Improved technician efficiency and job completion times",
                        "priority": "MEDIUM"
                    })

        return recommendations

    def _generate_revenue_recommendations(self) -> List[Dict]:
        """Generate revenue-related recommendations"""
        recommendations = []

        # Check for low-margin jobs
        low_margin = self.db.execute("""
            SELECT
                j.job_number,
                j.id,
                e.total as estimated,
                i.total as invoiced
            FROM jobs j
            JOIN estimates e ON j.id = e.job_id
            JOIN invoices i ON j.id = i.job_id
            WHERE j.status = 'COMPLETED'
            AND j.completed_at >= DATE('now', '-30 days')
            AND i.total < e.total * 0.8
        """)

        if len(low_margin) >= 3:
            recommendations.append({
                "recommendation_type": "PRICING",
                "target_entity": "jobs",
                "target_entity_id": None,
                "title": "Review Pricing Strategy",
                "description": f"{len(low_margin)} jobs in the last 30 days have invoiced below 80% of estimates. Review pricing and discount policies.",
                "expected_impact": "Potential 10-15% improvement in profit margins",
                "priority": "HIGH"
            })

        return recommendations

    def _store_recommendation(self, rec: Dict) -> int:
        """Store recommendation"""
        result = self.db.execute("""
            INSERT INTO ai_recommendations
            (recommendation_type, target_entity, target_entity_id, title,
             description, expected_impact, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            rec['recommendation_type'],
            rec.get('target_entity'),
            rec.get('target_entity_id'),
            rec['title'],
            rec['description'],
            rec.get('expected_impact'),
            rec.get('priority', 'MEDIUM')
        ])

        return result[0]['id']

    def get_pending_recommendations(self, priority: Optional[str] = None) -> List[Dict]:
        """Get pending recommendations"""
        query = "SELECT * FROM ai_recommendations WHERE status = 'PENDING'"
        params = []

        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END"

        return self.db.execute(query, params) if params else self.db.execute(query)

    def implement_recommendation(self, recommendation_id: int, notes: str) -> bool:
        """Mark a recommendation as implemented"""
        self.db.execute("""
            UPDATE ai_recommendations
            SET status = 'IMPLEMENTED',
                implemented_at = CURRENT_TIMESTAMP,
                implementation_notes = ?
            WHERE id = ?
        """, [notes, recommendation_id])

        return True

    # ==================== SENTIMENT ANALYSIS ====================

    def analyze_sentiment(self, text: str, source_type: str = 'REVIEW',
                          source_id: Optional[int] = None) -> Dict:
        """Analyze sentiment of text content"""
        # Simple rule-based sentiment analysis
        sentiment_score = self._calculate_sentiment_score(text)
        sentiment_level = self._get_sentiment_level(sentiment_score)
        keywords = self._extract_keywords(text)
        topics = self._extract_topics(text)

        result = {
            "text_content": text,
            "sentiment_score": sentiment_score,
            "sentiment_level": sentiment_level.value,
            "keywords": keywords,
            "topics": topics,
            "analyzed_at": datetime.now().isoformat()
        }

        # Store analysis
        self.db.execute("""
            INSERT INTO sentiment_analysis
            (source_type, source_id, text_content, sentiment_score,
             sentiment_level, keywords, topics)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            source_type,
            source_id,
            text,
            sentiment_score,
            sentiment_level.value,
            json.dumps(keywords),
            json.dumps(topics)
        ])

        return result

    def _calculate_sentiment_score(self, text: str) -> float:
        """Calculate sentiment score from -1 (very negative) to 1 (very positive)"""
        text_lower = text.lower()

        # Positive words/phrases
        positive_words = [
            'excellent', 'amazing', 'great', 'wonderful', 'fantastic', 'perfect',
            'good', 'nice', 'happy', 'satisfied', 'pleased', 'recommend', 'best',
            'professional', 'quality', 'fast', 'quick', 'friendly', 'helpful',
            'clean', 'thorough', 'impressive', 'outstanding', 'superb', 'love'
        ]

        # Negative words/phrases
        negative_words = [
            'terrible', 'awful', 'horrible', 'bad', 'poor', 'worst', 'disappointed',
            'unhappy', 'angry', 'frustrated', 'rude', 'unprofessional', 'slow',
            'expensive', 'overpriced', 'damage', 'problem', 'issue', 'complaint',
            'never', 'avoid', 'waste', 'regret', 'scam', 'dishonest'
        ]

        # Intensifiers
        intensifiers = ['very', 'really', 'extremely', 'absolutely', 'totally', 'so']

        positive_count = 0
        negative_count = 0

        words = text_lower.split()

        for i, word in enumerate(words):
            # Check for intensifier before word
            intensity = 1.5 if i > 0 and words[i-1] in intensifiers else 1.0

            if word in positive_words:
                positive_count += intensity
            elif word in negative_words:
                negative_count += intensity

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        score = (positive_count - negative_count) / max(total, 1)
        return round(max(-1, min(1, score)), 3)

    def _get_sentiment_level(self, score: float) -> SentimentLevel:
        """Convert numeric score to sentiment level"""
        if score >= 0.5:
            return SentimentLevel.VERY_POSITIVE
        elif score >= 0.2:
            return SentimentLevel.POSITIVE
        elif score >= -0.2:
            return SentimentLevel.NEUTRAL
        elif score >= -0.5:
            return SentimentLevel.NEGATIVE
        else:
            return SentimentLevel.VERY_NEGATIVE

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract key terms from text"""
        # PDR-related keywords to look for
        pdr_terms = [
            'dent', 'ding', 'hail', 'damage', 'repair', 'paint', 'body',
            'hood', 'door', 'fender', 'roof', 'trunk', 'bumper',
            'estimate', 'price', 'cost', 'insurance', 'claim',
            'technician', 'service', 'appointment', 'schedule'
        ]

        text_lower = text.lower()
        found = []

        for term in pdr_terms:
            if term in text_lower:
                found.append(term)

        return found[:10]  # Limit to 10 keywords

    def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics from text"""
        topics = []
        text_lower = text.lower()

        # Service quality
        if any(w in text_lower for w in ['quality', 'professional', 'expert', 'skill']):
            topics.append('service_quality')

        # Pricing
        if any(w in text_lower for w in ['price', 'cost', 'expensive', 'cheap', 'fair', 'quote']):
            topics.append('pricing')

        # Speed/timing
        if any(w in text_lower for w in ['fast', 'quick', 'slow', 'wait', 'time', 'schedule']):
            topics.append('timing')

        # Customer service
        if any(w in text_lower for w in ['friendly', 'helpful', 'rude', 'customer', 'service', 'staff']):
            topics.append('customer_service')

        # Results
        if any(w in text_lower for w in ['result', 'finish', 'look', 'perfect', 'satisfied']):
            topics.append('results')

        return topics

    def get_sentiment_summary(self, source_type: Optional[str] = None,
                               days: int = 30) -> Dict:
        """Get sentiment analysis summary"""
        query = """
            SELECT
                sentiment_level,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score
            FROM sentiment_analysis
            WHERE analyzed_at >= DATE('now', ?)
        """
        params = [f'-{days} days']

        if source_type:
            query += " AND source_type = ?"
            params.append(source_type)

        query += " GROUP BY sentiment_level"

        results = self.db.execute(query, params)

        summary = {
            "period_days": days,
            "source_type": source_type,
            "distribution": {r['sentiment_level']: r['count'] for r in results},
            "average_score": sum(r['avg_score'] * r['count'] for r in results) / sum(r['count'] for r in results) if results else 0,
            "total_analyzed": sum(r['count'] for r in results)
        }

        return summary

    # ==================== AI DASHBOARD ====================

    def get_ai_dashboard(self) -> Dict:
        """Get comprehensive AI analytics dashboard"""
        return {
            "churn_summary": self._get_churn_summary(),
            "revenue_forecast": self._get_revenue_forecast_summary(),
            "active_anomalies": len(self.get_open_anomalies()),
            "active_patterns": len(self.get_active_patterns()),
            "active_insights": len(self.get_active_insights()),
            "pending_recommendations": len(self.get_pending_recommendations()),
            "sentiment_overview": self.get_sentiment_summary(days=30),
            "generated_at": datetime.now().isoformat()
        }

    def _get_churn_summary(self) -> Dict:
        """Get churn prediction summary"""
        results = self.db.execute("""
            SELECT
                risk_level,
                COUNT(*) as count
            FROM churn_predictions
            WHERE is_current = 1
            GROUP BY risk_level
        """)

        return {
            "by_risk_level": {r['risk_level']: r['count'] for r in results},
            "total_predictions": sum(r['count'] for r in results)
        }

    def _get_revenue_forecast_summary(self) -> Dict:
        """Get revenue forecast summary"""
        results = self.db.execute("""
            SELECT
                prediction_period,
                predicted_revenue,
                confidence_lower,
                confidence_upper
            FROM revenue_predictions
            WHERE prediction_date = (SELECT MAX(prediction_date) FROM revenue_predictions)
            ORDER BY start_date
            LIMIT 6
        """)

        return {
            "forecasts": results,
            "total_forecasted": sum(r['predicted_revenue'] for r in results)
        }
