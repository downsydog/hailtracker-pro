"""
PDR CRM - Onboarding Schema
Database tables for customer onboarding, portal access, and referral system

This module creates all tables required for:
- Field enrollment workflow
- Customer portal access
- Job status tracking
- Referral tracking and commissions
- Digital flyer management
- Customer communications
"""

from typing import Optional


class OnboardingSchema:
    """
    Database schema for customer onboarding and referral system

    Creates all required tables for the complete onboarding workflow
    """

    @staticmethod
    def create_onboarding_tables(db) -> None:
        """
        Create all onboarding-related database tables

        Args:
            db: Database instance with execute() method
        """

        # ====================================================================
        # ENROLLMENT TABLES
        # ====================================================================

        # Enrollment sessions - tracks field enrollment workflow
        db.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment_id TEXT UNIQUE NOT NULL,
                salesperson_id INTEGER,
                customer_id INTEGER,
                location_lat REAL,
                location_lon REAL,
                vehicle_scan_type TEXT,
                vehicle_scan_data TEXT,
                started_at TEXT,
                completed_at TEXT,
                status TEXT DEFAULT 'IN_PROGRESS',
                FOREIGN KEY (salesperson_id) REFERENCES technicians(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Enrollment photos - reference photos during enrollment
        db.execute("""
            CREATE TABLE IF NOT EXISTS enrollment_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment_id TEXT NOT NULL,
                photo_type TEXT NOT NULL,
                photo_url TEXT,
                captured_at TEXT,
                FOREIGN KEY (enrollment_id) REFERENCES enrollment_sessions(enrollment_id)
            )
        """)

        # ====================================================================
        # INSURANCE TABLES
        # ====================================================================

        # Customer insurance info
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_insurance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                company TEXT,
                policy_number TEXT,
                claim_number TEXT,
                deductible REAL,
                agent_name TEXT,
                agent_phone TEXT,
                enrollment_id TEXT,
                created_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (enrollment_id) REFERENCES enrollment_sessions(enrollment_id)
            )
        """)

        # ====================================================================
        # SIGNATURE TABLES
        # ====================================================================

        # Customer signatures - e-signatures for forms
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                enrollment_id TEXT,
                form_type TEXT NOT NULL,
                signature_data TEXT,
                signed_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (enrollment_id) REFERENCES enrollment_sessions(enrollment_id)
            )
        """)

        # ====================================================================
        # PORTAL ACCESS TABLES
        # ====================================================================

        # Customer portal credentials
        db.execute("""
            CREATE TABLE IF NOT EXISTS portal_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT,
                last_login TEXT,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Customer portal access tokens (for token-based auth)
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_portal_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                username TEXT,
                password_hash TEXT,
                access_token TEXT UNIQUE,
                created_at TEXT,
                last_login TEXT,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Customer portal login history
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_portal_logins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                login_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                status TEXT DEFAULT 'SUCCESS',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # ====================================================================
        # JOB STATUS TABLES
        # ====================================================================

        # Job status history index (table is created by schema.py)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_status_history_job
            ON job_status_history(job_id)
        """)

        # ====================================================================
        # REFERRAL TABLES
        # ====================================================================

        # Customer referrals
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_customer_id INTEGER NOT NULL,
                referred_customer_id INTEGER NOT NULL,
                enrollment_id TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'PENDING',
                status_notes TEXT,
                commission_amount REAL,
                commission_earned_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (referrer_customer_id) REFERENCES customers(id),
                FOREIGN KEY (referred_customer_id) REFERENCES customers(id),
                FOREIGN KEY (enrollment_id) REFERENCES enrollment_sessions(enrollment_id)
            )
        """)

        # Referral link clicks tracking
        db.execute("""
            CREATE TABLE IF NOT EXISTS referral_link_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_customer_id INTEGER NOT NULL,
                click_source TEXT,
                clicked_at TEXT,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (referrer_customer_id) REFERENCES customers(id)
            )
        """)

        # Referral commission payments
        db.execute("""
            CREATE TABLE IF NOT EXISTS referral_commission_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                referral_id INTEGER,
                amount REAL NOT NULL,
                payment_method TEXT,
                paid_at TEXT,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (referral_id) REFERENCES customer_referrals(id)
            )
        """)

        # ====================================================================
        # DIGITAL FLYER TABLES
        # ====================================================================

        # Digital flyers - company marketing templates
        db.execute("""
            CREATE TABLE IF NOT EXISTS digital_flyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flyer_name TEXT NOT NULL,
                flyer_html TEXT,
                flyer_image_url TEXT,
                flyer_type TEXT DEFAULT 'STANDARD',
                campaign_id INTEGER,
                created_at TEXT,
                updated_at TEXT,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Personalized flyers - customer-specific versions
        db.execute("""
            CREATE TABLE IF NOT EXISTS personalized_flyers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                flyer_id INTEGER NOT NULL,
                flyer_url TEXT UNIQUE,
                referral_link TEXT,
                generated_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (flyer_id) REFERENCES digital_flyers(id)
            )
        """)

        # Flyer views tracking
        db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                flyer_id INTEGER,
                personalized_flyer_id INTEGER,
                viewer_ip TEXT,
                user_agent TEXT,
                viewed_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (flyer_id) REFERENCES digital_flyers(id),
                FOREIGN KEY (personalized_flyer_id) REFERENCES personalized_flyers(id)
            )
        """)

        # Flyer campaigns
        db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_name TEXT NOT NULL,
                campaign_type TEXT,
                start_date TEXT,
                end_date TEXT,
                target_audience TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'DRAFT'
            )
        """)

        # A/B test variants
        db.execute("""
            CREATE TABLE IF NOT EXISTS flyer_ab_variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flyer_id INTEGER NOT NULL,
                variant_name TEXT,
                variant_html TEXT,
                variant_image_url TEXT,
                weight INTEGER DEFAULT 50,
                created_at TEXT,
                FOREIGN KEY (flyer_id) REFERENCES digital_flyers(id)
            )
        """)

        # ====================================================================
        # CUSTOMER DOCUMENTS & COMMUNICATIONS
        # ====================================================================

        # Customer documents
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                document_type TEXT NOT NULL,
                document_name TEXT,
                document_url TEXT,
                uploaded_at TEXT,
                uploaded_by INTEGER,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # Customer communications log
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_communications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                subject TEXT,
                message TEXT,
                sent_at TEXT,
                sent_by INTEGER,
                status TEXT DEFAULT 'SENT',
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # ====================================================================
        # NOTIFICATION TABLES
        # ====================================================================

        # Customer notification preferences
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL UNIQUE,
                email_enabled INTEGER DEFAULT 1,
                sms_enabled INTEGER DEFAULT 0,
                push_enabled INTEGER DEFAULT 0,
                in_app_enabled INTEGER DEFAULT 1,
                notify_on_statuses TEXT,
                quiet_hours_start TEXT,
                quiet_hours_end TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)

        # In-app notifications for customer portal
        db.execute("""
            CREATE TABLE IF NOT EXISTS customer_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                job_id INTEGER,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT DEFAULT 'UNREAD',
                priority TEXT DEFAULT 'NORMAL',
                created_at TEXT,
                read_at TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # ====================================================================
        # CREATE INDEXES
        # ====================================================================

        # Enrollment indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_enrollment_sessions_enrollment_id
            ON enrollment_sessions(enrollment_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_enrollment_sessions_customer_id
            ON enrollment_sessions(customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_enrollment_photos_enrollment_id
            ON enrollment_photos(enrollment_id)
        """)

        # Portal indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_portal_credentials_username
            ON portal_credentials(username)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_portal_logins_customer_id
            ON customer_portal_logins(customer_id)
        """)

        # Job status indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_status_history_job_id
            ON job_status_history(job_id)
        """)

        # Referral indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_referrals_referrer
            ON customer_referrals(referrer_customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_referrals_referred
            ON customer_referrals(referred_customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_referral_clicks_customer
            ON referral_link_clicks(referrer_customer_id)
        """)

        # Flyer indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_personalized_flyers_customer
            ON personalized_flyers(customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_flyer_views_customer
            ON flyer_views(customer_id)
        """)

        # Notification indexes
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_notifications_customer_id
            ON customer_notifications(customer_id)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_notifications_status
            ON customer_notifications(status)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_customer_notifications_created_at
            ON customer_notifications(created_at)
        """)

        print("[OK] Created onboarding schema tables")
        print("     - enrollment_sessions")
        print("     - enrollment_photos")
        print("     - customer_insurance")
        print("     - customer_signatures")
        print("     - portal_credentials")
        print("     - customer_portal_access")
        print("     - customer_portal_logins")
        print("     - customer_referrals")
        print("     - referral_link_clicks")
        print("     - referral_commission_payments")
        print("     - digital_flyers")
        print("     - personalized_flyers")
        print("     - flyer_views")
        print("     - flyer_campaigns")
        print("     - flyer_ab_variants")
        print("     - customer_documents")
        print("     - customer_communications")
        print("     - customer_notification_preferences")
        print("     - customer_notifications")
