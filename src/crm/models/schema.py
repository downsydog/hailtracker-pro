"""
Enterprise PDR CRM Database Schema
Salesforce-level data architecture for paintless dent repair

CORE ENTITIES:
- Customer: Person/company who owns vehicle
- Vehicle: Car being repaired
- Lead: Potential customer from hail event or other source
- Job: Individual repair job with full workflow
- JobStatus: Detailed status tracking (25+ stages)
- Technician: Shop technician with assignments
- Estimate: Quote for work
- Invoice: Final billing
- Payment: Payment tracking and splits
- InsuranceClaim: Claim workflow and adjuster tracking
- EmailTracking: Every email sent/received about claim
- Part: Parts needed for job
- PartOrder: Orders placed to suppliers
- Communication: SMS/Email/Phone log
- Document: Photos, PDFs, claim docs
- HailEvent: Links to your swath system!
- RevenueBreakdown: How money splits
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
import json


class DatabaseSchema:
    """Create and manage enterprise PDR database schema"""

    @staticmethod
    def create_all_tables(db_path: str = "data/pdr_crm.db"):
        """
        Create complete database schema

        This creates a Salesforce-level database structure for PDR
        """

        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Creating enterprise PDR CRM database...")
        print()

        # ====================================================================
        # LOCATIONS (Multi-shop support) - Create first for foreign keys
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Location Info
            name TEXT NOT NULL,
            location_code TEXT UNIQUE,

            -- Address
            street_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,

            -- Contact
            phone TEXT,
            email TEXT,

            -- Capacity
            max_concurrent_jobs INTEGER,
            tech_count INTEGER DEFAULT 0,

            -- Status
            status TEXT DEFAULT 'ACTIVE',

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
        """)

        print("[OK] Created locations table")

        # ====================================================================
        # CUSTOMERS
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Basic Info
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            company_name TEXT,
            customer_type TEXT DEFAULT 'INDIVIDUAL',  -- INDIVIDUAL, DEALERSHIP, FLEET, BODY_SHOP

            -- Contact
            email TEXT,
            phone TEXT,
            phone_secondary TEXT,
            preferred_contact TEXT DEFAULT 'PHONE',  -- PHONE, EMAIL, SMS

            -- Address
            street_address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,

            -- Customer Status
            status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, INACTIVE, DO_NOT_CONTACT
            customer_since DATE,
            last_contact_date DATE,

            -- Marketing
            source TEXT,  -- HAIL_EVENT, REFERRAL, WEBSITE, WALK_IN, DEALERSHIP
            referral_source TEXT,
            marketing_consent INTEGER DEFAULT 1,

            -- Preferences
            preferred_location_id INTEGER,
            notes TEXT,
            tags TEXT,  -- JSON array: ["VIP", "FLEET", "REPEAT"]

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            updated_by TEXT,
            deleted_at TIMESTAMP,  -- Soft delete

            FOREIGN KEY (preferred_location_id) REFERENCES locations(id)
        )
        """)

        print("[OK] Created customers table")

        # ====================================================================
        # VEHICLES
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,

            -- Vehicle Info
            vin TEXT,
            year INTEGER,
            make TEXT,
            model TEXT,
            color TEXT,
            license_plate TEXT,

            -- Insurance
            insurance_company TEXT,
            policy_number TEXT,
            claim_number TEXT,

            -- Status
            status TEXT DEFAULT 'ACTIVE',

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,

            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)

        print("[OK] Created vehicles table")

        # ====================================================================
        # HAIL EVENTS (Integration with swath system!)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hail_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Event Info
            event_date DATE NOT NULL,
            event_name TEXT,  -- "Dallas Hail - Nov 15, 2024"

            -- Location
            location_name TEXT,
            affected_area_sq_miles REAL,

            -- Swath Data (from your system!)
            swath_geojson TEXT,  -- Store the GeoJSON
            max_hail_size REAL,

            -- Impact
            estimated_vehicles INTEGER,
            potential_customers INTEGER,
            potential_revenue REAL,

            -- Campaign
            campaign_created INTEGER DEFAULT 0,
            leads_generated INTEGER DEFAULT 0,
            leads_converted INTEGER DEFAULT 0,

            -- Notes
            notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        print("[OK] Created hail_events table (swath integration!)")

        # ====================================================================
        # LEADS (From hail events, walk-ins, referrals)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Basic Info
            first_name TEXT,
            last_name TEXT,
            company_name TEXT,
            email TEXT,
            phone TEXT,

            -- Lead Source
            source TEXT NOT NULL,  -- HAIL_EVENT, REFERRAL, WEBSITE, PHONE, WALK_IN
            hail_event_id INTEGER,  -- Links to your swath system!

            -- Lead Scoring
            score INTEGER DEFAULT 0,  -- 0-100
            temperature TEXT DEFAULT 'WARM',  -- HOT, WARM, COLD

            -- Status
            status TEXT DEFAULT 'NEW',  -- NEW, CONTACTED, QUALIFIED, CONVERTED, LOST
            converted_to_customer_id INTEGER,
            lost_reason TEXT,

            -- Assignment
            assigned_to TEXT,  -- Salesperson
            assigned_at TIMESTAMP,

            -- Follow-up
            next_follow_up_date DATE,
            follow_up_count INTEGER DEFAULT 0,
            last_contact_date DATE,

            -- Vehicle Info (if known)
            vehicle_year INTEGER,
            vehicle_make TEXT,
            vehicle_model TEXT,

            -- Damage Info
            damage_type TEXT,  -- HAIL, DENT, DOOR_DING, COLLISION
            damage_description TEXT,
            estimated_repair_cost REAL,

            -- Notes
            notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,

            FOREIGN KEY (hail_event_id) REFERENCES hail_events(id),
            FOREIGN KEY (converted_to_customer_id) REFERENCES customers(id)
        )
        """)

        print("[OK] Created leads table")

        # ====================================================================
        # TECHNICIANS
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Basic Info
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,

            -- Employment
            employee_id TEXT UNIQUE,
            location_id INTEGER,
            status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, INACTIVE, ON_LEAVE
            hire_date DATE,

            -- Skills
            skill_level TEXT DEFAULT 'INTERMEDIATE',  -- APPRENTICE, INTERMEDIATE, EXPERT, MASTER
            certifications TEXT,  -- JSON array
            specialties TEXT,  -- JSON: ["HAIL", "ALUMINUM", "CONVENTIONAL"]

            -- Capacity
            max_jobs_concurrent INTEGER DEFAULT 3,
            current_job_count INTEGER DEFAULT 0,

            -- Performance
            avg_job_hours REAL,
            quality_score REAL,  -- 0-100

            -- Revenue Split
            pay_type TEXT DEFAULT 'PERCENTAGE',  -- HOURLY, PERCENTAGE, FLAT
            pay_rate REAL,  -- Hourly rate or percentage

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP,

            FOREIGN KEY (location_id) REFERENCES locations(id)
        )
        """)

        print("[OK] Created technicians table")

        # ====================================================================
        # INSURANCE CLAIMS (The pain point!)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Claim Info
            claim_number TEXT UNIQUE NOT NULL,
            insurance_company TEXT NOT NULL,
            policy_number TEXT,

            -- Adjuster (The person who never responds!)
            adjuster_name TEXT,
            adjuster_email TEXT,
            adjuster_phone TEXT,
            adjuster_extension TEXT,

            -- Status
            status TEXT DEFAULT 'SUBMITTED',
            -- SUBMITTED -> PENDING_ADJUSTER -> ADJUSTER_SCHEDULED ->
            -- INSPECTED -> WAITING_APPROVAL -> APPROVED -> SUPPLEMENT_NEEDED ->
            -- SUPPLEMENT_APPROVED -> PAID -> CLOSED

            -- Important Dates
            claim_date DATE,
            submitted_date DATE,
            adjuster_scheduled_date TIMESTAMP,
            adjuster_inspection_date DATE,
            approval_date DATE,
            payment_received_date DATE,

            -- Follow-up Tracking (CRITICAL!)
            last_contact_date DATE,
            last_contact_method TEXT,  -- EMAIL, PHONE, PORTAL
            next_follow_up_date DATE,
            follow_up_count INTEGER DEFAULT 0,
            auto_follow_up_enabled INTEGER DEFAULT 1,  -- Auto-email adjuster
            days_since_last_response INTEGER,  -- Calculated

            -- Financial
            claimed_amount REAL,
            approved_amount REAL,
            supplement_amount REAL,
            deductible REAL,
            payment_received REAL,

            -- Documents
            estimate_sent INTEGER DEFAULT 0,
            supplement_sent INTEGER DEFAULT 0,

            -- Notes
            notes TEXT,
            adjuster_notes TEXT,  -- Track what they said

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
        """)

        print("[OK] Created insurance_claims table (adjuster tracking!)")

        # ====================================================================
        # JOBS (The core of the system!)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT UNIQUE NOT NULL,  -- JOB-2024-0001

            -- Relationships
            customer_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            location_id INTEGER,

            -- Job Type
            job_type TEXT DEFAULT 'PDR',  -- PDR, HAIL, CONVENTIONAL, DETAIL
            damage_type TEXT,  -- HAIL, DOOR_DING, DENT, COLLISION

            -- Current Status (THE CRITICAL WORKFLOW!)
            status TEXT DEFAULT 'NEW',
            -- Status workflow:
            -- NEW -> WAITING_DROP_OFF -> DROPPED_OFF -> WAITING_WRITEUP ->
            -- ESTIMATE_CREATED -> WAITING_INSURANCE -> WAITING_ADJUSTER ->
            -- ADJUSTER_SCHEDULED -> ADJUSTER_INSPECTED -> WAITING_APPROVAL ->
            -- APPROVED -> WAITING_PARTS -> PARTS_ORDERED -> PARTS_RECEIVED ->
            -- ASSIGNED_TO_TECH -> IN_PROGRESS -> TECH_COMPLETE ->
            -- WAITING_QC -> QC_COMPLETE -> WAITING_DETAIL -> DETAIL_COMPLETE ->
            -- READY_FOR_PICKUP -> COMPLETED -> INVOICED -> PAID

            status_changed_at TIMESTAMP,
            status_changed_by TEXT,

            -- Scheduling
            scheduled_drop_off TIMESTAMP,
            actual_drop_off TIMESTAMP,
            scheduled_pickup TIMESTAMP,
            actual_pickup TIMESTAMP,

            -- Assignment
            assigned_tech_id INTEGER,
            assigned_at TIMESTAMP,

            -- Tech Estimates
            estimated_hours REAL,
            estimated_completion_date DATE,
            tech_notes TEXT,  -- "Front hood: 2hrs, Roof: 4hrs, Trunk: 1hr"
            tech_daily_update TEXT,  -- "Finished hood, starting roof tomorrow"
            last_tech_update TIMESTAMP,

            -- Insurance
            insurance_claim_id INTEGER,

            -- Parts
            parts_needed TEXT,  -- JSON array of parts
            parts_status TEXT,  -- NOT_NEEDED, NEEDED, ORDERED, PARTIAL, RECEIVED

            -- Financial
            estimate_id INTEGER,
            invoice_id INTEGER,
            total_estimate REAL,
            total_actual REAL,

            -- Priority
            priority TEXT DEFAULT 'NORMAL',  -- URGENT, HIGH, NORMAL, LOW

            -- Notes
            internal_notes TEXT,
            customer_notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            deleted_at TIMESTAMP,

            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY (location_id) REFERENCES locations(id),
            FOREIGN KEY (assigned_tech_id) REFERENCES technicians(id),
            FOREIGN KEY (insurance_claim_id) REFERENCES insurance_claims(id)
        )
        """)

        print("[OK] Created jobs table (core workflow engine)")

        # ====================================================================
        # JOB STATUS HISTORY (Audit trail)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,

            from_status TEXT,
            to_status TEXT NOT NULL,

            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,

            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
        """)

        print("[OK] Created job_status_history table")

        # ====================================================================
        # EMAIL TRACKING (Track EVERY email with adjusters)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Relationships
            insurance_claim_id INTEGER NOT NULL,
            job_id INTEGER,

            -- Email Details
            direction TEXT NOT NULL,  -- SENT, RECEIVED
            from_address TEXT,
            to_address TEXT,
            cc_addresses TEXT,
            subject TEXT,
            body TEXT,

            -- Parsing
            contains_approval INTEGER DEFAULT 0,
            contains_denial INTEGER DEFAULT 0,
            contains_question INTEGER DEFAULT 0,
            sentiment TEXT,  -- POSITIVE, NEUTRAL, NEGATIVE

            -- Status
            response_received INTEGER DEFAULT 0,
            response_to_email_id INTEGER,  -- Links to email this responds to

            -- Follow-up
            requires_response INTEGER DEFAULT 0,
            response_deadline DATE,

            -- Metadata
            sent_at TIMESTAMP,
            received_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (insurance_claim_id) REFERENCES insurance_claims(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (response_to_email_id) REFERENCES email_tracking(id)
        )
        """)

        print("[OK] Created email_tracking table (never lose an email!)")

        # ====================================================================
        # PARTS
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Part Info
            part_number TEXT,
            description TEXT NOT NULL,
            category TEXT,  -- BODY_PANEL, TRIM, HARDWARE, PAINT, SUPPLIES

            -- Supplier
            preferred_supplier TEXT,
            supplier_part_number TEXT,

            -- Pricing
            cost REAL,
            retail_price REAL,

            -- Stock
            in_stock INTEGER DEFAULT 0,
            reorder_level INTEGER,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        )
        """)

        print("[OK] Created parts table")

        # ====================================================================
        # PART ORDERS (Local sourcing)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS part_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Order Info
            order_number TEXT UNIQUE,
            job_id INTEGER,

            -- Supplier
            supplier_name TEXT NOT NULL,
            supplier_email TEXT,
            supplier_phone TEXT,

            -- Status
            status TEXT DEFAULT 'QUOTED',
            -- QUOTED -> ORDERED -> SHIPPED -> RECEIVED -> RETURNED

            -- Dates
            quote_requested_date DATE,
            quote_received_date DATE,
            ordered_date DATE,
            expected_delivery_date DATE,
            actual_delivery_date DATE,

            -- Financial
            quote_amount REAL,
            actual_amount REAL,
            return_cost REAL,  -- Core charge or restocking fee

            -- Parts
            parts_json TEXT,  -- JSON array of parts with quantities

            -- Notes
            notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
        """)

        print("[OK] Created part_orders table (local sourcing)")

        # ====================================================================
        # PART ORDER QUOTES (Email local shops for prices)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS part_quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            part_order_id INTEGER NOT NULL,
            supplier_name TEXT NOT NULL,

            -- Quote
            quoted_price REAL,
            quoted_delivery_days INTEGER,
            return_policy TEXT,
            core_charge REAL,

            -- Status
            selected INTEGER DEFAULT 0,

            -- Response
            quote_received_at TIMESTAMP,
            quote_expires_at DATE,

            FOREIGN KEY (part_order_id) REFERENCES part_orders(id)
        )
        """)

        print("[OK] Created part_quotes table")

        # ====================================================================
        # ESTIMATES
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_number TEXT UNIQUE NOT NULL,

            job_id INTEGER NOT NULL,

            -- Status
            status TEXT DEFAULT 'DRAFT',  -- DRAFT, SENT, VIEWED, APPROVED, DECLINED

            -- Pricing
            labor_hours REAL,
            labor_rate REAL,
            labor_total REAL,
            parts_total REAL,
            subtotal REAL,
            tax_rate REAL DEFAULT 0.0,
            tax_amount REAL,
            total REAL NOT NULL,

            -- Line Items (stored as JSON)
            line_items TEXT,  -- JSON array

            -- Dates
            created_date DATE,
            sent_date DATE,
            viewed_date DATE,
            approved_date DATE,
            expires_date DATE,

            -- Notes
            notes TEXT,
            terms TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,

            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
        """)

        print("[OK] Created estimates table")

        # ====================================================================
        # INVOICES
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE NOT NULL,

            job_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,

            -- Status
            status TEXT DEFAULT 'DRAFT',  -- DRAFT, SENT, VIEWED, PARTIAL_PAID, PAID, OVERDUE

            -- Pricing
            subtotal REAL,
            tax_amount REAL,
            total REAL NOT NULL,
            amount_paid REAL DEFAULT 0,
            balance_due REAL,

            -- Line Items
            line_items TEXT,  -- JSON

            -- Dates
            invoice_date DATE NOT NULL,
            due_date DATE,
            sent_date DATE,
            paid_date DATE,

            -- Payment
            payment_method TEXT,  -- CHECK, CASH, CARD, INSURANCE
            payment_reference TEXT,  -- Check number, transaction ID

            -- Notes
            notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
        """)

        print("[OK] Created invoices table")

        # ====================================================================
        # PAYMENTS & REVENUE BREAKDOWN
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            invoice_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,

            -- Payment Info
            amount REAL NOT NULL,
            payment_method TEXT,  -- CHECK, CASH, CARD, INSURANCE, ACH
            payment_reference TEXT,
            payment_date DATE NOT NULL,

            -- Source
            payer_type TEXT,  -- CUSTOMER, INSURANCE, DEALERSHIP
            payer_name TEXT,

            -- Revenue Breakdown (YOUR REQUEST!)
            total_amount REAL NOT NULL,
            insurance_portion REAL DEFAULT 0,
            parts_cost REAL DEFAULT 0,
            sales_team_cut REAL DEFAULT 0,
            tech_cut REAL DEFAULT 0,
            office_cut REAL DEFAULT 0,
            shop_profit REAL DEFAULT 0,

            -- Breakdown percentages (for transparency)
            sales_percentage REAL,
            tech_percentage REAL,
            office_percentage REAL,

            -- Status
            status TEXT DEFAULT 'RECEIVED',  -- RECEIVED, DEPOSITED, CLEARED, BOUNCED
            cleared_date DATE,

            -- Notes
            notes TEXT,

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,

            FOREIGN KEY (invoice_id) REFERENCES invoices(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
        """)

        print("[OK] Created payments table (revenue breakdown!)")

        # ====================================================================
        # COMMUNICATIONS LOG
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS communications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Relationships
            customer_id INTEGER,
            lead_id INTEGER,
            job_id INTEGER,
            insurance_claim_id INTEGER,

            -- Communication Details
            type TEXT NOT NULL,  -- EMAIL, SMS, PHONE, IN_PERSON, PORTAL
            direction TEXT NOT NULL,  -- INBOUND, OUTBOUND

            subject TEXT,
            message TEXT,

            -- Participants
            from_person TEXT,
            to_person TEXT,

            -- Status
            status TEXT DEFAULT 'COMPLETED',  -- SCHEDULED, COMPLETED, FAILED

            -- Outcome
            outcome TEXT,  -- SUCCESSFUL, NO_ANSWER, VOICEMAIL, BOUNCED
            follow_up_required INTEGER DEFAULT 0,
            follow_up_date DATE,

            -- Metadata
            occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,

            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (lead_id) REFERENCES leads(id),
            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (insurance_claim_id) REFERENCES insurance_claims(id)
        )
        """)

        print("[OK] Created communications table")

        # ====================================================================
        # DOCUMENTS (Photos, PDFs, claim docs)
        # ====================================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Relationships
            job_id INTEGER,
            customer_id INTEGER,
            vehicle_id INTEGER,
            insurance_claim_id INTEGER,

            -- Document Info
            document_type TEXT NOT NULL,
            -- PHOTO_BEFORE, PHOTO_AFTER, PHOTO_PROGRESS, ESTIMATE_PDF,
            -- INVOICE_PDF, INSURANCE_DOCS, SUPPLEMENT, CONTRACT

            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            mime_type TEXT,

            -- Photo metadata (if applicable)
            photo_location TEXT,  -- "FRONT_HOOD", "ROOF", "DRIVER_DOOR"
            photo_angle TEXT,  -- "STRAIGHT", "45_DEGREE", "DETAIL"

            -- Status
            status TEXT DEFAULT 'ACTIVE',

            -- Notes
            description TEXT,
            tags TEXT,  -- JSON array

            -- Metadata
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by TEXT,
            deleted_at TIMESTAMP,

            FOREIGN KEY (job_id) REFERENCES jobs(id),
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY (insurance_claim_id) REFERENCES insurance_claims(id)
        )
        """)

        print("[OK] Created documents table")

        # ====================================================================
        # INDEXES FOR PERFORMANCE
        # ====================================================================

        print("\nCreating indexes for performance...")

        # Customer indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_customers_status ON customers(status)")

        # Vehicle indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_customer ON vehicles(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_vehicles_vin ON vehicles(vin)")

        # Job indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_customer ON jobs(customer_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_tech ON jobs(assigned_tech_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_scheduled ON jobs(scheduled_drop_off)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_number ON jobs(job_number)")

        # Insurance claim indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_number ON insurance_claims(claim_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_status ON insurance_claims(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_follow_up ON insurance_claims(next_follow_up_date)")

        # Email tracking indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_claim ON email_tracking(insurance_claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_direction ON email_tracking(direction)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_response ON email_tracking(requires_response)")

        # Lead indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_hail_event ON leads(hail_event_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_follow_up ON leads(next_follow_up_date)")

        print("[OK] Created performance indexes")

        conn.commit()
        conn.close()

        print("\n" + "="*80)
        print("DATABASE SCHEMA CREATED SUCCESSFULLY")
        print("="*80 + "\n")

        print("Your enterprise PDR CRM database is ready!")
        print()
        print("Tables created:")
        print("  - customers (complete profiles)")
        print("  - vehicles (linked to customers)")
        print("  - leads (from hail events + other sources)")
        print("  - jobs (25+ status workflow)")
        print("  - job_status_history (audit trail)")
        print("  - technicians (assignment + performance)")
        print("  - insurance_claims (adjuster tracking!)")
        print("  - email_tracking (never lose correspondence)")
        print("  - parts + part_orders + part_quotes")
        print("  - estimates + invoices + payments")
        print("  - communications (all contact logged)")
        print("  - documents (photos, PDFs, claims)")
        print("  - hail_events (swath system integration)")
        print("  - locations (multi-shop support)")
        print()

        return True

    @staticmethod
    def get_job_statuses() -> List[str]:
        """Return all valid job statuses in workflow order"""
        return [
            'NEW',
            'WAITING_DROP_OFF',
            'DROPPED_OFF',
            'WAITING_WRITEUP',
            'ESTIMATE_CREATED',
            'WAITING_INSURANCE',
            'WAITING_ADJUSTER',
            'ADJUSTER_SCHEDULED',
            'ADJUSTER_INSPECTED',
            'WAITING_APPROVAL',
            'APPROVED',
            'WAITING_PARTS',
            'PARTS_ORDERED',
            'PARTS_RECEIVED',
            'ASSIGNED_TO_TECH',
            'IN_PROGRESS',
            'TECH_COMPLETE',
            'WAITING_QC',
            'QC_COMPLETE',
            'WAITING_DETAIL',
            'DETAIL_COMPLETE',
            'READY_FOR_PICKUP',
            'COMPLETED',
            'INVOICED',
            'PAID'
        ]

    @staticmethod
    def get_insurance_claim_statuses() -> List[str]:
        """Return all valid insurance claim statuses"""
        return [
            'SUBMITTED',
            'PENDING_ADJUSTER',
            'ADJUSTER_SCHEDULED',
            'INSPECTED',
            'WAITING_APPROVAL',
            'APPROVED',
            'SUPPLEMENT_NEEDED',
            'SUPPLEMENT_APPROVED',
            'PAID',
            'CLOSED'
        ]
