"""
Priority Scoring Algorithm for Fleet Locations
Calculates 0-100 score based on multiple factors
"""

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ScoringResult:
    """Result of priority scoring"""
    score: float
    grade: str
    factors: Dict[str, float]
    estimated_revenue: float
    recommendation: str


class PriorityScorer:
    """
    Calculate priority scores for fleet locations after hail events

    Scoring factors:
    - Vehicle count (40 points max)
    - Accessibility (30 points max)
    - Hail severity (20 points max)
    - Competition (10 points max)
    - Bonuses/Penalties for various factors
    """

    # Grade thresholds
    GRADES = [
        (95, 'A+'),
        (90, 'A'),
        (85, 'A-'),
        (80, 'B+'),
        (75, 'B'),
        (70, 'B-'),
        (65, 'C+'),
        (60, 'C'),
        (55, 'C-'),
        (50, 'D+'),
        (45, 'D'),
        (40, 'D-'),
        (0, 'F')
    ]

    # Tier multipliers
    TIER_MULTIPLIERS = {
        1: 1.15,  # Tier 1 gets 15% boost
        2: 1.0,   # Tier 2 is baseline
        3: 0.85   # Tier 3 gets 15% reduction
    }

    def score_location(self, location: Dict, hail_event: Optional[Dict] = None) -> ScoringResult:
        """
        Calculate priority score for a fleet location

        Args:
            location: Fleet location dict with all fields
            hail_event: Optional hail event data with severity info

        Returns:
            ScoringResult with score, grade, and breakdown
        """
        score = 0.0
        factors = {}

        # =========================================
        # FACTOR 1: Vehicle Count (40 points max)
        # =========================================
        vehicles = location.get('estimated_vehicles', 50)

        if vehicles >= 500:
            vehicle_score = 40
        elif vehicles >= 300:
            vehicle_score = 38
        elif vehicles >= 200:
            vehicle_score = 35
        elif vehicles >= 150:
            vehicle_score = 32
        elif vehicles >= 100:
            vehicle_score = 28
        elif vehicles >= 75:
            vehicle_score = 24
        elif vehicles >= 50:
            vehicle_score = 20
        elif vehicles >= 25:
            vehicle_score = 15
        elif vehicles >= 10:
            vehicle_score = 10
        else:
            vehicle_score = vehicles * 0.5

        factors['vehicles'] = vehicle_score
        score += vehicle_score

        # =========================================
        # FACTOR 2: Accessibility (30 points max)
        # =========================================
        accessibility = location.get('accessibility', 'public')

        accessibility_scores = {
            'public': 30,           # Walk right in
            'private_open': 22,     # Private but no gate
            'private_gated': 12,    # Need permission
            'restricted': 5         # Very difficult
        }

        access_score = accessibility_scores.get(accessibility, 15)

        # Bonus for canvas-friendly
        if location.get('can_canvas_lot', True):
            access_score += 5

        # Penalty for appointment required
        if location.get('requires_appointment', False):
            access_score -= 5

        # Penalty for security
        if location.get('security_guard', False):
            access_score -= 3
        if location.get('has_security_gate', False):
            access_score -= 2

        access_score = max(0, min(35, access_score))  # Cap at 35
        factors['accessibility'] = access_score
        score += access_score

        # =========================================
        # FACTOR 3: Hail Severity (20 points max)
        # =========================================
        if hail_event:
            hail_size = hail_event.get('hail_size_inches', 1.0)
            confidence = hail_event.get('confidence_score', 0.8)

            if hail_size >= 2.75:     # Baseball+
                hail_score = 20
            elif hail_size >= 2.5:    # Tennis ball
                hail_score = 19
            elif hail_size >= 2.0:    # Lime
                hail_score = 17
            elif hail_size >= 1.75:   # Golf ball
                hail_score = 15
            elif hail_size >= 1.5:    # Ping pong
                hail_score = 13
            elif hail_size >= 1.0:    # Quarter
                hail_score = 10
            elif hail_size >= 0.75:   # Nickel
                hail_score = 7
            else:
                hail_score = 4

            # Adjust by confidence
            hail_score *= confidence
        else:
            # No hail event - assume moderate
            hail_score = 12

        factors['hail_severity'] = round(hail_score, 1)
        score += hail_score

        # =========================================
        # FACTOR 4: Competition (10 points max)
        # =========================================
        saturation = location.get('market_saturation', 'low')

        saturation_scores = {
            'low': 10,      # Little competition
            'medium': 5,    # Some competition
            'high': 0       # Saturated
        }

        comp_score = saturation_scores.get(saturation, 5)

        # First mover bonus
        if location.get('first_mover_advantage', False):
            comp_score += 5

        comp_score = min(15, comp_score)  # Cap
        factors['competition'] = comp_score
        score += comp_score

        # =========================================
        # BONUSES
        # =========================================
        bonus_score = 0

        # Luxury vehicles (higher revenue)
        if location.get('luxury_vehicles', False):
            bonus_score += 8
            factors['luxury_bonus'] = 8

        # Previous good relationship
        if location.get('worked_before', False):
            conversion = location.get('conversion_rate', 0)
            if conversion > 0.5:
                bonus_score += 6
                factors['relationship_bonus'] = 6
            elif conversion > 0.3:
                bonus_score += 4
                factors['relationship_bonus'] = 4

            if location.get('customer_satisfaction') == 'high':
                bonus_score += 3
                factors['satisfaction_bonus'] = 3

        # Internal champion
        if location.get('internal_champion'):
            bonus_score += 4
            factors['champion_bonus'] = 4

        # Tier bonus
        tier = location.get('tier', 2)
        tier_mult = self.TIER_MULTIPLIERS.get(tier, 1.0)
        if tier == 1:
            bonus_score += 5
            factors['tier_bonus'] = 5

        score += bonus_score

        # =========================================
        # PENALTIES
        # =========================================
        penalty_score = 0

        # Time decay (if hail event)
        if hail_event:
            hours_since = hail_event.get('time_since_hail_hours', 0)
            if hours_since > 168:  # 7 days
                penalty_score += 15
                factors['time_penalty'] = -15
            elif hours_since > 120:  # 5 days
                penalty_score += 10
                factors['time_penalty'] = -10
            elif hours_since > 72:  # 3 days
                penalty_score += 5
                factors['time_penalty'] = -5

        # Parking fee
        if location.get('parking_fee', False):
            penalty_score += 3
            factors['fee_penalty'] = -3

        score -= penalty_score

        # =========================================
        # FINAL SCORE
        # =========================================
        # Apply tier multiplier
        score *= tier_mult

        # Clamp to 0-100
        score = max(0, min(100, score))
        final_score = round(score, 1)

        # Determine grade
        grade = 'F'
        for threshold, g in self.GRADES:
            if final_score >= threshold:
                grade = g
                break

        # Calculate estimated revenue
        avg_revenue = location.get('avg_revenue_per_vehicle', 1500)
        damage_rate = 0.7 if hail_event and hail_event.get('hail_size_inches', 0) >= 1.5 else 0.5
        conversion = location.get('conversion_rate', 0.35) if location.get('worked_before') else 0.25
        estimated_revenue = vehicles * damage_rate * conversion * avg_revenue

        # Generate recommendation
        recommendation = self._generate_recommendation(location, final_score, grade, hail_event)

        return ScoringResult(
            score=final_score,
            grade=grade,
            factors=factors,
            estimated_revenue=round(estimated_revenue, 0),
            recommendation=recommendation
        )

    def _generate_recommendation(self, location: Dict, score: float, grade: str,
                                  hail_event: Optional[Dict]) -> str:
        """Generate actionable recommendation"""
        name = location.get('name', 'Location')
        vehicles = location.get('estimated_vehicles', 50)
        category = location.get('category', '')

        if grade.startswith('A'):
            urgency = "HIGH PRIORITY"
            action = "Visit immediately"
        elif grade.startswith('B'):
            urgency = "GOOD OPPORTUNITY"
            action = "Visit within 24 hours"
        elif grade.startswith('C'):
            urgency = "MODERATE"
            action = "Visit if time permits"
        else:
            urgency = "LOW PRIORITY"
            action = "Skip or visit last"

        contact = location.get('manager_name', '')
        if contact:
            contact_tip = f"Ask for {contact}"
        else:
            contact_tip = "Ask for the manager"

        parts = [
            f"[{urgency}] {action}",
            f"~{vehicles} vehicles at {category.replace('_', ' ').title()}",
            contact_tip
        ]

        if location.get('best_approach_time'):
            parts.append(f"Best time: {location['best_approach_time']}")

        if location.get('internal_champion'):
            parts.append(f"Champion: {location['internal_champion']}")

        return " | ".join(parts)

    def score_locations_for_event(self, locations: list, hail_event: Dict) -> list:
        """Score multiple locations for a hail event, return sorted by priority"""
        scored = []

        for loc in locations:
            result = self.score_location(loc, hail_event)
            scored.append({
                **loc,
                'priority_score': result.score,
                'opportunity_grade': result.grade,
                'estimated_total_revenue': result.estimated_revenue,
                'score_factors': result.factors,
                'recommendation': result.recommendation
            })

        # Sort by score descending
        scored.sort(key=lambda x: x['priority_score'], reverse=True)
        return scored


def calculate_priority_score(location: Dict, hail_event: Dict = None) -> Dict:
    """Convenience function for priority scoring"""
    scorer = PriorityScorer()
    result = scorer.score_location(location, hail_event)
    return {
        'score': result.score,
        'grade': result.grade,
        'factors': result.factors,
        'estimated_revenue': result.estimated_revenue,
        'recommendation': result.recommendation
    }
