"""
Call scripts for PDR fleet sales.
"""

FLEET_CALL_SCRIPTS = {
    'hail_affected_cold_call': {
        'name': 'Hail Affected - Cold Call',
        'category': 'hail',
        'script': '''**INTRO (10 seconds)**
"Hi, this is {caller_name} with {caller_company}. I'm calling because I noticed your location at {address} was recently in the path of the hail storm that hit {city} on {hail_date}. Do you have just a minute?"

**IF YES - QUALIFY (30 seconds)**
"Great! I specialize in repairing hail damage on fleet vehicles. We've been helping businesses in the area get their vehicles back to perfect condition.

Quick question - did any of your vehicles sustain hail damage from that storm?"

**IF THEY HAVE DAMAGE - BUILD VALUE (45 seconds)**
"I understand that can be really frustrating, especially when you need those vehicles for your business.

Here's the good news - we use a process called PDR, or Paintless Dent Repair, which means:
- We can repair the dents WITHOUT repainting
- It typically takes 1-2 days per vehicle instead of weeks
- It costs about 40-60% less than traditional body work
- We come to YOU - no need to transport vehicles anywhere

And we handle all the insurance paperwork if you're filing a claim."

**CLOSE FOR APPOINTMENT**
"I'd like to come out and do a free damage assessment - takes about 15 minutes and there's no obligation. I have availability this week. What works best for your schedule?"

---

**OBJECTION HANDLERS:**

**"We're already working with someone"**
"I understand. Many of our clients started with us as a second opinion. Would it hurt to get another estimate? We might be able to save you some time or money."

**"We'll handle it later"**
"I get it, you're busy. Just so you know, the longer hail damage sits, the more likely you'll get rust starting in those dents. A quick assessment now could save you bigger problems later."

**"Not interested"**
"No problem at all. Would it be okay if I sent you our information in case you need hail repair in the future?"

**"How much does it cost?"**
"It depends on the severity of the damage. Most door dings are $75-150 each. For hail damage, we usually need to see the vehicle to give an accurate quote. That's why I'd like to do a free assessment."

---

**ALWAYS GET SOMETHING:**
- Appointment
- Email to send info
- Name of decision maker
- Best time to call back
''',
    },

    'dealership_introduction': {
        'name': 'Dealership - Introduction Call',
        'category': 'dealership',
        'script': '''**INTRO**
"Hi, I'm looking for your used car manager or whoever handles reconditioning. Is that person available?"

**WHEN CONNECTED**
"Hi {contact_name}, this is {caller_name} with {caller_company}. We're a PDR company that works with dealerships in the {city} area. Do you have a quick minute?"

**PITCH**
"I wanted to introduce our services. We help dealerships like yours:
- Repair hail damage on inventory fast
- Fix door dings and minor dents before cars hit the lot
- Turn vehicles faster and increase per-unit profit

We're mobile, so we come to you. Most dealers we work with see us 1-2 times per week for ongoing dent work.

Do you currently have a PDR company you work with?"

**IF YES:**
"Great, I'm not trying to replace anyone. But it's always good to have a backup. Would you be open to seeing our pricing? Many dealers find we can save them money on certain types of damage."

**IF NO:**
"Perfect. I'd love to stop by and introduce myself - show you some before/afters and leave you our pricing sheet. No pressure, just want to be on your radar for when you need us. Would later this week work?"

**CLOSE**
"I'm in your area this week. I could swing by around 2pm - would that work? I'll only take 10 minutes of your time."

---

**KEY INFO TO GATHER:**
- Decision maker name
- How many vehicles they move per month
- Current reconditioning process
- Main pain points (turnaround time, cost, quality)
''',
    },

    'rental_car_company': {
        'name': 'Rental Car Company - Introduction',
        'category': 'rental',
        'script': '''**INTRO**
"Hi, I'm trying to reach whoever manages fleet maintenance or vehicle appearance for this location. Who would that be?"

**WHEN CONNECTED**
"Hi {contact_name}, this is {caller_name}. I run a PDR company that works with several rental locations in {city}. Quick question - who do you currently use for dent repairs on your fleet?"

**PITCH**
"The reason I ask - we specialize in fast turnaround for rental fleets. We know every day a car is out of service costs you money.

Our technicians are mobile and can work early mornings, evenings, or weekends - whatever minimizes impact on your rental availability.

Most of our rental clients have us come by weekly to handle any dings or damage that came in. Keeps the fleet looking sharp and prevents bigger problems."

**VALUE PROPOSITION**
"We typically charge $75-150 for door dings and minor dents - way less than putting it through insurance or sending to a body shop. And the car is back on the lot same day."

**CLOSE**
"I'd love to come by and leave you some info and our pricing. If you've got 10 minutes, I can also do a quick walk of your lot and let you know if I see anything that needs attention - no charge, no obligation. What day this week works for you?"

---

**KEY METRICS TO MENTION:**
- Same-day turnaround
- We come to your location
- No paperwork needed for minor repairs
- Volume discounts available
''',
    },

    'municipal_fleet': {
        'name': 'Municipal/Government Fleet',
        'category': 'government',
        'script': '''**INTRO**
"Hi, I'm trying to reach your fleet maintenance department, specifically whoever handles body work or dent repairs on city vehicles. Can you point me in the right direction?"

**WHEN CONNECTED**
"Hi {contact_name}, this is {caller_name} with {caller_company}. We're a local PDR company that specializes in fleet vehicle repairs. Do you have a moment?"

**PITCH**
"I'm reaching out because I know municipal fleets often deal with hail damage, parking lot dings, and minor accidents - and getting repairs done through traditional channels can be slow and expensive.

We offer PDR - Paintless Dent Repair - which is:
- Typically 40-60% less than body shop prices
- Done on-site at your facility
- Same-day or next-day turnaround
- Fully documented for your records

We work with several government fleets in the region and understand your procurement requirements."

**QUALIFY**
"Does your department handle vehicle repairs directly, or does that go through a central fleet services?"

**CLOSE**
"I'd be happy to provide a quote on any current damage you have. We can also set up as an approved vendor if that helps with your purchasing process.

What's the best way to get on your approved vendor list? And do you have any vehicles that need attention right now that I could quote for you?"

---

**GOVERNMENT-SPECIFIC NOTES:**
- They may need 3 quotes
- Ask about purchase order requirements
- Offer to provide W-9 and insurance certificate
- Be patient - procurement can be slow
''',
    },

    'service_company': {
        'name': 'Service Company (HVAC, Plumbing, etc)',
        'category': 'service',
        'script': '''**INTRO**
"Hi, is this {company_name}? Great - I'm trying to reach whoever manages your service vehicles or fleet. Who would that be?"

**WHEN CONNECTED**
"Hi {contact_name}, this is {caller_name}. I run a mobile dent repair company. Quick question - you know how your service trucks get dinged up just sitting in parking lots and driveways?"

**PITCH**
"We specialize in keeping fleet vehicles looking professional. A lot of service companies we work with have us come by once a month to clean up any new dents or dings.

Here's why they like it:
- Your trucks look professional when they pull up to a customer's house
- We come to YOUR shop - no downtime
- We can do multiple vehicles in one visit
- Way cheaper than body shop prices

Do your trucks ever come back with dents or dings?"

**IF YES**
"That's exactly what we fix. Most door dings are $75-150 and we can knock them out in 15-30 minutes. How many service vehicles do you have?"

**CLOSE**
"I'd love to come by and take a look at your fleet - give you a free assessment of what's there and what it would cost to clean everything up. Then we can talk about an ongoing maintenance schedule if you like what you see. What day works for you?"

---

**VALUE POINTS FOR SERVICE COMPANIES:**
- Professional appearance = more trust from customers
- Maintain resale value on vehicles
- Prevent rust from spreading
- One-stop shop for all minor damage
''',
    },
}


