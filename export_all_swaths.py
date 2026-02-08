"""
Export all swaths from database to GeoJSON
"""

import json
import os
from src.radar.swath_database import SwathDatabase

def export_all_swaths():
    print("\n" + "="*70)
    print("EXPORTING ALL SWATHS FROM DATABASE")
    print("="*70 + "\n")

    db = SwathDatabase()

    # Get all events
    all_events = db.get_all_events(limit=500)

    print(f"Found {len(all_events)} events in database")
    print()

    if not all_events:
        print("No events to export.")
        return

    # Export all events to single file
    db.export_all_events_geojson("data/all_swaths_export.geojson", limit=500)
    print()

    # Also create individual exports for each swath method
    methods = set(e['swath_method'] for e in all_events if e.get('swath_method'))

    print("Exporting by method:")
    for method in methods:
        method_events = [e for e in all_events if e.get('swath_method') == method]
        if method_events:
            features = []
            for event in method_events:
                if event['swath_polygon']:
                    color = get_color_by_hail_size(event['max_hail_size'] or 1.0)
                    features.append({
                        'type': 'Feature',
                        'geometry': event['swath_polygon'],
                        'properties': {
                            'id': event['id'],
                            'name': event['event_name'],
                            'date': event['event_date'],
                            'max_hail': event['max_hail_size'],
                            'area_sqmi': event['swath_area_sqmi'],
                            'fill': color,
                            'fill-opacity': 0.4,
                            'stroke': color,
                            'stroke-width': 2
                        }
                    })

            if features:
                geojson = {
                    'type': 'FeatureCollection',
                    'features': features
                }
                filename = f"data/swaths_{method}.geojson"
                with open(filename, 'w') as f:
                    json.dump(geojson, f, indent=2)
                print(f"   {method}: {len(features)} events -> {filename}")

    print()

    # Summary statistics
    print("EXPORT SUMMARY:")
    print("-" * 40)

    total_area = sum(e['swath_area_sqmi'] or 0 for e in all_events)
    max_hail = max((e['max_hail_size'] or 0) for e in all_events)
    largest_event = max(all_events, key=lambda e: e['swath_area_sqmi'] or 0)

    print(f"   Total events: {len(all_events)}")
    print(f"   Total area: {total_area:.1f} sq mi")
    print(f"   Largest hail: {max_hail}\"")
    print(f"   Largest event: {largest_event['event_name']}")
    print(f"     Area: {largest_event['swath_area_sqmi']} sq mi")
    print()
    print("FILES CREATED:")
    print("   data/all_swaths_export.geojson - All events")
    for method in methods:
        print(f"   data/swaths_{method}.geojson - {method.title()} method events")
    print()
    print("VISUALIZATION:")
    print("  -> Open any GeoJSON file at geojson.io to see swaths on a map")
    print("  -> Color-coded by hail size (gold=small, red=severe)")
    print()


def get_color_by_hail_size(size):
    """Get color based on hail size"""
    if size >= 2.5:
        return '#8B0000'  # Dark red - extreme
    elif size >= 2.0:
        return '#FF0000'  # Red - severe
    elif size >= 1.5:
        return '#FF6347'  # Tomato - significant
    elif size >= 1.0:
        return '#FFA500'  # Orange - moderate
    else:
        return '#FFD700'  # Gold - light


def export_events_by_date_range(start_date: str, end_date: str, filename: str):
    """
    Export events within a date range

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        filename: Output filename
    """
    print(f"\nExporting events from {start_date} to {end_date}...")

    db = SwathDatabase()
    events = db.get_events_by_date_range(start_date, end_date)

    if not events:
        print("No events found in date range.")
        return

    features = []
    for event in events:
        if event['swath_polygon']:
            color = get_color_by_hail_size(event['max_hail_size'] or 1.0)
            features.append({
                'type': 'Feature',
                'geometry': event['swath_polygon'],
                'properties': {
                    'id': event['id'],
                    'name': event['event_name'],
                    'date': event['event_date'],
                    'max_hail': event['max_hail_size'],
                    'area_sqmi': event['swath_area_sqmi'],
                    'fill': color,
                    'fill-opacity': 0.4,
                    'stroke': color,
                    'stroke-width': 2
                }
            })

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Exported {len(features)} events to {filename}")


def export_severe_events(min_hail_size: float = 2.0, filename: str = "data/severe_swaths.geojson"):
    """
    Export only severe hail events

    Args:
        min_hail_size: Minimum hail size (default 2.0")
        filename: Output filename
    """
    print(f"\nExporting events with {min_hail_size}\"+ hail...")

    db = SwathDatabase()
    events = db.get_events_by_hail_size(min_hail_size)

    if not events:
        print(f"No events found with {min_hail_size}\"+ hail.")
        return

    features = []
    for event in events:
        if event['swath_polygon']:
            features.append({
                'type': 'Feature',
                'geometry': event['swath_polygon'],
                'properties': {
                    'id': event['id'],
                    'name': event['event_name'],
                    'date': event['event_date'],
                    'max_hail': event['max_hail_size'],
                    'area_sqmi': event['swath_area_sqmi'],
                    'fill': '#FF0000',
                    'fill-opacity': 0.5,
                    'stroke': '#8B0000',
                    'stroke-width': 3
                }
            })

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"Exported {len(features)} severe events to {filename}")


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    export_all_swaths()

    # Also export severe events
    export_severe_events(2.0)
