"""
PDR Pro Estimating - Historical Comparables Manager
Track and compare approved estimates for negotiation support.

FEATURES:
- Store approved estimates as comparables
- Find similar vehicles and damage levels
- Calculate averages for negotiation
- Support insurance pushback with data
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from src.crm.models.database import Database


class EstimateComparablesManager:
    """
    Historical comparable estimates for negotiation support.

    Know what similar jobs got approved for - incredibly
    powerful for insurance negotiations.
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize comparables manager"""
        self.db = Database(db_path)

    # =========================================================================
    # FIND COMPARABLES
    # =========================================================================

    def find_comparables(
        self,
        vehicle_year: int,
        vehicle_make: str,
        vehicle_model: str,
        damage_severity: str = None,
        insurance_company_id: int = None,
        year_range: int = 3,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find similar approved estimates.

        Args:
            vehicle_year: Target vehicle year
            vehicle_make: Target vehicle make
            vehicle_model: Target vehicle model
            damage_severity: Optional severity filter (light, moderate, severe)
            insurance_company_id: Optional filter by insurance company
            year_range: How many years +/- to include (default 3)
            limit: Max results

        Returns:
            List of comparable estimates with totals and approval rates
        """
        query = """
            SELECT ec.*, ic.name as insurance_name
            FROM estimate_comparables ec
            LEFT JOIN insurance_companies ic ON ic.id = ec.insurance_company_id
            WHERE LOWER(ec.vehicle_make) = LOWER(?)
              AND LOWER(ec.vehicle_model) = LOWER(?)
              AND ABS(ec.vehicle_year - ?) <= ?
        """
        params = [vehicle_make, vehicle_model, vehicle_year, year_range]

        if damage_severity:
            query += " AND ec.damage_severity = ?"
            params.append(damage_severity)

        if insurance_company_id:
            query += " AND ec.insurance_company_id = ?"
            params.append(insurance_company_id)

        query += " ORDER BY ec.approval_date DESC LIMIT ?"
        params.append(limit)

        comparables = self.db.execute(query, tuple(params))

        # Parse JSON fields
        for comp in comparables:
            if comp.get('panel_breakdown'):
                try:
                    comp['panel_breakdown'] = json.loads(comp['panel_breakdown'])
                except:
                    pass
            if comp.get('ri_breakdown'):
                try:
                    comp['ri_breakdown'] = json.loads(comp['ri_breakdown'])
                except:
                    pass

        return comparables

    def get_comparable_stats(
        self,
        vehicle_make: str,
        vehicle_model: str,
        year_range: tuple = None,
        damage_severity: str = None
    ) -> Dict:
        """
        Get aggregate statistics for a vehicle type.

        Returns:
            - Average estimate total
            - Average approved total
            - Approval rate
            - Common R/I items
            - Sample size
        """
        query = """
            SELECT
                COUNT(*) as sample_size,
                AVG(estimate_total) as avg_estimate,
                AVG(approved_total) as avg_approved,
                AVG(approval_percentage) as avg_approval_rate,
                AVG(pdr_labor_total) as avg_pdr_labor,
                AVG(ri_labor_total) as avg_ri_labor,
                AVG(parts_total) as avg_parts,
                AVG(total_dent_count) as avg_dent_count,
                AVG(total_panels_damaged) as avg_panels
            FROM estimate_comparables
            WHERE LOWER(vehicle_make) = LOWER(?)
              AND LOWER(vehicle_model) = LOWER(?)
        """
        params = [vehicle_make, vehicle_model]

        if year_range:
            query += " AND vehicle_year BETWEEN ? AND ?"
            params.extend(year_range)

        if damage_severity:
            query += " AND damage_severity = ?"
            params.append(damage_severity)

        result = self.db.execute(query, tuple(params))
        stats = dict(result[0]) if result else {}

        stats['vehicle_make'] = vehicle_make
        stats['vehicle_model'] = vehicle_model

        return stats

    # =========================================================================
    # SAVE COMPARABLES
    # =========================================================================

    def save_comparable(self, estimate_id: int) -> int:
        """
        Save completed/approved estimate as a comparable.

        Call this when an estimate is marked approved and paid.
        Captures snapshot for future comparison.

        Returns:
            Comparable ID
        """
        # Get full estimate details
        estimate = self.db.execute("""
            SELECT e.*, j.id as job_id,
                   v.year as vehicle_year, v.make as vehicle_make,
                   v.model as vehicle_model,
                   ic.id as insurance_company_id
            FROM estimates e
            LEFT JOIN jobs j ON j.id = e.job_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            LEFT JOIN insurance_claims icl ON icl.id = j.insurance_claim_id
            LEFT JOIN insurance_companies ic ON ic.name = icl.insurance_company
            WHERE e.id = ?
        """, (estimate_id,))

        if not estimate:
            raise ValueError(f"Estimate not found: {estimate_id}")

        est = estimate[0]

        # Get R/I totals
        ri_result = self.db.execute("""
            SELECT COALESCE(SUM(line_total), 0) as total
            FROM estimate_ri_items WHERE estimate_id = ?
        """, (estimate_id,))
        ri_total = ri_result[0]['total'] if ri_result else 0

        # Get parts total
        parts_result = self.db.execute("""
            SELECT COALESCE(SUM(line_total), 0) as total
            FROM estimate_parts WHERE estimate_id = ?
        """, (estimate_id,))
        parts_total = parts_result[0]['total'] if parts_result else 0

        # Get panel counts from dent maps
        panel_stats = self._get_panel_stats(est.get('job_id'))

        # Calculate PDR labor (estimate total - R/I - parts)
        pdr_labor = (est.get('total', 0) or 0) - ri_total - parts_total

        # Determine damage severity
        dent_count = panel_stats.get('total_dents', 0)
        if dent_count > 100:
            severity = 'severe'
        elif dent_count > 50:
            severity = 'moderate'
        else:
            severity = 'light'

        # Calculate approval percentage
        approved = est.get('total', 0)  # Assuming approved = estimate for now
        approval_pct = 100.0 if approved else 0

        # Insert comparable
        result = self.db.execute("""
            INSERT INTO estimate_comparables (
                estimate_id, job_id,
                vehicle_year, vehicle_make, vehicle_model, vehicle_body_style,
                total_panels_damaged, total_dent_count, damage_severity,
                pdr_labor_total, ri_labor_total, parts_total, estimate_total,
                approved_total, approval_percentage,
                insurance_company_id,
                estimate_date, approval_date,
                panel_breakdown, ri_breakdown,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            est.get('job_id'),
            est.get('vehicle_year'),
            est.get('vehicle_make'),
            est.get('vehicle_model'),
            None,  # body_style
            panel_stats.get('panel_count', 0),
            dent_count,
            severity,
            pdr_labor,
            ri_total,
            parts_total,
            est.get('total', 0),
            approved,
            approval_pct,
            est.get('insurance_company_id'),
            est.get('created_date'),
            date.today().isoformat(),
            json.dumps(panel_stats.get('breakdown', {})),
            None,  # ri_breakdown
            datetime.now().isoformat()
        ))

        comp_id = result[0]['id']
        print(f"[OK] Saved estimate {estimate_id} as comparable #{comp_id}")

        return comp_id

    def _get_panel_stats(self, job_id: int) -> Dict:
        """Get panel statistics from dent maps"""
        if not job_id:
            return {'panel_count': 0, 'total_dents': 0, 'breakdown': {}}

        result = self.db.execute("""
            SELECT panel, COUNT(*) as dent_count
            FROM dents d
            JOIN dent_maps dm ON dm.id = d.dent_map_id
            WHERE dm.job_id = ?
            GROUP BY panel
        """, (job_id,))

        breakdown = {r['panel']: r['dent_count'] for r in result}

        return {
            'panel_count': len(breakdown),
            'total_dents': sum(breakdown.values()),
            'breakdown': breakdown
        }

    # =========================================================================
    # NEGOTIATION SUPPORT
    # =========================================================================

    def get_comparable_for_negotiation(self, estimate_id: int) -> Dict:
        """
        Get comparison data formatted for insurance negotiation.

        Returns data like:
        "Similar vehicles averaged $X, this estimate is $Y"
        """
        # Get estimate details
        estimate = self.db.execute("""
            SELECT e.*, v.year, v.make, v.model
            FROM estimates e
            LEFT JOIN jobs j ON j.id = e.job_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE e.id = ?
        """, (estimate_id,))

        if not estimate:
            return {'error': 'Estimate not found'}

        est = estimate[0]

        # Find comparables
        comparables = self.find_comparables(
            est.get('year', 2020),
            est.get('make', ''),
            est.get('model', ''),
            limit=20
        )

        if not comparables:
            return {
                'estimate_id': estimate_id,
                'this_estimate': est.get('total', 0),
                'comparables_found': 0,
                'message': f"No comparable estimates found for {est.get('year')} {est.get('make')} {est.get('model')}"
            }

        # Calculate stats
        avg_estimate = sum(c['estimate_total'] or 0 for c in comparables) / len(comparables)
        avg_approved = sum(c['approved_total'] or 0 for c in comparables) / len(comparables)
        avg_approval_rate = sum(c['approval_percentage'] or 0 for c in comparables) / len(comparables)

        this_estimate = est.get('total', 0)
        variance = ((this_estimate - avg_estimate) / avg_estimate * 100) if avg_estimate else 0

        result = {
            'estimate_id': estimate_id,
            'vehicle': f"{est.get('year')} {est.get('make')} {est.get('model')}",
            'this_estimate': this_estimate,
            'comparables_found': len(comparables),
            'average_estimate': round(avg_estimate, 2),
            'average_approved': round(avg_approved, 2),
            'average_approval_rate': round(avg_approval_rate, 1),
            'variance_from_average': round(variance, 1),
            'negotiation_points': []
        }

        # Generate negotiation points
        if variance < -10:
            result['negotiation_points'].append(
                f"This estimate is {abs(variance):.0f}% BELOW the average of ${avg_estimate:,.2f} for similar vehicles."
            )
        elif variance > 10:
            result['negotiation_points'].append(
                f"This estimate is only {variance:.0f}% above the average of ${avg_estimate:,.2f} for similar vehicles with comparable damage."
            )

        if avg_approval_rate > 90:
            result['negotiation_points'].append(
                f"Historical approval rate for similar vehicles is {avg_approval_rate:.0f}%."
            )

        # Add specific comparable examples
        best_comparable = max(comparables, key=lambda x: x['approved_total'] or 0)
        if best_comparable.get('approved_total'):
            result['negotiation_points'].append(
                f"A similar {best_comparable['vehicle_year']} {best_comparable['vehicle_make']} {best_comparable['vehicle_model']} was approved at ${best_comparable['approved_total']:,.2f}."
            )

        return result

    def generate_comparison_report(self, estimate_id: int) -> str:
        """Generate text report for negotiation"""
        data = self.get_comparable_for_negotiation(estimate_id)

        if data.get('error'):
            return data['error']

        lines = [
            "=" * 60,
            "HISTORICAL COMPARABLE ANALYSIS",
            "=" * 60,
            "",
            f"Vehicle: {data['vehicle']}",
            f"This Estimate: ${data['this_estimate']:,.2f}",
            "",
            f"Comparables Found: {data['comparables_found']}",
            f"Average Estimate: ${data['average_estimate']:,.2f}",
            f"Average Approved: ${data['average_approved']:,.2f}",
            f"Average Approval Rate: {data['average_approval_rate']:.1f}%",
            "",
            "NEGOTIATION POINTS:",
            "-" * 60
        ]

        for point in data.get('negotiation_points', []):
            lines.append(f"  - {point}")

        lines.extend([
            "",
            "=" * 60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60
        ])

        return "\n".join(lines)

    # =========================================================================
    # MANAGEMENT
    # =========================================================================

    def get_comparable(self, comparable_id: int) -> Optional[Dict]:
        """Get single comparable by ID"""
        result = self.db.execute("""
            SELECT ec.*, ic.name as insurance_name
            FROM estimate_comparables ec
            LEFT JOIN insurance_companies ic ON ic.id = ec.insurance_company_id
            WHERE ec.id = ?
        """, (comparable_id,))

        if not result:
            return None

        comp = dict(result[0])

        if comp.get('panel_breakdown'):
            try:
                comp['panel_breakdown'] = json.loads(comp['panel_breakdown'])
            except:
                pass

        return comp

    def update_approval(
        self,
        comparable_id: int,
        approved_total: float,
        approval_date: str = None
    ) -> bool:
        """Update approval info after negotiation"""
        comp = self.get_comparable(comparable_id)
        if not comp:
            return False

        approval_pct = (approved_total / comp['estimate_total'] * 100) if comp['estimate_total'] else 0

        self.db.execute("""
            UPDATE estimate_comparables
            SET approved_total = ?,
                approval_percentage = ?,
                approval_date = ?
            WHERE id = ?
        """, (
            approved_total,
            approval_pct,
            approval_date or date.today().isoformat(),
            comparable_id
        ))

        return True

    def get_vehicle_makes(self) -> List[str]:
        """Get list of vehicle makes in comparables"""
        result = self.db.execute("""
            SELECT DISTINCT vehicle_make
            FROM estimate_comparables
            ORDER BY vehicle_make
        """)
        return [r['vehicle_make'] for r in result]

    def get_vehicle_models(self, make: str) -> List[str]:
        """Get list of models for a make"""
        result = self.db.execute("""
            SELECT DISTINCT vehicle_model
            FROM estimate_comparables
            WHERE LOWER(vehicle_make) = LOWER(?)
            ORDER BY vehicle_model
        """, (make,))
        return [r['vehicle_model'] for r in result]

    def get_comparables_count(self) -> int:
        """Get total number of comparables"""
        result = self.db.execute("SELECT COUNT(*) as count FROM estimate_comparables")
        return result[0]['count'] if result else 0
