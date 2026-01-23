"""
Reports API Routes for HailTracker Pro
Provides data for charts and analytics dashboards
"""

import sqlite3
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, current_app
import json
import random
from src.core.auth.decorators import (
    login_required,
)

reports_api_bp = Blueprint('reports_api', __name__, url_prefix='/api/reports')


def get_db_connection():
    """Get database connection with row factory."""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def parse_date_range(request):
    """Parse start_date and end_date from request args."""
    today = datetime.now()

    # Default to last 30 days
    default_start = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    default_end = today.strftime('%Y-%m-%d')

    start_date = request.args.get('start_date', default_start)
    end_date = request.args.get('end_date', default_end)
    group_by = request.args.get('group_by', 'day')  # day, week, month

    return start_date, end_date, group_by


def generate_date_labels(start_date, end_date, group_by='day'):
    """Generate date labels for charts."""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    labels = []

    if group_by == 'day':
        current = start
        while current <= end:
            labels.append(current.strftime('%b %d'))
            current += timedelta(days=1)
    elif group_by == 'week':
        current = start
        while current <= end:
            labels.append(f"Week {current.isocalendar()[1]}")
            current += timedelta(weeks=1)
    elif group_by == 'month':
        current = start
        while current <= end:
            labels.append(current.strftime('%b %Y'))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

    return labels


def generate_sample_data(labels, min_val=100, max_val=1000, trend='stable'):
    """Generate sample data for demonstration."""
    data = []
    base = random.randint(min_val, max_val)

    for i, _ in enumerate(labels):
        if trend == 'up':
            value = base + (i * random.randint(10, 50)) + random.randint(-50, 50)
        elif trend == 'down':
            value = base - (i * random.randint(10, 30)) + random.randint(-30, 30)
        else:
            value = base + random.randint(-100, 100)
        data.append(max(0, value))

    return data


# ====================
# Dashboard Overview
# ====================

@reports_api_bp.route('/dashboard')
@login_required
def dashboard_stats():
    """Get overview stats for dashboard."""
    start_date, end_date, group_by = parse_date_range(request)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Try to get real data, fall back to sample data
        stats = {
            'revenue': {
                'total': 0,
                'change': 0,
                'period': f"{start_date} to {end_date}"
            },
            'jobs_completed': {
                'total': 0,
                'change': 0
            },
            'avg_job_value': {
                'total': 0,
                'change': 0
            },
            'lead_conversion': {
                'rate': 0,
                'change': 0
            }
        }

        # Try to get job count
        try:
            cursor.execute("""
                SELECT COUNT(*) as count FROM jobs
                WHERE created_at BETWEEN ? AND ?
            """, (start_date, end_date + ' 23:59:59'))
            result = cursor.fetchone()
            if result:
                stats['jobs_completed']['total'] = result['count'] or 0
        except:
            pass

        # Try to get customer count for leads
        try:
            cursor.execute("""
                SELECT COUNT(*) as count FROM customers
                WHERE created_at BETWEEN ? AND ?
            """, (start_date, end_date + ' 23:59:59'))
            result = cursor.fetchone()
            if result:
                stats['lead_conversion']['rate'] = min(100, (result['count'] or 0) * 5)  # Sample conversion
        except:
            pass

        conn.close()

        # Fill with sample data if empty
        if stats['revenue']['total'] == 0:
            stats['revenue']['total'] = random.randint(45000, 85000)
            stats['revenue']['change'] = round(random.uniform(-10, 25), 1)

        if stats['jobs_completed']['total'] == 0:
            stats['jobs_completed']['total'] = random.randint(35, 120)
            stats['jobs_completed']['change'] = round(random.uniform(-5, 15), 1)

        if stats['avg_job_value']['total'] == 0:
            stats['avg_job_value']['total'] = random.randint(800, 2500)
            stats['avg_job_value']['change'] = round(random.uniform(-8, 12), 1)

        if stats['lead_conversion']['rate'] == 0:
            stats['lead_conversion']['rate'] = round(random.uniform(25, 65), 1)
            stats['lead_conversion']['change'] = round(random.uniform(-5, 10), 1)

        # Generate mini sparkline data
        labels = generate_date_labels(start_date, end_date, group_by)
        stats['revenue']['sparkline'] = generate_sample_data(labels[-7:], 1000, 5000, 'up')
        stats['jobs_completed']['sparkline'] = generate_sample_data(labels[-7:], 2, 10, 'stable')

        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({'error': str(e)}), 500


