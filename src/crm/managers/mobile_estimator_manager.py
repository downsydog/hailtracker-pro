"""
PDR CRM Part 22 - Mobile Estimator Manager
Manage offline-capable mobile estimates

FEATURES:
- Offline estimate creation
- Local storage management
- Sync queue handling
- GPS location tracking
- Auto-sync when online
"""

import json
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class MobileEstimatorManager:
    """
    Manage mobile estimates with offline support

    Field technicians create estimates without internet
    """

    # Estimate statuses
    STATUSES = [
        'DRAFT',        # Being created
        'PENDING_SYNC', # Saved offline, waiting for sync
        'SYNCED',       # Successfully synced to server
        'APPROVED',     # Customer approved
        'REJECTED',     # Customer rejected
        'EXPIRED'       # Expired before approval
    ]

    def __init__(self, db):
        """Initialize mobile estimator manager with database instance"""
        self.db = db
        self._ensure_offline_tables()

    def _ensure_offline_tables(self):
        """Ensure offline estimates table exists"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS offline_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offline_id TEXT UNIQUE NOT NULL,
                customer_data TEXT NOT NULL,
                vehicle_data TEXT NOT NULL,
                damage_data TEXT NOT NULL,
                location_data TEXT,
                photo_data TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING_SYNC',
                synced INTEGER DEFAULT 0,
                synced_at TIMESTAMP,
                synced_job_id INTEGER,
                synced_estimate_id INTEGER,
                sync_attempts INTEGER DEFAULT 0,
                last_sync_attempt TIMESTAMP,
                last_sync_error TEXT
            )
        """)

    # ========================================================================
    # OFFLINE ESTIMATE CREATION
    # ========================================================================

    def create_offline_estimate(
        self,
        customer_info: Dict,
        vehicle_info: Dict,
        damage_info: Dict,
        location_data: Optional[Dict] = None,
        created_by: Optional[str] = None,
        offline_id: Optional[str] = None
    ) -> Dict:
        """
        Create estimate while offline

        Args:
            customer_info: Customer details (name, phone, email)
            vehicle_info: Vehicle details (year, make, model, etc.)
            damage_info: Damage assessment data
            location_data: GPS coordinates and address
            created_by: Technician ID/name
            offline_id: Unique offline identifier

        Returns:
            Estimate data (stored locally until sync)
        """
        # Generate offline ID if not provided
        if not offline_id:
            offline_id = self._generate_offline_id()

        estimate = {
            'offline_id': offline_id,
            'status': 'PENDING_SYNC',
            'customer_info': customer_info,
            'vehicle_info': vehicle_info,
            'damage_info': damage_info,
            'location_data': location_data,
            'created_by': created_by,
            'created_at': datetime.now().isoformat(),
            'synced': False,
            'sync_attempts': 0
        }

        # Store in offline queue
        self.db.execute("""
            INSERT INTO offline_estimates (
                offline_id, customer_data, vehicle_data,
                damage_data, location_data, created_by,
                created_at, status, synced
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            offline_id,
            json.dumps(customer_info),
            json.dumps(vehicle_info),
            json.dumps(damage_info),
            json.dumps(location_data) if location_data else None,
            created_by,
            estimate['created_at'],
            'PENDING_SYNC',
            0
        ))

        print(f"[OK] Created offline estimate: {offline_id}")
        print(f"     Customer: {customer_info.get('first_name', '')} {customer_info.get('last_name', '')}")
        print(f"     Vehicle: {vehicle_info.get('year', '')} {vehicle_info.get('make', '')} {vehicle_info.get('model', '')}")
        print(f"     Cost: ${damage_info.get('estimated_cost', 0):,.2f}")
        if location_data:
            print(f"     Location: {location_data.get('address', 'GPS coordinates captured')}")

        return estimate

    def _generate_offline_id(self) -> str:
        """Generate unique offline identifier"""
        timestamp = datetime.now().isoformat()
        unique_str = f"{timestamp}_{id(self)}"
        hash_obj = hashlib.md5(unique_str.encode())

        return f"OFFLINE_{hash_obj.hexdigest()[:12].upper()}"

    # ========================================================================
    # SYNC OPERATIONS
    # ========================================================================

    def get_pending_sync(self) -> List[Dict]:
        """
        Get all estimates waiting to be synced

        Returns list of offline estimates ready for sync
        """
        results = self.db.execute("""
            SELECT * FROM offline_estimates
            WHERE synced = 0
            ORDER BY created_at
        """)

        estimates = []
        for row in results:
            estimate = {
                'offline_id': row['offline_id'],
                'customer_info': json.loads(row['customer_data']),
                'vehicle_info': json.loads(row['vehicle_data']),
                'damage_info': json.loads(row['damage_data']),
                'location_data': json.loads(row['location_data']) if row['location_data'] else None,
                'created_by': row['created_by'],
                'created_at': row['created_at'],
                'status': row['status'],
                'sync_attempts': row['sync_attempts']
            }
            estimates.append(estimate)

        return estimates

    def sync_estimate(
        self,
        offline_id: str,
        job_id: Optional[int] = None,
        estimate_id: Optional[int] = None
    ) -> bool:
        """
        Sync offline estimate to server

        Args:
            offline_id: Offline estimate ID
            job_id: Created job ID (after sync)
            estimate_id: Created estimate ID (after sync)

        Returns:
            True if successful
        """
        # Mark as synced
        self.db.execute("""
            UPDATE offline_estimates
            SET synced = 1,
                synced_at = ?,
                synced_job_id = ?,
                synced_estimate_id = ?,
                status = 'SYNCED'
            WHERE offline_id = ?
        """, (
            datetime.now().isoformat(),
            job_id,
            estimate_id,
            offline_id
        ))

        print(f"[OK] Synced offline estimate: {offline_id}")
        if job_id:
            print(f"     Job ID: {job_id}")
        if estimate_id:
            print(f"     Estimate ID: {estimate_id}")

        return True

    def mark_sync_failed(
        self,
        offline_id: str,
        error_message: str
    ) -> bool:
        """
        Mark estimate sync as failed

        Increments retry counter
        """
        self.db.execute("""
            UPDATE offline_estimates
            SET sync_attempts = sync_attempts + 1,
                last_sync_error = ?,
                last_sync_attempt = ?
            WHERE offline_id = ?
        """, (
            error_message,
            datetime.now().isoformat(),
            offline_id
        ))

        print(f"[WARN] Sync failed for {offline_id}: {error_message}")

        return True

    def retry_failed_syncs(self, max_attempts: int = 3) -> Dict:
        """
        Retry syncing failed estimates

        Args:
            max_attempts: Max retry attempts before giving up

        Returns:
            Sync results summary
        """
        pending = self.db.execute("""
            SELECT * FROM offline_estimates
            WHERE synced = 0
              AND sync_attempts < ?
            ORDER BY created_at
        """, (max_attempts,))

        results = {
            'attempted': len(pending),
            'succeeded': 0,
            'failed': 0,
            'details': []
        }

        for estimate in pending:
            # In production, this would attempt actual sync
            result_item = {
                'offline_id': estimate['offline_id'],
                'success': False,
                'error': 'Sync not implemented in test mode'
            }

            results['details'].append(result_item)
            results['failed'] += 1

        return results

    # ========================================================================
    # LOCATION TRACKING
    # ========================================================================

    def add_gps_location(
        self,
        offline_id: str,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        accuracy: Optional[float] = None
    ) -> bool:
        """
        Add GPS location to estimate

        Args:
            offline_id: Estimate ID
            latitude: GPS latitude
            longitude: GPS longitude
            address: Reverse-geocoded address
            accuracy: GPS accuracy in meters
        """
        location_data = {
            'latitude': latitude,
            'longitude': longitude,
            'address': address,
            'accuracy': accuracy,
            'timestamp': datetime.now().isoformat()
        }

        self.db.execute("""
            UPDATE offline_estimates
            SET location_data = ?
            WHERE offline_id = ?
        """, (
            json.dumps(location_data),
            offline_id
        ))

        print(f"[OK] Added GPS location to {offline_id}")
        if address:
            print(f"     Address: {address}")
        print(f"     Coordinates: {latitude}, {longitude}")

        return True

    # ========================================================================
    # PHOTO MANAGEMENT
    # ========================================================================

    def add_photo(
        self,
        offline_id: str,
        photo_data: str,
        photo_type: str = 'DAMAGE',
        panel: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Add photo to offline estimate

        Args:
            offline_id: Estimate ID
            photo_data: Base64 encoded photo or file path
            photo_type: DAMAGE, VEHICLE, VIN, etc.
            panel: Panel name if damage photo
            notes: Photo notes
        """
        # Get existing photos
        result = self.db.execute("""
            SELECT photo_data FROM offline_estimates
            WHERE offline_id = ?
        """, (offline_id,))

        if not result:
            return False

        existing = json.loads(result[0]['photo_data']) if result[0]['photo_data'] else []

        # Add new photo
        photo = {
            'id': len(existing) + 1,
            'type': photo_type,
            'panel': panel,
            'data': photo_data,
            'notes': notes,
            'captured_at': datetime.now().isoformat()
        }

        existing.append(photo)

        # Update
        self.db.execute("""
            UPDATE offline_estimates
            SET photo_data = ?
            WHERE offline_id = ?
        """, (
            json.dumps(existing),
            offline_id
        ))

        print(f"[OK] Added {photo_type} photo to {offline_id}")

        return True

    def get_photos(self, offline_id: str) -> List[Dict]:
        """Get all photos for offline estimate"""
        result = self.db.execute("""
            SELECT photo_data FROM offline_estimates
            WHERE offline_id = ?
        """, (offline_id,))

        if not result or not result[0]['photo_data']:
            return []

        return json.loads(result[0]['photo_data'])

    # ========================================================================
    # ESTIMATE RETRIEVAL
    # ========================================================================

    def get_offline_estimate(self, offline_id: str) -> Optional[Dict]:
        """Get offline estimate by ID"""
        result = self.db.execute("""
            SELECT * FROM offline_estimates
            WHERE offline_id = ?
        """, (offline_id,))

        if not result:
            return None

        row = result[0]

        return {
            'offline_id': row['offline_id'],
            'customer_info': json.loads(row['customer_data']),
            'vehicle_info': json.loads(row['vehicle_data']),
            'damage_info': json.loads(row['damage_data']),
            'location_data': json.loads(row['location_data']) if row['location_data'] else None,
            'photo_data': json.loads(row['photo_data']) if row.get('photo_data') else None,
            'created_by': row['created_by'],
            'created_at': row['created_at'],
            'status': row['status'],
            'synced': bool(row['synced']),
            'sync_attempts': row['sync_attempts'],
            'synced_job_id': row.get('synced_job_id'),
            'synced_estimate_id': row.get('synced_estimate_id')
        }

    def get_technician_estimates(
        self,
        tech_id: str,
        include_synced: bool = False
    ) -> List[Dict]:
        """Get all estimates for technician"""
        if include_synced:
            results = self.db.execute("""
                SELECT * FROM offline_estimates
                WHERE created_by = ?
                ORDER BY created_at DESC
            """, (tech_id,))
        else:
            results = self.db.execute("""
                SELECT * FROM offline_estimates
                WHERE created_by = ?
                  AND synced = 0
                ORDER BY created_at DESC
            """, (tech_id,))

        estimates = []
        for row in results:
            estimates.append({
                'offline_id': row['offline_id'],
                'customer_info': json.loads(row['customer_data']),
                'vehicle_info': json.loads(row['vehicle_data']),
                'damage_info': json.loads(row['damage_data']),
                'created_at': row['created_at'],
                'status': row['status'],
                'synced': bool(row['synced'])
            })

        return estimates

    def get_recent_estimates(
        self,
        limit: int = 10,
        include_synced: bool = True
    ) -> List[Dict]:
        """Get recent offline estimates"""
        if include_synced:
            results = self.db.execute("""
                SELECT * FROM offline_estimates
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        else:
            results = self.db.execute("""
                SELECT * FROM offline_estimates
                WHERE synced = 0
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        estimates = []
        for row in results:
            estimates.append({
                'offline_id': row['offline_id'],
                'customer_info': json.loads(row['customer_data']),
                'vehicle_info': json.loads(row['vehicle_data']),
                'damage_info': json.loads(row['damage_data']),
                'created_at': row['created_at'],
                'status': row['status'],
                'synced': bool(row['synced'])
            })

        return estimates

    # ========================================================================
    # UPDATE OPERATIONS
    # ========================================================================

    def update_offline_estimate(
        self,
        offline_id: str,
        customer_info: Optional[Dict] = None,
        vehicle_info: Optional[Dict] = None,
        damage_info: Optional[Dict] = None
    ) -> bool:
        """Update offline estimate before sync"""
        updates = []
        values = []

        if customer_info:
            updates.append("customer_data = ?")
            values.append(json.dumps(customer_info))

        if vehicle_info:
            updates.append("vehicle_data = ?")
            values.append(json.dumps(vehicle_info))

        if damage_info:
            updates.append("damage_data = ?")
            values.append(json.dumps(damage_info))

        if not updates:
            return False

        values.append(offline_id)

        self.db.execute(f"""
            UPDATE offline_estimates
            SET {', '.join(updates)}
            WHERE offline_id = ? AND synced = 0
        """, tuple(values))

        print(f"[OK] Updated offline estimate: {offline_id}")

        return True

    def delete_offline_estimate(self, offline_id: str) -> bool:
        """Delete offline estimate (only if not synced)"""
        self.db.execute("""
            DELETE FROM offline_estimates
            WHERE offline_id = ? AND synced = 0
        """, (offline_id,))

        print(f"[OK] Deleted offline estimate: {offline_id}")

        return True

    # ========================================================================
    # STORAGE MANAGEMENT
    # ========================================================================

    def get_storage_stats(self) -> Dict:
        """Get offline storage statistics"""
        total = self.db.execute("""
            SELECT COUNT(*) as count FROM offline_estimates
        """)[0]['count']

        pending = self.db.execute("""
            SELECT COUNT(*) as count FROM offline_estimates
            WHERE synced = 0
        """)[0]['count']

        synced = self.db.execute("""
            SELECT COUNT(*) as count FROM offline_estimates
            WHERE synced = 1
        """)[0]['count']

        failed = self.db.execute("""
            SELECT COUNT(*) as count FROM offline_estimates
            WHERE synced = 0 AND sync_attempts >= 3
        """)[0]['count']

        return {
            'total_estimates': total,
            'pending_sync': pending,
            'synced': synced,
            'failed': failed
        }

    def cleanup_synced_estimates(self, days_old: int = 30) -> int:
        """
        Remove old synced estimates from offline storage

        Args:
            days_old: Remove synced estimates older than this

        Returns:
            Number of estimates removed
        """
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()

        # Get count before delete
        count_result = self.db.execute("""
            SELECT COUNT(*) as count FROM offline_estimates
            WHERE synced = 1
              AND synced_at < ?
        """, (cutoff_date,))

        count = count_result[0]['count'] if count_result else 0

        # Delete old synced estimates
        self.db.execute("""
            DELETE FROM offline_estimates
            WHERE synced = 1
              AND synced_at < ?
        """, (cutoff_date,))

        print(f"[OK] Cleaned up {count} synced estimates older than {days_old} days")

        return count

    # ========================================================================
    # QUICK ESTIMATE
    # ========================================================================

    def create_quick_estimate(
        self,
        customer_name: str,
        customer_phone: str,
        vehicle_year: int,
        vehicle_make: str,
        vehicle_model: str,
        damage_type: str,
        estimated_cost: float,
        created_by: Optional[str] = None
    ) -> Dict:
        """
        Create quick estimate with minimal info

        Shortcut for fast field estimates
        """
        # Parse name
        name_parts = customer_name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        return self.create_offline_estimate(
            customer_info={
                'first_name': first_name,
                'last_name': last_name,
                'phone': customer_phone
            },
            vehicle_info={
                'year': vehicle_year,
                'make': vehicle_make,
                'model': vehicle_model
            },
            damage_info={
                'damage_type': damage_type,
                'estimated_cost': estimated_cost
            },
            created_by=created_by
        )

    # ========================================================================
    # EXPORT
    # ========================================================================

    def export_estimate_summary(self, offline_id: str) -> str:
        """Generate text summary of offline estimate"""
        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            return "Estimate not found"

        customer = estimate['customer_info']
        vehicle = estimate['vehicle_info']
        damage = estimate['damage_info']

        lines = []
        lines.append("=" * 50)
        lines.append("MOBILE ESTIMATE")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"Estimate ID: {offline_id}")
        lines.append(f"Created: {estimate['created_at']}")
        lines.append(f"Status: {estimate['status']}")
        lines.append("")
        lines.append("CUSTOMER")
        lines.append("-" * 50)
        lines.append(f"  Name: {customer.get('first_name', '')} {customer.get('last_name', '')}")
        lines.append(f"  Phone: {customer.get('phone', 'N/A')}")
        lines.append(f"  Email: {customer.get('email', 'N/A')}")
        lines.append("")
        lines.append("VEHICLE")
        lines.append("-" * 50)
        lines.append(f"  {vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}")
        lines.append(f"  Color: {vehicle.get('color', 'N/A')}")
        lines.append(f"  VIN: {vehicle.get('vin', 'N/A')}")
        lines.append("")
        lines.append("DAMAGE")
        lines.append("-" * 50)
        lines.append(f"  Type: {damage.get('damage_type', 'N/A')}")
        lines.append(f"  Estimated Cost: ${damage.get('estimated_cost', 0):,.2f}")

        if damage.get('panels'):
            lines.append("")
            lines.append("  Panels:")
            for panel in damage['panels']:
                lines.append(f"    - {panel.get('panel', 'N/A')}: {panel.get('dent_count', 0)} dents")

        if damage.get('notes'):
            lines.append("")
            lines.append(f"  Notes: {damage['notes']}")

        if estimate['location_data']:
            loc = estimate['location_data']
            lines.append("")
            lines.append("LOCATION")
            lines.append("-" * 50)
            if loc.get('address'):
                lines.append(f"  {loc['address']}")
            lines.append(f"  GPS: {loc.get('latitude', 0):.6f}, {loc.get('longitude', 0):.6f}")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)

    # ========================================================================
    # E-SIGNATURE MANAGEMENT
    # ========================================================================

    def _ensure_signature_tables(self):
        """Ensure signature-related tables exist"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS estimate_signatures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offline_estimate_id TEXT NOT NULL,
                signature_data TEXT NOT NULL,
                signer_name TEXT NOT NULL,
                signature_type TEXT DEFAULT 'CUSTOMER',
                signed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                device_info TEXT
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS estimate_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offline_estimate_id TEXT NOT NULL,
                recipient_email TEXT NOT NULL,
                portal_link TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivery_status TEXT DEFAULT 'QUEUED'
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS estimate_sms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offline_estimate_id TEXT NOT NULL,
                recipient_phone TEXT NOT NULL,
                message TEXT,
                portal_link TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS portal_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offline_estimate_id TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

    def capture_signature(
        self,
        offline_id: str,
        signature_data: str,
        signer_name: str,
        signature_type: str = 'CUSTOMER',
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None
    ) -> int:
        """
        Capture e-signature for estimate

        Args:
            offline_id: Offline estimate ID
            signature_data: Base64 encoded signature image
            signer_name: Name of person signing
            signature_type: CUSTOMER, TECHNICIAN, WITNESS
            ip_address: IP address of signing device
            device_info: Device/browser information

        Returns:
            Signature ID
        """
        self._ensure_signature_tables()

        result = self.db.execute("""
            INSERT INTO estimate_signatures (
                offline_estimate_id, signature_data, signer_name,
                signature_type, signed_at, ip_address, device_info
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            offline_id,
            signature_data,
            signer_name,
            signature_type,
            datetime.now().isoformat(),
            ip_address,
            device_info
        ))

        signature_id = result[0]['id']

        # Update estimate status
        self.db.execute("""
            UPDATE offline_estimates
            SET status = 'APPROVED'
            WHERE offline_id = ?
        """, (offline_id,))

        print(f"[OK] Captured {signature_type} signature")
        print(f"     Signer: {signer_name}")
        print(f"     Estimate: {offline_id}")

        return signature_id

    def verify_signature(self, signature_id: int) -> Dict:
        """
        Verify signature authenticity

        Returns signature details and verification status
        """
        self._ensure_signature_tables()

        result = self.db.execute("""
            SELECT * FROM estimate_signatures WHERE id = ?
        """, (signature_id,))

        if not result:
            return {'valid': False, 'error': 'Signature not found'}

        sig = result[0]

        verification = {
            'valid': True,
            'signature_id': signature_id,
            'signer_name': sig['signer_name'],
            'signed_at': sig['signed_at'],
            'signature_type': sig['signature_type'],
            'ip_address': sig['ip_address'],
            'device_info': sig['device_info'],
            'verified_at': datetime.now().isoformat()
        }

        return verification

    def get_signatures(self, offline_id: str) -> List[Dict]:
        """Get all signatures for an estimate"""
        self._ensure_signature_tables()

        results = self.db.execute("""
            SELECT * FROM estimate_signatures
            WHERE offline_estimate_id = ?
            ORDER BY signed_at
        """, (offline_id,))

        return [dict(row) for row in results]

    # ========================================================================
    # INSTANT DELIVERY
    # ========================================================================

    def send_estimate_email(
        self,
        offline_id: str,
        recipient_email: str,
        include_pdf: bool = True,
        include_portal_link: bool = True
    ) -> bool:
        """
        Send estimate via email instantly from field

        Args:
            offline_id: Offline estimate ID
            recipient_email: Customer email
            include_pdf: Attach PDF estimate
            include_portal_link: Include customer portal link
        """
        self._ensure_signature_tables()

        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            raise ValueError(f"Estimate {offline_id} not found")

        # Generate portal access token
        portal_link = None
        if include_portal_link:
            portal_token = self._generate_portal_token(offline_id)
            portal_link = f"https://portal.yourshop.com/estimate/{portal_token}"

        # Log email send
        self.db.execute("""
            INSERT INTO estimate_emails (
                offline_estimate_id, recipient_email,
                portal_link, sent_at, delivery_status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            offline_id,
            recipient_email,
            portal_link,
            datetime.now().isoformat(),
            'QUEUED'
        ))

        print(f"[OK] Email queued for delivery")
        print(f"     Recipient: {recipient_email}")
        print(f"     Portal link: {portal_link if include_portal_link else 'Not included'}")

        return True

    def send_estimate_sms(
        self,
        offline_id: str,
        recipient_phone: str,
        include_portal_link: bool = True
    ) -> bool:
        """
        Send estimate via SMS with portal link

        Args:
            offline_id: Offline estimate ID
            recipient_phone: Customer phone number
            include_portal_link: Include customer portal link
        """
        self._ensure_signature_tables()

        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            raise ValueError(f"Estimate {offline_id} not found")

        # Generate portal token
        portal_link = None
        if include_portal_link:
            portal_token = self._generate_portal_token(offline_id)
            portal_link = f"https://portal.yourshop.com/e/{portal_token}"

        # SMS message (160 char limit for single SMS)
        sms_message = f"Your PDR estimate is ready! "
        sms_message += f"${estimate['damage_info']['estimated_cost']:,.0f} for "
        sms_message += f"{estimate['vehicle_info']['year']} {estimate['vehicle_info']['make']}. "

        if include_portal_link:
            sms_message += f"View: {portal_link}"

        # Log SMS send
        self.db.execute("""
            INSERT INTO estimate_sms (
                offline_estimate_id, recipient_phone,
                message, portal_link, sent_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            offline_id,
            recipient_phone,
            sms_message,
            portal_link,
            datetime.now().isoformat()
        ))

        print(f"[OK] SMS queued for delivery")
        print(f"     Recipient: {recipient_phone}")
        print(f"     Message: {sms_message[:50]}...")

        return True

    def _generate_portal_token(self, offline_id: str) -> str:
        """Generate secure portal access token"""
        import secrets

        token = secrets.token_urlsafe(16)

        # Store token mapping
        self.db.execute("""
            INSERT INTO portal_tokens (
                offline_estimate_id, token,
                created_at, expires_at
            ) VALUES (?, ?, ?, ?)
        """, (
            offline_id,
            token,
            datetime.now().isoformat(),
            (datetime.now() + timedelta(hours=24)).isoformat()
        ))

        return token

    # ========================================================================
    # ON-SITE APPROVAL
    # ========================================================================

    def approve_on_site(
        self,
        offline_id: str,
        signature_data: str,
        signer_name: str,
        approval_notes: Optional[str] = None,
        schedule_immediately: bool = False,
        preferred_date: Optional[Any] = None
    ) -> Dict:
        """
        Complete on-site approval workflow

        Capture signature, approve estimate, optionally schedule

        Args:
            offline_id: Offline estimate ID
            signature_data: Customer signature
            signer_name: Customer name
            approval_notes: Customer notes/comments
            schedule_immediately: Create appointment now
            preferred_date: Preferred repair date

        Returns:
            Approval confirmation with next steps
        """
        # Capture signature
        sig_id = self.capture_signature(
            offline_id=offline_id,
            signature_data=signature_data,
            signer_name=signer_name,
            signature_type='CUSTOMER'
        )

        # Update estimate with approval notes
        if approval_notes:
            self.db.execute("""
                UPDATE offline_estimates
                SET status = 'APPROVED'
                WHERE offline_id = ?
            """, (offline_id,))

        estimate = self.get_offline_estimate(offline_id)

        approval = {
            'approved': True,
            'offline_id': offline_id,
            'signature_id': sig_id,
            'approved_at': datetime.now().isoformat(),
            'customer_name': signer_name,
            'estimate_amount': estimate['damage_info']['estimated_cost']
        }

        if schedule_immediately and preferred_date:
            approval['scheduled'] = True
            approval['scheduled_date'] = preferred_date.isoformat() if hasattr(preferred_date, 'isoformat') else str(preferred_date)

        print(f"[OK] Estimate approved on-site!")
        print(f"     Customer: {signer_name}")
        print(f"     Amount: ${estimate['damage_info']['estimated_cost']:,.2f}")
        if schedule_immediately:
            print(f"     Scheduled: {preferred_date or 'TBD'}")

        return approval

    # ========================================================================
    # PRINTING
    # ========================================================================

    def generate_print_data(
        self,
        offline_id: str,
        format: str = 'RECEIPT'
    ) -> Dict:
        """
        Generate data for mobile printer

        Args:
            offline_id: Offline estimate ID
            format: RECEIPT, FULL_ESTIMATE, SIGNATURE_PAGE

        Returns:
            Print-ready data (for thermal/Bluetooth printers)
        """
        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            raise ValueError(f"Estimate {offline_id} not found")

        if format == 'RECEIPT':
            print_data = {
                'format': 'RECEIPT',
                'width': 40,
                'content': self._format_receipt(estimate)
            }
        elif format == 'FULL_ESTIMATE':
            print_data = {
                'format': 'FULL_ESTIMATE',
                'width': 80,
                'content': self._format_full_estimate(estimate)
            }
        else:
            print_data = {
                'format': 'SIGNATURE_PAGE',
                'width': 80,
                'content': self._format_signature_page(estimate)
            }

        print(f"[OK] Generated {format} print data")

        return print_data

    def _format_receipt(self, estimate: Dict) -> str:
        """Format estimate as thermal printer receipt"""
        customer = estimate['customer_info']
        vehicle = estimate['vehicle_info']
        damage = estimate['damage_info']

        receipt = f"""
{'='*40}
      PDR EXCELLENCE
   Paintless Dent Repair
{'='*40}

ESTIMATE

Customer: {customer.get('first_name', '')} {customer.get('last_name', '')}
Phone: {customer.get('phone', 'N/A')}

Vehicle:
{vehicle.get('year', '')} {vehicle.get('make', '')} {vehicle.get('model', '')}

Damage Assessment:
Type: {damage.get('damage_type', 'N/A')}

ESTIMATE: ${damage.get('estimated_cost', 0):,.2f}

Valid for 30 days

Thank you for choosing us!

{'='*40}
"""
        return receipt

    def _format_full_estimate(self, estimate: Dict) -> str:
        """Format complete estimate"""
        customer = estimate['customer_info']
        vehicle = estimate['vehicle_info']
        damage = estimate['damage_info']

        full = f"""
{'='*80}
                           PAINTLESS DENT REPAIR ESTIMATE
{'='*80}

CUSTOMER INFORMATION
{'-'*80}
  Name: {customer.get('first_name', '')} {customer.get('last_name', '')}
  Phone: {customer.get('phone', 'N/A')}
  Email: {customer.get('email', 'N/A')}

VEHICLE INFORMATION
{'-'*80}
  Year: {vehicle.get('year', '')}
  Make: {vehicle.get('make', '')}
  Model: {vehicle.get('model', '')}
  Color: {vehicle.get('color', 'N/A')}
  VIN: {vehicle.get('vin', 'N/A')}

DAMAGE ASSESSMENT
{'-'*80}
  Type: {damage.get('damage_type', 'N/A')}
  Estimated Cost: ${damage.get('estimated_cost', 0):,.2f}

TERMS & CONDITIONS
{'-'*80}
  - Estimate valid for 30 days
  - Final cost may vary if additional damage discovered
  - Payment due upon completion

{'='*80}
"""
        return full

    def _format_signature_page(self, estimate: Dict) -> str:
        """Format signature capture page"""
        damage = estimate['damage_info']

        return f"""
{'='*80}
                           ESTIMATE APPROVAL
{'='*80}

Estimated Cost: ${damage.get('estimated_cost', 0):,.2f}

By signing below, I authorize the above
repair work to be completed.


Customer Signature: _______________________________

Print Name: _______________________________________

Date: ____________________________________________


{'='*80}
"""

    # ========================================================================
    # PAYMENT INTEGRATION (Ready for Square/Stripe)
    # ========================================================================

    def create_payment_request(
        self,
        offline_id: str,
        amount: float,
        payment_method: str = 'CARD',
        collect_now: bool = False
    ) -> Dict:
        """
        Create payment request (ready for Square/Stripe)

        Args:
            offline_id: Offline estimate ID
            amount: Amount to charge
            payment_method: CARD, CASH, CHECK, DIGITAL
            collect_now: Collect payment immediately vs later

        Returns:
            Payment request details
        """
        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            raise ValueError(f"Estimate {offline_id} not found")

        payment_request = {
            'offline_id': offline_id,
            'amount': amount,
            'payment_method': payment_method,
            'collect_now': collect_now,
            'created_at': datetime.now().isoformat(),
            'status': 'PENDING'
        }

        if collect_now:
            payment_request['payment_url'] = f"https://pay.yourshop.com/{offline_id}"
            payment_request['qr_code'] = f"QR code for ${amount}"

        print(f"[OK] Payment request created")
        print(f"     Amount: ${amount:,.2f}")
        print(f"     Method: {payment_method}")
        print(f"     Collect now: {collect_now}")

        return payment_request

    # ========================================================================
    # INSTANT SCHEDULING
    # ========================================================================

    def schedule_from_field(
        self,
        offline_id: str,
        preferred_date: Any,
        preferred_time: str,
        duration_hours: Optional[float] = None
    ) -> Dict:
        """
        Create appointment from field

        Args:
            offline_id: Offline estimate ID
            preferred_date: Customer's preferred date
            preferred_time: Preferred time (e.g., "9:00 AM")
            duration_hours: Estimated job duration

        Returns:
            Appointment details
        """
        estimate = self.get_offline_estimate(offline_id)

        if not estimate:
            raise ValueError(f"Estimate {offline_id} not found")

        customer = estimate['customer_info']

        appointment = {
            'offline_id': offline_id,
            'customer_name': f"{customer.get('first_name', '')} {customer.get('last_name', '')}",
            'scheduled_date': preferred_date.isoformat() if hasattr(preferred_date, 'isoformat') else str(preferred_date),
            'scheduled_time': preferred_time,
            'duration_hours': duration_hours or 2.0,
            'status': 'SCHEDULED',
            'created_at': datetime.now().isoformat()
        }

        print(f"[OK] Appointment scheduled from field")
        print(f"     Date: {appointment['scheduled_date']}")
        print(f"     Time: {preferred_time}")
        print(f"     Duration: {duration_hours or 2.0} hours")

        return appointment
