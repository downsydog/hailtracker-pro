"""
FMCSA Database Integration
==========================

Data source: https://safer.fmcsa.dot.gov/
Downloadable data: https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx

This gives us VERIFIED fleet sizes for trucking/logistics companies.
The FMCSA Motor Carrier Census includes:
- Company name and address
- Number of power units (trucks)
- Number of drivers
- Operating status
- Cargo types

100% FREE - just download the census file.
"""

import sqlite3
import csv
import os
import logging
import time
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger('FMCSA')


class FMCSADatabase:
    """Interface to FMCSA trucking company data."""

    # FMCSA data download info
    DOWNLOAD_URL = "https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx"
    DATA_INFO = """
    To populate this database:
    1. Go to: https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx
    2. Download "Motor Carrier Census Information" file
    3. Extract the CSV file
    4. Run: fmcsa.import_census_file('path/to/FMCSA_CENSUS1_YYYY.txt')
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / 'data' / 'fmcsa_carriers.db'
        self.db_path = str(db_path)
        self._ensure_db()

    def _ensure_db(self):
        """Create the database table if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS carriers (
                dot_number TEXT PRIMARY KEY,
                legal_name TEXT,
                dba_name TEXT,
                physical_address TEXT,
                physical_city TEXT,
                physical_state TEXT,
                physical_zip TEXT,
                phone TEXT,
                power_units INTEGER,
                drivers INTEGER,
                mcs150_date TEXT,
                carrier_operation TEXT,
                cargo_carried TEXT,
                latitude REAL,
                longitude REAL,
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city_state ON carriers(physical_city, physical_state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_power_units ON carriers(power_units)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_lat_lon ON carriers(latitude, longitude)')

        conn.commit()
        conn.close()
        logger.info(f"FMCSA database initialized: {self.db_path}")

    def search_by_city(self, city: str, state: str, min_vehicles: int = 1) -> List[Dict]:
        """
        Search for carriers in a city with minimum vehicle count.

        Args:
            city: City name
            state: State abbreviation (e.g., 'TX')
            min_vehicles: Minimum number of power units

        Returns:
            List of carrier dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                dot_number, legal_name, dba_name, physical_address,
                physical_city, physical_state, physical_zip, phone,
                power_units, drivers, carrier_operation, cargo_carried,
                latitude, longitude, category
            FROM carriers
            WHERE LOWER(physical_city) LIKE LOWER(?)
            AND UPPER(physical_state) = UPPER(?)
            AND power_units >= ?
            ORDER BY power_units DESC
            LIMIT 500
        ''', (f'%{city}%', state, min_vehicles))

        results = []
        for row in cursor.fetchall():
            carrier = dict(row)
            carrier['source'] = 'FMCSA'
            carrier['name'] = carrier.get('dba_name') or carrier.get('legal_name')
            carrier['vehicle_count'] = carrier.get('power_units') or 0
            carrier['verified_fleet'] = True
            if not carrier.get('category'):
                carrier['category'] = self._categorize_carrier(carrier)
            results.append(carrier)

        conn.close()
        return results

    def search_by_bbox(self, min_lat: float, min_lon: float,
                       max_lat: float, max_lon: float,
                       min_vehicles: int = 1) -> List[Dict]:
        """Search carriers within a bounding box."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                dot_number, legal_name, dba_name, physical_address,
                physical_city, physical_state, physical_zip, phone,
                power_units, drivers, carrier_operation, cargo_carried,
                latitude, longitude, category
            FROM carriers
            WHERE latitude BETWEEN ? AND ?
            AND longitude BETWEEN ? AND ?
            AND power_units >= ?
            ORDER BY power_units DESC
            LIMIT 500
        ''', (min_lat, max_lat, min_lon, max_lon, min_vehicles))

        results = []
        for row in cursor.fetchall():
            carrier = dict(row)
            carrier['source'] = 'FMCSA'
            carrier['name'] = carrier.get('dba_name') or carrier.get('legal_name')
            carrier['vehicle_count'] = carrier.get('power_units') or 0
            carrier['verified_fleet'] = True
            if not carrier.get('category'):
                carrier['category'] = self._categorize_carrier(carrier)
            results.append(carrier)

        conn.close()
        return results

    def _categorize_carrier(self, carrier: Dict) -> str:
        """Categorize carrier based on cargo and name."""
        name = ((carrier.get('legal_name') or '') + ' ' +
                (carrier.get('dba_name') or '')).lower()
        cargo = (carrier.get('cargo_carried') or '').lower()

        if any(x in name for x in ['landscap', 'lawn', 'tree', 'garden']):
            return 'landscaping'
        elif any(x in name for x in ['pest', 'exterminator']):
            return 'pest_control'
        elif any(x in name for x in ['moving', 'mover', 'relocation']):
            return 'moving'
        elif any(x in name for x in ['hvac', 'heating', 'cooling', 'air condition']):
            return 'service_trades'
        elif any(x in name for x in ['plumb']):
            return 'service_trades'
        elif any(x in name for x in ['electric']):
            return 'service_trades'
        elif any(x in name for x in ['tow', 'wrecker']):
            return 'towing'
        elif any(x in cargo for x in ['food', 'beverage', 'refrigerated', 'produce']):
            return 'food_distribution'
        elif any(x in cargo for x in ['household goods']):
            return 'moving'
        else:
            return 'delivery'

    def import_census_file(self, csv_path: str) -> int:
        """
        Import FMCSA census data from CSV file.

        Download the census file from:
        https://ai.fmcsa.dot.gov/SMS/Tools/Downloads.aspx

        Look for "Motor Carrier Census Information" file.
        The file is typically named like FMCSA_CENSUS1_2024Oct.txt
        """
        logger.info(f"Importing FMCSA data from {csv_path}...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        imported = 0
        skipped = 0

        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Try to detect delimiter
            first_line = f.readline()
            f.seek(0)

            if '\t' in first_line:
                delimiter = '\t'
            elif '|' in first_line:
                delimiter = '|'
            else:
                delimiter = ','

            reader = csv.DictReader(f, delimiter=delimiter)

            for row in reader:
                try:
                    # Handle different column naming conventions
                    power_units = int(row.get('NBR_POWER_UNIT') or
                                      row.get('POWER_UNITS') or
                                      row.get('power_units') or 0)

                    # Skip carriers with no vehicles
                    if power_units < 1:
                        skipped += 1
                        continue

                    dot_number = (row.get('DOT_NUMBER') or
                                  row.get('dot_number') or '')

                    if not dot_number:
                        continue

                    cursor.execute('''
                        INSERT OR REPLACE INTO carriers (
                            dot_number, legal_name, dba_name, physical_address,
                            physical_city, physical_state, physical_zip, phone,
                            power_units, drivers, mcs150_date, carrier_operation,
                            cargo_carried
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        dot_number,
                        row.get('LEGAL_NAME') or row.get('legal_name'),
                        row.get('DBA_NAME') or row.get('dba_name'),
                        row.get('PHY_STREET') or row.get('phy_street'),
                        row.get('PHY_CITY') or row.get('phy_city'),
                        row.get('PHY_STATE') or row.get('phy_state'),
                        row.get('PHY_ZIP') or row.get('phy_zip'),
                        row.get('TELEPHONE') or row.get('telephone'),
                        power_units,
                        int(row.get('DRIVER_TOTAL') or row.get('driver_total') or 0),
                        row.get('MCS150_DATE') or row.get('mcs150_date'),
                        row.get('CARRIER_OPERATION') or row.get('carrier_operation'),
                        row.get('CARGO_CARRIED') or row.get('cargo_carried'),
                    ))

                    imported += 1
                    if imported % 10000 == 0:
                        logger.info(f"  Imported {imported} carriers...")
                        conn.commit()

                except Exception as e:
                    continue

        conn.commit()
        conn.close()
        logger.info(f"Import complete: {imported} carriers with vehicles, {skipped} skipped")

        return imported

    def geocode_carriers(self, limit: int = 1000) -> int:
        """
        Add lat/lon to carriers using Nominatim (free geocoding).
        Run this after importing census data.

        Rate limited to 1 request/second for Nominatim.
        """
        import requests

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT dot_number, physical_address, physical_city, physical_state, physical_zip
            FROM carriers
            WHERE latitude IS NULL AND physical_city IS NOT NULL
            ORDER BY power_units DESC
            LIMIT ?
        ''', (limit,))

        carriers = cursor.fetchall()
        logger.info(f"Geocoding {len(carriers)} carriers...")

        geocoded = 0
        for dot, address, city, state, zip_code in carriers:
            try:
                # Build address query
                parts = [p for p in [address, city, state, zip_code] if p]
                query = ', '.join(parts)

                url = "https://nominatim.openstreetmap.org/search"
                params = {
                    'q': query,
                    'format': 'json',
                    'limit': 1,
                    'countrycodes': 'us'
                }

                response = requests.get(url, params=params,
                                         headers={'User-Agent': 'HailTrackerPro/1.0'})
                data = response.json()

                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])

                    cursor.execute('''
                        UPDATE carriers SET latitude = ?, longitude = ? WHERE dot_number = ?
                    ''', (lat, lon, dot))

                    geocoded += 1
                    if geocoded % 100 == 0:
                        logger.info(f"  Geocoded {geocoded} carriers...")
                        conn.commit()

                # Rate limit: 1 request per second for Nominatim
                time.sleep(1.1)

            except Exception as e:
                logger.warning(f"Geocoding error for {dot}: {e}")
                continue

        conn.commit()
        conn.close()
        logger.info(f"Geocoding complete: {geocoded} carriers updated")

        return geocoded

    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM carriers')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(power_units) FROM carriers')
        total_vehicles = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(*) FROM carriers WHERE latitude IS NOT NULL')
        geocoded = cursor.fetchone()[0]

        cursor.execute('''
            SELECT physical_state, COUNT(*), SUM(power_units)
            FROM carriers
            GROUP BY physical_state
            ORDER BY SUM(power_units) DESC
            LIMIT 10
        ''')
        top_states = [{'state': r[0], 'carriers': r[1], 'vehicles': r[2]}
                      for r in cursor.fetchall()]

        conn.close()

        return {
            'total_carriers': total,
            'total_vehicles': total_vehicles,
            'geocoded_carriers': geocoded,
            'top_states': top_states,
            'data_source': 'FMCSA Motor Carrier Census',
            'download_url': self.DOWNLOAD_URL,
        }

    def is_populated(self) -> bool:
        """Check if the database has data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM carriers')
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
