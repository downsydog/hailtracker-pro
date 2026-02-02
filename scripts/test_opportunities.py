"""Test PDR opportunity finder with real events."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.pdr.opportunity import PDROpportunityScorer

scorer = PDROpportunityScorer()
opportunities = scorer.score_recent_events(days=30)

print('=' * 70)
print('PDR OPPORTUNITY FINDER - TOP OPPORTUNITIES')
print('=' * 70)

for i, opp in enumerate(opportunities[:10], 1):
    print(f'''
{i}. {opp.location}
   Score: {opp.opportunity_score}/100 [{opp.priority.upper()}]
   Hail Event: {opp.event_date.strftime('%Y-%m-%d')} ({opp.event_age_days} days ago)
   Damage Severity: {opp.damage_severity}
   Vehicles Damaged: {opp.estimated_vehicles_damaged:,}
   Unclaimed Potential: {opp.unclaimed_estimate:,}
   Total Market Value: ${opp.total_market_value:,.0f}
   Competition: {opp.competition_level}
   Window Remaining: {opp.window_remaining_days} days
   Top Action: {opp.recommended_actions[0] if opp.recommended_actions else 'N/A'}
''')

print('=' * 70)
print(f'Total Opportunities Scored: {len(opportunities)}')

# Store opportunities in database
print('\nStoring opportunities in database...')
for opp in opportunities:
    scorer.store_opportunity(opp)
print(f'Stored {len(opportunities)} opportunities.')
