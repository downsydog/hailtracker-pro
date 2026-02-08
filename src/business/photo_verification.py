"""
Simple Text-Based Photo Verification for Fleet Locations.

Extracts hail size information from text descriptions and validates
claims against known hail events. Designed to be simple and practical
for PDR sales reps in the field.

NOT for complex image analysis - just text parsing and validation.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger('PhotoVerification')


# Standard hail size reference chart
HAIL_SIZE_REFERENCE = {
    'pea': 0.25,
    'marble': 0.50,
    'dime': 0.70,
    'penny': 0.75,
    'nickel': 0.88,
    'quarter': 1.00,
    'half dollar': 1.25,
    'walnut': 1.50,
    'ping pong': 1.50,
    'golf ball': 1.75,
    'hen egg': 2.00,
    'tennis ball': 2.50,
    'baseball': 2.75,
    'apple': 3.00,
    'softball': 4.00,
    'grapefruit': 4.50,
}

# Damage severity based on hail size
DAMAGE_SEVERITY = {
    (0, 0.75): {'level': 'MINIMAL', 'description': 'Minor cosmetic damage possible'},
    (0.75, 1.0): {'level': 'LIGHT', 'description': 'Light dents on soft panels'},
    (1.0, 1.5): {'level': 'MODERATE', 'description': 'Visible dents, paintwork may crack'},
    (1.5, 2.0): {'level': 'SIGNIFICANT', 'description': 'Significant body damage'},
    (2.0, 3.0): {'level': 'SEVERE', 'description': 'Severe damage, possible glass breakage'},
    (3.0, float('inf')): {'level': 'CATASTROPHIC', 'description': 'Total loss possible'},
}


@dataclass
class VerificationResult:
    """Result of photo/text verification."""
    is_valid: bool
    confidence: float  # 0-100
    extracted_size: Optional[float]  # inches
    extracted_size_text: Optional[str]
    severity: Dict
    timestamp_valid: bool
    location_valid: bool
    event_match: Optional[Dict]
    warnings: List[str]
    notes: List[str]


class TextHailSizeExtractor:
    """
    Extracts hail size from text descriptions.

    Handles formats like:
    - "quarter sized hail"
    - "1.5 inch hail"
    - "golf ball hail"
    - "1-1/2" hail"
    """

    # Regex patterns for size extraction
    PATTERNS = [
        # Numeric with unit: "1.5 inch", "2 inches", "1-1/2 in"
        (r'(\d+(?:[.-]\d+)?(?:/\d+)?)\s*(?:inch(?:es)?|in\.?|")\s*(?:hail)?', 'numeric'),

        # Fractional: "1 1/2 inch", "2 3/4 inches"
        (r'(\d+)\s+(\d+/\d+)\s*(?:inch(?:es)?|in\.?|")', 'mixed_fraction'),

        # Reference objects
        (r'(pea)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(marble)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(dime)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(penny)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(nickel)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(quarter)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(half\s*dollar)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(walnut)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(ping\s*pong)[\s-]*(?:size[d]?|hail|ball)', 'reference'),
        (r'(golf\s*ball)[\s-]*(?:size[d]?|hail)?', 'reference'),
        (r'(hen\s*egg)[\s-]*(?:size[d]?|hail)?', 'reference'),
        (r'(tennis\s*ball)[\s-]*(?:size[d]?|hail)?', 'reference'),
        (r'(baseball)[\s-]*(?:size[d]?|hail)?', 'reference'),
        (r'(apple)[\s-]*(?:size[d]?|hail)', 'reference'),
        (r'(softball)[\s-]*(?:size[d]?|hail)?', 'reference'),
        (r'(grapefruit)[\s-]*(?:size[d]?|hail)?', 'reference'),
    ]

    def extract(self, text: str) -> Tuple[Optional[float], Optional[str]]:
        """
        Extract hail size from text.

        Returns:
            Tuple of (size_inches, original_text)
        """
        if not text:
            return None, None

        text_lower = text.lower()

        for pattern, pattern_type in self.PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                if pattern_type == 'numeric':
                    size_str = match.group(1)
                    size = self._parse_numeric(size_str)
                    return size, match.group(0)

                elif pattern_type == 'mixed_fraction':
                    whole = int(match.group(1))
                    frac = self._parse_fraction(match.group(2))
                    return whole + frac, match.group(0)

                elif pattern_type == 'reference':
                    ref = match.group(1).replace(' ', ' ')  # normalize spaces
                    ref = ref.strip()
                    for ref_name, size in HAIL_SIZE_REFERENCE.items():
                        if ref_name in ref or ref in ref_name:
                            return size, match.group(0)

        return None, None

    def _parse_numeric(self, s: str) -> float:
        """Parse numeric string like '1.5', '1-1/2', '2/3'."""
        s = s.strip()

        # Handle mixed fraction with hyphen: "1-1/2"
        if '-' in s and '/' in s:
            parts = s.split('-')
            whole = float(parts[0])
            frac = self._parse_fraction(parts[1])
            return whole + frac

        # Handle plain fraction: "1/2"
        if '/' in s:
            return self._parse_fraction(s)

        # Handle decimal or integer
        return float(s)

    def _parse_fraction(self, s: str) -> float:
        """Parse fraction string like '1/2', '3/4'."""
        parts = s.split('/')
        if len(parts) == 2:
            return float(parts[0]) / float(parts[1])
        return 0.0


class PhotoVerifier:
    """
    Simple text-based verification system for fleet location photos.

    Verifies:
    1. Hail size claims from text descriptions
    2. Timestamp plausibility
    3. Location proximity to known hail events
    """

    def __init__(self, db_path: Optional[str] = None):
        self.extractor = TextHailSizeExtractor()
        self.db_path = db_path

    def verify(
        self,
        description: str,
        claimed_location: Optional[Tuple[float, float]] = None,
        claimed_date: Optional[datetime] = None,
        photo_metadata: Optional[Dict] = None
    ) -> VerificationResult:
        """
        Verify a photo submission using text description.

        Args:
            description: Text description from user (e.g., "Quarter sized hail damage")
            claimed_location: (lat, lon) of the damage location
            claimed_date: Date the damage occurred
            photo_metadata: Optional EXIF/metadata from photo

        Returns:
            VerificationResult with confidence and extracted data
        """
        warnings = []
        notes = []
        confidence = 100.0

        # Extract hail size from description
        size_inches, size_text = self.extractor.extract(description)

        if size_inches is None:
            warnings.append('Could not extract hail size from description')
            confidence -= 30
        else:
            notes.append(f'Extracted hail size: {size_inches}" ({size_text})')

        # Get damage severity
        severity = self._get_severity(size_inches)

        # Validate timestamp
        timestamp_valid = True
        if claimed_date:
            # Check if date is reasonable (within last 90 days)
            days_ago = (datetime.now() - claimed_date).days
            if days_ago < 0:
                warnings.append('Claimed date is in the future')
                timestamp_valid = False
                confidence -= 40
            elif days_ago > 90:
                warnings.append('Damage claimed over 90 days ago - may be stale')
                confidence -= 20
            elif days_ago > 30:
                notes.append(f'Damage is {days_ago} days old')
                confidence -= 5
        else:
            notes.append('No date provided - cannot validate timeline')
            confidence -= 10

        # Check photo metadata if available
        if photo_metadata:
            if photo_metadata.get('has_exif'):
                notes.append('Photo has EXIF metadata')
            else:
                warnings.append('Photo missing EXIF metadata')
                confidence -= 10

            if photo_metadata.get('camera_model'):
                notes.append(f'Camera: {photo_metadata["camera_model"]}')

            # Check for location mismatch
            if claimed_location and photo_metadata.get('gps_lat'):
                photo_lat = photo_metadata['gps_lat']
                photo_lon = photo_metadata['gps_lon']
                distance = self._haversine_distance(
                    claimed_location[0], claimed_location[1],
                    photo_lat, photo_lon
                )
                if distance > 50:  # More than 50km away
                    warnings.append(f'Photo GPS is {distance:.0f}km from claimed location')
                    confidence -= 25

        # Check location against known hail events
        location_valid = True
        event_match = None
        if claimed_location and claimed_date:
            event_match = self._find_matching_event(
                claimed_location, claimed_date, size_inches
            )
            if event_match:
                notes.append(f'Matches hail event: {event_match.get("event_name", "Unknown")}')
                confidence = min(100, confidence + 15)
            else:
                notes.append('No matching hail event found in database')
                location_valid = False

        # Clamp confidence
        confidence = max(0, min(100, confidence))

        # Determine validity
        is_valid = confidence >= 50 and size_inches is not None

        return VerificationResult(
            is_valid=is_valid,
            confidence=round(confidence, 1),
            extracted_size=size_inches,
            extracted_size_text=size_text,
            severity=severity,
            timestamp_valid=timestamp_valid,
            location_valid=location_valid,
            event_match=event_match,
            warnings=warnings,
            notes=notes
        )

    def _get_severity(self, size_inches: Optional[float]) -> Dict:
        """Get damage severity for hail size."""
        if size_inches is None:
            return {'level': 'UNKNOWN', 'description': 'Size not determined'}

        for (min_size, max_size), severity in DAMAGE_SEVERITY.items():
            if min_size <= size_inches < max_size:
                return severity

        return DAMAGE_SEVERITY[(3.0, float('inf'))]

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in km."""
        import math

        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat/2)**2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        return R * c

    def _find_matching_event(
        self,
        location: Tuple[float, float],
        date: datetime,
        size_inches: Optional[float]
    ) -> Optional[Dict]:
        """
        Find matching hail event from database.

        In a real implementation, this would query the events database.
        """
        # Placeholder - would query actual hail events database
        # For now, return a mock match for demonstration
        return None


