"""
Field Sales Manager
Mobile app functionality for door-to-door sales team

FEATURES:
- Daily check-in/check-out
- Real-time location tracking
- Customer interaction logging
- Performance metrics
- Team leaderboard
- Commission tracking
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json


class FieldSalesManager:
    """
    Manage field sales operations and mobile app functionality

    Door-to-door sales team tools for hail damage canvassing
    """

    def __init__(self, db):
        self.db = db
        self._ensure_field_sales_tables()

    def _ensure_field_sales_tables(self):
        """Ensure field sales tables exist"""
        # Activity sessions (check-in/check-out)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sales_activity_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                check_in_time TIMESTAMP NOT NULL,
                check_in_lat REAL,
                check_in_lon REAL,
                check_in_notes TEXT,
                check_out_time TIMESTAMP,
                check_out_lat REAL,
                check_out_lon REAL,
                check_out_notes TEXT,
                daily_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id)
            )
        """)

        # Location tracking
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS salesperson_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy_meters REAL,
                activity_type TEXT DEFAULT 'CANVASSING',
                logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id)
            )
        """)

        # Customer interactions
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS customer_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                interaction_type TEXT NOT NULL,
                location_lat REAL,
                location_lon REAL,
                outcome TEXT,
                customer_name TEXT,
                customer_phone TEXT,
                customer_address TEXT,
                notes TEXT,
                lead_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id)
            )
        """)

        # Sales commissions
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sales_commissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                lead_id INTEGER,
                job_id INTEGER,
                invoice_id INTEGER,
                invoice_total REAL NOT NULL,
                commission_rate REAL NOT NULL,
                commission_amount REAL NOT NULL,
                status TEXT DEFAULT 'PENDING',
                paid_date DATE,
                payment_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id)
            )
        """)

    # ========================================================================
    # DAILY CHECK-IN/CHECK-OUT
    # ========================================================================

    def check_in(
        self,
        salesperson_id: int,
        location_lat: float,
        location_lon: float,
        notes: Optional[str] = None
    ) -> int:
        """
        Check in salesperson for the day

        Args:
            salesperson_id: Salesperson ID
            location_lat: Check-in location latitude
            location_lon: Check-in location longitude
            notes: Check-in notes

        Returns:
            Activity session ID
        """
        result = self.db.execute("""
            INSERT INTO sales_activity_sessions (
                salesperson_id, check_in_time,
                check_in_lat, check_in_lon,
                check_in_notes, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            datetime.now().isoformat(),
            location_lat,
            location_lon,
            notes,
            'ACTIVE'
        ])

        session_id = result[0]['id']

        # Log initial location
        self.log_location(salesperson_id, location_lat, location_lon, activity_type='CHECK_IN')

        return session_id

    def check_out(
        self,
        session_id: int,
        location_lat: float,
        location_lon: float,
        daily_summary: Dict,
        notes: Optional[str] = None
    ) -> bool:
        """
        Check out salesperson

        Args:
            session_id: Activity session ID
            location_lat: Check-out location latitude
            location_lon: Check-out location longitude
            daily_summary: Summary of day's activities
            notes: Check-out notes

        Example daily_summary:
            {
                'doors_knocked': 45,
                'conversations': 28,
                'leads_generated': 8,
                'appointments_set': 3,
                'miles_driven': 15.2
            }
        """
        self.db.execute("""
            UPDATE sales_activity_sessions
            SET check_out_time = ?,
                check_out_lat = ?,
                check_out_lon = ?,
                check_out_notes = ?,
                daily_summary = ?,
                status = 'COMPLETED'
            WHERE id = ?
        """, [
            datetime.now().isoformat(),
            location_lat,
            location_lon,
            notes,
            json.dumps(daily_summary),
            session_id
        ])

        # Get salesperson ID and log final location
        session = self.get_session(session_id)
        if session:
            self.log_location(
                session['salesperson_id'],
                location_lat, location_lon,
                activity_type='CHECK_OUT'
            )

        return True

    def get_session(self, session_id: int) -> Optional[Dict]:
        """Get activity session by ID"""
        results = self.db.execute(
            "SELECT * FROM sales_activity_sessions WHERE id = ?",
            [session_id]
        )
        if results:
            session = results[0]
            if session.get('daily_summary'):
                try:
                    session['daily_summary'] = json.loads(session['daily_summary'])
                except:
                    pass
            return session
        return None

    def get_active_session(self, salesperson_id: int) -> Optional[Dict]:
        """Get current active session for salesperson"""
        today = date.today().isoformat()
        results = self.db.execute("""
            SELECT * FROM sales_activity_sessions
            WHERE salesperson_id = ?
              AND DATE(check_in_time) = ?
              AND status = 'ACTIVE'
            ORDER BY check_in_time DESC
            LIMIT 1
        """, [salesperson_id, today])

        return results[0] if results else None

    def get_sessions_by_date(
        self,
        salesperson_id: int,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get activity sessions for date range"""
        sessions = self.db.execute("""
            SELECT * FROM sales_activity_sessions
            WHERE salesperson_id = ?
              AND DATE(check_in_time) BETWEEN ? AND ?
            ORDER BY check_in_time DESC
        """, [
            salesperson_id,
            start_date.isoformat(),
            end_date.isoformat()
        ])

        for session in sessions:
            if session.get('daily_summary'):
                try:
                    session['daily_summary'] = json.loads(session['daily_summary'])
                except:
                    pass

        return sessions

    # ========================================================================
    # LOCATION TRACKING
    # ========================================================================

    def log_location(
        self,
        salesperson_id: int,
        latitude: float,
        longitude: float,
        accuracy_meters: Optional[float] = None,
        activity_type: str = 'CANVASSING'
    ) -> int:
        """
        Log salesperson location (GPS ping)

        Args:
            salesperson_id: Salesperson ID
            latitude: Current latitude
            longitude: Current longitude
            accuracy_meters: GPS accuracy in meters
            activity_type: CANVASSING, TRAVELING, BREAK, CHECK_IN, CHECK_OUT

        Returns:
            Location log ID
        """
        result = self.db.execute("""
            INSERT INTO salesperson_locations (
                salesperson_id, latitude, longitude,
                accuracy_meters, activity_type
            ) VALUES (?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            latitude,
            longitude,
            accuracy_meters,
            activity_type
        ])

        return result[0]['id']

    def get_salesperson_location(self, salesperson_id: int) -> Optional[Dict]:
        """Get current (most recent) location of salesperson"""
        results = self.db.execute("""
            SELECT * FROM salesperson_locations
            WHERE salesperson_id = ?
            ORDER BY logged_at DESC
            LIMIT 1
        """, [salesperson_id])

        return results[0] if results else None

    def get_all_active_locations(self) -> List[Dict]:
        """Get current locations of all active salespeople (checked in today)"""
        today = date.today().isoformat()

        # Get salespeople who checked in today and are still active
        active_sessions = self.db.execute("""
            SELECT salesperson_id FROM sales_activity_sessions
            WHERE DATE(check_in_time) = ?
              AND status = 'ACTIVE'
        """, [today])

        locations = []

        for session in active_sessions:
            salesperson_id = session['salesperson_id']
            location = self.get_salesperson_location(salesperson_id)

            if location:
                # Get salesperson info
                salesperson = self.db.execute(
                    "SELECT * FROM salespeople WHERE id = ?",
                    [salesperson_id]
                )

                if salesperson:
                    sp = salesperson[0]
                    locations.append({
                        'salesperson_id': salesperson_id,
                        'name': f"{sp['first_name']} {sp['last_name']}",
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'last_update': location['logged_at'],
                        'activity_type': location['activity_type']
                    })

        return locations

    def get_location_history(
        self,
        salesperson_id: int,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get location history for salesperson"""
        if not end_time:
            end_time = datetime.now()

        return self.db.execute("""
            SELECT * FROM salesperson_locations
            WHERE salesperson_id = ?
              AND logged_at BETWEEN ? AND ?
            ORDER BY logged_at
        """, [
            salesperson_id,
            start_time.isoformat(),
            end_time.isoformat()
        ])

    # ========================================================================
    # CUSTOMER INTERACTIONS
    # ========================================================================

    def log_customer_interaction(
        self,
        salesperson_id: int,
        interaction_type: str,
        location_lat: float,
        location_lon: float,
        outcome: str,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_address: Optional[str] = None,
        notes: Optional[str] = None,
        lead_id: Optional[int] = None
    ) -> int:
        """
        Log customer interaction

        Args:
            salesperson_id: Salesperson ID
            interaction_type: DOOR_KNOCK, CONVERSATION, APPOINTMENT_SET, NO_ANSWER
            location_lat: Interaction latitude
            location_lon: Interaction longitude
            outcome: SUCCESS, REJECTION, NO_ANSWER, FOLLOW_UP, NOT_INTERESTED
            customer_name: Customer name (if obtained)
            customer_phone: Customer phone
            customer_address: Property address
            notes: Interaction notes
            lead_id: Lead ID if created

        Returns:
            Interaction ID
        """
        result = self.db.execute("""
            INSERT INTO customer_interactions (
                salesperson_id, interaction_type,
                location_lat, location_lon,
                outcome, customer_name, customer_phone,
                customer_address, notes, lead_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            interaction_type,
            location_lat,
            location_lon,
            outcome,
            customer_name,
            customer_phone,
            customer_address,
            notes,
            lead_id
        ])

        return result[0]['id']

    def get_interactions_today(self, salesperson_id: int) -> List[Dict]:
        """Get today's interactions for salesperson"""
        today = date.today().isoformat()

        return self.db.execute("""
            SELECT * FROM customer_interactions
            WHERE salesperson_id = ?
              AND DATE(created_at) = ?
            ORDER BY created_at DESC
        """, [salesperson_id, today])

    def get_interaction_stats(
        self,
        salesperson_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get interaction statistics for period"""
        stats = self.db.execute("""
            SELECT
                COUNT(*) as total_interactions,
                SUM(CASE WHEN interaction_type = 'DOOR_KNOCK' THEN 1 ELSE 0 END) as door_knocks,
                SUM(CASE WHEN interaction_type = 'CONVERSATION' THEN 1 ELSE 0 END) as conversations,
                SUM(CASE WHEN interaction_type = 'APPOINTMENT_SET' THEN 1 ELSE 0 END) as appointments,
                SUM(CASE WHEN outcome = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN outcome = 'NO_ANSWER' THEN 1 ELSE 0 END) as no_answers,
                SUM(CASE WHEN lead_id IS NOT NULL THEN 1 ELSE 0 END) as leads_created
            FROM customer_interactions
            WHERE salesperson_id = ?
              AND DATE(created_at) BETWEEN ? AND ?
        """, [
            salesperson_id,
            start_date.isoformat(),
            end_date.isoformat()
        ])

        result = stats[0] if stats else {}

        total = result.get('total_interactions', 0) or 0
        door_knocks = result.get('door_knocks', 0) or 0
        conversations = result.get('conversations', 0) or 0

        return {
            'total_interactions': total,
            'door_knocks': door_knocks,
            'conversations': conversations,
            'appointments': result.get('appointments', 0) or 0,
            'successful': result.get('successful', 0) or 0,
            'no_answers': result.get('no_answers', 0) or 0,
            'leads_created': result.get('leads_created', 0) or 0,
            'conversation_rate': round((conversations / door_knocks * 100), 1) if door_knocks > 0 else 0
        }

    # ========================================================================
    # PERFORMANCE METRICS
    # ========================================================================

    def get_salesperson_performance(
        self,
        salesperson_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """
        Get comprehensive salesperson performance metrics

        Args:
            salesperson_id: Salesperson ID
            start_date: Period start
            end_date: Period end

        Returns:
            Performance metrics
        """
        # Get salesperson info
        salesperson = self.db.execute(
            "SELECT * FROM salespeople WHERE id = ?",
            [salesperson_id]
        )

        if not salesperson:
            return {}

        sp = salesperson[0]

        # Get activity sessions
        sessions = self.get_sessions_by_date(salesperson_id, start_date, end_date)

        # Calculate totals from sessions
        total_doors = 0
        total_conversations = 0
        total_miles = 0

        for session in sessions:
            summary = session.get('daily_summary') or {}
            total_doors += summary.get('doors_knocked', 0)
            total_conversations += summary.get('conversations', 0)
            total_miles += summary.get('miles_driven', 0)

        total_days_worked = len([s for s in sessions if s['status'] == 'COMPLETED'])

        # Get leads generated
        leads = self.db.execute("""
            SELECT
                COUNT(*) as count,
                SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted
            FROM field_leads
            WHERE salesperson_id = ?
              AND DATE(created_at) BETWEEN ? AND ?
        """, [salesperson_id, start_date.isoformat(), end_date.isoformat()])

        leads_count = leads[0]['count'] if leads else 0
        leads_converted = leads[0]['converted'] if leads else 0

        # Get commissions
        commissions = self.db.execute("""
            SELECT
                COALESCE(SUM(invoice_total), 0) as total_revenue,
                COALESCE(SUM(commission_amount), 0) as total_commission
            FROM sales_commissions
            WHERE salesperson_id = ?
              AND DATE(created_at) BETWEEN ? AND ?
        """, [salesperson_id, start_date.isoformat(), end_date.isoformat()])

        comm = commissions[0] if commissions else {}
        total_revenue = comm.get('total_revenue', 0) or 0
        total_commission = comm.get('total_commission', 0) or 0

        return {
            'salesperson_id': salesperson_id,
            'name': f"{sp['first_name']} {sp['last_name']}",
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days_worked': total_days_worked
            },
            'activity': {
                'doors_knocked': total_doors,
                'conversations': total_conversations,
                'miles_driven': round(total_miles, 1),
                'doors_per_day': round(total_doors / total_days_worked, 1) if total_days_worked > 0 else 0,
                'conversation_rate': round((total_conversations / total_doors * 100), 1) if total_doors > 0 else 0
            },
            'leads': {
                'total_generated': leads_count,
                'converted': leads_converted,
                'conversion_rate': round((leads_converted / leads_count * 100), 1) if leads_count > 0 else 0,
                'leads_per_day': round(leads_count / total_days_worked, 1) if total_days_worked > 0 else 0
            },
            'revenue': {
                'total_revenue': total_revenue,
                'commission_earned': total_commission,
                'revenue_per_lead': round(total_revenue / leads_count, 2) if leads_count > 0 else 0,
                'revenue_per_day': round(total_revenue / total_days_worked, 2) if total_days_worked > 0 else 0
            }
        }

    def get_team_leaderboard(
        self,
        start_date: date,
        end_date: date,
        metric: str = 'REVENUE'
    ) -> List[Dict]:
        """
        Get sales team leaderboard

        Args:
            start_date: Period start
            end_date: Period end
            metric: REVENUE, LEADS, CONVERSIONS, DOORS

        Returns:
            Ranked list of salespeople
        """
        salespeople = self.db.execute(
            "SELECT * FROM salespeople WHERE status = 'ACTIVE'"
        )

        leaderboard = []

        for sp in salespeople:
            perf = self.get_salesperson_performance(sp['id'], start_date, end_date)

            if not perf:
                continue

            if metric == 'REVENUE':
                score = perf['revenue']['total_revenue']
            elif metric == 'LEADS':
                score = perf['leads']['total_generated']
            elif metric == 'CONVERSIONS':
                score = perf['leads']['converted']
            else:  # DOORS
                score = perf['activity']['doors_knocked']

            leaderboard.append({
                'salesperson_id': sp['id'],
                'name': perf['name'],
                'score': score,
                'metric': metric,
                'performance': perf
            })

        # Sort by score descending
        leaderboard.sort(key=lambda x: x['score'], reverse=True)

        # Add rank
        for i, entry in enumerate(leaderboard):
            entry['rank'] = i + 1

        return leaderboard

    def get_today_summary(self, salesperson_id: int) -> Dict:
        """Get today's activity summary for salesperson"""
        today = date.today()

        # Check if checked in
        session = self.get_active_session(salesperson_id)

        # Get today's interactions
        interactions = self.get_interaction_stats(salesperson_id, today, today)

        # Get today's leads
        leads = self.db.execute("""
            SELECT COUNT(*) as count
            FROM field_leads
            WHERE salesperson_id = ?
              AND DATE(created_at) = ?
        """, [salesperson_id, today.isoformat()])

        return {
            'date': today.isoformat(),
            'checked_in': session is not None,
            'session_id': session['id'] if session else None,
            'check_in_time': session['check_in_time'] if session else None,
            'interactions': interactions,
            'leads_generated': leads[0]['count'] if leads else 0
        }

    # ========================================================================
    # COMMISSION TRACKING
    # ========================================================================

    def calculate_commission(
        self,
        salesperson_id: int,
        lead_id: int,
        job_id: int,
        invoice_id: int,
        invoice_total: float
    ) -> int:
        """
        Calculate and record commission for a converted lead

        Args:
            salesperson_id: Salesperson ID
            lead_id: Original lead ID
            job_id: Job ID
            invoice_id: Invoice ID
            invoice_total: Invoice total amount

        Returns:
            Commission record ID
        """
        # Get salesperson commission rate
        salesperson = self.db.execute(
            "SELECT commission_rate FROM salespeople WHERE id = ?",
            [salesperson_id]
        )

        if not salesperson:
            return 0

        commission_rate = salesperson[0]['commission_rate']
        commission_amount = invoice_total * commission_rate

        result = self.db.execute("""
            INSERT INTO sales_commissions (
                salesperson_id, lead_id, job_id, invoice_id,
                invoice_total, commission_rate, commission_amount,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            lead_id,
            job_id,
            invoice_id,
            invoice_total,
            commission_rate,
            commission_amount,
            'PENDING'
        ])

        return result[0]['id']

    def get_pending_commissions(
        self,
        salesperson_id: Optional[int] = None
    ) -> List[Dict]:
        """Get pending commissions"""
        query = "SELECT * FROM sales_commissions WHERE status = 'PENDING'"
        params = []

        if salesperson_id:
            query += " AND salesperson_id = ?"
            params.append(salesperson_id)

        query += " ORDER BY created_at DESC"

        return self.db.execute(query, params) if params else self.db.execute(query)

    def mark_commission_paid(
        self,
        commission_id: int,
        payment_reference: str
    ) -> bool:
        """Mark commission as paid"""
        self.db.execute("""
            UPDATE sales_commissions
            SET status = 'PAID',
                paid_date = ?,
                payment_reference = ?
            WHERE id = ?
        """, [
            date.today().isoformat(),
            payment_reference,
            commission_id
        ])

        return True

    def get_commission_summary(
        self,
        salesperson_id: int,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get commission summary for period"""
        stats = self.db.execute("""
            SELECT
                COUNT(*) as total_commissions,
                COALESCE(SUM(invoice_total), 0) as total_sales,
                COALESCE(SUM(commission_amount), 0) as total_commission,
                COALESCE(SUM(CASE WHEN status = 'PAID' THEN commission_amount ELSE 0 END), 0) as paid,
                COALESCE(SUM(CASE WHEN status = 'PENDING' THEN commission_amount ELSE 0 END), 0) as pending
            FROM sales_commissions
            WHERE salesperson_id = ?
              AND DATE(created_at) BETWEEN ? AND ?
        """, [
            salesperson_id,
            start_date.isoformat(),
            end_date.isoformat()
        ])

        result = stats[0] if stats else {}

        return {
            'salesperson_id': salesperson_id,
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'total_commissions': result.get('total_commissions', 0) or 0,
            'total_sales': result.get('total_sales', 0) or 0,
            'total_commission': result.get('total_commission', 0) or 0,
            'paid': result.get('paid', 0) or 0,
            'pending': result.get('pending', 0) or 0
        }

    # ========================================================================
    # MOBILE APP FUNCTIONS
    # ========================================================================

    def get_today_assignment(self, salesperson_id: int) -> Dict:
        """
        Get today's territory assignment for mobile app

        Returns all info needed for field work
        """
        today = date.today()

        # Get assigned territories
        territories = self.db.execute("""
            SELECT sgc.*, hs.swath_name, hs.severity
            FROM sales_grid_cells sgc
            JOIN hail_swaths hs ON hs.id = sgc.swath_id
            WHERE sgc.assigned_to = ?
              AND sgc.status = 'ASSIGNED'
        """, [salesperson_id])

        # Get today's session
        session = self.get_active_session(salesperson_id)

        # Get today's leads count
        today_leads = self.db.execute("""
            SELECT COUNT(*) as count
            FROM field_leads
            WHERE salesperson_id = ?
              AND DATE(created_at) = ?
        """, [salesperson_id, today.isoformat()])

        # Get today's interactions
        today_interactions = self.db.execute("""
            SELECT COUNT(*) as count
            FROM customer_interactions
            WHERE salesperson_id = ?
              AND DATE(created_at) = ?
        """, [salesperson_id, today.isoformat()])

        return {
            'salesperson_id': salesperson_id,
            'date': today.isoformat(),
            'checked_in': session is not None,
            'session_id': session['id'] if session else None,
            'check_in_time': session['check_in_time'] if session else None,
            'territories': territories,
            'territory_count': len(territories),
            'today_stats': {
                'leads_generated': today_leads[0]['count'] if today_leads else 0,
                'interactions': today_interactions[0]['count'] if today_interactions else 0
            }
        }

    def quick_lead_capture(
        self,
        salesperson_id: int,
        name: str,
        phone: str,
        address: str,
        latitude: float,
        longitude: float
    ) -> int:
        """
        Quick lead capture (minimal info)

        For rapid door-to-door capture when speed is essential
        """
        # Find which grid cell this is in (get most recent assigned cell)
        grid_cell = self.db.execute("""
            SELECT id FROM sales_grid_cells
            WHERE assigned_to = ?
              AND status = 'ASSIGNED'
            ORDER BY id DESC
            LIMIT 1
        """, [salesperson_id])

        grid_cell_id = grid_cell[0]['id'] if grid_cell else None

        # Parse name
        name_parts = name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Create minimal lead
        result = self.db.execute("""
            INSERT INTO field_leads (
                salesperson_id, grid_cell_id,
                customer_info, vehicle_info, insurance_info,
                damage_assessment, location_lat, location_lon,
                lead_quality, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            grid_cell_id,
            json.dumps({
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'address': address
            }),
            json.dumps({}),
            json.dumps({}),
            json.dumps({'estimated_cost': 0}),
            latitude,
            longitude,
            'WARM',
            'NEW'
        ])

        lead_id = result[0]['id']

        # Log the interaction
        self.log_customer_interaction(
            salesperson_id=salesperson_id,
            interaction_type='CONVERSATION',
            location_lat=latitude,
            location_lon=longitude,
            outcome='SUCCESS',
            customer_name=name,
            customer_phone=phone,
            customer_address=address,
            lead_id=lead_id
        )

        return lead_id

    def get_nearby_leads(
        self,
        latitude: float,
        longitude: float,
        radius_miles: float = 0.5
    ) -> List[Dict]:
        """
        Get leads near a location

        Useful for finding nearby prospects while canvassing
        """
        # Simple bounding box calculation
        lat_delta = radius_miles / 69.0
        lon_delta = radius_miles / 69.0

        leads = self.db.execute("""
            SELECT fl.*, s.first_name as salesperson_first, s.last_name as salesperson_last
            FROM field_leads fl
            JOIN salespeople s ON fl.salesperson_id = s.id
            WHERE fl.location_lat BETWEEN ? AND ?
              AND fl.location_lon BETWEEN ? AND ?
            ORDER BY fl.created_at DESC
        """, [
            latitude - lat_delta,
            latitude + lat_delta,
            longitude - lon_delta,
            longitude + lon_delta
        ])

        # Parse JSON fields
        for lead in leads:
            for field in ['customer_info', 'vehicle_info', 'damage_assessment']:
                if lead.get(field):
                    try:
                        lead[field] = json.loads(lead[field])
                    except:
                        pass

        return leads
