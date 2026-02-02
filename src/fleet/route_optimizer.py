"""
Route Optimization Service
==========================

Optimize routes for visiting fleet locations using OSRM (Open Source Routing Machine).

OSRM is 100% FREE to use - no API key required.
Uses demo server: http://router.project-osrm.org

Features:
- Traveling salesman optimization (visit multiple locations in optimal order)
- Point-to-point directions
- Distance and time calculations
- Route geometry for map display
"""

import requests
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger('RouteOptimizer')


def optimize_route(locations: List[Dict], start_location: Dict = None) -> Dict:
    """
    Optimize visiting order for fleet locations.
    Uses OSRM traveling salesman solver (trip endpoint).

    Args:
        locations: List of dicts with 'latitude', 'longitude', and optionally 'name', 'id'
        start_location: Optional starting point (your current location)

    Returns:
        Dict with:
        - success: bool
        - locations: List in optimized order
        - order: List of indices
        - total_distance_miles: float
        - total_time_minutes: float
        - route_geometry: GeoJSON for map display
        - legs: List of leg info
    """
    if len(locations) < 2:
        return {
            'success': True,
            'locations': locations,
            'order': list(range(len(locations))),
            'total_distance_miles': 0,
            'total_time_minutes': 0,
        }

    # Prepend start location if provided
    all_locations = []
    start_index_offset = 0

    if start_location and start_location.get('latitude') and start_location.get('longitude'):
        start_location['_is_start'] = True
        all_locations.append(start_location)
        start_index_offset = 1

    all_locations.extend(locations)

    # Filter to valid coordinates
    valid_locations = [
        loc for loc in all_locations
        if loc.get('latitude') and loc.get('longitude')
    ]

    if len(valid_locations) < 2:
        return {'success': False, 'error': 'Need at least 2 valid locations'}

    # Build coordinates string for OSRM (lon,lat format)
    coords = ';'.join([
        f"{loc['longitude']},{loc['latitude']}"
        for loc in valid_locations
    ])

    # OSRM trip endpoint (traveling salesman)
    url = f"http://router.project-osrm.org/trip/v1/driving/{coords}"
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'roundtrip': 'false',  # Don't return to start
        'source': 'first' if start_location else 'any',  # Start from first point if specified
        'destination': 'any',  # End anywhere
        'annotations': 'true',
    }

    try:
        logger.info(f"Optimizing route for {len(valid_locations)} locations...")
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get('code') != 'Ok':
            error_msg = data.get('message', 'Route optimization failed')
            logger.error(f"OSRM error: {error_msg}")
            return {'success': False, 'error': error_msg}

        trip = data['trips'][0]
        waypoints = data['waypoints']

        # Extract optimized order from waypoint indices
        # OSRM returns waypoint_index which maps to original position
        order = []
        for wp in waypoints:
            order.append(wp.get('waypoint_index', 0))

        # Reorder locations according to optimized route
        optimized_locations = []
        for idx in order:
            if idx < len(valid_locations):
                loc = valid_locations[idx].copy()
                loc['visit_order'] = len(optimized_locations) + 1
                optimized_locations.append(loc)

        # Remove start location from results if it was added
        if start_location:
            optimized_locations = [l for l in optimized_locations if not l.get('_is_start')]
            # Adjust order indices
            order = [o - start_index_offset for o in order if o >= start_index_offset]

        # Parse leg information
        legs = []
        for i, leg in enumerate(trip.get('legs', [])):
            legs.append({
                'from_index': i,
                'to_index': i + 1,
                'distance_miles': round(leg['distance'] / 1609.34, 1),
                'duration_minutes': round(leg['duration'] / 60, 0),
            })

        result = {
            'success': True,
            'locations': optimized_locations,
            'order': order,
            'total_distance_miles': round(trip['distance'] / 1609.34, 1),
            'total_time_minutes': round(trip['duration'] / 60, 0),
            'route_geometry': trip.get('geometry'),
            'legs': legs,
        }

        logger.info(f"Route optimized: {result['total_distance_miles']} mi, {result['total_time_minutes']} min")
        return result

    except requests.exceptions.Timeout:
        logger.error("OSRM request timeout")
        return {'success': False, 'error': 'Route service timeout - try fewer locations'}
    except requests.exceptions.RequestException as e:
        logger.error(f"OSRM request failed: {e}")
        return {'success': False, 'error': f'Route service unavailable: {str(e)}'}
    except Exception as e:
        logger.error(f"Route optimization error: {e}")
        return {'success': False, 'error': str(e)}


