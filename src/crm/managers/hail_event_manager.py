"""
PDR CRM Part 16 - Hail Event Manager
Track hail storm events for PDR business operations

FEATURES:
- Storm event database
- Severity classification (Minor/Moderate/Severe/Catastrophic)
- Affected area tracking (ZIP codes, radius)
- Insurance storm codes
- NOAA event linking
- Storm search & filtering
- Active storm management
- Market opportunity estimation

NOTE: Adapts to existing schema and stores extended metadata in notes JSON
"""

import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any


class HailEventManager:
    """
    Manage hail storm events for PDR operations

    Foundation for storm-based lead generation and job tracking

    Works with existing hail_events table schema:
    - id, event_date, event_name, location_name, affected_area_sq_miles
    - swath_geojson, max_hail_size, estimated_vehicles
    - potential_customers, potential_revenue
    - campaign_created, leads_generated, leads_converted
    - notes, created_at, updated_at

    Extended metadata (city, state, severity, zip codes, etc.) stored as JSON
    """

    # Storm severity classifications with business metrics
    SEVERITY_LEVELS = {
        'MINOR': {
            'name': 'Minor',
            'hail_size': '< 1 inch',
            'hail_size_range': (0.25, 0.99),
            'damage_level': 'Light cosmetic damage, small dents',
            'avg_revenue_per_vehicle': 500,
            'avg_repair_hours': 2,
            'glass_damage_likely': False,
            'color': '#10b981'  # Green
        },
        'MODERATE': {
            'name': 'Moderate',
            'hail_size': '1 - 1.5 inches',
            'hail_size_range': (1.0, 1.49),
            'damage_level': 'Moderate panel damage, multiple dents',
            'avg_revenue_per_vehicle': 1500,
            'avg_repair_hours': 4,
            'glass_damage_likely': False,
            'color': '#f59e0b'  # Yellow
        },
        'SEVERE': {
            'name': 'Severe',
            'hail_size': '1.5 - 2 inches',
            'hail_size_range': (1.5, 1.99),
            'damage_level': 'Extensive panel damage, deep dents',
            'avg_revenue_per_vehicle': 3000,
            'avg_repair_hours': 8,
            'glass_damage_likely': True,
            'color': '#ef4444'  # Red
        },
        'CATASTROPHIC': {
            'name': 'Catastrophic',
            'hail_size': '> 2 inches',
            'hail_size_range': (2.0, 10.0),
            'damage_level': 'Extreme damage, glass breakage common',
            'avg_revenue_per_vehicle': 5000,
            'avg_repair_hours': 12,
            'glass_damage_likely': True,
            'color': '#7c3aed'  # Purple
        }
    }

    def __init__(self, db):
        """Initialize hail event manager with database instance"""
        self.db = db

    # =========================================================================
    # INTERNAL HELPERS - Metadata Management
    # =========================================================================

    def _build_metadata(
        self,
        city: str = None,
        state: str = None,
        severity: str = None,
        affected_zip_codes: List[str] = None,
        estimated_radius_miles: float = None,
        insurance_storm_code: str = None,
        noaa_event_id: str = None,
        status: str = 'ACTIVE',
        user_notes: str = None
    ) -> str:
        """Build JSON metadata string for notes field"""
        metadata = {
            '_meta': {
                'city': city,
                'state': state,
                'severity': severity,
                'affected_zip_codes': affected_zip_codes or [],
                'estimated_radius_miles': estimated_radius_miles,
                'insurance_storm_code': insurance_storm_code,
                'noaa_event_id': noaa_event_id,
                'status': status
            },
            'notes': user_notes or ''
        }
        return json.dumps(metadata)

    def _parse_metadata(self, notes_field: str) -> Dict[str, Any]:
        """Parse metadata from notes field"""
        if not notes_field:
            return {'_meta': {'status': 'ACTIVE'}, 'notes': ''}

        try:
            data = json.loads(notes_field)
            if '_meta' in data:
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        # Legacy plain text notes
        return {'_meta': {'status': 'ACTIVE'}, 'notes': notes_field}

    def _enrich_storm_record(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a storm record with parsed metadata"""
        storm = dict(row)

        # Parse metadata from notes field
        parsed = self._parse_metadata(storm.get('notes'))
        meta = parsed.get('_meta', {})

        # Add metadata fields to storm record
        storm['city'] = meta.get('city')
        storm['state'] = meta.get('state')
        storm['severity'] = meta.get('severity', self._infer_severity(storm.get('max_hail_size')))
        storm['affected_zip_codes'] = meta.get('affected_zip_codes', [])
        storm['estimated_radius_miles'] = meta.get('estimated_radius_miles')
        storm['insurance_storm_code'] = meta.get('insurance_storm_code')
        storm['noaa_event_id'] = meta.get('noaa_event_id')
        storm['status'] = meta.get('status', 'ACTIVE')

        # Store user notes separately
        storm['user_notes'] = parsed.get('notes', '')

        # Map schema columns to expected names
        storm['location'] = storm.get('location_name', '')
        storm['hail_size_inches'] = storm.get('max_hail_size')
        storm['estimated_vehicles_affected'] = storm.get('estimated_vehicles')

        # Add severity info
        if storm['severity'] in self.SEVERITY_LEVELS:
            storm['severity_info'] = self.SEVERITY_LEVELS[storm['severity']]

        return storm

    def _infer_severity(self, hail_size: float) -> str:
        """Infer severity from hail size if not explicitly set"""
        if not hail_size:
            return 'MODERATE'
        return self.classify_severity_by_hail_size(hail_size)

    # =========================================================================
    # STORM EVENT MANAGEMENT
    # =========================================================================

    def create_storm_event(
        self,
        event_name: str,
        event_date: date,
        location: str,
        city: str,
        state: str,
        severity: str,
        hail_size_inches: float = None,
        affected_zip_codes: List[str] = None,
        estimated_radius_miles: float = None,
        insurance_storm_code: str = None,
        noaa_event_id: str = None,
        estimated_vehicles_affected: int = None,
        notes: str = None
    ) -> int:
        """
        Create hail storm event record

        Args:
            event_name: Storm name (e.g., "Dallas Hail Storm May 2024")
            event_date: Date storm occurred
            location: Location description
            city: Primary city affected
            state: State (2-letter code)
            severity: MINOR, MODERATE, SEVERE, or CATASTROPHIC
            hail_size_inches: Maximum hail size in inches
            affected_zip_codes: List of affected ZIP codes
            estimated_radius_miles: Storm impact radius
            insurance_storm_code: Insurance company storm identifier
            noaa_event_id: NOAA weather event ID
            estimated_vehicles_affected: Estimated vehicles in area
            notes: Additional notes about the storm

        Returns:
            Storm event ID
        """
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(f"Invalid severity. Must be one of: {list(self.SEVERITY_LEVELS.keys())}")

        now = datetime.now().isoformat()
        severity_info = self.SEVERITY_LEVELS[severity]

        # Build metadata JSON for notes field
        metadata_json = self._build_metadata(
            city=city,
            state=state,
            severity=severity,
            affected_zip_codes=affected_zip_codes,
            estimated_radius_miles=estimated_radius_miles,
            insurance_storm_code=insurance_storm_code,
            noaa_event_id=noaa_event_id,
            status='ACTIVE',
            user_notes=notes
        )

        # Calculate potential revenue
        vehicles = estimated_vehicles_affected or 0
        potential_revenue = vehicles * severity_info['avg_revenue_per_vehicle'] * 0.05

        # Calculate affected area from radius if provided
        affected_area = None
        if estimated_radius_miles:
            import math
            affected_area = math.pi * (estimated_radius_miles ** 2)

        result = self.db.execute("""
            INSERT INTO hail_events (
                event_name, event_date, location_name,
                affected_area_sq_miles, max_hail_size,
                estimated_vehicles, potential_revenue,
                notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_name,
            event_date.isoformat() if isinstance(event_date, date) else event_date,
            location,
            affected_area,
            hail_size_inches,
            estimated_vehicles_affected,
            potential_revenue,
            metadata_json,
            now
        ))

        # Get ID from insert result (lastrowid)
        storm_id = result[0]['id']

        print(f"[OK] Created hail event: {event_name}")
        print(f"     Date: {event_date}")
        print(f"     Location: {city}, {state}")
        print(f"     Severity: {severity_info['name']} ({severity_info['hail_size']})")

        if affected_zip_codes:
            print(f"     Affected ZIPs: {len(affected_zip_codes)}")

        if estimated_vehicles_affected:
            est_revenue = estimated_vehicles_affected * severity_info['avg_revenue_per_vehicle'] * 0.05
            print(f"     Est. Market Opportunity: ${est_revenue:,.0f} (5% capture)")

        return storm_id

    def get_storm_event(self, storm_id: int) -> Optional[Dict[str, Any]]:
        """Get storm event by ID"""
        result = self.db.execute("""
            SELECT * FROM hail_events WHERE id = ?
        """, (storm_id,))

        if not result:
            return None

        return self._enrich_storm_record(result[0])

    def update_storm_event(self, storm_id: int, **updates) -> bool:
        """Update storm event fields"""
        if not updates:
            return False

        # Get current storm
        storm = self.get_storm_event(storm_id)
        if not storm:
            return False

        # Separate metadata updates from schema column updates
        metadata_fields = {'city', 'state', 'severity', 'affected_zip_codes',
                          'estimated_radius_miles', 'insurance_storm_code',
                          'noaa_event_id', 'status'}

        metadata_updates = {}
        column_updates = {}
        user_notes = None

        for key, value in updates.items():
            if key == 'notes':
                user_notes = value
            elif key in metadata_fields:
                metadata_updates[key] = value
            elif key == 'estimated_vehicles_affected':
                column_updates['estimated_vehicles'] = value
            elif key == 'hail_size_inches':
                column_updates['max_hail_size'] = value
            elif key == 'location':
                column_updates['location_name'] = value
            else:
                column_updates[key] = value

        # Rebuild metadata if needed
        if metadata_updates or user_notes is not None:
            parsed = self._parse_metadata(storm.get('notes'))
            meta = parsed.get('_meta', {})

            # Apply metadata updates
            for key, value in metadata_updates.items():
                meta[key] = value

            # Handle notes
            current_notes = parsed.get('notes', '')
            if user_notes is not None:
                current_notes = user_notes

            # Rebuild JSON
            new_metadata = json.dumps({'_meta': meta, 'notes': current_notes})
            column_updates['notes'] = new_metadata

        # Build update query
        if column_updates:
            set_clauses = []
            values = []

            for key, value in column_updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            set_clauses.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(storm_id)

            query = f"""
                UPDATE hail_events SET {', '.join(set_clauses)} WHERE id = ?
            """

            self.db.execute(query, tuple(values))
            print(f"[OK] Updated storm event #{storm_id}")

        return True

    def close_storm_event(self, storm_id: int, notes: str = None) -> bool:
        """Mark storm event as closed (no longer actively generating leads)"""
        storm = self.get_storm_event(storm_id)
        if not storm:
            return False

        update_notes = storm.get('user_notes') or ''
        if notes:
            update_notes = f"{update_notes}\n\n[CLOSED {date.today()}] {notes}".strip()

        return self.update_storm_event(storm_id, status='CLOSED', notes=update_notes)

    def reopen_storm_event(self, storm_id: int) -> bool:
        """Reopen a closed storm event"""
        return self.update_storm_event(storm_id, status='ACTIVE')

    # =========================================================================
    # STORM SEARCH & FILTERING
    # =========================================================================

    def search_storms(
        self,
        state: str = None,
        city: str = None,
        severity: str = None,
        status: str = None,
        start_date: date = None,
        end_date: date = None,
        zip_code: str = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search storm events with filters

        Args:
            state: Filter by state (2-letter code)
            city: Filter by city (partial match)
            severity: Filter by severity level
            status: Filter by status (ACTIVE, CLOSED)
            start_date: Events on or after this date
            end_date: Events on or before this date
            zip_code: Filter by affected ZIP code
            limit: Maximum results

        Returns:
            List of matching storm events
        """
        query = "SELECT * FROM hail_events WHERE 1=1"
        params = []

        if start_date:
            query += " AND event_date >= ?"
            params.append(start_date.isoformat() if isinstance(start_date, date) else start_date)

        if end_date:
            query += " AND event_date <= ?"
            params.append(end_date.isoformat() if isinstance(end_date, date) else end_date)

        # State, city, severity, status, zip_code are in JSON metadata
        # We'll filter after fetch for these
        query += " ORDER BY event_date DESC LIMIT ?"
        params.append(limit * 3)  # Fetch more to filter

        results = self.db.execute(query, tuple(params))

        storms = []
        for row in results:
            storm = self._enrich_storm_record(row)

            # Apply metadata filters
            if state and storm.get('state') != state:
                continue
            if city and city.lower() not in (storm.get('city') or '').lower():
                continue
            if severity and storm.get('severity') != severity:
                continue
            if status and storm.get('status') != status:
                continue
            if zip_code:
                zips = storm.get('affected_zip_codes') or []
                if zip_code not in zips:
                    continue

            storms.append(storm)

            if len(storms) >= limit:
                break

        return storms

    def get_active_storms(self, days_back: int = 90) -> List[Dict[str, Any]]:
        """Get recent active storms"""
        cutoff = date.today() - timedelta(days=days_back)
        return self.search_storms(status='ACTIVE', start_date=cutoff)

    def get_storms_by_zip(self, zip_code: str) -> List[Dict[str, Any]]:
        """Find storms that affected a specific ZIP code"""
        return self.search_storms(zip_code=zip_code)

    def get_storms_by_severity(self, severity: str, days_back: int = 365) -> List[Dict[str, Any]]:
        """Get storms of a specific severity level"""
        cutoff = date.today() - timedelta(days=days_back)
        return self.search_storms(severity=severity, start_date=cutoff)

    # =========================================================================
    # STORM STATISTICS & ANALYTICS
    # =========================================================================

    def get_storm_stats(self, storm_id: int) -> Dict[str, Any]:
        """Get statistics for a specific storm"""
        storm = self.get_storm_event(storm_id)
        if not storm:
            return {}

        severity = storm.get('severity', 'MODERATE')
        severity_info = self.SEVERITY_LEVELS.get(severity, {})

        stats = {
            'storm_id': storm_id,
            'event_name': storm['event_name'],
            'event_date': storm['event_date'],
            'severity': severity,
            'severity_info': severity_info,
            'affected_zip_count': len(storm.get('affected_zip_codes') or []),
            'estimated_vehicles': storm.get('estimated_vehicles') or 0,
            'market_opportunity': {}
        }

        # Calculate market opportunity at different capture rates
        vehicles = stats['estimated_vehicles']
        avg_revenue = severity_info.get('avg_revenue_per_vehicle', 0)

        for capture_rate in [0.01, 0.05, 0.10, 0.15]:
            stats['market_opportunity'][f'{int(capture_rate*100)}%'] = {
                'vehicles': int(vehicles * capture_rate),
                'revenue': vehicles * capture_rate * avg_revenue
            }

        # Get linked jobs count
        try:
            jobs = self.db.execute("""
                SELECT COUNT(*) as count FROM jobs WHERE hail_event_id = ?
            """, (storm_id,))
            stats['jobs_created'] = jobs[0]['count'] if jobs else 0
        except:
            stats['jobs_created'] = 0

        # Get linked leads count
        try:
            leads = self.db.execute("""
                SELECT COUNT(*) as count FROM leads WHERE hail_event_id = ?
            """, (storm_id,))
            stats['leads_generated'] = leads[0]['count'] if leads else 0
        except:
            stats['leads_generated'] = 0

        return stats

    def get_overall_storm_stats(self, days: int = 365) -> Dict[str, Any]:
        """Get overall storm statistics"""
        cutoff = (date.today() - timedelta(days=days)).isoformat()

        stats = {
            'period_days': days,
            'total_storms': 0,
            'by_severity': {},
            'by_state': {},
            'total_estimated_vehicles': 0,
            'active_storms': 0
        }

        # Fetch all storms in date range
        results = self.db.execute("""
            SELECT * FROM hail_events WHERE event_date >= ?
        """, (cutoff,))

        storms = [self._enrich_storm_record(row) for row in results]

        stats['total_storms'] = len(storms)

        # Count active storms
        stats['active_storms'] = sum(1 for s in storms if s.get('status') == 'ACTIVE')

        # Aggregate by severity
        for storm in storms:
            severity = storm.get('severity', 'MODERATE')
            vehicles = storm.get('estimated_vehicles') or 0

            if severity not in stats['by_severity']:
                stats['by_severity'][severity] = {'count': 0, 'estimated_vehicles': 0}
            stats['by_severity'][severity]['count'] += 1
            stats['by_severity'][severity]['estimated_vehicles'] += vehicles

        # Aggregate by state
        for storm in storms:
            state = storm.get('state') or 'UNKNOWN'
            vehicles = storm.get('estimated_vehicles') or 0

            if state not in stats['by_state']:
                stats['by_state'][state] = {'count': 0, 'estimated_vehicles': 0}
            stats['by_state'][state]['count'] += 1
            stats['by_state'][state]['estimated_vehicles'] += vehicles

        # Total estimated vehicles
        stats['total_estimated_vehicles'] = sum(
            (s.get('estimated_vehicles') or 0) for s in storms
        )

        return stats

    # =========================================================================
    # SEVERITY CLASSIFICATION HELPERS
    # =========================================================================

    def classify_severity_by_hail_size(self, hail_size_inches: float) -> str:
        """Determine severity classification based on hail size"""
        for level, info in self.SEVERITY_LEVELS.items():
            min_size, max_size = info['hail_size_range']
            if min_size <= hail_size_inches <= max_size:
                return level

        # Default to CATASTROPHIC if over max
        if hail_size_inches > 2.0:
            return 'CATASTROPHIC'

        return 'MINOR'

    def get_severity_info(self, severity: str) -> Dict[str, Any]:
        """Get detailed information about a severity level"""
        return self.SEVERITY_LEVELS.get(severity, {})

    def estimate_market_opportunity(
        self,
        vehicles_affected: int,
        severity: str,
        capture_rate: float = 0.05
    ) -> Dict[str, Any]:
        """
        Estimate market opportunity for a storm

        Args:
            vehicles_affected: Number of vehicles in affected area
            severity: Storm severity level
            capture_rate: Expected market capture rate (default 5%)

        Returns:
            Market opportunity estimates
        """
        severity_info = self.SEVERITY_LEVELS.get(severity, {})
        avg_revenue = severity_info.get('avg_revenue_per_vehicle', 1000)
        avg_hours = severity_info.get('avg_repair_hours', 4)

        captured_vehicles = int(vehicles_affected * capture_rate)
        total_revenue = captured_vehicles * avg_revenue
        total_hours = captured_vehicles * avg_hours

        return {
            'vehicles_in_area': vehicles_affected,
            'capture_rate': capture_rate,
            'captured_vehicles': captured_vehicles,
            'avg_revenue_per_vehicle': avg_revenue,
            'total_revenue_potential': total_revenue,
            'total_repair_hours': total_hours,
            'avg_repair_hours_per_vehicle': avg_hours,
            'techs_needed_30_days': int(total_hours / (8 * 22)) + 1  # 8hr days, 22 working days
        }

    # =========================================================================
    # REPORTING
    # =========================================================================

    def generate_storm_report(self, storm_id: int) -> str:
        """Generate detailed report for a specific storm"""
        storm = self.get_storm_event(storm_id)
        if not storm:
            return "Storm not found"

        stats = self.get_storm_stats(storm_id)
        severity_info = storm.get('severity_info', {})

        report = []
        report.append("=" * 60)
        report.append("HAIL STORM EVENT REPORT")
        report.append("=" * 60)
        report.append("")

        report.append(f"Event Name: {storm['event_name']}")
        report.append(f"Event Date: {storm['event_date']}")
        report.append(f"Location: {storm.get('location') or storm.get('location_name') or 'N/A'}")
        city = storm.get('city') or ''
        state = storm.get('state') or ''
        if city or state:
            report.append(f"City/State: {city}, {state}")
        report.append(f"Status: {storm.get('status', 'N/A')}")
        report.append("")

        report.append("STORM CHARACTERISTICS")
        report.append("-" * 40)
        report.append(f"Severity: {storm.get('severity', 'N/A')} - {severity_info.get('name', 'N/A')}")
        report.append(f"Hail Size: {storm.get('hail_size_inches') or storm.get('max_hail_size') or 'N/A'} inches")
        report.append(f"Damage Level: {severity_info.get('damage_level', 'N/A')}")
        report.append(f"Estimated Radius: {storm.get('estimated_radius_miles') or 'N/A'} miles")
        report.append("")

        report.append("IDENTIFIERS")
        report.append("-" * 40)
        report.append(f"Insurance Storm Code: {storm.get('insurance_storm_code') or 'N/A'}")
        report.append(f"NOAA Event ID: {storm.get('noaa_event_id') or 'N/A'}")
        report.append("")

        zips = storm.get('affected_zip_codes') or []
        report.append(f"AFFECTED AREAS ({len(zips)} ZIP codes)")
        report.append("-" * 40)
        if zips:
            # Display in columns
            for i in range(0, len(zips), 5):
                report.append("  " + "  ".join(zips[i:i+5]))
        report.append("")

        report.append("MARKET OPPORTUNITY")
        report.append("-" * 40)
        report.append(f"Estimated Vehicles Affected: {stats['estimated_vehicles']:,}")
        report.append(f"Avg Revenue per Vehicle: ${severity_info.get('avg_revenue_per_vehicle', 0):,}")
        report.append("")
        report.append("Revenue Potential by Capture Rate:")
        for rate, data in stats['market_opportunity'].items():
            report.append(f"  {rate:>5}: {data['vehicles']:>6,} vehicles = ${data['revenue']:>12,.0f}")
        report.append("")

        report.append("BUSINESS METRICS")
        report.append("-" * 40)
        report.append(f"Leads Generated: {stats['leads_generated']}")
        report.append(f"Jobs Created: {stats['jobs_created']}")
        report.append("")

        user_notes = storm.get('user_notes') or ''
        if user_notes:
            report.append("NOTES")
            report.append("-" * 40)
            report.append(user_notes)
            report.append("")

        return "\n".join(report)

    def generate_summary_report(self, days: int = 90) -> str:
        """Generate summary report of all storm activity"""
        stats = self.get_overall_storm_stats(days)

        report = []
        report.append("=" * 60)
        report.append(f"HAIL STORM SUMMARY REPORT (Last {days} Days)")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)
        report.append("")

        report.append("OVERVIEW")
        report.append("-" * 40)
        report.append(f"Total Storm Events:        {stats['total_storms']:>10}")
        report.append(f"Active Storms:             {stats['active_storms']:>10}")
        report.append(f"Total Vehicles Affected:   {stats['total_estimated_vehicles']:>10,}")
        report.append("")

        report.append("BY SEVERITY")
        report.append("-" * 40)
        for severity in ['CATASTROPHIC', 'SEVERE', 'MODERATE', 'MINOR']:
            data = stats['by_severity'].get(severity, {'count': 0, 'estimated_vehicles': 0})
            report.append(f"  {severity:15} {data['count']:>5} storms  {data['estimated_vehicles']:>10,} vehicles")
        report.append("")

        report.append("BY STATE (Top 10)")
        report.append("-" * 40)
        sorted_states = sorted(stats['by_state'].items(), key=lambda x: x[1]['count'], reverse=True)[:10]
        for state, data in sorted_states:
            report.append(f"  {state:5} {data['count']:>5} storms  {data['estimated_vehicles']:>10,} vehicles")
        report.append("")

        return "\n".join(report)

    # =========================================================================
    # STORM LINKING INFRASTRUCTURE
    # =========================================================================

    def _ensure_storm_linking_tables(self):
        """Ensure storm-job linking tables exist"""
        # Create hail_event_jobs linking table if it doesn't exist
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS hail_event_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hail_event_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                confidence TEXT DEFAULT 'CONFIRMED',
                notes TEXT,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                linked_by TEXT,
                FOREIGN KEY (hail_event_id) REFERENCES hail_events(id),
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                UNIQUE(hail_event_id, job_id)
            )
        """)

    # =========================================================================
    # JOB-TO-STORM LINKING
    # =========================================================================

    def link_job_to_storm(
        self,
        job_id: int,
        storm_id: int,
        confidence: str = 'CONFIRMED',
        notes: Optional[str] = None
    ) -> bool:
        """
        Link job to storm event

        Args:
            job_id: Job ID
            storm_id: Storm event ID
            confidence: CONFIRMED, LIKELY, POSSIBLE
            notes: Link justification

        Returns:
            True if linked successfully
        """
        # Ensure linking table exists
        self._ensure_storm_linking_tables()

        now = datetime.now().isoformat()

        # Insert or replace the link
        try:
            self.db.execute("""
                INSERT OR REPLACE INTO hail_event_jobs (
                    hail_event_id, job_id, confidence, notes, linked_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (storm_id, job_id, confidence, notes, now))
        except Exception as e:
            print(f"[ERROR] Failed to link job: {e}")
            return False

        # Get details for confirmation message
        try:
            job = self.db.execute("SELECT job_number FROM jobs WHERE id = ?", (job_id,))
            storm = self.get_storm_event(storm_id)

            job_num = job[0]['job_number'] if job else f"Job #{job_id}"
            storm_name = storm['event_name'] if storm else f"Storm #{storm_id}"

            print(f"[OK] Linked {job_num} to storm: {storm_name} ({confidence})")
        except:
            print(f"[OK] Linked job #{job_id} to storm #{storm_id}")

        return True

    def unlink_job_from_storm(self, job_id: int, storm_id: int) -> bool:
        """Remove job-storm link"""
        self._ensure_storm_linking_tables()

        self.db.execute("""
            DELETE FROM hail_event_jobs
            WHERE job_id = ? AND hail_event_id = ?
        """, (job_id, storm_id))

        print(f"[OK] Unlinked job #{job_id} from storm #{storm_id}")
        return True

    def get_job_storm_link(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get the storm linked to a job"""
        self._ensure_storm_linking_tables()

        result = self.db.execute("""
            SELECT hej.*, he.event_name, he.event_date
            FROM hail_event_jobs hej
            JOIN hail_events he ON he.id = hej.hail_event_id
            WHERE hej.job_id = ?
        """, (job_id,))

        if result:
            return dict(result[0])
        return None

    def find_matching_storm(
        self,
        customer_zip: str,
        damage_date: date,
        days_range: int = 14
    ) -> Optional[Dict[str, Any]]:
        """
        Auto-suggest storm based on customer location and damage date

        Args:
            customer_zip: Customer's ZIP code
            damage_date: When customer noticed damage
            days_range: Search +/- days from damage_date

        Returns:
            Best matching storm or None
        """
        start_date = damage_date - timedelta(days=days_range)
        end_date = damage_date + timedelta(days=days_range)

        # Find storms in date range
        storms = self.db.execute("""
            SELECT *
            FROM hail_events
            WHERE event_date >= ?
              AND event_date <= ?
            ORDER BY event_date DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        # Check each storm for ZIP match
        for storm_row in storms:
            storm = self._enrich_storm_record(storm_row)

            # Check if customer ZIP is in affected areas
            affected_zips = storm.get('affected_zip_codes') or []
            if customer_zip in affected_zips:
                print(f"[MATCH] Found: {storm['event_name']}")
                print(f"        Customer ZIP {customer_zip} in affected area")
                return storm

        # Return closest storm by date if no ZIP match
        if storms:
            closest = self._enrich_storm_record(storms[0])
            print(f"[INFO] Closest storm by date: {closest['event_name']}")
            return closest

        print(f"[INFO] No matching storm found for {customer_zip} around {damage_date}")
        return None

    def get_storm_jobs(self, storm_id: int) -> List[Dict[str, Any]]:
        """Get all jobs linked to storm"""
        self._ensure_storm_linking_tables()

        return self.db.execute("""
            SELECT
                j.*,
                c.first_name || ' ' || c.last_name as customer_name,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                hej.confidence,
                hej.linked_at
            FROM hail_event_jobs hej
            JOIN jobs j ON j.id = hej.job_id
            JOIN customers c ON c.id = j.customer_id
            JOIN vehicles v ON v.id = j.vehicle_id
            WHERE hej.hail_event_id = ?
              AND j.deleted_at IS NULL
            ORDER BY j.created_at DESC
        """, (storm_id,))

    def get_storm_job_count(self, storm_id: int) -> int:
        """Get count of jobs linked to storm"""
        self._ensure_storm_linking_tables()

        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM hail_event_jobs hej
            JOIN jobs j ON j.id = hej.job_id
            WHERE hej.hail_event_id = ?
              AND j.deleted_at IS NULL
        """, (storm_id,))

        return result[0]['count'] if result else 0

    # =========================================================================
    # STORM ANALYTICS & ROI
    # =========================================================================

    def get_storm_roi(self, storm_id: int) -> Dict[str, Any]:
        """
        Calculate ROI for specific storm event

        Returns comprehensive storm performance metrics including:
        - Jobs created
        - Total revenue
        - Lead conversion rate
        - Market penetration
        - Job status breakdown
        """
        self._ensure_storm_linking_tables()

        storm = self.get_storm_event(storm_id)
        if not storm:
            return {}

        roi = {
            'storm_id': storm_id,
            'event_name': storm['event_name'],
            'event_date': storm['event_date'],
            'severity': storm.get('severity', 'MODERATE'),
            'estimated_vehicles': storm.get('estimated_vehicles') or 0
        }

        # Jobs linked to this storm
        jobs = self.db.execute("""
            SELECT
                COUNT(DISTINCT j.id) as job_count,
                COUNT(DISTINCT j.customer_id) as customer_count
            FROM hail_event_jobs hej
            JOIN jobs j ON j.id = hej.job_id
            WHERE hej.hail_event_id = ?
              AND j.deleted_at IS NULL
        """, (storm_id,))

        roi['jobs_created'] = jobs[0]['job_count'] if jobs else 0
        roi['customers_acquired'] = jobs[0]['customer_count'] if jobs else 0

        # Revenue from storm jobs
        revenue = self.db.execute("""
            SELECT
                SUM(p.total_amount) as total_revenue,
                SUM(p.total_amount - COALESCE(p.parts_cost, 0)) as labor_revenue
            FROM payments p
            JOIN hail_event_jobs hej ON hej.job_id = p.job_id
            WHERE hej.hail_event_id = ?
              AND p.status != 'BOUNCED'
        """, (storm_id,))

        roi['total_revenue'] = round(revenue[0]['total_revenue'] or 0, 2)
        roi['labor_revenue'] = round(revenue[0]['labor_revenue'] or 0, 2)

        # Lead conversion (leads linked to this storm via hail_event_id)
        leads = self.db.execute("""
            SELECT COUNT(*) as lead_count
            FROM leads
            WHERE hail_event_id = ?
              AND deleted_at IS NULL
        """, (storm_id,))

        roi['leads_generated'] = leads[0]['lead_count'] if leads else 0

        if roi['leads_generated'] > 0:
            roi['lead_conversion_rate'] = (roi['jobs_created'] / roi['leads_generated']) * 100
        else:
            roi['lead_conversion_rate'] = 0

        # Average revenue per job
        if roi['jobs_created'] > 0:
            roi['avg_revenue_per_job'] = roi['total_revenue'] / roi['jobs_created']
        else:
            roi['avg_revenue_per_job'] = 0

        # Market penetration
        if roi['estimated_vehicles'] > 0:
            roi['market_penetration'] = (roi['jobs_created'] / roi['estimated_vehicles']) * 100
        else:
            roi['market_penetration'] = 0

        # Job status breakdown
        status_breakdown = self.db.execute("""
            SELECT j.status, COUNT(*) as count
            FROM hail_event_jobs hej
            JOIN jobs j ON j.id = hej.job_id
            WHERE hej.hail_event_id = ?
              AND j.deleted_at IS NULL
            GROUP BY j.status
        """, (storm_id,))

        roi['jobs_by_status'] = {row['status']: row['count'] for row in status_breakdown}

        # Confidence breakdown
        confidence_breakdown = self.db.execute("""
            SELECT confidence, COUNT(*) as count
            FROM hail_event_jobs
            WHERE hail_event_id = ?
            GROUP BY confidence
        """, (storm_id,))

        roi['jobs_by_confidence'] = {row['confidence']: row['count'] for row in confidence_breakdown}

        return roi

    def get_all_storms_performance(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_jobs: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics for all storms

        Args:
            start_date: Filter storms after this date
            end_date: Filter storms before this date
            min_jobs: Only include storms with at least this many jobs

        Returns:
            List of storms with performance data, sorted by revenue
        """
        self._ensure_storm_linking_tables()

        # Base query to get storms with job counts
        query = """
        SELECT
            he.id,
            he.event_name,
            he.event_date,
            he.notes,
            he.estimated_vehicles,
            COUNT(DISTINCT hej.job_id) as job_count,
            COALESCE(SUM(p.total_amount), 0) as total_revenue
        FROM hail_events he
        LEFT JOIN hail_event_jobs hej ON hej.hail_event_id = he.id
        LEFT JOIN jobs j ON j.id = hej.job_id AND j.deleted_at IS NULL
        LEFT JOIN payments p ON p.job_id = j.id AND p.status != 'BOUNCED'
        WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND he.event_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND he.event_date <= ?"
            params.append(end_date.isoformat())

        query += """
        GROUP BY he.id
        HAVING job_count >= ?
        ORDER BY total_revenue DESC
        """
        params.append(min_jobs)

        storms = self.db.execute(query, tuple(params))

        # Enrich with additional metrics
        results = []
        for storm_row in storms:
            storm = dict(storm_row)

            # Parse metadata for severity, city, state
            parsed = self._parse_metadata(storm.get('notes'))
            meta = parsed.get('_meta', {})
            storm['severity'] = meta.get('severity', 'MODERATE')
            storm['city'] = meta.get('city')
            storm['state'] = meta.get('state')
            storm['location'] = f"{meta.get('city', '')}, {meta.get('state', '')}"

            storm['total_revenue'] = round(storm['total_revenue'] or 0, 2)

            if storm['job_count'] > 0:
                storm['avg_revenue_per_job'] = storm['total_revenue'] / storm['job_count']
            else:
                storm['avg_revenue_per_job'] = 0

            if storm['estimated_vehicles'] and storm['estimated_vehicles'] > 0:
                storm['market_penetration'] = (storm['job_count'] / storm['estimated_vehicles']) * 100
            else:
                storm['market_penetration'] = 0

            results.append(storm)

        return results

    def get_storm_comparison(self, storm_ids: List[int]) -> Dict[str, Any]:
        """Compare performance across multiple storms"""
        comparison = {
            'storms': [],
            'totals': {
                'jobs': 0,
                'revenue': 0,
                'customers': 0
            }
        }

        for storm_id in storm_ids:
            roi = self.get_storm_roi(storm_id)
            comparison['storms'].append(roi)
            comparison['totals']['jobs'] += roi.get('jobs_created', 0)
            comparison['totals']['revenue'] += roi.get('total_revenue', 0)
            comparison['totals']['customers'] += roi.get('customers_acquired', 0)

        # Calculate averages
        if comparison['storms']:
            count = len(comparison['storms'])
            comparison['averages'] = {
                'jobs_per_storm': comparison['totals']['jobs'] / count,
                'revenue_per_storm': comparison['totals']['revenue'] / count,
                'customers_per_storm': comparison['totals']['customers'] / count
            }

        return comparison

    # =========================================================================
    # ENHANCED REPORTING
    # =========================================================================

    def generate_storm_performance_report(self, storm_id: int) -> str:
        """Generate comprehensive performance report for a storm"""
        storm = self.get_storm_event(storm_id)
        if not storm:
            return "Storm not found"

        roi = self.get_storm_roi(storm_id)
        severity_info = storm.get('severity_info', {})

        report = []
        report.append("=" * 70)
        report.append("STORM PERFORMANCE REPORT")
        report.append("=" * 70)
        report.append("")

        # Storm Info
        report.append("STORM INFORMATION")
        report.append("-" * 50)
        report.append(f"Event Name:       {storm['event_name']}")
        report.append(f"Event Date:       {storm['event_date']}")
        report.append(f"Location:         {storm.get('location') or 'N/A'}")
        if storm.get('city') or storm.get('state'):
            report.append(f"City/State:       {storm.get('city', '')}, {storm.get('state', '')}")
        report.append(f"Severity:         {storm.get('severity', 'N/A')} - {severity_info.get('name', 'N/A')}")
        report.append(f"Hail Size:        {storm.get('hail_size_inches') or 'N/A'} inches")
        report.append(f"Status:           {storm.get('status', 'ACTIVE')}")
        report.append("")

        # Market Info
        report.append("MARKET INFORMATION")
        report.append("-" * 50)
        zips = storm.get('affected_zip_codes') or []
        report.append(f"Affected ZIPs:    {len(zips)}")
        report.append(f"Est. Radius:      {storm.get('estimated_radius_miles') or 'N/A'} miles")
        report.append(f"Est. Vehicles:    {roi.get('estimated_vehicles', 0):,}")
        report.append("")

        # Performance Metrics
        report.append("PERFORMANCE METRICS")
        report.append("-" * 50)
        report.append(f"Jobs Created:     {roi['jobs_created']}")
        report.append(f"Customers:        {roi['customers_acquired']}")
        report.append(f"Leads Generated:  {roi['leads_generated']}")
        report.append(f"Conversion Rate:  {roi['lead_conversion_rate']:.1f}%")
        report.append(f"Market Penetration: {roi['market_penetration']:.4f}%")
        report.append("")

        # Revenue
        report.append("REVENUE")
        report.append("-" * 50)
        report.append(f"Total Revenue:    ${roi['total_revenue']:,.2f}")
        report.append(f"Labor Revenue:    ${roi['labor_revenue']:,.2f}")
        report.append(f"Avg per Job:      ${roi['avg_revenue_per_job']:,.2f}")
        report.append("")

        # Job Status Breakdown
        if roi.get('jobs_by_status'):
            report.append("JOBS BY STATUS")
            report.append("-" * 50)
            for status, count in sorted(roi['jobs_by_status'].items()):
                report.append(f"  {status:25} {count:>5}")
            report.append("")

        # Confidence Breakdown
        if roi.get('jobs_by_confidence'):
            report.append("JOBS BY CONFIDENCE")
            report.append("-" * 50)
            for conf, count in roi['jobs_by_confidence'].items():
                report.append(f"  {conf:25} {count:>5}")
            report.append("")

        # Potential vs Actual
        report.append("MARKET OPPORTUNITY ANALYSIS")
        report.append("-" * 50)
        est_vehicles = roi.get('estimated_vehicles', 0)
        if est_vehicles > 0:
            avg_rev = severity_info.get('avg_revenue_per_vehicle', 2000)
            for capture in [0.01, 0.05, 0.10]:
                potential_jobs = int(est_vehicles * capture)
                potential_rev = potential_jobs * avg_rev
                report.append(f"  At {capture*100:.0f}% capture: {potential_jobs:,} jobs = ${potential_rev:,.0f}")

            report.append("")
            actual_capture = roi['jobs_created'] / est_vehicles if est_vehicles else 0
            report.append(f"  Actual capture: {actual_capture*100:.4f}% ({roi['jobs_created']} jobs)")
        report.append("")

        report.append("=" * 70)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 70)

        return "\n".join(report)

    def generate_multi_storm_report(self, days: int = 365) -> str:
        """Generate performance report for all storms in period"""
        cutoff = date.today() - timedelta(days=days)
        storms = self.get_all_storms_performance(start_date=cutoff, min_jobs=0)

        report = []
        report.append("=" * 80)
        report.append(f"MULTI-STORM PERFORMANCE REPORT (Last {days} Days)")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 80)
        report.append("")

        # Summary
        total_jobs = sum(s['job_count'] for s in storms)
        total_revenue = sum(s['total_revenue'] for s in storms)
        storms_with_jobs = [s for s in storms if s['job_count'] > 0]

        report.append("SUMMARY")
        report.append("-" * 60)
        report.append(f"Total Storms:         {len(storms)}")
        report.append(f"Storms with Jobs:     {len(storms_with_jobs)}")
        report.append(f"Total Jobs:           {total_jobs}")
        report.append(f"Total Revenue:        ${total_revenue:,.2f}")
        if total_jobs > 0:
            report.append(f"Avg Revenue/Job:      ${total_revenue/total_jobs:,.2f}")
        report.append("")

        # Top performers
        if storms_with_jobs:
            report.append("TOP PERFORMING STORMS (by revenue)")
            report.append("-" * 60)
            report.append(f"{'Storm Name':<35} {'Jobs':>6} {'Revenue':>15}")
            report.append("-" * 60)
            for storm in storms_with_jobs[:10]:
                name = storm['event_name'][:32] + "..." if len(storm['event_name']) > 35 else storm['event_name']
                report.append(f"{name:<35} {storm['job_count']:>6} ${storm['total_revenue']:>13,.2f}")
            report.append("")

        # By severity
        report.append("BY SEVERITY")
        report.append("-" * 60)
        severity_stats = {}
        for storm in storms:
            sev = storm.get('severity', 'UNKNOWN')
            if sev not in severity_stats:
                severity_stats[sev] = {'count': 0, 'jobs': 0, 'revenue': 0}
            severity_stats[sev]['count'] += 1
            severity_stats[sev]['jobs'] += storm['job_count']
            severity_stats[sev]['revenue'] += storm['total_revenue']

        for sev in ['CATASTROPHIC', 'SEVERE', 'MODERATE', 'MINOR']:
            if sev in severity_stats:
                s = severity_stats[sev]
                report.append(f"  {sev:15} {s['count']:>3} storms  {s['jobs']:>5} jobs  ${s['revenue']:>12,.2f}")
        report.append("")

        return "\n".join(report)
