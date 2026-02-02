"""
Global Search API
=================
Unified search across leads, customers, jobs, and vehicles.

Endpoints:
- GET /api/search?q=<query>  - Search across all entities
"""

from flask import Blueprint, request, jsonify, g, current_app
from src.core.auth.decorators import login_required
from src.db.database import Database

search_api_bp = Blueprint('search_api', __name__, url_prefix='/api/search')


def get_db():
    """Get database connection using app config"""
    db_path = current_app.config.get('DATABASE_PATH', 'data/hailtracker_crm.db')
    return Database(db_path)


@search_api_bp.route('')
@login_required
def global_search():
    """
    Search across leads, customers, jobs, and vehicles.

    Query params:
        q: Search query (minimum 2 characters)

    Returns:
        {
            "leads": [{id, name, email, type: "lead"}],
            "customers": [{id, name, email, type: "customer"}],
            "jobs": [{id, job_number, customer_name, status, type: "job"}],
            "vehicles": [{id, display_name, owner_name, type: "vehicle"}]
        }
    """
    query = request.args.get('q', '').strip()

    # Require minimum 2 characters
    if len(query) < 2:
        return jsonify({
            'leads': [],
            'customers': [],
            'jobs': [],
            'vehicles': []
        })

    db = get_db()
    search_pattern = f'%{query}%'

    results = {
        'leads': [],
        'customers': [],
        'jobs': [],
        'vehicles': []
    }

    # Search leads (name, email, phone)
    leads_sql = """
        SELECT id, first_name, last_name, email, phone, status
        FROM leads
        WHERE deleted_at IS NULL
          AND (
              first_name LIKE ? OR
              last_name LIKE ? OR
              (first_name || ' ' || last_name) LIKE ? OR
              email LIKE ? OR
              phone LIKE ?
          )
        ORDER BY created_at DESC
        LIMIT 5
    """
    leads = db.execute(leads_sql, [search_pattern] * 5)
    for lead in leads:
        name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() or 'Unknown'
        results['leads'].append({
            'id': lead['id'],
            'name': name,
            'email': lead.get('email', ''),
            'phone': lead.get('phone', ''),
            'status': lead.get('status', ''),
            'type': 'lead'
        })

    # Search customers (name, email, phone)
    customers_sql = """
        SELECT id, first_name, last_name, email, phone, company_name
        FROM customers
        WHERE deleted_at IS NULL
          AND (
              first_name LIKE ? OR
              last_name LIKE ? OR
              (first_name || ' ' || last_name) LIKE ? OR
              email LIKE ? OR
              phone LIKE ? OR
              company_name LIKE ?
          )
        ORDER BY created_at DESC
        LIMIT 5
    """
    customers = db.execute(customers_sql, [search_pattern] * 6)
    for customer in customers:
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
        if customer.get('company_name'):
            name = f"{name} ({customer['company_name']})" if name else customer['company_name']
        results['customers'].append({
            'id': customer['id'],
            'name': name or 'Unknown',
            'email': customer.get('email', ''),
            'phone': customer.get('phone', ''),
            'type': 'customer'
        })

    # Search jobs (job number, customer name)
    jobs_sql = """
        SELECT j.id, j.job_number, j.status,
               c.first_name, c.last_name,
               v.year, v.make, v.model
        FROM jobs j
        LEFT JOIN customers c ON j.customer_id = c.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        WHERE j.deleted_at IS NULL
          AND (
              j.job_number LIKE ? OR
              c.first_name LIKE ? OR
              c.last_name LIKE ? OR
              (c.first_name || ' ' || c.last_name) LIKE ?
          )
        ORDER BY j.created_at DESC
        LIMIT 5
    """
    jobs = db.execute(jobs_sql, [search_pattern] * 4)
    for job in jobs:
        customer_name = f"{job.get('first_name', '')} {job.get('last_name', '')}".strip() or 'Unknown'
        vehicle_info = ''
        if job.get('year') or job.get('make') or job.get('model'):
            vehicle_info = f"{job.get('year', '')} {job.get('make', '')} {job.get('model', '')}".strip()
        results['jobs'].append({
            'id': job['id'],
            'job_number': job.get('job_number', ''),
            'customer_name': customer_name,
            'vehicle': vehicle_info,
            'status': job.get('status', ''),
            'type': 'job'
        })

    # Search vehicles (VIN, make, model, owner name)
    vehicles_sql = """
        SELECT v.id, v.vin, v.year, v.make, v.model, v.color,
               c.first_name, c.last_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        WHERE v.deleted_at IS NULL
          AND (
              v.vin LIKE ? OR
              v.make LIKE ? OR
              v.model LIKE ? OR
              (v.year || ' ' || v.make || ' ' || v.model) LIKE ? OR
              c.first_name LIKE ? OR
              c.last_name LIKE ? OR
              (c.first_name || ' ' || c.last_name) LIKE ?
          )
        ORDER BY v.created_at DESC
        LIMIT 5
    """
    vehicles = db.execute(vehicles_sql, [search_pattern] * 7)
    for vehicle in vehicles:
        display_name = f"{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}".strip()
        if vehicle.get('color'):
            display_name = f"{vehicle.get('color')} {display_name}".strip()
        owner_name = f"{vehicle.get('first_name', '')} {vehicle.get('last_name', '')}".strip() or 'Unknown'
        results['vehicles'].append({
            'id': vehicle['id'],
            'display_name': display_name or 'Unknown Vehicle',
            'vin': vehicle.get('vin', ''),
            'owner_name': owner_name,
            'type': 'vehicle'
        })

    return jsonify(results)
