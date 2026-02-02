"""
Email templates for PDR fleet outreach.
"""

FLEET_EMAIL_TEMPLATES = {
    'hail_affected_introduction': {
        'name': 'Hail Affected - Introduction',
        'subject': 'Hail Damage Assessment for {company_name} Fleet',
        'body': '''Dear {contact_name},

I noticed that {company_name} was recently affected by the hail storm that hit {city} on {hail_date}.

As a professional PDR (Paintless Dent Repair) company, we specialize in repairing hail damage quickly and affordably - often 40-60% less than traditional body shop repairs.

With your fleet of approximately {estimated_vehicles} vehicles, we understand that minimizing downtime is critical to your operations. Our mobile technicians can come to your location and repair vehicles on-site, eliminating the need for transportation.

Benefits of our fleet services:
- On-site repairs - no need to transport vehicles
- Typically 1-2 days per vehicle vs. weeks at a body shop
- Insurance claim assistance included
- Bulk fleet pricing available
- No paint, no fillers - retains factory finish and value

I'd like to offer a complimentary damage assessment for your fleet. When would be a convenient time for a quick 15-minute call to discuss your needs?

Best regards,
{sender_name}
{sender_company}
{sender_phone}
{sender_email}''',
        'follow_up_days': 3,
    },

    'hail_affected_followup': {
        'name': 'Hail Affected - Follow Up',
        'subject': 'Following up: Hail damage assessment for {company_name}',
        'body': '''Hi {contact_name},

I wanted to follow up on my previous email regarding hail damage repairs for your {city} location.

With storm season continuing, many fleet managers are getting their vehicles repaired now to:
- Prevent rust and further damage from hail dents
- Maintain vehicle resale value
- Ensure professional appearance for customers

We currently have availability to assess your fleet this week. Our team can provide a no-obligation estimate on-site at your convenience.

Would tomorrow or Thursday work for a quick visit?

Best regards,
{sender_name}
{sender_phone}''',
        'follow_up_days': 5,
    },

    'dealership_introduction': {
        'name': 'Dealership - Introduction',
        'subject': 'PDR Partnership Opportunity - {company_name}',
        'body': '''Dear {contact_name},

I'm reaching out to introduce our professional PDR services to {company_name}.

Many dealerships we work with use our services to:
- Repair hail damage on inventory quickly
- Fix minor dents before vehicles go to the lot
- Maintain CPO vehicle standards
- Increase profit per unit by improving condition

Our technicians are mobile and can work at your location during business hours or after-hours to minimize disruption.

We offer competitive wholesale pricing for dealership partners and can typically turn around vehicles within 24-48 hours.

I'd love to stop by and introduce myself. Do you have 10 minutes this week for a quick meeting?

Best regards,
{sender_name}
{sender_company}
{sender_phone}''',
        'follow_up_days': 4,
    },

    'rental_car_introduction': {
        'name': 'Rental Car Company - Introduction',
        'subject': 'PDR Services for {company_name} Fleet',
        'body': '''Dear {contact_name},

I understand that vehicle appearance and availability are critical for rental car operations. That's why I wanted to introduce our PDR services.

We currently work with several rental locations to:
- Repair hail damage quickly (usually same-day)
- Fix parking lot dings and door dents
- Keep vehicles road-ready and looking great
- Minimize out-of-service time

Our mobile technicians can work at your location on your schedule - early mornings, evenings, or weekends to minimize impact on your rental availability.

We also offer volume pricing for ongoing partnerships.

Could we schedule a brief meeting to discuss how we can help keep your fleet in top condition?

Best regards,
{sender_name}
{sender_phone}''',
        'follow_up_days': 3,
    },

    'municipal_fleet_introduction': {
        'name': 'Municipal/Government Fleet - Introduction',
        'subject': 'PDR Services for {city} Fleet Vehicles',
        'body': '''Dear {contact_name},

I'm reaching out regarding PDR (Paintless Dent Repair) services for {company_name} fleet vehicles.

Recent weather events have caused significant hail damage in the {city} area. Our company specializes in repairing hail damage on fleet vehicles, and we have experience working with municipal and government fleets.

Key benefits for government fleets:
- Cost-effective - typically 40-60% less than body shop repairs
- Fast turnaround - get vehicles back in service quickly
- On-site service - we come to your facility
- Detailed documentation for records and insurance
- We can work with your procurement process

We're happy to provide quotes in whatever format your department requires.

Would you be available for a brief call to discuss your fleet's needs?

Best regards,
{sender_name}
{sender_company}
{sender_phone}''',
        'follow_up_days': 5,
    },
}


def get_email_template(template_key: str, variables: dict) -> dict:
    """
    Get an email template with variables filled in.

    Args:
        template_key: Key from FLEET_EMAIL_TEMPLATES
        variables: Dict of variables to substitute

    Returns:
        Dict with 'subject' and 'body' filled in
    """
    import re

    template = FLEET_EMAIL_TEMPLATES.get(template_key)
    if not template:
        return None

    subject = template['subject']
    body = template['body']

    # Replace variables
    for key, value in variables.items():
        placeholder = '{' + key + '}'
        subject = subject.replace(placeholder, str(value) if value else '')
        body = body.replace(placeholder, str(value) if value else '')

    # Handle conditional placeholders like {contact_name or "Fleet Manager"}
    pattern = r'\{(\w+)\s+or\s+"([^"]+)"\}'

    def replace_conditional(match):
        var_name = match.group(1)
        default = match.group(2)
        return str(variables.get(var_name) or default)

    subject = re.sub(pattern, replace_conditional, subject)
    body = re.sub(pattern, replace_conditional, body)

    # Clean up any remaining empty placeholders
    subject = re.sub(r'\{[^}]+\}', '', subject)
    body = re.sub(r'\{[^}]+\}', '', body)

    return {
        'subject': subject.strip(),
        'body': body.strip(),
        'template_name': template['name'],
        'follow_up_days': template.get('follow_up_days', 3),
    }


def get_template_for_category(category: str, hail_affected: bool = False) -> str:
    """
    Get the best email template key for a business category.
    """
    if hail_affected:
        return 'hail_affected_introduction'

    category_map = {
        'car_dealership': 'dealership_introduction',
        'car_rental': 'rental_car_introduction',
        'municipal': 'municipal_fleet_introduction',
        'government': 'municipal_fleet_introduction',
        'county_government': 'municipal_fleet_introduction',
        'state_government': 'municipal_fleet_introduction',
        'school': 'municipal_fleet_introduction',
        'school_district': 'municipal_fleet_introduction',
    }

    return category_map.get(category, 'hail_affected_introduction')


def list_templates() -> list:
    """List all available templates with metadata."""
    templates = []
    for key, template in FLEET_EMAIL_TEMPLATES.items():
        templates.append({
            'key': key,
            'name': template['name'],
            'subject_preview': template['subject'][:50] + '...',
            'follow_up_days': template.get('follow_up_days', 3),
        })
    return templates
