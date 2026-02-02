"""
PDR CRM Part 24 - Fleet Manager
Manage fleet customers and batch processing

FEATURES:
- Fleet customer accounts
- Batch job creation
- Volume pricing
- Fleet contracts
- Bulk operations
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class FleetManager:
    """
    Manage fleet customers and batch operations

    Dealerships and commercial accounts
    """

    # Fleet types
    FLEET_TYPES = [
        'DEALERSHIP',           # Auto dealerships
        'RENTAL_COMPANY',       # Car rental companies
        'CORPORATE_FLEET',      # Company vehicles
        'LEASING_COMPANY',      # Leasing agencies
        'AUCTION_HOUSE',        # Auto auctions
        'BODY_SHOP',            # Body shop partners
        'INSURANCE_COMPANY'     # Insurance partners
    ]

    # Volume pricing tiers
    PRICING_TIERS = {
        'STANDARD': {
            'name': 'Standard',
            'min_vehicles_per_month': 0,
            'discount_percent': 0,
            'priority_level': 1
        },
        'BRONZE': {
            'name': 'Bronze Fleet',
            'min_vehicles_per_month': 10,
            'discount_percent': 10,
            'priority_level': 2
        },
        'SILVER': {
            'name': 'Silver Fleet',
            'min_vehicles_per_month': 25,
            'discount_percent': 15,
            'priority_level': 3
        },
        'GOLD': {
            'name': 'Gold Fleet',
            'min_vehicles_per_month': 50,
            'discount_percent': 20,
            'priority_level': 4
        },
        'PLATINUM': {
            'name': 'Platinum Fleet',
            'min_vehicles_per_month': 100,
            'discount_percent': 25,
            'priority_level': 5
        }
    }

    # Payment terms
    PAYMENT_TERMS = ['DUE_ON_RECEIPT', 'NET_15', 'NET_30', 'NET_45', 'NET_60']

    def __init__(self, db):
        """Initialize fleet manager with database instance"""
        self.db = db
        self._ensure_fleet_tables()

    def _ensure_fleet_tables(self):
        """Ensure fleet-related tables exist"""
        # Fleet customers table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS fleet_customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                fleet_type TEXT NOT NULL,
                primary_contact_name TEXT,
                primary_contact_email TEXT,
                primary_contact_phone TEXT,
                billing_address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                tax_id TEXT,
                pricing_tier TEXT DEFAULT 'STANDARD',
                payment_terms TEXT DEFAULT 'NET_30',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                tier_updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Batch jobs table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fleet_customer_id INTEGER NOT NULL,
                batch_name TEXT NOT NULL,
                vehicle_count INTEGER DEFAULT 0,
                total_estimated_cost REAL DEFAULT 0,
                total_actual_cost REAL,
                created_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

        # Batch vehicles table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS batch_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_job_id INTEGER NOT NULL,
                stock_number TEXT,
                year INTEGER,
                make TEXT,
                model TEXT,
                vin TEXT,
                color TEXT,
                damage_type TEXT,
                estimated_cost REAL DEFAULT 0,
                actual_cost REAL,
                status TEXT DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                completed_at TIMESTAMP,
                assigned_tech TEXT,
                notes TEXT,
                FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id)
            )
        """)

        # Fleet invoices table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS fleet_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_job_id INTEGER,
                fleet_customer_id INTEGER NOT NULL,
                invoice_number TEXT UNIQUE,
                invoice_date DATE,
                due_date DATE,
                subtotal REAL DEFAULT 0,
                discount_percent REAL DEFAULT 0,
                discount_amount REAL DEFAULT 0,
                tax_amount REAL DEFAULT 0,
                total REAL DEFAULT 0,
                amount_paid REAL DEFAULT 0,
                balance_due REAL DEFAULT 0,
                payment_terms TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                paid_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (batch_job_id) REFERENCES batch_jobs(id),
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

        # Fleet contracts table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS fleet_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fleet_customer_id INTEGER NOT NULL,
                contract_number TEXT UNIQUE,
                start_date DATE,
                end_date DATE,
                pricing_tier TEXT,
                min_monthly_volume INTEGER,
                discount_percent REAL,
                terms TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (fleet_customer_id) REFERENCES fleet_customers(id)
            )
        """)

    # ========================================================================
    # FLEET CUSTOMER MANAGEMENT
    # ========================================================================

    def create_fleet_customer(
        self,
        company_name: str,
        fleet_type: str,
        primary_contact_name: str,
        primary_contact_email: str,
        primary_contact_phone: str,
        billing_address: str,
        city: str,
        state: str,
        zip_code: str,
        tax_id: Optional[str] = None,
        pricing_tier: str = 'STANDARD',
        payment_terms: str = 'NET_30',
        notes: Optional[str] = None
    ) -> int:
        """
        Create fleet customer account

        Args:
            company_name: Company name
            fleet_type: Type of fleet (DEALERSHIP, RENTAL_COMPANY, etc.)
            primary_contact_name: Main contact person
            primary_contact_email: Contact email
            primary_contact_phone: Contact phone
            billing_address: Billing address
            city: City
            state: State
            zip_code: ZIP code
            tax_id: Tax ID / EIN
            pricing_tier: Volume pricing tier
            payment_terms: NET_30, NET_15, DUE_ON_RECEIPT
            notes: Account notes

        Returns:
            Fleet customer ID
        """
        if fleet_type not in self.FLEET_TYPES:
            raise ValueError(f"Invalid fleet_type. Must be: {self.FLEET_TYPES}")

        if pricing_tier not in self.PRICING_TIERS:
            raise ValueError(f"Invalid pricing_tier. Must be: {list(self.PRICING_TIERS.keys())}")

        result = self.db.execute("""
            INSERT INTO fleet_customers (
                company_name, fleet_type,
                primary_contact_name, primary_contact_email, primary_contact_phone,
                billing_address, city, state, zip_code,
                tax_id, pricing_tier, payment_terms,
                notes, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            company_name,
            fleet_type,
            primary_contact_name,
            primary_contact_email,
            primary_contact_phone,
            billing_address,
            city,
            state,
            zip_code,
            tax_id,
            pricing_tier,
            payment_terms,
            notes,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        fleet_id = result[0]['id']

        tier_info = self.PRICING_TIERS[pricing_tier]

        print(f"[OK] Created fleet customer: {company_name}")
        print(f"     Type: {fleet_type}")
        print(f"     Tier: {tier_info['name']} ({tier_info['discount_percent']}% discount)")
        print(f"     Payment terms: {payment_terms}")

        return fleet_id

    def get_fleet_customer(self, fleet_id: int) -> Optional[Dict]:
        """Get fleet customer by ID"""
        result = self.db.execute("""
            SELECT * FROM fleet_customers WHERE id = ?
        """, (fleet_id,))

        return dict(result[0]) if result else None

    def update_fleet_customer(self, fleet_id: int, **updates) -> bool:
        """Update fleet customer details"""
        allowed_fields = [
            'company_name', 'primary_contact_name', 'primary_contact_email',
            'primary_contact_phone', 'billing_address', 'city', 'state',
            'zip_code', 'tax_id', 'payment_terms', 'notes', 'status'
        ]

        set_clauses = []
        values = []

        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(fleet_id)

        self.db.execute(f"""
            UPDATE fleet_customers
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, tuple(values))

        return True

    def update_pricing_tier(
        self,
        fleet_id: int,
        new_tier: str,
        effective_date: Optional[date] = None
    ) -> bool:
        """
        Update fleet pricing tier

        Args:
            fleet_id: Fleet customer ID
            new_tier: New pricing tier
            effective_date: When tier change takes effect
        """
        if new_tier not in self.PRICING_TIERS:
            raise ValueError(f"Invalid tier. Must be: {list(self.PRICING_TIERS.keys())}")

        self.db.execute("""
            UPDATE fleet_customers
            SET pricing_tier = ?,
                tier_updated_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            new_tier,
            (effective_date or date.today()).isoformat(),
            datetime.now().isoformat(),
            fleet_id
        ))

        tier_info = self.PRICING_TIERS[new_tier]

        print(f"[OK] Updated fleet {fleet_id} to {tier_info['name']} tier")
        print(f"     Discount: {tier_info['discount_percent']}%")

        return True

    def get_all_fleet_customers(self, active_only: bool = True) -> List[Dict]:
        """Get all fleet customers"""
        if active_only:
            results = self.db.execute("""
                SELECT * FROM fleet_customers
                WHERE status = 'ACTIVE'
                ORDER BY company_name
            """)
        else:
            results = self.db.execute("""
                SELECT * FROM fleet_customers
                ORDER BY company_name
            """)

        return [dict(row) for row in results]

    # ========================================================================
    # BATCH JOB CREATION
    # ========================================================================

    def create_batch_job(
        self,
        fleet_id: int,
        batch_name: str,
        vehicles: List[Dict],
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create batch job for multiple vehicles

        Args:
            fleet_id: Fleet customer ID
            batch_name: Batch identifier (e.g., "Weekly Service - Nov 18")
            vehicles: List of vehicle dictionaries
            created_by: Who created batch
            notes: Batch notes

        Returns:
            Batch job ID
        """
        total_cost = sum(v.get('estimated_cost', 0) for v in vehicles)

        # Create batch record
        result = self.db.execute("""
            INSERT INTO batch_jobs (
                fleet_customer_id, batch_name,
                vehicle_count, total_estimated_cost,
                created_by, notes, created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fleet_id,
            batch_name,
            len(vehicles),
            total_cost,
            created_by,
            notes,
            datetime.now().isoformat(),
            'PENDING'
        ))

        batch_id = result[0]['id']

        # Create individual vehicle records
        for vehicle in vehicles:
            self.db.execute("""
                INSERT INTO batch_vehicles (
                    batch_job_id, stock_number,
                    year, make, model, vin, color,
                    damage_type, estimated_cost,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                vehicle.get('stock_number'),
                vehicle.get('year'),
                vehicle.get('make'),
                vehicle.get('model'),
                vehicle.get('vin'),
                vehicle.get('color'),
                vehicle.get('damage_type'),
                vehicle.get('estimated_cost', 0),
                'PENDING',
                datetime.now().isoformat()
            ))

        print(f"[OK] Created batch job: {batch_name}")
        print(f"     Vehicles: {len(vehicles)}")
        print(f"     Total estimated: ${total_cost:,.2f}")

        return batch_id

    def add_vehicle_to_batch(self, batch_id: int, vehicle: Dict) -> int:
        """
        Add vehicle to existing batch

        Args:
            batch_id: Batch job ID
            vehicle: Vehicle dictionary

        Returns:
            Batch vehicle ID
        """
        result = self.db.execute("""
            INSERT INTO batch_vehicles (
                batch_job_id, stock_number,
                year, make, model, vin, color,
                damage_type, estimated_cost,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            vehicle.get('stock_number'),
            vehicle.get('year'),
            vehicle.get('make'),
            vehicle.get('model'),
            vehicle.get('vin'),
            vehicle.get('color'),
            vehicle.get('damage_type'),
            vehicle.get('estimated_cost', 0),
            'PENDING',
            datetime.now().isoformat()
        ))

        vehicle_id = result[0]['id']

        # Update batch totals
        self.db.execute("""
            UPDATE batch_jobs
            SET vehicle_count = vehicle_count + 1,
                total_estimated_cost = total_estimated_cost + ?,
                updated_at = ?
            WHERE id = ?
        """, (
            vehicle.get('estimated_cost', 0),
            datetime.now().isoformat(),
            batch_id
        ))

        print(f"[OK] Added vehicle to batch {batch_id}")
        print(f"     Stock: {vehicle.get('stock_number')}")
        print(f"     Vehicle: {vehicle.get('year')} {vehicle.get('make')} {vehicle.get('model')}")

        return vehicle_id

    def update_batch_vehicle_status(
        self,
        batch_vehicle_id: int,
        new_status: str,
        actual_cost: Optional[float] = None,
        completed_at: Optional[datetime] = None,
        assigned_tech: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update batch vehicle status

        Args:
            batch_vehicle_id: Batch vehicle ID
            new_status: New status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED)
            actual_cost: Actual repair cost (if different from estimate)
            completed_at: Completion timestamp
            assigned_tech: Assigned technician
            notes: Status notes
        """
        self.db.execute("""
            UPDATE batch_vehicles
            SET status = ?,
                actual_cost = COALESCE(?, actual_cost),
                completed_at = ?,
                assigned_tech = COALESCE(?, assigned_tech),
                notes = COALESCE(?, notes),
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            actual_cost,
            completed_at.isoformat() if completed_at else None,
            assigned_tech,
            notes,
            datetime.now().isoformat(),
            batch_vehicle_id
        ))

        print(f"[OK] Updated batch vehicle {batch_vehicle_id} to {new_status}")

        return True

    def get_batch_details(self, batch_id: int) -> Dict:
        """Get batch job details with all vehicles"""
        batch_result = self.db.execute("""
            SELECT * FROM batch_jobs WHERE id = ?
        """, (batch_id,))

        if not batch_result:
            return {}

        batch = dict(batch_result[0])

        vehicles = self.db.execute("""
            SELECT * FROM batch_vehicles WHERE batch_job_id = ?
            ORDER BY stock_number
        """, (batch_id,))

        vehicle_list = [dict(v) for v in vehicles]

        return {
            'batch': batch,
            'vehicles': vehicle_list,
            'vehicle_count': len(vehicle_list),
            'completed_count': sum(1 for v in vehicle_list if v['status'] == 'COMPLETED'),
            'pending_count': sum(1 for v in vehicle_list if v['status'] == 'PENDING'),
            'in_progress_count': sum(1 for v in vehicle_list if v['status'] == 'IN_PROGRESS'),
            'cancelled_count': sum(1 for v in vehicle_list if v['status'] == 'CANCELLED')
        }

    def get_fleet_batches(
        self,
        fleet_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get all batches for a fleet customer"""
        if status:
            results = self.db.execute("""
                SELECT * FROM batch_jobs
                WHERE fleet_customer_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (fleet_id, status, limit))
        else:
            results = self.db.execute("""
                SELECT * FROM batch_jobs
                WHERE fleet_customer_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (fleet_id, limit))

        return [dict(row) for row in results]

    # ========================================================================
    # VOLUME PRICING
    # ========================================================================

    def calculate_fleet_pricing(self, fleet_id: int, base_cost: float) -> Dict:
        """
        Calculate pricing with fleet discount

        Args:
            fleet_id: Fleet customer ID
            base_cost: Base repair cost

        Returns:
            Pricing breakdown with discount
        """
        fleet = self.get_fleet_customer(fleet_id)

        if not fleet:
            raise ValueError(f"Fleet customer {fleet_id} not found")

        tier = fleet['pricing_tier']
        tier_info = self.PRICING_TIERS[tier]

        discount_percent = tier_info['discount_percent']
        discount_amount = base_cost * (discount_percent / 100)
        final_cost = base_cost - discount_amount

        return {
            'base_cost': base_cost,
            'pricing_tier': tier,
            'tier_name': tier_info['name'],
            'discount_percent': discount_percent,
            'discount_amount': round(discount_amount, 2),
            'final_cost': round(final_cost, 2),
            'savings': round(discount_amount, 2)
        }

    def calculate_batch_pricing(self, batch_id: int) -> Dict:
        """Calculate pricing for entire batch"""
        batch_details = self.get_batch_details(batch_id)

        if not batch_details:
            raise ValueError(f"Batch {batch_id} not found")

        batch = batch_details['batch']
        vehicles = batch_details['vehicles']

        # Calculate totals
        subtotal = sum(v.get('actual_cost') or v.get('estimated_cost', 0) for v in vehicles)

        # Get fleet discount
        pricing = self.calculate_fleet_pricing(batch['fleet_customer_id'], subtotal)

        pricing['batch_id'] = batch_id
        pricing['vehicle_count'] = len(vehicles)

        return pricing

    def get_recommended_tier(
        self,
        fleet_id: int,
        months_to_analyze: int = 3
    ) -> Dict:
        """
        Recommend pricing tier based on volume

        Analyzes recent activity to suggest tier upgrade/downgrade
        """
        cutoff_date = (datetime.now() - timedelta(days=months_to_analyze * 30)).isoformat()

        # Get vehicle count from last N months
        result = self.db.execute("""
            SELECT COUNT(*) as vehicle_count
            FROM batch_vehicles bv
            JOIN batch_jobs bj ON bj.id = bv.batch_job_id
            WHERE bj.fleet_customer_id = ?
              AND bv.created_at >= ?
        """, (fleet_id, cutoff_date))

        total_vehicles = result[0]['vehicle_count'] if result else 0
        avg_per_month = total_vehicles / months_to_analyze if months_to_analyze > 0 else 0

        # Determine recommended tier
        recommended_tier = 'STANDARD'
        for tier, info in sorted(
            self.PRICING_TIERS.items(),
            key=lambda x: x[1]['min_vehicles_per_month'],
            reverse=True
        ):
            if avg_per_month >= info['min_vehicles_per_month']:
                recommended_tier = tier
                break

        fleet = self.get_fleet_customer(fleet_id)
        current_tier = fleet['pricing_tier'] if fleet else 'STANDARD'

        current_discount = self.PRICING_TIERS[current_tier]['discount_percent']
        recommended_discount = self.PRICING_TIERS[recommended_tier]['discount_percent']

        return {
            'vehicles_analyzed': total_vehicles,
            'months_analyzed': months_to_analyze,
            'avg_vehicles_per_month': round(avg_per_month, 1),
            'current_tier': current_tier,
            'current_discount': current_discount,
            'recommended_tier': recommended_tier,
            'recommended_discount': recommended_discount,
            'should_upgrade': recommended_discount > current_discount,
            'should_downgrade': recommended_discount < current_discount
        }

    # ========================================================================
    # BULK INVOICING
    # ========================================================================

    def create_bulk_invoice(
        self,
        batch_id: int,
        invoice_date: Optional[date] = None,
        due_date: Optional[date] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create single invoice for entire batch

        Args:
            batch_id: Batch job ID
            invoice_date: Invoice date
            due_date: Payment due date
            notes: Invoice notes

        Returns:
            Invoice ID
        """
        batch_details = self.get_batch_details(batch_id)

        if not batch_details:
            raise ValueError(f"Batch {batch_id} not found")

        batch = batch_details['batch']
        vehicles = batch_details['vehicles']

        fleet = self.get_fleet_customer(batch['fleet_customer_id'])

        # Calculate totals with fleet discount
        subtotal = sum(v.get('actual_cost') or v.get('estimated_cost', 0) for v in vehicles)
        pricing = self.calculate_fleet_pricing(batch['fleet_customer_id'], subtotal)

        # Set dates
        if not invoice_date:
            invoice_date = date.today()

        if not due_date:
            payment_terms = fleet.get('payment_terms', 'NET_30')
            if payment_terms == 'NET_30':
                due_date = invoice_date + timedelta(days=30)
            elif payment_terms == 'NET_15':
                due_date = invoice_date + timedelta(days=15)
            elif payment_terms == 'NET_45':
                due_date = invoice_date + timedelta(days=45)
            elif payment_terms == 'NET_60':
                due_date = invoice_date + timedelta(days=60)
            else:
                due_date = invoice_date

        # Generate invoice number
        invoice_number = f"FLEET-{batch_id:06d}"

        result = self.db.execute("""
            INSERT INTO fleet_invoices (
                batch_job_id, fleet_customer_id,
                invoice_number, invoice_date, due_date,
                subtotal, discount_percent, discount_amount,
                total, balance_due,
                payment_terms, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            batch['fleet_customer_id'],
            invoice_number,
            invoice_date.isoformat(),
            due_date.isoformat(),
            pricing['base_cost'],
            pricing['discount_percent'],
            pricing['discount_amount'],
            pricing['final_cost'],
            pricing['final_cost'],
            fleet.get('payment_terms', 'NET_30'),
            notes,
            datetime.now().isoformat(),
            'SENT'
        ))

        invoice_id = result[0]['id']

        print(f"[OK] Created bulk invoice: {invoice_number}")
        print(f"     Fleet: {fleet['company_name']}")
        print(f"     Vehicles: {len(vehicles)}")
        print(f"     Subtotal: ${pricing['base_cost']:,.2f}")
        print(f"     Discount ({pricing['discount_percent']}%): -${pricing['discount_amount']:,.2f}")
        print(f"     Total: ${pricing['final_cost']:,.2f}")
        print(f"     Due: {due_date.strftime('%B %d, %Y')}")

        return invoice_id

    def record_invoice_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_method: str = 'CHECK',
        reference: Optional[str] = None
    ) -> bool:
        """Record payment against fleet invoice"""
        self.db.execute("""
            UPDATE fleet_invoices
            SET amount_paid = amount_paid + ?,
                balance_due = balance_due - ?,
                status = CASE
                    WHEN balance_due - ? <= 0 THEN 'PAID'
                    ELSE 'PARTIAL'
                END,
                paid_at = CASE
                    WHEN balance_due - ? <= 0 THEN ?
                    ELSE paid_at
                END
            WHERE id = ?
        """, (
            amount, amount, amount, amount,
            datetime.now().isoformat(),
            invoice_id
        ))

        print(f"[OK] Recorded ${amount:,.2f} payment on invoice {invoice_id}")

        return True

    def get_fleet_invoices(
        self,
        fleet_id: int,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get all invoices for a fleet customer"""
        if status:
            results = self.db.execute("""
                SELECT * FROM fleet_invoices
                WHERE fleet_customer_id = ? AND status = ?
                ORDER BY invoice_date DESC
            """, (fleet_id, status))
        else:
            results = self.db.execute("""
                SELECT * FROM fleet_invoices
                WHERE fleet_customer_id = ?
                ORDER BY invoice_date DESC
            """, (fleet_id,))

        return [dict(row) for row in results]

    # ========================================================================
    # FLEET CONTRACTS
    # ========================================================================

    def create_fleet_contract(
        self,
        fleet_id: int,
        start_date: date,
        end_date: date,
        pricing_tier: str,
        min_monthly_volume: int,
        discount_percent: float,
        terms: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Create fleet service contract"""
        contract_number = f"FC-{fleet_id:04d}-{datetime.now().strftime('%Y%m')}"

        result = self.db.execute("""
            INSERT INTO fleet_contracts (
                fleet_customer_id, contract_number,
                start_date, end_date,
                pricing_tier, min_monthly_volume,
                discount_percent, terms, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            fleet_id,
            contract_number,
            start_date.isoformat(),
            end_date.isoformat(),
            pricing_tier,
            min_monthly_volume,
            discount_percent,
            terms,
            notes,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        contract_id = result[0]['id']

        print(f"[OK] Created fleet contract: {contract_number}")
        print(f"     Period: {start_date} to {end_date}")
        print(f"     Min volume: {min_monthly_volume} vehicles/month")
        print(f"     Discount: {discount_percent}%")

        return contract_id

    # ========================================================================
    # REPORTING
    # ========================================================================

    def get_fleet_performance(
        self,
        fleet_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get fleet customer performance metrics

        Returns comprehensive analytics
        """
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()

        fleet = self.get_fleet_customer(fleet_id)

        if not fleet:
            return {}

        # Get batch jobs in period
        batches = self.db.execute("""
            SELECT * FROM batch_jobs
            WHERE fleet_customer_id = ?
              AND DATE(created_at) >= ?
              AND DATE(created_at) <= ?
        """, (fleet_id, start_date.isoformat(), end_date.isoformat()))

        # Get all vehicles
        vehicle_result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM batch_vehicles bv
            JOIN batch_jobs bj ON bj.id = bv.batch_job_id
            WHERE bj.fleet_customer_id = ?
              AND DATE(bv.created_at) >= ?
              AND DATE(bv.created_at) <= ?
        """, (fleet_id, start_date.isoformat(), end_date.isoformat()))

        total_vehicles = vehicle_result[0]['count'] if vehicle_result else 0

        # Get revenue
        revenue = self.db.execute("""
            SELECT
                SUM(total) as total_revenue,
                SUM(discount_amount) as total_discounts
            FROM fleet_invoices
            WHERE fleet_customer_id = ?
              AND DATE(invoice_date) >= ?
              AND DATE(invoice_date) <= ?
        """, (fleet_id, start_date.isoformat(), end_date.isoformat()))

        total_revenue = revenue[0]['total_revenue'] or 0
        total_discounts = revenue[0]['total_discounts'] or 0

        # Calculate metrics
        days_in_period = (end_date - start_date).days or 1
        months_in_period = days_in_period / 30

        return {
            'fleet_id': fleet_id,
            'company_name': fleet['company_name'],
            'fleet_type': fleet['fleet_type'],
            'pricing_tier': fleet['pricing_tier'],
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days_in_period
            },
            'activity': {
                'total_batches': len(batches),
                'total_vehicles': total_vehicles,
                'avg_vehicles_per_month': round(total_vehicles / months_in_period, 1) if months_in_period > 0 else 0,
                'avg_vehicles_per_batch': round(total_vehicles / len(batches), 1) if batches else 0
            },
            'revenue': {
                'total_revenue': total_revenue,
                'total_discounts_given': total_discounts,
                'avg_revenue_per_vehicle': round(total_revenue / total_vehicles, 2) if total_vehicles > 0 else 0
            }
        }

    def generate_fleet_summary_report(self, fleet_id: int) -> str:
        """Generate text summary report for fleet customer"""
        fleet = self.get_fleet_customer(fleet_id)
        performance = self.get_fleet_performance(fleet_id)

        if not fleet:
            return "Fleet customer not found"

        tier_info = self.PRICING_TIERS[fleet['pricing_tier']]

        lines = []
        lines.append("=" * 60)
        lines.append("FLEET CUSTOMER SUMMARY")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"Company: {fleet['company_name']}")
        lines.append(f"Type: {fleet['fleet_type']}")
        lines.append(f"Contact: {fleet['primary_contact_name']}")
        lines.append(f"Email: {fleet['primary_contact_email']}")
        lines.append(f"Phone: {fleet['primary_contact_phone']}")
        lines.append("")
        lines.append("PRICING")
        lines.append("-" * 60)
        lines.append(f"Tier: {tier_info['name']}")
        lines.append(f"Discount: {tier_info['discount_percent']}%")
        lines.append(f"Payment Terms: {fleet['payment_terms']}")
        lines.append("")
        lines.append("ACTIVITY (Last 90 Days)")
        lines.append("-" * 60)
        lines.append(f"Total Batches: {performance['activity']['total_batches']}")
        lines.append(f"Total Vehicles: {performance['activity']['total_vehicles']}")
        lines.append(f"Avg Vehicles/Month: {performance['activity']['avg_vehicles_per_month']}")
        lines.append("")
        lines.append("REVENUE")
        lines.append("-" * 60)
        lines.append(f"Total Revenue: ${performance['revenue']['total_revenue']:,.2f}")
        lines.append(f"Discounts Given: ${performance['revenue']['total_discounts_given']:,.2f}")
        lines.append(f"Avg Per Vehicle: ${performance['revenue']['avg_revenue_per_vehicle']:,.2f}")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
