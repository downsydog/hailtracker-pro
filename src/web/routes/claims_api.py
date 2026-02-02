"""
Claims API Routes
=================
RESTful API for insurance claim management.
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, date
from src.core.auth.decorators import login_required
from src.db.database import Database

claims_api_bp = Blueprint('claims_api', __name__, url_prefix='/api/claims')


def get_db():
    """Get database connection using CRM database"""
    # Use CRM database for claims
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return Database(db_path)


def generate_claim_number(db):
    """Generate next claim tracking number"""
    result = db.execute("""
        SELECT claim_number FROM insurance_claims
        WHERE claim_number LIKE 'CLM-%'
        ORDER BY id DESC LIMIT 1
    """)
    if result and result[0]['claim_number']:
        last = result[0]['claim_number']
        try:
            num = int(last.replace('CLM-', '')) + 1
        except:
            num = 1001
    else:
        num = 1001
    return f"CLM-{num:05d}"


@claims_api_bp.route('')
@login_required
def list_claims():
    """List insurance claims with filtering"""
    db = get_db()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Filters
    status = request.args.get('status')
    insurance_company = request.args.get('insurance_company')

    # Build query
    where_clauses = ['ic.deleted_at IS NULL']
    params = []

    if status:
        where_clauses.append('status = ?')
        params.append(status.upper())

    if insurance_company:
        where_clauses.append('insurance_company LIKE ?')
        params.append(f'%{insurance_company}%')

    where_sql = ' AND '.join(where_clauses)

    # Get claims with related job/customer info
    claims = db.execute(f"""
        SELECT
            ic.*,
            j.job_number,
            v.year as vehicle_year, v.make as vehicle_make, v.model as vehicle_model,
            c.first_name || ' ' || c.last_name as customer_name
        FROM insurance_claims ic
        LEFT JOIN jobs j ON j.insurance_claim_id = ic.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        LEFT JOIN customers c ON j.customer_id = c.id
        WHERE {where_sql}
        ORDER BY ic.created_at DESC
        LIMIT ? OFFSET ?
    """, tuple(params) + (per_page, offset))

    # Get total count
    count_result = db.execute(f"""
        SELECT COUNT(*) as total FROM insurance_claims ic WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['total'] if count_result else 0

    # Get stats
    stats = db.execute("""
        SELECT
            SUM(CASE WHEN status = 'SUBMITTED' THEN 1 ELSE 0 END) as submitted_count,
            SUM(CASE WHEN status IN ('PENDING_ADJUSTER', 'ADJUSTER_SCHEDULED') THEN 1 ELSE 0 END) as pending_adjuster_count,
            SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
            SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_count,
            SUM(COALESCE(approved_amount, 0)) as total_approved,
            SUM(COALESCE(payment_received, 0)) as total_received
        FROM insurance_claims
        WHERE deleted_at IS NULL
    """)

    return jsonify({
        'claims': claims,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'stats': stats[0] if stats else {}
    })


@claims_api_bp.route('/<int:claim_id>')
@login_required
def get_claim(claim_id):
    """Get claim details"""
    db = get_db()

    claim = db.execute("""
        SELECT
            ic.*,
            j.id as job_id,
            j.job_number,
            v.year as vehicle_year, v.make as vehicle_make, v.model as vehicle_model,
            c.id as customer_id,
            c.first_name || ' ' || c.last_name as customer_name,
            c.phone as customer_phone,
            c.email as customer_email
        FROM insurance_claims ic
        LEFT JOIN jobs j ON j.insurance_claim_id = ic.id
        LEFT JOIN vehicles v ON j.vehicle_id = v.id
        LEFT JOIN customers c ON j.customer_id = c.id
        WHERE ic.id = ? AND ic.deleted_at IS NULL
    """, (claim_id,))

    if not claim:
        return jsonify({'error': 'Claim not found'}), 404

    claim = claim[0]

    # Get claim history/notes
    # (could add a claim_history table for detailed tracking)

    return jsonify(claim)


