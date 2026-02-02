"""
Invoices API Routes
===================
RESTful API for invoice management.
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, date
import json
from src.core.auth.decorators import login_required
from src.db.database import Database

invoices_api_bp = Blueprint('invoices_api', __name__, url_prefix='/api/invoices')


def get_db():
    """Get database connection using CRM database"""
    # Use CRM database for invoices
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    db_path = os.path.join(project_root, 'data', 'hailtracker_crm.db')
    return Database(db_path)


def generate_invoice_number(db):
    """Generate next invoice number"""
    result = db.execute("""
        SELECT invoice_number FROM invoices
        ORDER BY id DESC LIMIT 1
    """)
    if result and result[0]['invoice_number']:
        last = result[0]['invoice_number']
        num = int(last.replace('INV-', '')) + 1
    else:
        num = 1001
    return f"INV-{num:05d}"


@invoices_api_bp.route('')
@login_required
def list_invoices():
    """List invoices with filtering"""
    db = get_db()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    offset = (page - 1) * per_page

    # Filters
    status = request.args.get('status')
    customer_id = request.args.get('customer_id', type=int)
    job_id = request.args.get('job_id', type=int)

    # Build query
    where_clauses = ['1=1']
    params = []

    if status:
        where_clauses.append('i.status = ?')
        params.append(status.upper())

    if customer_id:
        where_clauses.append('i.customer_id = ?')
        params.append(customer_id)

    if job_id:
        where_clauses.append('i.job_id = ?')
        params.append(job_id)

    where_sql = ' AND '.join(where_clauses)

    # Get invoices
    invoices = db.execute(f"""
        SELECT
            i.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.email as customer_email,
            j.job_number
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN jobs j ON i.job_id = j.id
        WHERE {where_sql}
        ORDER BY i.created_at DESC
        LIMIT ? OFFSET ?
    """, tuple(params) + (per_page, offset))

    # Get total count
    count_result = db.execute(f"""
        SELECT COUNT(*) as total FROM invoices i WHERE {where_sql}
    """, tuple(params))
    total = count_result[0]['total'] if count_result else 0

    # Get stats
    stats = db.execute("""
        SELECT
            SUM(CASE WHEN status = 'DRAFT' THEN 1 ELSE 0 END) as draft_count,
            SUM(CASE WHEN status = 'SENT' THEN 1 ELSE 0 END) as sent_count,
            SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) as overdue_count,
            SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_count,
            SUM(CASE WHEN status = 'PAID' THEN total ELSE 0 END) as total_paid,
            SUM(balance_due) as total_outstanding
        FROM invoices
    """)

    return jsonify({
        'invoices': invoices,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
        'stats': stats[0] if stats else {}
    })


@invoices_api_bp.route('/<int:invoice_id>')
@login_required
def get_invoice(invoice_id):
    """Get invoice details"""
    db = get_db()

    invoice = db.execute("""
        SELECT
            i.*,
            c.first_name || ' ' || c.last_name as customer_name,
            c.email as customer_email,
            c.phone as customer_phone,
            c.address_line1, c.city, c.state, c.zip_code,
            j.job_number,
            j.vehicle_year, j.vehicle_make, j.vehicle_model
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        LEFT JOIN jobs j ON i.job_id = j.id
        WHERE i.id = ?
    """, (invoice_id,))

    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    invoice = invoice[0]

    # Parse line items JSON
    if invoice.get('line_items'):
        try:
            invoice['line_items'] = json.loads(invoice['line_items'])
        except:
            invoice['line_items'] = []

    # Get payments
    payments = db.execute("""
        SELECT * FROM payments
        WHERE invoice_id = ?
        ORDER BY payment_date DESC
    """, (invoice_id,))
    invoice['payments'] = payments

    return jsonify(invoice)


@invoices_api_bp.route('', methods=['POST'])
@login_required
def create_invoice():
    """Create new invoice"""
    db = get_db()
    data = request.get_json()

    if not data.get('job_id') or not data.get('customer_id'):
        return jsonify({'error': 'job_id and customer_id are required'}), 400

    invoice_number = generate_invoice_number(db)

    # Calculate totals from line items
    line_items = data.get('line_items', [])
    subtotal = sum(item.get('quantity', 1) * item.get('price', 0) for item in line_items)
    tax_rate = data.get('tax_rate', 0)
    tax_amount = subtotal * (tax_rate / 100)
    total = subtotal + tax_amount

    invoice_id = db.execute("""
        INSERT INTO invoices (
            invoice_number, job_id, customer_id, status,
            subtotal, tax_amount, total, balance_due,
            line_items, invoice_date, due_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_number,
        data['job_id'],
        data['customer_id'],
        data.get('status', 'DRAFT'),
        subtotal,
        tax_amount,
        total,
        total,  # balance_due starts as total
        json.dumps(line_items),
        data.get('invoice_date', date.today().isoformat()),
        data.get('due_date'),
        data.get('notes')
    ))

    return jsonify({
        'id': invoice_id,
        'invoice_number': invoice_number,
        'message': 'Invoice created successfully'
    }), 201


