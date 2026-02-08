"""
PDR Pro Estimating - R/I (Remove & Install) Manager
Manages R/I operations, vehicle-specific times, auto-suggestions, and estimate integration.

FEATURES:
- R/I operations catalog with 60+ operations
- Vehicle-specific labor times (fallback chain)
- Panel → R/I auto-suggestions based on damage
- Crowdsourced time corrections
- Labor rate lookups
"""

import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from src.crm.models.database import Database


class RIManager:
    """
    Manage R/I operations and labor time lookups.

    This is the core of professional PDR estimating - knowing
    what R/I items are needed and getting accurate times.
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize R/I manager"""
        self.db = Database(db_path)
        self._labor_rate_cache = {}

    # =========================================================================
    # R/I OPERATIONS CATALOG
    # =========================================================================

    def get_all_ri_operations(self, category: str = None) -> List[Dict]:
        """
        Get all R/I operations, optionally filtered by category.

        Categories: electrical, trim, interior, molding, glass, mechanical
        """
        if category:
            return self.db.execute("""
                SELECT * FROM ri_operations
                WHERE category = ? AND is_active = 1
                ORDER BY name
            """, (category,))
        else:
            return self.db.execute("""
                SELECT * FROM ri_operations
                WHERE is_active = 1
                ORDER BY category, name
            """)

    def get_ri_operation(self, ri_operation_id: int) -> Optional[Dict]:
        """Get single R/I operation by ID"""
        result = self.db.execute("""
            SELECT * FROM ri_operations WHERE id = ?
        """, (ri_operation_id,))
        return dict(result[0]) if result else None

    def get_ri_operation_by_code(self, code: str) -> Optional[Dict]:
        """Get R/I operation by code (e.g., 'RI-HDLNR')"""
        result = self.db.execute("""
            SELECT * FROM ri_operations WHERE code = ?
        """, (code,))
        return dict(result[0]) if result else None

    # =========================================================================
    # R/I TIME LOOKUPS (THE MONEY LOGIC)
    # =========================================================================

    def lookup_ri_time(
        self,
        ri_operation_id: int,
        year: int,
        make: str,
        model: str,
        body_style: str = None
    ) -> Tuple[float, str, int, Optional[int]]:
        """
        Find best matching R/I time with intelligent fallback chain.

        Lookup priority:
        1. Exact match (year + make + model + body_style)
        2. Model match (year in range + make + model, any body style)
        3. Make match (year in range + make only)
        4. Generic fallback (ri_operations.default_hours)

        Args:
            ri_operation_id: R/I operation ID
            year: Vehicle year
            make: Vehicle make (e.g., 'Ford')
            model: Vehicle model (e.g., 'F-150')
            body_style: Body style (e.g., 'SuperCrew')

        Returns:
            Tuple of (hours, source, confidence_score, ri_time_id or None)
        """
        # Level 1: Exact match with body style
        if body_style:
            result = self.db.execute("""
                SELECT id, labor_hours, source, confidence_score
                FROM ri_times
                WHERE ri_operation_id = ?
                  AND ? BETWEEN year_start AND year_end
                  AND LOWER(make) = LOWER(?)
                  AND LOWER(model) = LOWER(?)
                  AND LOWER(body_style) = LOWER(?)
                ORDER BY confidence_score DESC
                LIMIT 1
            """, (ri_operation_id, year, make, model, body_style))

            if result:
                r = result[0]
                return (r['labor_hours'], f"exact_{r['source']}", r['confidence_score'], r['id'])

        # Level 2: Model match (any body style)
        result = self.db.execute("""
            SELECT id, labor_hours, source, confidence_score
            FROM ri_times
            WHERE ri_operation_id = ?
              AND ? BETWEEN year_start AND year_end
              AND LOWER(make) = LOWER(?)
              AND LOWER(model) = LOWER(?)
            ORDER BY confidence_score DESC
            LIMIT 1
        """, (ri_operation_id, year, make, model))

        if result:
            r = result[0]
            return (r['labor_hours'], f"model_{r['source']}", r['confidence_score'] - 10, r['id'])

        # Level 3: Make match only (for same make, different model)
        result = self.db.execute("""
            SELECT id, labor_hours, source, confidence_score
            FROM ri_times
            WHERE ri_operation_id = ?
              AND ? BETWEEN year_start AND year_end
              AND LOWER(make) = LOWER(?)
            ORDER BY confidence_score DESC
            LIMIT 1
        """, (ri_operation_id, year, make))

        if result:
            r = result[0]
            return (r['labor_hours'], f"make_{r['source']}", r['confidence_score'] - 25, r['id'])

        # Level 4: Generic fallback from ri_operations
        op = self.get_ri_operation(ri_operation_id)
        if op and op.get('default_hours'):
            return (op['default_hours'], 'default', 30, None)

        # Ultimate fallback
        return (0.5, 'fallback', 10, None)

    def get_labor_rate(self, rate_type: str = 'body') -> float:
        """
        Get current labor rate for a type.

        Types: body, paint, pdr, mechanical, electrical, glass, structural
        """
        if rate_type in self._labor_rate_cache:
            return self._labor_rate_cache[rate_type]

        result = self.db.execute("""
            SELECT hourly_rate FROM labor_rates
            WHERE rate_type = ? AND is_active = 1
            ORDER BY effective_date DESC
            LIMIT 1
        """, (rate_type,))

        rate = result[0]['hourly_rate'] if result else 52.00  # Default body rate
        self._labor_rate_cache[rate_type] = rate
        return rate

    # =========================================================================
    # AUTO-SUGGESTIONS
    # =========================================================================

    def get_suggested_ri_items(
        self,
        estimate_id: int,
        panel_name: str,
        dent_count: int,
        vehicle_info: Dict
    ) -> List[Dict]:
        """
        Get auto-suggested R/I items for a panel with damage.

        Uses panel_ri_associations rules plus vehicle options to
        determine what R/I items should be included.

        Args:
            estimate_id: Estimate ID
            panel_name: Panel with damage (e.g., 'roof', 'hood')
            dent_count: Number of dents on panel
            vehicle_info: Dict with year, make, model, body_style, has_sunroof, etc.

        Returns:
            List of suggested R/I items with times and pricing
        """
        # Normalize panel name
        panel_name = panel_name.lower().replace(' ', '_')

        # Get associations for this panel
        associations = self.db.execute("""
            SELECT pa.*, ri.name, ri.code, ri.default_hours, ri.default_labor_type
            FROM panel_ri_associations pa
            JOIN ri_operations ri ON ri.id = pa.ri_operation_id
            WHERE pa.panel_name = ?
              AND pa.min_dent_count <= ?
              AND ri.is_active = 1
            ORDER BY pa.priority ASC
        """, (panel_name, dent_count))

        suggestions = []
        already_added = set()

        for assoc in associations:
            # Check vehicle conditions
            condition = assoc.get('vehicle_condition')
            if condition:
                if condition == 'has_sunroof' and not vehicle_info.get('has_sunroof'):
                    continue
                if condition == 'no_sunroof' and vehicle_info.get('has_sunroof'):
                    continue
                if condition == 'has_roof_rails' and not vehicle_info.get('has_roof_rails'):
                    continue
                if condition == 'fuel_door_left' and vehicle_info.get('fuel_door_side') != 'left':
                    continue
                if condition == 'fuel_door_right' and vehicle_info.get('fuel_door_side') != 'right':
                    continue

            # Skip duplicates (e.g., don't add both headliner types)
            ri_code = assoc['code']
            if ri_code in already_added:
                continue

            # Skip conflicting items (headliner vs headliner-sunroof)
            if ri_code == 'RI-HDLNR' and 'RI-HDLNR-SR' in already_added:
                continue
            if ri_code == 'RI-HDLNR-SR' and 'RI-HDLNR' in already_added:
                continue

            # Lookup vehicle-specific time
            hours, source, confidence, ri_time_id = self.lookup_ri_time(
                assoc['ri_operation_id'],
                vehicle_info.get('year', 2020),
                vehicle_info.get('make', ''),
                vehicle_info.get('model', ''),
                vehicle_info.get('body_style')
            )

            # Get labor rate
            labor_type = assoc.get('default_labor_type', 'body')
            rate = self.get_labor_rate(labor_type)

            suggestion = {
                'ri_operation_id': assoc['ri_operation_id'],
                'name': assoc['name'],
                'code': assoc['code'],
                'hours': hours,
                'rate': rate,
                'labor_type': labor_type,
                'total': round(hours * rate, 2),
                'is_default': bool(assoc.get('is_default_selected', 0)),
                'source': source,
                'confidence': confidence,
                'ri_time_id': ri_time_id,
                'reason': assoc.get('condition_notes', ''),
                'panel_name': panel_name
            }

            suggestions.append(suggestion)
            already_added.add(ri_code)

        return suggestions

    # =========================================================================
    # ESTIMATE INTEGRATION
    # =========================================================================

    def add_ri_to_estimate(
        self,
        estimate_id: int,
        ri_operation_id: int,
        hours: float = None,
        panel_name: str = None,
        auto_suggested: bool = False,
        notes: str = None
    ) -> int:
        """
        Add R/I line item to estimate.

        Args:
            estimate_id: Estimate ID
            ri_operation_id: R/I operation ID
            hours: Labor hours (if None, uses lookup)
            panel_name: Panel this R/I is for
            auto_suggested: Was this auto-suggested?
            notes: Optional notes

        Returns:
            estimate_ri_items ID
        """
        # Get operation info
        op = self.get_ri_operation(ri_operation_id)
        if not op:
            raise ValueError(f"R/I operation not found: {ri_operation_id}")

        # Get hours if not provided
        source_ri_time_id = None
        if hours is None:
            # Try to get vehicle info from estimate
            estimate = self.db.execute("""
                SELECT e.*, v.year, v.make, v.model
                FROM estimates e
                LEFT JOIN jobs j ON j.id = e.job_id
                LEFT JOIN vehicles v ON v.id = j.vehicle_id
                WHERE e.id = ?
            """, (estimate_id,))

            if estimate:
                est = estimate[0]
                hours, source, confidence, source_ri_time_id = self.lookup_ri_time(
                    ri_operation_id,
                    est.get('year') or 2020,
                    est.get('make') or '',
                    est.get('model') or ''
                )
            else:
                hours = op.get('default_hours', 0.5)

        # Get labor rate
        labor_type = op.get('default_labor_type', 'body')
        rate = self.get_labor_rate(labor_type)

        line_total = round(hours * rate, 2)

        # Insert line item
        result = self.db.execute("""
            INSERT INTO estimate_ri_items (
                estimate_id, ri_operation_id, panel_name,
                labor_hours, labor_rate, labor_type, line_total,
                auto_suggested, source_ri_time_id, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            ri_operation_id,
            panel_name,
            hours,
            rate,
            labor_type,
            line_total,
            1 if auto_suggested else 0,
            source_ri_time_id,
            notes,
            datetime.now().isoformat()
        ))

        ri_item_id = result[0]['id']

        print(f"[OK] Added R/I: {op['name']}")
        print(f"     {hours} hrs @ ${rate}/hr = ${line_total:.2f}")

        return ri_item_id

    def update_ri_item(
        self,
        ri_item_id: int,
        hours: float = None,
        notes: str = None
    ) -> bool:
        """Update R/I line item hours or notes"""
        item = self.db.execute("SELECT * FROM estimate_ri_items WHERE id = ?", (ri_item_id,))
        if not item:
            return False

        item = item[0]

        if hours is not None:
            line_total = round(hours * item['labor_rate'], 2)
            self.db.execute("""
                UPDATE estimate_ri_items
                SET labor_hours = ?, line_total = ?, was_modified = 1
                WHERE id = ?
            """, (hours, line_total, ri_item_id))

        if notes is not None:
            self.db.execute("""
                UPDATE estimate_ri_items SET notes = ? WHERE id = ?
            """, (notes, ri_item_id))

        return True

    def remove_ri_from_estimate(self, ri_item_id: int) -> bool:
        """Remove R/I line item from estimate"""
        self.db.execute("DELETE FROM estimate_ri_items WHERE id = ?", (ri_item_id,))
        return True

    def get_estimate_ri_items(self, estimate_id: int) -> List[Dict]:
        """Get all R/I items for an estimate"""
        return self.db.execute("""
            SELECT eri.*, ri.name, ri.code, ri.category
            FROM estimate_ri_items eri
            JOIN ri_operations ri ON ri.id = eri.ri_operation_id
            WHERE eri.estimate_id = ?
            ORDER BY eri.created_at
        """, (estimate_id,))

    def recalculate_ri_totals(self, estimate_id: int) -> float:
        """Sum all R/I line items for estimate"""
        result = self.db.execute("""
            SELECT COALESCE(SUM(line_total), 0) as total
            FROM estimate_ri_items
            WHERE estimate_id = ?
        """, (estimate_id,))

        return result[0]['total'] if result else 0.0

    # =========================================================================
    # CROWDSOURCED TIME CORRECTIONS
    # =========================================================================

    def submit_time_correction(
        self,
        ri_time_id: Optional[int],
        estimate_id: int,
        ri_operation_id: int,
        suggested_hours: float,
        actual_hours: float,
        vehicle_info: Dict,
        technician_id: int = None,
        notes: str = None
    ) -> int:
        """
        Log when estimator corrects a time.

        This builds our crowdsourced database of accurate times.

        Args:
            ri_time_id: Original ri_times record (None if was fallback)
            estimate_id: Estimate ID
            ri_operation_id: R/I operation ID
            suggested_hours: What system suggested
            actual_hours: What estimator used
            vehicle_info: Vehicle details
            technician_id: Optional tech ID
            notes: Notes about why correction was made

        Returns:
            Submission ID
        """
        result = self.db.execute("""
            INSERT INTO ri_time_submissions (
                ri_time_id, estimate_id, ri_operation_id,
                vehicle_year, vehicle_make, vehicle_model, vehicle_body_style,
                suggested_hours, actual_hours,
                technician_id, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ri_time_id,
            estimate_id,
            ri_operation_id,
            vehicle_info.get('year'),
            vehicle_info.get('make'),
            vehicle_info.get('model'),
            vehicle_info.get('body_style'),
            suggested_hours,
            actual_hours,
            technician_id,
            notes,
            datetime.now().isoformat()
        ))

        return result[0]['id']

    def get_pending_time_corrections(self, limit: int = 50) -> List[Dict]:
        """Get time corrections awaiting admin approval"""
        return self.db.execute("""
            SELECT ts.*, ri.name as operation_name, ri.code
            FROM ri_time_submissions ts
            JOIN ri_operations ri ON ri.id = ts.ri_operation_id
            WHERE ts.approved = 0
            ORDER BY ts.created_at DESC
            LIMIT ?
        """, (limit,))

    def approve_time_correction(self, submission_id: int) -> bool:
        """
        Approve a time correction and update baseline.

        This updates the ri_times table with better data.
        """
        submission = self.db.execute(
            "SELECT * FROM ri_time_submissions WHERE id = ?",
            (submission_id,)
        )

        if not submission:
            return False

        sub = submission[0]

        # Mark as approved
        self.db.execute(
            "UPDATE ri_time_submissions SET approved = 1 WHERE id = ?",
            (submission_id,)
        )

        # If there was an existing ri_time, update it
        if sub['ri_time_id']:
            existing = self.db.execute(
                "SELECT * FROM ri_times WHERE id = ?",
                (sub['ri_time_id'],)
            )
            if existing:
                old = existing[0]
                # Average with existing data
                new_hours = (old['labor_hours'] + sub['actual_hours']) / 2
                new_sample = old['sample_count'] + 1
                new_confidence = min(100, old['confidence_score'] + 5)

                self.db.execute("""
                    UPDATE ri_times
                    SET labor_hours = ?, sample_count = ?, confidence_score = ?,
                        last_updated = ?
                    WHERE id = ?
                """, (new_hours, new_sample, new_confidence, datetime.now().isoformat(), old['id']))
        else:
            # Create new vehicle-specific time
            self.db.execute("""
                INSERT INTO ri_times (
                    ri_operation_id, year_start, year_end,
                    make, model, body_style,
                    labor_hours, source, confidence_score, sample_count, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'crowdsourced', 60, 1, ?)
            """, (
                sub['ri_operation_id'],
                sub['vehicle_year'],
                sub['vehicle_year'],
                sub['vehicle_make'],
                sub['vehicle_model'],
                sub['vehicle_body_style'],
                sub['actual_hours'],
                datetime.now().isoformat()
            ))

        return True

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_ri_usage_stats(self, days: int = 30) -> Dict:
        """Get R/I usage statistics"""
        result = self.db.execute("""
            SELECT ri.code, ri.name, ri.category,
                   COUNT(*) as usage_count,
                   AVG(eri.labor_hours) as avg_hours,
                   SUM(eri.line_total) as total_revenue
            FROM estimate_ri_items eri
            JOIN ri_operations ri ON ri.id = eri.ri_operation_id
            WHERE eri.created_at >= date('now', '-' || ? || ' days')
            GROUP BY ri.id
            ORDER BY usage_count DESC
            LIMIT 20
        """, (days,))

        return {
            'period_days': days,
            'top_items': result,
            'total_ri_items': sum(r['usage_count'] for r in result),
            'total_revenue': sum(r['total_revenue'] or 0 for r in result)
        }
