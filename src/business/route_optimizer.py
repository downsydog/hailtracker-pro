"""
Route Optimization for PDR Fleet Visits
Uses Traveling Salesman Problem (TSP) solver

Features:
- Nearest neighbor heuristic
- 2-opt local improvement
- Multi-stop route planning
- Export to GPX, CSV, Google Maps
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
import json
from datetime import datetime


@dataclass
class OptimizedRoute:
    """Optimized route result"""
    locations: List[Dict] = field(default_factory=list)
    route_indices: List[int] = field(default_factory=list)
    total_distance_miles: float = 0.0
    total_distance_km: float = 0.0
    drive_time_hours: float = 0.0
    total_vehicles: int = 0
    estimated_revenue: float = 0.0
    estimated_fuel_cost: float = 0.0
    google_maps_url: str = ""
    summary: Dict = field(default_factory=dict)


class RouteOptimizer:
    """
    Optimize routes through fleet locations using TSP algorithms

    Methods:
    - Nearest Neighbor: Fast initial solution
    - 2-opt: Local search improvement
    - Priority-weighted: Consider priority scores in routing
    """

    # Average speeds for drive time estimation
    CITY_SPEED_MPH = 25
    HIGHWAY_SPEED_MPH = 55
    MIXED_SPEED_MPH = 35

    # Fuel cost estimation
    AVG_MPG = 18
    FUEL_PRICE_PER_GALLON = 3.50

    # Time at each stop (minutes)
    AVG_STOP_TIME_MINUTES = 45

    def __init__(self):
        self.distance_cache = {}

    def haversine_distance(self, lat1: float, lon1: float,
                           lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula

        Returns distance in miles
        """
        # Cache key
        key = (round(lat1, 4), round(lon1, 4), round(lat2, 4), round(lon2, 4))
        if key in self.distance_cache:
            return self.distance_cache[key]

        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in miles
        r = 3956

        distance = c * r
        self.distance_cache[key] = distance
        return distance

    def calculate_distance_matrix(self, locations: List[Dict]) -> List[List[float]]:
        """Calculate distance matrix between all locations"""
        n = len(locations)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                dist = self.haversine_distance(
                    locations[i]['lat'], locations[i]['lon'],
                    locations[j]['lat'], locations[j]['lon']
                )
                matrix[i][j] = dist
                matrix[j][i] = dist

        return matrix

    def nearest_neighbor(self, locations: List[Dict],
                        start_index: int = 0) -> List[int]:
        """
        Nearest neighbor heuristic for TSP

        Greedy algorithm - always go to closest unvisited location
        """
        n = len(locations)
        if n <= 1:
            return list(range(n))

        dist_matrix = self.calculate_distance_matrix(locations)

        visited = [False] * n
        route = [start_index]
        visited[start_index] = True

        current = start_index

        for _ in range(n - 1):
            # Find nearest unvisited
            nearest = None
            min_dist = float('inf')

            for j in range(n):
                if not visited[j] and dist_matrix[current][j] < min_dist:
                    min_dist = dist_matrix[current][j]
                    nearest = j

            if nearest is not None:
                route.append(nearest)
                visited[nearest] = True
                current = nearest

        return route

    def two_opt(self, route: List[int], dist_matrix: List[List[float]],
               max_iterations: int = 1000) -> List[int]:
        """
        2-opt local search to improve route

        Repeatedly reverses segments to reduce total distance
        """
        best_route = route[:]
        n = len(route)
        improved = True
        iterations = 0

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1

            for i in range(1, n - 1):
                for j in range(i + 1, n):
                    # Calculate current distance
                    d1 = dist_matrix[best_route[i - 1]][best_route[i]]
                    d2 = dist_matrix[best_route[j - 1]][best_route[j]] if j < n else 0

                    # Calculate new distance if we reverse segment
                    d3 = dist_matrix[best_route[i - 1]][best_route[j - 1]]
                    d4 = dist_matrix[best_route[i]][best_route[j]] if j < n else 0

                    # If improvement, reverse segment
                    if d3 + d4 < d1 + d2:
                        best_route[i:j] = reversed(best_route[i:j])
                        improved = True

        return best_route

    def optimize_route(self, locations: List[Dict],
                      start_location: Optional[Dict] = None,
                      prioritize_high_value: bool = True) -> OptimizedRoute:
        """
        Optimize route through locations

        Args:
            locations: List of location dicts with lat, lon, priority_score, etc.
            start_location: Optional starting point (if None, starts at highest priority)
            prioritize_high_value: If True, bias toward high-priority locations first

        Returns:
            OptimizedRoute with ordered locations and stats
        """
        if not locations:
            return OptimizedRoute()

        n = len(locations)

        # Determine start index
        if start_location:
            # Find closest to start location
            start_idx = 0
            min_dist = float('inf')
            for i, loc in enumerate(locations):
                d = self.haversine_distance(
                    start_location.get('lat', 0), start_location.get('lon', 0),
                    loc['lat'], loc['lon']
                )
                if d < min_dist:
                    min_dist = d
                    start_idx = i
        else:
            # Start at highest priority location
            if prioritize_high_value:
                start_idx = max(range(n),
                               key=lambda i: locations[i].get('priority_score', 0))
            else:
                start_idx = 0

        # Get initial route using nearest neighbor
        dist_matrix = self.calculate_distance_matrix(locations)
        route = self.nearest_neighbor(locations, start_idx)

        # Improve with 2-opt
        if n > 2:
            route = self.two_opt(route, dist_matrix)

        # Calculate route statistics
        total_distance = 0.0
        for i in range(len(route) - 1):
            total_distance += dist_matrix[route[i]][route[i + 1]]

        # Estimate drive time
        drive_time_hours = total_distance / self.MIXED_SPEED_MPH

        # Reorder locations
        ordered_locations = [locations[i] for i in route]

        # Calculate totals
        total_vehicles = sum(loc.get('estimated_vehicles', 0) for loc in ordered_locations)
        total_revenue = sum(loc.get('estimated_total_revenue', 0) for loc in ordered_locations)

        # Fuel cost
        fuel_gallons = total_distance / self.AVG_MPG
        fuel_cost = fuel_gallons * self.FUEL_PRICE_PER_GALLON

        # Add stop numbers and cumulative distance
        cumulative_dist = 0
        for i, loc in enumerate(ordered_locations):
            loc['stop_number'] = i + 1
            if i > 0:
                cumulative_dist += dist_matrix[route[i-1]][route[i]]
            loc['cumulative_distance'] = round(cumulative_dist, 1)
            loc['drive_time_to_here'] = round(cumulative_dist / self.MIXED_SPEED_MPH * 60, 0)  # minutes

        # Generate Google Maps URL
        google_maps_url = self.generate_google_maps_url(ordered_locations)

        # Summary stats
        summary = {
            'total_stops': n,
            'total_distance_miles': round(total_distance, 1),
            'total_distance_km': round(total_distance * 1.60934, 1),
            'drive_time_hours': round(drive_time_hours, 2),
            'stop_time_hours': round(n * self.AVG_STOP_TIME_MINUTES / 60, 1),
            'total_time_hours': round(drive_time_hours + n * self.AVG_STOP_TIME_MINUTES / 60, 1),
            'fuel_gallons': round(fuel_gallons, 1),
            'fuel_cost': round(fuel_cost, 2),
            'total_vehicles': total_vehicles,
            'estimated_revenue': round(total_revenue, 0),
            'roi_estimate': round(total_revenue / max(fuel_cost, 1), 1)
        }

        return OptimizedRoute(
            locations=ordered_locations,
            route_indices=route,
            total_distance_miles=round(total_distance, 1),
            total_distance_km=round(total_distance * 1.60934, 1),
            drive_time_hours=round(drive_time_hours, 2),
            total_vehicles=total_vehicles,
            estimated_revenue=round(total_revenue, 0),
            estimated_fuel_cost=round(fuel_cost, 2),
            google_maps_url=google_maps_url,
            summary=summary
        )

    def generate_google_maps_url(self, locations: List[Dict], max_waypoints: int = 10) -> str:
        """
        Generate Google Maps directions URL

        Note: Google Maps has a limit on URL length and waypoints
        """
        if not locations:
            return ""

        base_url = "https://www.google.com/maps/dir/"

        # Use up to max_waypoints locations
        selected = locations[:max_waypoints]

        waypoints = []
        for loc in selected:
            # Use coordinates (more reliable than address)
            waypoints.append(f"{loc['lat']},{loc['lon']}")

        return base_url + "/".join(waypoints)

    def export_to_gpx(self, route: OptimizedRoute, filename: str = None) -> str:
        """
        Export route to GPX format for GPS devices

        Returns GPX content as string
        """
        gpx_template = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="HailTracker Pro - Fleet Intelligence"
     xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>PDR Hail Route</name>
    <desc>Optimized route for hail damage opportunities - {total_stops} stops, {total_vehicles:,} vehicles, ${revenue:,.0f} potential</desc>
    <time>{timestamp}</time>
  </metadata>
  <rte>
    <name>Hail Damage Route</name>
    <desc>{distance} miles, {time} hours drive time</desc>
{routepoints}
  </rte>
