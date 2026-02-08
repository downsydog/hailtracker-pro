"""
Sales Territory Manager
Manage sales territories, swath assignments, and field sales grid operations

FEATURES:
- Hail swath mapping
- Sales grid generation
- Territory assignment
- Coverage tracking
- Field lead management
- Lead conversion
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import math


class SalesTerritoryManager:
    """
    Manage sales territories and swath assignments

    AI-powered territory optimization for door-to-door hail damage canvassing
    """

    def __init__(self, db):
        self.db = db
        self._ensure_territory_tables()

    def _ensure_territory_tables(self):
        """Ensure sales territory tables exist"""
        # Hail swaths table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS hail_swaths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                swath_name TEXT NOT NULL,
                center_lat REAL NOT NULL,
                center_lon REAL NOT NULL,
                radius_miles REAL NOT NULL,
                area_sq_miles REAL,
                hail_date DATE NOT NULL,
                severity TEXT NOT NULL,
                estimated_homes INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

        # Sales grid cells table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS sales_grid_cells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                swath_id INTEGER NOT NULL,
                cell_number INTEGER NOT NULL,
                center_lat REAL NOT NULL,
                center_lon REAL NOT NULL,
                grid_size_miles REAL NOT NULL,
                estimated_homes INTEGER,
                assigned_to INTEGER,
                assignment_id INTEGER,
                homes_visited INTEGER DEFAULT 0,
                leads_generated INTEGER DEFAULT 0,
                canvassed_at TIMESTAMP,
                canvass_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'AVAILABLE',
                FOREIGN KEY (swath_id) REFERENCES hail_swaths(id)
            )
        """)

        # Territory assignments table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS territory_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                assigned_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE',
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id)
            )
        """)

        # Field leads table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS field_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesperson_id INTEGER NOT NULL,
                grid_cell_id INTEGER,
                customer_info TEXT NOT NULL,
                vehicle_info TEXT,
                insurance_info TEXT,
                damage_assessment TEXT,
                location_lat REAL,
                location_lon REAL,
                lead_quality TEXT DEFAULT 'WARM',
                photos TEXT,
                notes TEXT,
                customer_id INTEGER,
                job_id INTEGER,
                status_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'NEW',
                FOREIGN KEY (salesperson_id) REFERENCES salespeople(id),
                FOREIGN KEY (grid_cell_id) REFERENCES sales_grid_cells(id)
            )
        """)

        # Salespeople table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS salespeople (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                hire_date DATE,
                commission_rate REAL DEFAULT 0.15,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'ACTIVE'
            )
        """)

    # ========================================================================
    # SWATH MAPPING
    # ========================================================================

    def create_hail_swath(
        self,
        swath_name: str,
        center_lat: float,
        center_lon: float,
        radius_miles: float,
        hail_date: date,
        severity: str,
        estimated_homes: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create hail swath from weather data

        Args:
            swath_name: Swath identifier (e.g., "Dallas Nov 15 2024")
            center_lat: Center latitude
            center_lon: Center longitude
            radius_miles: Swath radius in miles
            hail_date: Date of hail event
            severity: LOW, MEDIUM, HIGH, SEVERE
            estimated_homes: Estimated affected homes
            notes: Swath notes

        Returns:
            Swath ID
        """
        # Calculate swath area
        area_sq_miles = math.pi * (radius_miles ** 2)

        result = self.db.execute("""
            INSERT INTO hail_swaths (
                swath_name, center_lat, center_lon,
                radius_miles, area_sq_miles, hail_date, severity,
                estimated_homes, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            swath_name,
            center_lat,
            center_lon,
            radius_miles,
            area_sq_miles,
            hail_date.isoformat() if isinstance(hail_date, date) else hail_date,
            severity,
            estimated_homes,
            notes,
            'ACTIVE'
        ])

        return result[0]['id']

    def get_hail_swath(self, swath_id: int) -> Optional[Dict]:
        """Get hail swath by ID"""
        results = self.db.execute(
            "SELECT * FROM hail_swaths WHERE id = ?",
            [swath_id]
        )
        return results[0] if results else None

    def get_active_swaths(self) -> List[Dict]:
        """Get all active hail swaths"""
        return self.db.execute(
            "SELECT * FROM hail_swaths WHERE status = 'ACTIVE' ORDER BY hail_date DESC"
        )

    def update_swath_status(self, swath_id: int, status: str) -> bool:
        """Update swath status (ACTIVE, COMPLETED, ARCHIVED)"""
        self.db.execute(
            "UPDATE hail_swaths SET status = ? WHERE id = ?",
            [status, swath_id]
        )
        return True

    # ========================================================================
    # SALES GRID GENERATION
    # ========================================================================

    def generate_sales_grid(
        self,
        swath_id: int,
        grid_size_miles: float = 0.5
    ) -> int:
        """
        Generate sales grid for swath

        Divides swath into manageable territories for door-to-door canvassing

        Args:
            swath_id: Swath ID
            grid_size_miles: Size of each grid cell (miles)

        Returns:
            Number of grid cells created
        """
        swath = self.get_hail_swath(swath_id)
        if not swath:
            return 0

        center_lat = swath['center_lat']
        center_lon = swath['center_lon']
        radius = swath['radius_miles']
        total_homes = swath['estimated_homes'] or 0

        # Approximate degrees per mile (varies by latitude)
        lat_per_mile = 1 / 69.0
        lon_per_mile = 1 / (69.0 * math.cos(math.radians(center_lat)))

        # Grid parameters
        grid_rows = int((radius * 2) / grid_size_miles) + 1
        grid_cols = int((radius * 2) / grid_size_miles) + 1

        start_lat = center_lat - (radius * lat_per_mile)
        start_lon = center_lon - (radius * lon_per_mile)

        cells_created = 0
        cell_number = 1

        # Estimate homes per cell
        total_cells_estimate = math.pi * (radius / grid_size_miles) ** 2
        homes_per_cell = int(total_homes / total_cells_estimate) if total_cells_estimate > 0 else 0

        for row in range(grid_rows):
            for col in range(grid_cols):
                cell_center_lat = start_lat + (row * grid_size_miles * lat_per_mile)
                cell_center_lon = start_lon + (col * grid_size_miles * lon_per_mile)

                # Check if cell is within swath radius
                distance = self._calculate_distance(
                    center_lat, center_lon,
                    cell_center_lat, cell_center_lon
                )

                if distance <= radius:
                    self.db.execute("""
                        INSERT INTO sales_grid_cells (
                            swath_id, cell_number,
                            center_lat, center_lon,
                            grid_size_miles, estimated_homes,
                            status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, [
                        swath_id,
                        cell_number,
                        cell_center_lat,
                        cell_center_lon,
                        grid_size_miles,
                        homes_per_cell,
                        'AVAILABLE'
                    ])

                    cells_created += 1
                    cell_number += 1

        return cells_created

    def _calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using Haversine formula

        Returns distance in miles
        """
        R = 3959.0  # Earth radius in miles

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def get_grid_cells(self, swath_id: int) -> List[Dict]:
        """Get all grid cells for a swath"""
        return self.db.execute("""
            SELECT * FROM sales_grid_cells
            WHERE swath_id = ?
            ORDER BY cell_number
        """, [swath_id])

    def get_grid_cell(self, cell_id: int) -> Optional[Dict]:
        """Get a specific grid cell"""
        results = self.db.execute(
            "SELECT * FROM sales_grid_cells WHERE id = ?",
            [cell_id]
        )
        return results[0] if results else None

    # ========================================================================
    # TERRITORY ASSIGNMENT
    # ========================================================================

    def assign_territory(
        self,
        salesperson_id: int,
        grid_cell_ids: List[int],
        assigned_date: Optional[date] = None
    ) -> int:
        """
        Assign territory (grid cells) to salesperson

        Args:
            salesperson_id: Salesperson ID
            grid_cell_ids: List of grid cell IDs to assign
            assigned_date: Assignment date

        Returns:
            Territory assignment ID
        """
        if not assigned_date:
            assigned_date = date.today()

        # Create territory assignment
        result = self.db.execute("""
            INSERT INTO territory_assignments (
                salesperson_id, assigned_date, status
            ) VALUES (?, ?, ?)
        """, [
            salesperson_id,
            assigned_date.isoformat() if isinstance(assigned_date, date) else assigned_date,
            'ACTIVE'
        ])

        assignment_id = result[0]['id']

        # Assign grid cells
        for cell_id in grid_cell_ids:
            self.db.execute("""
                UPDATE sales_grid_cells
                SET assigned_to = ?,
                    assignment_id = ?,
                    status = 'ASSIGNED'
                WHERE id = ?
            """, [salesperson_id, assignment_id, cell_id])

        return assignment_id

    def get_available_cells(self, swath_id: int) -> List[Dict]:
        """Get available (unassigned) grid cells"""
        return self.db.execute("""
            SELECT * FROM sales_grid_cells
            WHERE swath_id = ?
              AND status = 'AVAILABLE'
            ORDER BY cell_number
        """, [swath_id])

    def get_salesperson_territory(
        self,
        salesperson_id: int,
        active_only: bool = True
    ) -> List[Dict]:
        """Get salesperson's assigned territories"""
        query = """
            SELECT sgc.*, hs.swath_name, hs.severity
            FROM sales_grid_cells sgc
            JOIN hail_swaths hs ON hs.id = sgc.swath_id
            WHERE sgc.assigned_to = ?
        """

        if active_only:
            query += " AND sgc.status = 'ASSIGNED'"

        query += " ORDER BY sgc.swath_id, sgc.cell_number"

        return self.db.execute(query, [salesperson_id])

    def unassign_territory(self, assignment_id: int) -> bool:
        """Unassign territory and free up grid cells"""
        # Reset grid cells
        self.db.execute("""
            UPDATE sales_grid_cells
            SET assigned_to = NULL,
                assignment_id = NULL,
                status = 'AVAILABLE'
            WHERE assignment_id = ?
        """, [assignment_id])

        # Update assignment status
        self.db.execute("""
            UPDATE territory_assignments
            SET status = 'CANCELLED'
            WHERE id = ?
        """, [assignment_id])

        return True

    # ========================================================================
    # COVERAGE TRACKING
    # ========================================================================

    def mark_cell_canvassed(
        self,
        cell_id: int,
        salesperson_id: int,
        homes_visited: int,
        leads_generated: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Mark grid cell as canvassed

        Args:
            cell_id: Grid cell ID
            salesperson_id: Who canvassed
            homes_visited: Number of homes visited
            leads_generated: Number of leads generated
            notes: Canvassing notes
        """
        self.db.execute("""
            UPDATE sales_grid_cells
            SET status = 'CANVASSED',
                canvassed_at = ?,
                homes_visited = ?,
                leads_generated = ?,
                canvass_notes = ?
            WHERE id = ?
        """, [
            datetime.now().isoformat(),
            homes_visited,
            leads_generated,
            notes,
            cell_id
        ])

        return True

    def get_coverage_stats(self, swath_id: int) -> Dict:
        """Get coverage statistics for swath"""
        stats = self.db.execute("""
            SELECT
                COUNT(*) as total_cells,
                SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'ASSIGNED' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN status = 'CANVASSED' THEN 1 ELSE 0 END) as canvassed,
                SUM(COALESCE(homes_visited, 0)) as total_homes_visited,
                SUM(COALESCE(leads_generated, 0)) as total_leads
            FROM sales_grid_cells
            WHERE swath_id = ?
        """, [swath_id])

        result = stats[0] if stats else {}

        total = result.get('total_cells', 0) or 0
        canvassed = result.get('canvassed', 0) or 0

        return {
            'total_cells': total,
            'available': result.get('available', 0) or 0,
            'assigned': result.get('assigned', 0) or 0,
            'canvassed': canvassed,
            'coverage_percent': round((canvassed / total * 100), 1) if total > 0 else 0,
            'homes_visited': result.get('total_homes_visited', 0) or 0,
            'leads_generated': result.get('total_leads', 0) or 0
        }

    def get_salesperson_coverage(self, salesperson_id: int) -> Dict:
        """Get coverage stats for a salesperson's assigned territories"""
        stats = self.db.execute("""
            SELECT
                COUNT(*) as assigned_cells,
                SUM(CASE WHEN status = 'CANVASSED' THEN 1 ELSE 0 END) as completed_cells,
                SUM(COALESCE(homes_visited, 0)) as homes_visited,
                SUM(COALESCE(leads_generated, 0)) as leads_generated
            FROM sales_grid_cells
            WHERE assigned_to = ?
        """, [salesperson_id])

        result = stats[0] if stats else {}
        assigned = result.get('assigned_cells', 0) or 0
        completed = result.get('completed_cells', 0) or 0

        return {
            'assigned_cells': assigned,
            'completed_cells': completed,
            'remaining_cells': assigned - completed,
            'completion_percent': round((completed / assigned * 100), 1) if assigned > 0 else 0,
            'homes_visited': result.get('homes_visited', 0) or 0,
            'leads_generated': result.get('leads_generated', 0) or 0
        }

    # ========================================================================
    # FIELD LEAD MANAGEMENT
    # ========================================================================

    def create_field_lead(
        self,
        salesperson_id: int,
        customer_info: Dict,
        location_lat: float,
        location_lon: float,
        grid_cell_id: Optional[int] = None,
        vehicle_info: Optional[Dict] = None,
        insurance_info: Optional[Dict] = None,
        damage_assessment: Optional[Dict] = None,
        lead_quality: str = 'WARM',
        photos: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Create lead from field canvassing

        Args:
            salesperson_id: Salesperson who generated lead
            customer_info: Customer details (name, phone, email, address)
            location_lat: Lead location latitude
            location_lon: Lead location longitude
            grid_cell_id: Grid cell where lead was found
            vehicle_info: Vehicle details (year, make, model, vin)
            insurance_info: Insurance details (company, policy, claim filed)
            damage_assessment: Damage details (severity, panels, estimate)
            lead_quality: HOT, WARM, COLD
            photos: List of photo URLs
            notes: Lead notes

        Returns:
            Lead ID
        """
        result = self.db.execute("""
            INSERT INTO field_leads (
                salesperson_id, grid_cell_id,
                customer_info, vehicle_info, insurance_info,
                damage_assessment, location_lat, location_lon,
                lead_quality, photos, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            salesperson_id,
            grid_cell_id,
            json.dumps(customer_info),
            json.dumps(vehicle_info) if vehicle_info else None,
            json.dumps(insurance_info) if insurance_info else None,
            json.dumps(damage_assessment) if damage_assessment else None,
            location_lat,
            location_lon,
            lead_quality,
            json.dumps(photos) if photos else None,
            notes,
            'NEW'
        ])

        return result[0]['id']

    def get_field_lead(self, lead_id: int) -> Optional[Dict]:
        """Get field lead by ID with parsed JSON"""
        results = self.db.execute(
            "SELECT * FROM field_leads WHERE id = ?",
            [lead_id]
        )

        if not results:
            return None

        lead = results[0]
        return self._parse_lead(lead)

    def _parse_lead(self, lead: Dict) -> Dict:
        """Parse JSON fields in lead"""
        for field in ['customer_info', 'vehicle_info', 'insurance_info', 'damage_assessment', 'photos']:
            if lead.get(field):
                try:
                    lead[field] = json.loads(lead[field])
                except:
                    pass
        return lead

    def get_leads_by_salesperson(
        self,
        salesperson_id: int,
        status: Optional[str] = None
    ) -> List[Dict]:
        """Get leads by salesperson"""
        query = "SELECT * FROM field_leads WHERE salesperson_id = ?"
        params = [salesperson_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        leads = self.db.execute(query, params)
        return [self._parse_lead(lead) for lead in leads]

    def get_leads_by_status(self, status: str) -> List[Dict]:
        """Get all leads by status"""
        leads = self.db.execute(
            "SELECT * FROM field_leads WHERE status = ? ORDER BY created_at DESC",
            [status]
        )
        return [self._parse_lead(lead) for lead in leads]

    def update_lead_status(
        self,
        lead_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update lead status

        Statuses: NEW, CONTACTED, SCHEDULED, CONVERTED, LOST
        """
        self.db.execute("""
            UPDATE field_leads
            SET status = ?,
                status_notes = ?,
                updated_at = ?
            WHERE id = ?
        """, [
            new_status,
            notes,
            datetime.now().isoformat(),
            lead_id
        ])

        return True

    def convert_lead_to_customer(self, lead_id: int) -> Tuple[int, int]:
        """
        Convert field lead to customer and job

        Returns:
            (customer_id, job_id)
        """
        lead = self.get_field_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        customer_info = lead['customer_info']
        vehicle_info = lead.get('vehicle_info') or {}
        damage_assessment = lead.get('damage_assessment') or {}

        # Create customer
        # Parse address if provided (format: "123 Main St, Dallas, TX 75201")
        address = customer_info.get('address', '')
        street_address = address
        city = None
        state = None
        zip_code = None

        if ',' in address:
            parts = [p.strip() for p in address.split(',')]
            if len(parts) >= 1:
                street_address = parts[0]
            if len(parts) >= 2:
                city = parts[1]
            if len(parts) >= 3:
                # Parse state and zip from "TX 75201"
                state_zip = parts[2].strip().split()
                if len(state_zip) >= 1:
                    state = state_zip[0]
                if len(state_zip) >= 2:
                    zip_code = state_zip[1]

        customer_result = self.db.execute("""
            INSERT INTO customers (
                first_name, last_name, phone, email,
                street_address, city, state, zip_code, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            customer_info.get('first_name', ''),
            customer_info.get('last_name', ''),
            customer_info.get('phone'),
            customer_info.get('email'),
            street_address,
            city,
            state,
            zip_code,
            'FIELD_SALES'
        ])

        customer_id = customer_result[0]['id']

        # Create vehicle if info provided
        vehicle_id = None
        if vehicle_info:
            vehicle_result = self.db.execute("""
                INSERT INTO vehicles (
                    customer_id, year, make, model, vin, color
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, [
                customer_id,
                vehicle_info.get('year'),
                vehicle_info.get('make'),
                vehicle_info.get('model'),
                vehicle_info.get('vin'),
                vehicle_info.get('color')
            ])
            vehicle_id = vehicle_result[0]['id']

        # Create job
        job_number = f"JOB-{datetime.now().strftime('%Y%m%d')}-{lead_id:04d}"
        damage_desc = f"Hail damage - {damage_assessment.get('estimated_dents', 'Unknown')} dents"

        job_result = self.db.execute("""
            INSERT INTO jobs (
                job_number, customer_id, vehicle_id,
                status, job_type, damage_type
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, [
            job_number,
            customer_id,
            vehicle_id,
            'NEW',
            'HAIL',
            'HAIL'
        ])

        job_id = job_result[0]['id']

        # Update lead status
        self.db.execute("""
            UPDATE field_leads
            SET status = 'CONVERTED',
                customer_id = ?,
                job_id = ?,
                updated_at = ?
            WHERE id = ?
        """, [
            customer_id,
            job_id,
            datetime.now().isoformat(),
            lead_id
        ])

        return customer_id, job_id

    # ========================================================================
    # SALESPERSON MANAGEMENT
    # ========================================================================

    def create_salesperson(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        hire_date: Optional[date] = None,
        commission_rate: float = 0.15,
        notes: Optional[str] = None
    ) -> int:
        """Create salesperson record"""
        if not hire_date:
            hire_date = date.today()

        result = self.db.execute("""
            INSERT INTO salespeople (
                first_name, last_name, email, phone,
                hire_date, commission_rate, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            first_name,
            last_name,
            email,
            phone,
            hire_date.isoformat() if isinstance(hire_date, date) else hire_date,
            commission_rate,
            notes,
            'ACTIVE'
        ])

        return result[0]['id']

    def get_salesperson(self, salesperson_id: int) -> Optional[Dict]:
        """Get salesperson by ID"""
        results = self.db.execute(
            "SELECT * FROM salespeople WHERE id = ?",
            [salesperson_id]
        )
        return results[0] if results else None

    def get_active_salespeople(self) -> List[Dict]:
        """Get all active salespeople"""
        return self.db.execute(
            "SELECT * FROM salespeople WHERE status = 'ACTIVE' ORDER BY last_name, first_name"
        )

    def update_salesperson_status(self, salesperson_id: int, status: str) -> bool:
        """Update salesperson status (ACTIVE, INACTIVE)"""
        self.db.execute(
            "UPDATE salespeople SET status = ? WHERE id = ?",
            [status, salesperson_id]
        )
        return True

    # ========================================================================
    # ANALYTICS
    # ========================================================================

    def get_swath_summary(self, swath_id: int) -> Dict:
        """Get comprehensive summary for a swath"""
        swath = self.get_hail_swath(swath_id)
        if not swath:
            return {}

        coverage = self.get_coverage_stats(swath_id)

        # Get lead stats
        lead_stats = self.db.execute("""
            SELECT
                COUNT(*) as total_leads,
                SUM(CASE WHEN fl.status = 'CONVERTED' THEN 1 ELSE 0 END) as converted,
                SUM(CASE WHEN fl.status = 'NEW' THEN 1 ELSE 0 END) as new_leads,
                SUM(CASE WHEN fl.lead_quality = 'HOT' THEN 1 ELSE 0 END) as hot_leads
            FROM field_leads fl
            JOIN sales_grid_cells sgc ON fl.grid_cell_id = sgc.id
            WHERE sgc.swath_id = ?
        """, [swath_id])

        leads = lead_stats[0] if lead_stats else {}

        # Get assigned salespeople
        salespeople = self.db.execute("""
            SELECT DISTINCT s.*
            FROM salespeople s
            JOIN sales_grid_cells sgc ON sgc.assigned_to = s.id
            WHERE sgc.swath_id = ?
        """, [swath_id])

        return {
            'swath': swath,
            'coverage': coverage,
            'leads': {
                'total': leads.get('total_leads', 0) or 0,
                'converted': leads.get('converted', 0) or 0,
                'new': leads.get('new_leads', 0) or 0,
                'hot': leads.get('hot_leads', 0) or 0,
                'conversion_rate': round((leads.get('converted', 0) or 0) / (leads.get('total_leads', 1) or 1) * 100, 1)
            },
            'salespeople': salespeople,
            'salesperson_count': len(salespeople)
        }
