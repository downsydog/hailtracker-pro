"""
PDR CRM - Scheduling Schema
Database tables for advanced scheduling, tech availability, and customer self-scheduling

This module creates all tables required for:
- Technician weekly schedules
- Time off / blocked time
- Scheduling settings per organization
- Self-scheduling tokens for customer links
"""


class SchedulingSchema:
    """
    Database schema for scheduling and self-scheduling features

    Creates all required tables for the complete scheduling system
    """

    @staticmethod
    def create_scheduling_tables(db) -> None:
        """
        Create all scheduling-related database tables

        Args:
            db: Database instance with execute() method
        """

        # ====================================================================
        # TECHNICIAN SCHEDULE TABLES
        # ====================================================================

        # Technician weekly availability / working hours
        db.execute("""
            CREATE TABLE IF NOT EXISTS technician_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                technician_id INTEGER NOT NULL,

                -- Day of week (0=Sunday, 1=Monday, ..., 6=Saturday)
                day_of_week INTEGER NOT NULL,

                -- Working hours
                start_time TEXT,  -- HH:MM format
                end_time TEXT,    -- HH:MM format

                -- Is tech available this day?
                is_available INTEGER DEFAULT 1,

                -- Max appointments this tech can handle per day (optional override)
                max_appointments INTEGER,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,

                UNIQUE(technician_id, day_of_week),
                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (technician_id) REFERENCES technicians(id)
            )
        """)

        # Time off / blocked time for technicians
        db.execute("""
            CREATE TABLE IF NOT EXISTS technician_time_off (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                technician_id INTEGER NOT NULL,

                -- Time off period
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,

                -- Optional: specific times (if null, entire day is blocked)
                start_time TEXT,
                end_time TEXT,

                -- Reason
                reason TEXT,  -- vacation, sick, training, personal, etc.

                -- Status
                status TEXT DEFAULT 'approved',  -- pending, approved, denied

                -- Metadata
                notes TEXT,
                approved_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,

                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (technician_id) REFERENCES technicians(id),
                FOREIGN KEY (approved_by) REFERENCES users(id)
            )
        """)

        # ====================================================================
        # SCHEDULING SETTINGS
        # ====================================================================

        # Organization scheduling settings (for self-scheduling)
        db.execute("""
            CREATE TABLE IF NOT EXISTS scheduling_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL UNIQUE,

                -- Business hours (JSON: {"monday": {"start": "08:00", "end": "17:00", "enabled": true}, ...})
                business_hours TEXT,

                -- Slot configuration
                default_slot_duration INTEGER DEFAULT 60,       -- minutes
                buffer_between_appointments INTEGER DEFAULT 15,  -- minutes
                max_appointments_per_day INTEGER DEFAULT 20,
                max_appointments_per_slot INTEGER DEFAULT 4,

                -- Self-scheduling rules
                allow_self_scheduling INTEGER DEFAULT 1,
                min_notice_hours INTEGER DEFAULT 24,   -- can't book less than 24h out
                max_advance_days INTEGER DEFAULT 30,   -- can't book more than 30 days out

                -- Appointment types allowed for self-scheduling
                allowed_appointment_types TEXT DEFAULT '["DROP_OFF", "ESTIMATE"]',  -- JSON array

                -- Confirmation settings
                require_confirmation INTEGER DEFAULT 1,
                auto_confirm INTEGER DEFAULT 0,

                -- Reminder settings
                send_24h_reminder INTEGER DEFAULT 1,
                send_2h_reminder INTEGER DEFAULT 1,
                reminder_sms INTEGER DEFAULT 1,
                reminder_email INTEGER DEFAULT 1,

                -- Custom messages
                confirmation_message TEXT,
                reminder_message TEXT,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT,

                FOREIGN KEY (organization_id) REFERENCES organizations(id)
            )
        """)

        # ====================================================================
        # SELF-SCHEDULING TOKENS
        # ====================================================================

        # Tokens for customer self-scheduling links
        db.execute("""
            CREATE TABLE IF NOT EXISTS scheduling_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,

                -- The token (URL-safe string)
                token TEXT UNIQUE NOT NULL,

                -- Scope: who can use this token?
                customer_id INTEGER,      -- if set, only this customer can use
                lead_id INTEGER,          -- if from a lead
                job_id INTEGER,           -- if for a specific job

                -- Constraints
                appointment_type TEXT,    -- limit to specific type (DROP_OFF, PICKUP, etc.)

                -- Validity
                expires_at TEXT,
                max_uses INTEGER DEFAULT 1,
                times_used INTEGER DEFAULT 0,

                -- Status
                is_active INTEGER DEFAULT 1,

                -- Metadata
                created_by INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,

                FOREIGN KEY (organization_id) REFERENCES organizations(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (lead_id) REFERENCES leads(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # ====================================================================
        # APPOINTMENT REMINDERS
        # ====================================================================

        # Track sent reminders
        db.execute("""
            CREATE TABLE IF NOT EXISTS appointment_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,

                -- Reminder type
                reminder_type TEXT NOT NULL,  -- 24h, 2h, confirmation

                -- Delivery method
                method TEXT NOT NULL,  -- sms, email, push

                -- Status
                status TEXT DEFAULT 'sent',  -- sent, delivered, failed
                sent_at TEXT,
                delivered_at TEXT,
                error_message TEXT,

                -- External reference (message ID from SMS/email provider)
                external_id TEXT,

                FOREIGN KEY (appointment_id) REFERENCES appointments(id)
            )
        """)

        # ====================================================================
        # INDEXES
        # ====================================================================

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tech_schedules_tech
            ON technician_schedules(technician_id, day_of_week)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tech_time_off_dates
            ON technician_time_off(technician_id, start_date, end_date)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduling_tokens_token
            ON scheduling_tokens(token)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduling_tokens_customer
            ON scheduling_tokens(customer_id)
        """)

        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointment_reminders
            ON appointment_reminders(appointment_id, reminder_type)
        """)

        print("[OK] Scheduling tables created successfully")

    @staticmethod
    def create_default_settings(db, organization_id: int) -> None:
        """
        Create default scheduling settings for an organization

        Args:
            db: Database instance
            organization_id: Organization to create settings for
        """
        import json

        # Default business hours
        default_hours = {
            "sunday": {"start": "00:00", "end": "00:00", "enabled": False},
            "monday": {"start": "08:00", "end": "17:00", "enabled": True},
            "tuesday": {"start": "08:00", "end": "17:00", "enabled": True},
            "wednesday": {"start": "08:00", "end": "17:00", "enabled": True},
            "thursday": {"start": "08:00", "end": "17:00", "enabled": True},
            "friday": {"start": "08:00", "end": "17:00", "enabled": True},
            "saturday": {"start": "08:00", "end": "14:00", "enabled": True},
        }

        db.execute("""
            INSERT OR IGNORE INTO scheduling_settings (organization_id, business_hours)
            VALUES (?, ?)
        """, (organization_id, json.dumps(default_hours)))

    @staticmethod
    def create_default_tech_schedule(db, organization_id: int, technician_id: int) -> None:
        """
        Create default weekly schedule for a technician (Mon-Fri 8-5, Sat 8-2)

        Args:
            db: Database instance
            organization_id: Organization ID
            technician_id: Technician to create schedule for
        """
        default_schedule = [
            (0, False, None, None),         # Sunday - off
            (1, True, "08:00", "17:00"),    # Monday
            (2, True, "08:00", "17:00"),    # Tuesday
            (3, True, "08:00", "17:00"),    # Wednesday
            (4, True, "08:00", "17:00"),    # Thursday
            (5, True, "08:00", "17:00"),    # Friday
            (6, True, "08:00", "14:00"),    # Saturday (half day)
        ]

        for day_of_week, is_available, start_time, end_time in default_schedule:
            db.execute("""
                INSERT OR IGNORE INTO technician_schedules
                (organization_id, technician_id, day_of_week, is_available, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (organization_id, technician_id, day_of_week, is_available, start_time, end_time))
