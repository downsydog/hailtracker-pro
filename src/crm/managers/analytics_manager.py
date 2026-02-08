"""
Analytics Manager
PDR CRM Part 10 - Comprehensive Business Analytics & KPIs

PROVIDES:
- Executive dashboard metrics
- Revenue analytics
- Job pipeline analysis
- Tech performance
- Customer insights
- Trend analysis
- Business alerts
- Report generation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json


class AnalyticsManager:
    """
    Business analytics and KPI tracking

    Provides insights into shop performance
    """

    def __init__(self, db):
        """Initialize analytics manager with database connection"""
        self.db = db

    # ========================================================================
    # EXECUTIVE DASHBOARD
    # ========================================================================

    def get_executive_dashboard(
        self,
        period_days: int = 30
    ) -> Dict:
        """
        Get high-level executive dashboard

        Returns all key metrics in one view

        Args:
            period_days: Period for metrics (default 30 days)

        Returns:
            Dict with all KPIs
        """
        start_date = date.today() - timedelta(days=period_days)

        dashboard = {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': date.today().isoformat(),
                'days': period_days
            },
            'revenue': self._get_revenue_metrics(start_date),
            'jobs': self._get_job_metrics(start_date),
            'sales': self._get_sales_metrics(start_date),
            'operations': self._get_operations_metrics(start_date),
            'customers': self._get_customer_metrics(start_date),
            'alerts': self._get_alerts()
        }

        return dashboard

    def _get_revenue_metrics(self, start_date: date) -> Dict:
        """Revenue KPIs"""
        metrics = {}

        # Total revenue
        result = self.db.execute("""
            SELECT
                COUNT(*) as payment_count,
                COALESCE(SUM(total_amount), 0) as total,
                COALESCE(AVG(total_amount), 0) as avg_payment,
                COALESCE(SUM(insurance_portion), 0) as from_insurance,
                COALESCE(SUM(total_amount - COALESCE(insurance_portion, 0)), 0) as from_customers
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date >= ?
        """, (start_date.isoformat(),))

        row = result[0] if result else {}
        metrics['total'] = row.get('total') or 0
        metrics['count'] = row.get('payment_count') or 0
        metrics['average'] = row.get('avg_payment') or 0
        metrics['from_insurance'] = row.get('from_insurance') or 0
        metrics['from_customers'] = row.get('from_customers') or 0

        # Compare to previous period
        days_diff = (date.today() - start_date).days
        prev_start = start_date - timedelta(days=days_diff)

        prev_result = self.db.execute("""
            SELECT COALESCE(SUM(total_amount), 0) as total
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date >= ?
              AND payment_date < ?
        """, (prev_start.isoformat(), start_date.isoformat()))

        prev_total = prev_result[0]['total'] if prev_result else 0

        if prev_total > 0:
            metrics['growth_pct'] = ((metrics['total'] - prev_total) / prev_total) * 100
        else:
            metrics['growth_pct'] = 0 if metrics['total'] == 0 else 100

        # Daily average
        days = days_diff or 1
        metrics['daily_average'] = metrics['total'] / days

        return metrics

    def _get_job_metrics(self, start_date: date) -> Dict:
        """Job pipeline KPIs"""
        metrics = {}

        # Total jobs created
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND created_at >= ?
        """, (start_date.isoformat(),))
        metrics['created'] = result[0]['count'] if result else 0

        # Completed jobs
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND completed_at >= ?
        """, (start_date.isoformat(),))
        metrics['completed'] = result[0]['count'] if result else 0

        # By status (active jobs)
        result = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND status NOT IN ('COMPLETED', 'PAID')
            GROUP BY status
        """)
        metrics['active_by_status'] = {row['status']: row['count'] for row in result}

        # Total active
        metrics['active_total'] = sum(metrics['active_by_status'].values())

        # Average cycle time
        result = self.db.execute("""
            SELECT AVG(
                JULIANDAY(completed_at) - JULIANDAY(created_at)
            ) as avg_days
            FROM jobs
            WHERE deleted_at IS NULL
              AND completed_at IS NOT NULL
              AND completed_at >= ?
        """, (start_date.isoformat(),))
        metrics['avg_cycle_time_days'] = round(result[0]['avg_days'] or 0, 1) if result else 0

        # Completion rate
        if metrics['created'] > 0:
            metrics['completion_rate'] = (metrics['completed'] / metrics['created']) * 100
        else:
            metrics['completion_rate'] = 0

        return metrics

    def _get_sales_metrics(self, start_date: date) -> Dict:
        """Sales and conversion KPIs"""
        metrics = {}

        # Total leads
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND created_at >= ?
        """, (start_date.isoformat(),))
        metrics['total_leads'] = result[0]['count'] if result else 0

        # Converted leads
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND status = 'CONVERTED'
              AND created_at >= ?
        """, (start_date.isoformat(),))
        metrics['converted_leads'] = result[0]['count'] if result else 0

        # Conversion rate
        if metrics['total_leads'] > 0:
            metrics['conversion_rate'] = (metrics['converted_leads'] / metrics['total_leads']) * 100
        else:
            metrics['conversion_rate'] = 0

        # By source
        result = self.db.execute("""
            SELECT source, COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND created_at >= ?
            GROUP BY source
        """, (start_date.isoformat(),))
        metrics['leads_by_source'] = {row['source']: row['count'] for row in result}

        # Hot leads (need follow-up)
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND status IN ('NEW', 'CONTACTED', 'QUALIFIED')
              AND temperature = 'HOT'
        """)
        metrics['hot_leads'] = result[0]['count'] if result else 0

        return metrics

    def _get_operations_metrics(self, start_date: date) -> Dict:
        """Operations KPIs"""
        metrics = {}

        # Tech utilization
        result = self.db.execute("""
            SELECT
                COUNT(DISTINCT t.id) as tech_count,
                COALESCE(SUM(t.max_jobs_concurrent), 0) as total_capacity
            FROM technicians t
            WHERE t.deleted_at IS NULL
              AND t.status = 'ACTIVE'
        """)

        row = result[0] if result else {}
        metrics['tech_count'] = row.get('tech_count') or 0
        metrics['total_capacity'] = row.get('total_capacity') or 0

        # Active jobs assigned to techs
        result = self.db.execute("""
            SELECT COUNT(DISTINCT j.id) as active_jobs
            FROM jobs j
            WHERE j.deleted_at IS NULL
              AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
              AND j.assigned_tech_id IS NOT NULL
        """)
        metrics['active_jobs'] = result[0]['active_jobs'] if result else 0

        if metrics['total_capacity'] > 0:
            metrics['utilization_pct'] = (metrics['active_jobs'] / metrics['total_capacity']) * 100
        else:
            metrics['utilization_pct'] = 0

        # Jobs needing attention (overdue)
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND status NOT IN ('COMPLETED', 'PAID')
              AND (
                  (scheduled_drop_off < datetime('now') AND status = 'WAITING_DROP_OFF')
                  OR (estimated_completion_date < date('now') AND status = 'IN_PROGRESS')
              )
        """)
        metrics['needs_attention'] = result[0]['count'] if result else 0

        # Insurance claims needing follow-up
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
              AND status NOT IN ('APPROVED', 'PAID', 'CLOSED')
              AND (
                  last_contact_date IS NULL
                  OR JULIANDAY('now') - JULIANDAY(last_contact_date) >= 1
              )
        """)
        metrics['claims_need_followup'] = result[0]['count'] if result else 0

        return metrics

    def _get_customer_metrics(self, start_date: date) -> Dict:
        """Customer KPIs"""
        metrics = {}

        # New customers
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE deleted_at IS NULL
              AND (customer_since >= ? OR created_at >= ?)
        """, (start_date.isoformat(), start_date.isoformat()))
        metrics['new_customers'] = result[0]['count'] if result else 0

        # Total active customers
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM customers
            WHERE deleted_at IS NULL
              AND status = 'ACTIVE'
        """)
        metrics['total_active'] = result[0]['count'] if result else 0

        # Repeat customers (2+ jobs)
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM (
                SELECT customer_id, COUNT(*) as job_count
                FROM jobs
                WHERE deleted_at IS NULL
                  AND status IN ('COMPLETED', 'PAID')
                GROUP BY customer_id
                HAVING job_count >= 2
            )
        """)
        metrics['repeat_customers'] = result[0]['count'] if result else 0

        # Repeat rate
        if metrics['total_active'] > 0:
            metrics['repeat_rate'] = (metrics['repeat_customers'] / metrics['total_active']) * 100
        else:
            metrics['repeat_rate'] = 0

        return metrics

    def _get_alerts(self) -> List[Dict]:
        """Business alerts"""
        alerts = []

        # Overdue jobs
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM jobs
            WHERE deleted_at IS NULL
              AND status NOT IN ('COMPLETED', 'PAID')
              AND estimated_completion_date IS NOT NULL
              AND estimated_completion_date < date('now')
        """)

        if result and result[0]['count'] > 0:
            alerts.append({
                'type': 'OVERDUE_JOBS',
                'severity': 'HIGH',
                'count': result[0]['count'],
                'message': f"{result[0]['count']} job(s) past estimated completion"
            })

        # Insurance claims stalled
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM insurance_claims
            WHERE deleted_at IS NULL
              AND status IN ('WAITING_ADJUSTER', 'WAITING_APPROVAL')
              AND last_contact_date IS NOT NULL
              AND JULIANDAY('now') - JULIANDAY(last_contact_date) >= 3
        """)

        if result and result[0]['count'] > 0:
            alerts.append({
                'type': 'STALLED_CLAIMS',
                'severity': 'MEDIUM',
                'count': result[0]['count'],
                'message': f"{result[0]['count']} insurance claim(s) with no response in 3+ days"
            })

        # Parts needed
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM parts
            WHERE deleted_at IS NULL
              AND in_stock <= reorder_level
              AND reorder_level > 0
        """)

        if result and result[0]['count'] > 0:
            alerts.append({
                'type': 'LOW_PARTS',
                'severity': 'LOW',
                'count': result[0]['count'],
                'message': f"{result[0]['count']} part(s) need reordering"
            })

        # Hot leads without follow-up
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND temperature = 'HOT'
              AND status IN ('NEW', 'CONTACTED')
              AND (
                  next_follow_up_date IS NULL
                  OR next_follow_up_date <= date('now')
              )
        """)

        if result and result[0]['count'] > 0:
            alerts.append({
                'type': 'HOT_LEADS',
                'severity': 'MEDIUM',
                'count': result[0]['count'],
                'message': f"{result[0]['count']} hot lead(s) need follow-up"
            })

        return alerts

    # ========================================================================
    # REVENUE ANALYTICS
    # ========================================================================

    def get_revenue_trend(
        self,
        period: str = 'DAILY',
        days: int = 30
    ) -> List[Dict]:
        """
        Get revenue trend over time

        Args:
            period: DAILY, WEEKLY, MONTHLY
            days: Number of days to analyze

        Returns:
            List of data points for charting
        """
        start_date = date.today() - timedelta(days=days)

        if period == 'DAILY':
            query = """
                SELECT
                    DATE(payment_date) as date,
                    COALESCE(SUM(total_amount), 0) as revenue,
                    COUNT(*) as payment_count
                FROM payments
                WHERE status != 'BOUNCED'
                  AND payment_date >= ?
                GROUP BY DATE(payment_date)
                ORDER BY date
            """
        elif period == 'WEEKLY':
            query = """
                SELECT
                    DATE(payment_date, 'weekday 0', '-6 days') as date,
                    COALESCE(SUM(total_amount), 0) as revenue,
                    COUNT(*) as payment_count
                FROM payments
                WHERE status != 'BOUNCED'
                  AND payment_date >= ?
                GROUP BY DATE(payment_date, 'weekday 0', '-6 days')
                ORDER BY date
            """
        else:  # MONTHLY
            query = """
                SELECT
                    DATE(payment_date, 'start of month') as date,
                    COALESCE(SUM(total_amount), 0) as revenue,
                    COUNT(*) as payment_count
                FROM payments
                WHERE status != 'BOUNCED'
                  AND payment_date >= ?
                GROUP BY DATE(payment_date, 'start of month')
                ORDER BY date
            """

        results = self.db.execute(query, (start_date.isoformat(),))

        return [
            {
                'date': row['date'],
                'revenue': round(row['revenue'] or 0, 2),
                'count': row['payment_count']
            }
            for row in results
        ]

    def get_revenue_by_source(self, days: int = 30) -> Dict:
        """Revenue breakdown by source"""
        start_date = date.today() - timedelta(days=days)

        result = self.db.execute("""
            SELECT
                payer_type,
                COALESCE(SUM(total_amount), 0) as revenue,
                COUNT(*) as count
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date >= ?
            GROUP BY payer_type
        """, (start_date.isoformat(),))

        return {
            row['payer_type'] or 'UNKNOWN': {
                'revenue': round(row['revenue'], 2),
                'count': row['count']
            }
            for row in result
        }

    def get_revenue_by_job_type(self, days: int = 30) -> Dict:
        """Revenue breakdown by job type"""
        start_date = date.today() - timedelta(days=days)

        result = self.db.execute("""
            SELECT
                j.job_type,
                COALESCE(SUM(p.total_amount), 0) as revenue,
                COUNT(DISTINCT j.id) as job_count
            FROM payments p
            JOIN jobs j ON j.id = p.job_id
            WHERE p.status != 'BOUNCED'
              AND p.payment_date >= ?
            GROUP BY j.job_type
        """, (start_date.isoformat(),))

        return {
            row['job_type'] or 'OTHER': {
                'revenue': round(row['revenue'], 2),
                'job_count': row['job_count']
            }
            for row in result
        }

    # ========================================================================
    # JOB PIPELINE ANALYTICS
    # ========================================================================

    def get_job_pipeline(self) -> Dict:
        """
        Get job pipeline by stage

        Returns counts and values at each stage
        """
        from .job_manager import JobManager

        pipeline = {}

        for category, statuses in JobManager.STATUS_CATEGORIES.items():
            placeholders = ','.join(['?'] * len(statuses))

            result = self.db.execute(f"""
                SELECT
                    COUNT(*) as job_count,
                    COALESCE(SUM(e.total), 0) as total_value
                FROM jobs j
                LEFT JOIN estimates e ON e.job_id = j.id AND e.status = 'APPROVED'
                WHERE j.deleted_at IS NULL
                  AND j.status IN ({placeholders})
            """, tuple(statuses))

            row = result[0] if result else {}
            pipeline[category] = {
                'count': row.get('job_count') or 0,
                'value': round(row.get('total_value') or 0, 2)
            }

        return pipeline

    def get_job_status_summary(self) -> List[Dict]:
        """Get summary of jobs by individual status"""
        result = self.db.execute("""
            SELECT
                status,
                COUNT(*) as count,
                COALESCE(SUM(total_estimate), 0) as total_value
            FROM jobs
            WHERE deleted_at IS NULL
              AND status NOT IN ('COMPLETED', 'INVOICED', 'PAID')
            GROUP BY status
            ORDER BY
                CASE status
                    WHEN 'NEW' THEN 1
                    WHEN 'WAITING_DROP_OFF' THEN 2
                    WHEN 'DROPPED_OFF' THEN 3
                    WHEN 'WAITING_WRITEUP' THEN 4
                    WHEN 'ESTIMATE_CREATED' THEN 5
                    WHEN 'WAITING_INSURANCE' THEN 6
                    WHEN 'WAITING_ADJUSTER' THEN 7
                    WHEN 'ADJUSTER_SCHEDULED' THEN 8
                    WHEN 'ADJUSTER_INSPECTED' THEN 9
                    WHEN 'WAITING_APPROVAL' THEN 10
                    WHEN 'APPROVED' THEN 11
                    WHEN 'WAITING_PARTS' THEN 12
                    WHEN 'PARTS_ORDERED' THEN 13
                    WHEN 'PARTS_RECEIVED' THEN 14
                    WHEN 'ASSIGNED_TO_TECH' THEN 15
                    WHEN 'IN_PROGRESS' THEN 16
                    WHEN 'TECH_COMPLETE' THEN 17
                    WHEN 'WAITING_QC' THEN 18
                    WHEN 'QC_COMPLETE' THEN 19
                    WHEN 'WAITING_DETAIL' THEN 20
                    WHEN 'DETAIL_COMPLETE' THEN 21
                    WHEN 'READY_FOR_PICKUP' THEN 22
                    ELSE 99
                END
        """)

        return [
            {
                'status': row['status'],
                'count': row['count'],
                'value': round(row['total_value'], 2)
            }
            for row in result
        ]

    def get_conversion_funnel(self, days: int = 30) -> Dict:
        """
        Get sales funnel conversion rates

        Lead -> Qualified -> Customer -> Job -> Paid
        """
        start_date = date.today() - timedelta(days=days)

        funnel = {}

        # Total leads
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND created_at >= ?
        """, (start_date.isoformat(),))
        funnel['leads'] = result[0]['count'] if result else 0

        # Qualified leads
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND status IN ('QUALIFIED', 'CONVERTED')
              AND created_at >= ?
        """, (start_date.isoformat(),))
        funnel['qualified'] = result[0]['count'] if result else 0

        # Converted to customer
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM leads
            WHERE deleted_at IS NULL
              AND status = 'CONVERTED'
              AND created_at >= ?
        """, (start_date.isoformat(),))
        funnel['converted'] = result[0]['count'] if result else 0

        # Jobs created (from new customers in period)
        result = self.db.execute("""
            SELECT COUNT(DISTINCT j.id) as count
            FROM jobs j
            JOIN customers c ON c.id = j.customer_id
            WHERE j.deleted_at IS NULL
              AND j.created_at >= ?
        """, (start_date.isoformat(),))
        funnel['jobs'] = result[0]['count'] if result else 0

        # Jobs paid
        result = self.db.execute("""
            SELECT COUNT(DISTINCT j.id) as count
            FROM jobs j
            WHERE j.deleted_at IS NULL
              AND j.status = 'PAID'
              AND j.completed_at >= ?
        """, (start_date.isoformat(),))
        funnel['paid'] = result[0]['count'] if result else 0

        # Calculate conversion rates
        if funnel['leads'] > 0:
            funnel['lead_to_qualified_pct'] = round((funnel['qualified'] / funnel['leads']) * 100, 1)
            funnel['lead_to_customer_pct'] = round((funnel['converted'] / funnel['leads']) * 100, 1)
            funnel['lead_to_paid_pct'] = round((funnel['paid'] / funnel['leads']) * 100, 1)
        else:
            funnel['lead_to_qualified_pct'] = 0
            funnel['lead_to_customer_pct'] = 0
            funnel['lead_to_paid_pct'] = 0

        return funnel

    # ========================================================================
    # TECH PERFORMANCE
    # ========================================================================

    def get_tech_leaderboard(self, days: int = 30) -> List[Dict]:
        """
        Get tech performance rankings

        Ranked by jobs completed
        """
        start_date = date.today() - timedelta(days=days)

        query = """
            SELECT
                t.id,
                t.first_name || ' ' || t.last_name as tech_name,
                t.skill_level,
                COUNT(DISTINCT CASE WHEN j.completed_at >= ? THEN j.id END) as jobs_completed,
                COALESCE(SUM(CASE WHEN j.completed_at >= ? THEN j.estimated_hours END), 0) as total_hours,
                COALESCE(AVG(CASE WHEN j.completed_at >= ? THEN j.estimated_hours END), 0) as avg_hours_per_job,
                COALESCE(SUM(CASE WHEN p.payment_date >= ? THEN p.tech_cut END), 0) as total_earnings
            FROM technicians t
            LEFT JOIN jobs j ON j.assigned_tech_id = t.id
                AND j.deleted_at IS NULL
            LEFT JOIN payments p ON p.job_id = j.id
                AND p.status != 'BOUNCED'
            WHERE t.deleted_at IS NULL
              AND t.status = 'ACTIVE'
            GROUP BY t.id
            ORDER BY jobs_completed DESC, total_hours DESC
        """

        results = self.db.execute(query, (
            start_date.isoformat(),
            start_date.isoformat(),
            start_date.isoformat(),
            start_date.isoformat()
        ))

        return [
            {
                'rank': i + 1,
                'tech_id': row['id'],
                'tech_name': row['tech_name'],
                'skill_level': row['skill_level'],
                'jobs_completed': row['jobs_completed'],
                'total_hours': round(row['total_hours'] or 0, 1),
                'avg_hours': round(row['avg_hours_per_job'] or 0, 1),
                'earnings': round(row['total_earnings'] or 0, 2)
            }
            for i, row in enumerate(results)
        ]

    def get_tech_performance_detail(self, tech_id: int, days: int = 30) -> Dict:
        """Get detailed performance metrics for a specific tech"""
        start_date = date.today() - timedelta(days=days)

        # Basic info
        result = self.db.execute("""
            SELECT
                t.first_name || ' ' || t.last_name as tech_name,
                t.skill_level,
                t.max_jobs_concurrent
            FROM technicians t
            WHERE t.id = ?
        """, (tech_id,))

        if not result:
            return {}

        tech_info = result[0]

        # Jobs stats
        jobs_result = self.db.execute("""
            SELECT
                COUNT(CASE WHEN status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS') THEN 1 END) as active_jobs,
                COUNT(CASE WHEN completed_at >= ? THEN 1 END) as completed_jobs,
                COALESCE(SUM(CASE WHEN completed_at >= ? THEN estimated_hours END), 0) as total_hours,
                COALESCE(AVG(CASE WHEN completed_at >= ?
                    THEN JULIANDAY(completed_at) - JULIANDAY(assigned_at) END), 0) as avg_turnaround_days
            FROM jobs
            WHERE assigned_tech_id = ?
              AND deleted_at IS NULL
        """, (start_date.isoformat(), start_date.isoformat(), start_date.isoformat(), tech_id))

        jobs_stats = jobs_result[0] if jobs_result else {}

        # Earnings
        earnings_result = self.db.execute("""
            SELECT COALESCE(SUM(p.tech_cut), 0) as total_earnings
            FROM payments p
            JOIN jobs j ON j.id = p.job_id
            WHERE j.assigned_tech_id = ?
              AND p.payment_date >= ?
              AND p.status != 'BOUNCED'
        """, (tech_id, start_date.isoformat()))

        earnings = earnings_result[0]['total_earnings'] if earnings_result else 0

        return {
            'tech_id': tech_id,
            'tech_name': tech_info['tech_name'],
            'skill_level': tech_info['skill_level'],
            'max_concurrent': tech_info['max_jobs_concurrent'],
            'active_jobs': jobs_stats.get('active_jobs') or 0,
            'completed_jobs': jobs_stats.get('completed_jobs') or 0,
            'total_hours': round(jobs_stats.get('total_hours') or 0, 1),
            'avg_turnaround_days': round(jobs_stats.get('avg_turnaround_days') or 0, 1),
            'earnings': round(earnings, 2),
            'period_days': days
        }

    # ========================================================================
    # CUSTOMER ANALYTICS
    # ========================================================================

    def get_customer_acquisition(self, days: int = 30) -> Dict:
        """Get customer acquisition metrics"""
        start_date = date.today() - timedelta(days=days)

        # New customers by source
        result = self.db.execute("""
            SELECT
                source,
                COUNT(*) as count
            FROM customers
            WHERE deleted_at IS NULL
              AND created_at >= ?
            GROUP BY source
        """, (start_date.isoformat(),))

        by_source = {row['source'] or 'UNKNOWN': row['count'] for row in result}

        # Total new
        total_new = sum(by_source.values())

        # Customer lifetime value (average revenue per customer)
        result = self.db.execute("""
            SELECT
                AVG(customer_total) as avg_ltv
            FROM (
                SELECT
                    c.id,
                    COALESCE(SUM(p.total_amount), 0) as customer_total
                FROM customers c
                LEFT JOIN jobs j ON j.customer_id = c.id AND j.deleted_at IS NULL
                LEFT JOIN payments p ON p.job_id = j.id AND p.status != 'BOUNCED'
                WHERE c.deleted_at IS NULL
                GROUP BY c.id
                HAVING customer_total > 0
            )
        """)

        avg_ltv = result[0]['avg_ltv'] if result and result[0]['avg_ltv'] else 0

        return {
            'new_customers': total_new,
            'by_source': by_source,
            'avg_lifetime_value': round(avg_ltv, 2),
            'period_days': days
        }

    def get_top_customers(self, limit: int = 10) -> List[Dict]:
        """Get top customers by revenue"""
        result = self.db.execute("""
            SELECT
                c.id,
                c.first_name || ' ' || c.last_name as customer_name,
                c.company_name,
                COUNT(DISTINCT j.id) as total_jobs,
                COALESCE(SUM(p.total_amount), 0) as total_revenue
            FROM customers c
            LEFT JOIN jobs j ON j.customer_id = c.id AND j.deleted_at IS NULL
            LEFT JOIN payments p ON p.job_id = j.id AND p.status != 'BOUNCED'
            WHERE c.deleted_at IS NULL
            GROUP BY c.id
            HAVING total_revenue > 0
            ORDER BY total_revenue DESC
            LIMIT ?
        """, (limit,))

        return [
            {
                'rank': i + 1,
                'customer_id': row['id'],
                'customer_name': row['customer_name'],
                'company_name': row['company_name'],
                'total_jobs': row['total_jobs'],
                'total_revenue': round(row['total_revenue'], 2)
            }
            for i, row in enumerate(result)
        ]

    # ========================================================================
    # TREND ANALYSIS
    # ========================================================================

    def get_job_trend(self, period: str = 'DAILY', days: int = 30) -> List[Dict]:
        """Get job creation trend over time"""
        start_date = date.today() - timedelta(days=days)

        if period == 'DAILY':
            date_expr = "DATE(created_at)"
        elif period == 'WEEKLY':
            date_expr = "DATE(created_at, 'weekday 0', '-6 days')"
        else:  # MONTHLY
            date_expr = "DATE(created_at, 'start of month')"

        result = self.db.execute(f"""
            SELECT
                {date_expr} as date,
                COUNT(*) as jobs_created,
                COUNT(CASE WHEN job_type = 'HAIL' THEN 1 END) as hail_jobs,
                COUNT(CASE WHEN job_type = 'PDR' THEN 1 END) as pdr_jobs
            FROM jobs
            WHERE deleted_at IS NULL
              AND created_at >= ?
            GROUP BY {date_expr}
            ORDER BY date
        """, (start_date.isoformat(),))

        return [
            {
                'date': row['date'],
                'total': row['jobs_created'],
                'hail': row['hail_jobs'],
                'pdr': row['pdr_jobs']
            }
            for row in result
        ]

    # ========================================================================
    # REPORT GENERATION
    # ========================================================================

    def generate_executive_report(self, days: int = 30) -> str:
        """
        Generate formatted executive report

        Returns text report ready for email/PDF
        """
        dashboard = self.get_executive_dashboard(days)

        lines = []
        lines.append("=" * 70)
        lines.append(f"EXECUTIVE DASHBOARD REPORT")
        lines.append(f"Period: Last {days} Days ({dashboard['period']['start_date']} to {dashboard['period']['end_date']})")
        lines.append("=" * 70)
        lines.append("")

        # Revenue section
        lines.append("REVENUE")
        lines.append("-" * 70)
        lines.append(f"  Total Revenue:              ${dashboard['revenue']['total']:>15,.2f}")
        lines.append(f"  Average Transaction:        ${dashboard['revenue']['average']:>15,.2f}")
        lines.append(f"  Daily Average:              ${dashboard['revenue']['daily_average']:>15,.2f}")
        lines.append(f"  Growth vs Previous Period:  {dashboard['revenue']['growth_pct']:>15.1f}%")
        lines.append(f"  From Insurance:             ${dashboard['revenue']['from_insurance']:>15,.2f}")
        lines.append(f"  From Customers:             ${dashboard['revenue']['from_customers']:>15,.2f}")
        lines.append("")

        # Jobs section
        lines.append("JOBS")
        lines.append("-" * 70)
        lines.append(f"  Jobs Created:               {dashboard['jobs']['created']:>15d}")
        lines.append(f"  Jobs Completed:             {dashboard['jobs']['completed']:>15d}")
        lines.append(f"  Active Jobs:                {dashboard['jobs']['active_total']:>15d}")
        lines.append(f"  Completion Rate:            {dashboard['jobs']['completion_rate']:>14.1f}%")
        lines.append(f"  Avg Cycle Time:             {dashboard['jobs']['avg_cycle_time_days']:>13.1f} days")
        lines.append("")

        # Sales section
        lines.append("SALES & LEADS")
        lines.append("-" * 70)
        lines.append(f"  Total Leads:                {dashboard['sales']['total_leads']:>15d}")
        lines.append(f"  Converted:                  {dashboard['sales']['converted_leads']:>15d}")
        lines.append(f"  Conversion Rate:            {dashboard['sales']['conversion_rate']:>14.1f}%")
        lines.append(f"  Hot Leads (Need Follow-up): {dashboard['sales']['hot_leads']:>15d}")
        lines.append("")

        # Operations section
        lines.append("OPERATIONS")
        lines.append("-" * 70)
        lines.append(f"  Active Technicians:         {dashboard['operations']['tech_count']:>15d}")
        lines.append(f"  Total Capacity:             {dashboard['operations']['total_capacity']:>15d} jobs")
        lines.append(f"  Utilization:                {dashboard['operations']['utilization_pct']:>14.1f}%")
        lines.append(f"  Jobs Needing Attention:     {dashboard['operations']['needs_attention']:>15d}")
        lines.append(f"  Claims Need Follow-up:      {dashboard['operations']['claims_need_followup']:>15d}")
        lines.append("")

        # Customers section
        lines.append("CUSTOMERS")
        lines.append("-" * 70)
        lines.append(f"  New Customers:              {dashboard['customers']['new_customers']:>15d}")
        lines.append(f"  Total Active:               {dashboard['customers']['total_active']:>15d}")
        lines.append(f"  Repeat Customers:           {dashboard['customers']['repeat_customers']:>15d}")
        lines.append(f"  Repeat Rate:                {dashboard['customers']['repeat_rate']:>14.1f}%")
        lines.append("")

        # Alerts section
        if dashboard['alerts']:
            lines.append("ALERTS")
            lines.append("-" * 70)
            for alert in dashboard['alerts']:
                severity_marker = "!!!" if alert['severity'] == 'HIGH' else "!!" if alert['severity'] == 'MEDIUM' else "!"
                lines.append(f"  {severity_marker} [{alert['severity']}] {alert['message']}")
            lines.append("")

        lines.append("-" * 70)
        lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

        return "\n".join(lines)

    def generate_pipeline_report(self) -> str:
        """Generate formatted job pipeline report"""
        pipeline = self.get_job_pipeline()
        status_summary = self.get_job_status_summary()

        lines = []
        lines.append("=" * 70)
        lines.append("JOB PIPELINE REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Pipeline by category
        lines.append("PIPELINE BY STAGE")
        lines.append("-" * 70)
        lines.append(f"{'Stage':<20} {'Jobs':>10} {'Value':>15}")
        lines.append("-" * 70)

        total_jobs = 0
        total_value = 0
        for stage, data in pipeline.items():
            lines.append(f"{stage:<20} {data['count']:>10d} ${data['value']:>14,.2f}")
            total_jobs += data['count']
            total_value += data['value']

        lines.append("-" * 70)
        lines.append(f"{'TOTAL':<20} {total_jobs:>10d} ${total_value:>14,.2f}")
        lines.append("")

        # Detailed status breakdown
        lines.append("DETAILED STATUS BREAKDOWN")
        lines.append("-" * 70)
        for item in status_summary:
            lines.append(f"  {item['status']:<25} {item['count']:>5d} jobs  ${item['value']:>10,.2f}")

        return "\n".join(lines)

    def generate_tech_report(self, days: int = 30) -> str:
        """Generate formatted tech performance report"""
        leaderboard = self.get_tech_leaderboard(days)

        lines = []
        lines.append("=" * 70)
        lines.append(f"TECH PERFORMANCE REPORT (Last {days} Days)")
        lines.append("=" * 70)
        lines.append("")

        if not leaderboard:
            lines.append("No technician data available.")
            return "\n".join(lines)

        lines.append(f"{'Rank':<6} {'Technician':<20} {'Jobs':>8} {'Hours':>10} {'Earnings':>12}")
        lines.append("-" * 70)

        for tech in leaderboard:
            lines.append(
                f"#{tech['rank']:<5} {tech['tech_name']:<20} "
                f"{tech['jobs_completed']:>8d} {tech['total_hours']:>10.1f} "
                f"${tech['earnings']:>11,.2f}"
            )

        return "\n".join(lines)
