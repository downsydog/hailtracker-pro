"""
Storm Prediction Center - FREE convective outlooks and watches
https://www.spc.noaa.gov/

Provides:
- Convective Outlooks (Day 1-8 severe weather risk)
- Tornado and Severe Thunderstorm Watches
- Mesoscale Discussions
- Storm Reports
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
import re

logger = logging.getLogger(__name__)


class StormPredictionCenter:
    """
    Storm Prediction Center data client.

    The SPC is the authoritative source for severe weather
    forecasting in the United States. All data is FREE.
    """

    SPC_URL = "https://www.spc.noaa.gov"
    NWS_API = "https://api.weather.gov"
    IEM_URL = "https://mesonet.agron.iastate.edu"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTrackerPro/2.0',
            'Accept': 'application/geo+json, application/json'
        })

    def get_current_watches(self) -> List[Dict]:
        """
        Get active tornado and severe thunderstorm watches.

        Returns:
            List of watch dictionaries with parsed info
        """
        url = f"{self.NWS_API}/alerts/active"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            watches = []

            for feature in data.get('features', []):
                props = feature.get('properties', {})
                event = props.get('event', '')

                # Only include watches (not warnings)
                if 'Watch' not in event:
                    continue

                if 'Tornado' in event or 'Severe Thunderstorm' in event:
                    watch_info = {
                        'id': props.get('id'),
                        'event': event,
                        'headline': props.get('headline'),
                        'severity': props.get('severity'),
                        'areas': props.get('areaDesc'),
                        'effective': props.get('effective'),
                        'onset': props.get('onset'),
                        'expires': props.get('expires'),
                        'ends': props.get('ends'),
                        'sender': props.get('senderName'),
                        'description': props.get('description'),
                        'instruction': props.get('instruction'),
                        'geometry': feature.get('geometry'),
                        'is_pds': self._is_pds_watch(props),
                    }
                    watches.append(watch_info)

            return watches

        except requests.RequestException as e:
            logger.error(f"SPC watches error: {e}")
            return []

    def _is_pds_watch(self, props: Dict) -> bool:
        """Check if watch is a Particularly Dangerous Situation (PDS)."""
        description = props.get('description', '').upper()
        headline = props.get('headline', '').upper()
        return 'PDS' in description or 'PARTICULARLY DANGEROUS' in headline

    def get_tornado_watches(self) -> List[Dict]:
        """Get only tornado watches."""
        watches = self.get_current_watches()
        return [w for w in watches if 'Tornado' in w.get('event', '')]

    def get_severe_thunderstorm_watches(self) -> List[Dict]:
        """Get only severe thunderstorm watches."""
        watches = self.get_current_watches()
        return [w for w in watches if 'Severe Thunderstorm' in w.get('event', '')]

    def get_convective_outlook_day1(self) -> Dict:
        """
        Get Day 1 convective outlook (categorical risk areas).

        Risk levels:
        - TSTM: General thunderstorm risk
        - MRGL: Marginal risk (1)
        - SLGT: Slight risk (2)
        - ENH: Enhanced risk (3)
        - MDT: Moderate risk (4)
        - HIGH: High risk (5)

        Returns:
            GeoJSON with risk areas
        """
        url = f"{self.SPC_URL}/products/outlook/day1otlk_cat.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC Day 1 outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_convective_outlook_day2(self) -> Dict:
        """Get Day 2 convective outlook."""
        url = f"{self.SPC_URL}/products/outlook/day2otlk_cat.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC Day 2 outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_convective_outlook_day3(self) -> Dict:
        """Get Day 3 convective outlook."""
        url = f"{self.SPC_URL}/products/outlook/day3otlk_cat.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC Day 3 outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_hail_outlook_day1(self) -> Dict:
        """
        Get Day 1 hail probability outlook.

        Returns areas with probability of 1"+ hail within 25 miles.
        """
        url = f"{self.SPC_URL}/products/outlook/day1otlk_hail.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC hail outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_tornado_outlook_day1(self) -> Dict:
        """
        Get Day 1 tornado probability outlook.

        Returns areas with probability of tornado within 25 miles.
        """
        url = f"{self.SPC_URL}/products/outlook/day1otlk_torn.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC tornado outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_wind_outlook_day1(self) -> Dict:
        """
        Get Day 1 damaging wind probability outlook.

        Returns areas with probability of 58+ mph wind within 25 miles.
        """
        url = f"{self.SPC_URL}/products/outlook/day1otlk_wind.lyr.geojson"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"SPC wind outlook error: {e}")
            return {'type': 'FeatureCollection', 'features': []}

    def get_mesoscale_discussions(self, hours: int = 24) -> List[Dict]:
        """
        Get recent mesoscale discussions from IEM archive.

        Args:
            hours: How many hours back to search

        Returns:
            List of MCD features
        """
        url = f"{self.IEM_URL}/cgi-bin/request/gis/spc_mcd.py"
        params = {
            'recent': hours * 3600,
            'fmt': 'geojson'
        }

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get('features', [])
        except requests.RequestException as e:
            logger.error(f"SPC MCD error: {e}")
            return []

    def get_spc_storm_reports_today(self) -> Dict:
        """
        Get today's preliminary storm reports from SPC.

        Returns:
            Dictionary with tornado, hail, and wind reports
        """
        today = datetime.utcnow().strftime('%y%m%d')
        base_url = f"{self.SPC_URL}/climo/reports/{today}"

        reports = {
            'tornado': [],
            'hail': [],
            'wind': [],
            'date': today
        }

        # SPC provides CSV files for each report type
        report_types = [
            ('tornado', f"{base_url}_rpts_filtered_torn.csv"),
            ('hail', f"{base_url}_rpts_filtered_hail.csv"),
            ('wind', f"{base_url}_rpts_filtered_wind.csv"),
        ]

        for report_type, url in report_types:
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    # Parse CSV
                    lines = response.text.strip().split('\n')
                    if len(lines) > 1:
                        # First line is header
                        for line in lines[1:]:
                            parts = line.split(',')
                            if len(parts) >= 7:
                                reports[report_type].append({
                                    'time': parts[0],
                                    'magnitude': parts[1] if parts[1] else None,
                                    'location': parts[2],
                                    'county': parts[3],
                                    'state': parts[4],
                                    'lat': float(parts[5]) if parts[5] else None,
                                    'lon': float(parts[6]) if parts[6] else None,
                                    'comments': parts[7] if len(parts) > 7 else '',
                                })
            except Exception as e:
                logger.debug(f"SPC {report_type} reports error: {e}")

        return reports

    def get_risk_level_for_point(self, lat: float, lon: float) -> Dict:
        """
        Get current severe weather risk level for a specific point.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Dictionary with risk levels for categorical, hail, tornado, wind
        """
        # This would require point-in-polygon testing against outlook areas
        # For now, return the outlook data for manual checking
        return {
            'categorical': self.get_convective_outlook_day1(),
            'hail': self.get_hail_outlook_day1(),
            'tornado': self.get_tornado_outlook_day1(),
            'wind': self.get_wind_outlook_day1(),
            'point': {'lat': lat, 'lon': lon}
        }

    def get_all_outlooks(self) -> Dict:
        """
        Get all current outlooks.

        Returns:
            Dictionary with all outlook products
        """
        return {
            'day1_categorical': self.get_convective_outlook_day1(),
            'day1_hail': self.get_hail_outlook_day1(),
            'day1_tornado': self.get_tornado_outlook_day1(),
            'day1_wind': self.get_wind_outlook_day1(),
            'day2_categorical': self.get_convective_outlook_day2(),
            'day3_categorical': self.get_convective_outlook_day3(),
            'timestamp': datetime.utcnow().isoformat()
        }

    def parse_outlook_risk(self, outlook: Dict) -> List[Dict]:
        """
        Parse outlook GeoJSON into risk area list.

        Args:
            outlook: GeoJSON outlook data

        Returns:
            List of risk areas with level and geometry
        """
        risk_areas = []

        for feature in outlook.get('features', []):
            props = feature.get('properties', {})
            geometry = feature.get('geometry')

            # Get risk level
            label = props.get('LABEL', props.get('LABEL2', ''))
            dn = props.get('DN', 0)  # Numeric risk level

            risk_areas.append({
                'label': label,
                'level': dn,
                'stroke': props.get('stroke'),
                'fill': props.get('fill'),
                'geometry': geometry,
            })

        return risk_areas


# Test function
def test_spc():
    """Test Storm Prediction Center API."""
    print("Testing Storm Prediction Center API...")

    spc = StormPredictionCenter()

    # Get current watches
    print("\n[Current Watches]")
    watches = spc.get_current_watches()
    print(f"Found {len(watches)} active watches")

    for watch in watches[:5]:
        pds = " [PDS]" if watch.get('is_pds') else ""
        print(f"  - {watch['event']}{pds}")
        print(f"    Areas: {watch['areas'][:80]}...")

    # Get Day 1 outlook
    print("\n[Day 1 Convective Outlook]")
    outlook = spc.get_convective_outlook_day1()
    features = outlook.get('features', [])
    print(f"Found {len(features)} risk areas")

    risk_areas = spc.parse_outlook_risk(outlook)
    for area in risk_areas:
        print(f"  - {area['label']} (level {area['level']})")

    # Get Day 1 hail outlook
    print("\n[Day 1 Hail Outlook]")
    hail_outlook = spc.get_hail_outlook_day1()
    hail_features = hail_outlook.get('features', [])
    print(f"Found {len(hail_features)} hail probability areas")

    # Get tornado watches
    print("\n[Tornado Watches]")
    tor_watches = spc.get_tornado_watches()
    print(f"Found {len(tor_watches)} tornado watches")

    # Get mesoscale discussions
    print("\n[Mesoscale Discussions - Last 24h]")
    mcds = spc.get_mesoscale_discussions(24)
    print(f"Found {len(mcds)} mesoscale discussions")

    print("\nSPC test complete!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_spc()
