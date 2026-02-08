"""
PDR Market Analyzer

Analyzes PDR markets across North America:
- Seasonal patterns
- Historical hail frequency
- Market size estimation
- Competition analysis
"""

import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger('PDRMarketAnalyzer')


@dataclass
class PDRMarket:
    """Represents a PDR market region."""
    market_id: str
    name: str
    countries: List[str]
    states_provinces: List[str]
    major_cities: List[str]

    # Season info
    season_start_month: int
    season_end_month: int
    peak_months: List[int]

    # Historical data
    avg_events_per_year: int
    avg_hail_size_inches: float

    # Market metrics
    estimated_vehicles: int
    estimated_market_size_millions: float
    priority: int  # 1-5, 1 = highest


@dataclass
class MarketAnalysis:
    """Analysis results for a PDR market."""
    market: PDRMarket
    current_season_active: bool
    ytd_events: int
    ytd_vs_average: float
    recent_opportunities: int
    total_market_value_ytd: float
    competition_level: str
    recommended_actions: List[str]


class PDRMarketAnalyzer:
    """
    Analyzes PDR markets across North America.
    """

    # Predefined market regions
    MARKETS = {
        'tornado_alley': PDRMarket(
            market_id='tornado_alley',
            name='Tornado Alley',
            countries=['US'],
            states_provinces=['OK', 'KS', 'NE', 'TX', 'CO'],
            major_cities=['Oklahoma City', 'Dallas', 'Denver', 'Wichita', 'Omaha'],
            season_start_month=4,
            season_end_month=7,
            peak_months=[5, 6],
            avg_events_per_year=500,
            avg_hail_size_inches=1.5,
            estimated_vehicles=25000000,
            estimated_market_size_millions=500,
            priority=1
        ),
        'texas_triangle': PDRMarket(
            market_id='texas_triangle',
            name='Texas Triangle',
            countries=['US'],
            states_provinces=['TX'],
            major_cities=['Dallas', 'Houston', 'San Antonio', 'Austin'],
            season_start_month=3,
            season_end_month=6,
            peak_months=[4, 5],
            avg_events_per_year=300,
            avg_hail_size_inches=1.4,
            estimated_vehicles=18000000,
            estimated_market_size_millions=350,
            priority=1
        ),
        'canadian_prairies': PDRMarket(
            market_id='canadian_prairies',
            name='Canadian Prairies',
            countries=['CA'],
            states_provinces=['AB', 'SK', 'MB'],
            major_cities=['Calgary', 'Edmonton', 'Saskatoon', 'Winnipeg'],
            season_start_month=6,
            season_end_month=8,
            peak_months=[7],
            avg_events_per_year=150,
            avg_hail_size_inches=1.3,
            estimated_vehicles=4000000,
            estimated_market_size_millions=80,
            priority=1
        ),
        'midwest': PDRMarket(
            market_id='midwest',
            name='Midwest',
            countries=['US'],
            states_provinces=['IL', 'IN', 'OH', 'MI', 'WI', 'MN', 'IA', 'MO'],
            major_cities=['Chicago', 'Indianapolis', 'Minneapolis', 'St. Louis'],
            season_start_month=5,
            season_end_month=8,
            peak_months=[6],
            avg_events_per_year=250,
            avg_hail_size_inches=1.25,
            estimated_vehicles=35000000,
            estimated_market_size_millions=400,
            priority=2
        ),
        'great_plains': PDRMarket(
            market_id='great_plains',
            name='Great Plains',
            countries=['US'],
            states_provinces=['SD', 'ND', 'MT', 'WY'],
            major_cities=['Sioux Falls', 'Bismarck', 'Rapid City'],
            season_start_month=5,
            season_end_month=8,
            peak_months=[6],
            avg_events_per_year=100,
            avg_hail_size_inches=1.4,
            estimated_vehicles=3000000,
            estimated_market_size_millions=50,
            priority=2
        ),
        'southeast': PDRMarket(
            market_id='southeast',
            name='Southeast',
            countries=['US'],
            states_provinces=['AL', 'GA', 'TN', 'MS', 'LA', 'AR', 'FL'],
            major_cities=['Atlanta', 'Nashville', 'Memphis', 'New Orleans'],
            season_start_month=3,
            season_end_month=5,
            peak_months=[3, 4],
            avg_events_per_year=150,
            avg_hail_size_inches=1.2,
            estimated_vehicles=30000000,
            estimated_market_size_millions=250,
            priority=3
        ),
        'mexico_central': PDRMarket(
            market_id='mexico_central',
            name='Central Mexico',
            countries=['MX'],
            states_provinces=['CDM', 'JAL', 'NLE', 'MCH'],
            major_cities=['Mexico City', 'Guadalajara', 'Monterrey'],
            season_start_month=5,
            season_end_month=9,
            peak_months=[7, 8],
            avg_events_per_year=50,
            avg_hail_size_inches=1.0,
            estimated_vehicles=15000000,
            estimated_market_size_millions=100,
            priority=2
        ),
    }

    def __init__(self, db_path: str = None):
        """
        Initialize market analyzer.

        Args:
            db_path: Path to database
        """
        self.db_path = db_path or str(PROJECT_ROOT / 'database' / 'hailtracker_pro.db')

    def analyze_market(self, market_id: str) -> Optional[MarketAnalysis]:
        """
        Analyze a specific market.

        Args:
            market_id: Market identifier

        Returns:
            MarketAnalysis or None
        """
        market = self.MARKETS.get(market_id)
        if not market:
            logger.warning(f"Unknown market: {market_id}")
            return None

        # Check if in season
        current_month = datetime.utcnow().month
        in_season = market.season_start_month <= current_month <= market.season_end_month

        # Get YTD events
        ytd_events = self._count_ytd_events(market.states_provinces)
        expected_ytd = self._estimate_expected_ytd(market)
        ytd_vs_avg = ytd_events / max(expected_ytd, 1)

        # Get recent opportunities
        recent_opps = self._count_recent_opportunities(market.states_provinces)

        # Estimate YTD market value
        ytd_value = self._estimate_ytd_value(market.states_provinces)

        # Determine competition
        competition = self._assess_competition(market_id)

        # Generate recommendations
        actions = self._generate_market_recommendations(
            market, in_season, ytd_vs_avg, recent_opps
        )

        return MarketAnalysis(
            market=market,
            current_season_active=in_season,
            ytd_events=ytd_events,
            ytd_vs_average=round(ytd_vs_avg, 2),
            recent_opportunities=recent_opps,
            total_market_value_ytd=ytd_value,
            competition_level=competition,
            recommended_actions=actions
        )

    def analyze_all_markets(self) -> List[MarketAnalysis]:
        """
        Analyze all predefined markets.

        Returns:
            List of MarketAnalysis sorted by priority
        """
        analyses = []
        for market_id in self.MARKETS:
            analysis = self.analyze_market(market_id)
            if analysis:
                analyses.append(analysis)

        # Sort by priority then by recent opportunities
        analyses.sort(key=lambda x: (x.market.priority, -x.recent_opportunities))
        return analyses

    def _count_ytd_events(self, states: List[str]) -> int:
        """Count hail events year-to-date for states."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            year_start = datetime(datetime.utcnow().year, 1, 1).strftime('%Y-%m-%d')
            placeholders = ','.join(['?' for _ in states])

            cursor.execute(f"""
                SELECT COUNT(*) FROM hail_events
                WHERE event_date >= ?
                  AND state_province IN ({placeholders})
            """, [year_start] + states)

            count = cursor.fetchone()[0]
            conn.close()
            return count

        except Exception as e:
            logger.warning(f"Error counting events: {e}")
            return 0

    def _estimate_expected_ytd(self, market: PDRMarket) -> int:
        """Estimate expected YTD events based on typical season."""
        current_month = datetime.utcnow().month

        # Calculate what fraction of season has passed
        if current_month < market.season_start_month:
            # Before season
            return int(market.avg_events_per_year * 0.1)  # Off-season events
        elif current_month > market.season_end_month:
            # After season
            return market.avg_events_per_year
        else:
            # In season - interpolate
            season_length = market.season_end_month - market.season_start_month + 1
            months_into_season = current_month - market.season_start_month + 1
            fraction = months_into_season / season_length
            return int(market.avg_events_per_year * fraction * 0.8)

    def _count_recent_opportunities(self, states: List[str], days: int = 30) -> int:
        """Count recent high-opportunity events."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
            placeholders = ','.join(['?' for _ in states])

            cursor.execute(f"""
                SELECT COUNT(*) FROM hail_events
                WHERE event_date >= ?
                  AND state_province IN ({placeholders})
                  AND max_hail_size_inches >= 1.0
            """, [cutoff] + states)

            count = cursor.fetchone()[0]
            conn.close()
            return count

        except Exception as e:
            logger.warning(f"Error counting opportunities: {e}")
            return 0

    def _estimate_ytd_value(self, states: List[str]) -> float:
        """Estimate total market value YTD."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            year_start = datetime(datetime.utcnow().year, 1, 1).strftime('%Y-%m-%d')
            placeholders = ','.join(['?' for _ in states])

            cursor.execute(f"""
                SELECT SUM(pdr_opportunity_score * 1000)
                FROM hail_events
                WHERE event_date >= ?
                  AND state_province IN ({placeholders})
            """, [year_start] + states)

            result = cursor.fetchone()[0]
            conn.close()
            return result or 0

        except Exception as e:
            logger.warning(f"Error estimating value: {e}")
            return 0

    def _assess_competition(self, market_id: str) -> str:
        """Assess competition level in market."""
        high_competition = ['tornado_alley', 'texas_triangle']
        medium_competition = ['midwest', 'canadian_prairies', 'great_plains']

        if market_id in high_competition:
            return 'high'
        elif market_id in medium_competition:
            return 'medium'
        else:
            return 'low'

    def _generate_market_recommendations(
        self,
        market: PDRMarket,
        in_season: bool,
        ytd_vs_avg: float,
        recent_opps: int
    ) -> List[str]:
        """Generate market-specific recommendations."""
        actions = []

        if in_season:
            actions.append(f"ACTIVE SEASON - Deploy resources to {market.name}")

            if ytd_vs_avg > 1.2:
                actions.append("Above-average hail activity - maximize presence")
            elif ytd_vs_avg < 0.8:
                actions.append("Below-average activity - monitor closely")

            if recent_opps > 10:
                actions.append(f"High recent activity ({recent_opps} events) - immediate opportunity")
        else:
            # Off-season
            next_season_month = market.season_start_month
            current_month = datetime.utcnow().month
            months_until = (next_season_month - current_month) % 12
            if months_until <= 2:
                actions.append(f"Season starting in {months_until} months - prepare resources")
            else:
                actions.append("Off-season - focus on equipment maintenance")

        # Market-specific
        if market.priority == 1:
            actions.append("Tier 1 market - maintain strong presence")
        elif market.priority == 2:
            actions.append("Tier 2 market - opportunistic deployment")

        return actions

    def get_seasonal_forecast(self, market_id: str) -> Dict:
        """
        Get seasonal forecast for a market.

        Args:
            market_id: Market identifier

        Returns:
            Dict with forecast info
        """
        market = self.MARKETS.get(market_id)
        if not market:
            return {}

        current_month = datetime.utcnow().month

        # Determine season status
        if current_month < market.season_start_month:
            status = 'pre_season'
            months_until_start = market.season_start_month - current_month
        elif current_month > market.season_end_month:
            status = 'post_season'
            months_until_start = 12 - current_month + market.season_start_month
        elif current_month in market.peak_months:
            status = 'peak_season'
            months_until_start = 0
        else:
            status = 'active_season'
            months_until_start = 0

        return {
            'market': market.name,
            'status': status,
            'season_months': f"{market.season_start_month}-{market.season_end_month}",
            'peak_months': market.peak_months,
            'months_until_season': months_until_start if status in ('pre_season', 'post_season') else 0,
            'avg_events': market.avg_events_per_year,
            'avg_hail_size': market.avg_hail_size_inches,
            'market_size_millions': market.estimated_market_size_millions
        }

    def get_market_summary(self) -> Dict:
        """
        Get summary of all markets.

        Returns:
            Dict with market summary
        """
        summary = {
            'total_markets': len(self.MARKETS),
            'total_estimated_vehicles': sum(m.estimated_vehicles for m in self.MARKETS.values()),
            'total_market_size_millions': sum(m.estimated_market_size_millions for m in self.MARKETS.values()),
            'markets_in_season': 0,
            'markets_at_peak': 0,
            'tier1_markets': [],
            'active_markets': []
        }

        current_month = datetime.utcnow().month

        for market_id, market in self.MARKETS.items():
            if market.season_start_month <= current_month <= market.season_end_month:
                summary['markets_in_season'] += 1
                summary['active_markets'].append(market.name)

                if current_month in market.peak_months:
                    summary['markets_at_peak'] += 1

            if market.priority == 1:
                summary['tier1_markets'].append(market.name)

        return summary


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("PDR MARKET ANALYZER TEST")
    print("=" * 60)

    analyzer = PDRMarketAnalyzer()

    # Get market summary
    summary = analyzer.get_market_summary()
    print("\nMARKET SUMMARY")
    print("-" * 40)
    print(f"Total Markets: {summary['total_markets']}")
    print(f"Total Vehicles: {summary['total_estimated_vehicles']:,}")
    print(f"Total Market Size: ${summary['total_market_size_millions']}M")
    print(f"Markets In Season: {summary['markets_in_season']}")
    print(f"Markets At Peak: {summary['markets_at_peak']}")
    print(f"Tier 1 Markets: {', '.join(summary['tier1_markets'])}")
    print(f"Active Markets: {', '.join(summary['active_markets']) or 'None'}")

    # Analyze specific market
    print("\n" + "=" * 60)
    print("TORNADO ALLEY ANALYSIS")
    print("=" * 60)

    analysis = analyzer.analyze_market('tornado_alley')
    if analysis:
        print(f"\nMarket: {analysis.market.name}")
        print(f"Priority: Tier {analysis.market.priority}")
        print(f"Season Active: {'Yes' if analysis.current_season_active else 'No'}")
        print(f"YTD Events: {analysis.ytd_events}")
        print(f"YTD vs Average: {analysis.ytd_vs_average:.0%}")
        print(f"Recent Opportunities: {analysis.recent_opportunities}")
        print(f"Competition: {analysis.competition_level}")
        print(f"\nRecommended Actions:")
        for action in analysis.recommended_actions:
            print(f"  • {action}")

    # Seasonal forecast
    print("\n" + "=" * 60)
    print("SEASONAL FORECASTS")
    print("=" * 60)

    for market_id in ['tornado_alley', 'canadian_prairies', 'mexico_central']:
        forecast = analyzer.get_seasonal_forecast(market_id)
        print(f"\n{forecast['market']}:")
        print(f"  Status: {forecast['status'].replace('_', ' ').title()}")
        print(f"  Season: Months {forecast['season_months']}")
        print(f"  Peak: {forecast['peak_months']}")
        print(f"  Market Size: ${forecast['market_size_millions']}M")

    print("\nPDR market analyzer ready!")
