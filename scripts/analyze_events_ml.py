"""
Analyze test events using all ML models.
"""
import requests
import json

BASE_URL = 'http://localhost:5050'

def main():
    # Get events
    events_resp = requests.get(f'{BASE_URL}/api/events?days=365&limit=20')
    events = events_resp.json()['events']

    print('=' * 80)
    print('           HAILTRACKER PRO - ML ANALYSIS OF TEST EVENTS')
    print('=' * 80)

    # Analyze top 5 significant events
    top_events = [e for e in events if e['max_hail_size_inches'] >= 1.75][:5]

    for i, event in enumerate(top_events, 1):
        print(f'\n{"=" * 80}')
        print(f'EVENT {i}: {event["city"]}, {event["state_province"]} ({event["country"]})')
        print(f'  Date: {event["event_date"]} | Hail Size: {event["max_hail_size_inches"]}" | Radar: {event["primary_radar"]}')
        print('=' * 80)

        # Seasonal Risk
        risk = requests.get(f'{BASE_URL}/api/ml/risk/seasonal', params={
            'lat': event['lat'], 'lon': event['lon'], 'month': 1
        }).json()
        print(f'''
>> SEASONAL RISK ASSESSMENT
  Risk Level: {risk['risk_level']}
  Hail Probability: {risk['hail_probability']}%
  Expected Events/Year: {risk['expected_events']}
  Avg Hail Size: {risk['avg_hail_size_inches']}"''')

        # ML Opportunity Score
        opp = requests.post(f'{BASE_URL}/api/ml/opportunity/score', json={
            'hail_size': event['max_hail_size_inches'],
            'area_km2': 150,
            'population_density': 800,
            'state_province': event['state_province'],
            'month': 1
        }).json()
        print(f'''
>> ML OPPORTUNITY SCORE
  Score: {opp['score']}/100
  Priority: {opp['priority'].upper()}
  Confidence: {opp['confidence']}%''')

        # Claim Rate
        claim = requests.post(f'{BASE_URL}/api/ml/claim-rate/predict', json={
            'hail_size': event['max_hail_size_inches'],
            'median_income': 55000,
            'population_density': 800
        }).json()
        print(f'''
>> INSURANCE CLAIM PREDICTION
  Predicted Claim Rate: {claim['percentage']}%
  Unclaimed Opportunity: {round(claim['unclaimed_rate']*100, 1)}%''')

        # Damage Prediction
        damage = requests.post(f'{BASE_URL}/api/ml/damage/predict', json={
            'max_hail_size': event['max_hail_size_inches'],
            'duration': 25,
            'storm_speed': 30
        }).json()
        print(f'''
>> DAMAGE PREDICTION
  Damage Probability: {round(damage['damage_probability']*100, 1)}%
  Avg Dents/Vehicle: {damage['avg_dents_per_vehicle']}
  Avg Repair Cost: ${damage['avg_repair_cost']:,.0f}''')

        # Vehicle Estimate
        vehicles = requests.post(f'{BASE_URL}/api/ml/vehicles/estimate', json={
            'area_km2': 150,
            'population_density': 800,
            'dealership_count': 5
        }).json()
        print(f'''
>> AFFECTED VEHICLES ESTIMATE
  Total Vehicles in Area: {vehicles['total_vehicles']:,}
  Outdoor (Exposed): {vehicles['outdoor_vehicles']:,} ({vehicles['outdoor_percentage']}%)
  - Residential: {vehicles['by_category']['residential']:,}
  - Commercial Parking: {vehicles['by_category']['commercial_parking']:,}
  - Dealership Inventory: {vehicles['by_category']['dealership_inventory']:,}''')

        # Calculate total market value
        exposed = vehicles['outdoor_vehicles']
        damaged = int(exposed * damage['damage_probability'])
        unclaimed = int(damaged * claim['unclaimed_rate'])
        market_value = unclaimed * damage['avg_repair_cost']

        print(f'''
>> BUSINESS OPPORTUNITY SUMMARY
  Estimated Damaged Vehicles: {damaged:,}
  Unclaimed (Target Market): {unclaimed:,}
  Total Market Value: ${market_value:,.0f}''')

    print(f'''
{'=' * 80}
                              ROUTE OPTIMIZATION
{'=' * 80}
''')

    # Route optimization for top 3 events
    locations = [
        {'name': f"{top_events[0]['city']}, {top_events[0]['state_province']}", 'lat': top_events[0]['lat'], 'lon': top_events[0]['lon']},
        {'name': f"{top_events[1]['city']}, {top_events[1]['state_province']}", 'lat': top_events[1]['lat'], 'lon': top_events[1]['lon']},
        {'name': f"{top_events[2]['city']}, {top_events[2]['state_province']}", 'lat': top_events[2]['lat'], 'lon': top_events[2]['lon']},
    ]

    route = requests.post(f'{BASE_URL}/api/ml/route/optimize', json={'locations': locations}).json()

    print(f'Optimizing route through top 3 hail events:')
    for i, loc in enumerate(route['location_sequence']):
        print(f'  {i+1}. {loc["name"]}')
    print(f'''
  Total Distance: {route['total_distance_km']:.1f} km
  Estimated Travel Time: {route['estimated_travel_time_hours']:.1f} hours
  Efficiency Score: {route['efficiency_score']:.2f}
''')

    # Sentiment analysis on sample social posts
    print('=' * 80)
    print('                         SENTIMENT ANALYSIS')
    print('=' * 80)

    sample_posts = [
        "OMG huge hail in OKC right now! My car is getting destroyed!",
        "Just got an estimate for hail damage repair - $2500! Insurance better cover this.",
        "Great experience with ABC PDR. Fixed all the dents from last week's storm.",
        "Warning: Massive hail storm heading toward Dallas. Take cover!"
    ]

    print('\nAnalyzing sample social media posts:\n')
    for post in sample_posts:
        sentiment = requests.post(f'{BASE_URL}/api/ml/sentiment/analyze',
            json={'text': post}).json()
        print(f'  "{post[:50]}..."')
        print(f'    Sentiment: {sentiment["sentiment"].upper()} | Urgency: {sentiment["urgency"].upper()} | Is Damage Report: {sentiment["is_damage_report"]}')
        print()

    print('=' * 80)
    print('                 ANALYSIS COMPLETE - ALL ML MODELS UTILIZED')
    print('=' * 80)


if __name__ == '__main__':
    main()
