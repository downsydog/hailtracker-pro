"""Seed test hail events for demonstration."""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / 'database' / 'hailtracker_pro.db'

# Test events across North America
TEST_EVENTS = [
    # Recent severe events (high opportunity)
    {
        'date_offset': 2,  # days ago
        'lat': 35.4676, 'lon': -97.5164,
        'city': 'Oklahoma City', 'state': 'OK', 'country': 'US',
        'hail_size': 2.25, 'duration': 45, 'area': 180,
        'radar': 'KTLX', 'confidence': 0.95
    },
    {
        'date_offset': 5,
        'lat': 32.7767, 'lon': -96.7970,
        'city': 'Dallas', 'state': 'TX', 'country': 'US',
        'hail_size': 1.75, 'duration': 30, 'area': 120,
        'radar': 'KFWS', 'confidence': 0.92
    },
    {
        'date_offset': 7,
        'lat': 39.7392, 'lon': -104.9903,
        'city': 'Denver', 'state': 'CO', 'country': 'US',
        'hail_size': 2.0, 'duration': 35, 'area': 95,
        'radar': 'KFTG', 'confidence': 0.94
    },
    # Canadian events
    {
        'date_offset': 10,
        'lat': 51.0447, 'lon': -114.0719,
        'city': 'Calgary', 'state': 'AB', 'country': 'CA',
        'hail_size': 1.5, 'duration': 25, 'area': 85,
        'radar': 'CAXWH', 'confidence': 0.88
    },
    {
        'date_offset': 14,
        'lat': 53.5461, 'lon': -113.4938,
        'city': 'Edmonton', 'state': 'AB', 'country': 'CA',
        'hail_size': 1.25, 'duration': 20, 'area': 60,
        'radar': 'CAXWH', 'confidence': 0.85
    },
    # Mexico events
    {
        'date_offset': 12,
        'lat': 25.6866, 'lon': -100.3161,
        'city': 'Monterrey', 'state': 'NLE', 'country': 'MX',
        'hail_size': 1.0, 'duration': 15, 'area': 40,
        'radar': 'MMMY', 'confidence': 0.80
    },
    {
        'date_offset': 18,
        'lat': 20.6597, 'lon': -103.3496,
        'city': 'Guadalajara', 'state': 'JAL', 'country': 'MX',
        'hail_size': 1.25, 'duration': 20, 'area': 55,
        'radar': 'MMGL', 'confidence': 0.78
    },
    # More US events - Tornado Alley
    {
        'date_offset': 3,
        'lat': 37.6872, 'lon': -97.3301,
        'city': 'Wichita', 'state': 'KS', 'country': 'US',
        'hail_size': 1.75, 'duration': 40, 'area': 110,
        'radar': 'KICT', 'confidence': 0.91
    },
    {
        'date_offset': 8,
        'lat': 41.2565, 'lon': -95.9345,
        'city': 'Omaha', 'state': 'NE', 'country': 'US',
        'hail_size': 1.5, 'duration': 28, 'area': 75,
        'radar': 'KOAX', 'confidence': 0.89
    },
    {
        'date_offset': 15,
        'lat': 36.1540, 'lon': -95.9928,
        'city': 'Tulsa', 'state': 'OK', 'country': 'US',
        'hail_size': 2.5, 'duration': 55, 'area': 200,
        'radar': 'KINX', 'confidence': 0.96
    },
    # Midwest events
    {
        'date_offset': 20,
        'lat': 41.8781, 'lon': -87.6298,
        'city': 'Chicago', 'state': 'IL', 'country': 'US',
        'hail_size': 1.0, 'duration': 18, 'area': 45,
        'radar': 'KLOT', 'confidence': 0.87
    },
    {
        'date_offset': 25,
        'lat': 44.9778, 'lon': -93.2650,
        'city': 'Minneapolis', 'state': 'MN', 'country': 'US',
        'hail_size': 1.25, 'duration': 22, 'area': 65,
        'radar': 'KMPX', 'confidence': 0.86
    },
    # Texas Triangle
    {
        'date_offset': 4,
        'lat': 29.7604, 'lon': -95.3698,
        'city': 'Houston', 'state': 'TX', 'country': 'US',
        'hail_size': 1.5, 'duration': 32, 'area': 90,
        'radar': 'KHGX', 'confidence': 0.90
    },
    {
        'date_offset': 6,
        'lat': 30.2672, 'lon': -97.7431,
        'city': 'Austin', 'state': 'TX', 'country': 'US',
        'hail_size': 1.75, 'duration': 38, 'area': 105,
        'radar': 'KEWX', 'confidence': 0.93
    },
    {
        'date_offset': 9,
        'lat': 29.4241, 'lon': -98.4936,
        'city': 'San Antonio', 'state': 'TX', 'country': 'US',
        'hail_size': 2.0, 'duration': 42, 'area': 130,
        'radar': 'KEWX', 'confidence': 0.94
    },
    # Southeast
    {
        'date_offset': 22,
        'lat': 33.7490, 'lon': -84.3880,
        'city': 'Atlanta', 'state': 'GA', 'country': 'US',
        'hail_size': 1.0, 'duration': 15, 'area': 35,
        'radar': 'KFFC', 'confidence': 0.84
    },
    {
        'date_offset': 28,
        'lat': 36.1627, 'lon': -86.7816,
        'city': 'Nashville', 'state': 'TN', 'country': 'US',
        'hail_size': 1.25, 'duration': 20, 'area': 50,
        'radar': 'KOHX', 'confidence': 0.85
    },
    # Canadian Prairies
    {
        'date_offset': 16,
        'lat': 52.1332, 'lon': -106.6700,
        'city': 'Saskatoon', 'state': 'SK', 'country': 'CA',
        'hail_size': 1.5, 'duration': 30, 'area': 70,
        'radar': 'CAXSS', 'confidence': 0.87
    },
    {
        'date_offset': 21,
        'lat': 49.8951, 'lon': -97.1384,
        'city': 'Winnipeg', 'state': 'MB', 'country': 'CA',
        'hail_size': 1.0, 'duration': 18, 'area': 40,
        'radar': 'CAXWL', 'confidence': 0.82
    },
    # Great Plains
    {
        'date_offset': 11,
        'lat': 43.5460, 'lon': -96.7313,
        'city': 'Sioux Falls', 'state': 'SD', 'country': 'US',
        'hail_size': 1.75, 'duration': 35, 'area': 85,
        'radar': 'KFSD', 'confidence': 0.90
    },
]


