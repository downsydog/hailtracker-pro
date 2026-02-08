"""
PDR Pro Estimating System Schema
Industry-leading PDR-specific estimating with R/I labor, parts, insurance battle tools,
smart alerts, photo markup, and historical comparables.

FEATURES:
- R/I operations catalog with vehicle-specific times
- Panel → R/I auto-associations
- Parts catalog with vehicle-specific lookup
- Insurance company and adjuster tracking
- Adjuster interaction history and pushback justifications
- Historical comparables for negotiation support
- Photo markup and checklist system
- Smart alerts for missing items and consistency
- Supplement tracking and approval workflows
"""

import sqlite3
import os
from datetime import datetime


class EstimatingSchema:
    """Create and manage PDR Pro Estimating schema"""

    @staticmethod
    def create_all_tables(db_path: str = "data/pdr_crm.db"):
        """
        Create complete estimating schema tables.

        This adds industry-leading PDR estimating capabilities:
        - R/I operations with vehicle-specific labor times
        - Insurance battle tracking and justifications
        - Historical comparables for negotiation
        - Smart alerts for missing items
        - Photo documentation with markup
        """

        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("\n" + "=" * 70)
        print("PDR PRO ESTIMATING SYSTEM - SCHEMA CREATION")
        print("=" * 70 + "\n")

        # ==================================================================
        # PART 1: R/I OPERATIONS SYSTEM
        # ==================================================================

        print("Creating R/I Operations System...")

        # R/I Operations Catalog
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ri_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE,
            operation_type TEXT DEFAULT 'remove_install',
            category TEXT,
            default_hours REAL,
            default_labor_type TEXT DEFAULT 'body',
            notes TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created ri_operations table (R/I catalog)")

        # Panel → R/I Associations (auto-suggest logic)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS panel_ri_associations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_name TEXT NOT NULL,
            ri_operation_id INTEGER NOT NULL,
            is_default_selected BOOLEAN DEFAULT 1,
            min_dent_count INTEGER DEFAULT 0,
            access_trigger TEXT,
            condition_notes TEXT,
            vehicle_condition TEXT,
            priority INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ri_operation_id) REFERENCES ri_operations(id)
        )
        """)
        print("[OK] Created panel_ri_associations table (auto-suggest rules)")

        # Vehicle-Specific R/I Times (THE MONEY TABLE)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ri_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ri_operation_id INTEGER NOT NULL,
            year_start INTEGER,
            year_end INTEGER,
            make TEXT,
            model TEXT,
            body_style TEXT,
            trim_pattern TEXT,
            labor_hours REAL NOT NULL,
            labor_type TEXT DEFAULT 'body',
            source TEXT,
            confidence_score INTEGER DEFAULT 50,
            sample_count INTEGER DEFAULT 1,
            last_updated TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (ri_operation_id) REFERENCES ri_operations(id)
        )
        """)
        print("[OK] Created ri_times table (vehicle-specific labor times)")

        # Crowdsourced Time Corrections
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ri_time_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ri_time_id INTEGER,
            estimate_id INTEGER,
            ri_operation_id INTEGER NOT NULL,
            vehicle_year INTEGER,
            vehicle_make TEXT,
            vehicle_model TEXT,
            vehicle_body_style TEXT,
            suggested_hours REAL,
            actual_hours REAL NOT NULL,
            technician_id INTEGER,
            approved BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ri_time_id) REFERENCES ri_times(id),
            FOREIGN KEY (estimate_id) REFERENCES estimates(id)
        )
        """)
        print("[OK] Created ri_time_submissions table (crowdsourced corrections)")

        # Labor Rates (configurable per company)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS labor_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER DEFAULT 1,
            rate_type TEXT NOT NULL,
            hourly_rate REAL NOT NULL,
            effective_date DATE,
            is_active BOOLEAN DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created labor_rates table")

        # ==================================================================
        # PART 2: PARTS SYSTEM
        # ==================================================================

        print("\nCreating Parts System...")

        # Parts Catalog
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parts_catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            part_name TEXT NOT NULL,
            part_category TEXT,
            year_start INTEGER,
            year_end INTEGER,
            make TEXT,
            model TEXT,
            position TEXT,
            panel_name TEXT,
            oem_part_number TEXT,
            aftermarket_part_number TEXT,
            oem_price REAL,
            aftermarket_price REAL,
            labor_hours REAL,
            source TEXT,
            last_updated TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created parts_catalog table")

        # Panel → Parts Associations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS panel_parts_associations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_name TEXT NOT NULL,
            part_category TEXT,
            part_description TEXT,
            check_condition TEXT,
            is_default_selected BOOLEAN DEFAULT 0,
            priority INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created panel_parts_associations table")

        # ==================================================================
        # PART 3: VEHICLE DECODING
        # ==================================================================

        print("\nCreating Vehicle Decoding System...")

        # Cached VIN Decodes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS decoded_vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vin TEXT UNIQUE NOT NULL,
            year INTEGER,
            make TEXT,
            model TEXT,
            trim TEXT,
            body_style TEXT,
            doors INTEGER,
            drive_type TEXT,
            engine TEXT,
            has_sunroof BOOLEAN,
            has_roof_rails BOOLEAN,
            has_antenna_shark_fin BOOLEAN,
            paint_code TEXT,
            raw_nhtsa_response TEXT,
            decoded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created decoded_vehicles table (VIN cache)")

        # ==================================================================
        # PART 4: ESTIMATE R/I AND PARTS LINE ITEMS
        # ==================================================================

        print("\nCreating Estimate Line Item Tables...")

        # R/I Items on Estimate
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_ri_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            ri_operation_id INTEGER NOT NULL,
            panel_name TEXT,
            labor_hours REAL NOT NULL,
            labor_rate REAL NOT NULL,
            labor_type TEXT,
            line_total REAL NOT NULL,
            auto_suggested BOOLEAN DEFAULT 0,
            was_modified BOOLEAN DEFAULT 0,
            source_ri_time_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (ri_operation_id) REFERENCES ri_operations(id)
        )
        """)
        print("[OK] Created estimate_ri_items table")

        # Parts on Estimate
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            panel_name TEXT,
            part_name TEXT NOT NULL,
            part_number TEXT,
            part_type TEXT DEFAULT 'aftermarket',
            quantity INTEGER DEFAULT 1,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            auto_suggested BOOLEAN DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id)
        )
        """)
        print("[OK] Created estimate_parts table")

        # ==================================================================
        # PART 5: INSURANCE BATTLE SYSTEM
        # ==================================================================

        print("\nCreating Insurance Battle System...")

        # Insurance Companies
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE,

            -- Agreed rates
            body_rate REAL,
            paint_rate REAL,
            pdr_rate REAL,
            mechanical_rate REAL,

            -- Preferences and tendencies
            preferred_estimate_format TEXT,
            typical_review_days INTEGER,
            supplement_friendly BOOLEAN DEFAULT 1,

            -- Known pushback items (JSON array)
            common_pushback_items TEXT,

            -- Contact
            claims_phone TEXT,
            claims_email TEXT,
            claims_portal_url TEXT,

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
        """)
        print("[OK] Created insurance_companies table")

        # Insurance Adjusters
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS insurance_adjusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insurance_company_id INTEGER,
            name TEXT NOT NULL,
            employee_id TEXT,

            -- Contact info
            phone TEXT,
            email TEXT,
            territory TEXT,

            -- Work style
            is_field_adjuster BOOLEAN DEFAULT 0,
            is_ia BOOLEAN DEFAULT 0,
            response_speed TEXT,
            difficulty_rating INTEGER,

            -- Stats (auto-calculated)
            total_claims_handled INTEGER DEFAULT 0,
            average_approval_rate REAL,
            average_supplement_rounds REAL,
            average_days_to_approval REAL,

            notes TEXT,
            last_interaction_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            FOREIGN KEY (insurance_company_id) REFERENCES insurance_companies(id)
        )
        """)
        print("[OK] Created insurance_adjusters table")

        # Adjuster Interactions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS adjuster_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER,
            job_id INTEGER,
            adjuster_id INTEGER,
            insurance_company_id INTEGER,

            interaction_type TEXT,
            interaction_date DATE,

            -- What happened
            items_approved TEXT,
            items_denied TEXT,
            items_reduced TEXT,
            amount_requested REAL,
            amount_approved REAL,

            -- Supplement tracking
            supplement_number INTEGER DEFAULT 0,

            outcome TEXT,
            notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (adjuster_id) REFERENCES insurance_adjusters(id),
            FOREIGN KEY (insurance_company_id) REFERENCES insurance_companies(id)
        )
        """)
        print("[OK] Created adjuster_interactions table")

        # Pushback Justifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pushback_justifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            trigger_item TEXT,
            insurance_company_id INTEGER,

            title TEXT,
            justification_text TEXT NOT NULL,

            -- Supporting evidence
            oem_reference TEXT,
            mitchell_reference TEXT,
            labor_time_source TEXT,

            success_rate REAL,
            times_used INTEGER DEFAULT 0,
            times_successful INTEGER DEFAULT 0,

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (insurance_company_id) REFERENCES insurance_companies(id)
        )
        """)
        print("[OK] Created pushback_justifications table")

        # Estimate Supplements
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_supplements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_estimate_id INTEGER NOT NULL,
            supplement_number INTEGER NOT NULL,
            supplement_estimate_id INTEGER,

            reason TEXT,

            -- What changed
            panels_added TEXT,
            ri_items_added TEXT,
            parts_added TEXT,

            amount_added REAL,
            amount_approved REAL,

            status TEXT DEFAULT 'draft',
            submitted_date DATE,
            response_date DATE,

            adjuster_id INTEGER,
            adjuster_notes TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (original_estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (adjuster_id) REFERENCES insurance_adjusters(id)
        )
        """)
        print("[OK] Created estimate_supplements table")

        # ==================================================================
        # PART 6: HISTORICAL COMPARABLES
        # ==================================================================

        print("\nCreating Historical Comparables System...")

        # Estimate Comparables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_comparables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            job_id INTEGER,

            -- Vehicle info (denormalized for fast queries)
            vehicle_year INTEGER,
            vehicle_make TEXT,
            vehicle_model TEXT,
            vehicle_body_style TEXT,

            -- Damage summary
            total_panels_damaged INTEGER,
            total_dent_count INTEGER,
            damage_severity TEXT,

            -- Totals
            pdr_labor_total REAL,
            ri_labor_total REAL,
            parts_total REAL,
            estimate_total REAL,

            -- What was actually approved
            approved_total REAL,
            approval_percentage REAL,

            -- Insurance info
            insurance_company_id INTEGER,
            adjuster_id INTEGER,

            -- Timestamps
            estimate_date DATE,
            approval_date DATE,

            -- JSON snapshots for detailed comparison
            panel_breakdown TEXT,
            ri_breakdown TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (insurance_company_id) REFERENCES insurance_companies(id)
        )
        """)
        print("[OK] Created estimate_comparables table")

        # Create indexes for fast comparable lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comparables_vehicle ON estimate_comparables(vehicle_year, vehicle_make, vehicle_model)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comparables_insurance ON estimate_comparables(insurance_company_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comparables_severity ON estimate_comparables(damage_severity)")
        print("[OK] Created comparable lookup indexes")

        # ==================================================================
        # PART 7: PHOTO MARKUP SYSTEM
        # ==================================================================

        print("\nCreating Photo Documentation System...")

        # Estimate Photos with Markup
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            panel_name TEXT,
            photo_type TEXT DEFAULT 'damage',

            -- File paths
            original_path TEXT NOT NULL,
            thumbnail_path TEXT,
            marked_up_path TEXT,

            -- Markup/annotation data (JSON)
            markup_data TEXT,

            -- Auto-extracted info
            dent_count_in_photo INTEGER,
            price_shown REAL,

            -- Metadata
            taken_at TIMESTAMP,
            latitude REAL,
            longitude REAL,
            device_info TEXT,

            -- Quality flags
            quality_score INTEGER,
            quality_issues TEXT,

            sort_order INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id)
        )
        """)
        print("[OK] Created estimate_photos table")

        # Photo Checklist Templates
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS photo_checklists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            required_photos TEXT,
            is_default BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created photo_checklists table")

        # Estimate Photo Checklist Tracking
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_photo_checklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            checklist_id INTEGER NOT NULL,
            completion_status TEXT,
            completed_count INTEGER DEFAULT 0,
            required_count INTEGER,
            is_complete BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (checklist_id) REFERENCES photo_checklists(id)
        )
        """)
        print("[OK] Created estimate_photo_checklist table")

        # ==================================================================
        # PART 8: SMART ALERTS SYSTEM
        # ==================================================================

        print("\nCreating Smart Alerts System...")

        # Alert Rules Configuration
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            trigger_conditions TEXT NOT NULL,
            alert_type TEXT,
            severity TEXT DEFAULT 'warning',
            alert_message TEXT NOT NULL,
            suggested_action TEXT,
            auto_add_item_type TEXT,
            auto_add_item_id INTEGER,
            is_active BOOLEAN DEFAULT 1,
            priority INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        print("[OK] Created estimate_alert_rules table")

        # Alerts Generated for Estimates
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            alert_rule_id INTEGER,
            alert_type TEXT NOT NULL,
            severity TEXT,
            message TEXT NOT NULL,
            trigger_panel TEXT,
            trigger_data TEXT,
            status TEXT DEFAULT 'active',
            resolved_action TEXT,
            resolved_by INTEGER,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id),
            FOREIGN KEY (alert_rule_id) REFERENCES estimate_alert_rules(id)
        )
        """)
        print("[OK] Created estimate_alerts table")

        # Estimate Consistency Checks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estimate_consistency_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estimate_id INTEGER NOT NULL,
            comparable_count INTEGER,
            average_comparable_total REAL,
            this_estimate_total REAL,
            variance_percentage REAL,
            is_significantly_low BOOLEAN,
            is_significantly_high BOOLEAN,
            details TEXT,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (estimate_id) REFERENCES estimates(id)
        )
        """)
        print("[OK] Created estimate_consistency_checks table")

        # ==================================================================
        # PART 9: ADDITIONAL INDEXES
        # ==================================================================

        print("\nCreating Indexes...")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ri_times_vehicle ON ri_times(make, model, year_start, year_end)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ri_times_operation ON ri_times(ri_operation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_panel_ri_panel ON panel_ri_associations(panel_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estimate_ri_items_estimate ON estimate_ri_items(estimate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estimate_parts_estimate ON estimate_parts(estimate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estimate_photos_estimate ON estimate_photos(estimate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_estimate_alerts_estimate ON estimate_alerts(estimate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_adjuster_interactions_estimate ON adjuster_interactions(estimate_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decoded_vehicles_vin ON decoded_vehicles(vin)")

        print("[OK] Created all indexes")

        conn.commit()
        conn.close()

        print("\n" + "=" * 70)
        print("PDR PRO ESTIMATING SCHEMA CREATED SUCCESSFULLY")
        print("=" * 70 + "\n")

        return True

    @staticmethod
    def add_estimate_insurance_fields(db_path: str = "data/pdr_crm.db"):
        """Add insurance-related fields to existing estimates table"""

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if fields already exist
        cursor.execute("PRAGMA table_info(estimates)")
        existing_columns = [col[1] for col in cursor.fetchall()]

        new_columns = [
            ("insurance_company_id", "INTEGER"),
            ("adjuster_id", "INTEGER"),
            ("claim_number", "TEXT"),
            ("date_of_loss", "DATE"),
            ("pdr_labor_total", "REAL DEFAULT 0"),
            ("ri_labor_total", "REAL DEFAULT 0"),
            ("conventional_labor_total", "REAL DEFAULT 0"),
            ("paint_labor_total", "REAL DEFAULT 0"),
            ("materials_total", "REAL DEFAULT 0"),
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE estimates ADD COLUMN {col_name} {col_type}")
                    print(f"[OK] Added column: estimates.{col_name}")
                except sqlite3.OperationalError:
                    pass

        conn.commit()
        conn.close()


# Standalone execution
if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/pdr_crm.db"

    print(f"Creating estimating schema in: {db_path}")
    EstimatingSchema.create_all_tables(db_path)
    EstimatingSchema.add_estimate_insurance_fields(db_path)
    print("Done!")
