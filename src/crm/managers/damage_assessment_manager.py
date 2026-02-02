"""
PDR CRM Part 21 - Damage Assessment Manager
Comprehensive vehicle damage assessment and reporting

FEATURES:
- Panel-by-panel inspection
- Damage severity ratings
- Repair difficulty scoring
- Assessment reports
- Customer-friendly summaries
- Before/after comparison
"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime


class DamageAssessmentManager:
    """
    Manage comprehensive damage assessments

    Complete vehicle inspection and documentation
    """

    # Damage severity levels
    SEVERITY_LEVELS = {
        1: {'name': 'Minor', 'description': 'Light surface damage, easy repair', 'color': '#10b981'},
        2: {'name': 'Light', 'description': 'Noticeable but repairable', 'color': '#84cc16'},
        3: {'name': 'Moderate', 'description': 'Significant damage, standard repair', 'color': '#f59e0b'},
        4: {'name': 'Heavy', 'description': 'Extensive damage, complex repair', 'color': '#ef4444'},
        5: {'name': 'Severe', 'description': 'Major damage, difficult repair', 'color': '#991b1b'}
    }

    # Repair difficulty ratings
    DIFFICULTY_RATINGS = {
        'EASY': {'name': 'Easy', 'multiplier': 1.0, 'description': 'Standard PDR techniques'},
        'MEDIUM': {'name': 'Medium', 'multiplier': 1.3, 'description': 'Requires careful work'},
        'HARD': {'name': 'Hard', 'multiplier': 1.7, 'description': 'Complex access or multiple steps'},
        'VERY_HARD': {'name': 'Very Hard', 'multiplier': 2.2, 'description': 'Extreme difficulty, may need panel removal'}
    }

    # Assessment types
    ASSESSMENT_TYPES = [
        'INITIAL',      # First inspection
        'DETAILED',     # Comprehensive assessment
        'PROGRESS',     # During repair
        'FINAL',        # Post-repair verification
        'INSURANCE'     # For insurance claim
    ]

    # Damage types
    DAMAGE_TYPES = [
        'HAIL',
        'DOOR_DING',
        'CREASE',
        'LARGE_DENT',
        'SCRATCH',
        'PAINT_DAMAGE',
        'BODY_LINE_DAMAGE',
        'STRUCTURAL'
    ]

    # Panel types (consistent with DentMapper and PhotoManager)
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
        """Initialize damage assessment manager with database instance"""
        self.db = db
        self._ensure_assessment_tables()

    def _ensure_assessment_tables(self):
        """Ensure damage assessment tables exist"""
        # Create damage_assessments table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS damage_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                assessment_type TEXT NOT NULL,
                assessed_by TEXT,
                notes TEXT,
                final_notes TEXT,
                status TEXT DEFAULT 'IN_PROGRESS',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                dent_map_id INTEGER,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Create panel_assessments table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS panel_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assessment_id INTEGER NOT NULL,
                panel TEXT NOT NULL,
                damage_type TEXT NOT NULL,
                severity INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                dent_count INTEGER,
                estimated_time_minutes INTEGER,
                estimated_cost REAL,
                notes TEXT,
                photo_ids TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assessment_id) REFERENCES damage_assessments(id)
            )
        """)

    # ========================================================================
    # ASSESSMENT CREATION
    # ========================================================================

    def create_assessment(
        self,
        job_id: int,
        assessment_type: str = 'INITIAL',
        assessed_by: Optional[str] = None,
        notes: Optional[str] = None,
        dent_map_id: Optional[int] = None
    ) -> int:
        """
        Create new damage assessment

        Args:
            job_id: Job ID
            assessment_type: INITIAL, DETAILED, PROGRESS, FINAL, INSURANCE
            assessed_by: Who performed assessment
            notes: Assessment notes
            dent_map_id: Optional linked dent map

        Returns:
            Assessment ID
        """
        if assessment_type not in self.ASSESSMENT_TYPES:
            raise ValueError(f"Invalid assessment_type. Must be: {self.ASSESSMENT_TYPES}")

        result = self.db.execute("""
            INSERT INTO damage_assessments (
                job_id, assessment_type, assessed_by,
                notes, created_at, status, dent_map_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            assessment_type,
            assessed_by,
            notes,
            datetime.now().isoformat(),
            'IN_PROGRESS',
            dent_map_id
        ))

        assessment_id = result[0]['id']

        print(f"[OK] Created {assessment_type} assessment for job {job_id}")
        print(f"     Assessment ID: {assessment_id}")

        return assessment_id

    def add_panel_assessment(
        self,
        assessment_id: int,
        panel: str,
        damage_type: str,
        severity: int,
        difficulty: str,
        dent_count: Optional[int] = None,
        estimated_time_minutes: Optional[int] = None,
        estimated_cost: Optional[float] = None,
        notes: Optional[str] = None,
        photo_ids: Optional[List[int]] = None
    ) -> int:
        """
        Add panel assessment to overall assessment

        Args:
            assessment_id: Assessment ID
            panel: Panel name (HOOD, ROOF, etc.)
            damage_type: Type of damage
            severity: 1-5 severity rating
            difficulty: EASY, MEDIUM, HARD, VERY_HARD
            dent_count: Number of dents on panel
            estimated_time_minutes: Time estimate
            estimated_cost: Cost estimate
            notes: Panel-specific notes
            photo_ids: List of photo IDs for this panel

        Returns:
            Panel assessment ID
        """
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(f"Severity must be 1-5")

        if difficulty not in self.DIFFICULTY_RATINGS:
            raise ValueError(f"Invalid difficulty. Must be: {list(self.DIFFICULTY_RATINGS.keys())}")

        if damage_type not in self.DAMAGE_TYPES:
            raise ValueError(f"Invalid damage_type. Must be: {self.DAMAGE_TYPES}")

        if panel not in self.PANELS:
            raise ValueError(f"Invalid panel. Must be: {self.PANELS}")

        result = self.db.execute("""
            INSERT INTO panel_assessments (
                assessment_id, panel, damage_type,
                severity, difficulty, dent_count,
                estimated_time_minutes, estimated_cost,
                notes, photo_ids, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assessment_id,
            panel,
            damage_type,
            severity,
            difficulty,
            dent_count,
            estimated_time_minutes,
            estimated_cost,
            notes,
            json.dumps(photo_ids) if photo_ids else None,
            datetime.now().isoformat()
        ))

        panel_assessment_id = result[0]['id']

        severity_name = self.SEVERITY_LEVELS[severity]['name']

        print(f"[OK] Added {panel} assessment")
        print(f"     Damage: {damage_type} ({severity_name})")
        print(f"     Difficulty: {difficulty}")
        if dent_count:
            print(f"     Dents: {dent_count}")
        if estimated_cost:
            print(f"     Est. cost: ${estimated_cost:.2f}")

        return panel_assessment_id

    def update_panel_assessment(
        self,
        panel_assessment_id: int,
        **updates
    ) -> bool:
        """Update panel assessment"""
        allowed_fields = [
            'severity', 'difficulty', 'dent_count',
            'estimated_time_minutes', 'estimated_cost', 'notes'
        ]

        set_clauses = []
        values = []

        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if not set_clauses:
            return False

        values.append(panel_assessment_id)

        self.db.execute(f"""
            UPDATE panel_assessments
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """, tuple(values))

        return True

    def complete_assessment(
        self,
        assessment_id: int,
        final_notes: Optional[str] = None
    ) -> bool:
        """
        Mark assessment as complete

        Args:
            assessment_id: Assessment ID
            final_notes: Final assessment notes
        """
        self.db.execute("""
            UPDATE damage_assessments
            SET status = 'COMPLETE',
                completed_at = ?,
                final_notes = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            final_notes,
            assessment_id
        ))

        print(f"[OK] Assessment {assessment_id} marked complete")

        return True

    # ========================================================================
    # ASSESSMENT RETRIEVAL
    # ========================================================================

    def get_assessment(self, assessment_id: int) -> Optional[Dict[str, Any]]:
        """Get assessment details"""
        result = self.db.execute("""
            SELECT * FROM damage_assessments WHERE id = ?
        """, (assessment_id,))

        return dict(result[0]) if result else None

    def get_panel_assessments(self, assessment_id: int) -> List[Dict[str, Any]]:
        """Get all panel assessments for assessment"""
        return self.db.execute("""
            SELECT * FROM panel_assessments
            WHERE assessment_id = ?
            ORDER BY panel
        """, (assessment_id,))

    def get_panel_assessment(self, panel_assessment_id: int) -> Optional[Dict[str, Any]]:
        """Get single panel assessment"""
        result = self.db.execute("""
            SELECT * FROM panel_assessments WHERE id = ?
        """, (panel_assessment_id,))

        return dict(result[0]) if result else None

    def get_job_assessments(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all assessments for job"""
        return self.db.execute("""
            SELECT * FROM damage_assessments
            WHERE job_id = ?
            ORDER BY created_at DESC
        """, (job_id,))

    def get_latest_assessment(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get most recent assessment for job"""
        result = self.db.execute("""
            SELECT * FROM damage_assessments
            WHERE job_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (job_id,))

        return dict(result[0]) if result else None

    # ========================================================================
    # ASSESSMENT ANALYSIS
    # ========================================================================

    def get_assessment_summary(self, assessment_id: int) -> Dict[str, Any]:
        """
        Get assessment summary with totals

        Returns comprehensive summary
        """
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return {}

        panels = self.get_panel_assessments(assessment_id)

        summary = {
            'assessment_id': assessment_id,
            'assessment_type': assessment['assessment_type'],
            'assessed_by': assessment.get('assessed_by'),
            'created_at': assessment['created_at'],
            'completed_at': assessment.get('completed_at'),
            'status': assessment['status'],
            'notes': assessment.get('notes'),
            'final_notes': assessment.get('final_notes'),
            'total_panels': len(panels),
            'total_dents': 0,
            'total_time_minutes': 0,
            'total_cost': 0.0,
            'severity_breakdown': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            'difficulty_breakdown': {},
            'damage_type_breakdown': {},
            'panels': [],
            'average_severity': 0.0
        }

        for panel in panels:
            # Totals
            if panel.get('dent_count'):
                summary['total_dents'] += panel['dent_count']

            if panel.get('estimated_time_minutes'):
                summary['total_time_minutes'] += panel['estimated_time_minutes']

            if panel.get('estimated_cost'):
                summary['total_cost'] += panel['estimated_cost']

            # Severity
            summary['severity_breakdown'][panel['severity']] += 1

            # Difficulty
            diff = panel['difficulty']
            summary['difficulty_breakdown'][diff] = summary['difficulty_breakdown'].get(diff, 0) + 1

            # Damage type
            dtype = panel['damage_type']
            summary['damage_type_breakdown'][dtype] = summary['damage_type_breakdown'].get(dtype, 0) + 1

            # Panel info
            summary['panels'].append({
                'id': panel['id'],
                'panel': panel['panel'],
                'damage_type': panel['damage_type'],
                'severity': panel['severity'],
                'difficulty': panel['difficulty'],
                'dent_count': panel.get('dent_count'),
                'estimated_time_minutes': panel.get('estimated_time_minutes'),
                'estimated_cost': panel.get('estimated_cost'),
                'notes': panel.get('notes')
            })

        # Average severity
        if summary['total_panels'] > 0:
            total_severity = sum(s * count for s, count in summary['severity_breakdown'].items())
            summary['average_severity'] = total_severity / summary['total_panels']

        return summary

    def calculate_difficulty_multiplier(self, assessment_id: int) -> float:
        """
        Calculate overall difficulty multiplier

        Returns weighted average difficulty
        """
        panels = self.get_panel_assessments(assessment_id)

        if not panels:
            return 1.0

        total_multiplier = 0.0
        total_weight = 0

        for panel in panels:
            difficulty = panel['difficulty']
            multiplier = self.DIFFICULTY_RATINGS[difficulty]['multiplier']
            weight = panel.get('dent_count') or 1

            total_multiplier += multiplier * weight
            total_weight += weight

        if total_weight == 0:
            return 1.0

        return total_multiplier / total_weight

    def get_severity_distribution(self, assessment_id: int) -> Dict[str, Any]:
        """Get severity distribution with details"""
        summary = self.get_assessment_summary(assessment_id)

        distribution = {
            'total_panels': summary['total_panels'],
            'average_severity': summary['average_severity'],
            'levels': {}
        }

        for level, count in summary['severity_breakdown'].items():
            if count > 0:
                info = self.SEVERITY_LEVELS[level]
                distribution['levels'][level] = {
                    'name': info['name'],
                    'description': info['description'],
                    'color': info['color'],
                    'count': count,
                    'percentage': (count / summary['total_panels'] * 100) if summary['total_panels'] > 0 else 0
                }

        return distribution

    # ========================================================================
    # REPORT GENERATION
    # ========================================================================

    def generate_assessment_report(self, assessment_id: int) -> str:
        """
        Generate detailed assessment report

        Returns formatted text report for printing/documentation
        """
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return "Assessment not found"

        panels = self.get_panel_assessments(assessment_id)
        summary = self.get_assessment_summary(assessment_id)

        # Get job info
        job_result = self.db.execute("""
            SELECT j.*, c.first_name, c.last_name, v.year, v.make, v.model
            FROM jobs j
            LEFT JOIN customers c ON c.id = j.customer_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (assessment['job_id'],))

        job = job_result[0] if job_result else {}

        report = []
        report.append("=" * 70)
        report.append("DAMAGE ASSESSMENT REPORT")
        report.append("=" * 70)
        report.append("")

        # Job & Vehicle Info
        report.append("JOB INFORMATION")
        report.append("-" * 70)
        report.append(f"  Job Number:        {job.get('job_number', 'N/A')}")
        report.append(f"  Customer:          {job.get('first_name', '')} {job.get('last_name', '')}")
        report.append(f"  Vehicle:           {job.get('year', '')} {job.get('make', '')} {job.get('model', '')}")
        report.append("")

        # Assessment Info
        report.append("ASSESSMENT DETAILS")
        report.append("-" * 70)
        report.append(f"  Assessment ID:     {assessment_id}")
        report.append(f"  Type:              {assessment['assessment_type']}")
        report.append(f"  Assessed By:       {assessment.get('assessed_by', 'N/A')}")
        report.append(f"  Created:           {assessment['created_at']}")
        report.append(f"  Status:            {assessment['status']}")
        if assessment.get('completed_at'):
            report.append(f"  Completed:         {assessment['completed_at']}")
        report.append("")

        # Summary
        report.append("DAMAGE SUMMARY")
        report.append("-" * 70)
        report.append(f"  Panels Assessed:   {summary['total_panels']}")
        report.append(f"  Total Dents:       {summary['total_dents']}")
        report.append(f"  Average Severity:  {summary['average_severity']:.1f} / 5.0")
        report.append(f"  Total Time Est:    {summary['total_time_minutes']} min ({summary['total_time_minutes']/60:.1f} hrs)")
        report.append(f"  Total Cost Est:    ${summary['total_cost']:,.2f}")
        report.append("")

        # Severity Breakdown
        report.append("SEVERITY BREAKDOWN")
        report.append("-" * 70)
        for level in [1, 2, 3, 4, 5]:
            count = summary['severity_breakdown'][level]
            if count > 0:
                info = self.SEVERITY_LEVELS[level]
                report.append(f"  Level {level} ({info['name']:8s}):  {count} panels - {info['description']}")
        report.append("")

        # Difficulty Breakdown
        report.append("DIFFICULTY BREAKDOWN")
        report.append("-" * 70)
        for diff in ['EASY', 'MEDIUM', 'HARD', 'VERY_HARD']:
            count = summary['difficulty_breakdown'].get(diff, 0)
            if count > 0:
                info = self.DIFFICULTY_RATINGS[diff]
                report.append(f"  {info['name']:12s} ({info['multiplier']}x):  {count} panels")
        report.append("")

        # Panel-by-Panel Details
        report.append("PANEL-BY-PANEL ASSESSMENT")
        report.append("-" * 70)

        for panel in panels:
            severity_info = self.SEVERITY_LEVELS[panel['severity']]
            difficulty_info = self.DIFFICULTY_RATINGS[panel['difficulty']]
            panel_name = panel['panel'].replace('_', ' ').title()

            report.append("")
            report.append(f"  {panel_name}")
            report.append(f"  " + "-" * 40)
            report.append(f"    Damage Type:      {panel['damage_type']}")
            report.append(f"    Severity:         {severity_info['name']} (Level {panel['severity']})")
            report.append(f"    Difficulty:       {difficulty_info['name']}")
            if panel.get('dent_count'):
                report.append(f"    Dent Count:       {panel['dent_count']}")
            if panel.get('estimated_time_minutes'):
                report.append(f"    Est. Time:        {panel['estimated_time_minutes']} min")
            if panel.get('estimated_cost'):
                report.append(f"    Est. Cost:        ${panel['estimated_cost']:.2f}")
            if panel.get('notes'):
                report.append(f"    Notes:            {panel['notes']}")

        report.append("")

        # Assessment Notes
        if assessment.get('notes'):
            report.append("ASSESSMENT NOTES")
            report.append("-" * 70)
            report.append(f"  {assessment['notes']}")
            report.append("")

        if assessment.get('final_notes'):
            report.append("FINAL NOTES")
            report.append("-" * 70)
            report.append(f"  {assessment['final_notes']}")
            report.append("")

        report.append("=" * 70)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")
        report.append("=" * 70)

        return "\n".join(report)

    def generate_customer_summary(self, assessment_id: int) -> str:
        """
        Generate customer-friendly summary

        Simplified, non-technical version
        """
        summary = self.get_assessment_summary(assessment_id)
        if not summary:
            return "Assessment not found"

        # Get job info
        assessment = self.get_assessment(assessment_id)
        job_result = self.db.execute("""
            SELECT j.*, v.year, v.make, v.model
            FROM jobs j
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (assessment['job_id'],))

        job = job_result[0] if job_result else {}

        lines = []
        lines.append("=" * 50)
        lines.append("DAMAGE ASSESSMENT SUMMARY")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Vehicle: {job.get('year', '')} {job.get('make', '')} {job.get('model', '')}")
        lines.append("")
        lines.append("Your vehicle has been inspected and assessed for repair.")
        lines.append("")
        lines.append("DAMAGE FOUND:")
        lines.append(f"  - {summary['total_panels']} panels affected")
        lines.append(f"  - {summary['total_dents']} total dents identified")
        lines.append("")
        lines.append("REPAIR ESTIMATE:")
        lines.append(f"  - Time: Approximately {summary['total_time_minutes']/60:.1f} hours")
        lines.append(f"  - Cost: ${summary['total_cost']:,.2f}")
        lines.append("")
        lines.append("DAMAGED PANELS:")

        for panel_info in summary['panels']:
            panel_name = panel_info['panel'].replace('_', ' ').title()
            severity = self.SEVERITY_LEVELS[panel_info['severity']]['name']

            line = f"  - {panel_name}"
            if panel_info.get('dent_count'):
                line += f" - {panel_info['dent_count']} dents"
            line += f" ({severity} damage)"
            lines.append(line)

        lines.append("")
        lines.append("NEXT STEPS:")
        lines.append("  1. Review this assessment")
        lines.append("  2. Approve the estimate")
        lines.append("  3. Schedule your repair")
        lines.append("")
        lines.append("Questions? Contact us anytime!")
        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    def generate_insurance_report(self, assessment_id: int) -> str:
        """
        Generate insurance-ready report

        Formal documentation for claim submission
        """
        summary = self.get_assessment_summary(assessment_id)
        assessment = self.get_assessment(assessment_id)

        if not summary or not assessment:
            return "Assessment not found"

        # Get job info
        job_result = self.db.execute("""
            SELECT j.*, c.first_name, c.last_name, c.phone, c.email,
                   v.year, v.make, v.model, v.vin
            FROM jobs j
            LEFT JOIN customers c ON c.id = j.customer_id
            LEFT JOIN vehicles v ON v.id = j.vehicle_id
            WHERE j.id = ?
        """, (assessment['job_id'],))

        job = job_result[0] if job_result else {}

        lines = []
        lines.append("=" * 70)
        lines.append("INSURANCE DAMAGE ASSESSMENT DOCUMENTATION")
        lines.append("=" * 70)
        lines.append("")
        lines.append("CLAIMANT INFORMATION")
        lines.append("-" * 70)
        lines.append(f"  Name:              {job.get('first_name', '')} {job.get('last_name', '')}")
        lines.append(f"  Phone:             {job.get('phone', 'N/A')}")
        lines.append(f"  Email:             {job.get('email', 'N/A')}")
        lines.append("")
        lines.append("VEHICLE INFORMATION")
        lines.append("-" * 70)
        lines.append(f"  Year:              {job.get('year', 'N/A')}")
        lines.append(f"  Make:              {job.get('make', 'N/A')}")
        lines.append(f"  Model:             {job.get('model', 'N/A')}")
        lines.append(f"  VIN:               {job.get('vin', 'N/A')}")
        lines.append("")
        lines.append("DAMAGE ASSESSMENT")
        lines.append("-" * 70)
        lines.append(f"  Assessment Date:   {assessment['created_at'][:10]}")
        lines.append(f"  Assessment Type:   {assessment['assessment_type']}")
        lines.append(f"  Assessed By:       {assessment.get('assessed_by', 'N/A')}")
        lines.append("")
        lines.append("DAMAGE SUMMARY")
        lines.append("-" * 70)
        lines.append(f"  Panels Affected:   {summary['total_panels']}")
        lines.append(f"  Total Dent Count:  {summary['total_dents']}")
        lines.append(f"  Damage Severity:   {summary['average_severity']:.1f}/5.0 average")
        lines.append("")
        lines.append("REPAIR ESTIMATE")
        lines.append("-" * 70)
        lines.append(f"  Labor Hours:       {summary['total_time_minutes']/60:.1f}")
        lines.append(f"  Total Estimate:    ${summary['total_cost']:,.2f}")
        lines.append("")
        lines.append("ITEMIZED DAMAGE BY PANEL")
        lines.append("-" * 70)

        for panel in summary['panels']:
            panel_name = panel['panel'].replace('_', ' ').title()
            lines.append(f"  {panel_name}:")
            lines.append(f"    Damage Type: {panel['damage_type']}")
            lines.append(f"    Severity: Level {panel['severity']} ({self.SEVERITY_LEVELS[panel['severity']]['name']})")
            if panel.get('dent_count'):
                lines.append(f"    Dent Count: {panel['dent_count']}")
            if panel.get('estimated_cost'):
                lines.append(f"    Repair Cost: ${panel['estimated_cost']:.2f}")
            lines.append("")

        lines.append("CERTIFICATION")
        lines.append("-" * 70)
        lines.append("  I certify that this damage assessment accurately represents")
        lines.append("  the condition of the above-described vehicle as inspected.")
        lines.append("")
        lines.append(f"  Technician: {assessment.get('assessed_by', '_________________')}")
        lines.append(f"  Date: {datetime.now().strftime('%Y-%m-%d')}")
        lines.append("")
        lines.append("=" * 70)

        return "\n".join(lines)

    # ========================================================================
    # COMPARISON
    # ========================================================================

    def compare_assessments(
        self,
        before_assessment_id: int,
        after_assessment_id: int
    ) -> Dict[str, Any]:
        """
        Compare two assessments (before/after repair)

        Shows repair progress
        """
        before = self.get_assessment_summary(before_assessment_id)
        after = self.get_assessment_summary(after_assessment_id)

        if not before or not after:
            return {}

        comparison = {
            'before': {
                'assessment_id': before_assessment_id,
                'total_panels': before['total_panels'],
                'total_dents': before['total_dents'],
                'total_cost': before['total_cost'],
                'average_severity': before['average_severity']
            },
            'after': {
                'assessment_id': after_assessment_id,
                'total_panels': after['total_panels'],
                'total_dents': after['total_dents'],
                'total_cost': after['total_cost'],
                'average_severity': after['average_severity']
            },
            'improvement': {
                'panels_repaired': before['total_panels'] - after['total_panels'],
                'dents_removed': before['total_dents'] - after['total_dents'],
                'value_delivered': before['total_cost'] - after['total_cost'],
                'severity_reduction': before['average_severity'] - after['average_severity'],
                'percent_complete': 0.0
            }
        }

        if before['total_dents'] > 0:
            comparison['improvement']['percent_complete'] = (
                comparison['improvement']['dents_removed'] / before['total_dents']
            ) * 100

        return comparison

    def generate_comparison_report(
        self,
        before_assessment_id: int,
        after_assessment_id: int
    ) -> str:
        """Generate before/after comparison report"""
        comparison = self.compare_assessments(before_assessment_id, after_assessment_id)

        if not comparison:
            return "Could not generate comparison"

        lines = []
        lines.append("=" * 60)
        lines.append("BEFORE/AFTER ASSESSMENT COMPARISON")
        lines.append("=" * 60)
        lines.append("")
        lines.append("BEFORE REPAIR")
        lines.append("-" * 60)
        lines.append(f"  Panels Affected:    {comparison['before']['total_panels']}")
        lines.append(f"  Total Dents:        {comparison['before']['total_dents']}")
        lines.append(f"  Average Severity:   {comparison['before']['average_severity']:.1f}/5.0")
        lines.append(f"  Damage Value:       ${comparison['before']['total_cost']:,.2f}")
        lines.append("")
        lines.append("AFTER REPAIR")
        lines.append("-" * 60)
        lines.append(f"  Panels Affected:    {comparison['after']['total_panels']}")
        lines.append(f"  Total Dents:        {comparison['after']['total_dents']}")
        lines.append(f"  Average Severity:   {comparison['after']['average_severity']:.1f}/5.0")
        lines.append(f"  Remaining Value:    ${comparison['after']['total_cost']:,.2f}")
        lines.append("")
        lines.append("REPAIR RESULTS")
        lines.append("-" * 60)
        lines.append(f"  Panels Completed:   {comparison['improvement']['panels_repaired']}")
        lines.append(f"  Dents Removed:      {comparison['improvement']['dents_removed']}")
        lines.append(f"  Severity Reduction: {comparison['improvement']['severity_reduction']:.1f} points")
        lines.append(f"  Value Delivered:    ${comparison['improvement']['value_delivered']:,.2f}")
        lines.append(f"  Progress:           {comparison['improvement']['percent_complete']:.1f}% complete")
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def delete_assessment(self, assessment_id: int) -> bool:
        """Delete assessment and all panel assessments"""
        # Delete panel assessments first
        self.db.execute("""
            DELETE FROM panel_assessments WHERE assessment_id = ?
        """, (assessment_id,))

        # Delete assessment
        self.db.execute("""
            DELETE FROM damage_assessments WHERE id = ?
        """, (assessment_id,))

        return True

    def delete_panel_assessment(self, panel_assessment_id: int) -> bool:
        """Delete single panel assessment"""
        self.db.execute("""
            DELETE FROM panel_assessments WHERE id = ?
        """, (panel_assessment_id,))

        return True