@invoices_api_bp.route('/<int:invoice_id>', methods=['PUT'])
@login_required
def update_invoice(invoice_id):
    """Update invoice"""
    db = get_db()
    data = request.get_json()

    # Verify exists
    existing = db.execute("SELECT id, status FROM invoices WHERE id = ?", (invoice_id,))
    if not existing:
        return jsonify({'error': 'Invoice not found'}), 404

    # Calculate totals if line items provided
    line_items = data.get('line_items')
    if line_items:
        subtotal = sum(item.get('quantity', 1) * item.get('price', 0) for item in line_items)
        tax_rate = data.get('tax_rate', 0)
        tax_amount = subtotal * (tax_rate / 100)
        total = subtotal + tax_amount

        # Get amount already paid
        paid_result = db.execute("SELECT amount_paid FROM invoices WHERE id = ?", (invoice_id,))
        amount_paid = paid_result[0]['amount_paid'] or 0 if paid_result else 0
        balance_due = total - amount_paid
    else:
        subtotal = data.get('subtotal')
        tax_amount = data.get('tax_amount')
        total = data.get('total')
        balance_due = data.get('balance_due')

    db.execute("""
        UPDATE invoices SET
            status = COALESCE(?, status),
            subtotal = COALESCE(?, subtotal),
            tax_amount = COALESCE(?, tax_amount),
            total = COALESCE(?, total),
            balance_due = COALESCE(?, balance_due),
            line_items = COALESCE(?, line_items),
            due_date = COALESCE(?, due_date),
            notes = COALESCE(?, notes),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        data.get('status'),
        subtotal,
        tax_amount,
        total,
        balance_due,
        json.dumps(line_items) if line_items else None,
        data.get('due_date'),
        data.get('notes'),
        invoice_id
    ))

    return jsonify({'message': 'Invoice updated successfully'})


@invoices_api_bp.route('/<int:invoice_id>', methods=['DELETE'])
@login_required
def delete_invoice(invoice_id):
    """Delete invoice (only drafts)"""
    db = get_db()

    existing = db.execute("SELECT status FROM invoices WHERE id = ?", (invoice_id,))
    if not existing:
        return jsonify({'error': 'Invoice not found'}), 404

    if existing[0]['status'] != 'DRAFT':
        return jsonify({'error': 'Can only delete draft invoices'}), 400

    db.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    return jsonify({'message': 'Invoice deleted successfully'})


@invoices_api_bp.route('/<int:invoice_id>/send', methods=['POST'])
@login_required
def send_invoice(invoice_id):
    """Mark invoice as sent"""
    db = get_db()

    db.execute("""
        UPDATE invoices SET
            status = 'SENT',
            sent_date = CURRENT_DATE,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (invoice_id,))

    return jsonify({'message': 'Invoice sent successfully'})


@invoices_api_bp.route('/<int:invoice_id>/payments', methods=['POST'])
@login_required
def add_payment(invoice_id):
    """Add payment to invoice"""
    db = get_db()
    data = request.get_json()

    if not data.get('amount'):
        return jsonify({'error': 'amount is required'}), 400

    # Get invoice
    invoice = db.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    invoice = invoice[0]
    amount = float(data['amount'])
    new_amount_paid = (invoice['amount_paid'] or 0) + amount
    new_balance = invoice['total'] - new_amount_paid

    # Determine new status
    if new_balance <= 0:
        new_status = 'PAID'
    elif new_amount_paid > 0:
        new_status = 'PARTIAL_PAID'
    else:
        new_status = invoice['status']

    # Create payment record
    payment_id = db.execute("""
        INSERT INTO payments (
            invoice_id, job_id, amount, payment_method,
            payment_reference, payment_date, total_amount,
            payer_type, payer_name, notes, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_id,
        invoice['job_id'],
        amount,
        data.get('payment_method'),
        data.get('payment_reference'),
        data.get('payment_date', date.today().isoformat()),
        amount,
        data.get('payer_type', 'CUSTOMER'),
        data.get('payer_name'),
        data.get('notes'),
        g.current_user.get('username', 'system')
    ))

    # Update invoice
    db.execute("""
        UPDATE invoices SET
            amount_paid = ?,
            balance_due = ?,
            status = ?,
            paid_date = CASE WHEN ? = 'PAID' THEN CURRENT_DATE ELSE paid_date END,
            payment_method = ?,
            payment_reference = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        new_amount_paid,
        new_balance,
        new_status,
        new_status,
        data.get('payment_method'),
        data.get('payment_reference'),
        invoice_id
    ))

    return jsonify({
        'payment_id': payment_id,
        'new_balance': new_balance,
        'status': new_status,
        'message': 'Payment recorded successfully'
    })
