"""
PDR CRM Part 20 - Dent Mapper Manager
Interactive vehicle damage mapping and dent counting

FEATURES:
- Dent counting by panel
- Dent size classification
- Visual damage mapping
- Insurance reports
- Before/after comparison
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime


class DentMapper:
    """
    Manage dent mapping and damage assessment

    Visual documentation of damage for estimates and insurance
    """

    # Dent size classifications (industry standard)
    DENT_SIZES = {
        'DIME': {
            'name': 'Dime Size',
            'diameter_inches': 0.7,
            'typical_cost': 25.00,
            'difficulty': 'EASY'
        },
        'NICKEL': {
            'name': 'Nickel Size',
            'diameter_inches': 0.85,
            'typical_cost': 35.00,
            'difficulty': 'EASY'
        },
        'QUARTER': {
            'name': 'Quarter Size',
            'diameter_inches': 1.0,
            'typical_cost': 50.00,
            'difficulty': 'MEDIUM'
        },
        'HALF_DOLLAR': {
            'name': 'Half Dollar Size',
            'diameter_inches': 1.2,
            'typical_cost': 75.00,
            'difficulty': 'MEDIUM'
        },
        'GOLF_BALL': {
            'name': 'Golf Ball Size',
            'diameter_inches': 1.68,
            'typical_cost': 100.00,
            'difficulty': 'HARD'
        },
        'BASEBALL': {
            'name': 'Baseball Size',
            'diameter_inches': 2.9,
            'typical_cost': 150.00,
            'difficulty': 'VERY_HARD'
        }
    }

    # Panel types (matching PhotoManager)
    PANELS = [
        'HOOD', 'ROOF', 'TRUNK',
        'FRONT_BUMPER', 'REAR_BUMPER',
        'DRIVER_DOOR', 'PASSENGER_DOOR',
        'DRIVER_REAR_DOOR', 'PASSENGER_REAR_DOOR',
        'DRIVER_FENDER', 'PASSENGER_FENDER',
        'DRIVER_QUARTER', 'PASSENGER_QUARTER',
        'WINDSHIELD', 'REAR_GLASS'
    ]

    def __init__(self, db):
        """Initialize dent mapper with database instance"""
        self.db = db
        self._ensure_dent_tables()

    def _ensure_dent_tables(self):
        """Ensure dent mapping tables exist"""
        # Create dent_maps table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dent_maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                map_type TEXT DEFAULT 'INITIAL',
                status TEXT DEFAULT 'ACTIVE',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                updated_at TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Create dents table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS dents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dent_map_id INTEGER NOT NULL,
                panel TEXT NOT NULL,
                dent_size TEXT NOT NULL,
                x_position REAL,
                y_position REAL,
                severity INTEGER DEFAULT 3,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dent_map_id) REFERENCES dent_maps(id)
            )
        """)

    # ========================================================================
    # DENT MAPPING
    # ========================================================================

    def create_dent_map(
        self,
        job_id: int,
        map_type: str = 'INITIAL',
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create new dent map for job

        Args:
            job_id: Job ID
            map_type: INITIAL (before), PROGRESS, FINAL (after)
            notes: Optional notes
            created_by: Who created the map

        Returns:
            Dent map ID
        """
        result = self.db.execute("""
            INSERT INTO dent_maps (
                job_id, map_type, status, notes, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            map_type,
            'ACTIVE',
            notes,
            datetime.now().isoformat(),
            created_by
        ))

        map_id = result[0]['id']

        print(f"[OK] Created dent map for job {job_id}")
        print(f"     Type: {map_type}")
        print(f"     Map ID: {map_id}")

        return map_id

    def add_dent(
        self,
        map_id: int,
        panel: str,
        dent_size: str,
        x_position: Optional[float] = None,
        y_position: Optional[float] = None,
        severity: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Add dent to map

        Args:
            map_id: Dent map ID
            panel: Panel location
            dent_size: DIME, NICKEL, QUARTER, HALF_DOLLAR, GOLF_BALL, BASEBALL
            x_position: X coordinate on panel (0-100%)
            y_position: Y coordinate on panel (0-100%)
            severity: Severity 1-5 (depth/difficulty)
            notes: Additional notes

        Returns:
            Dent ID
        """
        if panel not in self.PANELS:
            raise ValueError(f"Invalid panel. Must be: {self.PANELS}")

        if dent_size not in self.DENT_SIZES:
            raise ValueError(f"Invalid dent_size. Must be: {list(self.DENT_SIZES.keys())}")

        result = self.db.execute("""
            INSERT INTO dents (
                dent_map_id, panel, dent_size,
                x_position, y_position, severity,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            map_id,
            panel,
            dent_size,
            x_position,
            y_position,
            severity or 3,
            notes,
            datetime.now().isoformat()
        ))

        dent_id = result[0]['id']

        return dent_id

    def add_dents_bulk(
        self,
        map_id: int,
        panel: str,
        dent_counts: Dict[str, int]
    ) -> int:
        """
        Add multiple dents at once (when exact positions unknown)

        Args:
            map_id: Dent map ID
            panel: Panel location
            dent_counts: Dictionary of size -> count

        Returns:
            Number of dents added
        """
        total_added = 0

        for dent_size, count in dent_counts.items():
            for _ in range(count):
                self.add_dent(
                    map_id=map_id,
                    panel=panel,
                    dent_size=dent_size
                )
                total_added += 1

        print(f"[OK] Added {total_added} dents to {panel}")
        for size, count in dent_counts.items():
            print(f"     {size}: {count}")

        return total_added

    def remove_dent(self, dent_id: int) -> bool:
        """Remove dent from map"""
        self.db.execute("""
            DELETE FROM dents WHERE id = ?
        """, (dent_id,))

        return True

    def clear_dents(self, map_id: int, panel: Optional[str] = None) -> int:
        """
        Clear dents from map

        Args:
            map_id: Dent map ID
            panel: Optional panel filter (clear all if not specified)

        Returns:
            Number of dents removed
        """
        if panel:
            result = self.db.execute("""
                DELETE FROM dents
                WHERE dent_map_id = ? AND panel = ?
            """, (map_id, panel))
        else:
            result = self.db.execute("""
                DELETE FROM dents WHERE dent_map_id = ?
            """, (map_id,))

        count = result[0]['rowcount'] if result else 0
        print(f"[OK] Cleared {count} dents from map")

        return count

    # ========================================================================
    # DENT COUNTING & ANALYSIS
    # ========================================================================

    def get_dent_count(
        self,
        map_id: int,
        panel: Optional[str] = None,
        dent_size: Optional[str] = None
    ) -> int:
        """
        Get dent count

        Args:
            map_id: Dent map ID
            panel: Filter by panel (optional)
            dent_size: Filter by size (optional)

        Returns:
            Total dent count
        """
        query = "SELECT COUNT(*) as count FROM dents WHERE dent_map_id = ?"
        params = [map_id]

        if panel:
            query += " AND panel = ?"
            params.append(panel)

        if dent_size:
            query += " AND dent_size = ?"
            params.append(dent_size)

        result = self.db.execute(query, tuple(params))

        return result[0]['count'] if result else 0

    def get_dents(self, map_id: int) -> List[Dict[str, Any]]:
        """Get all dents for a map"""
        return self.db.execute("""
            SELECT * FROM dents
            WHERE dent_map_id = ?
            ORDER BY panel, dent_size
        """, (map_id,))

    def get_dent_breakdown(self, map_id: int) -> Dict[str, Any]:
        """
        Get complete dent breakdown

        Returns counts by panel and size
        """
        dents = self.db.execute("""
            SELECT * FROM dents WHERE dent_map_id = ?
        """, (map_id,))

        breakdown = {
            'total_dents': len(dents),
            'by_panel': {},
            'by_size': {},
            'by_panel_and_size': {},
            'severity_avg': 0.0
        }

        total_severity = 0

        for dent in dents:
            panel = dent['panel']
            size = dent['dent_size']
            severity = dent.get('severity') or 3

            # By panel
            breakdown['by_panel'][panel] = breakdown['by_panel'].get(panel, 0) + 1

            # By size
            breakdown['by_size'][size] = breakdown['by_size'].get(size, 0) + 1

            # By panel and size
            key = f"{panel}_{size}"
            breakdown['by_panel_and_size'][key] = breakdown['by_panel_and_size'].get(key, 0) + 1

            total_severity += severity

        if len(dents) > 0:
            breakdown['severity_avg'] = total_severity / len(dents)

        return breakdown

    def get_panel_summary(self, map_id: int) -> Dict[str, Dict[str, int]]:
        """
        Get dent summary organized by panel

        Returns dictionary with panel -> {size: count} structure
        """
        dents = self.get_dents(map_id)

        summary = {}
        for dent in dents:
            panel = dent['panel']
            size = dent['dent_size']

            if panel not in summary:
                summary[panel] = {}

            summary[panel][size] = summary[panel].get(size, 0) + 1

        return summary

    def calculate_repair_estimate(self, map_id: int) -> Dict[str, Any]:
        """
        Calculate repair estimate based on dent map

        Uses standard pricing per dent size
        """
        dents = self.db.execute("""
            SELECT * FROM dents WHERE dent_map_id = ?
        """, (map_id,))

        estimate = {
            'total_dents': len(dents),
            'by_size': {},
            'by_panel': {},
            'total_cost': 0.0,
            'estimated_hours': 0.0,
            'difficulty_breakdown': {'EASY': 0, 'MEDIUM': 0, 'HARD': 0, 'VERY_HARD': 0}
        }

        for dent in dents:
            size = dent['dent_size']
            panel = dent['panel']
            size_info = self.DENT_SIZES[size]

            # By size
            if size not in estimate['by_size']:
                estimate['by_size'][size] = {
                    'count': 0,
                    'cost_per_dent': size_info['typical_cost'],
                    'total_cost': 0.0
                }

            estimate['by_size'][size]['count'] += 1
            estimate['by_size'][size]['total_cost'] += size_info['typical_cost']
            estimate['total_cost'] += size_info['typical_cost']

            # By panel
            if panel not in estimate['by_panel']:
                estimate['by_panel'][panel] = {
                    'count': 0,
                    'total_cost': 0.0
                }

            estimate['by_panel'][panel]['count'] += 1
            estimate['by_panel'][panel]['total_cost'] += size_info['typical_cost']

            # Difficulty
            estimate['difficulty_breakdown'][size_info['difficulty']] += 1

        # Estimate hours (rough: 10 dents per hour average)
        estimate['estimated_hours'] = len(dents) / 10.0

        return estimate

    # ========================================================================
    # DAMAGE REPORTS
    # ========================================================================

    def generate_damage_report(self, map_id: int) -> str:
        """
        Generate printable damage report

        Returns formatted text report
        """
        dent_map = self.get_dent_map(map_id)
        if not dent_map:
            return "Dent map not found"

        breakdown = self.get_dent_breakdown(map_id)
        estimate = self.calculate_repair_estimate(map_id)
        panel_summary = self.get_panel_summary(map_id)

        # Get job info
        job_result = self.db.execute("""
            SELECT j.*, c.first_name, c.last_name, v.year, v.make, v.model
            FROM jobs j
            LEFT JOIN customers c ON c.id = j.customer_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (dent_map['job_id'],))

        job = job_result[0] if job_result else {}

        report = []
        report.append("=" * 70)
        report.append("VEHICLE DAMAGE ASSESSMENT REPORT")
        report.append("=" * 70)
        report.append("")

        # Job Info
        report.append("JOB INFORMATION")
        report.append("-" * 70)
        report.append(f"  Job Number:  {job.get('job_number', 'N/A')}")
        report.append(f"  Customer:    {job.get('first_name', '')} {job.get('last_name', '')}")
        report.append(f"  Vehicle:     {job.get('year', '')} {job.get('make', '')} {job.get('model', '')}")
        report.append(f"  Map Type:    {dent_map['map_type']}")
        report.append(f"  Created:     {dent_map['created_at']}")
        report.append("")

        # Summary
        report.append("DAMAGE SUMMARY")
        report.append("-" * 70)
        report.append(f"  Total Dents:        {breakdown['total_dents']}")
        report.append(f"  Panels Affected:    {len(breakdown['by_panel'])}")
        report.append(f"  Avg Severity:       {breakdown['severity_avg']:.1f}/5")
        report.append("")

        # By Size
        report.append("DENTS BY SIZE")
        report.append("-" * 70)
        for size in ['DIME', 'NICKEL', 'QUARTER', 'HALF_DOLLAR', 'GOLF_BALL', 'BASEBALL']:
            count = breakdown['by_size'].get(size, 0)
            if count > 0:
                size_info = self.DENT_SIZES[size]
                cost = count * size_info['typical_cost']
                report.append(f"  {size_info['name']:20s}: {count:3d} dents  @ ${size_info['typical_cost']:6.2f} = ${cost:8.2f}")
        report.append("")

        # By Panel
        report.append("DENTS BY PANEL")
        report.append("-" * 70)
        for panel in sorted(breakdown['by_panel'].keys()):
            count = breakdown['by_panel'][panel]
            panel_cost = estimate['by_panel'].get(panel, {}).get('total_cost', 0)
            report.append(f"  {panel:20s}: {count:3d} dents  = ${panel_cost:8.2f}")

            # Show size breakdown for this panel
            if panel in panel_summary:
                for size, size_count in sorted(panel_summary[panel].items()):
                    size_name = self.DENT_SIZES[size]['name']
                    report.append(f"    - {size_name}: {size_count}")
        report.append("")

        # Estimate
        report.append("REPAIR ESTIMATE")
        report.append("-" * 70)
        report.append(f"  Total Dents:        {estimate['total_dents']}")
        report.append(f"  Estimated Hours:    {estimate['estimated_hours']:.1f}")
        report.append(f"  Estimated Cost:     ${estimate['total_cost']:,.2f}")
        report.append("")

        # Difficulty
        report.append("DIFFICULTY BREAKDOWN")
        report.append("-" * 70)
        for diff in ['EASY', 'MEDIUM', 'HARD', 'VERY_HARD']:
            count = estimate['difficulty_breakdown'][diff]
            if count > 0:
                report.append(f"  {diff:15s}: {count:3d} dents")
        report.append("")

        report.append("=" * 70)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        report.append("=" * 70)

        return "\n".join(report)

    def compare_before_after(
        self,
        before_map_id: int,
        after_map_id: int
    ) -> Dict[str, Any]:
        """
        Compare before and after dent maps

        Shows dent removal progress
        """
        before = self.get_dent_breakdown(before_map_id)
        after = self.get_dent_breakdown(after_map_id)

        comparison = {
            'before_total': before['total_dents'],
            'after_total': after['total_dents'],
            'dents_removed': before['total_dents'] - after['total_dents'],
            'percent_complete': 0.0,
            'by_panel': {},
            'by_size': {}
        }

        if before['total_dents'] > 0:
            comparison['percent_complete'] = (comparison['dents_removed'] / before['total_dents']) * 100

        # Compare by panel
        all_panels = set(list(before['by_panel'].keys()) + list(after['by_panel'].keys()))

        for panel in all_panels:
            before_count = before['by_panel'].get(panel, 0)
            after_count = after['by_panel'].get(panel, 0)

            comparison['by_panel'][panel] = {
                'before': before_count,
                'after': after_count,
                'removed': before_count - after_count,
                'percent': ((before_count - after_count) / before_count * 100) if before_count > 0 else 0
            }

        # Compare by size
        all_sizes = set(list(before['by_size'].keys()) + list(after['by_size'].keys()))

        for size in all_sizes:
            before_count = before['by_size'].get(size, 0)
            after_count = after['by_size'].get(size, 0)

            comparison['by_size'][size] = {
                'before': before_count,
                'after': after_count,
                'removed': before_count - after_count
            }

        return comparison

    def generate_comparison_report(
        self,
        before_map_id: int,
        after_map_id: int
    ) -> str:
        """Generate before/after comparison report"""
        comparison = self.compare_before_after(before_map_id, after_map_id)

        report = []
        report.append("=" * 70)
        report.append("BEFORE/AFTER COMPARISON REPORT")
        report.append("=" * 70)
        report.append("")

        report.append("SUMMARY")
        report.append("-" * 70)
        report.append(f"  Before:           {comparison['before_total']} dents")
        report.append(f"  After:            {comparison['after_total']} dents")
        report.append(f"  Removed:          {comparison['dents_removed']} dents")
        report.append(f"  Progress:         {comparison['percent_complete']:.1f}% complete")
        report.append("")

        report.append("BY PANEL")
        report.append("-" * 70)
        for panel, data in sorted(comparison['by_panel'].items()):
            if data['before'] > 0:
                report.append(f"  {panel:20s}: {data['before']:3d} -> {data['after']:3d} ({data['removed']} removed, {data['percent']:.0f}%)")
        report.append("")

        report.append("BY SIZE")
        report.append("-" * 70)
        for size, data in sorted(comparison['by_size'].items()):
            if data['before'] > 0:
                size_name = self.DENT_SIZES[size]['name']
                report.append(f"  {size_name:20s}: {data['before']:3d} -> {data['after']:3d} ({data['removed']} removed)")
        report.append("")

        report.append("=" * 70)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        report.append("=" * 70)

        return "\n".join(report)

    # ========================================================================
    # HEATMAP DATA
    # ========================================================================

    def get_heatmap_data(self, map_id: int) -> Dict[str, Any]:
        """
        Get data for visual heatmap display

        Returns severity/density data by panel
        """
        breakdown = self.get_dent_breakdown(map_id)
        estimate = self.calculate_repair_estimate(map_id)

        heatmap = {
            'panels': {},
            'max_count': 0,
            'max_severity': 0
        }

        for panel in self.PANELS:
            count = breakdown['by_panel'].get(panel, 0)
            cost = estimate['by_panel'].get(panel, {}).get('total_cost', 0)

            # Calculate severity score (weighted by dent size)
            severity_score = 0
            panel_dents = self.db.execute("""
                SELECT dent_size, severity FROM dents
                WHERE dent_map_id = ? AND panel = ?
            """, (map_id, panel))

            for dent in panel_dents:
                size_info = self.DENT_SIZES[dent['dent_size']]
                weight = {'EASY': 1, 'MEDIUM': 2, 'HARD': 3, 'VERY_HARD': 4}[size_info['difficulty']]
                severity_score += weight * (dent.get('severity') or 3)

            heatmap['panels'][panel] = {
                'count': count,
                'cost': cost,
                'severity_score': severity_score,
                'intensity': 0  # Will be calculated after max is known
            }

            if count > heatmap['max_count']:
                heatmap['max_count'] = count

            if severity_score > heatmap['max_severity']:
                heatmap['max_severity'] = severity_score

        # Calculate intensity (0-1) for each panel
        for panel in heatmap['panels']:
            if heatmap['max_severity'] > 0:
                heatmap['panels'][panel]['intensity'] = (
                    heatmap['panels'][panel]['severity_score'] / heatmap['max_severity']
                )

        return heatmap

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def get_dent_map(self, map_id: int) -> Optional[Dict[str, Any]]:
        """Get dent map details"""
        result = self.db.execute(
            "SELECT * FROM dent_maps WHERE id = ?",
            (map_id,)
        )

        return dict(result[0]) if result else None

    def get_job_dent_maps(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all dent maps for job"""
        return self.db.execute("""
            SELECT * FROM dent_maps
            WHERE job_id = ?
            ORDER BY created_at
        """, (job_id,))

    def update_dent_map(
        self,
        map_id: int,
        status: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """Update dent map"""
        updates = []
        params = []

        if status:
            updates.append("status = ?")
            params.append(status)

        if notes:
            updates.append("notes = ?")
            params.append(notes)

        if not updates:
            return False

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(map_id)

        self.db.execute(f"""
            UPDATE dent_maps
            SET {', '.join(updates)}
            WHERE id = ?
        """, tuple(params))

        return True

    def delete_dent_map(self, map_id: int) -> bool:
        """Delete dent map and all its dents"""
        # Delete dents first
        self.db.execute("DELETE FROM dents WHERE dent_map_id = ?", (map_id,))

        # Delete map
        self.db.execute("DELETE FROM dent_maps WHERE id = ?", (map_id,))

        return True
