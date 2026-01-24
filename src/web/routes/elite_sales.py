"""
Elite Sales API Routes
Professional-grade field sales endpoints for HailTracker Pro

Endpoints:
- /api/elite/routes - Route optimization
- /api/elite/leads - Field lead management
- /api/elite/competitors - Competitor intelligence
- /api/elite/estimates - Instant estimates
- /api/elite/contracts - Field contracts
- /api/elite/gamification - Achievements & leaderboard
- /api/elite/dnk - Do-not-knock list
- /api/elite/scripts - Smart scripts
- /api/elite/objections - Objection tracking
- /api/elite/salespeople - Salesperson management
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import os
import sys
import json

# Add project root to path
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.crm.managers.elite_sales_manager import EliteSalesManager

elite_sales_bp = Blueprint('elite_sales', __name__, url_prefix='/api/elite')

# Initialize Elite Sales Manager
db_path = os.path.join(PROJECT_ROOT, 'data', 'pdr_crm.db')
elite_mgr = EliteSalesManager(db_path)


# ============================================================================
# SALESPERSON MANAGEMENT
# ============================================================================

@elite_sales_bp.route('/salespeople', methods=['GET'])
@login_required
def get_salespeople():
    """Get all salespeople"""

    status = request.args.get('status', 'ACTIVE')

    if status == 'ALL':
        salespeople = elite_mgr.db.execute(
            "SELECT * FROM salespeople ORDER BY first_name, last_name"
        )
    else:
        salespeople = elite_mgr.db.execute(
            "SELECT * FROM salespeople WHERE status = ? ORDER BY first_name, last_name",
            (status,)
        )

    return jsonify({
        'salespeople': salespeople,
        'count': len(salespeople)
    })


@elite_sales_bp.route('/salespeople', methods=['POST'])
@login_required
def create_salesperson():
    """Create a new salesperson"""

    data = request.get_json()

    if not data or 'first_name' not in data or 'last_name' not in data:
        return jsonify({'error': 'first_name and last_name required'}), 400

    salesperson_id = elite_mgr.db.insert('salespeople', {
        'first_name': data['first_name'],
        'last_name': data['last_name'],
        'email': data.get('email'),
        'phone': data.get('phone'),
        'employee_id': data.get('employee_id'),
        'status': data.get('status', 'ACTIVE'),
        'hire_date': data.get('hire_date'),
        'commission_rate': data.get('commission_rate', 0.15)
    })

    return jsonify({
        'success': True,
        'salesperson_id': salesperson_id
    })


@elite_sales_bp.route('/salespeople/<int:salesperson_id>', methods=['GET'])
@login_required
def get_salesperson(salesperson_id):
    """Get salesperson details with stats"""

    salesperson = elite_mgr.db.get_by_id('salespeople', salesperson_id)

    if not salesperson:
        return jsonify({'error': 'Salesperson not found'}), 404

    # Get today's stats
    today = date.today().isoformat()
    today_leads = elite_mgr.db.execute("""
        SELECT COUNT(*) as count,
               SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot
        FROM field_leads
        WHERE salesperson_id = ? AND DATE(created_at) = ?
    """, (salesperson_id, today))[0]

    # Get achievements
    achievements = elite_mgr.get_salesperson_achievements(salesperson_id)
    points = elite_mgr.get_salesperson_points(salesperson_id)

    return jsonify({
        'salesperson': salesperson,
        'stats': {
            'leads_today': today_leads['count'],
            'hot_leads_today': today_leads['hot'] or 0,
            'total_points': points,
            'achievements_count': len(achievements)
        },
        'achievements': achievements[:5]  # Last 5
    })


@elite_sales_bp.route('/salespeople/<int:salesperson_id>', methods=['PUT'])
@login_required
def update_salesperson(salesperson_id):
    """Update salesperson details"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    allowed_fields = ['first_name', 'last_name', 'email', 'phone',
                      'employee_id', 'status', 'commission_rate']

    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if update_data:
        elite_mgr.db.update('salespeople', salesperson_id, update_data)

    return jsonify({'success': True})


