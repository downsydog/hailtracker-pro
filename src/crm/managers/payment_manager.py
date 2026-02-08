"""
Payment Manager
Track payments and revenue breakdowns with complete transparency

SOLVES THE PROBLEM:
- Everyone feels they're getting ripped off
- No visibility into how money is split
- Unclear commission structures
- Hard to track insurance vs customer payments

FEATURES:
- Complete payment tracking
- Transparent revenue breakdown
- Configurable split percentages
- Multiple payment sources
- Payment status (received, deposited, cleared, bounced)
- Revenue reports
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timedelta


class PaymentManager:
    """
    Manage payments and revenue splits

    Shows everyone exactly how money is divided!
    """

    # Default split percentages (can be configured per job/location)
    DEFAULT_SPLITS = {
        'sales_percentage': 10.0,      # 10% to sales team
        'tech_percentage': 50.0,       # 50% to technician
        'office_percentage': 10.0,     # 10% to office/admin
        # Remainder (30%) goes to shop profit
    }

    # Valid payment methods
    PAYMENT_METHODS = ['CHECK', 'CASH', 'CARD', 'INSURANCE', 'ACH', 'WIRE']

    # Valid payer types
    PAYER_TYPES = ['CUSTOMER', 'INSURANCE', 'DEALERSHIP', 'FLEET', 'OTHER']

    # Valid payment statuses
    PAYMENT_STATUSES = ['RECEIVED', 'DEPOSITED', 'CLEARED', 'BOUNCED']

    def __init__(self, db):
        """Initialize payment manager with database connection"""
        self.db = db

    # ========================================================================
    # PAYMENT RECORDING
    # ========================================================================

    def record_payment(
        self,
        invoice_id: int,
        job_id: int,
        amount: float,
        payment_method: str,
        payment_date: date,
        payer_type: str = "CUSTOMER",
        payer_name: Optional[str] = None,
        payment_reference: Optional[str] = None,
        parts_cost: float = 0.0,
        sales_percentage: Optional[float] = None,
        tech_percentage: Optional[float] = None,
        office_percentage: Optional[float] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Record payment with automatic revenue breakdown

        Args:
            invoice_id: Invoice this payment applies to
            job_id: Job this payment is for
            amount: Payment amount
            payment_method: CHECK, CASH, CARD, INSURANCE, ACH
            payment_date: Date payment received
            payer_type: CUSTOMER, INSURANCE, DEALERSHIP
            payer_name: Name of payer
            payment_reference: Check number, transaction ID, etc.
            parts_cost: Cost of parts (deducted before splits)
            sales_percentage: % to sales (defaults to DEFAULT_SPLITS)
            tech_percentage: % to tech (defaults to DEFAULT_SPLITS)
            office_percentage: % to office (defaults to DEFAULT_SPLITS)

        Returns:
            Payment ID

        The breakdown calculation:
        1. Start with total payment amount
        2. Subtract parts cost
        3. Calculate each percentage of remaining amount
        4. Shop profit = remainder after all cuts
        """
        # Validate inputs
        if payment_method not in self.PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method: {payment_method}. Valid: {self.PAYMENT_METHODS}")
        if payer_type not in self.PAYER_TYPES:
            raise ValueError(f"Invalid payer type: {payer_type}. Valid: {self.PAYER_TYPES}")

        # Use defaults if not specified
        if sales_percentage is None:
            sales_percentage = self.DEFAULT_SPLITS['sales_percentage']
        if tech_percentage is None:
            tech_percentage = self.DEFAULT_SPLITS['tech_percentage']
        if office_percentage is None:
            office_percentage = self.DEFAULT_SPLITS['office_percentage']

        # Calculate breakdown
        breakdown = self._calculate_breakdown(
            total_amount=amount,
            parts_cost=parts_cost,
            sales_pct=sales_percentage,
            tech_pct=tech_percentage,
            office_pct=office_percentage
        )

        # Determine insurance portion
        insurance_portion = amount if payer_type == 'INSURANCE' else 0.0

        payment_data = {
            'invoice_id': invoice_id,
            'job_id': job_id,
            'amount': amount,
            'payment_method': payment_method,
            'payment_date': payment_date.isoformat(),
            'payer_type': payer_type,
            'payer_name': payer_name,
            'payment_reference': payment_reference,
            'total_amount': breakdown['total_amount'],
            'insurance_portion': insurance_portion,
            'parts_cost': breakdown['parts_cost'],
            'sales_team_cut': breakdown['sales_cut'],
            'tech_cut': breakdown['tech_cut'],
            'office_cut': breakdown['office_cut'],
            'shop_profit': breakdown['shop_profit'],
            'sales_percentage': sales_percentage,
            'tech_percentage': tech_percentage,
            'office_percentage': office_percentage,
            'status': 'RECEIVED',
            'notes': notes,
            'created_by': created_by
        }

        payment_id = self.db.insert('payments', payment_data)

        # Update invoice
        self._update_invoice_payment_status(invoice_id, amount)

        print(f"[OK] Recorded payment #{payment_id}: ${amount:,.2f}")
        print(f"     Method: {payment_method}")
        print(f"     Payer: {payer_name or payer_type}")
        print()
        print(f"     REVENUE BREAKDOWN:")
        print(f"        Total payment:    ${breakdown['total_amount']:>10,.2f}")
        print(f"        Parts cost:      -${breakdown['parts_cost']:>10,.2f}")
        print(f"        -----------------------------------")
        print(f"        Net for splits:   ${breakdown['net_for_splits']:>10,.2f}")
        print()
        print(f"        Sales ({sales_percentage}%):      ${breakdown['sales_cut']:>10,.2f}")
        print(f"        Tech ({tech_percentage}%):       ${breakdown['tech_cut']:>10,.2f}")
        print(f"        Office ({office_percentage}%):    ${breakdown['office_cut']:>10,.2f}")
        print(f"        Shop profit:      ${breakdown['shop_profit']:>10,.2f}")
        print()

        return payment_id

    def _calculate_breakdown(
        self,
        total_amount: float,
        parts_cost: float,
        sales_pct: float,
        tech_pct: float,
        office_pct: float
    ) -> Dict[str, float]:
        """
        Calculate revenue breakdown

        Formula:
        1. Subtract parts cost from total
        2. Calculate each percentage of net amount
        3. Remainder goes to shop profit

        Returns:
            Dict with all breakdown values
        """
        # Net amount after parts
        net_for_splits = total_amount - parts_cost

        # Calculate cuts
        sales_cut = net_for_splits * (sales_pct / 100.0)
        tech_cut = net_for_splits * (tech_pct / 100.0)
        office_cut = net_for_splits * (office_pct / 100.0)

        # Shop gets the rest
        total_pct = sales_pct + tech_pct + office_pct
        shop_profit = net_for_splits * ((100.0 - total_pct) / 100.0)

        return {
            'total_amount': total_amount,
            'parts_cost': parts_cost,
            'net_for_splits': net_for_splits,
            'sales_cut': round(sales_cut, 2),
            'tech_cut': round(tech_cut, 2),
            'office_cut': round(office_cut, 2),
            'shop_profit': round(shop_profit, 2),
            'sales_pct': sales_pct,
            'tech_pct': tech_pct,
            'office_pct': office_pct
        }

    def _update_invoice_payment_status(self, invoice_id: int, payment_amount: float):
        """Update invoice payment status"""
        # Get invoice
        invoice = self.db.execute(
            "SELECT * FROM invoices WHERE id = ?",
            (invoice_id,)
        )

        if not invoice:
            return

        invoice = invoice[0]

        # Calculate new amounts
        current_paid = invoice.get('amount_paid') or 0.0
        new_paid = current_paid + payment_amount
        total = invoice.get('total') or 0.0
        new_balance = total - new_paid

        # Determine status
        if new_balance <= 0.01:  # Fully paid (allow for rounding)
            status = 'PAID'
        elif new_paid > 0.01:  # Partial payment
            status = 'PARTIAL_PAID'
        else:  # No payment (reversed or bounced)
            status = 'SENT'

        self.db.execute("""
            UPDATE invoices
            SET amount_paid = ?,
                balance_due = ?,
                status = ?,
                paid_date = CASE WHEN ? = 'PAID' THEN date('now') ELSE paid_date END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_paid, new_balance, status, status, invoice_id))

    def record_partial_payment(
        self,
        invoice_id: int,
        job_id: int,
        amount: float,
        payment_method: str,
        payment_date: date,
        payer_type: str = "CUSTOMER",
        payer_name: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Record a partial payment (uses default splits, no parts cost)"""
        return self.record_payment(
            invoice_id=invoice_id,
            job_id=job_id,
            amount=amount,
            payment_method=payment_method,
            payment_date=payment_date,
            payer_type=payer_type,
            payer_name=payer_name,
            parts_cost=0.0,
            notes=notes
        )

    # ========================================================================
    # PAYMENT STATUS UPDATES
    # ========================================================================

    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        cleared_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update payment status

        Status: RECEIVED, DEPOSITED, CLEARED, BOUNCED

        Args:
            payment_id: Payment ID
            status: New status
            cleared_date: Date check cleared (for CLEARED status)
            notes: Status change notes
        """
        if status not in self.PAYMENT_STATUSES:
            raise ValueError(f"Invalid status: {status}. Valid: {self.PAYMENT_STATUSES}")

        payment = self.get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        update_data = {'status': status}

        if cleared_date:
            update_data['cleared_date'] = cleared_date.isoformat()

        if notes:
            existing_notes = payment.get('notes') or ''
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_notes = f"[{timestamp}] {status}: {notes}"
            update_data['notes'] = f"{existing_notes}\n{new_notes}".strip()

        # Build update query (payments table doesn't have updated_at)
        set_clauses = [f"{k} = ?" for k in update_data.keys()]
        query = f"UPDATE payments SET {', '.join(set_clauses)} WHERE id = ?"
        values = list(update_data.values()) + [payment_id]
        self.db.execute(query, tuple(values))

        print(f"[OK] Updated payment #{payment_id} status: {status}")

        if status == 'BOUNCED':
            print(f"     WARNING: Payment BOUNCED - reversing invoice payment")
            # Reverse the invoice payment
            self._update_invoice_payment_status(
                payment['invoice_id'],
                -payment['amount']
            )

        return True

    def mark_deposited(self, payment_id: int, notes: str = None) -> bool:
        """Mark payment as deposited"""
        return self.update_payment_status(payment_id, 'DEPOSITED', notes=notes)

    def mark_cleared(self, payment_id: int, cleared_date: date = None, notes: str = None) -> bool:
        """Mark payment as cleared"""
        return self.update_payment_status(
            payment_id, 'CLEARED',
            cleared_date=cleared_date or date.today(),
            notes=notes
        )

    def mark_bounced(self, payment_id: int, notes: str = None) -> bool:
        """Mark payment as bounced (reverses invoice payment)"""
        return self.update_payment_status(payment_id, 'BOUNCED', notes=notes)

    # ========================================================================
    # PAYMENT RETRIEVAL
    # ========================================================================

    def get_payment(self, payment_id: int) -> Optional[Dict]:
        """Get payment details"""
        query = """
        SELECT
            p.*,
            i.invoice_number,
            j.job_number,
            c.first_name || ' ' || c.last_name as customer_name
        FROM payments p
        JOIN invoices i ON i.id = p.invoice_id
        JOIN jobs j ON j.id = p.job_id
        JOIN customers c ON c.id = j.customer_id
        WHERE p.id = ?
        """

        results = self.db.execute(query, (payment_id,))
        return results[0] if results else None

    def get_job_payments(self, job_id: int) -> List[Dict]:
        """Get all payments for a job"""
        return self.db.execute("""
            SELECT * FROM payments
            WHERE job_id = ?
            ORDER BY payment_date DESC
        """, (job_id,))

    def get_invoice_payments(self, invoice_id: int) -> List[Dict]:
        """Get all payments for an invoice"""
        return self.db.execute("""
            SELECT * FROM payments
            WHERE invoice_id = ?
            ORDER BY payment_date DESC
        """, (invoice_id,))

    def search_payments(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        payment_method: Optional[str] = None,
        payer_type: Optional[str] = None,
        status: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search payments with filters
        """
        query = """
        SELECT
            p.*,
            i.invoice_number,
            j.job_number,
            c.first_name || ' ' || c.last_name as customer_name
        FROM payments p
        JOIN invoices i ON i.id = p.invoice_id
        JOIN jobs j ON j.id = p.job_id
        JOIN customers c ON c.id = j.customer_id
        WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND p.payment_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND p.payment_date <= ?"
            params.append(end_date.isoformat())

        if payment_method:
            query += " AND p.payment_method = ?"
            params.append(payment_method)

        if payer_type:
            query += " AND p.payer_type = ?"
            params.append(payer_type)

        if status:
            query += " AND p.status = ?"
            params.append(status)

        if min_amount:
            query += " AND p.amount >= ?"
            params.append(min_amount)

        if max_amount:
            query += " AND p.amount <= ?"
            params.append(max_amount)

        query += " ORDER BY p.payment_date DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_pending_payments(self) -> List[Dict]:
        """Get payments pending clearance"""
        return self.search_payments(status='RECEIVED', limit=500)

    def get_bounced_payments(self) -> List[Dict]:
        """Get bounced payments"""
        return self.search_payments(status='BOUNCED', limit=500)

    # ========================================================================
    # REVENUE REPORTS
    # ========================================================================

    def get_revenue_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        location_id: Optional[int] = None
    ) -> Dict:
        """
        Get revenue summary with complete breakdown

        Returns total revenue and how it's split
        """
        query = """
        SELECT
            COUNT(*) as payment_count,
            SUM(total_amount) as total_revenue,
            SUM(insurance_portion) as insurance_revenue,
            SUM(total_amount - insurance_portion) as customer_revenue,
            SUM(parts_cost) as total_parts_cost,
            SUM(sales_team_cut) as total_sales_cut,
            SUM(tech_cut) as total_tech_cut,
            SUM(office_cut) as total_office_cut,
            SUM(shop_profit) as total_shop_profit
        FROM payments p
        JOIN jobs j ON j.id = p.job_id
        WHERE p.status != 'BOUNCED'
        """

        params = []

        if start_date:
            query += " AND p.payment_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND p.payment_date <= ?"
            params.append(end_date.isoformat())

        if location_id:
            query += " AND j.location_id = ?"
            params.append(location_id)

        results = self.db.execute(query, tuple(params))

        summary = results[0] if results else {}

        # Convert None to 0 and add percentages
        for key in ['total_revenue', 'insurance_revenue', 'customer_revenue',
                   'total_parts_cost', 'total_sales_cut', 'total_tech_cut',
                   'total_office_cut', 'total_shop_profit']:
            summary[key] = summary.get(key) or 0

        total = summary.get('total_revenue', 0)
        if total > 0:
            summary['sales_pct'] = (summary.get('total_sales_cut', 0)) / total * 100
            summary['tech_pct'] = (summary.get('total_tech_cut', 0)) / total * 100
            summary['office_pct'] = (summary.get('total_office_cut', 0)) / total * 100
            summary['shop_pct'] = (summary.get('total_shop_profit', 0)) / total * 100
        else:
            summary['sales_pct'] = 0
            summary['tech_pct'] = 0
            summary['office_pct'] = 0
            summary['shop_pct'] = 0

        return summary

    def get_tech_earnings(
        self,
        tech_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get earnings for a specific technician

        Shows tech exactly how much they've earned
        """
        query = """
        SELECT
            COUNT(DISTINCT p.job_id) as job_count,
            SUM(p.tech_cut) as total_earned,
            AVG(p.tech_cut) as avg_per_job,
            AVG(p.tech_percentage) as avg_tech_pct,
            SUM(p.total_amount) as total_job_value
        FROM payments p
        JOIN jobs j ON j.id = p.job_id
        WHERE j.assigned_tech_id = ?
          AND p.status != 'BOUNCED'
        """

        params = [tech_id]

        if start_date:
            query += " AND p.payment_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND p.payment_date <= ?"
            params.append(end_date.isoformat())

        results = self.db.execute(query, tuple(params))
        earnings = results[0] if results else {}

        # Convert None to 0
        for key in ['job_count', 'total_earned', 'avg_per_job', 'avg_tech_pct', 'total_job_value']:
            earnings[key] = earnings.get(key) or 0

        # Get job details
        job_query = """
        SELECT
            j.job_number,
            p.payment_date,
            p.total_amount,
            p.tech_cut,
            p.tech_percentage,
            c.first_name || ' ' || c.last_name as customer_name,
            v.year || ' ' || v.make || ' ' || v.model as vehicle
        FROM payments p
        JOIN jobs j ON j.id = p.job_id
        JOIN customers c ON c.id = j.customer_id
        JOIN vehicles v ON v.id = j.vehicle_id
        WHERE j.assigned_tech_id = ?
          AND p.status != 'BOUNCED'
        """

        job_params = [tech_id]

        if start_date:
            job_query += " AND p.payment_date >= ?"
            job_params.append(start_date.isoformat())

        if end_date:
            job_query += " AND p.payment_date <= ?"
            job_params.append(end_date.isoformat())

        job_query += " ORDER BY p.payment_date DESC"

        earnings['jobs'] = self.db.execute(job_query, tuple(job_params))

        return earnings

    def get_sales_earnings(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get sales team earnings for a period"""
        query = """
        SELECT
            COUNT(DISTINCT p.job_id) as job_count,
            SUM(p.sales_team_cut) as total_earned,
            AVG(p.sales_team_cut) as avg_per_job,
            AVG(p.sales_percentage) as avg_sales_pct
        FROM payments p
        WHERE p.status != 'BOUNCED'
        """

        params = []

        if start_date:
            query += " AND p.payment_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND p.payment_date <= ?"
            params.append(end_date.isoformat())

        results = self.db.execute(query, tuple(params))
        return results[0] if results else {}

    def get_daily_revenue(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get daily revenue breakdown"""
        return self.db.execute("""
            SELECT
                payment_date,
                COUNT(*) as payment_count,
                SUM(total_amount) as total_revenue,
                SUM(insurance_portion) as insurance_revenue,
                SUM(total_amount - insurance_portion) as customer_revenue,
                SUM(parts_cost) as parts_cost,
                SUM(sales_team_cut) as sales_cut,
                SUM(tech_cut) as tech_cut,
                SUM(office_cut) as office_cut,
                SUM(shop_profit) as shop_profit
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date BETWEEN ? AND ?
            GROUP BY payment_date
            ORDER BY payment_date DESC
        """, (start_date.isoformat(), end_date.isoformat()))

    def get_payment_breakdown_report(
        self,
        start_date: date,
        end_date: date
    ) -> str:
        """
        Generate detailed payment breakdown report

        Returns formatted text report showing exactly how money is split
        """
        summary = self.get_revenue_summary(start_date, end_date)

        report = f"""
================================================================================
                    REVENUE BREAKDOWN REPORT
                  {start_date} to {end_date}
================================================================================

TOTAL REVENUE:        ${summary.get('total_revenue', 0):>12,.2f}
  From Insurance:     ${summary.get('insurance_revenue', 0):>12,.2f}
  From Customers:     ${summary.get('customer_revenue', 0):>12,.2f}

DEDUCTIONS:
  Parts Cost:        -${summary.get('total_parts_cost', 0):>12,.2f}

REVENUE DISTRIBUTION:
  Sales Team:         ${summary.get('total_sales_cut', 0):>12,.2f}  ({summary.get('sales_pct', 0):>5.1f}%)
  Technicians:        ${summary.get('total_tech_cut', 0):>12,.2f}  ({summary.get('tech_pct', 0):>5.1f}%)
  Office/Admin:       ${summary.get('total_office_cut', 0):>12,.2f}  ({summary.get('office_pct', 0):>5.1f}%)
  Shop Profit:        ${summary.get('total_shop_profit', 0):>12,.2f}  ({summary.get('shop_pct', 0):>5.1f}%)

PAYMENTS PROCESSED: {summary.get('payment_count', 0)}

================================================================================
Everyone can see exactly where the money goes!
================================================================================
"""
        return report

    # ========================================================================
    # PAYMENT STATISTICS
    # ========================================================================

    def get_payment_stats(self) -> Dict:
        """Get payment statistics for dashboard"""
        stats = {}

        # Total payments
        result = self.db.execute("""
            SELECT
                COUNT(*) as count,
                SUM(amount) as total
            FROM payments
            WHERE status != 'BOUNCED'
        """)
        stats['total_payments'] = result[0]['count'] or 0
        stats['total_amount'] = result[0]['total'] or 0

        # This month
        result = self.db.execute("""
            SELECT
                COUNT(*) as count,
                SUM(amount) as total
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date >= date('now', 'start of month')
        """)
        stats['month_payments'] = result[0]['count'] or 0
        stats['month_amount'] = result[0]['total'] or 0

        # Today
        result = self.db.execute("""
            SELECT
                COUNT(*) as count,
                SUM(amount) as total
            FROM payments
            WHERE status != 'BOUNCED'
              AND payment_date = date('now')
        """)
        stats['today_payments'] = result[0]['count'] or 0
        stats['today_amount'] = result[0]['total'] or 0

        # By method
        result = self.db.execute("""
            SELECT payment_method, COUNT(*) as count, SUM(amount) as total
            FROM payments
            WHERE status != 'BOUNCED'
            GROUP BY payment_method
        """)
        stats['by_method'] = {
            row['payment_method']: {'count': row['count'], 'total': row['total'] or 0}
            for row in result
        }

        # By payer type
        result = self.db.execute("""
            SELECT payer_type, COUNT(*) as count, SUM(amount) as total
            FROM payments
            WHERE status != 'BOUNCED'
            GROUP BY payer_type
        """)
        stats['by_payer_type'] = {
            row['payer_type']: {'count': row['count'], 'total': row['total'] or 0}
            for row in result
        }

        # Pending clearance
        result = self.db.execute("""
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM payments
            WHERE status IN ('RECEIVED', 'DEPOSITED')
        """)
        stats['pending_clearance'] = result[0]['count'] or 0
        stats['pending_amount'] = result[0]['total'] or 0

        # Bounced
        result = self.db.execute("""
            SELECT COUNT(*) as count, SUM(amount) as total
            FROM payments
            WHERE status = 'BOUNCED'
        """)
        stats['bounced_count'] = result[0]['count'] or 0
        stats['bounced_amount'] = result[0]['total'] or 0

        return stats

    def get_average_splits(self) -> Dict:
        """Get average split percentages used"""
        result = self.db.execute("""
            SELECT
                AVG(sales_percentage) as avg_sales_pct,
                AVG(tech_percentage) as avg_tech_pct,
                AVG(office_percentage) as avg_office_pct
            FROM payments
            WHERE status != 'BOUNCED'
        """)
        return result[0] if result else {}
