"""
Lead Service
============
Operations for managing leads in the tenant database.
Each tenant has their own leads table.
"""

from datetime import datetime
from app.extensions import db
from app.models.tenant.lead import Lead
from app.models.tenant.contact import Contact
from app.models.tenant.call import Call
from app.models.master.business import Business


class LeadService:
    """Service for lead management - tenant-specific operations."""

    @staticmethod
    def create_lead(tenant_id, user_id, business_id, storm_id, notes=None, priority='medium'):
        """
        Save a business as a lead for this tenant.

        Args:
            tenant_id: Tenant ID
            user_id: User ID creating the lead
            business_id: Business ID from master DB
            storm_id: Storm ID
            notes: Optional notes
            priority: Lead priority (low, medium, high)

        Returns:
            Tuple of (lead, error_message)
        """
        # Check if lead already exists
        existing = Lead.query.filter_by(
            business_id=business_id,
            storm_id=storm_id
        ).first()

        if existing:
            return existing, "Lead already exists"

        # Get business info for estimated values
        business = Business.query.get(business_id)

        lead = Lead(
            business_id=business_id,
            storm_id=storm_id,
            status='new',
            priority=priority,
            notes=notes,
            estimated_vehicles=business.estimated_vehicles if business else None,
            assigned_to=user_id
        )

        db.session.add(lead)
        db.session.commit()

        return lead, None

    @staticmethod
    def get_leads(tenant_id, user_id, user_role, status=None, assigned_to=None, storm_id=None):
        """
        Get leads for this tenant.
        Techs/salesmen only see their assigned leads.

        Args:
            tenant_id: Tenant ID
            user_id: Current user ID
            user_role: Current user's role
            status: Filter by status
            assigned_to: Filter by assignee
            storm_id: Filter by storm

        Returns:
            List of lead dictionaries with business data
        """
        query = Lead.query

        # Filter by role permissions
        if user_role in ['tech', 'salesman']:
            query = query.filter(Lead.assigned_to == user_id)
        elif assigned_to:
            query = query.filter(Lead.assigned_to == assigned_to)

        if status:
            query = query.filter(Lead.status == status)

        if storm_id:
            query = query.filter(Lead.storm_id == storm_id)

        leads = query.order_by(Lead.created_at.desc()).all()

        # Enrich with business data from master DB
        result = []
        for lead in leads:
            business = Business.query.get(lead.business_id)
            lead_dict = lead.to_dict()
            lead_dict['business'] = business.to_dict() if business else None
            result.append(lead_dict)

        return result

    @staticmethod
    def get_lead(lead_id, user_id, user_role):
        """
        Get a single lead with full details.

        Args:
            lead_id: Lead ID
            user_id: Current user ID
            user_role: Current user's role

        Returns:
            Lead dictionary with business, contacts, and calls, or None
        """
        lead = Lead.query.get(lead_id)
        if not lead:
            return None

        # Check permission
        if user_role in ['tech', 'salesman'] and lead.assigned_to != user_id:
            return None

        business = Business.query.get(lead.business_id)
        contacts = Contact.query.filter_by(lead_id=lead_id).all()
        calls = Call.query.filter_by(lead_id=lead_id).order_by(Call.called_at.desc()).all()

        return {
            'lead': lead.to_dict(),
            'business': business.to_dict() if business else None,
            'contacts': [c.to_dict() for c in contacts],
            'calls': [c.to_dict() for c in calls]
        }

    @staticmethod
    def update_lead(lead_id, user_id, user_role, updates):
        """
        Update a lead.

        Args:
            lead_id: Lead ID
            user_id: Current user ID
            user_role: Current user's role
            updates: Dictionary of fields to update

        Returns:
            Tuple of (lead, error_message)
        """
        lead = Lead.query.get(lead_id)
        if not lead:
            return None, "Lead not found"

        # Check permission
        if user_role in ['tech', 'salesman'] and lead.assigned_to != user_id:
            return None, "Not authorized"

        # Update allowed fields
        allowed_fields = ['status', 'priority', 'notes', 'estimated_vehicles', 'estimated_value']

        for field in allowed_fields:
            if field in updates:
                setattr(lead, field, updates[field])

        # Only manager/owner can reassign
        if 'assigned_to' in updates and user_role in ['owner', 'manager']:
            lead.assigned_to = updates['assigned_to']

        lead.updated_at = datetime.utcnow()
        db.session.commit()

        return lead, None

    @staticmethod
    def add_contact(lead_id, user_id, name, phone=None, email=None, title=None, is_primary=False):
        """
        Add a contact to a lead.

        Args:
            lead_id: Lead ID
            user_id: User ID adding the contact
            name: Contact name
            phone: Phone number
            email: Email address
            title: Job title
            is_primary: Whether this is the primary contact

        Returns:
            Tuple of (contact, error_message)
        """
        lead = Lead.query.get(lead_id)
        if not lead:
            return None, "Lead not found"

        # If marking as primary, unmark others
        if is_primary:
            Contact.query.filter_by(lead_id=lead_id, is_primary=True).update({'is_primary': False})

        contact = Contact(
            lead_id=lead_id,
            name=name,
            phone=phone,
            email=email,
            title=title,
            is_primary=is_primary
        )

        db.session.add(contact)
        db.session.commit()

        return contact, None

    @staticmethod
    def log_call(lead_id, user_id, call_type, outcome, notes=None, duration_seconds=None, contact_id=None):
        """
        Log a call for a lead.

        Args:
            lead_id: Lead ID
            user_id: User ID making the call
            call_type: Type of call (inbound, outbound)
            outcome: Call outcome (connected, voicemail, no_answer, busy, wrong_number)
            notes: Call notes
            duration_seconds: Call duration
            contact_id: Contact ID if known

        Returns:
            Tuple of (call, error_message)
        """
        lead = Lead.query.get(lead_id)
        if not lead:
            return None, "Lead not found"

        call = Call(
            lead_id=lead_id,
            user_id=user_id,
            contact_id=contact_id,
            call_type=call_type,
            outcome=outcome,
            notes=notes,
            duration_seconds=duration_seconds
        )

        db.session.add(call)

        # Auto-update lead status if first contact
        if lead.status == 'new' and outcome in ['connected', 'voicemail']:
            lead.status = 'contacted'

        db.session.commit()

        return call, None

    @staticmethod
    def get_lead_stats(tenant_id, user_id=None, user_role=None):
        """
        Get lead statistics for dashboard.

        Args:
            tenant_id: Tenant ID
            user_id: User ID for role-based filtering
            user_role: User's role

        Returns:
            Dictionary with total and by_status counts
        """
        query = Lead.query

        if user_role in ['tech', 'salesman']:
            query = query.filter(Lead.assigned_to == user_id)

        total = query.count()
        by_status = {}

        for status in Lead.STATUSES:
            count = query.filter(Lead.status == status).count()
            by_status[status] = count

        return {
            'total': total,
            'by_status': by_status
        }

    @staticmethod
    def bulk_create_leads(tenant_id, user_id, business_ids, storm_id):
        """
        Create multiple leads at once (from map selection).

        Args:
            tenant_id: Tenant ID
            user_id: User ID creating leads
            business_ids: List of business IDs
            storm_id: Storm ID

        Returns:
            Dictionary with created and skipped counts
        """
        created = 0
        skipped = 0

        for business_id in business_ids:
            existing = Lead.query.filter_by(
                business_id=business_id,
                storm_id=storm_id
            ).first()

            if existing:
                skipped += 1
                continue

            business = Business.query.get(business_id)

            lead = Lead(
                business_id=business_id,
                storm_id=storm_id,
                status='new',
                priority='medium',
                estimated_vehicles=business.estimated_vehicles if business else None,
                assigned_to=user_id
            )

            db.session.add(lead)
            created += 1

        db.session.commit()

        return {'created': created, 'skipped': skipped}