# ============================================================================
# ROUTE OPTIMIZATION
# ============================================================================

@elite_sales_bp.route('/routes/optimize', methods=['POST'])
@login_required
def optimize_route():
    """Generate optimized canvassing route"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data:
        return jsonify({'error': 'salesperson_id required'}), 400

    # Parse start time or use now
    start_time_str = data.get('start_time')
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
    else:
        start_time = datetime.now()

    route = elite_mgr.optimize_daily_route(
        salesperson_id=data['salesperson_id'],
        grid_cell_id=data.get('grid_cell_id', 1),
        start_time=start_time,
        target_homes=data.get('target_homes', 50)
    )

    return jsonify({
        'success': True,
        'route': route
    })


@elite_sales_bp.route('/routes/storm', methods=['POST'])
@login_required
def generate_storm_route():
    """Generate canvassing route for homes within a hail storm swath"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data:
        return jsonify({'error': 'salesperson_id required'}), 400
    if 'hail_event_id' not in data:
        return jsonify({'error': 'hail_event_id required'}), 400

    # Get storm data
    from src.crm.managers.hail_event_manager import HailEventManager
    from src.db.database import Database
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    db = Database(db_path)
    hail_mgr = HailEventManager(db)

    storm = hail_mgr.get_storm_event(data['hail_event_id'])
    if not storm:
        return jsonify({'error': 'Storm not found'}), 404

    # For now, generate a standard route but include the storm info
    # In a full implementation, this would query addresses within the swath polygon
    route = elite_mgr.optimize_daily_route(
        salesperson_id=data['salesperson_id'],
        grid_cell_id=data.get('grid_cell_id', 1),
        start_time=datetime.now(),
        target_homes=data.get('target_homes', 50)
    )

    return jsonify({
        'success': True,
        'route': route,
        'storm': {
            'id': storm['id'],
            'event_name': storm.get('event_name'),
            'event_date': storm.get('event_date'),
            'max_hail_size': storm.get('max_hail_size') or storm.get('hail_size_inches'),
            'swath_polygon': storm.get('swath_polygon')
        }
    })


@elite_sales_bp.route('/routes/property/<path:address>', methods=['GET'])
@login_required
def get_property_data(address):
    """Get enriched property data for an address"""

    property_data = elite_mgr._get_property_enrichment(address)

    return jsonify({
        'address': address,
        'property_data': property_data
    })


# ============================================================================
# GRID CELL MANAGEMENT
# ============================================================================

@elite_sales_bp.route('/grid-cells', methods=['GET'])
@login_required
def get_grid_cells():
    """Get all grid cells with optional filters"""

    swath_id = request.args.get('swath_id', type=int)
    status = request.args.get('status')
    assigned_to = request.args.get('assigned_to', type=int)

    query = "SELECT * FROM sales_grid_cells WHERE 1=1"
    params = []

    if swath_id:
        query += " AND swath_id = ?"
        params.append(swath_id)

    if status:
        query += " AND status = ?"
        params.append(status)

    if assigned_to:
        query += " AND assigned_to = ?"
        params.append(assigned_to)

    query += " ORDER BY cell_index"

    cells = elite_mgr.db.execute(query, tuple(params))

    return jsonify({
        'grid_cells': cells,
        'count': len(cells)
    })


@elite_sales_bp.route('/grid-cells/<int:cell_id>/assign', methods=['PUT'])
@login_required
def assign_grid_cell(cell_id):
    """Assign grid cell to salesperson"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data:
        return jsonify({'error': 'salesperson_id required'}), 400

    elite_mgr.db.execute("""
        UPDATE sales_grid_cells
        SET assigned_to = ?, status = 'ASSIGNED', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (data['salesperson_id'], cell_id))

    return jsonify({'success': True})


# ============================================================================
# FIELD LEADS
# ============================================================================

