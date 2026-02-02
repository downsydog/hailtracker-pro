"""
Scheduling Manager
PDR CRM Part 9 - Appointment Scheduling & Capacity Management

FEATURES:
- Appointment scheduling (drop-off/pickup times)
- Available slot calculation
- Business hours enforcement (Mon-Sat configurable)
- Capacity management (max appointments per slot)
- Tech capacity tracking (max concurrent jobs)
- Conflict detection (overbooked slots, tech overload)
- Schedule views (daily, weekly, by tech)
- Utilization tracking
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta, time
import json


class SchedulingManager:
    """
    Manage shop scheduling and appointments

    Handles drop-off/pickup scheduling, tech capacity, and availability
    """

    # Default business hours (can be overridden per location)
    DEFAULT_BUSINESS_HOURS = {
        0: {'open': '08:00', 'close': '17:00', 'enabled': True},   # Monday
        1: {'open': '08:00', 'close': '17:00', 'enabled': True},   # Tuesday
        2: {'open': '08:00', 'close': '17:00', 'enabled': True},   # Wednesday
        3: {'open': '08:00', 'close': '17:00', 'enabled': True},   # Thursday
        4: {'open': '08:00', 'close': '17:00', 'enabled': True},   # Friday
        5: {'open': '08:00', 'close': '14:00', 'enabled': True},   # Saturday (half day)
        6: {'open': '00:00', 'close': '00:00', 'enabled': False},  # Sunday (closed)
    }

    # Appointment types
    APPOINTMENT_TYPES = ['DROP_OFF', 'PICKUP', 'ESTIMATE', 'ADJUSTER', 'OTHER']

    # Default slot duration in minutes
    DEFAULT_SLOT_DURATION = 30

    # Default max appointments per slot
    DEFAULT_MAX_PER_SLOT = 4

    def __init__(self, db, business_hours: Dict = None, slot_duration: int = None, max_per_slot: int = None):
        """
        Initialize scheduling manager

        Args:
            db: Database connection
            business_hours: Override default business hours
            slot_duration: Minutes per slot (default 30)
            max_per_slot: Max appointments per slot (default 4)
        """
        self.db = db
        self.business_hours = business_hours or self.DEFAULT_BUSINESS_HOURS
        self.slot_duration = slot_duration or self.DEFAULT_SLOT_DURATION
        self.max_per_slot = max_per_slot or self.DEFAULT_MAX_PER_SLOT

        # Ensure appointments table exists
        self._ensure_appointments_table()

    def _ensure_appointments_table(self):
        """Create appointments table if it doesn't exist"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Relationships
                job_id INTEGER,
                customer_id INTEGER,
                vehicle_id INTEGER,
                tech_id INTEGER,
                location_id INTEGER,

                -- Appointment Details
                appointment_type TEXT NOT NULL,  -- DROP_OFF, PICKUP, ESTIMATE, ADJUSTER, OTHER
                appointment_date DATE NOT NULL,
                start_time TEXT NOT NULL,  -- HH:MM format
                end_time TEXT NOT NULL,    -- HH:MM format
                duration_minutes INTEGER DEFAULT 30,

                -- Status
                status TEXT DEFAULT 'SCHEDULED',  -- SCHEDULED, CONFIRMED, ARRIVED, COMPLETED, CANCELLED, NO_SHOW

                -- Contact
                contact_name TEXT,
                contact_phone TEXT,
                contact_email TEXT,

                -- Notifications
                reminder_sent INTEGER DEFAULT 0,
                confirmation_sent INTEGER DEFAULT 0,

                -- Notes
                notes TEXT,
                internal_notes TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                cancelled_at TIMESTAMP,
                cancelled_reason TEXT,

                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (customer_id) REFERENCES customers(id),
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
                FOREIGN KEY (tech_id) REFERENCES technicians(id),
                FOREIGN KEY (location_id) REFERENCES locations(id)
            )
        """)

        # Create indexes
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_date
            ON appointments(appointment_date)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_job
            ON appointments(job_id)
        """)
        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_status
            ON appointments(status)
        """)

    # ========================================================================
    # APPOINTMENT CREATION & MANAGEMENT
    # ========================================================================

    def schedule_appointment(
        self,
        appointment_type: str,
        appointment_date: date,
        start_time: str,
        job_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        vehicle_id: Optional[int] = None,
        tech_id: Optional[int] = None,
        location_id: Optional[int] = None,
        duration_minutes: Optional[int] = None,
        contact_name: Optional[str] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
        force: bool = False
    ) -> int:
        """
        Schedule a new appointment

        Args:
            appointment_type: DROP_OFF, PICKUP, ESTIMATE, ADJUSTER, OTHER
            appointment_date: Date of appointment
            start_time: Start time in HH:MM format
            job_id: Related job ID
            customer_id: Customer ID
            vehicle_id: Vehicle ID
            tech_id: Assigned technician (optional)
            location_id: Shop location
            duration_minutes: Appointment duration (default 30)
            force: Skip availability check

        Returns:
            Appointment ID
        """
        if appointment_type not in self.APPOINTMENT_TYPES:
            raise ValueError(f"Invalid appointment type: {appointment_type}")

        duration = duration_minutes or self.slot_duration

        # Calculate end time
        start_dt = datetime.strptime(start_time, '%H:%M')
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.strftime('%H:%M')

        # Check availability (unless forced)
        if not force:
            # Check business hours
            if not self._is_within_business_hours(appointment_date, start_time, end_time):
                raise ValueError(f"Appointment time {start_time}-{end_time} is outside business hours")

            # Check slot availability
            slot_count = self._get_slot_appointment_count(
                appointment_date, start_time, end_time, location_id
            )
            if slot_count >= self.max_per_slot:
                raise ValueError(
                    f"Slot {start_time}-{end_time} is fully booked "
                    f"({slot_count}/{self.max_per_slot} appointments)"
                )

            # Check tech availability if assigned
            if tech_id:
                if not self._is_tech_available(tech_id, appointment_date, start_time, end_time):
                    raise ValueError(f"Tech #{tech_id} is not available at {start_time}")

        # Get customer/vehicle info from job if not provided
        if job_id and (not customer_id or not vehicle_id):
            job = self.db.execute("""
                SELECT customer_id, vehicle_id FROM jobs WHERE id = ?
            """, (job_id,))
            if job:
                customer_id = customer_id or job[0]['customer_id']
                vehicle_id = vehicle_id or job[0]['vehicle_id']

        # Get contact info from customer if not provided
        if customer_id and not contact_name:
            customer = self.db.execute("""
                SELECT first_name, last_name, phone, email FROM customers WHERE id = ?
            """, (customer_id,))
            if customer:
                contact_name = f"{customer[0]['first_name']} {customer[0]['last_name']}"
                contact_phone = contact_phone or customer[0]['phone']
                contact_email = contact_email or customer[0]['email']

        # Insert appointment
        appointment_id = self.db.insert('appointments', {
            'appointment_type': appointment_type,
            'appointment_date': appointment_date.isoformat() if isinstance(appointment_date, date) else appointment_date,
            'start_time': start_time,
            'end_time': end_time,
            'duration_minutes': duration,
            'job_id': job_id,
            'customer_id': customer_id,
            'vehicle_id': vehicle_id,
            'tech_id': tech_id,
            'location_id': location_id,
            'contact_name': contact_name,
            'contact_phone': contact_phone,
            'contact_email': contact_email,
            'notes': notes,
            'created_by': created_by,
            'status': 'SCHEDULED'
        })

        # Update job scheduled times if this is a drop-off or pickup
        if job_id:
            appointment_datetime = f"{appointment_date} {start_time}:00"
            if appointment_type == 'DROP_OFF':
                self.db.execute("""
                    UPDATE jobs SET scheduled_drop_off = ?, updated_at = ? WHERE id = ?
                """, (appointment_datetime, datetime.now().isoformat(), job_id))
            elif appointment_type == 'PICKUP':
                self.db.execute("""
                    UPDATE jobs SET scheduled_pickup = ?, updated_at = ? WHERE id = ?
                """, (appointment_datetime, datetime.now().isoformat(), job_id))

        print(f"[OK] Scheduled {appointment_type} appointment #{appointment_id}")
        print(f"     Date: {appointment_date}, Time: {start_time}-{end_time}")
        if contact_name:
            print(f"     Contact: {contact_name}")

        return appointment_id

    def get_appointment(self, appointment_id: int) -> Optional[Dict]:
        """Get appointment details"""
        results = self.db.execute("""
            SELECT
                a.*,
                c.first_name || ' ' || c.last_name as customer_name,
                c.phone as customer_phone,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                j.job_number,
                j.status as job_status,
                t.first_name || ' ' || t.last_name as tech_name
            FROM appointments a
            LEFT JOIN customers c ON c.id = a.customer_id
            LEFT JOIN vehicles v ON v.id = a.vehicle_id
            LEFT JOIN jobs j ON j.id = a.job_id
            LEFT JOIN technicians t ON t.id = a.tech_id
            WHERE a.id = ?
        """, (appointment_id,))

        return results[0] if results else None

    def update_appointment(
        self,
        appointment_id: int,
        appointment_date: Optional[date] = None,
        start_time: Optional[str] = None,
        duration_minutes: Optional[int] = None,
        tech_id: Optional[int] = None,
        notes: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Update appointment time or details

        Args:
            appointment_id: Appointment to update
            appointment_date: New date (optional)
            start_time: New start time (optional)
            force: Skip availability check
        """
        appointment = self.get_appointment(appointment_id)
        if not appointment:
            raise ValueError(f"Appointment {appointment_id} not found")

        # Build update data
        update_data = {'updated_at': datetime.now().isoformat()}

        new_date = appointment_date or appointment['appointment_date']
        new_start = start_time or appointment['start_time']
        new_duration = duration_minutes or appointment['duration_minutes']

        # Calculate new end time
        start_dt = datetime.strptime(new_start, '%H:%M')
        end_dt = start_dt + timedelta(minutes=new_duration)
        new_end = end_dt.strftime('%H:%M')

        # Check availability if time changed
        if not force and (appointment_date or start_time or duration_minutes):
            if not self._is_within_business_hours(new_date, new_start, new_end):
                raise ValueError(f"New time {new_start}-{new_end} is outside business hours")

        if appointment_date:
            update_data['appointment_date'] = appointment_date.isoformat() if isinstance(appointment_date, date) else appointment_date
        if start_time:
            update_data['start_time'] = start_time
            update_data['end_time'] = new_end
        if duration_minutes:
            update_data['duration_minutes'] = duration_minutes
            update_data['end_time'] = new_end
        if tech_id is not None:
            update_data['tech_id'] = tech_id
        if notes is not None:
            update_data['notes'] = notes

        self.db.update('appointments', appointment_id, update_data)

        # Update job if drop-off/pickup
        if appointment['job_id'] and (appointment_date or start_time):
            final_date = update_data.get('appointment_date', appointment['appointment_date'])
            final_time = update_data.get('start_time', appointment['start_time'])
            appointment_datetime = f"{final_date} {final_time}:00"

            if appointment['appointment_type'] == 'DROP_OFF':
                self.db.execute("""
                    UPDATE jobs SET scheduled_drop_off = ?, updated_at = ? WHERE id = ?
                """, (appointment_datetime, datetime.now().isoformat(), appointment['job_id']))
            elif appointment['appointment_type'] == 'PICKUP':
                self.db.execute("""
                    UPDATE jobs SET scheduled_pickup = ?, updated_at = ? WHERE id = ?
                """, (appointment_datetime, datetime.now().isoformat(), appointment['job_id']))

        print(f"[OK] Updated appointment #{appointment_id}")
        return True

    def cancel_appointment(
        self,
        appointment_id: int,
        reason: Optional[str] = None,
        cancelled_by: Optional[str] = None
    ) -> bool:
        """Cancel an appointment"""
        self.db.execute("""
            UPDATE appointments
            SET status = 'CANCELLED',
                cancelled_at = ?,
                cancelled_reason = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            reason,
            datetime.now().isoformat(),
            appointment_id
        ))

        print(f"[OK] Cancelled appointment #{appointment_id}")
        if reason:
            print(f"     Reason: {reason}")

        return True

    def update_status(
        self,
        appointment_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update appointment status"""
        valid_statuses = ['SCHEDULED', 'CONFIRMED', 'ARRIVED', 'COMPLETED', 'CANCELLED', 'NO_SHOW']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}")

        update_data = {
            'status': status,
            'updated_at': datetime.now().isoformat()
        }

        if notes:
            appointment = self.get_appointment(appointment_id)
            current_notes = appointment.get('internal_notes', '') or ''
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            new_note = f"[{timestamp}] {status}: {notes}"
            update_data['internal_notes'] = f"{current_notes}\n{new_note}".strip()

        self.db.update('appointments', appointment_id, update_data)

        print(f"[OK] Updated appointment #{appointment_id} status to {status}")
        return True

    def mark_arrived(self, appointment_id: int) -> bool:
        """Mark customer as arrived for appointment"""
        return self.update_status(appointment_id, 'ARRIVED', 'Customer arrived')

    def mark_completed(self, appointment_id: int) -> bool:
        """Mark appointment as completed"""
        return self.update_status(appointment_id, 'COMPLETED')

    def mark_no_show(self, appointment_id: int) -> bool:
        """Mark customer as no-show"""
        return self.update_status(appointment_id, 'NO_SHOW', 'Customer did not arrive')

    # ========================================================================
    # AVAILABILITY & SLOT MANAGEMENT
    # ========================================================================

    def get_available_slots(
        self,
        target_date: date,
        appointment_type: str = 'DROP_OFF',
        duration_minutes: Optional[int] = None,
        location_id: Optional[int] = None,
        tech_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get available appointment slots for a date

        Args:
            target_date: Date to check
            appointment_type: Type of appointment
            duration_minutes: Required duration
            location_id: Specific location
            tech_id: Specific technician

        Returns:
            List of available slots with times and remaining capacity
        """
        duration = duration_minutes or self.slot_duration

        # Get business hours for this day
        day_of_week = target_date.weekday()
        hours = self.business_hours.get(day_of_week, {})

        if not hours.get('enabled', False):
            return []  # Closed this day

        open_time = datetime.strptime(hours['open'], '%H:%M')
        close_time = datetime.strptime(hours['close'], '%H:%M')

        # Generate all possible slots
        slots = []
        current_time = open_time

        while current_time + timedelta(minutes=duration) <= close_time:
            start_str = current_time.strftime('%H:%M')
            end_str = (current_time + timedelta(minutes=duration)).strftime('%H:%M')

            # Count existing appointments in this slot
            appointment_count = self._get_slot_appointment_count(
                target_date, start_str, end_str, location_id
            )

            available_spots = self.max_per_slot - appointment_count

            # Check tech availability if specified
            tech_available = True
            if tech_id and available_spots > 0:
                tech_available = self._is_tech_available(
                    tech_id, target_date, start_str, end_str
                )

            if available_spots > 0 and tech_available:
                slots.append({
                    'start_time': start_str,
                    'end_time': end_str,
                    'available_spots': available_spots,
                    'booked': appointment_count,
                    'tech_available': tech_available
                })

            current_time += timedelta(minutes=self.slot_duration)

        return slots

    def get_next_available_slot(
        self,
        appointment_type: str = 'DROP_OFF',
        duration_minutes: Optional[int] = None,
        location_id: Optional[int] = None,
        start_date: Optional[date] = None,
        days_to_check: int = 14
    ) -> Optional[Dict]:
        """
        Find the next available appointment slot

        Args:
            appointment_type: Type of appointment
            duration_minutes: Required duration
            location_id: Specific location
            start_date: Start checking from this date
            days_to_check: How many days ahead to check

        Returns:
            Next available slot or None
        """
        check_date = start_date or date.today()

        for i in range(days_to_check):
            current_date = check_date + timedelta(days=i)
            slots = self.get_available_slots(
                current_date, appointment_type, duration_minutes, location_id
            )

            if slots:
                return {
                    'date': current_date,
                    'slot': slots[0]
                }

        return None

    def _get_slot_appointment_count(
        self,
        target_date: date,
        start_time: str,
        end_time: str,
        location_id: Optional[int] = None
    ) -> int:
        """Count appointments that overlap with a time slot"""
        date_str = target_date.isoformat() if isinstance(target_date, date) else target_date

        query = """
            SELECT COUNT(*) as count
            FROM appointments
            WHERE appointment_date = ?
              AND status NOT IN ('CANCELLED', 'NO_SHOW')
              AND (
                  (start_time < ? AND end_time > ?)
                  OR (start_time >= ? AND start_time < ?)
              )
        """
        params = [date_str, end_time, start_time, start_time, end_time]

        if location_id:
            query += " AND location_id = ?"
            params.append(location_id)

        result = self.db.execute(query, tuple(params))
        return result[0]['count'] if result else 0

    def _is_within_business_hours(
        self,
        target_date: date,
        start_time: str,
        end_time: str
    ) -> bool:
        """Check if time slot is within business hours"""
        day_of_week = target_date.weekday() if isinstance(target_date, date) else datetime.fromisoformat(target_date).weekday()
        hours = self.business_hours.get(day_of_week, {})

        if not hours.get('enabled', False):
            return False

        open_time = hours['open']
        close_time = hours['close']

        return start_time >= open_time and end_time <= close_time

    def _is_tech_available(
        self,
        tech_id: int,
        target_date: date,
        start_time: str,
        end_time: str
    ) -> bool:
        """Check if tech is available at specified time"""
        date_str = target_date.isoformat() if isinstance(target_date, date) else target_date

        # Check for conflicting appointments
        result = self.db.execute("""
            SELECT COUNT(*) as count
            FROM appointments
            WHERE tech_id = ?
              AND appointment_date = ?
              AND status NOT IN ('CANCELLED', 'NO_SHOW')
              AND (
                  (start_time < ? AND end_time > ?)
                  OR (start_time >= ? AND start_time < ?)
              )
        """, (tech_id, date_str, end_time, start_time, start_time, end_time))

        return result[0]['count'] == 0 if result else True

    # ========================================================================
    # SCHEDULE VIEWS
    # ========================================================================

    def get_daily_schedule(
        self,
        target_date: date,
        location_id: Optional[int] = None,
        appointment_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all appointments for a day

        Args:
            target_date: Date to view
            location_id: Filter by location
            appointment_type: Filter by type

        Returns:
            List of appointments ordered by time
        """
        date_str = target_date.isoformat() if isinstance(target_date, date) else target_date

        query = """
            SELECT
                a.*,
                c.first_name || ' ' || c.last_name as customer_name,
                c.phone as customer_phone,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                v.color as vehicle_color,
                j.job_number,
                j.status as job_status,
                t.first_name || ' ' || t.last_name as tech_name
            FROM appointments a
            LEFT JOIN customers c ON c.id = a.customer_id
            LEFT JOIN vehicles v ON v.id = a.vehicle_id
            LEFT JOIN jobs j ON j.id = a.job_id
            LEFT JOIN technicians t ON t.id = a.tech_id
            WHERE a.appointment_date = ?
              AND a.status NOT IN ('CANCELLED')
        """
        params = [date_str]

        if location_id:
            query += " AND a.location_id = ?"
            params.append(location_id)

        if appointment_type:
            query += " AND a.appointment_type = ?"
            params.append(appointment_type)

        query += " ORDER BY a.start_time"

        return self.db.execute(query, tuple(params))

    def get_weekly_schedule(
        self,
        start_date: date,
        location_id: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get appointments for a week

        Args:
            start_date: Start of week
            location_id: Filter by location

        Returns:
            Dict with date keys and appointment lists
        """
        schedule = {}

        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.isoformat()
            schedule[date_str] = self.get_daily_schedule(current_date, location_id)

        return schedule

    def get_tech_schedule(
        self,
        tech_id: int,
        start_date: date,
        days: int = 7
    ) -> List[Dict]:
        """Get schedule for a specific technician"""
        end_date = start_date + timedelta(days=days)

        return self.db.execute("""
            SELECT
                a.*,
                c.first_name || ' ' || c.last_name as customer_name,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                j.job_number
            FROM appointments a
            LEFT JOIN customers c ON c.id = a.customer_id
            LEFT JOIN vehicles v ON v.id = a.vehicle_id
            LEFT JOIN jobs j ON j.id = a.job_id
            WHERE a.tech_id = ?
              AND a.appointment_date >= ?
              AND a.appointment_date < ?
              AND a.status NOT IN ('CANCELLED')
            ORDER BY a.appointment_date, a.start_time
        """, (tech_id, start_date.isoformat(), end_date.isoformat()))

    def get_job_appointments(self, job_id: int) -> List[Dict]:
        """Get all appointments for a job"""
        return self.db.execute("""
            SELECT *
            FROM appointments
            WHERE job_id = ?
            ORDER BY appointment_date, start_time
        """, (job_id,))

    def get_customer_appointments(
        self,
        customer_id: int,
        include_past: bool = False
    ) -> List[Dict]:
        """Get all appointments for a customer"""
        query = """
            SELECT
                a.*,
                v.year || ' ' || v.make || ' ' || v.model as vehicle_description,
                j.job_number
            FROM appointments a
            LEFT JOIN vehicles v ON v.id = a.vehicle_id
            LEFT JOIN jobs j ON j.id = a.job_id
            WHERE a.customer_id = ?
        """
        params = [customer_id]

        if not include_past:
            query += " AND a.appointment_date >= ?"
            params.append(date.today().isoformat())

        query += " ORDER BY a.appointment_date DESC, a.start_time DESC"

        return self.db.execute(query, tuple(params))

    # ========================================================================
    # CAPACITY & UTILIZATION
    # ========================================================================

    def get_capacity_summary(
        self,
        target_date: date,
        location_id: Optional[int] = None
    ) -> Dict:
        """
        Get capacity summary for a date

        Returns:
            Summary with total slots, booked, available
        """
        date_str = target_date.isoformat() if isinstance(target_date, date) else target_date

        # Get business hours
        day_of_week = target_date.weekday()
        hours = self.business_hours.get(day_of_week, {})

        if not hours.get('enabled', False):
            return {
                'date': date_str,
                'is_open': False,
                'total_slots': 0,
                'booked': 0,
                'available': 0,
                'utilization_pct': 0
            }

        # Calculate total possible slots
        open_time = datetime.strptime(hours['open'], '%H:%M')
        close_time = datetime.strptime(hours['close'], '%H:%M')
        total_minutes = (close_time - open_time).seconds // 60
        total_slots = (total_minutes // self.slot_duration) * self.max_per_slot

        # Count booked appointments
        query = """
            SELECT COUNT(*) as count
            FROM appointments
            WHERE appointment_date = ?
              AND status NOT IN ('CANCELLED', 'NO_SHOW')
        """
        params = [date_str]

        if location_id:
            query += " AND location_id = ?"
            params.append(location_id)

        result = self.db.execute(query, tuple(params))
        booked = result[0]['count'] if result else 0

        available = max(0, total_slots - booked)
        utilization = (booked / total_slots * 100) if total_slots > 0 else 0

        return {
            'date': date_str,
            'is_open': True,
            'business_hours': f"{hours['open']} - {hours['close']}",
            'total_slots': total_slots,
            'booked': booked,
            'available': available,
            'utilization_pct': round(utilization, 1)
        }

    def get_weekly_capacity(
        self,
        start_date: date,
        location_id: Optional[int] = None
    ) -> List[Dict]:
        """Get capacity summary for each day of the week"""
        summaries = []

        for i in range(7):
            current_date = start_date + timedelta(days=i)
            summary = self.get_capacity_summary(current_date, location_id)
            summary['day_name'] = current_date.strftime('%A')
            summaries.append(summary)

        return summaries

    def get_tech_workload(
        self,
        target_date: Optional[date] = None
    ) -> List[Dict]:
        """
        Get workload summary for all technicians

        Returns:
            List of techs with appointment counts and active jobs
        """
        date_filter = ""
        params = []

        if target_date:
            date_filter = "AND a.appointment_date = ?"
            params.append(target_date.isoformat())

        return self.db.execute(f"""
            SELECT
                t.id as tech_id,
                t.first_name || ' ' || t.last_name as tech_name,
                t.skill_level,
                t.max_jobs_concurrent,
                COUNT(DISTINCT CASE
                    WHEN a.status NOT IN ('CANCELLED', 'NO_SHOW', 'COMPLETED')
                    THEN a.id
                END) as scheduled_appointments,
                COUNT(DISTINCT CASE
                    WHEN j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                    THEN j.id
                END) as active_jobs,
                t.max_jobs_concurrent - COUNT(DISTINCT CASE
                    WHEN j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                    THEN j.id
                END) as available_capacity
            FROM technicians t
            LEFT JOIN appointments a ON a.tech_id = t.id {date_filter}
            LEFT JOIN jobs j ON j.assigned_tech_id = t.id
                AND j.status IN ('ASSIGNED_TO_TECH', 'IN_PROGRESS')
                AND j.deleted_at IS NULL
            WHERE t.status = 'ACTIVE' AND t.deleted_at IS NULL
            GROUP BY t.id
            ORDER BY t.first_name
        """, tuple(params))

    # ========================================================================
    # CONFLICT DETECTION
    # ========================================================================

    def check_conflicts(
        self,
        target_date: date,
        location_id: Optional[int] = None
    ) -> Dict:
        """
        Check for scheduling conflicts on a date

        Returns:
            Conflict report with overbooked slots, tech overload, etc.
        """
        conflicts = {
            'date': target_date.isoformat(),
            'has_conflicts': False,
            'overbooked_slots': [],
            'tech_overload': [],
            'double_bookings': []
        }

        # Check for overbooked slots
        day_of_week = target_date.weekday()
        hours = self.business_hours.get(day_of_week, {})

        if not hours.get('enabled', False):
            return conflicts

        open_time = datetime.strptime(hours['open'], '%H:%M')
        close_time = datetime.strptime(hours['close'], '%H:%M')
        current_time = open_time

        while current_time + timedelta(minutes=self.slot_duration) <= close_time:
            start_str = current_time.strftime('%H:%M')
            end_str = (current_time + timedelta(minutes=self.slot_duration)).strftime('%H:%M')

            count = self._get_slot_appointment_count(
                target_date, start_str, end_str, location_id
            )

            if count > self.max_per_slot:
                conflicts['overbooked_slots'].append({
                    'time': f"{start_str}-{end_str}",
                    'booked': count,
                    'max': self.max_per_slot,
                    'over_by': count - self.max_per_slot
                })
                conflicts['has_conflicts'] = True

            current_time += timedelta(minutes=self.slot_duration)

        # Check for tech overload
        tech_workload = self.get_tech_workload(target_date)
        for tech in tech_workload:
            if tech['active_jobs'] > tech['max_jobs_concurrent']:
                conflicts['tech_overload'].append({
                    'tech_id': tech['tech_id'],
                    'tech_name': tech['tech_name'],
                    'active_jobs': tech['active_jobs'],
                    'max_concurrent': tech['max_jobs_concurrent'],
                    'over_by': tech['active_jobs'] - tech['max_jobs_concurrent']
                })
                conflicts['has_conflicts'] = True

        # Check for double-booked techs (same tech, overlapping appointments)
        double_bookings = self.db.execute("""
            SELECT
                a1.tech_id,
                t.first_name || ' ' || t.last_name as tech_name,
                a1.id as apt1_id,
                a1.start_time as apt1_start,
                a1.end_time as apt1_end,
                a2.id as apt2_id,
                a2.start_time as apt2_start,
                a2.end_time as apt2_end
            FROM appointments a1
            JOIN appointments a2 ON a1.tech_id = a2.tech_id
                AND a1.appointment_date = a2.appointment_date
                AND a1.id < a2.id
                AND a1.status NOT IN ('CANCELLED', 'NO_SHOW')
                AND a2.status NOT IN ('CANCELLED', 'NO_SHOW')
                AND (
                    (a1.start_time < a2.end_time AND a1.end_time > a2.start_time)
                )
            JOIN technicians t ON t.id = a1.tech_id
            WHERE a1.appointment_date = ?
              AND a1.tech_id IS NOT NULL
        """, (target_date.isoformat(),))

        if double_bookings:
            conflicts['double_bookings'] = double_bookings
            conflicts['has_conflicts'] = True

        return conflicts

    # ========================================================================
    # REPORTING
    # ========================================================================

    def get_scheduling_stats(
        self,
        start_date: date,
        end_date: date,
        location_id: Optional[int] = None
    ) -> Dict:
        """
        Get scheduling statistics for a date range

        Returns:
            Stats including total appointments, completion rate, no-shows
        """
        query_base = """
            FROM appointments
            WHERE appointment_date >= ?
              AND appointment_date <= ?
        """
        params = [start_date.isoformat(), end_date.isoformat()]

        if location_id:
            query_base += " AND location_id = ?"
            params.append(location_id)

        # Total appointments
        total = self.db.execute(f"SELECT COUNT(*) as count {query_base}", tuple(params))
        total_count = total[0]['count'] if total else 0

        # By status
        by_status = self.db.execute(f"""
            SELECT status, COUNT(*) as count
            {query_base}
            GROUP BY status
        """, tuple(params))

        status_counts = {row['status']: row['count'] for row in by_status}

        # By type
        by_type = self.db.execute(f"""
            SELECT appointment_type, COUNT(*) as count
            {query_base}
            GROUP BY appointment_type
        """, tuple(params))

        type_counts = {row['appointment_type']: row['count'] for row in by_type}

        # Calculate rates
        completed = status_counts.get('COMPLETED', 0)
        no_shows = status_counts.get('NO_SHOW', 0)
        cancelled = status_counts.get('CANCELLED', 0)

        scheduled_total = total_count - cancelled
        completion_rate = (completed / scheduled_total * 100) if scheduled_total > 0 else 0
        no_show_rate = (no_shows / scheduled_total * 100) if scheduled_total > 0 else 0

        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'total_appointments': total_count,
            'by_status': status_counts,
            'by_type': type_counts,
            'completion_rate': round(completion_rate, 1),
            'no_show_rate': round(no_show_rate, 1),
            'cancellation_count': cancelled
        }

    def format_daily_schedule_report(
        self,
        target_date: date,
        location_id: Optional[int] = None
    ) -> str:
        """Generate formatted daily schedule report"""
        appointments = self.get_daily_schedule(target_date, location_id)
        capacity = self.get_capacity_summary(target_date, location_id)

        lines = []
        lines.append("=" * 70)
        lines.append(f"DAILY SCHEDULE - {target_date.strftime('%A, %B %d, %Y')}")
        lines.append("=" * 70)
        lines.append("")

        if not capacity['is_open']:
            lines.append("SHOP CLOSED")
            return "\n".join(lines)

        lines.append(f"Business Hours: {capacity['business_hours']}")
        lines.append(f"Utilization: {capacity['utilization_pct']}% ({capacity['booked']}/{capacity['total_slots']} slots)")
        lines.append("")
        lines.append("-" * 70)

        if not appointments:
            lines.append("No appointments scheduled")
        else:
            for apt in appointments:
                lines.append(f"{apt['start_time']}-{apt['end_time']}  {apt['appointment_type']}")
                if apt['customer_name']:
                    lines.append(f"  Customer: {apt['customer_name']}")
                if apt['vehicle_description']:
                    lines.append(f"  Vehicle: {apt['vehicle_description']}")
                if apt['job_number']:
                    lines.append(f"  Job: {apt['job_number']}")
                if apt['tech_name']:
                    lines.append(f"  Tech: {apt['tech_name']}")
                lines.append(f"  Status: {apt['status']}")
                lines.append("")

        # Check for conflicts
        conflicts = self.check_conflicts(target_date, location_id)
        if conflicts['has_conflicts']:
            lines.append("-" * 70)
            lines.append("!!! CONFLICTS DETECTED !!!")

            if conflicts['overbooked_slots']:
                for slot in conflicts['overbooked_slots']:
                    lines.append(f"  OVERBOOKED: {slot['time']} ({slot['booked']}/{slot['max']})")

            if conflicts['tech_overload']:
                for tech in conflicts['tech_overload']:
                    lines.append(f"  TECH OVERLOAD: {tech['tech_name']} ({tech['active_jobs']}/{tech['max_concurrent']} jobs)")

            if conflicts['double_bookings']:
                lines.append(f"  DOUBLE BOOKINGS: {len(conflicts['double_bookings'])} found")

        return "\n".join(lines)

    def format_weekly_capacity_report(
        self,
        start_date: date,
        location_id: Optional[int] = None
    ) -> str:
        """Generate formatted weekly capacity report"""
        capacity = self.get_weekly_capacity(start_date, location_id)

        lines = []
        lines.append("=" * 70)
        lines.append(f"WEEKLY CAPACITY - Week of {start_date.strftime('%B %d, %Y')}")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"{'Day':<12} {'Hours':<14} {'Booked':<10} {'Available':<10} {'Utilization':<12}")
        lines.append("-" * 70)

        total_booked = 0
        total_available = 0

        for day in capacity:
            if day['is_open']:
                lines.append(
                    f"{day['day_name']:<12} {day['business_hours']:<14} "
                    f"{day['booked']:<10} {day['available']:<10} {day['utilization_pct']:<10}%"
                )
                total_booked += day['booked']
                total_available += day['available']
            else:
                lines.append(f"{day['day_name']:<12} CLOSED")

        lines.append("-" * 70)
        total_slots = total_booked + total_available
        weekly_util = (total_booked / total_slots * 100) if total_slots > 0 else 0
        lines.append(f"{'TOTAL':<12} {'':<14} {total_booked:<10} {total_available:<10} {round(weekly_util, 1):<10}%")

        return "\n".join(lines)

    # ========================================================================
    # SELF-SCHEDULING FEATURES
    # ========================================================================

    def get_scheduling_settings(self, organization_id: int) -> Dict:
        """
        Get scheduling settings for an organization

        Returns settings with defaults applied for any missing values
        """
        results = self.db.execute("""
            SELECT * FROM scheduling_settings WHERE organization_id = ?
        """, (organization_id,))

        if results:
            settings = dict(results[0])
            # Parse JSON fields
            if settings.get('business_hours'):
                try:
                    settings['business_hours'] = json.loads(settings['business_hours'])
                except:
                    pass
            if settings.get('allowed_appointment_types'):
                try:
                    settings['allowed_appointment_types'] = json.loads(settings['allowed_appointment_types'])
                except:
                    settings['allowed_appointment_types'] = ['DROP_OFF', 'ESTIMATE']
            return settings

        # Return defaults
        return {
            'organization_id': organization_id,
            'business_hours': self.DEFAULT_BUSINESS_HOURS,
            'default_slot_duration': 60,
            'buffer_between_appointments': 15,
            'max_appointments_per_day': 20,
            'max_appointments_per_slot': self.max_per_slot,
            'allow_self_scheduling': True,
            'min_notice_hours': 24,
            'max_advance_days': 30,
            'allowed_appointment_types': ['DROP_OFF', 'ESTIMATE'],
            'require_confirmation': True,
            'auto_confirm': False,
            'send_24h_reminder': True,
            'send_2h_reminder': True,
        }

    def update_scheduling_settings(self, organization_id: int, settings: Dict) -> bool:
        """Update scheduling settings for an organization"""
        # Serialize JSON fields
        if 'business_hours' in settings and isinstance(settings['business_hours'], dict):
            settings['business_hours'] = json.dumps(settings['business_hours'])
        if 'allowed_appointment_types' in settings and isinstance(settings['allowed_appointment_types'], list):
            settings['allowed_appointment_types'] = json.dumps(settings['allowed_appointment_types'])

        settings['updated_at'] = datetime.now().isoformat()

        # Check if exists
        existing = self.db.execute("""
            SELECT id FROM scheduling_settings WHERE organization_id = ?
        """, (organization_id,))

        if existing:
            self.db.update('scheduling_settings', existing[0]['id'], settings)
        else:
            settings['organization_id'] = organization_id
            self.db.insert('scheduling_settings', settings)

        return True

    def create_scheduling_token(
        self,
        organization_id: int,
        customer_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        job_id: Optional[int] = None,
        appointment_type: Optional[str] = None,
        expires_days: int = 7,
        max_uses: int = 1,
        created_by: Optional[int] = None
    ) -> str:
        """
        Create a self-scheduling token for a customer

        Args:
            organization_id: Organization ID
            customer_id: Limit token to specific customer
            lead_id: Associated lead
            job_id: Associated job
            appointment_type: Limit to specific appointment type
            expires_days: Days until token expires
            max_uses: Max times token can be used

        Returns:
            Token string
        """
        import secrets

        # Generate secure token
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()

        self.db.insert('scheduling_tokens', {
            'organization_id': organization_id,
            'token': token,
            'customer_id': customer_id,
            'lead_id': lead_id,
            'job_id': job_id,
            'appointment_type': appointment_type,
            'expires_at': expires_at,
            'max_uses': max_uses,
            'times_used': 0,
            'is_active': 1,
            'created_by': created_by,
        })

        print(f"[OK] Created scheduling token: {token[:20]}...")
        return token

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate a scheduling token

        Returns:
            Token data if valid, None if invalid/expired
        """
        results = self.db.execute("""
            SELECT st.*, o.name as organization_name,
                   c.first_name || ' ' || c.last_name as customer_name,
                   c.phone as customer_phone, c.email as customer_email
            FROM scheduling_tokens st
            JOIN organizations o ON o.id = st.organization_id
            LEFT JOIN customers c ON c.id = st.customer_id
            WHERE st.token = ?
              AND st.is_active = 1
        """, (token,))

        if not results:
            return None

        token_data = dict(results[0])

        # Check expiration
        if token_data.get('expires_at'):
            expires = datetime.fromisoformat(token_data['expires_at'])
            if expires < datetime.now():
                return None

        # Check max uses
        if token_data.get('max_uses'):
            if token_data['times_used'] >= token_data['max_uses']:
                return None

        return token_data

    def book_via_token(
        self,
        token: str,
        appointment_date: str,
        start_time: str,
        customer_info: Optional[Dict] = None
    ) -> Dict:
        """
        Book an appointment via self-scheduling token

        Args:
            token: Scheduling token
            appointment_date: Date to book (YYYY-MM-DD)
            start_time: Start time (HH:MM)
            customer_info: Optional customer info (name, phone, email) if not in token

        Returns:
            Dict with success status and appointment_id or error
        """
        # Validate token
        token_data = self.validate_token(token)
        if not token_data:
            return {'success': False, 'error': 'Invalid or expired scheduling link'}

        org_id = token_data['organization_id']
        settings = self.get_scheduling_settings(org_id)

        # Check if self-scheduling is enabled
        if not settings.get('allow_self_scheduling'):
            return {'success': False, 'error': 'Online scheduling is not available'}

        # Parse date
        try:
            target_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
        except ValueError:
            return {'success': False, 'error': 'Invalid date format'}

        # Check min notice
        min_notice_hours = settings.get('min_notice_hours', 24)
        min_book_time = datetime.now() + timedelta(hours=min_notice_hours)
        book_datetime = datetime.combine(target_date, datetime.strptime(start_time, '%H:%M').time())

        if book_datetime < min_book_time:
            return {'success': False, 'error': f'Appointments must be booked at least {min_notice_hours} hours in advance'}

        # Check max advance
        max_advance_days = settings.get('max_advance_days', 30)
        max_date = date.today() + timedelta(days=max_advance_days)
        if target_date > max_date:
            return {'success': False, 'error': f'Cannot book more than {max_advance_days} days in advance'}

        # Determine appointment type
        appointment_type = token_data.get('appointment_type') or 'DROP_OFF'

        # Get customer info
        customer_id = token_data.get('customer_id')
        contact_name = token_data.get('customer_name')
        contact_phone = token_data.get('customer_phone')
        contact_email = token_data.get('customer_email')

        if customer_info:
            contact_name = customer_info.get('name') or contact_name
            contact_phone = customer_info.get('phone') or contact_phone
            contact_email = customer_info.get('email') or contact_email

        # Validate required info
        if not contact_name or not contact_phone:
            return {'success': False, 'error': 'Name and phone number are required'}

        # Create appointment
        try:
            duration = settings.get('default_slot_duration', 60)

            appointment_id = self.schedule_appointment(
                appointment_type=appointment_type,
                appointment_date=target_date,
                start_time=start_time,
                job_id=token_data.get('job_id'),
                customer_id=customer_id,
                duration_minutes=duration,
                contact_name=contact_name,
                contact_phone=contact_phone,
                contact_email=contact_email,
                notes=f"Booked via self-scheduling link",
                created_by='self_schedule'
            )

            # Update token usage
            self.db.execute("""
                UPDATE scheduling_tokens
                SET times_used = times_used + 1, last_used_at = ?
                WHERE token = ?
            """, (datetime.now().isoformat(), token))

            # Auto-confirm if enabled
            if settings.get('auto_confirm'):
                self.update_status(appointment_id, 'CONFIRMED')

            return {
                'success': True,
                'appointment_id': appointment_id,
                'appointment_date': appointment_date,
                'start_time': start_time,
                'message': 'Appointment booked successfully!'
            }

        except ValueError as e:
            return {'success': False, 'error': str(e)}

    def get_available_dates_for_self_scheduling(
        self,
        organization_id: int,
        start_date: Optional[date] = None,
        days: int = 14,
        appointment_type: str = 'DROP_OFF'
    ) -> List[Dict]:
        """
        Get available dates for self-scheduling

        Returns list of dates with availability info
        """
        settings = self.get_scheduling_settings(organization_id)

        check_date = start_date or date.today()

        # Apply min notice
        min_notice_hours = settings.get('min_notice_hours', 24)
        min_date = (datetime.now() + timedelta(hours=min_notice_hours)).date()
        if check_date < min_date:
            check_date = min_date

        # Apply max advance
        max_advance_days = settings.get('max_advance_days', 30)
        max_date = date.today() + timedelta(days=max_advance_days)
        days = min(days, (max_date - check_date).days + 1)

        available_dates = []
        duration = settings.get('default_slot_duration', 60)

        for i in range(days):
            current_date = check_date + timedelta(days=i)

            if current_date > max_date:
                break

            slots = self.get_available_slots(
                current_date,
                appointment_type,
                duration
            )

            if slots:
                available_dates.append({
                    'date': current_date.isoformat(),
                    'day_name': current_date.strftime('%A'),
                    'display': current_date.strftime('%B %d'),
                    'slot_count': len(slots)
                })

        return available_dates

    def get_available_slots_for_self_scheduling(
        self,
        organization_id: int,
        target_date: str,
        appointment_type: str = 'DROP_OFF'
    ) -> List[Dict]:
        """
        Get available time slots for self-scheduling on a specific date

        Returns formatted slots for display
        """
        settings = self.get_scheduling_settings(organization_id)

        # Parse date
        try:
            if isinstance(target_date, str):
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        except ValueError:
            return []

        duration = settings.get('default_slot_duration', 60)

        slots = self.get_available_slots(
            target_date,
            appointment_type,
            duration
        )

        # Format for display
        formatted_slots = []
        for slot in slots:
            start_time = slot['start_time']
            # Convert to 12-hour format for display
            start_dt = datetime.strptime(start_time, '%H:%M')
            display_time = start_dt.strftime('%I:%M %p').lstrip('0')

            formatted_slots.append({
                'start_time': start_time,
                'display_time': display_time,
                'available_spots': slot['available_spots']
            })

        return formatted_slots

    # ========================================================================
    # TECHNICIAN SCHEDULE MANAGEMENT
    # ========================================================================

    def set_technician_schedule(
        self,
        organization_id: int,
        technician_id: int,
        schedule: List[Dict]
    ) -> bool:
        """
        Set weekly schedule for a technician

        Args:
            organization_id: Organization ID
            technician_id: Technician ID
            schedule: List of {day_of_week, is_available, start_time, end_time}
        """
        now = datetime.now().isoformat()

        for day_schedule in schedule:
            day_of_week = day_schedule['day_of_week']

            # Check if exists
            existing = self.db.execute("""
                SELECT id FROM technician_schedules
                WHERE technician_id = ? AND day_of_week = ?
            """, (technician_id, day_of_week))

            data = {
                'is_available': day_schedule.get('is_available', True),
                'start_time': day_schedule.get('start_time'),
                'end_time': day_schedule.get('end_time'),
                'max_appointments': day_schedule.get('max_appointments'),
                'updated_at': now
            }

            if existing:
                self.db.update('technician_schedules', existing[0]['id'], data)
            else:
                data.update({
                    'organization_id': organization_id,
                    'technician_id': technician_id,
                    'day_of_week': day_of_week
                })
                self.db.insert('technician_schedules', data)

        return True

    def get_technician_schedule(self, technician_id: int) -> List[Dict]:
        """Get weekly schedule for a technician"""
        results = self.db.execute("""
            SELECT * FROM technician_schedules
            WHERE technician_id = ?
            ORDER BY day_of_week
        """, (technician_id,))

        # Return with day names
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        schedule = []
        for row in results:
            schedule.append({
                **dict(row),
                'day_name': day_names[row['day_of_week']]
            })

        return schedule

    def add_time_off(
        self,
        organization_id: int,
        technician_id: int,
        start_date: str,
        end_date: str,
        reason: Optional[str] = None,
        notes: Optional[str] = None
    ) -> int:
        """Add time off for a technician"""
        time_off_id = self.db.insert('technician_time_off', {
            'organization_id': organization_id,
            'technician_id': technician_id,
            'start_date': start_date,
            'end_date': end_date,
            'reason': reason,
            'notes': notes,
            'status': 'approved'
        })

        print(f"[OK] Added time off #{time_off_id} for tech #{technician_id}: {start_date} to {end_date}")
        return time_off_id

    def remove_time_off(self, time_off_id: int) -> bool:
        """Remove a time off entry"""
        self.db.execute("DELETE FROM technician_time_off WHERE id = ?", (time_off_id,))
        return True

    def get_technician_time_off(
        self,
        technician_id: int,
        include_past: bool = False
    ) -> List[Dict]:
        """Get time off entries for a technician"""
        query = """
            SELECT * FROM technician_time_off
            WHERE technician_id = ?
        """
        params = [technician_id]

        if not include_past:
            query += " AND end_date >= ?"
            params.append(date.today().isoformat())

        query += " ORDER BY start_date"

        return self.db.execute(query, tuple(params))

    def is_tech_on_time_off(self, technician_id: int, check_date: date) -> bool:
        """Check if a tech is on time off on a specific date"""
        date_str = check_date.isoformat() if isinstance(check_date, date) else check_date

        results = self.db.execute("""
            SELECT id FROM technician_time_off
            WHERE technician_id = ?
              AND start_date <= ?
              AND end_date >= ?
              AND status = 'approved'
        """, (technician_id, date_str, date_str))

        return len(results) > 0

    # ========================================================================
    # REMINDER MANAGEMENT
    # ========================================================================

    def get_appointments_needing_reminder(self, reminder_type: str) -> List[Dict]:
        """
        Get appointments that need a reminder sent

        Args:
            reminder_type: '24h' or '2h'
        """
        now = datetime.now()

        if reminder_type == '24h':
            # Appointments 24-25 hours from now
            target_start = now + timedelta(hours=24)
            target_end = now + timedelta(hours=25)
            reminder_field = 'reminder_sent'
        elif reminder_type == '2h':
            # Appointments 2-3 hours from now
            target_start = now + timedelta(hours=2)
            target_end = now + timedelta(hours=3)
            reminder_field = 'confirmation_sent'
        else:
            return []

        return self.db.execute(f"""
            SELECT a.*, c.email as customer_email, c.phone as customer_phone
            FROM appointments a
            LEFT JOIN customers c ON c.id = a.customer_id
            WHERE a.status IN ('SCHEDULED', 'CONFIRMED')
              AND a.{reminder_field} = 0
              AND datetime(a.appointment_date || ' ' || a.start_time) >= ?
              AND datetime(a.appointment_date || ' ' || a.start_time) < ?
        """, (target_start.strftime('%Y-%m-%d %H:%M'), target_end.strftime('%Y-%m-%d %H:%M')))

    def mark_reminder_sent(self, appointment_id: int, reminder_type: str) -> bool:
        """Mark that a reminder was sent"""
        if reminder_type == '24h':
            self.db.execute("""
                UPDATE appointments SET reminder_sent = 1, updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), appointment_id))
        elif reminder_type == '2h':
            self.db.execute("""
                UPDATE appointments SET confirmation_sent = 1, updated_at = ? WHERE id = ?
            """, (datetime.now().isoformat(), appointment_id))

        return True

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_schedule_overview(self, organization_id: int, target_date: Optional[date] = None) -> Dict:
        """
        Get scheduling overview for dashboard

        Returns summary stats for today or specified date
        """
        check_date = target_date or date.today()
        date_str = check_date.isoformat()

        # Today's appointments
        today_count = self.db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'SCHEDULED' THEN 1 ELSE 0 END) as scheduled,
                SUM(CASE WHEN status = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed,
                SUM(CASE WHEN status = 'ARRIVED' THEN 1 ELSE 0 END) as arrived,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed
            FROM appointments
            WHERE appointment_date = ?
              AND status NOT IN ('CANCELLED')
        """, (date_str,))

        # Upcoming week
        week_end = (check_date + timedelta(days=7)).isoformat()
        week_count = self.db.execute("""
            SELECT COUNT(*) as count FROM appointments
            WHERE appointment_date >= ? AND appointment_date < ?
              AND status NOT IN ('CANCELLED')
        """, (date_str, week_end))

        # Unassigned appointments
        unassigned = self.db.execute("""
            SELECT COUNT(*) as count FROM appointments
            WHERE appointment_date >= ?
              AND tech_id IS NULL
              AND status NOT IN ('CANCELLED', 'COMPLETED')
        """, (date_str,))

        return {
            'date': date_str,
            'today': dict(today_count[0]) if today_count else {},
            'week_total': week_count[0]['count'] if week_count else 0,
            'unassigned': unassigned[0]['count'] if unassigned else 0
        }
