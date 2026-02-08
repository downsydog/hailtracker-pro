"""
PDR Pro Estimating - Smart Alerts Manager
Automatic detection of missing items, low estimates, and inconsistencies.

FEATURES:
- Missing R/I detection
- Estimate consistency checks vs comparables
- Photo documentation gaps
- Configurable alert rules
- Alert resolution tracking
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from src.crm.models.database import Database


class EstimateAlertsManager:
    """
    Smart alerts for PDR estimates.

    The "you might be missing money" system that catches:
    - Missing R/I items for damaged panels
    - Estimates significantly below average
    - Missing photo documentation
    - Other configurable issues
    """

    def __init__(self, db_path: str = "data/pdr_crm.db"):
        """Initialize alerts manager"""
        self.db = Database(db_path)

    # =========================================================================
    # RUN ALL ALERTS
    # =========================================================================

    def run_alerts(self, estimate_id: int) -> List[Dict]:
        """
        Run all active alert rules against an estimate.

        Returns list of triggered alerts.
        """
        triggered = []

        # Get estimate info
        estimate = self._get_estimate_details(estimate_id)
        if not estimate:
            return []

        # Check missing R/I
        ri_alerts = self.check_missing_ri(estimate_id)
        triggered.extend(ri_alerts)

        # Check consistency
        consistency = self.check_consistency(estimate_id)
        if consistency.get('alert'):
            triggered.append(consistency['alert'])

        # Check photos
        photo_alerts = self.check_photos(estimate_id)
        triggered.extend(photo_alerts)

        # Save all triggered alerts
        for alert in triggered:
            self._save_alert(estimate_id, alert)

        return triggered

    # =========================================================================
    # MISSING R/I DETECTION
    # =========================================================================

    def check_missing_ri(self, estimate_id: int) -> List[Dict]:
        """
        Check for panels with damage but missing expected R/I.

        Uses panel_ri_associations to determine what should be included.
        """
        alerts = []

        # Get panels with damage from estimate
        # This assumes we have estimate line items or a panel damage table
        panels = self._get_damaged_panels(estimate_id)

        # Get current R/I items on estimate
        ri_items = self.db.execute("""
            SELECT eri.*, ri.code
            FROM estimate_ri_items eri
            JOIN ri_operations ri ON ri.id = eri.ri_operation_id
            WHERE eri.estimate_id = ?
        """, (estimate_id,))

        current_ri_codes = set(ri['code'] for ri in ri_items)

        # Check each panel
        for panel in panels:
            panel_name = panel['panel_name']
            dent_count = panel.get('dent_count', 0)

            # Get expected R/I for this panel
            expected = self.db.execute("""
                SELECT pa.*, ri.code, ri.name
                FROM panel_ri_associations pa
                JOIN ri_operations ri ON ri.id = pa.ri_operation_id
                WHERE pa.panel_name = ?
                  AND pa.is_default_selected = 1
                  AND pa.min_dent_count <= ?
            """, (panel_name, dent_count))

            for exp in expected:
                if exp['code'] not in current_ri_codes:
                    # Check alert rules for specific message
                    rule = self._get_alert_rule_for_ri(exp['code'])

                    alerts.append({
                        'alert_type': 'missing_ri',
                        'severity': 'warning',
                        'message': rule.get('alert_message',
                            f"Panel '{panel_name}' has {dent_count} dents but no {exp['name']} included.").format(
                                dent_count=dent_count,
                                panel=panel_name
                            ),
                        'trigger_panel': panel_name,
                        'trigger_data': json.dumps({
                            'missing_ri_code': exp['code'],
                            'missing_ri_name': exp['name'],
                            'dent_count': dent_count
                        }),
                        'suggested_action': f"Add {exp['name']}",
                        'alert_rule_id': rule.get('id')
                    })

        return alerts

    def _get_damaged_panels(self, estimate_id: int) -> List[Dict]:
        """Get panels with damage from estimate"""
        # Try to get from estimate line items
        panels = self.db.execute("""
            SELECT DISTINCT panel_name, COUNT(*) as dent_count
            FROM estimate_ri_items
            WHERE estimate_id = ? AND panel_name IS NOT NULL
            GROUP BY panel_name
        """, (estimate_id,))

        if panels:
            return panels

        # Fallback: check dent_maps linked to job
        estimate = self.db.execute("""
            SELECT job_id FROM estimates WHERE id = ?
        """, (estimate_id,))

        if estimate and estimate[0].get('job_id'):
            job_id = estimate[0]['job_id']

            return self.db.execute("""
                SELECT panel as panel_name, COUNT(*) as dent_count
                FROM dents d
                JOIN dent_maps dm ON dm.id = d.dent_map_id
                WHERE dm.job_id = ?
                GROUP BY panel
            """, (job_id,))

        return []

    def _get_alert_rule_for_ri(self, ri_code: str) -> Dict:
        """Get alert rule that matches this R/I code"""
        rules = self.db.execute("""
            SELECT * FROM estimate_alert_rules
            WHERE alert_type = 'missing_ri'
              AND is_active = 1
              AND trigger_conditions LIKE ?
        """, (f'%{ri_code}%',))

        return dict(rules[0]) if rules else {}

    # =========================================================================
    # CONSISTENCY CHECKS
    # =========================================================================

    def check_consistency(self, estimate_id: int) -> Dict:
        """
        Compare estimate to historical comparables.

        Returns variance info and generates alert if significantly low.
        """
        estimate = self._get_estimate_details(estimate_id)
        if not estimate:
            return {'error': 'Estimate not found'}

        # Find comparable estimates
        comparables = self.db.execute("""
            SELECT AVG(estimate_total) as avg_total,
                   AVG(approved_total) as avg_approved,
                   COUNT(*) as count
            FROM estimate_comparables
            WHERE vehicle_make = ?
              AND vehicle_model = ?
              AND ABS(vehicle_year - ?) <= 3
              AND damage_severity = ?
        """, (
            estimate.get('vehicle_make'),
            estimate.get('vehicle_model'),
            estimate.get('vehicle_year', 2020),
            estimate.get('damage_severity', 'moderate')
        ))

        comp = comparables[0] if comparables else {}
        result = {
            'estimate_id': estimate_id,
            'this_total': estimate.get('total', 0),
            'comparable_count': comp.get('count', 0),
            'average_total': comp.get('avg_total', 0),
            'average_approved': comp.get('avg_approved', 0),
            'variance_percentage': 0,
            'is_low': False,
            'is_high': False,
            'alert': None
        }

        if comp.get('avg_total') and comp['avg_total'] > 0:
            this_total = estimate.get('total', 0)
            variance = ((this_total - comp['avg_total']) / comp['avg_total']) * 100
            result['variance_percentage'] = variance

            # Check for alerts
            if variance < -40:
                result['is_low'] = True
                result['alert'] = {
                    'alert_type': 'low_estimate',
                    'severity': 'critical',
                    'message': f"This estimate is {abs(variance):.0f}% below average for similar vehicles. Strongly recommend review.",
                    'trigger_data': json.dumps(result)
                }
            elif variance < -25:
                result['is_low'] = True
                result['alert'] = {
                    'alert_type': 'low_estimate',
                    'severity': 'warning',
                    'message': f"This estimate is {abs(variance):.0f}% below average for similar vehicles. Review for missed items.",
                    'trigger_data': json.dumps(result)
                }
            elif variance > 50:
                result['is_high'] = True
                result['alert'] = {
                    'alert_type': 'high_estimate',
                    'severity': 'info',
                    'message': f"This estimate is {variance:.0f}% above average. Ensure all items are justified.",
                    'trigger_data': json.dumps(result)
                }

        # Save consistency check
        self.db.execute("""
            INSERT INTO estimate_consistency_checks (
                estimate_id, comparable_count, average_comparable_total,
                this_estimate_total, variance_percentage,
                is_significantly_low, is_significantly_high,
                details, checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estimate_id,
            result['comparable_count'],
            result['average_total'],
            result['this_total'],
            result['variance_percentage'],
            1 if result['is_low'] else 0,
            1 if result['is_high'] else 0,
            json.dumps(result),
            datetime.now().isoformat()
        ))

        return result

    # =========================================================================
    # PHOTO CHECKS
    # =========================================================================

    def check_photos(self, estimate_id: int) -> List[Dict]:
        """Check for missing required photos"""
        alerts = []

        # Get photos on estimate
        photos = self.db.execute("""
            SELECT * FROM estimate_photos WHERE estimate_id = ?
        """, (estimate_id,))

        photo_types = set(p['photo_type'] for p in photos)
        panels_with_photos = set(p['panel_name'] for p in photos if p.get('panel_name'))

        # Get damaged panels
        damaged_panels = self._get_damaged_panels(estimate_id)

        # Check for panels without photos
        panels_missing_photos = []
        for panel in damaged_panels:
            if panel['panel_name'] not in panels_with_photos:
                panels_missing_photos.append(panel['panel_name'])

        if panels_missing_photos:
            alerts.append({
                'alert_type': 'photo_missing',
                'severity': 'warning',
                'message': f"Panels with damage but no photos: {', '.join(panels_missing_photos)}. Insurance may push back without documentation.",
                'trigger_data': json.dumps({'panels': panels_missing_photos})
            })

        # Check for VIN photo
        if 'vin' not in photo_types:
            alerts.append({
                'alert_type': 'photo_missing',
                'severity': 'info',
                'message': "No VIN photo included. Consider adding for complete documentation.",
                'trigger_data': json.dumps({'missing': 'vin'})
            })

        return alerts

    # =========================================================================
    # ALERT MANAGEMENT
    # =========================================================================

    def _save_alert(self, estimate_id: int, alert: Dict) -> int:
        """Save triggered alert to database"""
        result = self.db.execute("""
            INSERT INTO estimate_alerts (
                estimate_id, alert_rule_id, alert_type, severity,
                message, trigger_panel, trigger_data,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
        """, (
            estimate_id,
            alert.get('alert_rule_id'),
            alert['alert_type'],
            alert.get('severity', 'warning'),
            alert['message'],
            alert.get('trigger_panel'),
            alert.get('trigger_data'),
            datetime.now().isoformat()
        ))

        return result[0]['id']

    def get_active_alerts(self, estimate_id: int) -> List[Dict]:
        """Get all active alerts for an estimate"""
        return self.db.execute("""
            SELECT * FROM estimate_alerts
            WHERE estimate_id = ? AND status = 'active'
            ORDER BY
                CASE severity
                    WHEN 'critical' THEN 1
                    WHEN 'warning' THEN 2
                    WHEN 'info' THEN 3
                    ELSE 4
                END,
                created_at DESC
        """, (estimate_id,))

    def dismiss_alert(self, alert_id: int, reason: str = None, user_id: int = None) -> bool:
        """Mark alert as dismissed"""
        self.db.execute("""
            UPDATE estimate_alerts
            SET status = 'dismissed',
                resolved_action = ?,
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
        """, (reason, user_id, datetime.now().isoformat(), alert_id))

        return True

    def resolve_alert(self, alert_id: int, action_taken: str, user_id: int = None) -> bool:
        """Mark alert as resolved with action taken"""
        self.db.execute("""
            UPDATE estimate_alerts
            SET status = 'resolved',
                resolved_action = ?,
                resolved_by = ?,
                resolved_at = ?
            WHERE id = ?
        """, (action_taken, user_id, datetime.now().isoformat(), alert_id))

        return True

    # =========================================================================
    # ALERT RULES
    # =========================================================================

    def get_all_alert_rules(self, active_only: bool = True) -> List[Dict]:
        """Get all alert rules"""
        if active_only:
            return self.db.execute("""
                SELECT * FROM estimate_alert_rules
                WHERE is_active = 1
                ORDER BY priority
            """)
        else:
            return self.db.execute("""
                SELECT * FROM estimate_alert_rules
                ORDER BY priority
            """)

    def toggle_alert_rule(self, rule_id: int, is_active: bool) -> bool:
        """Enable or disable an alert rule"""
        self.db.execute("""
            UPDATE estimate_alert_rules
            SET is_active = ?
            WHERE id = ?
        """, (1 if is_active else 0, rule_id))

        return True

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_estimate_details(self, estimate_id: int) -> Optional[Dict]:
        """Get estimate with vehicle info"""
        result = self.db.execute("""
            SELECT e.*, v.year as vehicle_year, v.make as vehicle_make,
                   v.model as vehicle_model
            FROM estimates e
            LEFT JOIN jobs j ON j.id = e.job_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE e.id = ?
        """, (estimate_id,))

        return dict(result[0]) if result else None

    def get_alert_summary(self, estimate_id: int) -> Dict:
        """Get summary of alerts for an estimate"""
        alerts = self.get_active_alerts(estimate_id)

        return {
            'estimate_id': estimate_id,
            'total_alerts': len(alerts),
            'critical': len([a for a in alerts if a['severity'] == 'critical']),
            'warning': len([a for a in alerts if a['severity'] == 'warning']),
            'info': len([a for a in alerts if a['severity'] == 'info']),
            'alerts': alerts
        }