def seed_events():
    """Insert test events into database."""
    print("=" * 60)
    print("SEEDING TEST HAIL EVENTS")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Clear existing events
    cursor.execute("DELETE FROM hail_events")
    cursor.execute("DELETE FROM pdr_opportunities")
    print("\nCleared existing events")

    now = datetime.now()
    inserted = 0

    for event in TEST_EVENTS:
        event_date = (now - timedelta(days=event['date_offset'])).strftime('%Y-%m-%d')
        event_time = f"{random.randint(14, 20)}:{random.randint(0, 59):02d}:00"

        # Calculate PDR opportunity score (simplified)
        size = event['hail_size']
        age = event['date_offset']

        if size >= 2.0:
            base_score = 85
        elif size >= 1.5:
            base_score = 70
        elif size >= 1.0:
            base_score = 55
        else:
            base_score = 40

        # Age penalty
        if age <= 7:
            age_bonus = 10
        elif age <= 14:
            age_bonus = 5
        elif age <= 30:
            age_bonus = 0
        else:
            age_bonus = -10

        pdr_score = min(100, base_score + age_bonus)

        utc_datetime = (now - timedelta(days=event['date_offset'])).strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute("""
            INSERT INTO hail_events (
                event_date, event_time, utc_datetime, latitude, longitude,
                city, state_province, country,
                max_hail_size_inches, duration_minutes, affected_area_km2,
                primary_radar, radar_confidence, pdr_opportunity_score,
                processed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            event_date, event_time, utc_datetime,
            event['lat'], event['lon'],
            event['city'], event['state'],
            event['country'],
            event['hail_size'], event['duration'], event['area'],
            event['radar'], 'HIGH' if event['confidence'] >= 0.9 else 'MEDIUM', pdr_score
        ))

        inserted += 1
        severity = 'SEVERE' if size >= 2.0 else 'MODERATE' if size >= 1.5 else 'LIGHT'
        print(f"  + {event['city']}, {event['state']} ({event['country']}) - {size}\" [{severity}] - {age} days ago")

    conn.commit()

    # Summary by country
    cursor.execute("SELECT country, COUNT(*) FROM hail_events GROUP BY country")
    by_country = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM hail_events WHERE max_hail_size_inches >= 2.0")
    severe_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM hail_events WHERE max_hail_size_inches >= 1.5 AND max_hail_size_inches < 2.0")
    moderate_count = cursor.fetchone()[0]

    conn.close()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTotal Events: {inserted}")
    print("\nBy Country:")
    for country, count in by_country:
        print(f"  {country}: {count}")
    print(f"\nBy Severity:")
    print(f"  Severe (2.0\"+): {severe_count}")
    print(f"  Moderate (1.5-2.0\"): {moderate_count}")
    print(f"  Light (<1.5\"): {inserted - severe_count - moderate_count}")
    print("\nTest events seeded successfully!")


if __name__ == '__main__':
    seed_events()