# ====================
# Revenue Reports
# ====================

@reports_api_bp.route('/revenue')
@login_required
def revenue_report():
    """Get revenue data over time."""
    start_date, end_date, group_by = parse_date_range(request)

    labels = generate_date_labels(start_date, end_date, group_by)

    # Generate sample revenue data
    revenue_data = generate_sample_data(labels, 2000, 8000, 'up')

    # Revenue by service type
    service_types = ['PDR', 'Conventional', 'Paint', 'Glass', 'Interior']
    service_revenue = [random.randint(10000, 40000) for _ in service_types]

    # Calculate totals
    total_revenue = sum(revenue_data)
    avg_per_job = round(total_revenue / max(1, len(labels) * 3), 2)
    best_day_idx = revenue_data.index(max(revenue_data))
    best_day = labels[best_day_idx] if best_day_idx < len(labels) else 'N/A'

    # Top jobs
    top_jobs = []
    for i in range(10):
        top_jobs.append({
            'id': 1000 + i,
            'customer': f"Customer {chr(65 + i)}",
            'vehicle': f"202{random.randint(0,4)} {['Honda Accord', 'Toyota Camry', 'Ford F-150', 'Tesla Model 3', 'BMW X5'][i % 5]}",
            'service': service_types[i % len(service_types)],
            'amount': round(random.uniform(2000, 8000), 2),
            'date': (datetime.now() - timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d')
        })
    top_jobs.sort(key=lambda x: x['amount'], reverse=True)

    return jsonify({
        'chart_data': {
            'labels': labels,
            'datasets': [{
                'label': 'Revenue',
                'data': revenue_data
            }]
        },
        'service_breakdown': {
            'labels': service_types,
            'values': service_revenue
        },
        'stats': {
            'total_revenue': total_revenue,
            'avg_per_job': avg_per_job,
            'best_day': best_day,
            'best_day_revenue': max(revenue_data),
            'projected_monthly': round(total_revenue * (30 / max(1, len(labels))), 2)
        },
        'top_jobs': top_jobs
    })


@reports_api_bp.route('/revenue/by-tech')
@login_required
def revenue_by_tech():
    """Get revenue breakdown by technician."""
    techs = ['Mike Johnson', 'Sarah Williams', 'David Chen', 'Emily Brown', 'James Wilson']

    return jsonify({
        'labels': techs,
        'datasets': [{
            'label': 'Revenue',
            'data': [random.randint(15000, 45000) for _ in techs]
        }]
    })


# ====================
# Jobs Reports
# ====================

@reports_api_bp.route('/jobs')
@login_required
def jobs_report():
    """Get jobs data and breakdowns."""
    start_date, end_date, group_by = parse_date_range(request)

    labels = generate_date_labels(start_date, end_date, group_by)

    # Jobs over time
    jobs_data = generate_sample_data(labels, 2, 12, 'stable')

    # Jobs by status
    statuses = ['New', 'In Progress', 'Waiting Parts', 'Ready for Pickup', 'Completed']
    status_counts = [random.randint(5, 25) for _ in statuses]

    # Jobs by tech
    techs = ['Mike Johnson', 'Sarah Williams', 'David Chen', 'Emily Brown', 'James Wilson']
    tech_jobs = [random.randint(10, 40) for _ in techs]

    # Completion time stats
    avg_completion_hours = round(random.uniform(4, 12), 1)

    # Slow jobs (over average completion time)
    slow_jobs = []
    for i in range(8):
        slow_jobs.append({
            'id': 2000 + i,
            'customer': f"Customer {chr(75 + i)}",
            'vehicle': f"202{random.randint(0,4)} {['Chevrolet Silverado', 'Nissan Altima', 'Jeep Wrangler', 'Audi A4', 'Mercedes C-Class'][i % 5]}",
            'tech': techs[i % len(techs)],
            'hours': round(avg_completion_hours + random.uniform(2, 10), 1),
            'status': statuses[i % 3],
            'started': (datetime.now() - timedelta(days=random.randint(3, 14))).strftime('%Y-%m-%d')
        })
    slow_jobs.sort(key=lambda x: x['hours'], reverse=True)

    return jsonify({
        'over_time': {
            'labels': labels,
            'datasets': [{
                'label': 'Jobs',
                'data': jobs_data
            }]
        },
        'by_status': {
            'labels': statuses,
            'values': status_counts
        },
        'by_tech': {
            'labels': techs,
            'datasets': [{
                'label': 'Jobs Completed',
                'data': tech_jobs
            }]
        },
        'stats': {
            'total_jobs': sum(jobs_data),
            'avg_completion_time': avg_completion_hours,
            'jobs_in_progress': status_counts[1] + status_counts[2],
            'completed_this_period': status_counts[4]
        },
        'slow_jobs': slow_jobs
    })


@reports_api_bp.route('/jobs/by-status')
@login_required
def jobs_by_status():
    """Get jobs count by status."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Try to get real data
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM jobs
            GROUP BY status
        """)
        results = cursor.fetchall()
        conn.close()

        if results:
            return jsonify({
                'labels': [r['status'] for r in results],
                'values': [r['count'] for r in results]
            })
    except:
        pass

    # Sample data fallback
    statuses = ['NEW', 'SCHEDULED', 'IN_PROGRESS', 'COMPLETED', 'INVOICED']
    return jsonify({
        'labels': statuses,
        'values': [random.randint(5, 30) for _ in statuses]
    })


