"""
PDR Pro Estimating - VIN Decoder Utility
Decode VINs using NHTSA free API with caching.

FEATURES:
- NHTSA VIN API integration
- Intelligent caching
- Vehicle option detection (sunroof, roof rails, etc.)
- Fallback handling
"""

import json
import sqlite3
import os
from typing import Optional, Dict, Any
from datetime import datetime
import urllib.request
import urllib.error


# NHTSA API endpoint
NHTSA_API_URL = "https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin}?format=json"


def decode_vin(vin: str, db_path: str = "data/pdr_crm.db") -> Dict:
    """
    Decode a VIN using NHTSA API with caching.

    Args:
        vin: 17-character VIN
        db_path: Database path for caching

    Returns:
        Dict with vehicle info:
        - year, make, model, trim, body_style
        - doors, drive_type, engine
        - has_sunroof, has_roof_rails, has_antenna_shark_fin
        - paint_code (if available)
    """
    # Validate VIN format
    vin = vin.upper().strip()
    if len(vin) != 17:
        return {'error': f'Invalid VIN length: {len(vin)} (expected 17)'}

    # Check cache first
    cached = get_cached_vehicle(vin, db_path)
    if cached:
        return cached

    # Call NHTSA API
    try:
        url = NHTSA_API_URL.format(vin=vin)
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        return {'error': f'API error: {str(e)}', 'vin': vin}
    except Exception as e:
        return {'error': f'Request failed: {str(e)}', 'vin': vin}

    # Parse response
    result = parse_nhtsa_response(data, vin)

    # Cache result
    cache_vehicle(vin, result, data, db_path)

    return result


def parse_nhtsa_response(data: Dict, vin: str) -> Dict:
    """Parse NHTSA API response into structured vehicle info"""

    result = {
        'vin': vin,
        'year': None,
        'make': None,
        'model': None,
        'trim': None,
        'body_style': None,
        'doors': None,
        'drive_type': None,
        'engine': None,
        'has_sunroof': False,
        'has_roof_rails': False,
        'has_antenna_shark_fin': True,  # Assume most modern vehicles have shark fin
        'paint_code': None,
        'fuel_door_side': 'left',  # Default, most vehicles
    }

    if not data.get('Results'):
        return result

    # Build lookup dict
    lookup = {}
    for item in data['Results']:
        var_id = item.get('VariableId')
        value = item.get('Value')
        if value and value.strip():
            lookup[var_id] = value.strip()

    # Map NHTSA variable IDs to our fields
    # Reference: https://vpic.nhtsa.dot.gov/api/

    # Model Year (29)
    if 29 in lookup:
        try:
            result['year'] = int(lookup[29])
        except:
            pass

    # Make (26)
    if 26 in lookup:
        result['make'] = lookup[26]

    # Model (28)
    if 28 in lookup:
        result['model'] = lookup[28]

    # Trim (38)
    if 38 in lookup:
        result['trim'] = lookup[38]

    # Body Class (5)
    if 5 in lookup:
        body = lookup[5].lower()
        if 'sedan' in body:
            result['body_style'] = 'Sedan'
        elif 'suv' in body or 'sport utility' in body:
            result['body_style'] = 'SUV'
        elif 'pickup' in body or 'truck' in body:
            # Check for cab types
            if 'crew' in body:
                result['body_style'] = 'Crew Cab'
            elif 'super' in body:
                result['body_style'] = 'SuperCrew'
            elif 'extended' in body or 'supercab' in body:
                result['body_style'] = 'Extended Cab'
            else:
                result['body_style'] = 'Regular Cab'
        elif 'coupe' in body:
            result['body_style'] = 'Coupe'
        elif 'hatchback' in body:
            result['body_style'] = 'Hatchback'
        elif 'wagon' in body:
            result['body_style'] = 'Wagon'
        elif 'van' in body or 'minivan' in body:
            result['body_style'] = 'Van'
        elif 'convertible' in body:
            result['body_style'] = 'Convertible'
        else:
            result['body_style'] = lookup[5]

    # Doors (14)
    if 14 in lookup:
        try:
            result['doors'] = int(lookup[14])
        except:
            pass

    # Drive Type (15)
    if 15 in lookup:
        drive = lookup[15].upper()
        if '4WD' in drive or '4X4' in drive:
            result['drive_type'] = '4WD'
        elif 'AWD' in drive:
            result['drive_type'] = 'AWD'
        elif 'FWD' in drive or 'FRONT' in drive:
            result['drive_type'] = 'FWD'
        elif 'RWD' in drive or 'REAR' in drive:
            result['drive_type'] = 'RWD'
        else:
            result['drive_type'] = lookup[15]

    # Engine (13) - Displacement
    if 13 in lookup:
        result['engine'] = lookup[13]

    # Detect vehicle options from various fields
    result.update(detect_vehicle_options(lookup, result))

    return result


