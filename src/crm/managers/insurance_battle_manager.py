"""
PDR Pro Estimating - Insurance Battle Manager
Track insurance companies, adjusters, claim interactions, and pushback justifications.

FEATURES:
- Insurance company profiles with agreed rates
- Adjuster tracking with performance stats
- Interaction logging and outcome tracking
- Pre-built pushback justifications
- Supplement workflow management
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from src.crm.models.database import Database


class InsuranceBattleManager:
    """
    Manage insurance company relationships and claim negotiations.

    This is what separates pros from amateurs - knowing which adjusters
    are easy to work with, what pushback to expect, and how to respond.
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize insurance battle manager"""
        self.db = Database(db_path)

    # =========================================================================
    # INSURANCE COMPANIES
    # =========================================================================

    def get_all_insurance_companies(self) -> List[Dict]:
        """Get all insurance companies"""
        return self.db.execute("""
            SELECT * FROM insurance_companies
            ORDER BY name
        """)

    def get_insurance_company(self, company_id: int) -> Optional[Dict]:
        """Get insurance company profile with rates and tendencies"""
        result = self.db.execute("""
            SELECT * FROM insurance_companies WHERE id = ?
        """, (company_id,))

        if not result:
            return None

        company = dict(result[0])

        # Parse JSON fields
        if company.get('common_pushback_items'):
            try:
                company['common_pushback_items'] = json.loads(company['common_pushback_items'])
            except:
                company['common_pushback_items'] = []

        # Get adjuster count
        adjuster_count = self.db.execute("""
            SELECT COUNT(*) as count FROM insurance_adjusters
            WHERE insurance_company_id = ?
        """, (company_id,))
        company['adjuster_count'] = adjuster_count[0]['count'] if adjuster_count else 0

        return company

    def get_company_by_code(self, code: str) -> Optional[Dict]:
        """Get insurance company by code (e.g., 'STATEFARM')"""
        result = self.db.execute("""
            SELECT * FROM insurance_companies WHERE code = ?
        """, (code,))
        return dict(result[0]) if result else None

    def create_insurance_company(self, data: Dict) -> int:
        """Create new insurance company"""
        result = self.db.execute("""
            INSERT INTO insurance_companies (
                name, code, body_rate, paint_rate, pdr_rate, mechanical_rate,
                preferred_estimate_format, typical_review_days, supplement_friendly,
                common_pushback_items, claims_phone, claims_email, claims_portal_url,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'],
            data.get('code'),
            data.get('body_rate'),
            data.get('paint_rate'),
            data.get('pdr_rate'),
            data.get('mechanical_rate'),
            data.get('preferred_estimate_format'),
            data.get('typical_review_days'),
            1 if data.get('supplement_friendly', True) else 0,
            json.dumps(data.get('common_pushback_items', [])),
            data.get('claims_phone'),
            data.get('claims_email'),
            data.get('claims_portal_url'),
            data.get('notes'),
            datetime.now().isoformat()
        ))

        return result[0]['id']

    def get_company_stats(self, company_id: int, days: int = 90) -> Dict:
        """
        Get aggregate statistics for insurance company.

        Returns approval rates, average times, etc.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # Total claims
        claims = self.db.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN outcome = 'approved' THEN 1 ELSE 0 END) as approved,
                   SUM(CASE WHEN outcome = 'partial' THEN 1 ELSE 0 END) as partial,
                   SUM(CASE WHEN outcome = 'denied' THEN 1 ELSE 0 END) as denied,
                   SUM(amount_requested) as total_requested,
                   SUM(amount_approved) as total_approved,
                   AVG(JULIANDAY(response_date) - JULIANDAY(interaction_date)) as avg_response_days
            FROM adjuster_interactions
            WHERE insurance_company_id = ?
              AND created_at >= ?
        """, (company_id, cutoff))

        stats = claims[0] if claims else {}

        # Calculate approval rate
        if stats.get('total_requested') and stats['total_requested'] > 0:
            stats['approval_rate'] = (stats['total_approved'] or 0) / stats['total_requested'] * 100
        else:
            stats['approval_rate'] = 0

        stats['period_days'] = days
        stats['company_id'] = company_id

        return stats

    # =========================================================================
    # ADJUSTERS
    # =========================================================================

    def get_adjuster(self, adjuster_id: int) -> Optional[Dict]:
        """Get adjuster with calculated stats"""
        result = self.db.execute("""
            SELECT a.*, ic.name as company_name, ic.code as company_code
            FROM insurance_adjusters a
            LEFT JOIN insurance_companies ic ON ic.id = a.insurance_company_id
            WHERE a.id = ?
        """, (adjuster_id,))

        if not result:
            return None

        adjuster = dict(result[0])

        # Get recent stats
        stats = self._calculate_adjuster_stats(adjuster_id)
        adjuster.update(stats)

        return adjuster

    def get_adjusters_by_company(self, company_id: int) -> List[Dict]:
        """Get all adjusters for a company"""
        return self.db.execute("""
            SELECT * FROM insurance_adjusters
            WHERE insurance_company_id = ?
            ORDER BY name
        """, (company_id,))

    def create_adjuster(self, data: Dict) -> int:
        """Create new adjuster"""
        result = self.db.execute("""
            INSERT INTO insurance_adjusters (
                insurance_company_id, name, employee_id,
                phone, email, territory,
                is_field_adjuster, is_ia, response_speed, difficulty_rating,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('insurance_company_id'),
            data['name'],
            data.get('employee_id'),
            data.get('phone'),
            data.get('email'),
            data.get('territory'),
            1 if data.get('is_field_adjuster') else 0,
            1 if data.get('is_ia') else 0,
            data.get('response_speed'),
            data.get('difficulty_rating'),
            data.get('notes'),
            datetime.now().isoformat()
        ))

        return result[0]['id']

    def update_adjuster(self, adjuster_id: int, data: Dict) -> bool:
        """Update adjuster info"""
        updates = []
        params = []

        for key in ['name', 'phone', 'email', 'territory', 'response_speed',
                    'difficulty_rating', 'notes']:
            if key in data:
                updates.append(f"{key} = ?")
                params.append(data[key])

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(adjuster_id)

        self.db.execute(f"""
            UPDATE insurance_adjusters
            SET {', '.join(updates)}
            WHERE id = ?
        """, tuple(params))

        return True

    def search_adjusters(self, query: str) -> List[Dict]:
        """Search adjusters by name or company"""
        return self.db.execute("""
            SELECT a.*, ic.name as company_name
            FROM insurance_adjusters a
            LEFT JOIN insurance_companies ic ON ic.id = a.insurance_company_id
            WHERE a.name LIKE ? OR ic.name LIKE ?
            ORDER BY a.name
            LIMIT 20
        """, (f"%{query}%", f"%{query}%"))

    def _calculate_adjuster_stats(self, adjuster_id: int, days: int = 90) -> Dict:
        """Calculate adjuster performance stats"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        result = self.db.execute("""
            SELECT
                COUNT(*) as total_claims,
                SUM(CASE WHEN outcome = 'approved' THEN 1 ELSE 0 END) as approved_count,
                SUM(amount_requested) as total_requested,
                SUM(amount_approved) as total_approved,
                AVG(supplement_number) as avg_supplements,
                MAX(supplement_number) as max_supplements
            FROM adjuster_interactions
            WHERE adjuster_id = ?
              AND created_at >= ?
        """, (adjuster_id, cutoff))

        stats = result[0] if result else {}

        if stats.get('total_requested') and stats['total_requested'] > 0:
            stats['approval_rate'] = (stats['total_approved'] or 0) / stats['total_requested'] * 100
        else:
            stats['approval_rate'] = 0

        return stats

    # =========================================================================
    # INTERACTIONS
    # =========================================================================

    def log_interaction(
        self,
        estimate_id: int,
        adjuster_id: int,
        interaction_type: str,
        items_approved: List = None,
        items_denied: List = None,
        items_reduced: List = None,
        amount_requested: float = None,
        amount_approved: float = None,
        supplement_number: int = 0,
        outcome: str = 'pending',
        notes: str = None
    ) -> int:
        """
        Log an interaction with adjuster.

        Interaction types:
        - initial_review
        - supplement_request
        - negotiation
        - approval
        - denial

        Outcomes:
        - approved
        - partial
        - denied
        - pending
        """
        # Get insurance company from adjuster
        adjuster = self.db.execute(
            "SELECT insurance_company_id FROM insurance_adjusters WHERE id = ?",
            (adjuster_id,)
        )
        company_id = adjuster[0]['insurance_company_id'] if adjuster else None

        # Get job_id from estimate
        estimate = self.db.execute(
            "SELECT job_id FROM estimates WHERE id = ?",
            (estimate_id,)
        )
        job_id = estimate[0]['job_id'] if estimate else None

        result = self.db.execute("""
            INSERT INTO adjuster_interactions (
                estimate_id, job_id, adjuster_id, insurance_company_id,
                interaction_type, interaction_date,
                items_approved, items_denied, items_reduced,
                amount_requested, amount_approved,
                supplement_number, outcome, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            job_id,
            adjuster_id,
            company_id,
            interaction_type,
            date.today().isoformat(),
            json.dumps(items_approved) if items_approved else None,
            json.dumps(items_denied) if items_denied else None,
            json.dumps(items_reduced) if items_reduced else None,
            amount_requested,
            amount_approved,
            supplement_number,
            outcome,
            notes,
            datetime.now().isoformat()
        ))

        interaction_id = result[0]['id']

        # Update adjuster stats
        self._update_adjuster_stats(adjuster_id)

        print(f"[OK] Logged {interaction_type} with adjuster")
        if amount_approved:
            print(f"     Approved: ${amount_approved:,.2f} of ${amount_requested:,.2f}")

        return interaction_id

    def get_interactions(self, estimate_id: int) -> List[Dict]:
        """Get all interactions for an estimate"""
        interactions = self.db.execute("""
            SELECT ai.*, ia.name as adjuster_name, ic.name as company_name
            FROM adjuster_interactions ai
            LEFT JOIN insurance_adjusters ia ON ia.id = ai.adjuster_id
            LEFT JOIN insurance_companies ic ON ic.id = ai.insurance_company_id
            WHERE ai.estimate_id = ?
            ORDER BY ai.created_at DESC
        """, (estimate_id,))

        # Parse JSON fields
        for interaction in interactions:
            for field in ['items_approved', 'items_denied', 'items_reduced']:
                if interaction.get(field):
                    try:
                        interaction[field] = json.loads(interaction[field])
                    except:
                        pass

        return interactions

    def _update_adjuster_stats(self, adjuster_id: int):
        """Update cached adjuster stats"""
        stats = self._calculate_adjuster_stats(adjuster_id)

        self.db.execute("""
            UPDATE insurance_adjusters
            SET total_claims_handled = ?,
                average_approval_rate = ?,
                average_supplement_rounds = ?,
                last_interaction_date = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            stats.get('total_claims', 0),
            stats.get('approval_rate', 0),
            stats.get('avg_supplements', 0),
            date.today().isoformat(),
            datetime.now().isoformat(),
            adjuster_id
        ))

    # =========================================================================
    # PUSHBACK JUSTIFICATIONS
    # =========================================================================

    def get_justification(
        self,
        category: str,
        trigger_item: str,
        insurance_company_id: int = None
    ) -> Optional[Dict]:
        """
        Get best pushback justification for an item.

        First tries company-specific, then universal.

        Categories: ri_time, pdr_price, parts, conventional
        """
        # Try company-specific first
        if insurance_company_id:
            result = self.db.execute("""
                SELECT * FROM pushback_justifications
                WHERE category = ?
                  AND trigger_item = ?
                  AND insurance_company_id = ?
                ORDER BY success_rate DESC
                LIMIT 1
            """, (category, trigger_item, insurance_company_id))

            if result:
                return dict(result[0])

        # Fall back to universal
        result = self.db.execute("""
            SELECT * FROM pushback_justifications
            WHERE category = ?
              AND trigger_item = ?
              AND insurance_company_id IS NULL
            ORDER BY success_rate DESC
            LIMIT 1
        """, (category, trigger_item))

        return dict(result[0]) if result else None

    def get_all_justifications(self, category: str = None) -> List[Dict]:
        """Get all justifications, optionally by category"""
        if category:
            return self.db.execute("""
                SELECT pj.*, ic.name as company_name
                FROM pushback_justifications pj
                LEFT JOIN insurance_companies ic ON ic.id = pj.insurance_company_id
                WHERE pj.category = ?
                ORDER BY pj.success_rate DESC
            """, (category,))
        else:
            return self.db.execute("""
                SELECT pj.*, ic.name as company_name
                FROM pushback_justifications pj
                LEFT JOIN insurance_companies ic ON ic.id = pj.insurance_company_id
                ORDER BY pj.category, pj.success_rate DESC
            """)

    def record_justification_usage(
        self,
        justification_id: int,
        was_successful: bool
    ) -> bool:
        """Record that a justification was used and whether it worked"""
        self.db.execute("""
            UPDATE pushback_justifications
            SET times_used = times_used + 1,
                times_successful = times_successful + CASE WHEN ? THEN 1 ELSE 0 END,
                success_rate = CAST(times_successful + CASE WHEN ? THEN 1 ELSE 0 END AS REAL) /
                              CAST(times_used + 1 AS REAL) * 100
            WHERE id = ?
        """, (was_successful, was_successful, justification_id))

        return True

    def create_justification(self, data: Dict) -> int:
        """Create new pushback justification"""
        result = self.db.execute("""
            INSERT INTO pushback_justifications (
                category, trigger_item, insurance_company_id,
                title, justification_text,
                oem_reference, mitchell_reference, labor_time_source,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['category'],
            data['trigger_item'],
            data.get('insurance_company_id'),
            data.get('title'),
            data['justification_text'],
            data.get('oem_reference'),
            data.get('mitchell_reference'),
            data.get('labor_time_source'),
            data.get('notes'),
            datetime.now().isoformat()
        ))

        return result[0]['id']

    # =========================================================================
    # SUPPLEMENTS
    # =========================================================================

    def create_supplement(
        self,
        original_estimate_id: int,
        reason: str,
        panels_added: List = None,
        ri_items_added: List = None,
        parts_added: List = None,
        amount_added: float = None
    ) -> int:
        """Create a supplement for an estimate"""
        # Get next supplement number
        existing = self.db.execute("""
            SELECT MAX(supplement_number) as max_num
            FROM estimate_supplements
            WHERE original_estimate_id = ?
        """, (original_estimate_id,))

        next_num = (existing[0]['max_num'] or 0) + 1 if existing else 1

        result = self.db.execute("""
            INSERT INTO estimate_supplements (
                original_estimate_id, supplement_number,
                reason, panels_added, ri_items_added, parts_added,
                amount_added, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?)
        """, (
            original_estimate_id,
            next_num,
            reason,
            json.dumps(panels_added) if panels_added else None,
            json.dumps(ri_items_added) if ri_items_added else None,
            json.dumps(parts_added) if parts_added else None,
            amount_added,
            datetime.now().isoformat()
        ))

        print(f"[OK] Created supplement #{next_num} for estimate {original_estimate_id}")

        return result[0]['id']

    def get_supplements(self, original_estimate_id: int) -> List[Dict]:
        """Get all supplements for an estimate"""
        supplements = self.db.execute("""
            SELECT es.*, ia.name as adjuster_name
            FROM estimate_supplements es
            LEFT JOIN insurance_adjusters ia ON ia.id = es.adjuster_id
            WHERE es.original_estimate_id = ?
            ORDER BY es.supplement_number
        """, (original_estimate_id,))

        for sup in supplements:
            for field in ['panels_added', 'ri_items_added', 'parts_added']:
                if sup.get(field):
                    try:
                        sup[field] = json.loads(sup[field])
                    except:
                        pass

        return supplements

    def submit_supplement(self, supplement_id: int, adjuster_id: int = None) -> bool:
        """Mark supplement as submitted"""
        self.db.execute("""
            UPDATE estimate_supplements
            SET status = 'submitted',
                submitted_date = ?,
                adjuster_id = ?
            WHERE id = ?
        """, (date.today().isoformat(), adjuster_id, supplement_id))

        return True

    def record_supplement_response(
        self,
        supplement_id: int,
        amount_approved: float,
        status: str = 'approved',
        adjuster_notes: str = None
    ) -> bool:
        """Record insurance response to supplement"""
        self.db.execute("""
            UPDATE estimate_supplements
            SET status = ?,
                amount_approved = ?,
                response_date = ?,
                adjuster_notes = ?
            WHERE id = ?
        """, (status, amount_approved, date.today().isoformat(), adjuster_notes, supplement_id))

        return True

    # =========================================================================
    # REPORTS
    # =========================================================================

    def get_insurance_performance_report(self, days: int = 90) -> Dict:
        """Get report on insurance company performance"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        companies = self.db.execute("""
            SELECT ic.id, ic.name, ic.code,
                   COUNT(ai.id) as claim_count,
                   SUM(ai.amount_requested) as total_requested,
                   SUM(ai.amount_approved) as total_approved,
                   AVG(ai.supplement_number) as avg_supplements
            FROM insurance_companies ic
            LEFT JOIN adjuster_interactions ai ON ai.insurance_company_id = ic.id
                AND ai.created_at >= ?
            GROUP BY ic.id
            ORDER BY claim_count DESC
        """, (cutoff,))

        for co in companies:
            if co['total_requested'] and co['total_requested'] > 0:
                co['approval_rate'] = (co['total_approved'] or 0) / co['total_requested'] * 100
            else:
                co['approval_rate'] = 0

        return {
            'period_days': days,
            'companies': companies,
            'total_claims': sum(c['claim_count'] or 0 for c in companies),
            'total_requested': sum(c['total_requested'] or 0 for c in companies),
            'total_approved': sum(c['total_approved'] or 0 for c in companies)
        }