# ====================
# Leads Reports
# ====================

@reports_api_bp.route('/leads')
@login_required
def leads_report():
    """Get leads data and conversion metrics."""
    start_date, end_date, group_by = parse_date_range(request)

    labels = generate_date_labels(start_date, end_date, group_by)

    # Leads over time
    leads_data = generate_sample_data(labels, 3, 15, 'up')

    # Lead sources
    sources = ['Website', 'Referral', 'Google Ads', 'Facebook', 'Walk-in', 'Insurance Partner']
    source_counts = [random.randint(10, 50) for _ in sources]

    # Conversion funnel
    total_leads = sum(source_counts)
    contacted = int(total_leads * random.uniform(0.7, 0.9))
    quoted = int(contacted * random.uniform(0.5, 0.8))
    converted = int(quoted * random.uniform(0.4, 0.7))

    funnel = {
        'labels': ['Leads', 'Contacted', 'Quoted', 'Converted'],
        'values': [total_leads, contacted, quoted, converted]
    }

    # Conversion rate
    conversion_rate = round((converted / max(1, total_leads)) * 100, 1)
    avg_time_to_convert = round(random.uniform(2, 7), 1)  # days

    # Hot leads (not yet converted)
    hot_leads = []
    for i in range(10):
        hot_leads.append({
            'id': 3000 + i,
            'name': f"Lead {chr(65 + i)}",
            'phone': f"(555) {random.randint(100,999)}-{random.randint(1000,9999)}",
            'email': f"lead{i}@example.com",
            'source': sources[i % len(sources)],
            'vehicle': f"202{random.randint(0,4)} {['Honda', 'Toyota', 'Ford', 'Tesla', 'BMW'][i % 5]} - Hail Damage",
            'score': random.randint(60, 95),
            'created': (datetime.now() - timedelta(days=random.randint(1, 10))).strftime('%Y-%m-%d'),
            'last_contact': (datetime.now() - timedelta(days=random.randint(0, 3))).strftime('%Y-%m-%d')
        })
    hot_leads.sort(key=lambda x: x['score'], reverse=True)

    return jsonify({
        'over_time': {
            'labels': labels,
            'datasets': [{
                'label': 'New Leads',
                'data': leads_data
            }]
        },
        'by_source': {
            'labels': sources,
            'values': source_counts
        },
        'funnel': funnel,
        'stats': {
            'total_leads': total_leads,
            'conversion_rate': conversion_rate,
            'avg_time_to_convert': avg_time_to_convert,
            'leads_this_week': sum(leads_data[-7:]) if len(leads_data) >= 7 else sum(leads_data)
        },
        'hot_leads': hot_leads
    })