@elite_sales_bp.route('/leads', methods=['GET'])
@login_required
def get_field_leads():
    """Get field leads with optional filters"""

    salesperson_id = request.args.get('salesperson_id', type=int)
    quality = request.args.get('quality')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    synced = request.args.get('synced')
    limit = request.args.get('limit', 100, type=int)

    query = "SELECT * FROM field_leads WHERE 1=1"
    params = []

    if salesperson_id:
        query += " AND salesperson_id = ?"
        params.append(salesperson_id)

    if quality:
        query += " AND lead_quality = ?"
        params.append(quality)

    if date_from:
        query += " AND DATE(created_at) >= ?"
        params.append(date_from)

    if date_to:
        query += " AND DATE(created_at) <= ?"
        params.append(date_to)

    if synced is not None:
        query += " AND synced_to_crm = ?"
        params.append(1 if synced == 'true' else 0)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    leads = elite_mgr.db.execute(query, tuple(params))

    return jsonify({
        'leads': leads,
        'count': len(leads)
    })


@elite_sales_bp.route('/leads', methods=['POST'])
@login_required
def create_field_lead():
    """Create a new field lead"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['salesperson_id', 'latitude', 'longitude', 'address', 'customer_name']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    lead_id = elite_mgr.create_field_lead(
        salesperson_id=data['salesperson_id'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        address=data['address'],
        customer_name=data['customer_name'],
        phone=data.get('phone'),
        email=data.get('email'),
        vehicle_info=data.get('vehicle_info'),
        damage_description=data.get('damage_description'),
        lead_quality=data.get('lead_quality', 'WARM'),
        notes=data.get('notes'),
        photo_urls=data.get('photo_urls'),
        grid_cell_id=data.get('grid_cell_id')
    )

    return jsonify({
        'success': True,
        'lead_id': lead_id
    })


@elite_sales_bp.route('/leads/<int:lead_id>', methods=['GET'])
@login_required
def get_field_lead(lead_id):
    """Get field lead details"""

    lead = elite_mgr.db.get_by_id('field_leads', lead_id)

    if not lead:
        return jsonify({'error': 'Lead not found'}), 404

    # Parse JSON fields
    if lead.get('vehicle_info'):
        lead['vehicle_info'] = json.loads(lead['vehicle_info'])
    if lead.get('photo_urls'):
        lead['photo_urls'] = json.loads(lead['photo_urls'])

    return jsonify(lead)


@elite_sales_bp.route('/leads/<int:lead_id>', methods=['PUT'])
@login_required
def update_field_lead(lead_id):
    """Update field lead"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    allowed_fields = ['customer_name', 'phone', 'email', 'damage_description',
                      'lead_quality', 'notes']

    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if 'vehicle_info' in data:
        update_data['vehicle_info'] = json.dumps(data['vehicle_info'])

    if 'photo_urls' in data:
        update_data['photo_urls'] = json.dumps(data['photo_urls'])

    if update_data:
        elite_mgr.db.update('field_leads', lead_id, update_data)

    return jsonify({'success': True})


@elite_sales_bp.route('/leads/<int:lead_id>/sync', methods=['POST'])
@login_required
def sync_lead_to_crm(lead_id):
    """Sync field lead to main CRM"""

    crm_lead_id = elite_mgr.sync_lead_to_crm(lead_id)

    if crm_lead_id:
        return jsonify({
            'success': True,
            'crm_lead_id': crm_lead_id
        })
    else:
        return jsonify({'error': 'Failed to sync lead'}), 400


@elite_sales_bp.route('/leads/bulk-sync', methods=['POST'])
@login_required
def bulk_sync_leads():
    """Sync multiple leads to CRM"""

    data = request.get_json()

    if not data or 'lead_ids' not in data:
        return jsonify({'error': 'lead_ids required'}), 400

    results = []
    for lead_id in data['lead_ids']:
        crm_lead_id = elite_mgr.sync_lead_to_crm(lead_id)
        results.append({
            'field_lead_id': lead_id,
            'crm_lead_id': crm_lead_id,
            'success': crm_lead_id is not None
        })

    return jsonify({
        'results': results,
        'synced': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success'])
    })


# ============================================================================
# COMPETITOR INTELLIGENCE
# ============================================================================