</gpx>'''

        routepoints = []
        for i, loc in enumerate(route.locations, 1):
            rpt = f'''    <rtept lat="{loc['lat']}" lon="{loc['lon']}">
      <name>{i}. {loc.get('name', 'Stop')}</name>
      <desc>{loc.get('estimated_vehicles', 0)} vehicles - ${loc.get('estimated_total_revenue', 0):,.0f}</desc>
    </rtept>'''
            routepoints.append(rpt)

        gpx_content = gpx_template.format(
            total_stops=len(route.locations),
            total_vehicles=route.total_vehicles,
            revenue=route.estimated_revenue,
            timestamp=datetime.utcnow().isoformat() + 'Z',
            distance=route.total_distance_miles,
            time=route.drive_time_hours,
            routepoints='\n'.join(routepoints)
        )

        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(gpx_content)

        return gpx_content

    def export_to_csv(self, route: OptimizedRoute, filename: str = None) -> str:
        """
        Export route to CSV format

        Returns CSV content as string
        """
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            'Stop #', 'Name', 'Category', 'Address', 'City', 'State',
            'Phone', 'Contact', 'Vehicles', 'Priority', 'Grade',
            'Est. Revenue', 'Distance (mi)', 'Drive Time (min)',
            'Accessibility', 'Notes', 'Lat', 'Lon'
        ])

        # Data rows
        for loc in route.locations:
            writer.writerow([
                loc.get('stop_number', ''),
                loc.get('name', ''),
                loc.get('category', ''),
                loc.get('address', ''),
                loc.get('city', ''),
                loc.get('state', ''),
                loc.get('phone', ''),
                loc.get('manager_name', ''),
                loc.get('estimated_vehicles', 0),
                loc.get('priority_score', 0),
                loc.get('opportunity_grade', ''),
                f"${loc.get('estimated_total_revenue', 0):,.0f}",
                loc.get('cumulative_distance', 0),
                loc.get('drive_time_to_here', 0),
                loc.get('accessibility', ''),
                loc.get('notes', ''),
                loc.get('lat', ''),
                loc.get('lon', '')
            ])

        csv_content = output.getvalue()

        if filename:
            with open(filename, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)

        return csv_content

    def export_to_json(self, route: OptimizedRoute, filename: str = None) -> str:
        """Export route to JSON format"""
        data = {
            'generated': datetime.utcnow().isoformat(),
            'summary': route.summary,
            'google_maps_url': route.google_maps_url,
            'locations': route.locations
        }

        json_content = json.dumps(data, indent=2)

        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(json_content)

        return json_content

    def generate_printable_html(self, route: OptimizedRoute) -> str:
        """Generate printable HTML route sheet"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <title>PDR Route Sheet</title>
    <style>
        body { font-family: Arial, sans-serif; font-size: 12px; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }
        .summary { background: #f0f4ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .summary-item { text-align: center; }
        .summary-value { font-size: 24px; font-weight: bold; color: #1a73e8; }
        .summary-label { font-size: 11px; color: #666; }
        .stop { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; page-break-inside: avoid; }
        .stop-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .stop-number { background: #1a73e8; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; }
        .stop-name { font-size: 16px; font-weight: bold; flex-grow: 1; margin-left: 10px; }
        .stop-grade { padding: 5px 10px; border-radius: 4px; font-weight: bold; }
        .grade-a { background: #4caf50; color: white; }
        .grade-b { background: #2196f3; color: white; }
        .grade-c { background: #ff9800; color: white; }
        .grade-d { background: #f44336; color: white; }
        .stop-details { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
        .detail-item { }
        .detail-label { color: #666; font-size: 10px; }
        .detail-value { font-weight: 500; }
        .highlight { background: #e8f5e9; padding: 5px; border-radius: 4px; }
        .contact-box { background: #fff3e0; padding: 10px; border-radius: 4px; margin-top: 10px; }
        .notes { font-style: italic; color: #666; margin-top: 10px; }
        @media print { .stop { page-break-inside: avoid; } }
    </style>
</head>
<body>
    <h1>PDR Hail Route Sheet</h1>
    <p>Generated: ''' + datetime.now().strftime('%B %d, %Y at %I:%M %p') + '''</p>

    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="summary-value">''' + str(len(route.locations)) + '''</div>
                <div class="summary-label">Stops</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">''' + f"{route.total_distance_miles}" + '''</div>
                <div class="summary-label">Miles</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">''' + f"{route.total_vehicles:,}" + '''</div>
                <div class="summary-label">Vehicles</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">$''' + f"{route.estimated_revenue:,.0f}" + '''</div>
                <div class="summary-label">Potential Revenue</div>
            </div>
        </div>
    </div>
'''

        for loc in route.locations:
            grade = loc.get('opportunity_grade', 'C')
            grade_class = 'grade-a' if grade.startswith('A') else 'grade-b' if grade.startswith('B') else 'grade-c' if grade.startswith('C') else 'grade-d'

            html += f'''
    <div class="stop">
        <div class="stop-header">
            <div class="stop-number">{loc.get('stop_number', '')}</div>
            <div class="stop-name">{loc.get('name', 'Unknown')}</div>
            <div class="stop-grade {grade_class}">{grade}</div>
        </div>
        <div class="stop-details">
            <div class="detail-item">
                <div class="detail-label">Address</div>
                <div class="detail-value">{loc.get('address', '')} {loc.get('city', '')}, {loc.get('state', '')}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Category</div>
                <div class="detail-value">{loc.get('category', '').replace('_', ' ').title()}</div>
            </div>
            <div class="detail-item highlight">
                <div class="detail-label">Estimated Vehicles</div>
                <div class="detail-value">~{loc.get('estimated_vehicles', 0):,}</div>
            </div>
            <div class="detail-item highlight">
                <div class="detail-label">Est. Revenue</div>
                <div class="detail-value">${loc.get('estimated_total_revenue', 0):,.0f}</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Distance</div>
                <div class="detail-value">{loc.get('cumulative_distance', 0)} mi ({loc.get('drive_time_to_here', 0):.0f} min)</div>
            </div>
            <div class="detail-item">
                <div class="detail-label">Accessibility</div>
                <div class="detail-value">{loc.get('accessibility', 'unknown').replace('_', ' ').title()}</div>
            </div>
        </div>
'''

            if loc.get('phone') or loc.get('manager_name'):
                html += f'''
        <div class="contact-box">
            <strong>Contact:</strong> {loc.get('manager_name', 'Manager')}
            {' - ' + loc.get('phone', '') if loc.get('phone') else ''}
            {' (Best time: ' + loc.get('best_approach_time', '') + ')' if loc.get('best_approach_time') else ''}
        </div>
'''

            if loc.get('notes'):
                html += f'''
        <div class="notes">Notes: {loc.get('notes', '')}</div>
'''

            html += '''
    </div>
'''

        html += '''
</body>
</html>'''

        return html


