"""
Storm Verification Manager

Manages social media verifications for hail events.
Links Reddit/Twitter/Instagram posts to storm events as ground truth verification.

FEATURES:
- Store social media verifications with AI analysis
- Link verifications to hail events
- Track verification photos and hail size estimates
- Calculate verification confidence scores
- Query verifications by event or source
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class StormVerificationManager:
    """
    Manage social media verifications for storm events.

    Provides ground truth verification from crowdsourced reports.
    """

    SOURCES = ['reddit', 'twitter', 'instagram', 'youtube', 'facebook', 'manual']

    def __init__(self, db_path: str = None):
        """
        Initialize verification manager.

        Args:
            db_path: Path to database (defaults to hailtracker_crm.db)
        """
        if db_path is None:
            db_path = str(PROJECT_ROOT / 'data' / 'hailtracker_crm.db')
        self.db_path = db_path
        self._ensure_table()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self):
        """Create storm_verifications table if it doesn't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS storm_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Link to hail event
            hail_event_id INTEGER,

            -- Social media source
            source TEXT NOT NULL,  -- reddit, twitter, instagram, youtube, facebook, manual
            post_id TEXT,  -- Platform-specific post ID
            post_url TEXT,
            author TEXT,

            -- Content
            title TEXT,
            content TEXT,

            -- Media
            photo_url TEXT,
            video_url TEXT,
            thumbnail_url TEXT,

            -- Timing
            posted_at TIMESTAMP,

            -- Location mentioned
            location_mentioned TEXT,
            latitude REAL,
            longitude REAL,

            -- Hail size from post text
            hail_size_mentioned TEXT,  -- "golf ball", "2 inch", etc.
            hail_size_inches REAL,  -- Extracted size in inches

            -- AI Analysis results
            ai_analyzed INTEGER DEFAULT 0,  -- Whether photo was analyzed
            ai_detected_hail INTEGER DEFAULT 0,  -- Whether hail detected in photo
            ai_estimated_size REAL,  -- AI-estimated hail size
            ai_size_category TEXT,  -- pea, quarter, golf_ball, etc.
            ai_confidence REAL,  -- 0-100 confidence score
            ai_severity TEXT,  -- trace, minor, moderate, severe, catastrophic

            -- Verification status
            is_verified INTEGER DEFAULT 0,  -- Manually verified
            verified_by TEXT,
            verified_at TIMESTAMP,

            -- Engagement (for relevance scoring)
            likes INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            relevance_score REAL DEFAULT 0.0,

            -- Metadata
            raw_data TEXT,  -- JSON of full scraped data
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (hail_event_id) REFERENCES hail_events(id)
        )
        """)

        # Create indexes for faster queries
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_verifications_event
        ON storm_verifications(hail_event_id)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_verifications_source
        ON storm_verifications(source)
        """)
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_verifications_posted
        ON storm_verifications(posted_at)
        """)

        conn.commit()
        conn.close()

    def add_verification(
        self,
        hail_event_id: int,
        source: str,
        post_url: str,
        **kwargs
    ) -> int:
        """
        Add a social media verification to a storm event.

        Args:
            hail_event_id: ID of the hail event
            source: Social media source (reddit, twitter, etc.)
            post_url: URL of the post
            **kwargs: Additional fields

        Returns:
            ID of created verification
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Build insert statement dynamically
        fields = ['hail_event_id', 'source', 'post_url']
        values = [hail_event_id, source, post_url]

        allowed_fields = [
            'post_id', 'author', 'title', 'content',
            'photo_url', 'video_url', 'thumbnail_url',
            'posted_at', 'location_mentioned', 'latitude', 'longitude',
            'hail_size_mentioned', 'hail_size_inches',
            'ai_analyzed', 'ai_detected_hail', 'ai_estimated_size',
            'ai_size_category', 'ai_confidence', 'ai_severity',
            'is_verified', 'verified_by', 'verified_at',
            'likes', 'shares', 'comments', 'relevance_score',
            'raw_data'
        ]

        for field in allowed_fields:
            if field in kwargs and kwargs[field] is not None:
                fields.append(field)
                values.append(kwargs[field])

        placeholders = ', '.join(['?' for _ in values])
        field_names = ', '.join(fields)

        cursor.execute(f"""
        INSERT INTO storm_verifications ({field_names})
        VALUES ({placeholders})
        """, values)

        verification_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return verification_id

    def get_verifications_for_event(self, hail_event_id: int) -> List[Dict]:
        """
        Get all verifications for a hail event.

        Args:
            hail_event_id: ID of the hail event

        Returns:
            List of verification records
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM storm_verifications
        WHERE hail_event_id = ?
        ORDER BY relevance_score DESC, posted_at DESC
        """, (hail_event_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_verification_count(self, hail_event_id: int) -> int:
        """Get count of verifications for an event."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT COUNT(*) FROM storm_verifications
        WHERE hail_event_id = ?
        """, (hail_event_id,))

        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_verification_summary(self, hail_event_id: int) -> Dict:
        """
        Get verification summary for an event.

        Returns:
            Dict with verification count, sources, avg confidence, etc.
        """
        verifications = self.get_verifications_for_event(hail_event_id)

        if not verifications:
            return {
                'count': 0,
                'verified': False,
                'sources': [],
                'avg_confidence': 0,
                'avg_size_inches': None,
                'photos_analyzed': 0,
                'hail_detected': 0
            }

        sources = list(set(v['source'] for v in verifications))
        confidences = [v['ai_confidence'] for v in verifications if v['ai_confidence']]
        sizes = [v['ai_estimated_size'] for v in verifications if v['ai_estimated_size']]
        photos_analyzed = sum(1 for v in verifications if v['ai_analyzed'])
        hail_detected = sum(1 for v in verifications if v['ai_detected_hail'])

        return {
            'count': len(verifications),
            'verified': len(verifications) >= 2 or any(v['is_verified'] for v in verifications),
            'sources': sources,
            'avg_confidence': sum(confidences) / len(confidences) if confidences else 0,
            'avg_size_inches': sum(sizes) / len(sizes) if sizes else None,
            'photos_analyzed': photos_analyzed,
            'hail_detected': hail_detected
        }

    def update_ai_analysis(
        self,
        verification_id: int,
        estimated_size: float,
        size_category: str,
        confidence: float,
        severity: str,
        detected_hail: bool = True
    ):
        """
        Update verification with AI analysis results.

        Args:
            verification_id: ID of the verification
            estimated_size: AI-estimated hail size in inches
            size_category: Size category (pea, quarter, golf_ball, etc.)
            confidence: Confidence score 0-100
            severity: Severity rating
            detected_hail: Whether hail was detected in the photo
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE storm_verifications
        SET ai_analyzed = 1,
            ai_detected_hail = ?,
            ai_estimated_size = ?,
            ai_size_category = ?,
            ai_confidence = ?,
            ai_severity = ?,
            updated_at = ?
        WHERE id = ?
        """, (
            1 if detected_hail else 0,
            estimated_size,
            size_category,
            confidence,
            severity,
            datetime.now().isoformat(),
            verification_id
        ))

        conn.commit()
        conn.close()

    def search_verifications(
        self,
        source: str = None,
        min_confidence: float = None,
        has_photo: bool = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search verifications with filters.

        Args:
            source: Filter by source platform
            min_confidence: Minimum AI confidence
            has_photo: Filter by photo presence
            limit: Max results

        Returns:
            List of matching verifications
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM storm_verifications WHERE 1=1"
        params = []

        if source:
            query += " AND source = ?"
            params.append(source)

        if min_confidence:
            query += " AND ai_confidence >= ?"
            params.append(min_confidence)

        if has_photo is True:
            query += " AND photo_url IS NOT NULL"
        elif has_photo is False:
            query += " AND photo_url IS NULL"

        query += " ORDER BY relevance_score DESC, created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def delete_verification(self, verification_id: int) -> bool:
        """Delete a verification."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM storm_verifications WHERE id = ?
        """, (verification_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted


# Test
if __name__ == '__main__':
    print("=" * 60)
    print("STORM VERIFICATION MANAGER TEST")
    print("=" * 60)

    manager = StormVerificationManager()

    # Add test verification
    ver_id = manager.add_verification(
        hail_event_id=1,
        source='reddit',
        post_url='https://reddit.com/r/weather/test',
        author='storm_chaser_42',
        title='Massive hail in Dallas!',
        content='Golf ball sized hail coming down hard in Richardson TX',
        photo_url='https://i.redd.it/test.jpg',
        posted_at=datetime.now().isoformat(),
        location_mentioned='Richardson, TX',
        hail_size_mentioned='golf ball',
        hail_size_inches=1.75,
        likes=150,
        comments=23,
        relevance_score=0.85
    )

    print(f"\nCreated verification ID: {ver_id}")

    # Get verifications
    verifications = manager.get_verifications_for_event(1)
    print(f"\nVerifications for event 1: {len(verifications)}")

    # Get summary
    summary = manager.get_verification_summary(1)
    print(f"\nSummary: {summary}")

    # Update with AI analysis
    manager.update_ai_analysis(
        verification_id=ver_id,
        estimated_size=1.8,
        size_category='golf_ball',
        confidence=87.5,
        severity='moderate',
        detected_hail=True
    )

    print("\nAI analysis added!")

    # Get updated summary
    summary = manager.get_verification_summary(1)
    print(f"Updated summary: {summary}")

    print("\n✅ Storm Verification Manager ready!")
