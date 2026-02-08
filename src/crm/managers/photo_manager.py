"""
PDR CRM Part 18 - Photo Manager
Manage before/after photos for PDR jobs

FEATURES:
- Before/after photo pairs
- Panel categorization
- Photo timestamps
- Approval workflow
- Metadata tracking
- Cloud storage ready (S3/Cloudinary)
"""

import os
import hashlib
from datetime import datetime, date
from typing import Optional, List, Dict, Any


class PhotoManager:
    """
    Manage job photos for damage documentation

    Critical for insurance claims and quality proof
    """

    # Panel types for categorization
    PANEL_TYPES = [
        'HOOD',
        'ROOF',
        'TRUNK',
        'FRONT_BUMPER',
        'REAR_BUMPER',
        'DRIVER_DOOR',
        'PASSENGER_DOOR',
        'DRIVER_REAR_DOOR',
        'PASSENGER_REAR_DOOR',
        'DRIVER_FENDER',
        'PASSENGER_FENDER',
        'DRIVER_QUARTER',
        'PASSENGER_QUARTER',
        'WINDSHIELD',
        'REAR_GLASS',
        'OTHER'
    ]

    # Photo types
    PHOTO_TYPES = [
        'BEFORE',      # Before repair
        'AFTER',       # After repair
        'PROGRESS',    # During repair
        'DAMAGE',      # Close-up damage
        'OVERVIEW',    # Full vehicle
        'DETAIL'       # Detail/quality shot
    ]

    # Photo statuses
    PHOTO_STATUSES = [
        'PENDING',     # Awaiting review
        'APPROVED',    # Approved for use
        'REJECTED',    # Rejected (needs retake)
        'ARCHIVED'     # No longer active
    ]

    def __init__(self, db):
        """Initialize photo manager with database instance"""
        self.db = db
        self.storage_path = "data/photos"
        os.makedirs(self.storage_path, exist_ok=True)
        self._ensure_photo_tables()

    def _ensure_photo_tables(self):
        """Ensure photo management tables exist"""
        # Create job_photos table
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS job_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                file_hash TEXT,
                file_size INTEGER,
                photo_type TEXT NOT NULL,
                panel_type TEXT,
                description TEXT,
                capture_date TIMESTAMP,
                uploaded_by TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'PENDING',
                approved_by TEXT,
                approved_at TIMESTAMP,
                approval_notes TEXT,
                rejected_by TEXT,
                rejected_at TIMESTAMP,
                rejection_reason TEXT,
                sequence_order INTEGER DEFAULT 0,
                metadata TEXT,
                updated_at TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)

        # Create photo_pairs table for before/after linking
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS photo_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                before_photo_id INTEGER NOT NULL,
                after_photo_id INTEGER NOT NULL,
                panel_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (before_photo_id) REFERENCES job_photos(id),
                FOREIGN KEY (after_photo_id) REFERENCES job_photos(id),
                UNIQUE(before_photo_id, after_photo_id)
            )
        """)

    # ========================================================================
    # PHOTO UPLOAD & STORAGE
    # ========================================================================

    def upload_photo(
        self,
        job_id: int,
        photo_data: bytes,
        filename: str,
        photo_type: str,
        panel_type: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by: Optional[str] = None,
        capture_date: Optional[datetime] = None,
        sequence_order: int = 0
    ) -> int:
        """
        Upload photo for job

        Args:
            job_id: Job ID
            photo_data: Photo binary data
            filename: Original filename
            photo_type: BEFORE, AFTER, PROGRESS, DAMAGE, OVERVIEW, DETAIL
            panel_type: Panel affected (HOOD, ROOF, etc.)
            description: Photo description
            uploaded_by: Who uploaded (user, customer, tech)
            capture_date: When photo was taken
            sequence_order: Display order

        Returns:
            Photo ID
        """
        if photo_type not in self.PHOTO_TYPES:
            raise ValueError(f"Invalid photo_type. Must be: {self.PHOTO_TYPES}")

        if panel_type and panel_type not in self.PANEL_TYPES:
            raise ValueError(f"Invalid panel_type. Must be: {self.PANEL_TYPES}")

        # Calculate file hash for deduplication
        file_hash = hashlib.md5(photo_data).hexdigest()

        # Get file extension
        file_ext = os.path.splitext(filename)[1].lower() or '.jpg'

        # Generate storage filename
        storage_filename = f"{file_hash}{file_ext}"
        storage_path = os.path.join(self.storage_path, storage_filename)

        # Save file to disk (in production, upload to S3/Cloudinary)
        with open(storage_path, 'wb') as f:
            f.write(photo_data)

        file_size = len(photo_data)
        now = datetime.now().isoformat()

        # Store metadata in database
        result = self.db.execute("""
            INSERT INTO job_photos (
                job_id, filename, storage_path, file_hash,
                file_size, photo_type, panel_type,
                description, uploaded_by, capture_date,
                uploaded_at, status, sequence_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id,
            filename,
            storage_path,
            file_hash,
            file_size,
            photo_type,
            panel_type,
            description,
            uploaded_by or 'system',
            (capture_date or datetime.now()).isoformat(),
            now,
            'PENDING',
            sequence_order
        ))

        photo_id = result[0]['id']

        print(f"[OK] Uploaded photo: {filename}")
        print(f"     Job: {job_id}")
        print(f"     Type: {photo_type}")
        if panel_type:
            print(f"     Panel: {panel_type}")
        print(f"     Size: {file_size:,} bytes")

        return photo_id

    def upload_photo_from_file(
        self,
        job_id: int,
        file_path: str,
        photo_type: str,
        panel_type: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> int:
        """
        Upload photo from file path

        Args:
            job_id: Job ID
            file_path: Path to photo file
            photo_type: BEFORE, AFTER, etc.
            panel_type: Panel affected
            description: Photo description
            uploaded_by: Who uploaded

        Returns:
            Photo ID
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)

        with open(file_path, 'rb') as f:
            photo_data = f.read()

        return self.upload_photo(
            job_id=job_id,
            photo_data=photo_data,
            filename=filename,
            photo_type=photo_type,
            panel_type=panel_type,
            description=description,
            uploaded_by=uploaded_by
        )

    def upload_photo_base64(
        self,
        job_id: int,
        base64_data: str,
        filename: str,
        photo_type: str,
        panel_type: Optional[str] = None,
        description: Optional[str] = None,
        uploaded_by: Optional[str] = None
    ) -> int:
        """
        Upload photo from base64 encoded data (for web/mobile uploads)

        Args:
            job_id: Job ID
            base64_data: Base64 encoded image data
            filename: Filename to use
            photo_type: BEFORE, AFTER, etc.
            panel_type: Panel affected
            description: Photo description
            uploaded_by: Who uploaded

        Returns:
            Photo ID
        """
        import base64

        # Remove data URL prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        photo_data = base64.b64decode(base64_data)

        return self.upload_photo(
            job_id=job_id,
            photo_data=photo_data,
            filename=filename,
            photo_type=photo_type,
            panel_type=panel_type,
            description=description,
            uploaded_by=uploaded_by
        )

    # ========================================================================
    # BEFORE/AFTER PAIRS
    # ========================================================================

    def create_before_after_pair(
        self,
        before_photo_id: int,
        after_photo_id: int,
        notes: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> int:
        """
        Create before/after photo pair

        Links two photos as a before/after set

        Args:
            before_photo_id: Before repair photo ID
            after_photo_id: After repair photo ID
            notes: Optional notes about the pair
            created_by: Who created the pair

        Returns:
            Pair ID
        """
        # Get both photos
        before = self.get_photo(before_photo_id)
        after = self.get_photo(after_photo_id)

        if not before or not after:
            raise ValueError("One or both photos not found")

        if before['job_id'] != after['job_id']:
            raise ValueError("Photos must be from the same job")

        # Determine panel type
        panel_type = before.get('panel_type') or after.get('panel_type')

        # Create pair
        result = self.db.execute("""
            INSERT INTO photo_pairs (
                job_id, before_photo_id, after_photo_id,
                panel_type, notes, created_at, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            before['job_id'],
            before_photo_id,
            after_photo_id,
            panel_type,
            notes,
            datetime.now().isoformat(),
            created_by
        ))

        pair_id = result[0]['id']

        print(f"[OK] Created before/after pair")
        print(f"     Before: {before['filename']}")
        print(f"     After: {after['filename']}")
        if panel_type:
            print(f"     Panel: {panel_type}")

        return pair_id

    def auto_create_pairs(self, job_id: int) -> List[int]:
        """
        Automatically create before/after pairs by matching panels

        Pairs photos with same panel_type that have BEFORE and AFTER types

        Args:
            job_id: Job ID

        Returns:
            List of created pair IDs
        """
        photos = self.get_job_photos(job_id)

        # Group by panel
        by_panel = {}
        for photo in photos:
            panel = photo.get('panel_type')
            if not panel:
                continue
            if panel not in by_panel:
                by_panel[panel] = {'before': [], 'after': []}

            if photo['photo_type'] == 'BEFORE':
                by_panel[panel]['before'].append(photo)
            elif photo['photo_type'] == 'AFTER':
                by_panel[panel]['after'].append(photo)

        pair_ids = []

        for panel, photos_dict in by_panel.items():
            before_photos = photos_dict['before']
            after_photos = photos_dict['after']

            # Match pairs (simple: first before with first after)
            for i, before in enumerate(before_photos):
                if i < len(after_photos):
                    after = after_photos[i]
                    try:
                        pair_id = self.create_before_after_pair(
                            before['id'],
                            after['id'],
                            notes=f'Auto-paired for {panel}'
                        )
                        pair_ids.append(pair_id)
                    except Exception as e:
                        print(f"[WARN] Could not pair {panel}: {e}")

        return pair_ids

    def get_before_after_pairs(self, job_id: int) -> List[Dict[str, Any]]:
        """
        Get all before/after pairs for job

        Returns pairs with full photo details
        """
        return self.db.execute("""
            SELECT
                pp.*,
                bp.filename as before_filename,
                bp.storage_path as before_path,
                bp.description as before_description,
                bp.capture_date as before_date,
                bp.photo_type as before_type,
                ap.filename as after_filename,
                ap.storage_path as after_path,
                ap.description as after_description,
                ap.capture_date as after_date,
                ap.photo_type as after_type
            FROM photo_pairs pp
            JOIN job_photos bp ON bp.id = pp.before_photo_id
            JOIN job_photos ap ON ap.id = pp.after_photo_id
            WHERE pp.job_id = ?
            ORDER BY pp.panel_type, pp.created_at
        """, (job_id,))

    # ========================================================================
    # PHOTO RETRIEVAL
    # ========================================================================

    def get_photo(self, photo_id: int) -> Optional[Dict[str, Any]]:
        """Get photo by ID"""
        result = self.db.execute("""
            SELECT * FROM job_photos
            WHERE id = ? AND deleted_at IS NULL
        """, (photo_id,))

        return dict(result[0]) if result else None

    def get_job_photos(
        self,
        job_id: int,
        photo_type: Optional[str] = None,
        panel_type: Optional[str] = None,
        status: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get photos for job

        Args:
            job_id: Job ID
            photo_type: Filter by type (BEFORE, AFTER, etc.)
            panel_type: Filter by panel
            status: Filter by status
            include_deleted: Include soft-deleted photos

        Returns:
            List of photos
        """
        query = "SELECT * FROM job_photos WHERE job_id = ?"
        params = [job_id]

        if not include_deleted:
            query += " AND deleted_at IS NULL"

        if photo_type:
            query += " AND photo_type = ?"
            params.append(photo_type)

        if panel_type:
            query += " AND panel_type = ?"
            params.append(panel_type)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY sequence_order, capture_date, uploaded_at"

        return self.db.execute(query, tuple(params))

    def get_photos_by_panel(self, job_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get photos organized by panel

        Returns:
            Dictionary with panel_type as keys
        """
        photos = self.get_job_photos(job_id)

        by_panel = {}
        for photo in photos:
            panel = photo.get('panel_type') or 'UNSPECIFIED'
            if panel not in by_panel:
                by_panel[panel] = []
            by_panel[panel].append(photo)

        return by_panel

    def get_photos_by_type(self, job_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get photos organized by type

        Returns:
            Dictionary with photo_type as keys
        """
        photos = self.get_job_photos(job_id)

        by_type = {}
        for photo in photos:
            ptype = photo['photo_type']
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(photo)

        return by_type

    # ========================================================================
    # PHOTO APPROVAL WORKFLOW
    # ========================================================================

    def approve_photo(
        self,
        photo_id: int,
        approved_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve photo for use

        Args:
            photo_id: Photo ID
            approved_by: Who approved
            notes: Approval notes

        Returns:
            True if approved
        """
        self.db.execute("""
            UPDATE job_photos
            SET status = 'APPROVED',
                approved_by = ?,
                approved_at = ?,
                approval_notes = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            approved_by,
            datetime.now().isoformat(),
            notes,
            datetime.now().isoformat(),
            photo_id
        ))

        photo = self.get_photo(photo_id)
        if photo:
            print(f"[OK] Approved photo: {photo['filename']}")

        return True

    def reject_photo(
        self,
        photo_id: int,
        rejected_by: str,
        reason: str
    ) -> bool:
        """
        Reject photo

        Args:
            photo_id: Photo ID
            rejected_by: Who rejected
            reason: Rejection reason

        Returns:
            True if rejected
        """
        self.db.execute("""
            UPDATE job_photos
            SET status = 'REJECTED',
                rejected_by = ?,
                rejected_at = ?,
                rejection_reason = ?,
                updated_at = ?
            WHERE id = ?
        """, (
            rejected_by,
            datetime.now().isoformat(),
            reason,
            datetime.now().isoformat(),
            photo_id
        ))

        photo = self.get_photo(photo_id)
        if photo:
            print(f"[REJECT] Photo: {photo['filename']}")
            print(f"         Reason: {reason}")

        return True

    def bulk_approve(self, photo_ids: List[int], approved_by: str) -> int:
        """
        Approve multiple photos at once

        Args:
            photo_ids: List of photo IDs
            approved_by: Who approved

        Returns:
            Count of approved photos
        """
        count = 0
        for photo_id in photo_ids:
            if self.approve_photo(photo_id, approved_by):
                count += 1
        return count

    def get_pending_photos(self, job_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get photos pending approval

        Args:
            job_id: Optional job filter

        Returns:
            List of pending photos
        """
        if job_id:
            return self.db.execute("""
                SELECT jp.*, j.job_number
                FROM job_photos jp
                JOIN jobs j ON j.id = jp.job_id
                WHERE jp.job_id = ?
                  AND jp.status = 'PENDING'
                  AND jp.deleted_at IS NULL
                ORDER BY jp.uploaded_at
            """, (job_id,))
        else:
            return self.db.execute("""
                SELECT jp.*, j.job_number
                FROM job_photos jp
                JOIN jobs j ON j.id = jp.job_id
                WHERE jp.status = 'PENDING'
                  AND jp.deleted_at IS NULL
                ORDER BY jp.uploaded_at
            """)

    # ========================================================================
    # PHOTO OPERATIONS
    # ========================================================================

    def delete_photo(self, photo_id: int, soft_delete: bool = True) -> bool:
        """
        Delete photo

        Args:
            photo_id: Photo ID
            soft_delete: If True, mark as deleted. If False, remove file

        Returns:
            True if deleted
        """
        photo = self.get_photo(photo_id)
        if not photo:
            return False

        if soft_delete:
            self.db.execute("""
                UPDATE job_photos
                SET deleted_at = ?, status = 'ARCHIVED'
                WHERE id = ?
            """, (datetime.now().isoformat(), photo_id))

            print(f"[OK] Soft deleted photo: {photo['filename']}")
        else:
            # Delete physical file
            if photo.get('storage_path') and os.path.exists(photo['storage_path']):
                os.remove(photo['storage_path'])

            # Delete database record
            self.db.execute("DELETE FROM job_photos WHERE id = ?", (photo_id,))

            # Delete any pairs referencing this photo
            self.db.execute("""
                DELETE FROM photo_pairs
                WHERE before_photo_id = ? OR after_photo_id = ?
            """, (photo_id, photo_id))

            print(f"[OK] Permanently deleted photo: {photo['filename']}")

        return True

    def update_photo(self, photo_id: int, **updates) -> bool:
        """
        Update photo metadata

        Args:
            photo_id: Photo ID
            **updates: Fields to update

        Returns:
            True if updated
        """
        if not updates:
            return False

        set_clauses = []
        values = []

        allowed_fields = ['description', 'panel_type', 'photo_type', 'sequence_order']

        for key, value in updates.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if not set_clauses:
            return False

        set_clauses.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(photo_id)

        query = f"""
            UPDATE job_photos
            SET {', '.join(set_clauses)}
            WHERE id = ?
        """

        self.db.execute(query, tuple(values))
        print(f"[OK] Updated photo #{photo_id}")

        return True

    def reorder_photos(self, job_id: int, photo_order: List[int]) -> bool:
        """
        Set photo display order

        Args:
            job_id: Job ID
            photo_order: List of photo IDs in desired order

        Returns:
            True if reordered
        """
        for i, photo_id in enumerate(photo_order):
            self.db.execute("""
                UPDATE job_photos
                SET sequence_order = ?
                WHERE id = ? AND job_id = ?
            """, (i, photo_id, job_id))

        print(f"[OK] Reordered {len(photo_order)} photos for job #{job_id}")
        return True

    # ========================================================================
    # PHOTO ANALYTICS
    # ========================================================================

    def get_job_photo_summary(self, job_id: int) -> Dict[str, Any]:
        """
        Get photo summary for job

        Returns counts and stats
        """
        photos = self.get_job_photos(job_id)

        summary = {
            'total_photos': len(photos),
            'by_type': {},
            'by_panel': {},
            'by_status': {},
            'total_size_bytes': 0,
            'before_after_pairs': 0,
            'approved_count': 0,
            'pending_count': 0,
            'rejected_count': 0
        }

        for photo in photos:
            # By type
            ptype = photo['photo_type']
            summary['by_type'][ptype] = summary['by_type'].get(ptype, 0) + 1

            # By panel
            panel = photo.get('panel_type') or 'UNSPECIFIED'
            summary['by_panel'][panel] = summary['by_panel'].get(panel, 0) + 1

            # By status
            status = photo['status']
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1

            if status == 'APPROVED':
                summary['approved_count'] += 1
            elif status == 'PENDING':
                summary['pending_count'] += 1
            elif status == 'REJECTED':
                summary['rejected_count'] += 1

            # Total size
            summary['total_size_bytes'] += photo.get('file_size') or 0

        # Count pairs
        pairs = self.db.execute("""
            SELECT COUNT(*) as count FROM photo_pairs WHERE job_id = ?
        """, (job_id,))
        summary['before_after_pairs'] = pairs[0]['count'] if pairs else 0

        # Human readable size
        size_mb = summary['total_size_bytes'] / (1024 * 1024)
        summary['total_size_mb'] = round(size_mb, 2)

        return summary

    def find_missing_photos(self, job_id: int) -> List[str]:
        """
        Identify missing photo types for complete documentation

        Returns list of recommendations
        """
        photos = self.get_job_photos(job_id)

        has_before = any(p['photo_type'] == 'BEFORE' for p in photos)
        has_after = any(p['photo_type'] == 'AFTER' for p in photos)
        has_overview = any(p['photo_type'] == 'OVERVIEW' for p in photos)

        missing = []

        if not has_before:
            missing.append("BEFORE photos (damage documentation required)")

        if not has_after:
            missing.append("AFTER photos (quality proof required)")

        if not has_overview:
            missing.append("OVERVIEW photos (full vehicle shot)")

        # Check for unpaired before/after by panel
        by_panel = self.get_photos_by_panel(job_id)

        for panel, panel_photos in by_panel.items():
            if panel == 'UNSPECIFIED':
                continue

            panel_before = any(p['photo_type'] == 'BEFORE' for p in panel_photos)
            panel_after = any(p['photo_type'] == 'AFTER' for p in panel_photos)

            if panel_before and not panel_after:
                missing.append(f"AFTER photo for {panel} (has BEFORE)")
            elif panel_after and not panel_before:
                missing.append(f"BEFORE photo for {panel} (has AFTER)")

        return missing

    def get_photo_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get overall photo statistics

        Args:
            days: Number of days to look back

        Returns:
            Statistics dictionary
        """
        cutoff = datetime.now().isoformat()[:10]  # Just date part

        stats = {
            'total_photos': 0,
            'photos_by_type': {},
            'photos_by_status': {},
            'total_size_bytes': 0,
            'total_pairs': 0,
            'avg_photos_per_job': 0
        }

        # Total photos
        total = self.db.execute("""
            SELECT COUNT(*) as count, SUM(file_size) as size
            FROM job_photos
            WHERE deleted_at IS NULL
        """)

        stats['total_photos'] = total[0]['count'] if total else 0
        stats['total_size_bytes'] = total[0]['size'] or 0

        # By type
        by_type = self.db.execute("""
            SELECT photo_type, COUNT(*) as count
            FROM job_photos
            WHERE deleted_at IS NULL
            GROUP BY photo_type
        """)
        stats['photos_by_type'] = {row['photo_type']: row['count'] for row in by_type}

        # By status
        by_status = self.db.execute("""
            SELECT status, COUNT(*) as count
            FROM job_photos
            WHERE deleted_at IS NULL
            GROUP BY status
        """)
        stats['photos_by_status'] = {row['status']: row['count'] for row in by_status}

        # Total pairs
        pairs = self.db.execute("SELECT COUNT(*) as count FROM photo_pairs")
        stats['total_pairs'] = pairs[0]['count'] if pairs else 0

        # Avg per job
        jobs_with_photos = self.db.execute("""
            SELECT COUNT(DISTINCT job_id) as count
            FROM job_photos
            WHERE deleted_at IS NULL
        """)
        job_count = jobs_with_photos[0]['count'] if jobs_with_photos else 0

        if job_count > 0:
            stats['avg_photos_per_job'] = round(stats['total_photos'] / job_count, 1)

        return stats

    # ========================================================================
    # REPORTING
    # ========================================================================

    def generate_photo_report(self, job_id: int) -> str:
        """Generate photo documentation report for job"""
        summary = self.get_job_photo_summary(job_id)
        pairs = self.get_before_after_pairs(job_id)
        missing = self.find_missing_photos(job_id)

        report = []
        report.append("=" * 60)
        report.append("PHOTO DOCUMENTATION REPORT")
        report.append("=" * 60)
        report.append("")

        report.append(f"Job ID: {job_id}")
        report.append(f"Total Photos: {summary['total_photos']}")
        report.append(f"Total Size: {summary['total_size_mb']} MB")
        report.append(f"Before/After Pairs: {summary['before_after_pairs']}")
        report.append("")

        report.append("BY TYPE")
        report.append("-" * 40)
        for ptype, count in summary['by_type'].items():
            report.append(f"  {ptype:15} {count:>5}")
        report.append("")

        report.append("BY PANEL")
        report.append("-" * 40)
        for panel, count in summary['by_panel'].items():
            report.append(f"  {panel:20} {count:>5}")
        report.append("")

        report.append("BY STATUS")
        report.append("-" * 40)
        for status, count in summary['by_status'].items():
            report.append(f"  {status:15} {count:>5}")
        report.append("")

        if pairs:
            report.append("BEFORE/AFTER PAIRS")
            report.append("-" * 40)
            for pair in pairs:
                report.append(f"  {pair.get('panel_type', 'N/A')}:")
                report.append(f"    Before: {pair['before_filename']}")
                report.append(f"    After:  {pair['after_filename']}")
            report.append("")

        if missing:
            report.append("MISSING DOCUMENTATION")
            report.append("-" * 40)
            for item in missing:
                report.append(f"  - {item}")
            report.append("")
        else:
            report.append("[OK] Photo documentation complete!")
            report.append("")

        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 60)

        return "\n".join(report)

    # ========================================================================
    # INSURANCE PACKAGES
    # ========================================================================

    def create_insurance_package(
        self,
        job_id: int,
        include_overview: bool = True,
        include_details: bool = True,
        package_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create insurance submission package

        Generates formatted photo package for insurance claims

        Args:
            job_id: Job ID
            include_overview: Include overview photos
            include_details: Include detail/damage photos
            package_name: Custom package name

        Returns:
            Package metadata with photo list
        """
        # Get job details
        job_result = self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        job = job_result[0] if job_result else {'job_number': f'JOB-{job_id}'}

        # Collect photos for package
        photos_to_include = []

        # 1. All before photos (required)
        before_photos = self.get_job_photos(job_id, photo_type='BEFORE')
        photos_to_include.extend(before_photos)

        # 2. All after photos (required)
        after_photos = self.get_job_photos(job_id, photo_type='AFTER')
        photos_to_include.extend(after_photos)

        # 3. Overview photos (optional)
        if include_overview:
            overview_photos = self.get_job_photos(job_id, photo_type='OVERVIEW')
            photos_to_include.extend(overview_photos)

        # 4. Damage detail photos (optional)
        if include_details:
            damage_photos = self.get_job_photos(job_id, photo_type='DAMAGE')
            photos_to_include.extend(damage_photos)

        # Get before/after pairs
        pairs = self.get_before_after_pairs(job_id)

        # Create package metadata
        if not package_name:
            package_name = f"Insurance_Package_{job.get('job_number', f'JOB-{job_id}')}"

        package = {
            'package_name': package_name,
            'job_id': job_id,
            'job_number': job.get('job_number', f'JOB-{job_id}'),
            'created_at': datetime.now().isoformat(),
            'photo_count': len(photos_to_include),
            'pair_count': len(pairs),
            'photos': photos_to_include,
            'pairs': pairs,
            'organized_by_panel': self._organize_photos_for_insurance(photos_to_include, pairs)
        }

        print(f"[OK] Created insurance package: {package_name}")
        print(f"     Total photos: {len(photos_to_include)}")
        print(f"     Before/After pairs: {len(pairs)}")

        return package

    def _organize_photos_for_insurance(
        self,
        photos: List[Dict],
        pairs: List[Dict]
    ) -> Dict[str, Dict[str, List]]:
        """
        Organize photos by panel for insurance submission

        Insurance companies want photos organized by damaged area
        """
        organized = {}

        # Group by panel
        for photo in photos:
            panel = photo.get('panel_type') or 'GENERAL'

            if panel not in organized:
                organized[panel] = {
                    'before': [],
                    'after': [],
                    'damage': [],
                    'other': []
                }

            if photo['photo_type'] == 'BEFORE':
                organized[panel]['before'].append(photo)
            elif photo['photo_type'] == 'AFTER':
                organized[panel]['after'].append(photo)
            elif photo['photo_type'] == 'DAMAGE':
                organized[panel]['damage'].append(photo)
            else:
                organized[panel]['other'].append(photo)

        return organized

    def export_insurance_package(
        self,
        job_id: int,
        export_format: str = 'ZIP',
        include_metadata: bool = True
    ) -> str:
        """
        Export insurance package to file

        Args:
            job_id: Job ID
            export_format: ZIP, PDF
            include_metadata: Include text file with photo descriptions

        Returns:
            Path to exported package
        """
        import zipfile
        import json

        package = self.create_insurance_package(job_id)

        export_dir = "data/exports"
        os.makedirs(export_dir, exist_ok=True)

        export_filename = f"{package['package_name']}.zip"
        export_path = os.path.join(export_dir, export_filename)

        with zipfile.ZipFile(export_path, 'w') as zipf:
            # Add photos organized by panel
            for panel, panel_photos in package['organized_by_panel'].items():
                panel_dir = panel.replace('_', ' ').title()

                # Before photos
                for i, photo in enumerate(panel_photos['before'], 1):
                    if photo.get('storage_path') and os.path.exists(photo['storage_path']):
                        arcname = f"{panel_dir}/Before/{i:02d}_{photo['filename']}"
                        zipf.write(photo['storage_path'], arcname)

                # After photos
                for i, photo in enumerate(panel_photos['after'], 1):
                    if photo.get('storage_path') and os.path.exists(photo['storage_path']):
                        arcname = f"{panel_dir}/After/{i:02d}_{photo['filename']}"
                        zipf.write(photo['storage_path'], arcname)

                # Damage photos
                for i, photo in enumerate(panel_photos['damage'], 1):
                    if photo.get('storage_path') and os.path.exists(photo['storage_path']):
                        arcname = f"{panel_dir}/Damage Detail/{i:02d}_{photo['filename']}"
                        zipf.write(photo['storage_path'], arcname)

            # Add metadata file
            if include_metadata:
                metadata = {
                    'job_number': package['job_number'],
                    'package_created': package['created_at'],
                    'total_photos': package['photo_count'],
                    'before_after_pairs': package['pair_count'],
                    'panels_documented': list(package['organized_by_panel'].keys())
                }

                metadata_json = json.dumps(metadata, indent=2)
                zipf.writestr('PACKAGE_INFO.json', metadata_json)

        print(f"[OK] Exported insurance package: {export_path}")

        return export_path

    # ========================================================================
    # WATERMARKING
    # ========================================================================

    def add_watermark(
        self,
        photo_id: int,
        watermark_text: str,
        position: str = 'BOTTOM_RIGHT'
    ) -> int:
        """
        Add watermark to photo (for social media/marketing)

        Args:
            photo_id: Photo ID
            watermark_text: Text to watermark (e.g., "PDR Excellence")
            position: TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT, CENTER

        Returns:
            New watermarked photo ID

        Note:
            In production, use PIL/Pillow for actual watermarking
            This creates a record and would call watermarking service
        """
        photo_result = self.db.execute(
            "SELECT * FROM job_photos WHERE id = ?",
            (photo_id,)
        )

        if not photo_result:
            raise ValueError(f"Photo not found: {photo_id}")

        photo = photo_result[0]

        # In production: Use PIL to add watermark to image
        # For now, just create metadata record

        watermarked_filename = f"watermarked_{photo['filename']}"

        # Create watermarked version record
        result = self.db.execute("""
            INSERT INTO job_photos (
                job_id, filename, storage_path, file_hash,
                file_size, photo_type, panel_type,
                description, uploaded_by, capture_date,
                uploaded_at, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            photo['job_id'],
            watermarked_filename,
            photo['storage_path'],  # In production, would be new file
            photo['file_hash'] + '_wm',
            photo['file_size'],
            photo['photo_type'],
            photo.get('panel_type'),
            f"{photo.get('description', '')} (Watermarked: {watermark_text})",
            'system',
            photo.get('capture_date'),
            datetime.now().isoformat(),
            'APPROVED',
            f'{{"watermark_text": "{watermark_text}", "watermark_position": "{position}", "source_photo_id": {photo_id}}}'
        ))

        watermarked_id = result[0]['id']

        print(f"[OK] Created watermarked photo: {watermarked_filename}")
        print(f"     Text: {watermark_text}")
        print(f"     Position: {position}")

        return watermarked_id

    def get_watermarked_photos(self, job_id: int) -> List[Dict[str, Any]]:
        """Get all watermarked photos for a job"""
        return self.db.execute("""
            SELECT * FROM job_photos
            WHERE job_id = ?
              AND filename LIKE 'watermarked_%'
              AND deleted_at IS NULL
            ORDER BY uploaded_at DESC
        """, (job_id,))

    # ========================================================================
    # GALLERY HELPERS
    # ========================================================================

    def get_gallery_data(self, job_id: int) -> Dict[str, Any]:
        """
        Get all data needed for photo gallery display

        Returns organized data ready for UI rendering
        """
        pairs = self.get_before_after_pairs(job_id)
        all_photos = self.get_job_photos(job_id)
        by_panel = self.get_photos_by_panel(job_id)
        summary = self.get_job_photo_summary(job_id)

        return {
            'job_id': job_id,
            'before_after_pairs': pairs,
            'all_photos': all_photos,
            'by_panel': by_panel,
            'summary': summary,
            'panels': list(by_panel.keys()),
            'has_complete_documentation': len(self.find_missing_photos(job_id)) == 0
        }

    def get_slideshow_photos(
        self,
        job_id: int,
        photo_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get photos formatted for slideshow display

        Args:
            job_id: Job ID
            photo_types: Filter by types (default: all)

        Returns:
            Ordered list of photos for slideshow
        """
        photos = self.get_job_photos(job_id)

        if photo_types:
            photos = [p for p in photos if p['photo_type'] in photo_types]

        # Sort for optimal slideshow order:
        # 1. Overview first
        # 2. Before photos grouped by panel
        # 3. Damage detail
        # 4. After photos grouped by panel

        type_order = {'OVERVIEW': 0, 'BEFORE': 1, 'DAMAGE': 2, 'PROGRESS': 3, 'AFTER': 4, 'DETAIL': 5}

        def sort_key(photo):
            type_rank = type_order.get(photo['photo_type'], 99)
            panel = photo.get('panel_type') or 'ZZZ'
            return (type_rank, panel, photo.get('sequence_order', 0))

        return sorted(photos, key=sort_key)

    def get_comparison_pairs(self, job_id: int) -> List[Dict[str, Any]]:
        """
        Get before/after pairs formatted for side-by-side comparison

        Returns pairs with full photo details for comparison view
        """
        pairs = self.get_before_after_pairs(job_id)

        comparison_data = []
        for pair in pairs:
            comparison_data.append({
                'panel_type': pair.get('panel_type', 'Unknown'),
                'panel_display': (pair.get('panel_type') or 'Unknown').replace('_', ' ').title(),
                'before': {
                    'id': pair['before_photo_id'],
                    'filename': pair['before_filename'],
                    'path': pair['before_path'],
                    'description': pair.get('before_description', ''),
                    'date': pair.get('before_date', '')
                },
                'after': {
                    'id': pair['after_photo_id'],
                    'filename': pair['after_filename'],
                    'path': pair['after_path'],
                    'description': pair.get('after_description', ''),
                    'date': pair.get('after_date', '')
                },
                'notes': pair.get('notes', '')
            })

        return comparison_data
