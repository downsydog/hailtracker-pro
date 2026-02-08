"""
Vehicle Manager
Handles vehicle CRUD and related operations for PDR CRM

Features:
- Vehicle CRUD operations
- VIN decoding support
- Vehicle history tracking
- Job history per vehicle
"""

from datetime import datetime, date
from typing import Optional, Dict, List, Any


class VehicleManager:
    """
    Vehicle management for PDR CRM

    Tracks vehicles linked to customers with full history.
    """

    def __init__(self, db):
        """Initialize with database connection"""
        self.db = db

    # ========================================================================
    # VEHICLE CRUD
    # ========================================================================

    def create_vehicle(self, data: Dict) -> int:
        """
        Create new vehicle

        Required: customer_id
        Optional: vin, year, make, model, color, license_plate, insurance info

        Returns: vehicle ID
        """
        if 'customer_id' not in data:
            raise ValueError("customer_id is required")

        if 'status' not in data:
            data['status'] = 'ACTIVE'

        return self.db.insert('vehicles', data)

    def get_vehicle(self, vehicle_id: int) -> Optional[Dict]:
        """Get vehicle by ID"""
        return self.db.get_by_id('vehicles', vehicle_id)

    def get_vehicle_by_vin(self, vin: str) -> Optional[Dict]:
        """Find vehicle by VIN"""
        results = self.db.execute(
            "SELECT * FROM vehicles WHERE vin = ? AND deleted_at IS NULL",
            (vin.upper(),)
        )
        return results[0] if results else None

    def update_vehicle(self, vehicle_id: int, data: Dict) -> bool:
        """Update vehicle information"""
        return self.db.update('vehicles', vehicle_id, data)

    def delete_vehicle(self, vehicle_id: int, hard: bool = False) -> bool:
        """Delete vehicle (soft delete by default)"""
        return self.db.delete('vehicles', vehicle_id, soft=not hard)

    def get_customer_vehicles(self, customer_id: int) -> List[Dict]:
        """Get all vehicles for a customer"""
        return self.db.execute("""
            SELECT * FROM vehicles
            WHERE customer_id = ? AND deleted_at IS NULL
            ORDER BY year DESC, make, model
        """, (customer_id,))

    def search_vehicles(
        self,
        query: str = None,
        make: str = None,
        model: str = None,
        year: int = None,
        customer_id: int = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search vehicles with filters

        Args:
            query: Search VIN, make, model, or license plate
            make: Filter by make (Toyota, Honda, etc.)
            model: Filter by model
            year: Filter by year
            customer_id: Filter by customer
            limit: Max results
        """
        conditions = []
        params = []

        if query:
            conditions.append("""
                (vin LIKE ? OR make LIKE ? OR model LIKE ? OR license_plate LIKE ?)
            """)
            search = f"%{query}%"
            params.extend([search] * 4)

        if make:
            conditions.append("make = ?")
            params.append(make)

        if model:
            conditions.append("model = ?")
            params.append(model)

        if year:
            conditions.append("year = ?")
            params.append(year)

        if customer_id:
            conditions.append("customer_id = ?")
            params.append(customer_id)

        where_clause = ' AND '.join(conditions) if conditions else '1=1'

        return self.db.execute(f"""
            SELECT v.*, c.first_name, c.last_name, c.phone
            FROM vehicles v
            JOIN customers c ON v.customer_id = c.id
            WHERE {where_clause} AND v.deleted_at IS NULL
            ORDER BY v.year DESC, v.make, v.model
            LIMIT ?
        """, tuple(params) + (limit,))

    # ========================================================================
    # VEHICLE HISTORY
    # ========================================================================

    def get_vehicle_jobs(self, vehicle_id: int) -> List[Dict]:
        """Get all jobs for a vehicle"""
        return self.db.execute("""
            SELECT j.*, t.first_name as tech_first_name, t.last_name as tech_last_name
            FROM jobs j
            LEFT JOIN technicians t ON j.assigned_tech_id = t.id
            WHERE j.vehicle_id = ? AND j.deleted_at IS NULL
            ORDER BY j.created_at DESC
        """, (vehicle_id,))

    def get_vehicle_with_owner(self, vehicle_id: int) -> Optional[Dict]:
        """Get vehicle with owner information"""
        results = self.db.execute("""
            SELECT v.*,
                   c.first_name, c.last_name, c.email, c.phone,
                   c.company_name
            FROM vehicles v
            JOIN customers c ON v.customer_id = c.id
            WHERE v.id = ? AND v.deleted_at IS NULL
        """, (vehicle_id,))
        return results[0] if results else None

    def get_vehicle_summary(self, vehicle_id: int) -> Dict:
        """Get summary of vehicle with job history stats"""
        vehicle = self.get_vehicle_with_owner(vehicle_id)
        if not vehicle:
            return {}

        # Get job stats
        job_stats = self.db.execute("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'COMPLETED' OR status = 'PAID' THEN 1 ELSE 0 END) as completed_jobs,
                SUM(total_actual) as total_spent,
                MAX(created_at) as last_job_date
            FROM jobs
            WHERE vehicle_id = ? AND deleted_at IS NULL
        """, (vehicle_id,))

        vehicle['job_stats'] = job_stats[0] if job_stats else {}
        return vehicle

    # ========================================================================
    # INSURANCE INFO
    # ========================================================================

    def update_insurance_info(
        self,
        vehicle_id: int,
        insurance_company: str,
        policy_number: str = None,
        claim_number: str = None
    ) -> bool:
        """Update vehicle insurance information"""
        data = {'insurance_company': insurance_company}

        if policy_number:
            data['policy_number'] = policy_number
        if claim_number:
            data['claim_number'] = claim_number

        return self.update_vehicle(vehicle_id, data)

    # ========================================================================
    # BULK OPERATIONS
    # ========================================================================

    def get_vehicles_by_make(self, make: str) -> List[Dict]:
        """Get all vehicles of a specific make"""
        return self.db.execute("""
            SELECT v.*, c.first_name, c.last_name
            FROM vehicles v
            JOIN customers c ON v.customer_id = c.id
            WHERE v.make = ? AND v.deleted_at IS NULL
            ORDER BY v.year DESC
        """, (make,))

    def get_vehicles_needing_work(self) -> List[Dict]:
        """Get vehicles with active jobs not completed"""
        return self.db.execute("""
            SELECT DISTINCT v.*, c.first_name, c.last_name, j.status as job_status
            FROM vehicles v
            JOIN customers c ON v.customer_id = c.id
            JOIN jobs j ON j.vehicle_id = v.id
            WHERE j.status NOT IN ('COMPLETED', 'PAID', 'INVOICED')
              AND j.deleted_at IS NULL
              AND v.deleted_at IS NULL
            ORDER BY j.priority DESC, j.created_at ASC
        """)

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_vehicle_stats(self) -> Dict:
        """Get overall vehicle statistics"""
        result = self.db.execute("""
            SELECT
                COUNT(*) as total_vehicles,
                COUNT(DISTINCT make) as unique_makes,
                COUNT(DISTINCT customer_id) as unique_owners
            FROM vehicles
            WHERE deleted_at IS NULL
        """)
        return result[0] if result else {}

    def get_popular_makes(self, limit: int = 10) -> List[Dict]:
        """Get most common vehicle makes"""
        return self.db.execute("""
            SELECT make, COUNT(*) as count
            FROM vehicles
            WHERE deleted_at IS NULL AND make IS NOT NULL
            GROUP BY make
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))

    def get_popular_models(self, make: str = None, limit: int = 10) -> List[Dict]:
        """Get most common vehicle models, optionally filtered by make"""
        if make:
            return self.db.execute("""
                SELECT make, model, COUNT(*) as count
                FROM vehicles
                WHERE deleted_at IS NULL AND make = ?
                GROUP BY make, model
                ORDER BY count DESC
                LIMIT ?
            """, (make, limit))
        else:
            return self.db.execute("""
                SELECT make, model, COUNT(*) as count
                FROM vehicles
                WHERE deleted_at IS NULL AND make IS NOT NULL AND model IS NOT NULL
                GROUP BY make, model
                ORDER BY count DESC
                LIMIT ?
            """, (limit,))

    # ========================================================================
    # VIN UTILITIES
    # ========================================================================

    def validate_vin(self, vin: str) -> bool:
        """
        Basic VIN validation (17 characters, no I, O, Q)

        For full VIN decoding, integrate with NHTSA API
        """
        if not vin or len(vin) != 17:
            return False

        # VIN cannot contain I, O, or Q
        invalid_chars = set('IOQ')
        if any(c.upper() in invalid_chars for c in vin):
            return False

        # Must be alphanumeric
        if not vin.isalnum():
            return False

        return True

    def get_vin_year(self, vin: str) -> Optional[int]:
        """
        Extract year from VIN (10th character)

        Returns model year or None if invalid
        """
        if not self.validate_vin(vin):
            return None

        year_code = vin[9].upper()

        # Year encoding (simplified - covers 1980-2030)
        year_map = {
            'A': 2010, 'B': 2011, 'C': 2012, 'D': 2013, 'E': 2014,
            'F': 2015, 'G': 2016, 'H': 2017, 'J': 2018, 'K': 2019,
            'L': 2020, 'M': 2021, 'N': 2022, 'P': 2023, 'R': 2024,
            'S': 2025, 'T': 2026, 'V': 2027, 'W': 2028, 'X': 2029,
            'Y': 2030,
            '1': 2001, '2': 2002, '3': 2003, '4': 2004, '5': 2005,
            '6': 2006, '7': 2007, '8': 2008, '9': 2009
        }

        return year_map.get(year_code)

    def find_duplicate_vins(self) -> List[Dict]:
        """Find duplicate VINs in the system"""
        return self.db.execute("""
            SELECT vin, COUNT(*) as count
            FROM vehicles
            WHERE deleted_at IS NULL AND vin IS NOT NULL
            GROUP BY vin
            HAVING count > 1
            ORDER BY count DESC
        """)
