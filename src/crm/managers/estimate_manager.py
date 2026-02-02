"""
Estimate Manager
Professional estimate building with templates, line items, and invoice conversion

PDR CRM Part 6 - Professional Estimates!

FEATURES:
- Template-based estimates (HAIL_BASIC, HAIL_SEVERE, DOOR_DING, CUSTOM)
- Line item management (LABOR + PART types)
- Tax calculations
- Status tracking (DRAFT -> SENT -> VIEWED -> APPROVED -> DECLINED)
- Convert estimate to invoice
- Professional formatting
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json


class EstimateManager:
    """
    Manage professional estimates with templates and line items

    This is the sales tool for PDR shops
    """

    # Estimate templates with default line items
    TEMPLATES = {
        'HAIL_BASIC': {
            'name': 'Basic Hail Damage',
            'description': 'Light hail damage - scattered dents, no broken glass',
            'default_items': [
                {'type': 'LABOR', 'description': 'PDR - Hood', 'quantity': 1, 'unit_price': 350.00},
                {'type': 'LABOR', 'description': 'PDR - Roof', 'quantity': 1, 'unit_price': 500.00},
                {'type': 'LABOR', 'description': 'PDR - Trunk/Decklid', 'quantity': 1, 'unit_price': 300.00},
            ],
            'labor_rate': 75.00
        },
        'HAIL_SEVERE': {
            'name': 'Severe Hail Damage',
            'description': 'Heavy hail damage - extensive dents, possible glass replacement',
            'default_items': [
                {'type': 'LABOR', 'description': 'PDR - Hood (Heavy)', 'quantity': 1, 'unit_price': 600.00},
                {'type': 'LABOR', 'description': 'PDR - Roof (Heavy)', 'quantity': 1, 'unit_price': 900.00},
                {'type': 'LABOR', 'description': 'PDR - Trunk/Decklid (Heavy)', 'quantity': 1, 'unit_price': 500.00},
                {'type': 'LABOR', 'description': 'PDR - Left Fender', 'quantity': 1, 'unit_price': 400.00},
                {'type': 'LABOR', 'description': 'PDR - Right Fender', 'quantity': 1, 'unit_price': 400.00},
                {'type': 'LABOR', 'description': 'PDR - Left Quarter Panel', 'quantity': 1, 'unit_price': 450.00},
                {'type': 'LABOR', 'description': 'PDR - Right Quarter Panel', 'quantity': 1, 'unit_price': 450.00},
            ],
            'labor_rate': 85.00
        },
        'DOOR_DING': {
            'name': 'Door Ding Repair',
            'description': 'Single or multiple door dings',
            'default_items': [
                {'type': 'LABOR', 'description': 'PDR - Door Ding Repair', 'quantity': 1, 'unit_price': 150.00},
            ],
            'labor_rate': 75.00
        },
        'CUSTOM': {
            'name': 'Custom Estimate',
            'description': 'Build your own estimate',
            'default_items': [],
            'labor_rate': 75.00
        }
    }

    # Valid status transitions
    VALID_TRANSITIONS = {
        'DRAFT': ['SENT', 'DECLINED'],
        'SENT': ['VIEWED', 'APPROVED', 'DECLINED'],
        'VIEWED': ['APPROVED', 'DECLINED', 'SENT'],
        'APPROVED': ['DECLINED'],  # Can undo approval
        'DECLINED': ['DRAFT']  # Can revise
    }

    def __init__(self, db):
        """Initialize estimate manager with database connection"""
        self.db = db

    # ========================================================================
    # ESTIMATE CREATION
    # ========================================================================

    def create_estimate(
        self,
        job_id: int,
        template: str = 'CUSTOM',
        labor_rate: Optional[float] = None,
        tax_rate: float = 0.0,
        expires_days: int = 30,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create a new estimate from template

        Args:
            job_id: Job ID
            template: HAIL_BASIC, HAIL_SEVERE, DOOR_DING, CUSTOM
            labor_rate: Override default labor rate
            tax_rate: Tax percentage (0.0 - 100.0)
            expires_days: Days until estimate expires
            notes: Estimate notes
            terms: Terms and conditions
            created_by: Who created the estimate

        Returns:
            Estimate ID
        """
        # Get template
        tmpl = self.TEMPLATES.get(template, self.TEMPLATES['CUSTOM'])

        # Generate estimate number
        estimate_number = self._generate_estimate_number()

        # Use template labor rate if not overridden
        if labor_rate is None:
            labor_rate = tmpl.get('labor_rate', 75.00)

        # Default terms if not provided
        if terms is None:
            terms = self._get_default_terms()

        # Calculate expiration date
        expires_date = (date.today() + timedelta(days=expires_days)).isoformat()

        # Create line items from template
        line_items = []
        for item in tmpl.get('default_items', []):
            line_items.append({
                'type': item['type'],
                'description': item['description'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price'],
                'total': item['quantity'] * item['unit_price']
            })

        # Calculate totals
        totals = self._calculate_totals(line_items, labor_rate, tax_rate)

        # Insert estimate
        estimate_data = {
            'estimate_number': estimate_number,
            'job_id': job_id,
            'status': 'DRAFT',
            'labor_rate': labor_rate,
            'labor_hours': totals['labor_hours'],
            'labor_total': totals['labor_total'],
            'parts_total': totals['parts_total'],
            'subtotal': totals['subtotal'],
            'tax_rate': tax_rate,
            'tax_amount': totals['tax_amount'],
            'total': totals['total'],
            'line_items': json.dumps(line_items),
            'created_date': date.today().isoformat(),
            'expires_date': expires_date,
            'notes': notes,
            'terms': terms,
            'created_by': created_by
        }

        estimate_id = self.db.insert('estimates', estimate_data)

        # Update job with estimate reference
        self.db.execute("""
            UPDATE jobs SET estimate_id = ?, total_estimate = ?, updated_at = ?
            WHERE id = ?
        """, (estimate_id, totals['total'], datetime.now().isoformat(), job_id))

        print(f"[OK] Created estimate #{estimate_number} (ID: {estimate_id})")
        print(f"     Template: {template} ({tmpl['name']})")
        print(f"     Total: ${totals['total']:,.2f}")

        return estimate_id

    def _generate_estimate_number(self) -> str:
        """Generate unique estimate number: EST-2024-0001"""
        year = datetime.now().year

        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM estimates
            WHERE estimate_number LIKE ?
        """, (f"EST-{year}-%",))

        count = result[0]['count'] + 1

        return f"EST-{year}-{count:04d}"

    def _get_default_terms(self) -> str:
        """Get default terms and conditions"""
        return """TERMS AND CONDITIONS:
1. This estimate is valid for 30 days from the date issued.
2. Prices are subject to change upon inspection of actual damage.
3. Payment is due upon completion unless otherwise arranged.
4. A supplement may be required if additional damage is discovered.
5. We warranty our work for the life of your ownership.

ACCEPTED BY:

_____________________________    ______________
Customer Signature                Date"""

    # ========================================================================
    # LINE ITEM MANAGEMENT
    # ========================================================================

    def add_line_item(
        self,
        estimate_id: int,
        item_type: str,
        description: str,
        quantity: float = 1,
        unit_price: float = 0.0,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add a line item to an estimate

        Args:
            estimate_id: Estimate ID
            item_type: LABOR or PART
            description: Item description
            quantity: Quantity
            unit_price: Price per unit
            notes: Optional item notes

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate['status'] != 'DRAFT':
            raise ValueError(f"Cannot modify estimate in {estimate['status']} status")

        # Get current line items
        line_items = json.loads(estimate['line_items'] or '[]')

        # Add new item
        new_item = {
            'type': item_type.upper(),
            'description': description,
            'quantity': quantity,
            'unit_price': unit_price,
            'total': quantity * unit_price,
            'notes': notes
        }
        line_items.append(new_item)

        # Recalculate totals
        totals = self._calculate_totals(
            line_items,
            estimate['labor_rate'],
            estimate['tax_rate']
        )

        # Update estimate
        self._update_estimate_totals(estimate_id, line_items, totals)

        print(f"[OK] Added line item: {description} (${unit_price:,.2f})")

        return True

    def update_line_item(
        self,
        estimate_id: int,
        item_index: int,
        description: Optional[str] = None,
        quantity: Optional[float] = None,
        unit_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update a line item

        Args:
            estimate_id: Estimate ID
            item_index: Index of item to update (0-based)

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate['status'] != 'DRAFT':
            raise ValueError(f"Cannot modify estimate in {estimate['status']} status")

        # Get current line items
        line_items = json.loads(estimate['line_items'] or '[]')

        if item_index < 0 or item_index >= len(line_items):
            raise ValueError(f"Invalid item index: {item_index}")

        # Update item
        if description is not None:
            line_items[item_index]['description'] = description
        if quantity is not None:
            line_items[item_index]['quantity'] = quantity
        if unit_price is not None:
            line_items[item_index]['unit_price'] = unit_price
        if notes is not None:
            line_items[item_index]['notes'] = notes

        # Recalculate item total
        item = line_items[item_index]
        item['total'] = item['quantity'] * item['unit_price']

        # Recalculate totals
        totals = self._calculate_totals(
            line_items,
            estimate['labor_rate'],
            estimate['tax_rate']
        )

        # Update estimate
        self._update_estimate_totals(estimate_id, line_items, totals)

        print(f"[OK] Updated line item {item_index}: {item['description']}")

        return True

    def remove_line_item(self, estimate_id: int, item_index: int) -> bool:
        """
        Remove a line item from estimate

        Args:
            estimate_id: Estimate ID
            item_index: Index of item to remove (0-based)

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate['status'] != 'DRAFT':
            raise ValueError(f"Cannot modify estimate in {estimate['status']} status")

        # Get current line items
        line_items = json.loads(estimate['line_items'] or '[]')

        if item_index < 0 or item_index >= len(line_items):
            raise ValueError(f"Invalid item index: {item_index}")

        # Remove item
        removed = line_items.pop(item_index)

        # Recalculate totals
        totals = self._calculate_totals(
            line_items,
            estimate['labor_rate'],
            estimate['tax_rate']
        )

        # Update estimate
        self._update_estimate_totals(estimate_id, line_items, totals)

        print(f"[OK] Removed line item: {removed['description']}")

        return True

    def _update_estimate_totals(
        self,
        estimate_id: int,
        line_items: List[Dict],
        totals: Dict
    ):
        """Update estimate with new line items and totals"""
        self.db.execute("""
            UPDATE estimates SET
                line_items = ?,
                labor_hours = ?,
                labor_total = ?,
                parts_total = ?,
                subtotal = ?,
                tax_amount = ?,
                total = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            json.dumps(line_items),
            totals['labor_hours'],
            totals['labor_total'],
            totals['parts_total'],
            totals['subtotal'],
            totals['tax_amount'],
            totals['total'],
            datetime.now().isoformat(),
            estimate_id
        ))

        # Also update job total
        estimate = self.db.get_by_id('estimates', estimate_id)
        if estimate and estimate.get('job_id'):
            self.db.execute("""
                UPDATE jobs SET total_estimate = ?, updated_at = ?
                WHERE id = ?
            """, (totals['total'], datetime.now().isoformat(), estimate['job_id']))

    def _calculate_totals(
        self,
        line_items: List[Dict],
        labor_rate: float,
        tax_rate: float
    ) -> Dict:
        """
        Calculate all totals from line items

        Returns dict with:
            labor_hours, labor_total, parts_total, subtotal, tax_amount, total
        """
        labor_total = 0.0
        parts_total = 0.0
        labor_hours = 0.0

        for item in line_items:
            item_total = item.get('quantity', 1) * item.get('unit_price', 0)

            if item.get('type', '').upper() == 'LABOR':
                labor_total += item_total
                # Estimate hours based on labor rate
                if labor_rate > 0:
                    labor_hours += item_total / labor_rate
            else:
                parts_total += item_total

        subtotal = labor_total + parts_total
        tax_amount = subtotal * (tax_rate / 100.0)
        total = subtotal + tax_amount

        return {
            'labor_hours': round(labor_hours, 2),
            'labor_total': round(labor_total, 2),
            'parts_total': round(parts_total, 2),
            'subtotal': round(subtotal, 2),
            'tax_amount': round(tax_amount, 2),
            'total': round(total, 2)
        }

    # ========================================================================
    # STATUS MANAGEMENT
    # ========================================================================

    def update_status(
        self,
        estimate_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update estimate status

        Args:
            estimate_id: Estimate ID
            new_status: DRAFT, SENT, VIEWED, APPROVED, DECLINED
            notes: Optional notes

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        current_status = estimate['status']

        # Validate transition
        valid_next = self.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in valid_next:
            raise ValueError(
                f"Invalid status transition: {current_status} -> {new_status}. "
                f"Valid transitions: {', '.join(valid_next)}"
            )

        # Prepare update
        update_data = {
            'status': new_status,
            'notes': notes if notes else estimate.get('notes')
        }

        # Set date fields based on status
        now = datetime.now().isoformat()
        if new_status == 'SENT':
            update_data['sent_date'] = date.today().isoformat()
        elif new_status == 'VIEWED':
            update_data['viewed_date'] = date.today().isoformat()
        elif new_status == 'APPROVED':
            update_data['approved_date'] = date.today().isoformat()

        # Build update query
        set_clauses = [f"{k} = ?" for k in update_data.keys()]
        set_clauses.append("updated_at = ?")
        query = f"UPDATE estimates SET {', '.join(set_clauses)} WHERE id = ?"
        values = list(update_data.values()) + [now, estimate_id]

        self.db.execute(query, tuple(values))

        print(f"[OK] Estimate #{estimate['estimate_number']}: {current_status} -> {new_status}")

        return True

    def mark_sent(self, estimate_id: int) -> bool:
        """Mark estimate as sent to customer"""
        return self.update_status(estimate_id, 'SENT')

    def mark_viewed(self, estimate_id: int) -> bool:
        """Mark estimate as viewed by customer"""
        return self.update_status(estimate_id, 'VIEWED')

    def mark_approved(self, estimate_id: int) -> bool:
        """Mark estimate as approved by customer"""
        return self.update_status(estimate_id, 'APPROVED')

    def mark_declined(self, estimate_id: int, reason: Optional[str] = None) -> bool:
        """Mark estimate as declined"""
        return self.update_status(estimate_id, 'DECLINED', notes=reason)

    # ========================================================================
    # CONVERT TO INVOICE
    # ========================================================================

    def convert_to_invoice(
        self,
        estimate_id: int,
        due_days: int = 30,
        created_by: Optional[str] = None
    ) -> int:
        """
        Convert approved estimate to invoice

        Args:
            estimate_id: Estimate ID
            due_days: Days until invoice is due
            created_by: Who created the invoice

        Returns:
            Invoice ID
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate['status'] != 'APPROVED':
            raise ValueError(f"Estimate must be APPROVED to convert to invoice. Current: {estimate['status']}")

        # Get job info for customer_id
        job = self.db.execute("""
            SELECT * FROM jobs WHERE id = ?
        """, (estimate['job_id'],))

        if not job:
            raise ValueError(f"Job {estimate['job_id']} not found")

        job = job[0]

        # Generate invoice number
        invoice_number = self._generate_invoice_number()

        # Create invoice
        invoice_data = {
            'invoice_number': invoice_number,
            'job_id': estimate['job_id'],
            'customer_id': job['customer_id'],
            'status': 'DRAFT',
            'subtotal': estimate['subtotal'],
            'tax_amount': estimate['tax_amount'],
            'total': estimate['total'],
            'amount_paid': 0.0,
            'balance_due': estimate['total'],
            'line_items': estimate['line_items'],
            'invoice_date': date.today().isoformat(),
            'due_date': (date.today() + timedelta(days=due_days)).isoformat(),
            'notes': estimate['notes']
        }

        invoice_id = self.db.insert('invoices', invoice_data)

        # Update job with invoice reference
        self.db.execute("""
            UPDATE jobs SET invoice_id = ?, total_actual = ?, updated_at = ?
            WHERE id = ?
        """, (invoice_id, estimate['total'], datetime.now().isoformat(), estimate['job_id']))

        print(f"[OK] Created invoice #{invoice_number} from estimate #{estimate['estimate_number']}")
        print(f"     Total: ${estimate['total']:,.2f}")
        print(f"     Due: {invoice_data['due_date']}")

        return invoice_id

    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number: INV-2024-0001"""
        year = datetime.now().year

        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM invoices
            WHERE invoice_number LIKE ?
        """, (f"INV-{year}-%",))

        count = result[0]['count'] + 1

        return f"INV-{year}-{count:04d}"

    # ========================================================================
    # ESTIMATE RETRIEVAL
    # ========================================================================

    def get_estimate(self, estimate_id: int) -> Optional[Dict]:
        """
        Get estimate details

        Returns estimate with parsed line_items
        """
        result = self.db.execute("""
            SELECT e.*,
                   j.job_number,
                   j.customer_id,
                   c.first_name || ' ' || c.last_name as customer_name,
                   c.email as customer_email,
                   c.phone as customer_phone,
                   v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM estimates e
            JOIN jobs j ON j.id = e.job_id
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE e.id = ?
        """, (estimate_id,))

        if not result:
            return None

        estimate = result[0]

        # Parse line items
        if estimate.get('line_items'):
            estimate['line_items_parsed'] = json.loads(estimate['line_items'])
        else:
            estimate['line_items_parsed'] = []

        # Calculate item count
        estimate['item_count'] = len(estimate['line_items_parsed'])

        return estimate

    def get_estimate_by_number(self, estimate_number: str) -> Optional[Dict]:
        """Get estimate by estimate number"""
        result = self.db.execute("""
            SELECT id FROM estimates WHERE estimate_number = ?
        """, (estimate_number,))

        if result:
            return self.get_estimate(result[0]['id'])
        return None

    def get_estimates_for_job(self, job_id: int) -> List[Dict]:
        """Get all estimates for a job"""
        results = self.db.execute("""
            SELECT * FROM estimates WHERE job_id = ?
            ORDER BY created_at DESC
        """, (job_id,))

        for est in results:
            if est.get('line_items'):
                est['line_items_parsed'] = json.loads(est['line_items'])

        return results

    def search_estimates(
        self,
        status: Optional[str] = None,
        customer_id: Optional[int] = None,
        search_term: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        expired_only: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search estimates with filters
        """
        query = """
            SELECT e.*,
                   j.job_number,
                   c.first_name || ' ' || c.last_name as customer_name,
                   v.year || ' ' || v.make || ' ' || v.model as vehicle_description
            FROM estimates e
            JOIN jobs j ON j.id = e.job_id
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE 1=1
        """

        params = []

        if status:
            query += " AND e.status = ?"
            params.append(status)

        if customer_id:
            query += " AND j.customer_id = ?"
            params.append(customer_id)

        if search_term:
            query += """ AND (
                e.estimate_number LIKE ? OR
                c.first_name LIKE ? OR
                c.last_name LIKE ? OR
                j.job_number LIKE ?
            )"""
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern] * 4)

        if start_date:
            query += " AND e.created_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND e.created_date <= ?"
            params.append(end_date.isoformat())

        if expired_only:
            query += " AND e.expires_date < date('now') AND e.status IN ('DRAFT', 'SENT', 'VIEWED')"

        query += " ORDER BY e.created_at DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_pending_estimates(self) -> List[Dict]:
        """Get estimates awaiting customer response"""
        return self.search_estimates(status='SENT')

    def get_expired_estimates(self) -> List[Dict]:
        """Get expired estimates that haven't been approved"""
        return self.search_estimates(expired_only=True)

    # ========================================================================
    # ESTIMATE FORMATTING
    # ========================================================================

    def format_estimate(self, estimate_id: int) -> str:
        """
        Format estimate for display/print

        Returns formatted string
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            return "Estimate not found"

        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("                        ESTIMATE")
        lines.append("=" * 70)
        lines.append("")

        # Estimate info
        lines.append(f"Estimate #: {estimate['estimate_number']}")
        lines.append(f"Date: {estimate['created_date']}")
        lines.append(f"Expires: {estimate['expires_date']}")
        lines.append(f"Status: {estimate['status']}")
        lines.append("")

        # Customer info
        lines.append("CUSTOMER:")
        lines.append(f"  {estimate['customer_name']}")
        if estimate.get('customer_email'):
            lines.append(f"  {estimate['customer_email']}")
        if estimate.get('customer_phone'):
            lines.append(f"  {estimate['customer_phone']}")
        lines.append("")

        # Vehicle info
        lines.append("VEHICLE:")
        lines.append(f"  {estimate['vehicle_description']}")
        lines.append(f"  Job #: {estimate['job_number']}")
        lines.append("")

        # Line items
        lines.append("-" * 70)
        lines.append(f"{'Description':<40} {'Qty':>6} {'Price':>10} {'Total':>10}")
        lines.append("-" * 70)

        for item in estimate['line_items_parsed']:
            qty = item.get('quantity', 1)
            price = item.get('unit_price', 0)
            total = item.get('total', qty * price)
            desc = item.get('description', '')[:38]
            item_type = f"[{item.get('type', 'ITEM')[:1]}]"

            lines.append(
                f"{item_type} {desc:<37} {qty:>6.1f} ${price:>9,.2f} ${total:>9,.2f}"
            )

        lines.append("-" * 70)

        # Totals
        lines.append(f"{'Labor:':<50} ${estimate['labor_total']:>16,.2f}")
        lines.append(f"{'Parts:':<50} ${estimate['parts_total']:>16,.2f}")
        lines.append("-" * 70)
        lines.append(f"{'Subtotal:':<50} ${estimate['subtotal']:>16,.2f}")

        if estimate['tax_rate'] > 0:
            lines.append(f"{'Tax (' + str(estimate['tax_rate']) + '%):':<50} ${estimate['tax_amount']:>16,.2f}")

        lines.append("=" * 70)
        lines.append(f"{'TOTAL:':<50} ${estimate['total']:>16,.2f}")
        lines.append("=" * 70)

        # Notes
        if estimate.get('notes'):
            lines.append("")
            lines.append("NOTES:")
            lines.append(estimate['notes'])

        # Terms
        if estimate.get('terms'):
            lines.append("")
            lines.append(estimate['terms'])

        return '\n'.join(lines)

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_estimate_stats(self, days: int = 30) -> Dict:
        """Get estimate statistics for dashboard"""
        stats = {}

        # Total estimates
        result = self.db.execute("""
            SELECT COUNT(*) as count, SUM(total) as total_value
            FROM estimates
            WHERE created_date >= date('now', '-' || ? || ' days')
        """, (days,))
        stats['total_estimates'] = result[0]['count'] or 0
        stats['total_value'] = result[0]['total_value'] or 0

        # By status
        result = self.db.execute("""
            SELECT status, COUNT(*) as count, SUM(total) as value
            FROM estimates
            WHERE created_date >= date('now', '-' || ? || ' days')
            GROUP BY status
        """, (days,))

        stats['by_status'] = {}
        for row in result:
            stats['by_status'][row['status']] = {
                'count': row['count'],
                'value': row['value'] or 0
            }

        # Approval rate
        approved = stats['by_status'].get('APPROVED', {}).get('count', 0)
        declined = stats['by_status'].get('DECLINED', {}).get('count', 0)
        total_decided = approved + declined

        if total_decided > 0:
            stats['approval_rate'] = round((approved / total_decided) * 100, 1)
        else:
            stats['approval_rate'] = 0

        # Average estimate value
        if stats['total_estimates'] > 0:
            stats['avg_estimate_value'] = round(stats['total_value'] / stats['total_estimates'], 2)
        else:
            stats['avg_estimate_value'] = 0

        # Pending estimates
        result = self.db.execute("""
            SELECT COUNT(*) as count, SUM(total) as value
            FROM estimates
            WHERE status IN ('DRAFT', 'SENT', 'VIEWED')
        """)
        stats['pending_count'] = result[0]['count'] or 0
        stats['pending_value'] = result[0]['value'] or 0

        # Expired estimates
        result = self.db.execute("""
            SELECT COUNT(*) as count, SUM(total) as value
            FROM estimates
            WHERE status IN ('DRAFT', 'SENT', 'VIEWED')
              AND expires_date < date('now')
        """)
        stats['expired_count'] = result[0]['count'] or 0
        stats['expired_value'] = result[0]['value'] or 0

        return stats

    def get_templates(self) -> Dict:
        """Get available estimate templates"""
        return self.TEMPLATES.copy()

    def update_estimate(
        self,
        estimate_id: int,
        labor_rate: Optional[float] = None,
        tax_rate: Optional[float] = None,
        notes: Optional[str] = None,
        terms: Optional[str] = None,
        expires_date: Optional[date] = None
    ) -> bool:
        """
        Update estimate properties

        Args:
            estimate_id: Estimate ID
            labor_rate: New labor rate
            tax_rate: New tax rate
            notes: New notes
            terms: New terms
            expires_date: New expiration date

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        if estimate['status'] != 'DRAFT':
            raise ValueError(f"Cannot modify estimate in {estimate['status']} status")

        updates = {}

        if labor_rate is not None:
            updates['labor_rate'] = labor_rate
        if tax_rate is not None:
            updates['tax_rate'] = tax_rate
        if notes is not None:
            updates['notes'] = notes
        if terms is not None:
            updates['terms'] = terms
        if expires_date is not None:
            updates['expires_date'] = expires_date.isoformat()

        if not updates:
            return True

        # If rate changed, recalculate totals
        if labor_rate is not None or tax_rate is not None:
            line_items = estimate['line_items_parsed']
            new_labor_rate = labor_rate if labor_rate is not None else estimate['labor_rate']
            new_tax_rate = tax_rate if tax_rate is not None else estimate['tax_rate']

            totals = self._calculate_totals(line_items, new_labor_rate, new_tax_rate)

            updates.update({
                'labor_hours': totals['labor_hours'],
                'labor_total': totals['labor_total'],
                'parts_total': totals['parts_total'],
                'subtotal': totals['subtotal'],
                'tax_amount': totals['tax_amount'],
                'total': totals['total']
            })

        # Build update query
        set_clauses = [f"{k} = ?" for k in updates.keys()]
        set_clauses.append("updated_at = ?")
        query = f"UPDATE estimates SET {', '.join(set_clauses)} WHERE id = ?"
        values = list(updates.values()) + [datetime.now().isoformat(), estimate_id]

        self.db.execute(query, tuple(values))

        print(f"[OK] Updated estimate #{estimate['estimate_number']}")

        return True

    def duplicate_estimate(
        self,
        estimate_id: int,
        new_job_id: Optional[int] = None
    ) -> int:
        """
        Duplicate an existing estimate

        Args:
            estimate_id: Estimate to duplicate
            new_job_id: Optional different job (defaults to same job)

        Returns:
            New estimate ID
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Create new estimate with same line items
        new_estimate_number = self._generate_estimate_number()

        estimate_data = {
            'estimate_number': new_estimate_number,
            'job_id': new_job_id or estimate['job_id'],
            'status': 'DRAFT',
            'labor_rate': estimate['labor_rate'],
            'labor_hours': estimate['labor_hours'],
            'labor_total': estimate['labor_total'],
            'parts_total': estimate['parts_total'],
            'subtotal': estimate['subtotal'],
            'tax_rate': estimate['tax_rate'],
            'tax_amount': estimate['tax_amount'],
            'total': estimate['total'],
            'line_items': estimate['line_items'],
            'created_date': date.today().isoformat(),
            'expires_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': estimate.get('notes'),
            'terms': estimate.get('terms')
        }

        new_id = self.db.insert('estimates', estimate_data)

        print(f"[OK] Duplicated estimate #{estimate['estimate_number']} -> #{new_estimate_number}")

        return new_id

    # ========================================================================
    # ADVANCED ESTIMATING - R/I, PARTS, INSURANCE INTEGRATION
    # ========================================================================

    def calculate_full_totals(self, estimate_id: int) -> Dict:
        """
        Calculate complete estimate totals including PDR labor, R/I labor, Parts, Materials.

        This integrates with the new estimate_ri_items and estimate_parts tables.

        Returns:
            Dict with pdr_labor, ri_labor, parts, materials, subtotal, tax, total
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Get PDR labor from line items (existing system)
        line_items = estimate.get('line_items_parsed', [])
        pdr_labor = sum(
            item.get('total', 0)
            for item in line_items
            if item.get('type', '').upper() == 'LABOR'
        )

        # Get R/I labor from estimate_ri_items table
        ri_result = self.db.execute("""
            SELECT COALESCE(SUM(line_total), 0) as total
            FROM estimate_ri_items WHERE estimate_id = ?
        """, (estimate_id,))
        ri_labor = ri_result[0]['total'] if ri_result else 0

        # Get parts from estimate_parts table
        parts_result = self.db.execute("""
            SELECT COALESCE(SUM(line_total), 0) as total
            FROM estimate_parts WHERE estimate_id = ?
        """, (estimate_id,))
        parts_total = parts_result[0]['total'] if parts_result else 0

        # Add parts from legacy line items
        legacy_parts = sum(
            item.get('total', 0)
            for item in line_items
            if item.get('type', '').upper() == 'PART'
        )
        parts_total += legacy_parts

        # Materials (typically a percentage or flat fee)
        # Check if materials field exists on estimate
        materials = estimate.get('materials_total', 0) or 0

        # Calculate totals
        subtotal = pdr_labor + ri_labor + parts_total + materials
        tax_rate = estimate.get('tax_rate', 0) or 0
        tax_amount = subtotal * (tax_rate / 100.0)
        total = subtotal + tax_amount

        result = {
            'estimate_id': estimate_id,
            'pdr_labor': round(pdr_labor, 2),
            'ri_labor': round(ri_labor, 2),
            'parts_total': round(parts_total, 2),
            'materials': round(materials, 2),
            'subtotal': round(subtotal, 2),
            'tax_rate': tax_rate,
            'tax_amount': round(tax_amount, 2),
            'total': round(total, 2),
            'breakdown': {
                'pdr_labor_pct': round((pdr_labor / subtotal * 100), 1) if subtotal > 0 else 0,
                'ri_labor_pct': round((ri_labor / subtotal * 100), 1) if subtotal > 0 else 0,
                'parts_pct': round((parts_total / subtotal * 100), 1) if subtotal > 0 else 0,
                'materials_pct': round((materials / subtotal * 100), 1) if subtotal > 0 else 0
            }
        }

        return result

    def link_insurance_claim(
        self,
        estimate_id: int,
        insurance_company_id: int,
        claim_number: str,
        adjuster_id: int = None,
        deductible: float = 0.0
    ) -> bool:
        """
        Link estimate to an insurance claim.

        Creates connection between estimate and insurance tracking system.

        Args:
            estimate_id: Estimate ID
            insurance_company_id: ID from insurance_companies table
            claim_number: Insurance claim number
            adjuster_id: Optional ID from insurance_adjusters table
            deductible: Customer deductible amount

        Returns:
            Success
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Update estimate with insurance fields
        self.db.execute("""
            UPDATE estimates SET
                insurance_company_id = ?,
                claim_number = ?,
                adjuster_id = ?,
                deductible = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            insurance_company_id,
            claim_number,
            adjuster_id,
            deductible,
            datetime.now().isoformat(),
            estimate_id
        ))

        # Get company name for logging
        company = self.db.execute("""
            SELECT name FROM insurance_companies WHERE id = ?
        """, (insurance_company_id,))
        company_name = company[0]['name'] if company else f"Company #{insurance_company_id}"

        print(f"[OK] Linked estimate #{estimate['estimate_number']} to {company_name}")
        print(f"     Claim: {claim_number}")
        if deductible > 0:
            print(f"     Deductible: ${deductible:,.2f}")

        return True

    def create_supplement(
        self,
        original_estimate_id: int,
        reason: str,
        notes: str = None
    ) -> int:
        """
        Create a supplement estimate for additional damage discovered.

        Supplements are common in PDR when damage is worse than initially estimated.

        Args:
            original_estimate_id: Original estimate ID
            reason: Reason for supplement (e.g., "Additional damage found during repair")
            notes: Additional notes

        Returns:
            New supplement estimate ID
        """
        original = self.get_estimate(original_estimate_id)
        if not original:
            raise ValueError(f"Original estimate {original_estimate_id} not found")

        # Generate supplement number
        supp_count = self.db.execute("""
            SELECT COUNT(*) as count FROM estimate_supplements
            WHERE original_estimate_id = ?
        """, (original_estimate_id,))
        supp_number = (supp_count[0]['count'] if supp_count else 0) + 1

        # Create new estimate for supplement
        new_estimate_number = f"{original['estimate_number']}-S{supp_number}"

        estimate_data = {
            'estimate_number': new_estimate_number,
            'job_id': original['job_id'],
            'status': 'DRAFT',
            'labor_rate': original['labor_rate'],
            'labor_hours': 0,
            'labor_total': 0,
            'parts_total': 0,
            'subtotal': 0,
            'tax_rate': original['tax_rate'],
            'tax_amount': 0,
            'total': 0,
            'line_items': json.dumps([]),
            'created_date': date.today().isoformat(),
            'expires_date': (date.today() + timedelta(days=30)).isoformat(),
            'notes': notes or f"Supplement #{supp_number}: {reason}",
            'terms': original.get('terms'),
            'is_supplement': 1,
            'parent_estimate_id': original_estimate_id
        }

        supplement_id = self.db.insert('estimates', estimate_data)

        # Record in estimate_supplements table
        self.db.execute("""
            INSERT INTO estimate_supplements (
                original_estimate_id, supplement_estimate_id,
                supplement_number, reason, status, created_at
            ) VALUES (?, ?, ?, ?, 'PENDING', ?)
        """, (
            original_estimate_id,
            supplement_id,
            supp_number,
            reason,
            datetime.now().isoformat()
        ))

        print(f"[OK] Created supplement #{new_estimate_number}")
        print(f"     Original: #{original['estimate_number']}")
        print(f"     Reason: {reason}")

        return supplement_id

    def get_estimate_for_export(self, estimate_id: int) -> Dict:
        """
        Get complete estimate data formatted for PDF generation.

        Includes all data needed for professional estimate documents.

        Returns:
            Dict with all estimate data organized for PDF export
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        # Get full totals
        totals = self.calculate_full_totals(estimate_id)

        # Get R/I items with details
        ri_items = self.db.execute("""
            SELECT eri.*, ri.code, ri.name as operation_name, ri.category
            FROM estimate_ri_items eri
            JOIN ri_operations ri ON ri.id = eri.ri_operation_id
            WHERE eri.estimate_id = ?
            ORDER BY ri.category, ri.name
        """, (estimate_id,))

        # Get parts with details
        parts = self.db.execute("""
            SELECT ep.*, pc.part_number, pc.name as part_name
            FROM estimate_parts ep
            LEFT JOIN parts_catalog pc ON pc.id = ep.part_id
            WHERE ep.estimate_id = ?
            ORDER BY ep.description
        """, (estimate_id,))

        # Get photos
        photos = self.db.execute("""
            SELECT * FROM estimate_photos
            WHERE estimate_id = ?
            ORDER BY photo_type, panel_name
        """, (estimate_id,))

        # Get vehicle info
        vehicle = self.db.execute("""
            SELECT v.*, dv.body_style, dv.has_sunroof, dv.has_roof_rails
            FROM vehicles v
            JOIN jobs j ON j.vehicle_id = v.id
            LEFT JOIN decoded_vehicles dv ON dv.vin = v.vin
            WHERE j.id = ?
        """, (estimate.get('job_id'),))
        vehicle_info = dict(vehicle[0]) if vehicle else {}

        # Get customer info
        customer = self.db.execute("""
            SELECT c.*, ca.street, ca.city, ca.state, ca.zip
            FROM customers c
            JOIN jobs j ON j.customer_id = c.id
            LEFT JOIN customer_addresses ca ON ca.customer_id = c.id AND ca.is_primary = 1
            WHERE j.id = ?
        """, (estimate.get('job_id'),))
        customer_info = dict(customer[0]) if customer else {}

        # Get insurance info if linked
        insurance_info = None
        if estimate.get('insurance_company_id'):
            ins = self.db.execute("""
                SELECT ic.*, ia.name as adjuster_name, ia.email as adjuster_email,
                       ia.phone as adjuster_phone
                FROM insurance_companies ic
                LEFT JOIN insurance_adjusters ia ON ia.id = ?
                WHERE ic.id = ?
            """, (estimate.get('adjuster_id'), estimate.get('insurance_company_id')))
            if ins:
                insurance_info = dict(ins[0])
                insurance_info['claim_number'] = estimate.get('claim_number')
                insurance_info['deductible'] = estimate.get('deductible', 0)

        # Get panel damage summary from dent maps
        panel_damage = self.db.execute("""
            SELECT panel, COUNT(*) as dent_count,
                   AVG(size) as avg_size,
                   SUM(CASE WHEN access_difficulty > 2 THEN 1 ELSE 0 END) as difficult_count
            FROM dents d
            JOIN dent_maps dm ON dm.id = d.dent_map_id
            WHERE dm.job_id = ?
            GROUP BY panel
            ORDER BY dent_count DESC
        """, (estimate.get('job_id'),))

        # Get supplements if any
        supplements = self.db.execute("""
            SELECT es.*, e.estimate_number, e.total, e.status
            FROM estimate_supplements es
            JOIN estimates e ON e.id = es.supplement_estimate_id
            WHERE es.original_estimate_id = ?
            ORDER BY es.supplement_number
        """, (estimate_id,))

        # Get alerts
        alerts = self.db.execute("""
            SELECT * FROM estimate_alerts
            WHERE estimate_id = ? AND status = 'active'
            ORDER BY severity, created_at
        """, (estimate_id,))

        # Build export structure
        export_data = {
            'estimate': {
                'id': estimate_id,
                'number': estimate['estimate_number'],
                'status': estimate['status'],
                'created_date': estimate['created_date'],
                'expires_date': estimate['expires_date'],
                'sent_date': estimate.get('sent_date'),
                'approved_date': estimate.get('approved_date'),
                'notes': estimate.get('notes'),
                'terms': estimate.get('terms')
            },
            'totals': totals,
            'line_items': {
                'pdr_labor': estimate.get('line_items_parsed', []),
                'ri_items': [dict(r) for r in ri_items],
                'parts': [dict(p) for p in parts]
            },
            'vehicle': vehicle_info,
            'customer': customer_info,
            'insurance': insurance_info,
            'panel_damage': [dict(p) for p in panel_damage],
            'photos': [dict(p) for p in photos],
            'supplements': [dict(s) for s in supplements],
            'alerts': [dict(a) for a in alerts],
            'export_date': datetime.now().isoformat()
        }

        return export_data

    def get_estimate_with_ri(self, estimate_id: int) -> Dict:
        """
        Get estimate with all R/I items included.

        Returns estimate dict with 'ri_items' key containing all R/I line items.
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            return None

        ri_items = self.db.execute("""
            SELECT eri.*, ri.code, ri.name, ri.category
            FROM estimate_ri_items eri
            JOIN ri_operations ri ON ri.id = eri.ri_operation_id
            WHERE eri.estimate_id = ?
            ORDER BY eri.panel_name, ri.category
        """, (estimate_id,))

        estimate['ri_items'] = [dict(r) for r in ri_items]
        estimate['ri_total'] = sum(r['line_total'] or 0 for r in ri_items)

        return estimate

    def add_ri_item(
        self,
        estimate_id: int,
        ri_operation_id: int,
        panel_name: str,
        hours: float,
        rate: float,
        notes: str = None
    ) -> int:
        """
        Add an R/I item to the estimate.

        Args:
            estimate_id: Estimate ID
            ri_operation_id: ID from ri_operations table
            panel_name: Panel being worked on
            hours: Labor hours
            rate: Hourly rate
            notes: Optional notes

        Returns:
            R/I item ID
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        line_total = hours * rate

        result = self.db.execute("""
            INSERT INTO estimate_ri_items (
                estimate_id, ri_operation_id, panel_name,
                hours, rate, line_total, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            ri_operation_id,
            panel_name,
            hours,
            rate,
            line_total,
            notes,
            datetime.now().isoformat()
        ))

        ri_item_id = result[0]['id'] if result else None

        # Get operation name for logging
        op = self.db.execute("""
            SELECT name FROM ri_operations WHERE id = ?
        """, (ri_operation_id,))
        op_name = op[0]['name'] if op else f"Operation #{ri_operation_id}"

        print(f"[OK] Added R/I: {op_name} ({panel_name}) - {hours}hrs @ ${rate}/hr = ${line_total:.2f}")

        return ri_item_id

    def remove_ri_item(self, estimate_id: int, ri_item_id: int) -> bool:
        """Remove an R/I item from the estimate"""
        self.db.execute("""
            DELETE FROM estimate_ri_items
            WHERE id = ? AND estimate_id = ?
        """, (ri_item_id, estimate_id))

        print(f"[OK] Removed R/I item #{ri_item_id}")
        return True

    def add_part(
        self,
        estimate_id: int,
        description: str,
        part_number: str = None,
        quantity: float = 1,
        unit_cost: float = 0,
        markup_percent: float = 25,
        notes: str = None
    ) -> int:
        """
        Add a part to the estimate.

        Args:
            estimate_id: Estimate ID
            description: Part description
            part_number: Optional part number
            quantity: Quantity
            unit_cost: Cost per unit
            markup_percent: Markup percentage (default 25%)
            notes: Optional notes

        Returns:
            Part item ID
        """
        estimate = self.get_estimate(estimate_id)
        if not estimate:
            raise ValueError(f"Estimate {estimate_id} not found")

        unit_price = unit_cost * (1 + markup_percent / 100)
        line_total = quantity * unit_price

        result = self.db.execute("""
            INSERT INTO estimate_parts (
                estimate_id, description, part_number,
                quantity, unit_cost, markup_percent, unit_price, line_total,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            description,
            part_number,
            quantity,
            unit_cost,
            markup_percent,
            unit_price,
            line_total,
            notes,
            datetime.now().isoformat()
        ))

        part_id = result[0]['id'] if result else None

        print(f"[OK] Added part: {description} x{quantity} @ ${unit_price:.2f} = ${line_total:.2f}")

        return part_id

    def get_supplements(self, original_estimate_id: int) -> List[Dict]:
        """Get all supplements for an estimate"""
        return self.db.execute("""
            SELECT es.*, e.estimate_number, e.total, e.status as estimate_status
            FROM estimate_supplements es
            JOIN estimates e ON e.id = es.supplement_estimate_id
            WHERE es.original_estimate_id = ?
            ORDER BY es.supplement_number
        """, (original_estimate_id,))
