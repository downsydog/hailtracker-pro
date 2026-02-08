"""
PDR CRM Part 26 - Insurance Partner Manager
Manage insurance partners, claims processing, and DRP programs

FEATURES:
- Insurance partner accounts
- Claims processing workflow
- Pre-authorization management
- Photo documentation system
- Preferred shop programs (DRP)
- Direct billing
- Automated claim submission
- Supplement requests
- Payment reconciliation
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class InsurancePartnerManager:
    """
    Manage insurance partners and claims processing

    Integration with insurance companies for PDR work
    """

    # Major insurance carriers
    MAJOR_CARRIERS = [
        'STATE_FARM',
        'GEICO',
        'PROGRESSIVE',
        'ALLSTATE',
        'USAA',
        'LIBERTY_MUTUAL',
        'FARMERS',
        'NATIONWIDE',
        'TRAVELERS',
        'AAA'
    ]

    # Claim statuses
    CLAIM_STATUSES = [
        'PENDING_AUTH',      # Waiting for authorization
        'AUTHORIZED',        # Approved by insurance
        'IN_PROGRESS',       # Work in progress
        'COMPLETED',         # Work finished
        'SUBMITTED',         # Claim submitted
        'PAID',              # Payment received
        'DENIED',            # Claim denied
        'SUPPLEMENTED'       # Supplement requested
    ]

    # Loss types
    LOSS_TYPES = ['HAIL', 'COLLISION', 'COMPREHENSIVE', 'VANDALISM', 'OTHER']

    # Payment methods
    PAYMENT_METHODS = ['CHECK', 'ACH', 'WIRE', 'EFT']

    def __init__(self, db):
        """Initialize insurance partner manager with database instance"""
        self.db = db
        self._ensure_insurance_tables()

    def _ensure_insurance_tables(self):
        """Ensure insurance-related tables exist"""
        # Insurance partners table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS insurance_partners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                carrier_name TEXT NOT NULL,
                carrier_type TEXT NOT NULL,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                claims_email TEXT,
                claims_phone TEXT,
                drp_agreement INTEGER DEFAULT 0,
                drp_discount_percent REAL,
                drp_updated_at TIMESTAMP,
                requires_pre_auth INTEGER DEFAULT 1,
                photo_requirements TEXT,
                payment_terms TEXT DEFAULT 'NET_30',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Insurance claims table (extended)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS insurance_claims_ext (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER,
                insurance_partner_id INTEGER NOT NULL,
                claim_number TEXT NOT NULL,
                policy_number TEXT NOT NULL,
                policyholder_name TEXT NOT NULL,
                deductible_amount REAL DEFAULT 0,
                date_of_loss DATE,
                loss_type TEXT DEFAULT 'HAIL',
                adjuster_name TEXT,
                adjuster_phone TEXT,
                adjuster_email TEXT,
                authorization_number TEXT,
                authorized_amount REAL,
                authorized_by TEXT,
                authorized_at TIMESTAMP,
                authorization_notes TEXT,
                requires_inspection INTEGER DEFAULT 0,
                submitted_at TIMESTAMP,
                submission_method TEXT,
                submitted_amount REAL,
                supporting_documents TEXT,
                paid_at TIMESTAMP,
                paid_amount REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING_AUTH',
                FOREIGN KEY (insurance_partner_id) REFERENCES insurance_partners(id)
            )
        """)

        # Claim photos table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS claim_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                photo_type TEXT NOT NULL,
                file_path TEXT,
                description TEXT,
                taken_at TIMESTAMP,
                uploaded_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES insurance_claims_ext(id)
            )
        """)

        # Claim supplements table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS claim_supplements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                supplement_reason TEXT NOT NULL,
                additional_damage_found TEXT,
                original_estimate REAL,
                supplement_amount REAL,
                approved_amount REAL,
                approved_by TEXT,
                approved_at TIMESTAMP,
                approval_notes TEXT,
                supporting_photos TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                FOREIGN KEY (claim_id) REFERENCES insurance_claims_ext(id)
            )
        """)

        # Insurance payments table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS insurance_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                payment_amount REAL NOT NULL,
                payment_method TEXT,
                check_number TEXT,
                payment_date DATE,
                reference_number TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES insurance_claims_ext(id)
            )
        """)

    # ========================================================================
    # INSURANCE PARTNER MANAGEMENT
    # ========================================================================

    def create_insurance_partner(
        self,
        carrier_name: str,
        carrier_type: str,
        contact_name: str,
        contact_email: str,
        contact_phone: str,
        claims_email: Optional[str] = None,
        claims_phone: Optional[str] = None,
        drp_agreement: bool = False,
        drp_discount_percent: Optional[float] = None,
        requires_pre_auth: bool = True,
        photo_requirements: Optional[Dict] = None,
        payment_terms: str = 'NET_30',
        notes: Optional[str] = None
    ) -> int:
        """
        Create insurance partner account

        Args:
            carrier_name: Insurance company name
            carrier_type: Type (STATE_FARM, GEICO, etc.)
            contact_name: Account representative
            contact_email: Rep email
            contact_phone: Rep phone
            claims_email: Claims submission email
            claims_phone: Claims phone
            drp_agreement: Direct Repair Program agreement
            drp_discount_percent: DRP discount (if applicable)
            requires_pre_auth: Requires pre-authorization
            photo_requirements: Photo documentation requirements
            payment_terms: Payment terms
            notes: Account notes

        Returns:
            Insurance partner ID
        """
        result = self.db.execute("""
            INSERT INTO insurance_partners (
                carrier_name, carrier_type,
                contact_name, contact_email, contact_phone,
                claims_email, claims_phone,
                drp_agreement, drp_discount_percent,
                requires_pre_auth, photo_requirements,
                payment_terms, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            carrier_name,
            carrier_type,
            contact_name,
            contact_email,
            contact_phone,
            claims_email,
            claims_phone,
            1 if drp_agreement else 0,
            drp_discount_percent,
            1 if requires_pre_auth else 0,
            json.dumps(photo_requirements) if photo_requirements else None,
            payment_terms,
            notes,
            datetime.now().isoformat(),
            'ACTIVE'
        ))

        partner_id = result[0]['id']

        print(f"[OK] Created insurance partner: {carrier_name}")
        print(f"     Contact: {contact_name}")
        if drp_agreement:
            print(f"     DRP Agreement: Yes ({drp_discount_percent}% discount)")
        print(f"     Pre-auth required: {requires_pre_auth}")

        return partner_id

    def get_insurance_partner(self, partner_id: int) -> Optional[Dict]:
        """Get insurance partner by ID"""
        result = self.db.execute("""
            SELECT * FROM insurance_partners WHERE id = ?
        """, (partner_id,))

        if not result:
            return None

        partner = dict(result[0])
        if partner.get('photo_requirements'):
            partner['photo_requirements'] = json.loads(partner['photo_requirements'])

        return partner

    def update_drp_status(
        self,
        partner_id: int,
        drp_agreement: bool,
        drp_discount_percent: Optional[float] = None,
        effective_date: Optional[date] = None
    ) -> bool:
        """
        Update Direct Repair Program status

        Args:
            partner_id: Insurance partner ID
            drp_agreement: DRP agreement active
            drp_discount_percent: DRP discount percentage
            effective_date: When change takes effect
        """
        self.db.execute("""
            UPDATE insurance_partners
            SET drp_agreement = ?,
                drp_discount_percent = ?,
                drp_updated_at = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            1 if drp_agreement else 0,
            drp_discount_percent,
            (effective_date or date.today()).isoformat(),
            datetime.now().isoformat(),
            partner_id
        ))

        status = "activated" if drp_agreement else "deactivated"
        print(f"[OK] DRP agreement {status} for partner {partner_id}")
        if drp_agreement and drp_discount_percent:
            print(f"     Discount: {drp_discount_percent}%")

        return True

    def get_all_partners(self, active_only: bool = True, drp_only: bool = False) -> List[Dict]:
        """Get all insurance partners"""
        query = "SELECT * FROM insurance_partners WHERE 1=1"

        if active_only:
            query += " AND status = 'ACTIVE'"
        if drp_only:
            query += " AND drp_agreement = 1"

        query += " ORDER BY carrier_name"

        results = self.db.execute(query)
        return [dict(row) for row in results]

    # ========================================================================
    # CLAIMS PROCESSING
    # ========================================================================

    def create_insurance_claim(
        self,
        insurance_partner_id: int,
        claim_number: str,
        policy_number: str,
        policyholder_name: str,
        deductible_amount: float,
        date_of_loss: date,
        loss_type: str = 'HAIL',
        job_id: Optional[int] = None,
        adjuster_name: Optional[str] = None,
        adjuster_phone: Optional[str] = None,
        adjuster_email: Optional[str] = None,
        authorization_number: Optional[str] = None,
        authorized_amount: Optional[float] = None,
        requires_inspection: bool = False,
        notes: Optional[str] = None
    ) -> int:
        """
        Create insurance claim record

        Args:
            insurance_partner_id: Insurance partner ID
            claim_number: Insurance claim number
            policy_number: Policy number
            policyholder_name: Policy holder name
            deductible_amount: Deductible amount
            date_of_loss: Date of loss
            loss_type: Type of loss (HAIL, COLLISION, etc.)
            job_id: Optional job ID
            adjuster_name: Adjuster name
            adjuster_phone: Adjuster phone
            adjuster_email: Adjuster email
            authorization_number: Pre-auth number
            authorized_amount: Authorized repair amount
            requires_inspection: Needs adjuster inspection
            notes: Claim notes

        Returns:
            Claim ID
        """
        status = 'AUTHORIZED' if authorization_number else 'PENDING_AUTH'

        result = self.db.execute("""
            INSERT INTO insurance_claims_ext (
                job_id, insurance_partner_id,
                claim_number, policy_number, policyholder_name,
                deductible_amount, date_of_loss, loss_type,
                adjuster_name, adjuster_phone, adjuster_email,
                authorization_number, authorized_amount,
                requires_inspection, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            insurance_partner_id,
            claim_number,
            policy_number,
            policyholder_name,
            deductible_amount,
            date_of_loss.isoformat(),
            loss_type,
            adjuster_name,
            adjuster_phone,
            adjuster_email,
            authorization_number,
            authorized_amount,
            1 if requires_inspection else 0,
            notes,
            datetime.now().isoformat(),
            status
        ))

        claim_id = result[0]['id']

        print(f"[OK] Created insurance claim: {claim_number}")
        print(f"     Policyholder: {policyholder_name}")
        print(f"     Policy: {policy_number}")
        print(f"     Deductible: ${deductible_amount:,.2f}")
        if authorization_number:
            print(f"     Authorization: {authorization_number}")
            print(f"     Authorized amount: ${authorized_amount:,.2f}")
        else:
            print(f"     Status: Pending authorization")

        return claim_id

    def get_claim(self, claim_id: int) -> Optional[Dict]:
        """Get claim by ID"""
        result = self.db.execute("""
            SELECT * FROM insurance_claims_ext WHERE id = ?
        """, (claim_id,))

        return dict(result[0]) if result else None

    def authorize_claim(
        self,
        claim_id: int,
        authorization_number: str,
        authorized_amount: float,
        authorized_by: Optional[str] = None,
        authorization_notes: Optional[str] = None
    ) -> bool:
        """
        Authorize insurance claim

        Args:
            claim_id: Claim ID
            authorization_number: Authorization number
            authorized_amount: Authorized amount
            authorized_by: Who authorized (adjuster name)
            authorization_notes: Authorization notes
        """
        self.db.execute("""
            UPDATE insurance_claims_ext
            SET authorization_number = ?,
                authorized_amount = ?,
                authorized_by = ?,
                authorized_at = ?,
                authorization_notes = ?,
                status = 'AUTHORIZED',
                updated_at = ?
            WHERE id = ?
        """, (
            authorization_number,
            authorized_amount,
            authorized_by,
            datetime.now().isoformat(),
            authorization_notes,
            datetime.now().isoformat(),
            claim_id
        ))

        print(f"[OK] Claim {claim_id} authorized")
        print(f"     Authorization #: {authorization_number}")
        print(f"     Amount: ${authorized_amount:,.2f}")

        return True

    def update_claim_status(
        self,
        claim_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update claim status"""
        if new_status not in self.CLAIM_STATUSES:
            raise ValueError(f"Invalid status. Must be: {self.CLAIM_STATUSES}")

        self.db.execute("""
            UPDATE insurance_claims_ext
            SET status = ?,
                notes = COALESCE(?, notes),
                updated_at = ?
            WHERE id = ?
        """, (
            new_status,
            notes,
            datetime.now().isoformat(),
            claim_id
        ))

        print(f"[OK] Claim {claim_id} status updated to {new_status}")

        return True

    def submit_claim(
        self,
        claim_id: int,
        submission_method: str = 'ELECTRONIC',
        submitted_amount: Optional[float] = None,
        supporting_documents: Optional[List[str]] = None
    ) -> bool:
        """
        Submit claim to insurance company

        Args:
            claim_id: Claim ID
            submission_method: ELECTRONIC, EMAIL, FAX, PORTAL
            submitted_amount: Amount submitted
            supporting_documents: List of document paths/URLs

        Returns:
            True if successful
        """
        claim = self.get_claim(claim_id)

        if not claim:
            raise ValueError(f"Claim {claim_id} not found")

        if claim['status'] not in ['COMPLETED', 'AUTHORIZED', 'IN_PROGRESS']:
            raise ValueError("Claim must be authorized or completed before submission")

        amount = submitted_amount or claim.get('authorized_amount', 0)

        self.db.execute("""
            UPDATE insurance_claims_ext
            SET submitted_at = ?,
                submission_method = ?,
                submitted_amount = ?,
                supporting_documents = ?,
                status = 'SUBMITTED',
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            submission_method,
            amount,
            json.dumps(supporting_documents) if supporting_documents else None,
            datetime.now().isoformat(),
            claim_id
        ))

        print(f"[OK] Claim {claim['claim_number']} submitted")
        print(f"     Method: {submission_method}")
        print(f"     Amount: ${amount:,.2f}")

        return True

    # ========================================================================
    # PHOTO DOCUMENTATION
    # ========================================================================

    def add_claim_photos(
        self,
        claim_id: int,
        photos: List[Dict],
        uploaded_by: Optional[str] = None
    ) -> int:
        """
        Add photos to insurance claim

        Args:
            claim_id: Claim ID
            photos: List of photo dictionaries
            uploaded_by: Who uploaded photos

        Returns:
            Number of photos added
        """
        for photo in photos:
            taken_at = photo.get('taken_at')
            if isinstance(taken_at, datetime):
                taken_at = taken_at.isoformat()
            elif taken_at is None:
                taken_at = datetime.now().isoformat()

            self.db.execute("""
                INSERT INTO claim_photos (
                    claim_id, photo_type, file_path,
                    description, taken_at, uploaded_by,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                claim_id,
                photo.get('photo_type', 'other'),
                photo.get('file_path'),
                photo.get('description'),
                taken_at,
                uploaded_by,
                datetime.now().isoformat()
            ))

        print(f"[OK] Added {len(photos)} photos to claim {claim_id}")

        return len(photos)

    def get_claim_photos(self, claim_id: int) -> List[Dict]:
        """Get all photos for a claim"""
        results = self.db.execute("""
            SELECT * FROM claim_photos WHERE claim_id = ?
            ORDER BY created_at
        """, (claim_id,))

        return [dict(row) for row in results]

    def verify_photo_requirements(self, claim_id: int) -> Dict:
        """
        Verify claim meets photo requirements

        Returns verification status
        """
        claim = self.get_claim(claim_id)

        if not claim:
            return {'meets_requirements': False, 'error': 'Claim not found'}

        partner = self.get_insurance_partner(claim['insurance_partner_id'])

        if not partner:
            return {'meets_requirements': False, 'error': 'Partner not found'}

        photos = self.get_claim_photos(claim_id)

        # Parse requirements
        requirements = partner.get('photo_requirements', {})
        if isinstance(requirements, str):
            requirements = json.loads(requirements) if requirements else {}

        min_photos = requirements.get('min_photos', 4)
        required_angles = requirements.get('required_angles', [])

        # Check requirements
        photo_types = [p['photo_type'] for p in photos]

        meets_min = len(photos) >= min_photos
        missing_angles = [angle for angle in required_angles if angle not in photo_types]
        meets_angles = len(missing_angles) == 0

        verification = {
            'meets_requirements': meets_min and meets_angles,
            'total_photos': len(photos),
            'required_photos': min_photos,
            'has_minimum': meets_min,
            'photo_types': photo_types,
            'required_angles': required_angles,
            'missing_angles': missing_angles
        }

        return verification

    # ========================================================================
    # SUPPLEMENT REQUESTS
    # ========================================================================

    def create_supplement(
        self,
        claim_id: int,
        supplement_reason: str,
        additional_damage_found: str,
        original_estimate: float,
        supplement_amount: float,
        supporting_photos: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create supplement request

        Args:
            claim_id: Claim ID
            supplement_reason: Reason for supplement
            additional_damage_found: Description of additional damage
            original_estimate: Original estimate amount
            supplement_amount: Additional amount requested
            supporting_photos: Photo evidence
            notes: Additional notes

        Returns:
            Supplement ID
        """
        result = self.db.execute("""
            INSERT INTO claim_supplements (
                claim_id, supplement_reason,
                additional_damage_found,
                original_estimate, supplement_amount,
                supporting_photos, notes,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_id,
            supplement_reason,
            additional_damage_found,
            original_estimate,
            supplement_amount,
            json.dumps(supporting_photos) if supporting_photos else None,
            notes,
            datetime.now().isoformat(),
            'PENDING'
        ))

        supplement_id = result[0]['id']

        # Update claim status
        self.db.execute("""
            UPDATE insurance_claims_ext
            SET status = 'SUPPLEMENTED',
                updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), claim_id))

        print(f"[OK] Created supplement request for claim {claim_id}")
        print(f"     Reason: {supplement_reason}")
        print(f"     Original: ${original_estimate:,.2f}")
        print(f"     Supplement: ${supplement_amount:,.2f}")
        print(f"     New total: ${original_estimate + supplement_amount:,.2f}")

        return supplement_id

    def approve_supplement(
        self,
        supplement_id: int,
        approved_amount: float,
        approved_by: Optional[str] = None,
        approval_notes: Optional[str] = None
    ) -> bool:
        """Approve supplement request"""
        self.db.execute("""
            UPDATE claim_supplements
            SET status = 'APPROVED',
                approved_amount = ?,
                approved_by = ?,
                approved_at = ?,
                approval_notes = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            approved_amount,
            approved_by,
            datetime.now().isoformat(),
            approval_notes,
            datetime.now().isoformat(),
            supplement_id
        ))

        print(f"[OK] Supplement {supplement_id} approved")
        print(f"     Approved amount: ${approved_amount:,.2f}")

        return True

    def get_claim_supplements(self, claim_id: int) -> List[Dict]:
        """Get all supplements for a claim"""
        results = self.db.execute("""
            SELECT * FROM claim_supplements WHERE claim_id = ?
            ORDER BY created_at
        """, (claim_id,))

        return [dict(row) for row in results]

    # ========================================================================
    # PAYMENT PROCESSING
    # ========================================================================

    def record_insurance_payment(
        self,
        claim_id: int,
        payment_amount: float,
        payment_method: str = 'CHECK',
        check_number: Optional[str] = None,
        payment_date: Optional[date] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Record payment from insurance company

        Args:
            claim_id: Claim ID
            payment_amount: Payment amount
            payment_method: CHECK, ACH, WIRE, EFT
            check_number: Check number (if applicable)
            payment_date: Date payment received
            reference_number: Payment reference
            notes: Payment notes

        Returns:
            Payment ID
        """
        result = self.db.execute("""
            INSERT INTO insurance_payments (
                claim_id, payment_amount, payment_method,
                check_number, payment_date, reference_number,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_id,
            payment_amount,
            payment_method,
            check_number,
            (payment_date or date.today()).isoformat(),
            reference_number,
            notes,
            datetime.now().isoformat()
        ))

        payment_id = result[0]['id']

        # Update claim status
        self.db.execute("""
            UPDATE insurance_claims_ext
            SET status = 'PAID',
                paid_at = ?,
                paid_amount = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            payment_amount,
            datetime.now().isoformat(),
            claim_id
        ))

        print(f"[OK] Recorded insurance payment")
        print(f"     Claim ID: {claim_id}")
        print(f"     Amount: ${payment_amount:,.2f}")
        print(f"     Method: {payment_method}")
        if check_number:
            print(f"     Check #: {check_number}")

        return payment_id

    def get_claim_payments(self, claim_id: int) -> List[Dict]:
        """Get all payments for a claim"""
        results = self.db.execute("""
            SELECT * FROM insurance_payments WHERE claim_id = ?
            ORDER BY payment_date
        """, (claim_id,))

        return [dict(row) for row in results]

    # ========================================================================
    # REPORTING
    # ========================================================================

    def get_partner_performance(
        self,
        partner_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """
        Get insurance partner performance metrics

        Returns comprehensive analytics
        """
        if not start_date:
            start_date = date.today() - timedelta(days=90)
        if not end_date:
            end_date = date.today()

        partner = self.get_insurance_partner(partner_id)

        if not partner:
            return {}

        # Get claims in period
        claims = self.db.execute("""
            SELECT * FROM insurance_claims_ext
            WHERE insurance_partner_id = ?
              AND DATE(created_at) >= ?
              AND DATE(created_at) <= ?
        """, (partner_id, start_date.isoformat(), end_date.isoformat()))

        claims_list = [dict(c) for c in claims]

        # Count by status
        status_counts = {}
        for claim in claims_list:
            status = claim['status']
            status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate revenue
        total_authorized = sum(c.get('authorized_amount') or 0 for c in claims_list)
        total_paid = sum(c.get('paid_amount') or 0 for c in claims_list if c.get('paid_amount'))

        # Calculate average days to payment
        paid_claims = [c for c in claims_list if c.get('paid_at')]

        avg_days_to_pay = 0
        if paid_claims:
            total_days = 0
            for claim in paid_claims:
                created = datetime.fromisoformat(claim['created_at'])
                paid = datetime.fromisoformat(claim['paid_at'])
                total_days += (paid - created).days
            avg_days_to_pay = total_days / len(paid_claims)

        # Authorization rate
        auth_count = len([c for c in claims_list if c.get('authorization_number')])
        auth_rate = (auth_count / len(claims_list) * 100) if claims_list else 0

        performance = {
            'partner_id': partner_id,
            'carrier_name': partner['carrier_name'],
            'drp_agreement': bool(partner['drp_agreement']),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days
            },
            'claims': {
                'total_claims': len(claims_list),
                'status_breakdown': status_counts,
                'authorization_rate': round(auth_rate, 1)
            },
            'financial': {
                'total_authorized': total_authorized,
                'total_paid': total_paid,
                'outstanding': total_authorized - total_paid,
                'avg_claim_amount': round(total_authorized / len(claims_list), 2) if claims_list else 0
            },
            'timing': {
                'avg_days_to_payment': round(avg_days_to_pay, 1)
            }
        }

        return performance

    def get_claim_details(self, claim_id: int) -> Optional[Dict]:
        """Get complete claim details with all related data"""
        claim = self.get_claim(claim_id)

        if not claim:
            return None

        # Get partner
        partner = self.get_insurance_partner(claim['insurance_partner_id'])

        # Get photos
        photos = self.get_claim_photos(claim_id)

        # Get supplements
        supplements = self.get_claim_supplements(claim_id)

        # Get payments
        payments = self.get_claim_payments(claim_id)

        return {
            'claim': claim,
            'partner': partner,
            'photos': photos,
            'supplements': supplements,
            'payments': payments
        }

    def get_pending_claims(self, partner_id: Optional[int] = None) -> List[Dict]:
        """Get all claims pending authorization"""
        if partner_id:
            results = self.db.execute("""
                SELECT c.*, p.carrier_name
                FROM insurance_claims_ext c
                JOIN insurance_partners p ON p.id = c.insurance_partner_id
                WHERE c.status = 'PENDING_AUTH'
                  AND c.insurance_partner_id = ?
                ORDER BY c.created_at
            """, (partner_id,))
        else:
            results = self.db.execute("""
                SELECT c.*, p.carrier_name
                FROM insurance_claims_ext c
                JOIN insurance_partners p ON p.id = c.insurance_partner_id
                WHERE c.status = 'PENDING_AUTH'
                ORDER BY c.created_at
            """)

        return [dict(row) for row in results]

    def get_drp_partners(self) -> List[Dict]:
        """Get all DRP (Direct Repair Program) partners"""
        return self.get_all_partners(active_only=True, drp_only=True)

    def calculate_drp_discount(self, partner_id: int, base_amount: float) -> Dict:
        """Calculate DRP discount for a partner"""
        partner = self.get_insurance_partner(partner_id)

        if not partner:
            return {'error': 'Partner not found'}

        if not partner['drp_agreement']:
            return {
                'base_amount': base_amount,
                'discount_percent': 0,
                'discount_amount': 0,
                'final_amount': base_amount,
                'is_drp': False
            }

        discount_percent = partner.get('drp_discount_percent') or 0
        discount_amount = base_amount * (discount_percent / 100)
        final_amount = base_amount - discount_amount

        return {
            'base_amount': base_amount,
            'discount_percent': discount_percent,
            'discount_amount': round(discount_amount, 2),
            'final_amount': round(final_amount, 2),
            'is_drp': True
        }
