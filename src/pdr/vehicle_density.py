"""
Vehicle Density Estimator

Estimates vehicle density and concentration zones for hail damage assessment:
- Dealership lots
- Shopping centers
- Parking garages
- Residential areas
- Highway traffic
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger('VehicleDensityEstimator')


@dataclass
class VehicleZone:
    """A zone with concentrated vehicles."""
    zone_id: str
    zone_type: str  # 'dealership', 'mall', 'parking', 'residential', 'highway'
    name: str
    lat: float
    lon: float
    estimated_vehicles: int
    typical_occupancy: float  # 0-1
    peak_occupancy: float
    operating_hours: str
    priority: int  # 1-5, 1 = highest


@dataclass
class DensityEstimate:
    """Estimated vehicle density for an area."""
    lat: float
    lon: float
    radius_km: float
    total_vehicles: int
    outdoor_vehicles: int
    dealership_vehicles: int
    residential_vehicles: int
    commercial_vehicles: int
    zones: List[VehicleZone]


class VehicleDensityEstimator:
    """
    Estimates vehicle density in areas affected by hail.
    """

    # Average vehicles per zone type
    ZONE_ESTIMATES = {
        'dealership': {
            'vehicles': 300,
            'outdoor_pct': 0.95,
            'damage_vulnerability': 0.95
        },
        'mall': {
            'vehicles': 1500,
            'outdoor_pct': 0.90,
            'damage_vulnerability': 0.85
        },
        'parking_garage': {
            'vehicles': 500,
            'outdoor_pct': 0.10,  # Top floor only
            'damage_vulnerability': 0.15
        },
        'office_complex': {
            'vehicles': 400,
            'outdoor_pct': 0.70,
            'damage_vulnerability': 0.65
        },
        'hospital': {
            'vehicles': 800,
            'outdoor_pct': 0.50,
            'damage_vulnerability': 0.45
        },
        'airport_parking': {
            'vehicles': 5000,
            'outdoor_pct': 0.60,
            'damage_vulnerability': 0.55
        },
        'residential_dense': {
            'vehicles_per_km2': 2000,
            'outdoor_pct': 0.30,
            'damage_vulnerability': 0.25
        },
        'residential_suburban': {
            'vehicles_per_km2': 800,
            'outdoor_pct': 0.40,
            'damage_vulnerability': 0.35
        },
        'residential_rural': {
            'vehicles_per_km2': 200,
            'outdoor_pct': 0.50,
            'damage_vulnerability': 0.45
        },
    }

    # Time-of-day multipliers for outdoor vehicles
    TIME_MULTIPLIERS = {
        'morning_rush': 0.80,    # 7-9 AM - many in transit
        'workday': 0.60,         # 9 AM - 5 PM - parked at work
        'evening_rush': 0.85,    # 5-7 PM - many in transit
        'evening': 0.45,         # 7-10 PM - many home in garages
        'night': 0.35,           # 10 PM - 6 AM - mostly garaged
        'weekend_day': 0.55,     # Weekend daytime
    }

    def __init__(self, db_path: str = None):
        """
        Initialize vehicle density estimator.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')

    def estimate_density(
        self,
        lat: float,
        lon: float,
        radius_km: float = 10.0,
        time_of_day: str = 'workday'
    ) -> DensityEstimate:
        """
        Estimate vehicle density in an area.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Radius in kilometers
            time_of_day: Time category for occupancy adjustment

        Returns:
            DensityEstimate with all metrics
        """
        # Load known zones from database
        zones = self._load_zones_in_area(lat, lon, radius_km)

        # Calculate area
        area_km2 = math.pi * radius_km ** 2

        # Estimate by zone type
        dealership_vehicles = 0
        commercial_vehicles = 0
        outdoor_vehicles = 0

        for zone in zones:
            zone_vehicles = self._estimate_zone_vehicles(zone, time_of_day)
            outdoor_vehicles += zone_vehicles

            if zone.zone_type == 'dealership':
                dealership_vehicles += zone.estimated_vehicles
            else:
                commercial_vehicles += zone.estimated_vehicles

        # Estimate residential vehicles
        residential_density = self._get_residential_density(lat, lon)
        residential_vehicles = int(area_km2 * residential_density)
        residential_outdoor = int(residential_vehicles *
                                 self.ZONE_ESTIMATES['residential_suburban']['outdoor_pct'] *
                                 self.TIME_MULTIPLIERS.get(time_of_day, 0.5))

        # Total outdoor vehicles
        total_outdoor = outdoor_vehicles + residential_outdoor

        # Total vehicles (including garaged)
        total_vehicles = sum(z.estimated_vehicles for z in zones) + residential_vehicles

        return DensityEstimate(
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            total_vehicles=total_vehicles,
            outdoor_vehicles=total_outdoor,
            dealership_vehicles=dealership_vehicles,
            residential_vehicles=residential_vehicles,
            commercial_vehicles=commercial_vehicles,
            zones=zones
        )

    def _load_zones_in_area(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[VehicleZone]:
        """Load vehicle concentration zones from database."""
        zones = []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Simple bounding box query (SQLite doesn't have spatial extensions)
            # Convert radius to approximate lat/lon bounds
            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

            cursor.execute("""
                SELECT id, zone_type, name, latitude, longitude,
                       parking_spaces, typical_occupancy_rate, operating_hours
                FROM vehicle_concentration_zones
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
            """, (
                lat - lat_delta, lat + lat_delta,
                lon - lon_delta, lon + lon_delta
            ))

            for row in cursor.fetchall():
                zones.append(VehicleZone(
                    zone_id=str(row['id']),
                    zone_type=row['zone_type'] or 'commercial',
                    name=row['name'],
                    lat=row['latitude'],
                    lon=row['longitude'],
                    estimated_vehicles=row['parking_spaces'] or 200,
                    typical_occupancy=row['typical_occupancy_rate'] or 0.7,
                    peak_occupancy=0.95,
                    operating_hours=row['operating_hours'] or '24/7',
                    priority=2
                ))

            conn.close()

        except Exception as e:
            logger.warning(f"Error loading zones: {e}")
            # Generate synthetic zones based on location
            zones = self._generate_synthetic_zones(lat, lon, radius_km)

        return zones

    def _generate_synthetic_zones(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[VehicleZone]:
        """Generate synthetic vehicle zones when no database data available."""
        zones = []

        # Estimate number of zones based on area
        area_km2 = math.pi * radius_km ** 2

        # Approximate zone counts
        num_dealerships = max(1, int(area_km2 / 50))  # 1 per 50 km²
        num_malls = max(1, int(area_km2 / 100))       # 1 per 100 km²
        num_offices = max(2, int(area_km2 / 30))     # 1 per 30 km²

        # Generate dealerships
        for i in range(num_dealerships):
            offset_lat = (i - num_dealerships/2) * 0.02
            offset_lon = (i % 3 - 1) * 0.02
            zones.append(VehicleZone(
                zone_id=f'dealer_{i}',
                zone_type='dealership',
                name=f'Auto Dealership #{i+1}',
                lat=lat + offset_lat,
                lon=lon + offset_lon,
                estimated_vehicles=300,
                typical_occupancy=0.90,
                peak_occupancy=0.95,
                operating_hours='9AM-8PM',
                priority=1
            ))

        # Generate malls
        for i in range(num_malls):
            offset_lat = (i * 0.03) - 0.02
            offset_lon = (i * 0.02) + 0.01
            zones.append(VehicleZone(
                zone_id=f'mall_{i}',
                zone_type='mall',
                name=f'Shopping Center #{i+1}',
                lat=lat + offset_lat,
                lon=lon + offset_lon,
                estimated_vehicles=1200,
                typical_occupancy=0.65,
                peak_occupancy=0.90,
                operating_hours='10AM-9PM',
                priority=2
            ))

        # Generate office parks
        for i in range(num_offices):
            offset_lat = ((i * 7) % 5 - 2) * 0.015
            offset_lon = ((i * 3) % 5 - 2) * 0.015
            zones.append(VehicleZone(
                zone_id=f'office_{i}',
                zone_type='office_complex',
                name=f'Office Complex #{i+1}',
                lat=lat + offset_lat,
                lon=lon + offset_lon,
                estimated_vehicles=350,
                typical_occupancy=0.80,
                peak_occupancy=0.95,
                operating_hours='7AM-7PM',
                priority=3
            ))

        return zones

    def _estimate_zone_vehicles(
        self,
        zone: VehicleZone,
        time_of_day: str
    ) -> int:
        """Estimate outdoor vehicles for a zone at given time."""
        zone_config = self.ZONE_ESTIMATES.get(zone.zone_type, {
            'outdoor_pct': 0.5, 'damage_vulnerability': 0.5
        })

        # Base vehicles at typical occupancy
        base_vehicles = zone.estimated_vehicles * zone.typical_occupancy

        # Adjust for outdoor percentage
        outdoor_pct = zone_config.get('outdoor_pct', 0.5)

        # Adjust for time of day
        time_mult = self.TIME_MULTIPLIERS.get(time_of_day, 0.5)

        return int(base_vehicles * outdoor_pct * time_mult)

    def _get_residential_density(self, lat: float, lon: float) -> int:
        """Estimate residential vehicle density for location."""
        # Simple heuristic based on typical US/CA/MX patterns
        # In production, would use census data

        # Higher density near major cities
        major_cities = [
            (35.47, -97.52, 1500),   # OKC
            (32.78, -96.80, 2000),   # Dallas
            (29.76, -95.37, 2000),   # Houston
            (39.74, -105.0, 1800),   # Denver
            (51.05, -114.07, 1500),  # Calgary
            (19.43, -99.13, 2500),   # Mexico City
        ]

        max_density = 800  # Default suburban

        for city_lat, city_lon, density in major_cities:
            dist = ((lat - city_lat)**2 + (lon - city_lon)**2)**0.5
            if dist < 0.5:  # Within ~50km
                max_density = max(max_density, density)

        return max_density

    def find_dealerships(
        self,
        lat: float,
        lon: float,
        radius_km: float = 25
    ) -> List[VehicleZone]:
        """
        Find auto dealerships in an area.

        Args:
            lat: Center latitude
            lon: Center longitude
            radius_km: Search radius

        Returns:
            List of dealership zones
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            lat_delta = radius_km / 111.0
            lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

            cursor.execute("""
                SELECT id, name, brand, latitude, longitude,
                       estimated_inventory, city, state_province
                FROM dealerships
                WHERE latitude BETWEEN ? AND ?
                  AND longitude BETWEEN ? AND ?
            """, (
                lat - lat_delta, lat + lat_delta,
                lon - lon_delta, lon + lon_delta
            ))

            dealerships = []
            for row in cursor.fetchall():
                dealerships.append(VehicleZone(
                    zone_id=str(row['id']),
                    zone_type='dealership',
                    name=f"{row['name']} ({row['brand']})" if row['brand'] else row['name'],
                    lat=row['latitude'],
                    lon=row['longitude'],
                    estimated_vehicles=row['estimated_inventory'] or 200,
                    typical_occupancy=0.90,
                    peak_occupancy=0.95,
                    operating_hours='9AM-8PM',
                    priority=1
                ))

            conn.close()
            return dealerships

        except Exception as e:
            logger.warning(f"Error finding dealerships: {e}")
            return []

    def estimate_damage_potential(
        self,
        density: DensityEstimate,
        hail_size_inches: float
    ) -> Dict:
        """
        Estimate damage potential for a density estimate.

        Args:
            density: DensityEstimate for area
            hail_size_inches: Hail size

        Returns:
            Dict with damage estimates
        """
        # Damage probability increases with hail size
        if hail_size_inches < 1.0:
            damage_rate = 0.15
        elif hail_size_inches < 1.5:
            damage_rate = 0.40
        elif hail_size_inches < 2.0:
            damage_rate = 0.70
        else:
            damage_rate = 0.90

        outdoor_damaged = int(density.outdoor_vehicles * damage_rate)
        dealership_damaged = int(density.dealership_vehicles * damage_rate * 0.95)  # Nearly all outdoor

        return {
            'total_outdoor_vehicles': density.outdoor_vehicles,
            'estimated_damaged': outdoor_damaged,
            'dealership_vehicles_at_risk': density.dealership_vehicles,
            'dealership_damaged': dealership_damaged,
            'damage_rate': damage_rate,
            'hail_size_inches': hail_size_inches,
            'high_value_zones': [
                z for z in density.zones
                if z.zone_type == 'dealership' and z.estimated_vehicles > 200
            ]
        }


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("VEHICLE DENSITY ESTIMATOR TEST")
    print("=" * 60)

    estimator = VehicleDensityEstimator()

    # Test for Oklahoma City
    print("\nEstimating vehicle density for Oklahoma City area...")
    density = estimator.estimate_density(35.47, -97.52, radius_km=15)

    print(f"\nLocation: ({density.lat:.2f}, {density.lon:.2f})")
    print(f"Radius: {density.radius_km} km")
    print(f"\nVehicle Estimates:")
    print(f"  Total Vehicles: {density.total_vehicles:,}")
    print(f"  Outdoor Vehicles: {density.outdoor_vehicles:,}")
    print(f"  Dealership Vehicles: {density.dealership_vehicles:,}")
    print(f"  Residential Vehicles: {density.residential_vehicles:,}")
    print(f"  Commercial Vehicles: {density.commercial_vehicles:,}")

    print(f"\nVehicle Zones Found: {len(density.zones)}")
    for zone in density.zones[:5]:
        print(f"  - {zone.name} ({zone.zone_type}): ~{zone.estimated_vehicles} vehicles")

    # Test damage potential
    print("\n" + "=" * 60)
    print("DAMAGE POTENTIAL ESTIMATE (2\" hail)")
    print("=" * 60)

    damage = estimator.estimate_damage_potential(density, 2.0)
    print(f"\nDamage Rate: {damage['damage_rate']*100:.0f}%")
    print(f"Estimated Damaged Vehicles: {damage['estimated_damaged']:,}")
    print(f"Dealership Vehicles at Risk: {damage['dealership_vehicles_at_risk']:,}")
    print(f"Dealership Vehicles Damaged: {damage['dealership_damaged']:,}")

    if damage['high_value_zones']:
        print(f"\nHigh-Value Targets: {len(damage['high_value_zones'])}")
        for zone in damage['high_value_zones'][:3]:
            print(f"  - {zone.name}: {zone.estimated_vehicles} vehicles")

    print("\nVehicle density estimator ready!")