@elite_sales_bp.route('/competitors', methods=['GET'])
@login_required
def get_competitor_activity():
    """Get competitor activity with filters"""

    days_back = request.args.get('days', 7, type=int)
    competitor_name = request.args.get('competitor')
    activity_type = request.args.get('type')
    limit = request.args.get('limit', 100, type=int)

    cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()

    query = "SELECT * FROM competitor_activity WHERE spotted_at >= ?"
    params = [cutoff]

    if competitor_name:
        query += " AND competitor_name = ?"
        params.append(competitor_name)

    if activity_type:
        query += " AND activity_type = ?"
        params.append(activity_type)

    query += " ORDER BY spotted_at DESC LIMIT ?"
    params.append(limit)

    activity = elite_mgr.db.execute(query, tuple(params))

    return jsonify({
        'activity': activity,
        'count': len(activity),
        'period_days': days_back
    })


@elite_sales_bp.route('/competitors', methods=['POST'])
@login_required
def log_competitor():
    """Log competitor activity"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['salesperson_id', 'competitor_name', 'location_lat',
                'location_lon', 'activity_type']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    activity_id = elite_mgr.log_competitor_activity(
        salesperson_id=data['salesperson_id'],
        competitor_name=data['competitor_name'],
        location_lat=data['location_lat'],
        location_lon=data['location_lon'],
        activity_type=data['activity_type'],
        notes=data.get('notes'),
        photo_url=data.get('photo_url')
    )

    return jsonify({
        'success': True,
        'activity_id': activity_id
    })


@elite_sales_bp.route('/competitors/heatmap', methods=['GET'])
@login_required
def get_competitor_heatmap():
    """Get competitor activity heatmap"""

    swath_id = request.args.get('swath_id', 1, type=int)
    days_back = request.args.get('days', 7, type=int)

    heatmap = elite_mgr.get_competitor_heatmap(swath_id, days_back)

    return jsonify(heatmap)


@elite_sales_bp.route('/competitors/summary', methods=['GET'])
@login_required
def get_competitor_summary():
    """Get competitor summary stats"""

    days_back = request.args.get('days', 30, type=int)
    cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()

    summary = elite_mgr.db.execute("""
        SELECT
            competitor_name,
            COUNT(*) as total_sightings,
            COUNT(DISTINCT DATE(spotted_at)) as active_days,
            MAX(spotted_at) as last_seen
        FROM competitor_activity
        WHERE spotted_at >= ?
        GROUP BY competitor_name
        ORDER BY total_sightings DESC
    """, (cutoff,))

    return jsonify({
        'competitors': summary,
        'period_days': days_back
    })


# ============================================================================
# INSTANT ESTIMATES
# ============================================================================

@elite_sales_bp.route('/estimates/instant', methods=['POST'])
@login_required
def generate_instant_estimate():
    """Generate instant estimate from photos"""

    data = request.get_json()

    if not data or 'vehicle_info' not in data:
        return jsonify({'error': 'vehicle_info required'}), 400

    estimate = elite_mgr.generate_instant_estimate(
        photos=data.get('photos', []),
        vehicle_info=data['vehicle_info']
    )

    return jsonify({
        'success': True,
        'estimate': estimate
    })


# ============================================================================
# FIELD CONTRACTS
# ============================================================================

@elite_sales_bp.route('/contracts', methods=['POST'])
@login_required
def create_field_contract():
    """Generate e-signature contract"""

    data = request.get_json()

    if not data or 'lead_id' not in data or 'customer_email' not in data:
        return jsonify({'error': 'lead_id and customer_email required'}), 400

    contract_url = elite_mgr.create_field_contract(
        lead_id=data['lead_id'],
        estimate=data.get('estimate', {}),
        customer_email=data['customer_email']
    )

    return jsonify({
        'success': True,
        'contract_url': contract_url
    })


# ============================================================================
# GAMIFICATION - ACHIEVEMENTS
# ============================================================================

@elite_sales_bp.route('/achievements/<int:salesperson_id>', methods=['GET'])
@login_required
def get_achievements(salesperson_id):
    """Get achievements for salesperson"""

    achievements = elite_mgr.get_salesperson_achievements(salesperson_id)
    points = elite_mgr.get_salesperson_points(salesperson_id)

    # Parse achievement data
    for ach in achievements:
        if ach.get('achievement_data'):
            ach['achievement_data'] = json.loads(ach['achievement_data'])

    return jsonify({
        'achievements': achievements,
        'total_points': points,
        'count': len(achievements)
    })


@elite_sales_bp.route('/achievements', methods=['POST'])
@login_required
def award_achievement():
    """Award achievement to salesperson"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data or 'achievement_type' not in data:
        return jsonify({'error': 'salesperson_id and achievement_type required'}), 400

    achievement_id = elite_mgr.award_achievement(
        salesperson_id=data['salesperson_id'],
        achievement_type=data['achievement_type'],
        achievement_data=data.get('achievement_data', {})
    )

    return jsonify({
        'success': True,
        'achievement_id': achievement_id
    })