@claims_api_bp.route('', methods=['POST'])
@login_required
def create_claim():
    """Create new insurance claim"""
    db = get_db()
    data = request.get_json()

    if not data.get('insurance_company'):
        return jsonify({'error': 'insurance_company is required'}), 400

    # Generate or use provided claim number
    claim_number = data.get('claim_number') or generate_claim_number(db)

    claim_id = db.execute("""
        INSERT INTO insurance_claims (
            claim_number, insurance_company, policy_number,
            adjuster_name, adjuster_email, adjuster_phone, adjuster_extension,
            status, claim_date, submitted_date,
            claimed_amount, deductible, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        claim_number,
        data['insurance_company'],
        data.get('policy_number'),
        data.get('adjuster_name'),
        data.get('adjuster_email'),
        data.get('adjuster_phone'),
        data.get('adjuster_extension'),
        data.get('status', 'SUBMITTED'),
        data.get('claim_date', date.today().isoformat()),
        data.get('submitted_date', date.today().isoformat()),
        data.get('claimed_amount'),
        data.get('deductible'),
        data.get('notes')
    ))

    # Link to job if provided
    if data.get('job_id'):
        db.execute("""
            UPDATE jobs SET insurance_claim_id = ? WHERE id = ?
        """, (claim_id, data['job_id']))

    return jsonify({
        'id': claim_id,
        'claim_number': claim_number,
        'message': 'Claim created successfully'
    }), 201


@claims_api_bp.route('/<int:claim_id>', methods=['PUT'])
@login_required
def update_claim(claim_id):
    """Update insurance claim"""
    db = get_db()
    data = request.get_json()

    # Verify exists
    existing = db.execute("SELECT id FROM insurance_claims WHERE id = ? AND deleted_at IS NULL", (claim_id,))
    if not existing:
        return jsonify({'error': 'Claim not found'}), 404

    db.execute("""
        UPDATE insurance_claims SET
            insurance_company = COALESCE(?, insurance_company),
            policy_number = COALESCE(?, policy_number),
            adjuster_name = COALESCE(?, adjuster_name),
            adjuster_email = COALESCE(?, adjuster_email),
            adjuster_phone = COALESCE(?, adjuster_phone),
            adjuster_extension = COALESCE(?, adjuster_extension),
            status = COALESCE(?, status),
            adjuster_scheduled_date = COALESCE(?, adjuster_scheduled_date),
            adjuster_inspection_date = COALESCE(?, adjuster_inspection_date),
            approval_date = COALESCE(?, approval_date),
            payment_received_date = COALESCE(?, payment_received_date),
            claimed_amount = COALESCE(?, claimed_amount),
            approved_amount = COALESCE(?, approved_amount),
            supplement_amount = COALESCE(?, supplement_amount),
            deductible = COALESCE(?, deductible),
            payment_received = COALESCE(?, payment_received),
            notes = COALESCE(?, notes),
            adjuster_notes = COALESCE(?, adjuster_notes),
            last_contact_date = COALESCE(?, last_contact_date),
            last_contact_method = COALESCE(?, last_contact_method),
            next_follow_up_date = COALESCE(?, next_follow_up_date),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.get('insurance_company'),
        data.get('policy_number'),
        data.get('adjuster_name'),
        data.get('adjuster_email'),
        data.get('adjuster_phone'),
        data.get('adjuster_extension'),
        data.get('status'),
        data.get('adjuster_scheduled_date'),
        data.get('adjuster_inspection_date'),
        data.get('approval_date'),
        data.get('payment_received_date'),
        data.get('claimed_amount'),
        data.get('approved_amount'),
        data.get('supplement_amount'),
        data.get('deductible'),
        data.get('payment_received'),
        data.get('notes'),
        data.get('adjuster_notes'),
        data.get('last_contact_date'),
        data.get('last_contact_method'),
        data.get('next_follow_up_date'),
        claim_id
    ))

    return jsonify({'message': 'Claim updated successfully'})


@claims_api_bp.route('/<int:claim_id>', methods=['DELETE'])
@login_required
def delete_claim(claim_id):
    """Soft delete claim"""
    db = get_db()

    existing = db.execute("SELECT id FROM insurance_claims WHERE id = ? AND deleted_at IS NULL", (claim_id,))
    if not existing:
        return jsonify({'error': 'Claim not found'}), 404

    db.execute("""
        UPDATE insurance_claims SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?
    """, (claim_id,))

    return jsonify({'message': 'Claim deleted successfully'})


@claims_api_bp.route('/<int:claim_id>/status', methods=['POST'])
@login_required
def update_claim_status(claim_id):
    """Update claim status with tracking"""
    db = get_db()
    data = request.get_json()

    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'status is required'}), 400

    # Update based on status
    updates = {
        'status': new_status,
        'updated_at': 'CURRENT_TIMESTAMP'
    }

    if new_status == 'ADJUSTER_SCHEDULED':
        updates['adjuster_scheduled_date'] = data.get('date')
    elif new_status == 'INSPECTED':
        updates['adjuster_inspection_date'] = data.get('date', date.today().isoformat())
    elif new_status == 'APPROVED':
        updates['approval_date'] = data.get('date', date.today().isoformat())
        updates['approved_amount'] = data.get('approved_amount')
    elif new_status == 'PAID':
        updates['payment_received_date'] = data.get('date', date.today().isoformat())
        updates['payment_received'] = data.get('payment_received')

    # Build dynamic update
    set_clauses = []
    params = []
    for key, val in updates.items():
        if val == 'CURRENT_TIMESTAMP':
            set_clauses.append(f"{key} = CURRENT_TIMESTAMP")
        else:
            set_clauses.append(f"{key} = ?")
            params.append(val)

    params.append(claim_id)

    db.execute(f"""
        UPDATE insurance_claims SET {', '.join(set_clauses)} WHERE id = ?
    """, tuple(params))

    return jsonify({'message': f'Claim status updated to {new_status}'})


@claims_api_bp.route('/insurance-companies')
@login_required
def get_insurance_companies():
    """Get list of insurance companies"""
    db = get_db()

    companies = db.execute("""
        SELECT DISTINCT insurance_company, COUNT(*) as claim_count
        FROM insurance_claims
        WHERE deleted_at IS NULL AND insurance_company IS NOT NULL
        GROUP BY insurance_company
        ORDER BY claim_count DESC
    """)

    return jsonify({'companies': companies})
