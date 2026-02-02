"""
NWS Weather Alerts API - 100% FREE, no API key needed
https://api.weather.gov/alerts

Provides real-time severe weather alerts including:
- Severe Thunderstorm Warnings (with hail size)
- Tornado Warnings
- Flash Flood Warnings
- Special Weather Statements
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)


class NWSAlerts:
    """
    National Weather Service Alerts API client.

    Features:
    - Get all active alerts nationwide
    - Filter by event type (Severe Thunderstorm, Tornado, etc.)
    - Filter by state or specific location
    - Parse hail size from alert descriptions
    """

    BASE_URL = "https://api.weather.gov"

    def __init__(self):
        self.headers = {
            'User-Agent': 'HailTrackerPro/2.0 (hailtracker@example.com)',
            'Accept': 'application/geo+json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def get_active_alerts(self, event_type: str = None, severity: str = None) -> List[Dict]:
        """
        Get all active weather alerts, optionally filtered.

        Args:
            event_type: Filter by event (e.g., 'Severe Thunderstorm Warning')
            severity: Filter by severity (Extreme, Severe, Moderate, Minor)

        Returns:
            List of alert features from GeoJSON response
        """
        url = f"{self.BASE_URL}/alerts/active"
        params = {}

        if event_type:
            params['event'] = event_type
        if severity:
            params['severity'] = severity

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get('features', [])
        except requests.RequestException as e:
            logger.error(f"NWS API error: {e}")
            return []

    def get_severe_thunderstorm_warnings(self) -> List[Dict]:
        """Get active severe thunderstorm warnings (includes hail info)."""
        return self.get_active_alerts(event_type='Severe Thunderstorm Warning')

    def get_tornado_warnings(self) -> List[Dict]:
        """Get active tornado warnings."""
        return self.get_active_alerts(event_type='Tornado Warning')

    def get_tornado_watches(self) -> List[Dict]:
        """Get active tornado watches."""
        return self.get_active_alerts(event_type='Tornado Watch')

    def get_severe_thunderstorm_watches(self) -> List[Dict]:
        """Get active severe thunderstorm watches."""
        return self.get_active_alerts(event_type='Severe Thunderstorm Watch')

    def get_alerts_for_point(self, lat: float, lon: float) -> List[Dict]:
        """
        Get alerts for a specific location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            List of alerts affecting this point
        """
        url = f"{self.BASE_URL}/alerts/active"
        params = {'point': f'{lat},{lon}'}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('features', [])
        except requests.RequestException as e:
            logger.error(f"NWS point alerts error: {e}")
            return []

    def get_alerts_for_state(self, state: str) -> List[Dict]:
        """
        Get alerts for a state.

        Args:
            state: Two-letter state code (e.g., 'OK', 'TX')

        Returns:
            List of alerts for the state
        """
        url = f"{self.BASE_URL}/alerts/active/area/{state.upper()}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('features', [])
        except requests.RequestException as e:
            logger.error(f"NWS state alerts error: {e}")
            return []

    def get_alerts_for_zone(self, zone_id: str) -> List[Dict]:
        """
        Get alerts for a specific NWS zone.

        Args:
            zone_id: NWS zone ID (e.g., 'OKC001')

        Returns:
            List of alerts for the zone
        """
        url = f"{self.BASE_URL}/alerts/active/zone/{zone_id}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json().get('features', [])
        except requests.RequestException as e:
            logger.error(f"NWS zone alerts error: {e}")
            return []

    def parse_hail_info(self, alert: Dict) -> Dict:
        """
        Extract hail and wind information from alert description.

        NWS includes hail size in descriptions like:
        - "HAIL...1.75 INCHES"
        - "QUARTER SIZE HAIL"
        - "GOLF BALL SIZE HAIL"

        Args:
            alert: Alert feature from API

        Returns:
            Parsed alert info with hail_size_inches, wind_mph, etc.
        """
        props = alert.get('properties', {})
        description = props.get('description', '')
        parameters = props.get('parameters', {})

        # Try to get hail size from parameters first (more reliable)
        hail_size = None
        wind_speed = None

        # NWS sometimes includes maxHailSize in parameters
        if 'maxHailSize' in parameters:
            try:
                hail_size = float(parameters['maxHailSize'][0])
            except (ValueError, IndexError, TypeError):
                pass

        if 'maxWindGust' in parameters:
            try:
                wind_speed = int(parameters['maxWindGust'][0])
            except (ValueError, IndexError, TypeError):
                pass

        # Fall back to parsing description
        if hail_size is None:
            # Pattern: "HAIL...1.75 INCHES" or "HAIL...2 INCH"
            hail_match = re.search(
                r'HAIL[.\s]*(\d+\.?\d*)\s*INCH',
                description,
                re.IGNORECASE
            )
            if hail_match:
                hail_size = float(hail_match.group(1))
            else:
                # Try common size descriptions
                size_map = {
                    'PEA': 0.25,
                    'MARBLE': 0.5,
                    'DIME': 0.75,
                    'PENNY': 0.75,
                    'NICKEL': 0.88,
                    'QUARTER': 1.0,
                    'HALF DOLLAR': 1.25,
                    'PING PONG': 1.5,
                    'GOLF BALL': 1.75,
                    'HEN EGG': 2.0,
                    'TENNIS BALL': 2.5,
                    'BASEBALL': 2.75,
                    'SOFTBALL': 4.0,
                    'GRAPEFRUIT': 4.5,
                }

                desc_upper = description.upper()
                for size_name, size_inches in size_map.items():
                    if size_name in desc_upper:
                        hail_size = size_inches
                        break

        if wind_speed is None:
            # Pattern: "WIND...70 MPH" or "WINDS TO 80 MPH"
            wind_match = re.search(
                r'WIND[S]?[.\s]*(?:TO\s+)?(\d+)\s*MPH',
                description,
                re.IGNORECASE
            )
            if wind_match:
                wind_speed = int(wind_match.group(1))

        # Extract affected areas from geometry
        geometry = alert.get('geometry')
        affected_polygon = None
        if geometry and geometry.get('type') == 'Polygon':
            affected_polygon = geometry.get('coordinates')

        return {
            'id': props.get('id'),
            'event': props.get('event'),
            'headline': props.get('headline'),
            'severity': props.get('severity'),
            'certainty': props.get('certainty'),
            'urgency': props.get('urgency'),
            'hail_size_inches': hail_size,
            'wind_mph': wind_speed,
            'effective': props.get('effective'),
            'onset': props.get('onset'),
            'expires': props.get('expires'),
            'ends': props.get('ends'),
            'sender': props.get('senderName'),
            'areas': props.get('areaDesc'),
            'description': description,
            'instruction': props.get('instruction'),
            'geometry': geometry,
            'polygon': affected_polygon,
            'references': props.get('references', []),
        }

    def get_hail_alerts(self, min_size: float = 0.0) -> List[Dict]:
        """
        Get all active alerts that mention hail.

        Args:
            min_size: Minimum hail size in inches to include

        Returns:
            List of parsed alerts with hail information
        """
        # Get severe thunderstorm warnings (most likely to have hail)
        alerts = self.get_severe_thunderstorm_warnings()

        # Also check special weather statements
        alerts.extend(self.get_active_alerts(event_type='Special Weather Statement'))

        hail_alerts = []
        seen_ids = set()

        for alert in alerts:
            parsed = self.parse_hail_info(alert)
            alert_id = parsed.get('id')

            # Skip duplicates
            if alert_id in seen_ids:
                continue
            seen_ids.add(alert_id)

            # Include if hail mentioned
            if parsed['hail_size_inches'] is not None:
                if parsed['hail_size_inches'] >= min_size:
                    hail_alerts.append(parsed)
            elif 'HAIL' in parsed.get('description', '').upper():
                # Include even without parsed size if hail is mentioned
                hail_alerts.append(parsed)

        # Sort by hail size (largest first)
        hail_alerts.sort(
            key=lambda x: x.get('hail_size_inches') or 0,
            reverse=True
        )

        return hail_alerts

    def get_all_severe_alerts(self) -> Dict[str, List[Dict]]:
        """
        Get all severe weather alerts organized by type.

        Returns:
            Dictionary with keys: tornado_warnings, tornado_watches,
            severe_thunderstorm_warnings, severe_thunderstorm_watches
        """
        return {
            'tornado_warnings': [
                self.parse_hail_info(a) for a in self.get_tornado_warnings()
            ],
            'tornado_watches': [
                self.parse_hail_info(a) for a in self.get_tornado_watches()
            ],
            'severe_thunderstorm_warnings': [
                self.parse_hail_info(a) for a in self.get_severe_thunderstorm_warnings()
            ],
            'severe_thunderstorm_watches': [
                self.parse_hail_info(a) for a in self.get_severe_thunderstorm_watches()
            ],
        }


# Test function
def test_nws_alerts():
    """Test NWS Alerts API."""
    print("Testing NWS Alerts API...")

    nws = NWSAlerts()

    # Get all hail alerts
    print("\n[Hail Alerts]")
    hail_alerts = nws.get_hail_alerts()
    print(f"Found {len(hail_alerts)} hail alerts")

    for alert in hail_alerts[:5]:
        print(f"  - {alert['headline']}")
        if alert['hail_size_inches']:
            print(f"    Hail: {alert['hail_size_inches']}\"")
        if alert['wind_mph']:
            print(f"    Wind: {alert['wind_mph']} mph")

    # Get alerts for Texas
    print("\n[Texas Alerts]")
    tx_alerts = nws.get_alerts_for_state('TX')
    print(f"Found {len(tx_alerts)} alerts in Texas")

    # Get all severe
    print("\n[All Severe Alerts]")
    all_severe = nws.get_all_severe_alerts()
    for alert_type, alerts in all_severe.items():
        print(f"  {alert_type}: {len(alerts)}")

    print("\nNWS Alerts test complete!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_nws_alerts()