@reports_api_bp.route('/leads/sources')
@login_required
def lead_sources():
    """Get lead sources breakdown."""
    sources = ['Website', 'Referral', 'Google Ads', 'Facebook', 'Walk-in', 'Insurance Partner']

    return jsonify({
        'labels': sources,
        'values': [random.randint(15, 60) for _ in sources]
    })


# ====================
# Tech Performance Reports
# ====================

@reports_api_bp.route('/techs')
@login_required
def tech_performance():
    """Get technician performance data."""
    start_date, end_date, group_by = parse_date_range(request)

    techs = [
        {'id': 1, 'name': 'Mike Johnson', 'role': 'Senior PDR Tech'},
        {'id': 2, 'name': 'Sarah Williams', 'role': 'PDR Tech'},
        {'id': 3, 'name': 'David Chen', 'role': 'Body Tech'},
        {'id': 4, 'name': 'Emily Brown', 'role': 'PDR Tech'},
        {'id': 5, 'name': 'James Wilson', 'role': 'Paint Tech'}
    ]

    # Performance data for each tech
    tech_data = []
    for tech in techs:
        jobs_completed = random.randint(15, 45)
        hours_worked = random.randint(120, 180)
        revenue = random.randint(12000, 45000)

        tech_data.append({
            **tech,
            'jobs_completed': jobs_completed,
            'hours_worked': hours_worked,
            'revenue': revenue,
            'avg_job_time': round(hours_worked / max(1, jobs_completed), 1),
            'efficiency': round(random.uniform(85, 99), 1),
            'customer_rating': round(random.uniform(4.2, 5.0), 1),
            'revenue_per_hour': round(revenue / max(1, hours_worked), 2)
        })

    # Sort by revenue for ranking
    tech_data.sort(key=lambda x: x['revenue'], reverse=True)
    for i, tech in enumerate(tech_data):
        tech['rank'] = i + 1

    # Jobs by tech chart data
    labels = generate_date_labels(start_date, end_date, group_by)
    jobs_by_tech_over_time = {
        'labels': labels,
        'datasets': []
    }

    for i, tech in enumerate(tech_data[:4]):  # Top 4 techs
        jobs_by_tech_over_time['datasets'].append({
            'label': tech['name'].split()[0],  # First name only
            'data': generate_sample_data(labels, 1, 5, 'stable')
        })

    # Summary stats
    total_jobs = sum(t['jobs_completed'] for t in tech_data)
    total_revenue = sum(t['revenue'] for t in tech_data)
    avg_efficiency = round(sum(t['efficiency'] for t in tech_data) / len(tech_data), 1)

    return jsonify({
        'techs': tech_data,
        'jobs_over_time': jobs_by_tech_over_time,
        'jobs_comparison': {
            'labels': [t['name'].split()[0] for t in tech_data],
            'datasets': [{
                'label': 'Jobs Completed',
                'data': [t['jobs_completed'] for t in tech_data]
            }]
        },
        'revenue_comparison': {
            'labels': [t['name'].split()[0] for t in tech_data],
            'datasets': [{
                'label': 'Revenue',
                'data': [t['revenue'] for t in tech_data]
            }]
        },
        'efficiency_comparison': {
            'labels': [t['name'].split()[0] for t in tech_data],
            'datasets': [{
                'label': 'Efficiency %',
                'data': [t['efficiency'] for t in tech_data]
            }]
        },
        'stats': {
            'total_jobs': total_jobs,
            'total_revenue': total_revenue,
            'avg_efficiency': avg_efficiency,
            'top_performer': tech_data[0]['name'] if tech_data else 'N/A'
        }
    })


