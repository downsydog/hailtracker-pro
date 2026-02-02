"""
Commission Manager
Calculate and track technician commissions

PDR CRM Part 13 - Payment Processing & Commissions!

FEATURES:
- Commission calculation (percentage or flat rate)
- Tiered commission structures
- Payout tracking
- Commission history
- Performance bonuses
- Deductions (chargebacks, damages)
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
import json


class CommissionManager:
    """
    Manage technician commissions and payouts

    Tracks earnings and payments to technicians
    """

    # Default commission structure
    DEFAULT_COMMISSION_RATE = 0.50  # 50% of labor

    # Tiered commission structure
    TIERED_RATES = {
        'JUNIOR': 0.40,      # 40% for new techs
        'INTERMEDIATE': 0.45,  # 45% for intermediate techs
        'STANDARD': 0.50,    # 50% for regular techs
        'SENIOR': 0.55,      # 55% for experienced techs
        'EXPERT': 0.58,      # 58% for expert techs
        'MASTER': 0.60       # 60% for master techs
    }

    # Commission types
    COMMISSION_TYPES = ['COMMISSION', 'BONUS', 'DEDUCTION', 'ADJUSTMENT']

    # Payout statuses
    PAYOUT_STATUSES = ['PENDING', 'APPROVED', 'PAID', 'CANCELLED']

    def __init__(self, db):
        """Initialize commission manager with database connection"""
        self.db = db
        self._ensure_tables_exist()

    def _ensure_tables_exist(self):
        """Create commissions and payouts tables if they don't exist"""
        # Create commissions table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payment_id INTEGER,
                tech_id INTEGER NOT NULL,
                job_id INTEGER,
                commission_amount REAL NOT NULL,
                commission_date DATE NOT NULL,
                commission_type TEXT DEFAULT 'COMMISSION',
                commission_rate REAL,
                labor_amount REAL,
                status TEXT DEFAULT 'PENDING',
                payout_id INTEGER,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (payment_id) REFERENCES payments(id),
                FOREIGN KEY (tech_id) REFERENCES technicians(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (payout_id) REFERENCES payouts(id)
            )
        """)

        # Create payouts table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tech_id INTEGER NOT NULL,
                payout_date DATE NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                total_amount REAL NOT NULL,
                commission_count INTEGER DEFAULT 0,
                commission_ids TEXT,
                status TEXT DEFAULT 'PENDING',
                paid_date DATE,
                payment_method TEXT,
                reference_number TEXT,
                notes TEXT,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (tech_id) REFERENCES technicians(id)
            )
        """)

        # Create indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_commissions_tech
            ON commissions(tech_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_commissions_status
            ON commissions(status)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payouts_tech
            ON payouts(tech_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payouts_status
            ON payouts(status)
        """)

    # ========================================================================
    # COMMISSION CALCULATION
    # ========================================================================

    def calculate_commission(
        self,
        payment_id: int,
        override_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate commission for a payment

        Args:
            payment_id: Payment ID
            override_rate: Override commission rate (0.0-1.0)

        Returns:
            Dict with commission_amount, rate, labor_amount, details
        """
        # Get payment details with job and tech info
        payment = self.db.execute("""
            SELECT
                p.*,
                j.id as job_id,
                j.assigned_tech_id,
                t.skill_level
            FROM payments p
            JOIN jobs j ON j.id = p.job_id
            LEFT JOIN technicians t ON t.id = j.assigned_tech_id
            WHERE p.id = ?
        """, (payment_id,))

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        payment = payment[0]

        if not payment.get('assigned_tech_id'):
            raise ValueError("Job has no assigned technician")

        # Determine commission rate
        if override_rate is not None:
            rate = override_rate
        else:
            # Get rate from tech's skill level
            skill_level = payment.get('skill_level') or 'STANDARD'
            rate = self.TIERED_RATES.get(skill_level, self.DEFAULT_COMMISSION_RATE)

        # Calculate commission base (labor only, not parts)
        total_amount = payment.get('total_amount') or payment.get('amount', 0)
        parts_cost = payment.get('parts_cost', 0) or 0
        labor_amount = total_amount - parts_cost

        # Calculate commission
        commission_amount = labor_amount * rate

        return {
            'commission_amount': round(commission_amount, 2),
            'rate': rate,
            'labor_amount': round(labor_amount, 2),
            'total_amount': round(total_amount, 2),
            'parts_cost': round(parts_cost, 2),
            'tech_id': payment['assigned_tech_id'],
            'job_id': payment['job_id']
        }

    def record_commission(
        self,
        payment_id: int,
        tech_id: int,
        commission_amount: Optional[float] = None,
        job_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Record commission for a payment

        Args:
            payment_id: Payment ID
            tech_id: Technician ID
            commission_amount: Commission amount (or auto-calculate)
            job_id: Job ID (optional, will be looked up from payment)
            notes: Commission notes

        Returns:
            Commission record ID
        """
        # Auto-calculate if not provided
        calc_result = None
        if commission_amount is None:
            calc_result = self.calculate_commission(payment_id)
            commission_amount = calc_result['commission_amount']

        # Get payment info
        payment = self.db.execute(
            "SELECT payment_date, job_id FROM payments WHERE id = ?",
            (payment_id,)
        )

        if not payment:
            raise ValueError(f"Payment {payment_id} not found")

        payment = payment[0]
        job_id = job_id or payment.get('job_id')

        # Record commission
        self.db.execute("""
            INSERT INTO commissions (
                payment_id, tech_id, job_id,
                commission_amount, commission_date,
                commission_type, commission_rate, labor_amount,
                status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payment_id,
            tech_id,
            job_id,
            commission_amount,
            payment['payment_date'],
            'COMMISSION',
            calc_result['rate'] if calc_result else None,
            calc_result['labor_amount'] if calc_result else None,
            'PENDING',
            notes,
            datetime.now().isoformat()
        ))

        # Get the commission ID
        result = self.db.execute("SELECT last_insert_rowid() as id")
        commission_id = result[0]['id']

        # Update payment with tech cut
        self.db.execute("""
            UPDATE payments
            SET tech_cut = ?
            WHERE id = ?
        """, (commission_amount, payment_id))

        print(f"  [OK] Recorded commission: ${commission_amount:,.2f} for tech #{tech_id}")

        return commission_id

    # ========================================================================
    # COMMISSION ADJUSTMENTS
    # ========================================================================

    def add_bonus(
        self,
        tech_id: int,
        amount: float,
        reason: str,
        bonus_date: Optional[date] = None
    ) -> int:
        """
        Add bonus to technician

        Args:
            tech_id: Technician ID
            amount: Bonus amount
            reason: Reason for bonus
            bonus_date: Date of bonus (defaults to today)

        Returns:
            Commission record ID
        """
        if not bonus_date:
            bonus_date = date.today()

        self.db.execute("""
            INSERT INTO commissions (
                tech_id, commission_amount, commission_date,
                commission_type, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            abs(amount),  # Positive amount
            bonus_date.isoformat(),
            'BONUS',
            'PENDING',
            reason,
            datetime.now().isoformat()
        ))

        result = self.db.execute("SELECT last_insert_rowid() as id")
        commission_id = result[0]['id']

        print(f"  [OK] Added ${amount:,.2f} bonus for tech #{tech_id}")
        print(f"       Reason: {reason}")

        return commission_id

    def add_deduction(
        self,
        tech_id: int,
        amount: float,
        reason: str,
        deduction_date: Optional[date] = None
    ) -> int:
        """
        Add deduction (chargeback, damage, etc.)

        Args:
            tech_id: Technician ID
            amount: Deduction amount (positive number, will be stored as negative)
            reason: Reason for deduction
            deduction_date: Date of deduction

        Returns:
            Commission record ID
        """
        if not deduction_date:
            deduction_date = date.today()

        self.db.execute("""
            INSERT INTO commissions (
                tech_id, commission_amount, commission_date,
                commission_type, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            -abs(amount),  # Negative amount
            deduction_date.isoformat(),
            'DEDUCTION',
            'PENDING',
            reason,
            datetime.now().isoformat()
        ))

        result = self.db.execute("SELECT last_insert_rowid() as id")
        commission_id = result[0]['id']

        print(f"  [!] Added ${amount:,.2f} deduction for tech #{tech_id}")
        print(f"      Reason: {reason}")

        return commission_id

    def add_adjustment(
        self,
        tech_id: int,
        amount: float,
        reason: str,
        adjustment_date: Optional[date] = None
    ) -> int:
        """
        Add general adjustment (can be positive or negative)

        Args:
            tech_id: Technician ID
            amount: Adjustment amount (positive or negative)
            reason: Reason for adjustment
            adjustment_date: Date of adjustment

        Returns:
            Commission record ID
        """
        if not adjustment_date:
            adjustment_date = date.today()

        self.db.execute("""
            INSERT INTO commissions (
                tech_id, commission_amount, commission_date,
                commission_type, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            amount,
            adjustment_date.isoformat(),
            'ADJUSTMENT',
            'PENDING',
            reason,
            datetime.now().isoformat()
        ))

        result = self.db.execute("SELECT last_insert_rowid() as id")
        commission_id = result[0]['id']

        sign = '+' if amount >= 0 else ''
        print(f"  [OK] Added {sign}${amount:,.2f} adjustment for tech #{tech_id}")
        print(f"       Reason: {reason}")

        return commission_id

    # ========================================================================
    # PAYOUT MANAGEMENT
    # ========================================================================

    def get_pending_commissions(
        self,
        tech_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get pending commissions for a technician

        Args:
            tech_id: Technician ID
            start_date: Period start date
            end_date: Period end date

        Returns:
            List of pending commission records
        """
        query = """
            SELECT c.*, j.job_number
            FROM commissions c
            LEFT JOIN jobs j ON c.job_id = j.id
            WHERE c.tech_id = ?
              AND c.status = 'PENDING'
        """
        params = [tech_id]

        if start_date:
            query += " AND DATE(c.commission_date) >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND DATE(c.commission_date) <= ?"
            params.append(end_date.isoformat())

        query += " ORDER BY c.commission_date"

        return self.db.execute(query, tuple(params))

    def create_payout(
        self,
        tech_id: int,
        start_date: date,
        end_date: date,
        payout_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create payout for technician

        Groups all pending commissions into a single payout

        Args:
            tech_id: Technician ID
            start_date: Period start date
            end_date: Period end date
            payout_date: When payout will be made
            notes: Payout notes

        Returns:
            Payout ID
        """
        if not payout_date:
            payout_date = date.today()

        # Get pending commissions for period
        commissions = self.get_pending_commissions(tech_id, start_date, end_date)

        if not commissions:
            raise ValueError(f"No pending commissions found for period {start_date} to {end_date}")

        # Calculate total
        total_amount = sum(c['commission_amount'] for c in commissions)
        commission_ids = [c['id'] for c in commissions]

        # Create payout
        self.db.execute("""
            INSERT INTO payouts (
                tech_id, payout_date,
                period_start, period_end,
                total_amount, commission_count, commission_ids,
                status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            payout_date.isoformat(),
            start_date.isoformat(),
            end_date.isoformat(),
            total_amount,
            len(commission_ids),
            json.dumps(commission_ids),
            'PENDING',
            notes,
            datetime.now().isoformat()
        ))

        result = self.db.execute("SELECT last_insert_rowid() as id")
        payout_id = result[0]['id']

        # Mark commissions as included in payout
        placeholders = ','.join(['?'] * len(commission_ids))
        self.db.execute(f"""
            UPDATE commissions
            SET payout_id = ?,
                status = 'INCLUDED_IN_PAYOUT',
                updated_at = ?
            WHERE id IN ({placeholders})
        """, tuple([payout_id, datetime.now().isoformat()] + commission_ids))

        print(f"  [OK] Created payout #{payout_id} for tech #{tech_id}")
        print(f"       Period: {start_date} to {end_date}")
        print(f"       Total: ${total_amount:,.2f} ({len(commissions)} items)")

        return payout_id

    def approve_payout(
        self,
        payout_id: int,
        approved_by: str = 'System'
    ) -> bool:
        """
        Approve a payout for processing

        Args:
            payout_id: Payout ID
            approved_by: Who approved the payout

        Returns:
            True if approved
        """
        self.db.execute("""
            UPDATE payouts
            SET status = 'APPROVED',
                approved_by = ?,
                approved_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            approved_by,
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            payout_id
        ))

        print(f"  [OK] Approved payout #{payout_id}")

        return True

    def process_payout(
        self,
        payout_id: int,
        payment_method: str = 'CHECK',
        reference_number: Optional[str] = None
    ) -> bool:
        """
        Mark payout as paid

        Args:
            payout_id: Payout ID
            payment_method: CHECK, DIRECT_DEPOSIT, CASH
            reference_number: Check number or transaction ID

        Returns:
            True if processed
        """
        # Update payout
        self.db.execute("""
            UPDATE payouts
            SET status = 'PAID',
                paid_date = ?,
                payment_method = ?,
                reference_number = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            date.today().isoformat(),
            payment_method,
            reference_number,
            datetime.now().isoformat(),
            payout_id
        ))

        # Get commission IDs and update them
        payout = self.db.execute(
            "SELECT commission_ids, total_amount FROM payouts WHERE id = ?",
            (payout_id,)
        )

        if payout and payout[0].get('commission_ids'):
            commission_ids = json.loads(payout[0]['commission_ids'])

            placeholders = ','.join(['?'] * len(commission_ids))
            self.db.execute(f"""
                UPDATE commissions
                SET status = 'PAID',
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, tuple([datetime.now().isoformat()] + commission_ids))

            print(f"  [OK] Processed payout #{payout_id}")
            print(f"       Amount: ${payout[0]['total_amount']:,.2f}")
            print(f"       Method: {payment_method}")
            if reference_number:
                print(f"       Reference: {reference_number}")

        return True

    def cancel_payout(
        self,
        payout_id: int,
        reason: str = 'Cancelled'
    ) -> bool:
        """
        Cancel a pending payout

        Args:
            payout_id: Payout ID
            reason: Cancellation reason

        Returns:
            True if cancelled
        """
        # Get payout
        payout = self.db.execute(
            "SELECT * FROM payouts WHERE id = ?",
            (payout_id,)
        )

        if not payout:
            raise ValueError(f"Payout {payout_id} not found")

        payout = payout[0]

        if payout['status'] == 'PAID':
            raise ValueError("Cannot cancel a paid payout")

        # Update payout
        self.db.execute("""
            UPDATE payouts
            SET status = 'CANCELLED',
                notes = COALESCE(notes, '') || ' [Cancelled: ' || ? || ']',
                updated_at = ?
            WHERE id = ?
        """, (reason, datetime.now().isoformat(), payout_id))

        # Return commissions to pending status
        if payout.get('commission_ids'):
            commission_ids = json.loads(payout['commission_ids'])

            placeholders = ','.join(['?'] * len(commission_ids))
            self.db.execute(f"""
                UPDATE commissions
                SET status = 'PENDING',
                    payout_id = NULL,
                    updated_at = ?
                WHERE id IN ({placeholders})
            """, tuple([datetime.now().isoformat()] + commission_ids))

        print(f"  [OK] Cancelled payout #{payout_id}")

        return True

    # ========================================================================
    # REPORTING
    # ========================================================================

    def get_tech_earnings(
        self,
        tech_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get technician earnings summary

        Args:
            tech_id: Technician ID
            start_date: Period start (defaults to 30 days ago)
            end_date: Period end (defaults to today)

        Returns:
            Earnings summary dict
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Total commissions by type
        result = self.db.execute("""
            SELECT
                SUM(CASE WHEN commission_type = 'COMMISSION' THEN commission_amount ELSE 0 END) as total_commissions,
                SUM(CASE WHEN commission_type = 'BONUS' THEN commission_amount ELSE 0 END) as total_bonuses,
                SUM(CASE WHEN commission_type = 'DEDUCTION' THEN commission_amount ELSE 0 END) as total_deductions,
                SUM(CASE WHEN commission_type = 'ADJUSTMENT' THEN commission_amount ELSE 0 END) as total_adjustments,
                SUM(commission_amount) as total_earnings,
                COUNT(CASE WHEN commission_type = 'COMMISSION' THEN 1 END) as job_count
            FROM commissions
            WHERE tech_id = ?
              AND DATE(commission_date) >= ?
              AND DATE(commission_date) <= ?
        """, (tech_id, start_date.isoformat(), end_date.isoformat()))

        row = result[0]

        earnings = {
            'tech_id': tech_id,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'total_commissions': round(row['total_commissions'] or 0, 2),
            'total_bonuses': round(row['total_bonuses'] or 0, 2),
            'total_deductions': abs(round(row['total_deductions'] or 0, 2)),
            'total_adjustments': round(row['total_adjustments'] or 0, 2),
            'total_earnings': round(row['total_earnings'] or 0, 2),
            'job_count': row['job_count'] or 0
        }

        # Pending earnings (not yet paid out)
        result = self.db.execute("""
            SELECT SUM(commission_amount) as pending
            FROM commissions
            WHERE tech_id = ?
              AND status = 'PENDING'
        """, (tech_id,))

        earnings['pending_earnings'] = round(result[0]['pending'] or 0, 2)

        # Included in payout but not paid yet
        result = self.db.execute("""
            SELECT SUM(commission_amount) as in_payout
            FROM commissions
            WHERE tech_id = ?
              AND status = 'INCLUDED_IN_PAYOUT'
        """, (tech_id,))

        earnings['in_payout_earnings'] = round(result[0]['in_payout'] or 0, 2)

        # Paid earnings in period
        result = self.db.execute("""
            SELECT SUM(commission_amount) as paid
            FROM commissions
            WHERE tech_id = ?
              AND status = 'PAID'
              AND DATE(commission_date) >= ?
              AND DATE(commission_date) <= ?
        """, (tech_id, start_date.isoformat(), end_date.isoformat()))

        earnings['paid_earnings'] = round(result[0]['paid'] or 0, 2)

        # Average per job
        if earnings['job_count'] > 0:
            earnings['avg_per_job'] = round(earnings['total_commissions'] / earnings['job_count'], 2)
        else:
            earnings['avg_per_job'] = 0

        return earnings

    def get_pending_payouts(
        self,
        tech_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get pending payouts

        Args:
            tech_id: Filter by technician (None = all techs)

        Returns:
            List of pending payouts
        """
        query = """
            SELECT
                p.*,
                t.first_name || ' ' || t.last_name as tech_name,
                t.employee_id
            FROM payouts p
            JOIN technicians t ON t.id = p.tech_id
            WHERE p.status IN ('PENDING', 'APPROVED')
        """

        params = []

        if tech_id:
            query += " AND p.tech_id = ?"
            params.append(tech_id)

        query += " ORDER BY p.payout_date"

        return self.db.execute(query, tuple(params))

    def get_payout_history(
        self,
        tech_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get payout history

        Args:
            tech_id: Filter by technician
            limit: Max records

        Returns:
            List of payout records
        """
        query = """
            SELECT
                p.*,
                t.first_name || ' ' || t.last_name as tech_name,
                t.employee_id
            FROM payouts p
            JOIN technicians t ON t.id = p.tech_id
            WHERE 1=1
        """

        params = []

        if tech_id:
            query += " AND p.tech_id = ?"
            params.append(tech_id)

        query += " ORDER BY p.payout_date DESC LIMIT ?"
        params.append(limit)

        return self.db.execute(query, tuple(params))

    def get_commission_history(
        self,
        tech_id: int,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get commission history for technician

        Args:
            tech_id: Technician ID
            limit: Max records

        Returns:
            List of commission records
        """
        query = """
            SELECT
                c.*,
                j.job_number,
                p.payment_method as pmt_method,
                py.payout_date
            FROM commissions c
            LEFT JOIN jobs j ON j.id = c.job_id
            LEFT JOIN payments p ON p.id = c.payment_id
            LEFT JOIN payouts py ON py.id = c.payout_id
            WHERE c.tech_id = ?
            ORDER BY c.commission_date DESC
            LIMIT ?
        """

        return self.db.execute(query, (tech_id, limit))

    # ========================================================================
    # COMMISSION REPORTS
    # ========================================================================

    def generate_commission_report(
        self,
        tech_id: int,
        start_date: date,
        end_date: date
    ) -> str:
        """
        Generate formatted commission report

        Args:
            tech_id: Technician ID
            start_date: Report start date
            end_date: Report end date

        Returns:
            Formatted text report
        """
        # Get tech info
        tech = self.db.execute(
            "SELECT * FROM technicians WHERE id = ?",
            (tech_id,)
        )

        if not tech:
            raise ValueError(f"Technician {tech_id} not found")

        tech = tech[0]

        # Get earnings
        earnings = self.get_tech_earnings(tech_id, start_date, end_date)

        # Get commission details
        commissions = self.db.execute("""
            SELECT c.*, j.job_number
            FROM commissions c
            LEFT JOIN jobs j ON j.id = c.job_id
            WHERE c.tech_id = ?
              AND DATE(c.commission_date) >= ?
              AND DATE(c.commission_date) <= ?
            ORDER BY c.commission_date
        """, (tech_id, start_date.isoformat(), end_date.isoformat()))

        # Build report
        report = []
        report.append("")
        report.append("=" * 70)
        report.append(f"COMMISSION REPORT")
        report.append("=" * 70)
        report.append("")
        report.append(f"Technician: {tech['first_name']} {tech['last_name']}")
        report.append(f"Employee ID: {tech.get('employee_id', 'N/A')}")
        report.append(f"Skill Level: {tech.get('skill_level', 'STANDARD')}")
        report.append(f"Period: {start_date} to {end_date}")
        report.append("")
        report.append("-" * 70)
        report.append("EARNINGS SUMMARY")
        report.append("-" * 70)
        report.append("")
        report.append(f"  Jobs Completed:      {earnings['job_count']:>8d}")
        report.append(f"  Total Commissions:   ${earnings['total_commissions']:>10,.2f}")
        report.append(f"  Bonuses:             ${earnings['total_bonuses']:>10,.2f}")
        report.append(f"  Deductions:         -${earnings['total_deductions']:>10,.2f}")
        report.append(f"  Adjustments:         ${earnings['total_adjustments']:>10,.2f}")
        report.append("  " + "-" * 35)
        report.append(f"  TOTAL EARNINGS:      ${earnings['total_earnings']:>10,.2f}")
        report.append("")
        report.append(f"  Average per Job:     ${earnings['avg_per_job']:>10,.2f}")
        report.append("")
        report.append("-" * 70)
        report.append("COMMISSION DETAILS")
        report.append("-" * 70)
        report.append("")
        report.append(f"{'Date':<12} {'Type':<12} {'Job #':<15} {'Amount':>12}")
        report.append("-" * 70)

        for comm in commissions:
            comm_date = comm['commission_date']
            comm_type = comm.get('commission_type', 'COMMISSION')
            job_num = comm.get('job_number', '-')
            amount = comm['commission_amount']

            if comm_type == 'COMMISSION':
                desc = job_num or '-'
            elif comm_type == 'BONUS':
                desc = 'BONUS'
            elif comm_type == 'DEDUCTION':
                desc = 'DEDUCTION'
            else:
                desc = 'ADJUSTMENT'

            sign = '+' if amount >= 0 else ''
            report.append(f"{comm_date:<12} {comm_type:<12} {desc:<15} {sign}${amount:>10,.2f}")

        report.append("-" * 70)
        report.append(f"{'TOTAL':<40} ${earnings['total_earnings']:>10,.2f}")
        report.append("")
        report.append("-" * 70)
        report.append("PAYOUT STATUS")
        report.append("-" * 70)
        report.append("")
        report.append(f"  Pending (not in payout):    ${earnings['pending_earnings']:>10,.2f}")
        report.append(f"  In Payout (awaiting pay):   ${earnings['in_payout_earnings']:>10,.2f}")
        report.append(f"  Paid this period:           ${earnings['paid_earnings']:>10,.2f}")
        report.append("")
        report.append("=" * 70)
        report.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        report.append("=" * 70)
        report.append("")

        return "\n".join(report)

    def generate_payout_summary(self, days: int = 30) -> str:
        """
        Generate summary of all payouts

        Args:
            days: Number of days to include

        Returns:
            Formatted summary report
        """
        start_date = (date.today() - timedelta(days=days)).isoformat()

        # Get payout stats
        stats = self.db.execute("""
            SELECT
                COUNT(*) as total_payouts,
                SUM(CASE WHEN status = 'PAID' THEN 1 ELSE 0 END) as paid_count,
                SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'APPROVED' THEN 1 ELSE 0 END) as approved_count,
                SUM(CASE WHEN status = 'PAID' THEN total_amount ELSE 0 END) as total_paid,
                SUM(CASE WHEN status IN ('PENDING', 'APPROVED') THEN total_amount ELSE 0 END) as total_pending
            FROM payouts
            WHERE DATE(created_at) >= ?
        """, (start_date,))[0]

        # Get per-tech breakdown
        by_tech = self.db.execute("""
            SELECT
                t.first_name || ' ' || t.last_name as tech_name,
                COUNT(p.id) as payout_count,
                SUM(p.total_amount) as total_amount
            FROM payouts p
            JOIN technicians t ON t.id = p.tech_id
            WHERE DATE(p.created_at) >= ?
              AND p.status = 'PAID'
            GROUP BY p.tech_id
            ORDER BY total_amount DESC
        """, (start_date,))

        # Build report
        report = []
        report.append("")
        report.append("=" * 60)
        report.append(f"PAYOUT SUMMARY (Last {days} Days)")
        report.append("=" * 60)
        report.append("")
        report.append(f"Total Payouts:     {stats['total_payouts'] or 0}")
        report.append(f"  Paid:            {stats['paid_count'] or 0}")
        report.append(f"  Pending:         {stats['pending_count'] or 0}")
        report.append(f"  Approved:        {stats['approved_count'] or 0}")
        report.append("")
        report.append(f"Total Paid Out:    ${(stats['total_paid'] or 0):,.2f}")
        report.append(f"Pending Payouts:   ${(stats['total_pending'] or 0):,.2f}")
        report.append("")

        if by_tech:
            report.append("-" * 60)
            report.append("BY TECHNICIAN (Paid)")
            report.append("-" * 60)
            for tech in by_tech:
                report.append(f"  {tech['tech_name']:<25} {tech['payout_count']:>3} payouts  ${tech['total_amount']:>10,.2f}")

        report.append("")

        return "\n".join(report)

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_commission_rate_for_tech(self, tech_id: int) -> float:
        """Get the commission rate for a technician based on skill level"""
        tech = self.db.execute(
            "SELECT skill_level FROM technicians WHERE id = ?",
            (tech_id,)
        )

        if not tech:
            return self.DEFAULT_COMMISSION_RATE

        skill_level = tech[0].get('skill_level') or 'STANDARD'
        return self.TIERED_RATES.get(skill_level, self.DEFAULT_COMMISSION_RATE)

    def get_tiered_rates(self) -> Dict[str, float]:
        """Get all tiered commission rates"""
        return self.TIERED_RATES.copy()

    def update_tech_commission_tier(
        self,
        tech_id: int,
        new_tier: str
    ) -> bool:
        """
        Update a technician's commission tier

        Args:
            tech_id: Technician ID
            new_tier: New tier (JUNIOR, INTERMEDIATE, STANDARD, SENIOR, EXPERT, MASTER)

        Returns:
            True if updated
        """
        if new_tier not in self.TIERED_RATES:
            raise ValueError(f"Invalid tier: {new_tier}. Valid tiers: {list(self.TIERED_RATES.keys())}")

        self.db.execute("""
            UPDATE technicians
            SET skill_level = ?,
                updated_at = ?
            WHERE id = ?
        """, (new_tier, datetime.now().isoformat(), tech_id))

        print(f"  [OK] Updated tech #{tech_id} to {new_tier} tier ({self.TIERED_RATES[new_tier]*100:.0f}% commission)")

        return True