# ============================================================================
# GAMIFICATION - LEADERBOARD
# ============================================================================

@elite_sales_bp.route('/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    """Get real-time leaderboard"""

    period = request.args.get('period', 'TODAY')

    leaderboard = elite_mgr.get_leaderboard_realtime(period)

    # Add points to leaderboard
    for entry in leaderboard:
        entry['points'] = elite_mgr.get_salesperson_points(entry['id'])

    return jsonify({
        'leaderboard': leaderboard,
        'period': period,
        'updated_at': datetime.now().isoformat()
    })


@elite_sales_bp.route('/leaderboard/stats', methods=['GET'])
@login_required
def get_leaderboard_stats():
    """Get team-wide leaderboard statistics"""

    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    month_start = date.today().replace(day=1).isoformat()

    stats = {
        'today': elite_mgr.db.execute("""
            SELECT COUNT(*) as leads,
                   SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
            FROM field_leads WHERE DATE(created_at) = ?
        """, (today,))[0],
        'this_week': elite_mgr.db.execute("""
            SELECT COUNT(*) as leads,
                   SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
            FROM field_leads WHERE DATE(created_at) >= ?
        """, (week_start,))[0],
        'this_month': elite_mgr.db.execute("""
            SELECT COUNT(*) as leads,
                   SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
            FROM field_leads WHERE DATE(created_at) >= ?
        """, (month_start,))[0]
    }

    return jsonify(stats)


# ============================================================================
# DO-NOT-KNOCK LIST
# ============================================================================

@elite_sales_bp.route('/dnk', methods=['GET'])
@login_required
def get_dnk_list():
    """Get do-not-knock list"""

    limit = request.args.get('limit', 100, type=int)
    reason = request.args.get('reason')

    dnk_list = elite_mgr.get_do_not_knock_list(limit=limit)

    if reason:
        dnk_list = [d for d in dnk_list if d['reason'] == reason]

    return jsonify({
        'dnk_list': dnk_list,
        'count': len(dnk_list)
    })


@elite_sales_bp.route('/dnk', methods=['POST'])
@login_required
def add_dnk():
    """Add address to do-not-knock list"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['address', 'latitude', 'longitude', 'reason']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    dnk_id = elite_mgr.mark_do_not_knock(
        address=data['address'],
        latitude=data['latitude'],
        longitude=data['longitude'],
        reason=data['reason'],
        notes=data.get('notes'),
        salesperson_id=data.get('salesperson_id')
    )

    return jsonify({
        'success': True,
        'dnk_id': dnk_id
    })


@elite_sales_bp.route('/dnk/check', methods=['GET'])
@login_required
def check_dnk():
    """Check if location is on do-not-knock list"""

    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', 50, type=float)

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon required'}), 400

    result = elite_mgr.check_do_not_knock(lat, lon, radius)

    if result:
        return jsonify({
            'is_dnk': True,
            'dnk_entry': result
        })
    else:
        return jsonify({
            'is_dnk': False,
            'dnk_entry': None
        })


@elite_sales_bp.route('/dnk/<int:dnk_id>', methods=['DELETE'])
@login_required
def remove_dnk(dnk_id):
    """Remove address from do-not-knock list"""

    elite_mgr.db.execute(
        "DELETE FROM do_not_knock_list WHERE id = ?",
        (dnk_id,)
    )

    return jsonify({'success': True})


# ============================================================================
# SMART SCRIPTS
# ============================================================================

@elite_sales_bp.route('/scripts/<situation>', methods=['GET'])
@login_required
def get_script(situation):
    """Get smart script for situation"""

    # Get optional property data from query params
    property_data = None
    if request.args.get('owner_name'):
        property_data = {
            'owner_name': request.args.get('owner_name'),
            'vehicles_registered': []
        }

        if request.args.get('vehicle_year'):
            property_data['vehicles_registered'].append({
                'year': request.args.get('vehicle_year'),
                'make': request.args.get('vehicle_make', ''),
                'model': request.args.get('vehicle_model', '')
            })

    script = elite_mgr.get_smart_script(situation, property_data)

    return jsonify({
        'situation': situation,
        'script': script
    })


@elite_sales_bp.route('/scripts', methods=['GET'])
@login_required
def get_all_scripts():
    """Get all available scripts"""

    situations = [
        'DOOR_APPROACH',
        'OBJECTION_PRICE',
        'OBJECTION_TIME',
        'OBJECTION_INSURANCE',
        'CLOSE_APPOINTMENT'
    ]

    scripts = {}
    for situation in situations:
        scripts[situation] = elite_mgr.get_smart_script(situation)

    return jsonify({
        'scripts': scripts,
        'count': len(scripts)
    })


# ============================================================================
# OBJECTION TRACKING
# ============================================================================

@elite_sales_bp.route('/objections', methods=['GET'])
@login_required
def get_objections():
    """Get objection log with filters"""

    salesperson_id = request.args.get('salesperson_id', type=int)
    objection_type = request.args.get('type')
    outcome = request.args.get('outcome')
    days_back = request.args.get('days', 30, type=int)
    limit = request.args.get('limit', 100, type=int)

    cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()

    query = "SELECT * FROM objection_log WHERE logged_at >= ?"
    params = [cutoff]

    if salesperson_id:
        query += " AND salesperson_id = ?"
        params.append(salesperson_id)

    if objection_type:
        query += " AND objection_type = ?"
        params.append(objection_type)

    if outcome:
        query += " AND outcome = ?"
        params.append(outcome)

    query += " ORDER BY logged_at DESC LIMIT ?"
    params.append(limit)

    objections = elite_mgr.db.execute(query, tuple(params))

    return jsonify({
        'objections': objections,
        'count': len(objections),
        'period_days': days_back
    })


@elite_sales_bp.route('/objections', methods=['POST'])
@login_required
def log_objection():
    """Log an objection"""

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['salesperson_id', 'objection_type', 'response_used', 'outcome']
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    objection_id = elite_mgr.log_objection(
        salesperson_id=data['salesperson_id'],
        objection_type=data['objection_type'],
        response_used=data['response_used'],
        outcome=data['outcome']
    )

    return jsonify({
        'success': True,
        'objection_id': objection_id
    })


@elite_sales_bp.route('/objections/analytics', methods=['GET'])
@login_required
def get_objection_analytics():
    """Get objection handling analytics"""

    days_back = request.args.get('days', 30, type=int)

    analytics = elite_mgr.get_objection_analytics(days_back)

    return jsonify(analytics)


# ============================================================================
# MOBILE-SPECIFIC ENDPOINTS
# ============================================================================

@elite_sales_bp.route('/mobile/checkin', methods=['POST'])
@login_required
def mobile_checkin():
    """Mobile app check-in with location"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data:
        return jsonify({'error': 'salesperson_id required'}), 400

    # Record check-in
    checkin = {
        'salesperson_id': data['salesperson_id'],
        'latitude': data.get('latitude'),
        'longitude': data.get('longitude'),
        'timestamp': datetime.now().isoformat(),
        'battery_level': data.get('battery_level'),
        'app_version': data.get('app_version')
    }

    # Get today's route if exists
    route = None
    if data.get('latitude') and data.get('longitude'):
        # In production: Load assigned route for salesperson
        pass

    # Get today's stats
    today = date.today().isoformat()
    stats = elite_mgr.db.execute("""
        SELECT COUNT(*) as leads_today,
               SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
        FROM field_leads
        WHERE salesperson_id = ? AND DATE(created_at) = ?
    """, (data['salesperson_id'], today))[0]

    # Check for nearby DNK addresses
    nearby_dnk = []
    if data.get('latitude') and data.get('longitude'):
        # Check larger radius for mobile
        dnk = elite_mgr.check_do_not_knock(
            data['latitude'],
            data['longitude'],
            radius_feet=500
        )
        if dnk:
            nearby_dnk.append(dnk)

    # Check for nearby competitor activity (last 24 hours)
    nearby_competitors = []
    if data.get('latitude') and data.get('longitude'):
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        nearby_competitors = elite_mgr.db.execute("""
            SELECT * FROM competitor_activity
            WHERE spotted_at >= ?
              AND ABS(location_lat - ?) < 0.01
              AND ABS(location_lon - ?) < 0.01
            ORDER BY spotted_at DESC
            LIMIT 5
        """, (cutoff, data['latitude'], data['longitude']))

    return jsonify({
        'success': True,
        'checkin': checkin,
        'stats': stats,
        'nearby_dnk': nearby_dnk,
        'nearby_competitors': nearby_competitors,
        'server_time': datetime.now().isoformat()
    })


@elite_sales_bp.route('/mobile/quick-lead', methods=['POST'])
@login_required
def mobile_quick_lead():
    """Quick lead capture from mobile"""

    data = request.get_json()

    if not data or 'salesperson_id' not in data:
        return jsonify({'error': 'salesperson_id required'}), 400

    # Create lead with minimal data
    lead_id = elite_mgr.create_field_lead(
        salesperson_id=data['salesperson_id'],
        latitude=data.get('latitude', 0),
        longitude=data.get('longitude', 0),
        address=data.get('address', 'Address pending'),
        customer_name=data.get('customer_name', 'Name pending'),
        phone=data.get('phone'),
        lead_quality=data.get('lead_quality', 'WARM'),
        notes=data.get('notes')
    )

    return jsonify({
        'success': True,
        'lead_id': lead_id,
        'message': 'Lead captured - complete details later'
    })


@elite_sales_bp.route('/mobile/dashboard', methods=['GET'])
@login_required
def mobile_dashboard():
    """Get mobile dashboard data for salesperson"""

    salesperson_id = request.args.get('salesperson_id', type=int)

    if not salesperson_id:
        return jsonify({'error': 'salesperson_id required'}), 400

    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    # Today's stats
    today_stats = elite_mgr.db.execute("""
        SELECT COUNT(*) as leads,
               SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads,
               SUM(CASE WHEN lead_quality = 'WARM' THEN 1 ELSE 0 END) as warm_leads
        FROM field_leads
        WHERE salesperson_id = ? AND DATE(created_at) = ?
    """, (salesperson_id, today))[0]

    # Week stats
    week_stats = elite_mgr.db.execute("""
        SELECT COUNT(*) as leads,
               SUM(CASE WHEN lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
        FROM field_leads
        WHERE salesperson_id = ? AND DATE(created_at) >= ?
    """, (salesperson_id, week_start))[0]

    # Leaderboard position
    leaderboard = elite_mgr.get_leaderboard_realtime('TODAY')
    rank = next((i + 1 for i, e in enumerate(leaderboard) if e['id'] == salesperson_id), None)

    # Recent achievements
    achievements = elite_mgr.get_salesperson_achievements(salesperson_id)[:3]
    points = elite_mgr.get_salesperson_points(salesperson_id)

    return jsonify({
        'salesperson_id': salesperson_id,
        'today': today_stats,
        'this_week': week_stats,
        'rank': rank,
        'total_salespeople': len(leaderboard),
        'points': points,
        'recent_achievements': achievements,
        'updated_at': datetime.now().isoformat()
    })


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@elite_sales_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({'error': 'Bad request'}), 400


@elite_sales_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404


@elite_sales_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500