def detect_vehicle_options(lookup: Dict, base_info: Dict) -> Dict:
    """
    Detect vehicle options that affect R/I operations.

    Uses various NHTSA fields and heuristics.
    """
    options = {
        'has_sunroof': False,
        'has_roof_rails': False,
        'has_antenna_shark_fin': True,
    }

    # Check trim for sunroof indicators
    trim = (base_info.get('trim') or '').lower()
    if any(x in trim for x in ['sunroof', 'moonroof', 'panoramic', 'limited', 'platinum', 'lariat']):
        options['has_sunroof'] = True

    # SUVs and crossovers often have roof rails
    body = (base_info.get('body_style') or '').lower()
    if any(x in body for x in ['suv', 'wagon', 'crossover']):
        options['has_roof_rails'] = True

    # Trucks with certain trims have roof rails
    make = (base_info.get('make') or '').lower()
    if 'truck' in body or 'cab' in body:
        if any(x in trim for x in ['lariat', 'king ranch', 'platinum', 'limited', 'denali', 'high country']):
            options['has_roof_rails'] = True

    # Pre-2010 vehicles likely have mast antenna
    year = base_info.get('year') or 2020
    if year < 2010:
        options['has_antenna_shark_fin'] = False

    return options


def get_cached_vehicle(vin: str, db_path: str) -> Optional[Dict]:
    """Get vehicle from cache if exists"""
    if not os.path.exists(db_path):
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM decoded_vehicles WHERE vin = ?
        """, (vin,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)

        return None

    except Exception:
        return None


def cache_vehicle(vin: str, result: Dict, raw_response: Dict, db_path: str):
    """Cache decoded vehicle in database"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create table if needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decoded_vehicles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vin TEXT UNIQUE NOT NULL,
                year INTEGER,
                make TEXT,
                model TEXT,
                trim TEXT,
                body_style TEXT,
                doors INTEGER,
                drive_type TEXT,
                engine TEXT,
                has_sunroof BOOLEAN,
                has_roof_rails BOOLEAN,
                has_antenna_shark_fin BOOLEAN,
                paint_code TEXT,
                raw_nhtsa_response TEXT,
                decoded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO decoded_vehicles (
                vin, year, make, model, trim, body_style,
                doors, drive_type, engine,
                has_sunroof, has_roof_rails, has_antenna_shark_fin,
                paint_code, raw_nhtsa_response, decoded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vin,
            result.get('year'),
            result.get('make'),
            result.get('model'),
            result.get('trim'),
            result.get('body_style'),
            result.get('doors'),
            result.get('drive_type'),
            result.get('engine'),
            1 if result.get('has_sunroof') else 0,
            1 if result.get('has_roof_rails') else 0,
            1 if result.get('has_antenna_shark_fin') else 0,
            result.get('paint_code'),
            json.dumps(raw_response),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Warning: Could not cache VIN: {e}")


def clear_cache(db_path: str = "data/pdr_crm.db"):
    """Clear all cached VIN decodes"""
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM decoded_vehicles")
    conn.commit()
    conn.close()

    print("[OK] VIN cache cleared")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_vehicle_summary(vin: str, db_path: str = "data/pdr_crm.db") -> str:
    """Get formatted vehicle summary from VIN"""
    vehicle = decode_vin(vin, db_path)

    if vehicle.get('error'):
        return f"Error: {vehicle['error']}"

    parts = []
    if vehicle.get('year'):
        parts.append(str(vehicle['year']))
    if vehicle.get('make'):
        parts.append(vehicle['make'])
    if vehicle.get('model'):
        parts.append(vehicle['model'])
    if vehicle.get('trim'):
        parts.append(vehicle['trim'])
    if vehicle.get('body_style'):
        parts.append(f"({vehicle['body_style']})")

    return ' '.join(parts) or 'Unknown Vehicle'


def get_vehicle_options_summary(vin: str, db_path: str = "data/pdr_crm.db") -> Dict:
    """Get summary of vehicle options affecting R/I"""
    vehicle = decode_vin(vin, db_path)

    return {
        'vin': vin,
        'vehicle': get_vehicle_summary(vin, db_path),
        'has_sunroof': vehicle.get('has_sunroof', False),
        'has_roof_rails': vehicle.get('has_roof_rails', False),
        'has_shark_fin_antenna': vehicle.get('has_antenna_shark_fin', True),
        'ri_implications': _get_ri_implications(vehicle)
    }


def _get_ri_implications(vehicle: Dict) -> list:
    """Get list of R/I implications based on vehicle options"""
    implications = []

    if vehicle.get('has_sunroof'):
        implications.append("Use headliner R/I WITH SUNROOF time (RI-HDLNR-SR)")
    else:
        implications.append("Use standard headliner R/I time (RI-HDLNR)")

    if vehicle.get('has_roof_rails'):
        implications.append("Include roof rail R/I for roof panel work")

    if vehicle.get('has_antenna_shark_fin'):
        implications.append("Include antenna/shark fin R/I for roof work")

    return implications


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python vin_decoder.py <VIN>")
        sys.exit(1)

    vin = sys.argv[1]
    print(f"\nDecoding VIN: {vin}")
    print("-" * 50)

    result = decode_vin(vin)

    if result.get('error'):
        print(f"Error: {result['error']}")
    else:
        print(f"Year:       {result.get('year')}")
        print(f"Make:       {result.get('make')}")
        print(f"Model:      {result.get('model')}")
        print(f"Trim:       {result.get('trim')}")
        print(f"Body Style: {result.get('body_style')}")
        print(f"Doors:      {result.get('doors')}")
        print(f"Drive Type: {result.get('drive_type')}")
        print(f"Engine:     {result.get('engine')}")
        print()
        print("Options:")
        print(f"  Sunroof:    {'Yes' if result.get('has_sunroof') else 'No'}")
        print(f"  Roof Rails: {'Yes' if result.get('has_roof_rails') else 'No'}")
        print(f"  Shark Fin:  {'Yes' if result.get('has_antenna_shark_fin') else 'No'}")
