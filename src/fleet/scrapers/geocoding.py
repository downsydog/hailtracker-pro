"""
Geocoding Service
=================

Convert addresses to lat/lon coordinates using Nominatim (OpenStreetMap).

FREE to use - requires 1 second delay between requests.
"""

import requests
import sqlite3
import time
import logging
from typing import Dict, Optional, Tuple, List
from pathlib import Path

logger = logging.getLogger('GeocodingService')


class GeocodingService:
    """
    Geocode addresses using Nominatim (OpenStreetMap).

    Features:
    - Caches results in SQLite to avoid repeat lookups
    - Respects Nominatim rate limit (1 request/second)
    - Handles batch geocoding for multiple businesses
    """

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self, db_path: str = None, cache_db_path: str = None):
        """
        Initialize geocoding service.

        Args:
            db_path: Path to businesses database
            cache_db_path: Path to geocoding cache (default: same dir as db)
        """
        if db_path is None:
            data_dir = Path(__file__).parent.parent.parent.parent / 'data'
            db_path = str(data_dir / 'fleet_businesses.db')

        self.db_path = db_path

        if cache_db_path is None:
            cache_db_path = str(Path(db_path).parent / 'geocode_cache.db')

        self.cache_db_path = cache_db_path
        self._init_cache_db()
        self._last_request_time = 0

        # Session with proper user-agent (required by Nominatim)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTrackerPDR/1.0 (PDR fleet prospecting tool)',
            'Accept': 'application/json',
        })

    def _init_cache_db(self):
        """Initialize geocoding cache database."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS geocode_cache (
                address TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                display_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logger.debug(f"Geocode cache initialized: {self.cache_db_path}")

    def _rate_limit(self):
        """Ensure we respect Nominatim's 1 request/second rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        self._last_request_time = time.time()

    def _check_cache(self, address: str) -> Optional[Tuple[float, float]]:
        """Check if address is in cache."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT latitude, longitude FROM geocode_cache WHERE address = ?',
            (address,)
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0] is not None:
            return (result[0], result[1])
        return None

    def _cache_result(self, address: str, lat: float, lon: float, display_name: str = None):
        """Cache a geocoding result."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO geocode_cache (address, latitude, longitude, display_name)
            VALUES (?, ?, ?, ?)
        ''', (address, lat, lon, display_name))

        conn.commit()
        conn.close()

    def geocode(self, address: str = None, city: str = None, state: str = None,
                zip_code: str = None) -> Optional[Tuple[float, float]]:
        """
        Geocode a single address.

        Args:
            address: Street address
            city: City name
            state: State abbreviation
            zip_code: ZIP code

        Returns:
            Tuple of (latitude, longitude) or None if not found
        """
        # Build full address string
        parts = [p for p in [address, city, state, zip_code] if p]
        full_address = ', '.join(parts)

        if not full_address:
            return None

        # Check cache first
        cached = self._check_cache(full_address)
        if cached:
            logger.debug(f"Cache hit: {full_address[:50]}...")
            return cached

        # Rate limit
        self._rate_limit()

        try:
            params = {
                'q': full_address,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'us',
            }

            response = self.session.get(self.NOMINATIM_URL, params=params, timeout=10)

            if response.ok:
                results = response.json()

                if results:
                    lat = float(results[0]['lat'])
                    lon = float(results[0]['lon'])
                    display_name = results[0].get('display_name', '')

                    # Cache the result
                    self._cache_result(full_address, lat, lon, display_name)

                    logger.debug(f"Geocoded: {full_address[:50]}... -> ({lat}, {lon})")
                    return (lat, lon)
                else:
                    # Cache empty result to avoid repeat lookups
                    self._cache_result(full_address, None, None, None)
                    logger.debug(f"No results for: {full_address[:50]}...")

        except Exception as e:
            logger.error(f"Geocoding error: {e}")

        return None

    def geocode_business(self, business: Dict) -> Optional[Tuple[float, float]]:
        """
        Geocode a business dictionary.

        Args:
            business: Dict with address, city, state, zip fields

        Returns:
            Tuple of (latitude, longitude) or None
        """
        return self.geocode(
            address=business.get('address'),
            city=business.get('city'),
            state=business.get('state'),
            zip_code=business.get('zip')
        )

    def geocode_businesses_in_db(self, limit: int = 100, batch_size: int = 50) -> int:
        """
        Geocode businesses in the database that don't have coordinates.

        Args:
            limit: Maximum businesses to geocode
            batch_size: Commit after this many updates

        Returns:
            Number of businesses geocoded
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find businesses without coordinates
        cursor.execute('''
            SELECT id, name, address, city, state, zip
            FROM businesses
            WHERE (latitude IS NULL OR longitude IS NULL)
              AND address IS NOT NULL
            LIMIT ?
        ''', (limit,))

        businesses = cursor.fetchall()
        logger.info(f"Found {len(businesses)} businesses to geocode")

        geocoded = 0

        for i, (biz_id, name, address, city, state, zip_code) in enumerate(businesses):
            coords = self.geocode(address, city, state, zip_code)

            if coords:
                cursor.execute('''
                    UPDATE businesses
                    SET latitude = ?, longitude = ?
                    WHERE id = ?
                ''', (coords[0], coords[1], biz_id))

                geocoded += 1
                logger.info(f"  [{i+1}/{len(businesses)}] {name}: ({coords[0]:.4f}, {coords[1]:.4f})")

            else:
                logger.debug(f"  [{i+1}/{len(businesses)}] {name}: No coordinates found")

            # Commit in batches
            if (i + 1) % batch_size == 0:
                conn.commit()
                logger.info(f"  Committed batch ({i+1} processed)")

        conn.commit()
        conn.close()

        logger.info(f"Geocoded {geocoded} of {len(businesses)} businesses")
        return geocoded

    def geocode_city_center(self, city: str, state: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a city center.

        Args:
            city: City name
            state: State abbreviation

        Returns:
            Tuple of (latitude, longitude) for city center
        """
        return self.geocode(city=city, state=state)

    def get_cache_stats(self) -> Dict:
        """Get statistics about the geocoding cache."""
        conn = sqlite3.connect(self.cache_db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM geocode_cache')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM geocode_cache WHERE latitude IS NOT NULL')
        successful = cursor.fetchone()[0]

        conn.close()

        return {
            'total_cached': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
        }


def geocode_all_businesses(db_path: str = None, limit: int = 500):
    """
    Convenience function to geocode all businesses in database.

    Args:
        db_path: Path to database
        limit: Maximum to geocode (default: 500)
    """
    service = GeocodingService(db_path=db_path)
    geocoded = service.geocode_businesses_in_db(limit=limit)

    stats = service.get_cache_stats()
    print(f"\nGeocoding Complete!")
    print(f"  Businesses geocoded: {geocoded}")
    print(f"  Cache total: {stats['total_cached']}")
    print(f"  Cache success rate: {stats['success_rate']:.1f}%")

    return geocoded
