"""
Fleet Leads API - CRM for Fleet Prospecting
============================================

CRM system specifically for fleet prospect leads from business scraping:
- Create leads from scraped businesses
- Track status (NEW, CONTACTED, QUOTED, WON, LOST)
- Log activities and notes
- Schedule follow-ups
- Track quotes and wins

Uses SQLite table 'fleet_leads' to avoid conflicts with existing leads system.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import sqlite3
import os
import logging

logger = logging.getLogger('FleetLeadsAPI')

fleet_leads_bp = Blueprint('fleet_leads', __name__, url_prefix='/api/fleet-leads')

# Database path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'hailtracker_crm.db')


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_fleet_leads_table():
    """Create fleet_leads table if not exists."""
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fleet_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER,
            company_name TEXT NOT NULL,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            phone TEXT,
            website TEXT,
            contact_name TEXT,
            contact_title TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            source TEXT DEFAULT 'FLEET_DISCOVERY',
            category TEXT,
            estimated_vehicles INTEGER DEFAULT 0,
            tier INTEGER DEFAULT 3,
            status TEXT DEFAULT 'NEW',
            priority TEXT DEFAULT 'MEDIUM',
            latitude REAL,
            longitude REAL,
            hail_affected INTEGER DEFAULT 0,
            hail_date TEXT,
            hail_size REAL,
            hail_distance REAL,
            last_contact_date TEXT,
            next_followup_date TEXT,
            call_count INTEGER DEFAULT 0,
            notes TEXT,
            quote_amount REAL,
            quote_date TEXT,
            quote_vehicles INTEGER,
            won_amount REAL,
            won_date TEXT,
            lost_reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create indexes for faster queries
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fleet_leads_status ON fleet_leads(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fleet_leads_city_state ON fleet_leads(city, state)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fleet_leads_hail ON fleet_leads(hail_affected)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fleet_leads_followup ON fleet_leads(next_followup_date)')

    conn.commit()
    conn.close()
    logger.info(f"Fleet leads table initialized: {DB_PATH}")


# Initialize table on import
init_fleet_leads_table()


@fleet_leads_bp.route('')
def get_leads():
    """
    Get all fleet leads with optional filtering.

    Query params:
    - status: Filter by status (NEW, CONTACTED, CALLBACK, QUOTED, NEGOTIATING, WON, LOST)
    - city: Filter by city
    - state: Filter by state
    - priority: Filter by priority (HIGH, MEDIUM, LOW)
    - hail_affected: Filter by hail affected (true/false)
    - search: Search company name
    - limit: Max results (default: 500)
    """
    status = request.args.get('status')
    city = request.args.get('city')
    state = request.args.get('state')
    priority = request.args.get('priority')
    hail_affected = request.args.get('hail_affected')
    search = request.args.get('search')
    limit = request.args.get('limit', 500, type=int)

    conn = get_db()

    query = 'SELECT * FROM fleet_leads WHERE 1=1'
    params = []

    if status:
        query += ' AND status = ?'
        params.append(status)
    if city:
        query += ' AND LOWER(city) LIKE LOWER(?)'
        params.append(f'%{city}%')
    if state:
        query += ' AND UPPER(state) = UPPER(?)'
        params.append(state)
    if priority:
        query += ' AND priority = ?'
        params.append(priority)
    if hail_affected and hail_affected.lower() == 'true':
        query += ' AND hail_affected = 1'
    if search:
        query += ' AND company_name LIKE ?'
        params.append(f'%{search}%')

    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    leads = [dict(row) for row in rows]

    return jsonify({
        'count': len(leads),
        'leads': leads
    })


@fleet_leads_bp.route('', methods=['POST'])
def create_lead():
    """
    Create a new fleet lead from a scraped business.

    POST body:
    {
        "business_id": 123,
        "company_name": "ABC Company",
        "address": "123 Main St",
        "city": "Dallas",
        "state": "TX",
        "phone": "555-1234",
        "category": "landscaping",
        "estimated_vehicles": 15,
        "tier": 2,
        "hail_affected": true,
        ...
    }
    """
    data = request.get_json()

    if not data.get('company_name') and not data.get('name'):
        return jsonify({'error': 'company_name is required'}), 400

    company_name = data.get('company_name') or data.get('name')

    conn = get_db()

    # Check for duplicate
    existing = conn.execute(
        'SELECT id FROM fleet_leads WHERE company_name = ? AND city = ? AND state = ?',
        (company_name, data.get('city'), data.get('state'))
    ).fetchone()

    if existing:
        conn.close()
        return jsonify({
            'error': 'Lead already exists',
            'lead_id': existing['id']
        }), 409

    # Calculate priority based on tier and hail
    priority = 'MEDIUM'
    if data.get('hail_affected') or data.get('tier') == 1:
        priority = 'HIGH'
    elif data.get('tier') == 3 and not data.get('hail_affected'):
        priority = 'LOW'

    # Initial note
    initial_note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Lead created from {data.get('source', 'fleet discovery')}"
    if data.get('hail_affected'):
        initial_note += f" - HAIL AFFECTED ({data.get('hail_distance', '?')} mi from hail report)"

    # Insert lead
    cursor = conn.execute('''
        INSERT INTO fleet_leads (
            business_id, company_name, address, city, state, zip_code,
            phone, website, source, category, estimated_vehicles, tier,
            status, priority, latitude, longitude,
            hail_affected, hail_date, hail_size, hail_distance, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('business_id') or data.get('id'),
        company_name,
        data.get('address'),
        data.get('city'),
        data.get('state'),
        data.get('zip_code') or data.get('zip'),
        data.get('phone'),
        data.get('website'),
        data.get('source', 'FLEET_DISCOVERY'),
        data.get('category'),
        data.get('estimated_vehicles', 0),
        data.get('tier', 3),
        'NEW',
        priority,
        data.get('latitude'),
        data.get('longitude'),
        1 if data.get('hail_affected') else 0,
        data.get('hail_date'),
        data.get('hail_size'),
        data.get('hail_distance'),
        initial_note
    ))

    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Created fleet lead {lead_id}: {company_name}")

    return jsonify({
        'success': True,
        'lead_id': lead_id,
        'message': f"Lead created for {company_name}"
    }), 201


@fleet_leads_bp.route('/<int:lead_id>')
def get_lead(lead_id):
    """Get a single fleet lead by ID."""
    conn = get_db()
    row = conn.execute('SELECT * FROM fleet_leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Lead not found'}), 404

    return jsonify(dict(row))


@fleet_leads_bp.route('/<int:lead_id>', methods=['PUT'])
def update_lead(lead_id):
    """
    Update a fleet lead.

    PUT body:
    {
        "status": "CONTACTED",
        "contact_name": "John Smith",
        "notes": "Spoke with manager...",
        "next_followup_date": "2024-02-01",
        ...
    }
    """
    data = request.get_json()
    conn = get_db()

    # Check exists
    existing = conn.execute('SELECT * FROM fleet_leads WHERE id = ?', (lead_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Lead not found'}), 404

    # Build update query
    updates = []
    params = []

    allowed_fields = [
        'status', 'priority', 'contact_name', 'contact_title',
        'contact_email', 'contact_phone', 'notes', 'next_followup_date',
        'quote_amount', 'quote_vehicles', 'won_amount', 'lost_reason'
    ]

    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])

    # Auto-set dates based on status changes
    if 'status' in data:
        new_status = data['status']

        if new_status in ['CONTACTED', 'CALLBACK', 'QUOTED', 'NEGOTIATING']:
            updates.append('last_contact_date = ?')
            params.append(datetime.now().isoformat())
            # Increment call count
            conn.execute('UPDATE fleet_leads SET call_count = call_count + 1 WHERE id = ?', (lead_id,))

        if new_status == 'QUOTED' and data.get('quote_amount'):
            updates.append('quote_date = ?')
            params.append(datetime.now().isoformat())

        if new_status == 'WON':
            updates.append('won_date = ?')
            params.append(datetime.now().isoformat())
            if data.get('won_amount'):
                updates.append('won_amount = ?')
                params.append(data['won_amount'])

    updates.append('updated_at = ?')
    params.append(datetime.now().isoformat())

    params.append(lead_id)

    if updates:
        query = f"UPDATE fleet_leads SET {', '.join(updates)} WHERE id = ?"
        conn.execute(query, params)
        conn.commit()

    # Fetch updated lead
    row = conn.execute('SELECT * FROM fleet_leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()

    return jsonify({
        'success': True,
        'lead': dict(row)
    })


@fleet_leads_bp.route('/<int:lead_id>', methods=['DELETE'])
def delete_lead(lead_id):
    """Delete a fleet lead."""
    conn = get_db()

    existing = conn.execute('SELECT id FROM fleet_leads WHERE id = ?', (lead_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Lead not found'}), 404

    conn.execute('DELETE FROM fleet_leads WHERE id = ?', (lead_id,))
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Lead deleted'})


@fleet_leads_bp.route('/<int:lead_id>/log', methods=['POST'])
def log_activity(lead_id):
    """
    Log an activity on a fleet lead.

    POST body:
    {
        "type": "Call",  // Call, Email, Visit, Note
        "text": "Left voicemail with receptionist",
        "next_followup": "2024-02-05"  // optional
    }
    """
    data = request.get_json()
    conn = get_db()

    # Get current notes
    row = conn.execute('SELECT notes FROM fleet_leads WHERE id = ?', (lead_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Lead not found'}), 404

    # Append new activity
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    activity_type = data.get('type', 'Note')
    activity_text = data.get('text', data.get('activity', ''))
    new_entry = f"[{timestamp}] {activity_type}: {activity_text}"

    current_notes = row['notes'] or ''
    updated_notes = f"{new_entry}\n\n{current_notes}".strip()

    # Build update
    update_parts = ['notes = ?', 'last_contact_date = ?', 'updated_at = ?']
    update_values = [updated_notes, datetime.now().isoformat(), datetime.now().isoformat()]

    if data.get('next_followup'):
        update_parts.append('next_followup_date = ?')
        update_values.append(data['next_followup'])

    update_values.append(lead_id)

    conn.execute(f"UPDATE fleet_leads SET {', '.join(update_parts)} WHERE id = ?", update_values)

    if activity_type in ['Call', 'Visit']:
        conn.execute('UPDATE fleet_leads SET call_count = call_count + 1 WHERE id = ?', (lead_id,))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'message': 'Activity logged'})


@fleet_leads_bp.route('/stats')
def lead_stats():
    """Get fleet lead statistics for dashboard."""
    conn = get_db()

    # Total counts by status
    status_counts = conn.execute('''
        SELECT status, COUNT(*) as count,
               SUM(estimated_vehicles) as vehicles,
               SUM(CASE WHEN quote_amount IS NOT NULL THEN quote_amount ELSE estimated_vehicles * 500 END) as value
        FROM fleet_leads
        GROUP BY status
    ''').fetchall()

    # Pipeline value (not won/lost)
    pipeline = conn.execute('''
        SELECT COUNT(*) as count,
               SUM(estimated_vehicles) as vehicles,
               SUM(CASE WHEN quote_amount IS NOT NULL THEN quote_amount ELSE estimated_vehicles * 500 END) as value
        FROM fleet_leads
        WHERE status NOT IN ('WON', 'LOST')
    ''').fetchone()

    # Won deals
    won = conn.execute('''
        SELECT COUNT(*) as count,
               SUM(won_amount) as value
        FROM fleet_leads
        WHERE status = 'WON'
    ''').fetchone()

    # Hail affected
    hail_affected = conn.execute('''
        SELECT COUNT(*) as count, SUM(estimated_vehicles) as vehicles
        FROM fleet_leads
        WHERE hail_affected = 1 AND status NOT IN ('WON', 'LOST')
    ''').fetchone()

    # Follow-ups due today or overdue
    followups_due = conn.execute('''
        SELECT COUNT(*) as count
        FROM fleet_leads
        WHERE next_followup_date <= date('now')
        AND status NOT IN ('WON', 'LOST')
    ''').fetchone()

    # Recent activity (leads contacted in last 7 days)
    recent_activity = conn.execute('''
        SELECT COUNT(*) as count
        FROM fleet_leads
        WHERE last_contact_date >= date('now', '-7 days')
    ''').fetchone()

    # By city
    by_city = conn.execute('''
        SELECT city, state, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
        FROM fleet_leads
        WHERE status NOT IN ('WON', 'LOST')
        GROUP BY city, state
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()

    conn.close()

    return jsonify({
        'by_status': [dict(row) for row in status_counts],
        'pipeline': {
            'count': pipeline['count'] or 0,
            'vehicles': pipeline['vehicles'] or 0,
            'value': pipeline['value'] or 0,
        },
        'won': {
            'count': won['count'] or 0,
            'value': won['value'] or 0,
        },
        'hail_affected': {
            'count': hail_affected['count'] or 0,
            'vehicles': hail_affected['vehicles'] or 0,
        },
        'followups_due': followups_due['count'] or 0,
        'recent_activity': recent_activity['count'] or 0,
        'by_city': [dict(row) for row in by_city],
    })


@fleet_leads_bp.route('/followups')
def get_followups():
    """Get fleet leads with followups due today or overdue."""
    conn = get_db()

    rows = conn.execute('''
        SELECT * FROM fleet_leads
        WHERE next_followup_date <= date('now', '+1 day')
        AND status NOT IN ('WON', 'LOST')
        ORDER BY next_followup_date ASC
    ''').fetchall()

    conn.close()

    return jsonify({
        'count': len(rows),
        'leads': [dict(row) for row in rows]
    })


@fleet_leads_bp.route('/bulk', methods=['POST'])
def bulk_create_leads():
    """
    Create multiple fleet leads at once (from batch selection).

    POST body:
    {
        "businesses": [
            { "business_id": 1, "company_name": "...", ... },
            ...
        ]
    }
    """
    data = request.get_json()
    businesses = data.get('businesses', [])

    if not businesses:
        return jsonify({'error': 'No businesses provided'}), 400

    conn = get_db()
    created = 0
    duplicates = 0
    errors = []

    for biz in businesses:
        try:
            company_name = biz.get('company_name') or biz.get('name')
            if not company_name:
                errors.append("Missing company name")
                continue

            # Check for duplicate
            existing = conn.execute(
                'SELECT id FROM fleet_leads WHERE company_name = ? AND city = ? AND state = ?',
                (company_name, biz.get('city'), biz.get('state'))
            ).fetchone()

            if existing:
                duplicates += 1
                continue

            # Calculate priority
            priority = 'MEDIUM'
            if biz.get('hail_affected') or biz.get('tier') == 1:
                priority = 'HIGH'
            elif biz.get('tier') == 3:
                priority = 'LOW'

            initial_note = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Bulk import from fleet discovery"

            conn.execute('''
                INSERT INTO fleet_leads (
                    business_id, company_name, address, city, state, zip_code,
                    phone, website, source, category, estimated_vehicles, tier,
                    status, priority, latitude, longitude,
                    hail_affected, hail_date, hail_size, hail_distance, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                biz.get('business_id') or biz.get('id'),
                company_name,
                biz.get('address'),
                biz.get('city'),
                biz.get('state'),
                biz.get('zip_code') or biz.get('zip'),
                biz.get('phone'),
                biz.get('website'),
                biz.get('source', 'FLEET_DISCOVERY'),
                biz.get('category'),
                biz.get('estimated_vehicles', 0),
                biz.get('tier', 3),
                'NEW',
                priority,
                biz.get('latitude'),
                biz.get('longitude'),
                1 if biz.get('hail_affected') else 0,
                biz.get('hail_date'),
                biz.get('hail_size'),
                biz.get('hail_distance'),
                initial_note
            ))
            created += 1

        except Exception as e:
            errors.append(f"{biz.get('company_name', 'Unknown')}: {str(e)}")

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'created': created,
        'duplicates': duplicates,
        'errors': errors
    })


@fleet_leads_bp.route('/map')
def get_leads_for_map():
    """Get fleet leads with coordinates for map display."""
    status = request.args.get('status')
    city = request.args.get('city')
    state = request.args.get('state')

    conn = get_db()

    query = '''
        SELECT id, company_name, category, tier, estimated_vehicles,
               address, city, state, zip_code, phone, website,
               latitude, longitude, status, priority, hail_affected
        FROM fleet_leads
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    '''
    params = []

    if status:
        query += ' AND status = ?'
        params.append(status)
    if city:
        query += ' AND LOWER(city) = LOWER(?)'
        params.append(city)
    if state:
        query += ' AND UPPER(state) = UPPER(?)'
        params.append(state)

    query += ' ORDER BY estimated_vehicles DESC LIMIT 500'

    rows = conn.execute(query, params).fetchall()
    conn.close()

    leads = []
    for row in rows:
        lead = dict(row)
        # Add marker info for map
        lead['marker'] = {
            'lat': lead['latitude'],
            'lng': lead['longitude'],
            'title': lead['company_name'],
            'status': lead['status'],
            'priority': lead['priority'],
        }
        leads.append(lead)

    return jsonify({
        'count': len(leads),
        'leads': leads
    })
