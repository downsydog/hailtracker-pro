"""
Base Scraper Class for Business Discovery
==========================================

All business scrapers inherit from this base class.
Provides common functionality for scraping, parsing, and storing business data.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import sqlite3
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import re
import logging
from pathlib import Path

logger = logging.getLogger('BusinessScraper')


class BaseScraper(ABC):
    """Base class for all business scrapers."""

    # Vehicle estimates by category
    VEHICLE_ESTIMATES = {
        # Tier 1 - High vehicle count (50+)
        'car_dealership': 150,
        'auto_auction': 500,
        'car_rental': 80,
        'government': 75,
        'municipal': 75,
        'school': 50,
        'school_district': 100,
        'hospital': 100,
        'university': 75,
        'transit': 100,
        # Tier 2 - Medium vehicle count (10-50)
        'landscaping': 12,
        'lawn_care': 8,
        'pest_control': 15,
        'hvac': 10,
        'plumbing': 8,
        'electrical': 8,
        'roofing': 10,
        'contractor': 12,
        'general_contractor': 12,
        'moving': 20,
        'security': 25,
        'property_management': 15,
        'cleaning': 10,
        'janitorial': 10,
        'catering': 8,
        'food_distribution': 25,
        'delivery': 15,
        'courier': 12,
        'towing': 10,
        # Tier 3 - Smaller fleets (5-15)
        'pool_service': 6,
        'garage_door': 5,
        'appliance_repair': 5,
        'carpet_cleaning': 4,
        'window_cleaning': 4,
        'pressure_washing': 4,
        'painting': 6,
        'flooring': 5,
        'tree_service': 8,
        'irrigation': 5,
        'septic': 5,
        'locksmith': 4,
        'glass_repair': 4,
        'fencing': 6,
        'concrete': 8,
    }

    # Categories by tier
    TIER_1_CATEGORIES = [
        'car_dealership', 'auto_auction', 'car_rental', 'government',
        'municipal', 'school', 'school_district', 'hospital',
        'university', 'transit'
    ]

    TIER_2_CATEGORIES = [
        'landscaping', 'lawn_care', 'pest_control', 'hvac', 'plumbing',
        'electrical', 'roofing', 'contractor', 'general_contractor',
        'moving', 'security', 'property_management', 'cleaning',
        'janitorial', 'catering', 'food_distribution', 'delivery',
        'courier', 'towing'
    ]

    def __init__(self, db_path: str = None):
        """
        Initialize the scraper.

        Args:
            db_path: Path to SQLite database for storing results
        """
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            db_path = project_root / 'data' / 'business_prospects.db'

        self.db_path = str(db_path)

        # Set up requests session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
        })

        self._ensure_db()

    def _ensure_db(self):
        """Create database tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                city TEXT,
                state TEXT,
                zip TEXT,
                phone TEXT,
                website TEXT,
                email TEXT,
                category TEXT,
                subcategory TEXT,
                source TEXT,
                latitude REAL,
                longitude REAL,
                estimated_vehicles INTEGER DEFAULT 0,
                tier INTEGER DEFAULT 3,
                rating REAL,
                review_count INTEGER,
                years_in_business INTEGER,
                employees TEXT,
                bbb_accredited INTEGER DEFAULT 0,
                notes TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, address, city, state)
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_biz_city_state ON businesses(city, state)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_biz_category ON businesses(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_biz_tier ON businesses(tier)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_biz_vehicles ON businesses(estimated_vehicles)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_biz_source ON businesses(source)')

        conn.commit()
        conn.close()
        logger.info(f"Business database initialized: {self.db_path}")

    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Random delay to avoid rate limiting."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _clean_phone(self, phone: str) -> str:
        """Clean and format phone number."""
        if not phone:
            return ''

        # Extract digits
        digits = re.sub(r'\D', '', phone)

        # Format as (xxx) xxx-xxxx
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

        return phone

    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace."""
        if not text:
            return ''
        return ' '.join(text.split())

    def _estimate_vehicles(self, category: str, employees: str = None,
                          review_count: int = None, name: str = None) -> int:
        """
        Estimate vehicle count based on business type and size indicators.

        Args:
            category: Business category
            employees: Employee count (can be range like "10-50")
            review_count: Number of reviews (proxy for business size)
            name: Business name (to detect chains)

        Returns:
            Estimated vehicle count
        """
        # Base estimate from category
        base = self.VEHICLE_ESTIMATES.get(category, 5)

        multiplier = 1.0

        # Adjust based on employee count
        if employees:
            try:
                if '-' in str(employees):
                    emp_count = int(str(employees).split('-')[1])
                else:
                    emp_count = int(re.sub(r'\D', '', str(employees)) or 0)

                if emp_count > 100:
                    multiplier *= 2.5
                elif emp_count > 50:
                    multiplier *= 2.0
                elif emp_count > 20:
                    multiplier *= 1.5
                elif emp_count > 10:
                    multiplier *= 1.2
            except:
                pass

        # Adjust based on review count
        if review_count:
            if review_count > 500:
                multiplier *= 2.0
            elif review_count > 200:
                multiplier *= 1.5
            elif review_count > 100:
                multiplier *= 1.2
            elif review_count > 50:
                multiplier *= 1.1

        # Detect large chains by name
        if name:
            name_lower = name.lower()
            large_chains = [
                'enterprise', 'hertz', 'avis', 'budget', 'national',
                'sysco', 'us foods', 'fedex', 'ups', 'amazon',
                'terminix', 'orkin', 'trugreen', 'servicemaster',
                'adt', 'brinks', 'securitas',
                'united rentals', 'sunbelt',
            ]
            if any(chain in name_lower for chain in large_chains):
                multiplier *= 1.5

        return max(1, int(base * multiplier))

    def _get_tier(self, category: str) -> int:
        """Get tier (1-3) based on category."""
        if category in self.TIER_1_CATEGORIES:
            return 1
        elif category in self.TIER_2_CATEGORIES:
            return 2
        else:
            return 3

    def save_business(self, business: Dict) -> bool:
        """
        Save a business to the database.

        Args:
            business: Dictionary with business data

        Returns:
            True if saved (new record), False if skipped (duplicate)
        """
        if not business.get('name'):
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Estimate vehicles if not provided
            if not business.get('estimated_vehicles'):
                business['estimated_vehicles'] = self._estimate_vehicles(
                    business.get('category', ''),
                    business.get('employees'),
                    business.get('review_count'),
                    business.get('name')
                )

            # Get tier if not provided
            if not business.get('tier'):
                business['tier'] = self._get_tier(business.get('category', ''))

            cursor.execute('''
                INSERT OR IGNORE INTO businesses (
                    name, address, city, state, zip, phone, website, email,
                    category, subcategory, source, latitude, longitude,
                    estimated_vehicles, tier, rating, review_count,
                    years_in_business, employees, bbb_accredited, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self._clean_text(business.get('name')),
                self._clean_text(business.get('address')),
                self._clean_text(business.get('city')),
                business.get('state', '').upper() if business.get('state') else None,
                business.get('zip'),
                self._clean_phone(business.get('phone', '')),
                business.get('website'),
                business.get('email'),
                business.get('category'),
                business.get('subcategory'),
                business.get('source'),
                business.get('latitude'),
                business.get('longitude'),
                business.get('estimated_vehicles', 0),
                business.get('tier', 3),
                business.get('rating'),
                business.get('review_count'),
                business.get('years_in_business'),
                business.get('employees'),
                1 if business.get('bbb_accredited') else 0,
                business.get('notes'),
            ))

            conn.commit()
            success = cursor.rowcount > 0
            conn.close()
            return success

        except Exception as e:
            conn.close()
            logger.error(f"Error saving business: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get database statistics."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) as count FROM businesses')
        total = cursor.fetchone()['count']

        cursor.execute('SELECT SUM(estimated_vehicles) as sum FROM businesses')
        total_vehicles = cursor.fetchone()['sum'] or 0

        cursor.execute('''
            SELECT category, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM businesses
            GROUP BY category
            ORDER BY SUM(estimated_vehicles) DESC
            LIMIT 20
        ''')
        by_category = [dict(row) for row in cursor.fetchall()]

        cursor.execute('''
            SELECT tier, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM businesses
            GROUP BY tier
            ORDER BY tier
        ''')
        by_tier = [dict(row) for row in cursor.fetchall()]

        cursor.execute('''
            SELECT city, state, COUNT(*) as count, SUM(estimated_vehicles) as vehicles
            FROM businesses
            GROUP BY city, state
            ORDER BY COUNT(*) DESC
            LIMIT 15
        ''')
        by_city = [dict(row) for row in cursor.fetchall()]

        cursor.execute('''
            SELECT source, COUNT(*) as count
            FROM businesses
            GROUP BY source
        ''')
        by_source = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return {
            'total_businesses': total,
            'total_estimated_vehicles': total_vehicles,
            'by_category': by_category,
            'by_tier': by_tier,
            'by_city': by_city,
            'by_source': by_source,
        }

    @abstractmethod
    def search(self, city: str, state: str, category: str) -> List[Dict]:
        """
        Search for businesses. Must be implemented by subclasses.

        Args:
            city: City name
            state: State abbreviation
            category: Category to search

        Returns:
            List of business dictionaries
        """
        pass

    @abstractmethod
    def scrape_city(self, city: str, state: str) -> int:
        """
        Scrape all relevant businesses in a city.
        Must be implemented by subclasses.

        Args:
            city: City name
            state: State abbreviation

        Returns:
            Number of new businesses saved
        """
        pass
