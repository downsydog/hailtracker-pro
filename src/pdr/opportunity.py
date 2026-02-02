"""
PDR Opportunity Scorer

Calculates business opportunity scores for hail events based on:
- Hail severity (size, duration)
- Vehicle density in affected area
- Estimated claim rates
- Market competition
- Time since event
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import math
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger('PDROpportunityScorer')


@dataclass
class HailEvent:
    """Represents a hail event for opportunity scoring."""
    event_id: int
    event_date: datetime
    lat: float
    lon: float
    max_hail_size_inches: float
    duration_minutes: int = 0
    affected_area_km2: float = 0
    state_province: str = ''
    city: str = ''


@dataclass
class PDROpportunity:
    """Calculated PDR opportunity from a hail event."""
    event_id: int
    event_date: datetime
    location: str

    # Vehicle estimates
    estimated_vehicles_exposed: int
    estimated_vehicles_damaged: int
    unclaimed_estimate: int

    # Damage estimates
    damage_severity: str  # 'light', 'moderate', 'severe', 'catastrophic'
    avg_repair_cost: float
    total_market_value: float

    # Opportunity metrics
    opportunity_score: float  # 0-100
    priority: str  # 'critical', 'high', 'medium', 'low'
    competition_level: str

    # Time factors
    event_age_days: int
    window_remaining_days: int

    # Action items
    recommended_actions: List[str] = field(default_factory=list)


class PDROpportunityScorer:
    """
    Scores hail events for PDR business opportunities.
    """

    # Damage probability by hail size (inches)
    DAMAGE_PROBABILITY = {
        0.5: 0.05,   # Pea - minimal damage
        0.75: 0.15,  # Dime - light damage possible
        1.0: 0.35,   # Quarter - moderate damage likely
        1.25: 0.55,  # Half dollar - significant damage
        1.5: 0.70,   # Ping pong - widespread damage
        1.75: 0.85,  # Golf ball - severe damage
        2.0: 0.92,   # Hen egg - very severe
        2.5: 0.97,   # Tennis ball - catastrophic
        3.0: 0.99,   # Baseball - total damage
    }

    # Average repair costs by severity
    REPAIR_COSTS = {
        'light': 500,
        'moderate': 1200,
        'severe': 2500,
        'catastrophic': 4500,
    }

    # Insurance claim rates by region (approximate)
    CLAIM_RATES = {
        'US': 0.45,  # 45% of damaged vehicles file claims
        'CA': 0.50,  # Higher in Canada
        'MX': 0.25,  # Lower in Mexico
    }

    # Opportunity window (days before repairs typically complete)
    OPPORTUNITY_WINDOW_DAYS = 90

    def __init__(self, db_path: str = None):
        """
        Initialize opportunity scorer.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')

    def score_event(self, event: HailEvent) -> PDROpportunity:
        """
        Calculate PDR opportunity for a hail event.

        Args:
            event: HailEvent to score

        Returns:
            PDROpportunity with all metrics
        """
        # Estimate vehicle exposure
        vehicles_exposed = self._estimate_vehicle_exposure(event)

        # Calculate damage probability
        damage_prob = self._get_damage_probability(event.max_hail_size_inches)
        vehicles_damaged = int(vehicles_exposed * damage_prob)

        # Estimate unclaimed (cash job) potential
        country = self._get_country(event.state_province)
        claim_rate = self.CLAIM_RATES.get(country, 0.40)
        unclaimed = int(vehicles_damaged * (1 - claim_rate))

        # Determine damage severity
        severity = self._get_damage_severity(event.max_hail_size_inches)

        # Calculate market value
        avg_cost = self.REPAIR_COSTS[severity]
        total_value = vehicles_damaged * avg_cost

        # Calculate opportunity score (0-100)
        score = self._calculate_score(
            vehicles_damaged, severity, event, unclaimed
        )

        # Determine priority
        priority = self._get_priority(score)

        # Competition level (placeholder - would need market data)
        competition = self._estimate_competition(event.state_province)

        # Time factors
        event_age = (datetime.utcnow() - event.event_date).days
        window_remaining = max(0, self.OPPORTUNITY_WINDOW_DAYS - event_age)

        # Generate recommendations
        actions = self._generate_recommendations(
            score, severity, vehicles_damaged, event_age
        )

        return PDROpportunity(
            event_id=event.event_id,
            event_date=event.event_date,
            location=f"{event.city}, {event.state_province}" if event.city else event.state_province,
            estimated_vehicles_exposed=vehicles_exposed,
            estimated_vehicles_damaged=vehicles_damaged,
            unclaimed_estimate=unclaimed,
            damage_severity=severity,
            avg_repair_cost=avg_cost,
            total_market_value=total_value,
            opportunity_score=round(score, 1),
            priority=priority,
            competition_level=competition,
            event_age_days=event_age,
            window_remaining_days=window_remaining,
            recommended_actions=actions
        )

    def _estimate_vehicle_exposure(self, event: HailEvent) -> int:
        """Estimate number of vehicles exposed to hail."""
        # Base estimate on affected area and population density
        # Default to moderate density if area unknown
        area_km2 = event.affected_area_km2 or 100  # Default 100 km²

        # Vehicles per km² varies by region
        # Urban: 500-1000, Suburban: 200-400, Rural: 50-150
        density_per_km2 = self._get_vehicle_density(event.state_province)

        # Base vehicle count
        base_vehicles = int(area_km2 * density_per_km2)

        # Adjust for time of day if known (more vehicles outdoors during day)
        # For now, use 0.3 factor (30% of vehicles outdoors on average)
        outdoor_factor = 0.30

        return int(base_vehicles * outdoor_factor)

    def _get_vehicle_density(self, state_province: str) -> int:
        """Get estimated vehicle density for a region."""
        # High-density states/provinces
        high_density = ['TX', 'CA', 'FL', 'NY', 'ON', 'QC']
        medium_density = ['CO', 'OK', 'KS', 'NE', 'AB', 'SK', 'MB']

        if state_province in high_density:
            return 400
        elif state_province in medium_density:
            return 250
        else:
            return 150

    def _get_damage_probability(self, hail_size_inches: float) -> float:
        """Get damage probability for given hail size."""
        # Find closest size in lookup table
        sizes = sorted(self.DAMAGE_PROBABILITY.keys())

        for i, size in enumerate(sizes):
            if hail_size_inches <= size:
                if i == 0:
                    return self.DAMAGE_PROBABILITY[size]
                # Interpolate
                prev_size = sizes[i - 1]
                prev_prob = self.DAMAGE_PROBABILITY[prev_size]
                curr_prob = self.DAMAGE_PROBABILITY[size]
                factor = (hail_size_inches - prev_size) / (size - prev_size)
                return prev_prob + factor * (curr_prob - prev_prob)

        # Larger than max - assume max probability
        return self.DAMAGE_PROBABILITY[sizes[-1]]

    def _get_damage_severity(self, hail_size_inches: float) -> str:
        """Determine damage severity from hail size."""
        if hail_size_inches < 1.0:
            return 'light'
        elif hail_size_inches < 1.5:
            return 'moderate'
        elif hail_size_inches < 2.5:
            return 'severe'
        else:
            return 'catastrophic'

    def _get_country(self, state_province: str) -> str:
        """Determine country from state/province code."""
        us_states = [
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
        ]
        ca_provinces = ['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'ON', 'PE', 'QC', 'SK']

        if state_province in us_states:
            return 'US'
        elif state_province in ca_provinces:
            return 'CA'
        else:
            return 'MX'

    def _calculate_score(
        self,
        vehicles_damaged: int,
        severity: str,
        event: HailEvent,
        unclaimed: int
    ) -> float:
        """Calculate opportunity score (0-100)."""
        score = 0

        # Volume factor (up to 40 points)
        if vehicles_damaged >= 10000:
            score += 40
        elif vehicles_damaged >= 5000:
            score += 35
        elif vehicles_damaged >= 1000:
            score += 30
        elif vehicles_damaged >= 500:
            score += 25
        elif vehicles_damaged >= 100:
            score += 20
        else:
            score += 10

        # Severity factor (up to 30 points)
        severity_scores = {'light': 10, 'moderate': 20, 'severe': 27, 'catastrophic': 30}
        score += severity_scores.get(severity, 15)

        # Unclaimed potential (up to 20 points)
        if unclaimed >= 5000:
            score += 20
        elif unclaimed >= 1000:
            score += 15
        elif unclaimed >= 500:
            score += 12
        elif unclaimed >= 100:
            score += 8
        else:
            score += 4

        # Recency factor (up to 10 points) - newer events score higher
        event_age = (datetime.utcnow() - event.event_date).days
        if event_age <= 7:
            score += 10
        elif event_age <= 14:
            score += 8
        elif event_age <= 30:
            score += 6
        elif event_age <= 60:
            score += 3
        else:
            score += 1

        return min(score, 100)

    def _get_priority(self, score: float) -> str:
        """Determine priority from score."""
        if score >= 80:
            return 'critical'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        else:
            return 'low'

    def _estimate_competition(self, state_province: str) -> str:
        """Estimate competition level in region."""
        # High competition in major hail markets
        high_competition = ['TX', 'OK', 'CO', 'KS', 'NE', 'AB']
        medium_competition = ['MO', 'AR', 'IL', 'IA', 'MN', 'SD', 'SK', 'MB']

        if state_province in high_competition:
            return 'high'
        elif state_province in medium_competition:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendations(
        self,
        score: float,
        severity: str,
        vehicles_damaged: int,
        event_age: int
    ) -> List[str]:
        """Generate actionable recommendations."""
        actions = []

        if score >= 70:
            actions.append("Deploy mobile team immediately")
            actions.append("Contact local dealerships for lot damage")

        if severity in ('severe', 'catastrophic'):
            actions.append("Establish local presence/office")
            actions.append("Partner with body shops for overflow")

        if vehicles_damaged >= 1000:
            actions.append("Run targeted digital ads in area")
            actions.append("Set up damage assessment stations")

        if event_age <= 7:
            actions.append("Door-to-door canvassing in affected neighborhoods")
            actions.append("Social media outreach for recent storm")
        elif event_age <= 30:
            actions.append("Follow up on unrepaired vehicles")
        elif event_age <= 60:
            actions.append("Target vehicles still showing damage")

        # Always include
        actions.append("Document event with photos for marketing")

        return actions

    def score_recent_events(self, days: int = 30) -> List[PDROpportunity]:
        """
        Score all recent hail events.

        Args:
            days: Number of days to look back

        Returns:
            List of PDROpportunity objects sorted by score
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT id, event_date, latitude, longitude,
                   max_hail_size_inches, duration_minutes,
                   affected_area_km2, state_province, city
            FROM hail_events
            WHERE event_date >= ?
            ORDER BY event_date DESC
        """, (cutoff,))

        opportunities = []
        for row in cursor.fetchall():
            event = HailEvent(
                event_id=row['id'],
                event_date=datetime.strptime(row['event_date'], '%Y-%m-%d'),
                lat=row['latitude'],
                lon=row['longitude'],
                max_hail_size_inches=row['max_hail_size_inches'] or 1.0,
                duration_minutes=row['duration_minutes'] or 0,
                affected_area_km2=row['affected_area_km2'] or 0,
                state_province=row['state_province'] or '',
                city=row['city'] or ''
            )
            opportunities.append(self.score_event(event))

        conn.close()

        # Sort by score descending
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)

        return opportunities

    def store_opportunity(self, opp: PDROpportunity) -> int:
        """Store opportunity in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO pdr_opportunities (
                event_id, estimated_vehicles, estimated_claim_rate,
                unclaimed_vehicles_estimate, opportunity_score, priority,
                estimated_revenue_potential, estimated_avg_repair_cost,
                event_age_days, opportunity_window_days, competition_activity,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            opp.event_id,
            opp.estimated_vehicles_damaged,
            1 - (opp.unclaimed_estimate / max(opp.estimated_vehicles_damaged, 1)),
            opp.unclaimed_estimate,
            opp.opportunity_score,
            opp.priority,
            opp.total_market_value,
            opp.avg_repair_cost,
            opp.event_age_days,
            opp.window_remaining_days,
            opp.competition_level
        ))

        conn.commit()
        opp_id = cursor.lastrowid
        conn.close()

        return opp_id


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("PDR OPPORTUNITY SCORER TEST")
    print("=" * 60)

    scorer = PDROpportunityScorer()

    # Create test events
    test_events = [
        HailEvent(
            event_id=1,
            event_date=datetime.utcnow() - timedelta(days=3),
            lat=35.47,
            lon=-97.52,
            max_hail_size_inches=2.0,
            affected_area_km2=150,
            state_province='OK',
            city='Oklahoma City'
        ),
        HailEvent(
            event_id=2,
            event_date=datetime.utcnow() - timedelta(days=10),
            lat=39.74,
            lon=-104.99,
            max_hail_size_inches=1.5,
            affected_area_km2=80,
            state_province='CO',
            city='Denver'
        ),
        HailEvent(
            event_id=3,
            event_date=datetime.utcnow() - timedelta(days=45),
            lat=32.78,
            lon=-96.80,
            max_hail_size_inches=1.0,
            affected_area_km2=50,
            state_province='TX',
            city='Dallas'
        ),
    ]

    print("\nScoring test events:")
    for event in test_events:
        opp = scorer.score_event(event)

        print(f"\n{'=' * 50}")
        print(f"Event: {event.city}, {event.state_province}")
        print(f"Hail Size: {event.max_hail_size_inches}\"")
        print(f"Event Age: {opp.event_age_days} days")
        print(f"{'=' * 50}")
        print(f"Opportunity Score: {opp.opportunity_score}/100 [{opp.priority.upper()}]")
        print(f"Vehicles Exposed: {opp.estimated_vehicles_exposed:,}")
        print(f"Vehicles Damaged: {opp.estimated_vehicles_damaged:,}")
        print(f"Unclaimed Potential: {opp.unclaimed_estimate:,}")
        print(f"Damage Severity: {opp.damage_severity}")
        print(f"Total Market Value: ${opp.total_market_value:,.0f}")
        print(f"Competition: {opp.competition_level}")
        print(f"Window Remaining: {opp.window_remaining_days} days")
        print(f"\nRecommended Actions:")
        for action in opp.recommended_actions:
            print(f"  • {action}")

    print("\nPDR opportunity scorer ready!")