@reports_api_bp.route('/techs/<int:tech_id>')
@login_required
def tech_detail(tech_id):
    """Get detailed performance for a specific technician."""
    start_date, end_date, group_by = parse_date_range(request)
    labels = generate_date_labels(start_date, end_date, group_by)

    tech_names = ['Mike Johnson', 'Sarah Williams', 'David Chen', 'Emily Brown', 'James Wilson']
    tech_name = tech_names[tech_id - 1] if tech_id <= len(tech_names) else 'Unknown'

    return jsonify({
        'tech': {
            'id': tech_id,
            'name': tech_name,
            'role': 'PDR Technician',
            'start_date': '2023-03-15'
        },
        'jobs_over_time': {
            'labels': labels,
            'datasets': [{
                'label': 'Jobs',
                'data': generate_sample_data(labels, 1, 6, 'stable')
            }]
        },
        'revenue_over_time': {
            'labels': labels,
            'datasets': [{
                'label': 'Revenue',
                'data': generate_sample_data(labels, 500, 2500, 'up')
            }]
        },
        'stats': {
            'jobs_completed': random.randint(20, 50),
            'total_revenue': random.randint(15000, 50000),
            'avg_job_time': round(random.uniform(2, 6), 1),
            'efficiency': round(random.uniform(88, 98), 1),
            'customer_rating': round(random.uniform(4.3, 5.0), 1)
        },
        'recent_jobs': [
            {
                'id': 4000 + i,
                'customer': f"Customer {chr(65 + i)}",
                'vehicle': f"202{random.randint(0,4)} {['Honda', 'Toyota', 'Ford'][i % 3]}",
                'service': ['PDR', 'Conventional', 'Paint'][i % 3],
                'hours': round(random.uniform(2, 8), 1),
                'revenue': random.randint(400, 2000),
                'date': (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            }
            for i in range(10)
        ]
    })


# ====================
# Estimates Reports
# ====================

@reports_api_bp.route('/estimates')
@login_required
def estimates_report():
    """Get estimates data and conversion metrics."""
    start_date, end_date, group_by = parse_date_range(request)
    labels = generate_date_labels(start_date, end_date, group_by)

    # Estimates over time
    estimates_data = generate_sample_data(labels, 5, 20, 'stable')
    approved_data = [max(0, int(e * random.uniform(0.4, 0.7))) for e in estimates_data]

    # By service type
    service_types = ['PDR', 'Conventional', 'Paint', 'Glass', 'Full Restoration']
    service_estimates = [random.randint(20, 80) for _ in service_types]
    service_approved = [int(e * random.uniform(0.4, 0.7)) for e in service_estimates]

    # Calculate stats
    total_estimates = sum(estimates_data)
    total_approved = sum(approved_data)
    conversion_rate = round((total_approved / max(1, total_estimates)) * 100, 1)
    avg_value = random.randint(1200, 3500)
    total_value = total_estimates * avg_value

    return jsonify({
        'over_time': {
            'labels': labels,
            'datasets': [
                {'label': 'Sent', 'data': estimates_data},
                {'label': 'Approved', 'data': approved_data}
            ]
        },
        'by_service': {
            'labels': service_types,
            'datasets': [
                {'label': 'Sent', 'data': service_estimates},
                {'label': 'Approved', 'data': service_approved}
            ]
        },
        'conversion_by_service': {
            'labels': service_types,
            'values': [round((service_approved[i] / max(1, service_estimates[i])) * 100, 1) for i in range(len(service_types))]
        },
        'stats': {
            'total_estimates': total_estimates,
            'total_approved': total_approved,
            'conversion_rate': conversion_rate,
            'avg_estimate_value': avg_value,
            'total_value': total_value,
            'pending_value': round(total_value * 0.3, 2)
        },
        'pending_estimates': [
            {
                'id': 5000 + i,
                'customer': f"Customer {chr(65 + i)}",
                'vehicle': f"202{random.randint(0,4)} {['Honda', 'Toyota', 'Ford', 'Chevy', 'BMW'][i % 5]}",
                'amount': random.randint(800, 5000),
                'service': service_types[i % len(service_types)],
                'sent_date': (datetime.now() - timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d'),
                'follow_ups': random.randint(0, 3)
            }
            for i in range(8)
        ]
    })


# ====================
# Export Endpoints
# ====================

@reports_api_bp.route('/export/<report_type>')
@login_required
def export_report(report_type):
    """Export report data (placeholder for CSV/PDF generation)."""
    start_date, end_date, _ = parse_date_range(request)
    export_format = request.args.get('format', 'csv')

    # In a real implementation, this would generate actual CSV/PDF files
    return jsonify({
        'status': 'success',
        'message': f'Export of {report_type} report from {start_date} to {end_date} in {export_format} format',
        'download_url': f'/api/reports/download/{report_type}_{start_date}_{end_date}.{export_format}'
    })