def get_call_script(script_key: str, variables: dict = None) -> dict:
    """Get a call script with optional variable substitution."""
    import re

    script = FLEET_CALL_SCRIPTS.get(script_key)
    if not script:
        return None

    result = {
        'name': script['name'],
        'category': script['category'],
        'script': script['script'],
    }

    if variables:
        for key, value in variables.items():
            placeholder = '{' + key + '}'
            result['script'] = result['script'].replace(placeholder, str(value) if value else '')

    # Clean up any remaining empty placeholders
    result['script'] = re.sub(r'\{[^}]+\}', '[FILL IN]', result['script'])

    return result


def get_script_for_category(category: str, hail_affected: bool = False) -> str:
    """Get the best call script key for a business category."""
    if hail_affected:
        return 'hail_affected_cold_call'

    category_map = {
        'car_dealership': 'dealership_introduction',
        'car_rental': 'rental_car_company',
        'municipal': 'municipal_fleet',
        'government': 'municipal_fleet',
        'county_government': 'municipal_fleet',
        'state_government': 'municipal_fleet',
        'school': 'municipal_fleet',
        'school_district': 'municipal_fleet',
        'hvac': 'service_company',
        'plumbing': 'service_company',
        'electrical': 'service_company',
        'electrician': 'service_company',
        'landscaping': 'service_company',
        'pest_control': 'service_company',
        'service_trades': 'service_company',
        'roofing': 'service_company',
        'cleaning': 'service_company',
    }

    return category_map.get(category, 'hail_affected_cold_call')


def list_scripts() -> list:
    """List all available call scripts."""
    scripts = []
    for key, script in FLEET_CALL_SCRIPTS.items():
        scripts.append({
            'key': key,
            'name': script['name'],
            'category': script['category'],
        })
    return scripts