def quick_verify(description: str) -> Dict:
    """
    Quick verification for API use.

    Args:
        description: Text description of hail damage

    Returns:
        Dict with verification results
    """
    verifier = PhotoVerifier()
    result = verifier.verify(description)

    return {
        'valid': result.is_valid,
        'confidence': result.confidence,
        'extracted_size_inches': result.extracted_size,
        'extracted_size_text': result.extracted_size_text,
        'severity': result.severity,
        'warnings': result.warnings,
        'notes': result.notes
    }


# Test the extractor
if __name__ == '__main__':
    extractor = TextHailSizeExtractor()

    test_cases = [
        "We had quarter sized hail here yesterday",
        "Golf ball hail damaged my car",
        "Hail was 1.5 inches",
        "Got hit with 2 inch hail",
        "Marble-sized hail fell for 20 minutes",
        "The hail was about 1-1/2 inch diameter",
        "Tennis ball size hail in Norman",
        "Pea size hail, no damage",
        "Large hail, maybe softball sized",
    ]

    print("Text Hail Size Extractor Tests")
    print("=" * 50)

    for text in test_cases:
        size, match = extractor.extract(text)
        print(f"\nInput: '{text}'")
        if size:
            print(f"  Size: {size}\" (matched: '{match}')")
        else:
            print("  No size found")

    print("\n" + "=" * 50)
    print("Full Verification Test")
    print("=" * 50)

    verifier = PhotoVerifier()
    result = verifier.verify(
        "Quarter sized hail hit the dealership lot yesterday",
        claimed_location=(35.4676, -97.5164),  # Oklahoma City
        claimed_date=datetime.now() - timedelta(days=1)
    )

    print(f"\nValid: {result.is_valid}")
    print(f"Confidence: {result.confidence}%")
    print(f"Extracted size: {result.extracted_size}\"")
    print(f"Severity: {result.severity['level']}")
    print(f"Warnings: {result.warnings}")
    print(f"Notes: {result.notes}")
