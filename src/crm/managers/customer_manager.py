"""
Customer & Lead Manager
Handles customer lifecycle and lead management for PDR CRM

Features:
- Customer CRUD operations
- Lead management and scoring
- Hail event lead generation
- Lead-to-customer conversion
- Customer search and filtering
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
import json


class CustomerManager:
    """
    Enterprise customer and lead management system

    Lead Scoring (0-100):
    - Has vehicle info: +20
    - Has insurance info: +15
    - From hail event: +25
    - Has email: +10
    - Has phone: +10
    - Has damage estimate: +20

    Temperature:
    - HOT: score >= 70
    - WARM: score 40-69
    - COLD: score < 40
    """

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db

    # ========================================================================
    # CUSTOMER CRUD
    # ========================================================================

    def create_customer(self, data: Dict) -> int:
        """
        Create new customer

        Required fields: first_name, last_name
        Optional: email, phone, company_name, address fields, etc.

        Returns: customer ID
        """
        # Set defaults
        if 'customer_since' not in data:
            data['customer_since'] = date.today().isoformat()
        if 'status' not in data:
            data['status'] = 'ACTIVE'

        return self.db.insert('customers', data)

    def get_customer(self, customer_id: int) -> Optional[Dict]:
        """Get customer by ID"""
        return self.db.get_by_id('customers', customer_id)

    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Find customer by email"""
        results = self.db.execute(
            "SELECT * FROM customers WHERE email = ? AND deleted_at IS NULL",
            (email,)
        )
        return results[0] if results else None

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Find customer by phone number"""
        # Normalize phone number (remove non-digits)
        clean_phone = ''.join(c for c in phone if c.isdigit())

        results = self.db.execute("""
            SELECT * FROM customers
            WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') = ?
              AND deleted_at IS NULL
        """, (clean_phone,))
        return results[0] if results else None

    def update_customer(self, customer_id: int, data: Dict) -> bool:
        """Update customer information"""
        return self.db.update('customers', customer_id, data)

    def delete_customer(self, customer_id: int, hard: bool = False) -> bool:
        """Delete customer (soft delete by default)"""
        return self.db.delete('customers', customer_id, soft=not hard)

    def search_customers(
        self,
        query: str = None,
        status: str = None,
        source: str = None,
        customer_type: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search customers with filters

        Args:
            query: Search name, email, phone, or company
            status: ACTIVE, INACTIVE, DO_NOT_CONTACT
            source: HAIL_EVENT, REFERRAL, WEBSITE, WALK_IN, DEALERSHIP
            customer_type: INDIVIDUAL, DEALERSHIP, FLEET, BODY_SHOP
            limit: Max results
        """
        conditions = []
        params = []

        if query:
            conditions.append("""
                (first_name LIKE ? OR last_name LIKE ? OR
                 email LIKE ? OR phone LIKE ? OR company_name LIKE ?)
            """)
            search = f"%{query}%"
            params.extend([search] * 5)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if source:
            conditions.append("source = ?")
            params.append(source)

        if customer_type:
            conditions.append("customer_type = ?")
            params.append(customer_type)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        return self.db.execute(f"""
            SELECT * FROM customers
            WHERE {where_clause} AND deleted_at IS NULL
            ORDER BY last_name, first_name
            LIMIT ?
        """, tuple(params) + (limit,))

    def get_customer_with_vehicles(self, customer_id: int) -> Optional[Dict]:
        """Get customer with all their vehicles"""
        customer = self.get_customer(customer_id)
        if not customer:
            return None

        vehicles = self.db.execute("""
            SELECT * FROM vehicles
            WHERE customer_id = ? AND deleted_at IS NULL
            ORDER BY year DESC
        """, (customer_id,))

        customer['vehicles'] = vehicles
        return customer

    def get_customer_jobs(self, customer_id: int) -> List[Dict]:
        """Get all jobs for a customer"""
        return self.db.execute("""
            SELECT j.*, v.year, v.make, v.model, v.color
            FROM jobs j
            JOIN vehicles v ON j.vehicle_id = v.id
            WHERE j.customer_id = ? AND j.deleted_at IS NULL
            ORDER BY j.created_at DESC
        """, (customer_id,))

    def record_contact(self, customer_id: int, notes: str = None) -> bool:
        """Record customer contact date"""
        return self.update_customer(customer_id, {
            'last_contact_date': date.today().isoformat()
        })

    def add_customer_tag(self, customer_id: int, tag: str) -> bool:
        """Add tag to customer (VIP, FLEET, REPEAT, etc.)"""
        customer = self.get_customer(customer_id)
        if not customer:
            return False

        tags = json.loads(customer.get('tags') or '[]')
        if tag not in tags:
            tags.append(tag)

        return self.update_customer(customer_id, {
            'tags': json.dumps(tags)
        })

    def remove_customer_tag(self, customer_id: int, tag: str) -> bool:
        """Remove tag from customer"""
        customer = self.get_customer(customer_id)
        if not customer:
            return False

        tags = json.loads(customer.get('tags') or '[]')
        if tag in tags:
            tags.remove(tag)

        return self.update_customer(customer_id, {
            'tags': json.dumps(tags)
        })

    # ========================================================================
    # LEAD MANAGEMENT
    # ========================================================================

    def create_lead(self, data: Dict) -> int:
        """
        Create new lead

        Required: source
        Optional: first_name, last_name, email, phone, vehicle info, etc.

        Auto-calculates lead score based on provided information.
        Returns: lead ID
        """
        # Calculate lead score
        score = self._calculate_lead_score(data)
        data['score'] = score
        data['temperature'] = self._get_temperature(score)

        # Set default status if not provided
        if 'status' not in data:
            data['status'] = 'NEW'

        # Set follow-up date (3 days from now for new leads)
        if 'next_follow_up_date' not in data:
            data['next_follow_up_date'] = (date.today() + timedelta(days=3)).isoformat()

        return self.db.insert('leads', data)

    def get_lead(self, lead_id: int) -> Optional[Dict]:
        """Get lead by ID"""
        return self.db.get_by_id('leads', lead_id)

    def update_lead(self, lead_id: int, data: Dict) -> bool:
        """
        Update lead information

        Auto-recalculates score if relevant fields change.
        """
        # If updating fields that affect score, recalculate
        score_fields = ['vehicle_year', 'vehicle_make', 'email', 'phone',
                       'estimated_repair_cost', 'hail_event_id']

        if any(field in data for field in score_fields):
            lead = self.get_lead(lead_id)
            if lead:
                # Merge existing data with updates
                merged = {**lead, **data}
                data['score'] = self._calculate_lead_score(merged)
                data['temperature'] = self._get_temperature(data['score'])

        return self.db.update('leads', lead_id, data)

    def delete_lead(self, lead_id: int) -> bool:
        """Soft delete lead"""
        return self.db.delete('leads', lead_id, soft=True)

    def search_leads(
        self,
        status: str = None,
        temperature: str = None,
        source: str = None,
        hail_event_id: int = None,
        assigned_to: str = None,
        needs_followup: bool = False,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search leads with filters

        Args:
            status: NEW, CONTACTED, QUALIFIED, CONVERTED, LOST
            temperature: HOT, WARM, COLD
            source: HAIL_EVENT, REFERRAL, WEBSITE, PHONE, WALK_IN
            hail_event_id: Filter by specific hail event
            assigned_to: Filter by assigned salesperson
            needs_followup: Only leads needing follow-up today or earlier
            limit: Max results
        """
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if temperature:
            conditions.append("temperature = ?")
            params.append(temperature)

        if source:
            conditions.append("source = ?")
            params.append(source)

        if hail_event_id:
            conditions.append("hail_event_id = ?")
            params.append(hail_event_id)

        if assigned_to:
            conditions.append("assigned_to = ?")
            params.append(assigned_to)

        if needs_followup:
            conditions.append("next_follow_up_date <= date('now')")
            conditions.append("status NOT IN ('CONVERTED', 'LOST')")

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        return self.db.execute(f"""
            SELECT * FROM leads
            WHERE {where_clause} AND deleted_at IS NULL
            ORDER BY score DESC, next_follow_up_date ASC
            LIMIT ?
        """, tuple(params) + (limit,))

    def get_hot_leads(self, limit: int = 50) -> List[Dict]:
        """Get leads with temperature HOT"""
        return self.search_leads(temperature='HOT', limit=limit)

    def get_leads_needing_followup(self) -> List[Dict]:
        """Get all leads that need follow-up today or are overdue"""
        return self.search_leads(needs_followup=True, limit=500)

    def assign_lead(self, lead_id: int, assigned_to: str) -> bool:
        """Assign lead to salesperson"""
        return self.update_lead(lead_id, {
            'assigned_to': assigned_to,
            'assigned_at': datetime.now().isoformat()
        })

    def record_lead_contact(self, lead_id: int, notes: str = None,
                           next_followup_days: int = 3) -> bool:
        """Record contact with lead and schedule next follow-up"""
        lead = self.get_lead(lead_id)
        if not lead:
            return False

        follow_up_count = (lead.get('follow_up_count') or 0) + 1

        # Update status to CONTACTED if still NEW
        status = lead.get('status')
        if status == 'NEW':
            status = 'CONTACTED'

        update_data = {
            'last_contact_date': date.today().isoformat(),
            'follow_up_count': follow_up_count,
            'next_follow_up_date': (date.today() + timedelta(days=next_followup_days)).isoformat(),
            'status': status
        }

        if notes:
            existing_notes = lead.get('notes') or ''
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
            new_notes = f"{timestamp}: {notes}"
            update_data['notes'] = f"{existing_notes}\n{new_notes}" if existing_notes else new_notes

        return self.update_lead(lead_id, update_data)

    def qualify_lead(self, lead_id: int) -> bool:
        """Mark lead as qualified"""
        return self.update_lead(lead_id, {'status': 'QUALIFIED'})

    def lose_lead(self, lead_id: int, reason: str = None) -> bool:
        """Mark lead as lost"""
        return self.update_lead(lead_id, {
            'status': 'LOST',
            'lost_reason': reason
        })

    def convert_lead_to_customer(self, lead_id: int, vehicle_data: Dict = None) -> Dict:
        """
        Convert lead to customer

        Creates customer record (and optionally vehicle) from lead data.

        Returns: dict with customer_id and optionally vehicle_id
        """
        lead = self.get_lead(lead_id)
        if not lead:
            return {'error': 'Lead not found'}

        if lead.get('status') == 'CONVERTED':
            return {'error': 'Lead already converted',
                   'customer_id': lead.get('converted_to_customer_id')}

        # Check if customer already exists (by email or phone)
        existing = None
        if lead.get('email'):
            existing = self.get_customer_by_email(lead['email'])
        if not existing and lead.get('phone'):
            existing = self.get_customer_by_phone(lead['phone'])

        if existing:
            customer_id = existing['id']
        else:
            # Create new customer from lead
            customer_data = {
                'first_name': lead.get('first_name', 'Unknown'),
                'last_name': lead.get('last_name', 'Customer'),
                'company_name': lead.get('company_name'),
                'email': lead.get('email'),
                'phone': lead.get('phone'),
                'source': lead.get('source', 'LEAD'),
                'status': 'ACTIVE',
                'customer_since': date.today().isoformat()
            }
            customer_id = self.create_customer(customer_data)

        result = {'customer_id': customer_id}

        # Create vehicle if data provided or lead has vehicle info
        if vehicle_data or lead.get('vehicle_year'):
            from .vehicle_manager import VehicleManager
            vehicle_mgr = VehicleManager(self.db)

            v_data = vehicle_data or {
                'customer_id': customer_id,
                'year': lead.get('vehicle_year'),
                'make': lead.get('vehicle_make'),
                'model': lead.get('vehicle_model')
            }
            v_data['customer_id'] = customer_id

            vehicle_id = vehicle_mgr.create_vehicle(v_data)
            result['vehicle_id'] = vehicle_id

        # Update lead status
        self.update_lead(lead_id, {
            'status': 'CONVERTED',
            'converted_to_customer_id': customer_id
        })

        return result

    # ========================================================================
    # HAIL EVENT LEAD GENERATION
    # ========================================================================

    def generate_leads_from_hail_event(
        self,
        hail_event_id: int,
        lead_list: List[Dict],
        default_damage_type: str = 'HAIL'
    ) -> Dict:
        """
        Generate leads from a hail event

        Args:
            hail_event_id: ID of the hail event from swath system
            lead_list: List of potential customer dicts with contact info
            default_damage_type: Type of damage (default: HAIL)

        Returns: dict with created, skipped, and total counts
        """
        created = 0
        skipped = 0
        lead_ids = []

        for lead_data in lead_list:
            # Check for duplicates
            existing = None
            if lead_data.get('email'):
                existing = self._find_existing_lead_or_customer(
                    email=lead_data['email']
                )
            if not existing and lead_data.get('phone'):
                existing = self._find_existing_lead_or_customer(
                    phone=lead_data['phone']
                )

            if existing:
                skipped += 1
                continue

            # Create lead with hail event source
            lead_data['source'] = 'HAIL_EVENT'
            lead_data['hail_event_id'] = hail_event_id
            lead_data['damage_type'] = default_damage_type

            lead_id = self.create_lead(lead_data)
            lead_ids.append(lead_id)
            created += 1

        # Update hail event statistics
        self.db.execute("""
            UPDATE hail_events SET
                leads_generated = leads_generated + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (created, hail_event_id))

        return {
            'created': created,
            'skipped': skipped,
            'total': len(lead_list),
            'lead_ids': lead_ids
        }

    def get_leads_by_hail_event(self, hail_event_id: int) -> List[Dict]:
        """Get all leads generated from a specific hail event"""
        return self.db.execute("""
            SELECT * FROM leads
            WHERE hail_event_id = ? AND deleted_at IS NULL
            ORDER BY score DESC
        """, (hail_event_id,))

    def get_hail_event_stats(self, hail_event_id: int) -> Dict:
        """Get statistics for a hail event's leads"""
        result = self.db.execute("""
            SELECT
                COUNT(*) as total_leads,
                SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
                SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as lost,
                SUM(CASE WHEN temperature = 'HOT' THEN 1 ELSE 0 END) as hot_leads,
                AVG(score) as avg_score,
                SUM(estimated_repair_cost) as potential_revenue
            FROM leads
            WHERE hail_event_id = ? AND deleted_at IS NULL
        """, (hail_event_id,))

        return result[0] if result else {}

    # ========================================================================
    # LEAD SCORING
    # ========================================================================

    def _calculate_lead_score(self, data: Dict) -> int:
        """
        Calculate lead score (0-100)

        Scoring factors:
        - Has vehicle info (year/make/model): +20
        - Has insurance info: +15
        - From hail event: +25
        - Has email: +10
        - Has phone: +10
        - Has damage estimate: +20
        """
        score = 0

        # Vehicle info (+20)
        if data.get('vehicle_year') or data.get('vehicle_make'):
            score += 20

        # Insurance info (+15) - not typically in lead data, but check anyway
        # This would be updated when more info is gathered

        # From hail event (+25)
        if data.get('hail_event_id') or data.get('source') == 'HAIL_EVENT':
            score += 25

        # Has email (+10)
        if data.get('email'):
            score += 10

        # Has phone (+10)
        if data.get('phone'):
            score += 10

        # Has damage estimate (+20)
        if data.get('estimated_repair_cost'):
            score += 20

        # Has damage description (+5)
        if data.get('damage_description'):
            score += 5

        # Has company name (fleet potential) (+10)
        if data.get('company_name'):
            score += 10

        return min(score, 100)  # Cap at 100

    def _get_temperature(self, score: int) -> str:
        """Get lead temperature from score"""
        if score >= 70:
            return 'HOT'
        elif score >= 40:
            return 'WARM'
        else:
            return 'COLD'

    def recalculate_lead_score(self, lead_id: int) -> int:
        """Recalculate and update lead score"""
        lead = self.get_lead(lead_id)
        if not lead:
            return 0

        score = self._calculate_lead_score(lead)
        self.update_lead(lead_id, {
            'score': score,
            'temperature': self._get_temperature(score)
        })
        return score

    def _find_existing_lead_or_customer(
        self,
        email: str = None,
        phone: str = None
    ) -> Optional[Dict]:
        """Check if lead or customer already exists"""
        if email:
            # Check leads
            results = self.db.execute(
                "SELECT * FROM leads WHERE email = ? AND deleted_at IS NULL",
                (email,)
            )
            if results:
                return {'type': 'lead', **results[0]}

            # Check customers
            customer = self.get_customer_by_email(email)
            if customer:
                return {'type': 'customer', **customer}

        if phone:
            clean_phone = ''.join(c for c in phone if c.isdigit())

            # Check leads
            results = self.db.execute("""
                SELECT * FROM leads
                WHERE REPLACE(REPLACE(REPLACE(phone, '-', ''), '(', ''), ')', '') = ?
                  AND deleted_at IS NULL
            """, (clean_phone,))
            if results:
                return {'type': 'lead', **results[0]}

            # Check customers
            customer = self.get_customer_by_phone(phone)
            if customer:
                return {'type': 'customer', **customer}

        return None

    # ========================================================================
    # STATISTICS & REPORTS
    # ========================================================================

    def get_customer_stats(self) -> Dict:
        """Get overall customer statistics"""
        result = self.db.execute("""
            SELECT
                COUNT(*) as total_customers,
                SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'INACTIVE' THEN 1 ELSE 0 END) as inactive,
                SUM(CASE WHEN customer_type = 'INDIVIDUAL' THEN 1 ELSE 0 END) as individuals,
                SUM(CASE WHEN customer_type = 'FLEET' THEN 1 ELSE 0 END) as fleets,
                SUM(CASE WHEN customer_type = 'DEALERSHIP' THEN 1 ELSE 0 END) as dealerships,
                SUM(CASE WHEN source = 'HAIL_EVENT' THEN 1 ELSE 0 END) as from_hail_events
            FROM customers
            WHERE deleted_at IS NULL
        """)
        return result[0] if result else {}

    def get_lead_stats(self) -> Dict:
        """Get overall lead statistics"""
        result = self.db.execute("""
            SELECT
                COUNT(*) as total_leads,
                SUM(CASE WHEN status = 'NEW' THEN 1 ELSE 0 END) as new_leads,
                SUM(CASE WHEN status = 'CONTACTED' THEN 1 ELSE 0 END) as contacted,
                SUM(CASE WHEN status = 'QUALIFIED' THEN 1 ELSE 0 END) as qualified,
                SUM(CASE WHEN status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
                SUM(CASE WHEN status = 'LOST' THEN 1 ELSE 0 END) as lost,
                SUM(CASE WHEN temperature = 'HOT' THEN 1 ELSE 0 END) as hot,
                SUM(CASE WHEN temperature = 'WARM' THEN 1 ELSE 0 END) as warm,
                SUM(CASE WHEN temperature = 'COLD' THEN 1 ELSE 0 END) as cold,
                AVG(score) as avg_score
            FROM leads
            WHERE deleted_at IS NULL
        """)
        return result[0] if result else {}

    def get_conversion_rate(self) -> float:
        """Calculate lead to customer conversion rate"""
        stats = self.get_lead_stats()
        total = stats.get('total_leads', 0)
        converted = stats.get('converted', 0)

        if total == 0:
            return 0.0

        return (converted / total) * 100