def test_route_optimizer():
    """Test the route optimizer"""
    # Sample locations
    locations = [
        {'name': 'Dealership A', 'lat': 35.4676, 'lon': -97.5164, 'estimated_vehicles': 200, 'priority_score': 85, 'estimated_total_revenue': 50000},
        {'name': 'Rental Car B', 'lat': 35.4800, 'lon': -97.5300, 'estimated_vehicles': 100, 'priority_score': 75, 'estimated_total_revenue': 25000},
        {'name': 'Parking C', 'lat': 35.4550, 'lon': -97.5000, 'estimated_vehicles': 300, 'priority_score': 90, 'estimated_total_revenue': 60000},
        {'name': 'Golf Course D', 'lat': 35.4900, 'lon': -97.4800, 'estimated_vehicles': 120, 'priority_score': 70, 'estimated_total_revenue': 35000},
        {'name': 'Hospital E', 'lat': 35.4600, 'lon': -97.5400, 'estimated_vehicles': 250, 'priority_score': 80, 'estimated_total_revenue': 45000},
    ]

    optimizer = RouteOptimizer()
    route = optimizer.optimize_route(locations)

    print("Optimized Route:")
    print(f"Total Distance: {route.total_distance_miles} miles")
    print(f"Drive Time: {route.drive_time_hours} hours")
    print(f"Total Vehicles: {route.total_vehicles}")
    print(f"Est. Revenue: ${route.estimated_revenue:,.0f}")
    print(f"Google Maps: {route.google_maps_url}")
    print("\nRoute Order:")
    for loc in route.locations:
        print(f"  {loc['stop_number']}. {loc['name']} ({loc['priority_score']} pts)")


if __name__ == '__main__':
    test_route_optimizer()