def get_directions(origin: Dict, destination: Dict) -> Dict:
    """
    Get turn-by-turn directions between two points.

    Args:
        origin: Dict with 'latitude' and 'longitude'
        destination: Dict with 'latitude' and 'longitude'

    Returns:
        Dict with route info and step-by-step directions
    """
    if not origin.get('latitude') or not origin.get('longitude'):
        return {'success': False, 'error': 'Invalid origin'}
    if not destination.get('latitude') or not destination.get('longitude'):
        return {'success': False, 'error': 'Invalid destination'}

    coords = f"{origin['longitude']},{origin['latitude']};{destination['longitude']},{destination['latitude']}"

    url = f"http://router.project-osrm.org/route/v1/driving/{coords}"
    params = {
        'overview': 'full',
        'geometries': 'geojson',
        'steps': 'true',
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        if data.get('code') != 'Ok':
            return {'success': False, 'error': data.get('message', 'Routing failed')}

        route = data['routes'][0]

        # Extract step-by-step directions
        steps = []
        for leg in route.get('legs', []):
            for step in leg.get('steps', []):
                maneuver = step.get('maneuver', {})
                instruction = maneuver.get('instruction', '')

                # Build instruction if not provided
                if not instruction:
                    modifier = maneuver.get('modifier', '')
                    step_type = maneuver.get('type', '')
                    name = step.get('name', '')

                    if step_type == 'depart':
                        instruction = f"Start on {name}" if name else "Start"
                    elif step_type == 'arrive':
                        instruction = "Arrive at destination"
                    elif step_type == 'turn':
                        instruction = f"Turn {modifier} onto {name}" if name else f"Turn {modifier}"
                    elif step_type == 'continue':
                        instruction = f"Continue on {name}" if name else "Continue straight"
                    else:
                        instruction = f"{step_type.capitalize()} {modifier} {name}".strip()

                steps.append({
                    'instruction': instruction,
                    'distance_miles': round(step['distance'] / 1609.34, 2),
                    'duration_minutes': round(step['duration'] / 60, 1),
                    'name': step.get('name', ''),
                })

        return {
            'success': True,
            'distance_miles': round(route['distance'] / 1609.34, 1),
            'duration_minutes': round(route['duration'] / 60, 0),
            'geometry': route.get('geometry'),
            'steps': steps,
        }

    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'Route service timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def calculate_distance(point1: Tuple[float, float], point2: Tuple[float, float]) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        point1: (latitude, longitude)
        point2: (latitude, longitude)

    Returns:
        Distance in miles
    """
    import math

    lat1, lon1 = point1
    lat2, lon2 = point2

    R = 3959  # Earth's radius in miles

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def simple_nearest_neighbor(locations: List[Dict], start: Tuple[float, float] = None) -> List[Dict]:
    """
    Simple nearest neighbor heuristic for route optimization.
    Fallback when OSRM is unavailable.

    Args:
        locations: List of dicts with latitude/longitude
        start: Optional starting point (lat, lon)

    Returns:
        Locations in optimized visiting order
    """
    if not locations:
        return []

    remaining = locations.copy()
    ordered = []

    # Start from given point or first location
    if start:
        current = start
    else:
        first = remaining.pop(0)
        ordered.append(first)
        current = (first['latitude'], first['longitude'])

    while remaining:
        # Find nearest unvisited location
        nearest = min(
            remaining,
            key=lambda loc: calculate_distance(
                current,
                (loc['latitude'], loc['longitude'])
            )
        )
        remaining.remove(nearest)
        ordered.append(nearest)
        current = (nearest['latitude'], nearest['longitude'])

    # Add visit order
    for i, loc in enumerate(ordered):
        loc['visit_order'] = i + 1

    return ordered


def estimate_route_time(locations: List[Dict], avg_speed_mph: float = 30) -> Dict:
    """
    Estimate route time and distance without using OSRM.
    Simple straight-line calculation with average speed.

    Args:
        locations: List of locations in visiting order
        avg_speed_mph: Average driving speed

    Returns:
        Dict with distance and time estimates
    """
    if len(locations) < 2:
        return {
            'total_distance_miles': 0,
            'total_time_minutes': 0,
            'legs': [],
        }

    total_distance = 0
    legs = []

    for i in range(len(locations) - 1):
        loc1 = locations[i]
        loc2 = locations[i + 1]

        if not all([loc1.get('latitude'), loc1.get('longitude'),
                    loc2.get('latitude'), loc2.get('longitude')]):
            continue

        distance = calculate_distance(
            (loc1['latitude'], loc1['longitude']),
            (loc2['latitude'], loc2['longitude'])
        )

        total_distance += distance
        legs.append({
            'from_index': i,
            'to_index': i + 1,
            'distance_miles': round(distance, 1),
            'duration_minutes': round(distance / avg_speed_mph * 60, 0),
        })

    return {
        'total_distance_miles': round(total_distance, 1),
        'total_time_minutes': round(total_distance / avg_speed_mph * 60, 0),
        'legs': legs,
    }


def create_google_maps_url(locations: List[Dict]) -> str:
    """
    Create a Google Maps directions URL for the route.

    Args:
        locations: List of locations in visiting order

    Returns:
        Google Maps URL string
    """
    if not locations:
        return ""

    base_url = "https://www.google.com/maps/dir/"

    # Add each location as a waypoint
    waypoints = []
    for loc in locations:
        if loc.get('latitude') and loc.get('longitude'):
            waypoints.append(f"{loc['latitude']},{loc['longitude']}")

    return base_url + "/".join(waypoints)
