"""
Iowa Environmental Mesonet - FREE Local Storm Reports
https://mesonet.agron.iastate.edu/

Provides real-time Local Storm Reports (LSRs) including:
- Hail reports with measured sizes
- Tornado reports
- Damaging wind reports
- Flash flood reports

Data is collected from NWS offices across the country.
"""

import requests
import csv
from io import StringIO
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class IowaMesonet:
    """
    Iowa Environmental Mesonet LSR client.

    The IEM collects and archives Local Storm Reports from all
    NWS Weather Forecast Offices. This is the most comprehensive
    free source for verified hail reports with actual measured sizes.
    """

    BASE_URL = "https://mesonet.agron.iastate.edu"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailTrackerPro/2.0'
        })

    def get_recent_lsrs(
        self,
        hours: int = 24,
        wfo: str = 'ALL',
        lsr_type: str = None
    ) -> List[Dict]:
        """
        Get recent Local Storm Reports.

        Args:
            hours: How many hours back to search (max ~168 for recent)
            wfo: Weather Forecast Office code or 'ALL' for nationwide
            lsr_type: Filter by type ('H' for hail, 'T' for tornado, etc.)

        Returns:
            List of LSR dictionaries
        """
        seconds = hours * 3600
        url = f"{self.BASE_URL}/cgi-bin/request/gis/lsr.py"
        params = {
            'wfo': wfo,
            'recent': seconds,
            'fmt': 'csv'
        }

        if lsr_type:
            params['type'] = lsr_type

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            reader = csv.DictReader(StringIO(response.text))
            return list(reader)
        except requests.RequestException as e:
            logger.error(f"IEM LSR request error: {e}")
            return []
        except csv.Error as e:
            logger.error(f"IEM CSV parse error: {e}")
            return []

    def get_lsrs_by_state(self, state: str, hours: int = 24) -> List[Dict]:
        """
        Get LSRs for a specific state.

        Args:
            state: Two-letter state code (e.g., 'OK', 'TX')
            hours: How many hours back to search

        Returns:
            List of LSR dictionaries
        """
        seconds = hours * 3600
        url = f"{self.BASE_URL}/cgi-bin/request/gis/lsr.py"
        params = {
            'state': state.upper(),
            'recent': seconds,
            'fmt': 'csv'
        }

        try:
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()

            reader = csv.DictReader(StringIO(response.text))
            return list(reader)
        except requests.RequestException as e:
            logger.error(f"IEM state LSR error: {e}")
            return []

    def get_lsrs_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        state: str = None
    ) -> List[Dict]:
        """
        Get LSRs for a specific date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            state: Optional state filter

        Returns:
            List of LSR dictionaries
        """
        url = f"{self.BASE_URL}/cgi-bin/request/gis/lsr.py"
        params = {
            'sts': start_date.strftime('%Y-%m-%d'),
            'ets': end_date.strftime('%Y-%m-%d'),
            'fmt': 'csv'
        }

        if state:
            params['state'] = state.upper()

        try:
            response = self.session.get(url, params=params, timeout=120)
            response.raise_for_status()

            reader = csv.DictReader(StringIO(response.text))
            return list(reader)
        except requests.RequestException as e:
            logger.error(f"IEM date range LSR error: {e}")
            return []

    def get_hail_reports(
        self,
        hours: int = 24,
        state: str = None,
        min_size: float = 0.0
    ) -> List[Dict]:
        """
        Get recent hail reports with sizes.

        Args:
            hours: How many hours back to search
            state: Optional state filter
            min_size: Minimum hail size in inches

        Returns:
            List of hail report dictionaries with parsed data
        """
        if state:
            reports = self.get_lsrs_by_state(state, hours)
        else:
            reports = self.get_recent_lsrs(hours)

        hail_reports = []

        for r in reports:
            type_text = r.get('typetext', '').upper()

            # Check if it's a hail report
            if 'HAIL' not in type_text:
                continue

            try:
                # Parse magnitude (hail size)
                magnitude = r.get('magnitude', '')
                hail_size = None
                if magnitude:
                    try:
                        hail_size = float(magnitude)
                    except ValueError:
                        # Try to parse size from typetext or remarks
                        pass

                # Skip if below minimum size
                if hail_size is not None and hail_size < min_size:
                    continue

                # Parse coordinates
                lat = float(r.get('lat', 0))
                lon = float(r.get('lon', 0))

                if lat == 0 and lon == 0:
                    continue

                hail_reports.append({
                    'lat': lat,
                    'lon': lon,
                    'city': r.get('city', ''),
                    'county': r.get('county', ''),
                    'state': r.get('state', ''),
                    'hail_size_inches': hail_size,
                    'remarks': r.get('remark', ''),
                    'valid_time': r.get('valid', ''),
                    'valid_utc': r.get('valid_utc', ''),
                    'source': r.get('source', ''),
                    'wfo': r.get('wfo', ''),
                    'type': type_text,
                    'type_code': r.get('type', ''),
                })

            except (ValueError, TypeError) as e:
                logger.debug(f"Error parsing hail report: {e}")
                continue

        # Sort by size (largest first), then by time
        hail_reports.sort(
            key=lambda x: (x.get('hail_size_inches') or 0, x.get('valid_time', '')),
            reverse=True
        )

        return hail_reports

    def get_tornado_reports(self, hours: int = 24, state: str = None) -> List[Dict]:
        """
        Get recent tornado reports.

        Args:
            hours: How many hours back to search
            state: Optional state filter

        Returns:
            List of tornado report dictionaries
        """
        if state:
            reports = self.get_lsrs_by_state(state, hours)
        else:
            reports = self.get_recent_lsrs(hours)

        tornado_reports = []

        for r in reports:
            type_text = r.get('typetext', '').upper()

            if 'TORNADO' not in type_text:
                continue

            try:
                lat = float(r.get('lat', 0))
                lon = float(r.get('lon', 0))

                if lat == 0 and lon == 0:
                    continue

                tornado_reports.append({
                    'lat': lat,
                    'lon': lon,
                    'city': r.get('city', ''),
                    'county': r.get('county', ''),
                    'state': r.get('state', ''),
                    'remarks': r.get('remark', ''),
                    'valid_time': r.get('valid', ''),
                    'valid_utc': r.get('valid_utc', ''),
                    'source': r.get('source', ''),
                    'wfo': r.get('wfo', ''),
                    'type': type_text,
                })

            except (ValueError, TypeError):
                continue

        return tornado_reports

    def get_wind_reports(
        self,
        hours: int = 24,
        state: str = None,
        min_speed: int = 58
    ) -> List[Dict]:
        """
        Get recent damaging wind reports.

        Args:
            hours: How many hours back to search
            state: Optional state filter
            min_speed: Minimum wind speed in mph (58 = severe threshold)

        Returns:
            List of wind report dictionaries
        """
        if state:
            reports = self.get_lsrs_by_state(state, hours)
        else:
            reports = self.get_recent_lsrs(hours)

        wind_reports = []

        for r in reports:
            type_text = r.get('typetext', '').upper()

            if 'WIND' not in type_text and 'GUST' not in type_text:
                continue

            try:
                # Parse wind speed from magnitude
                magnitude = r.get('magnitude', '')
                wind_speed = None
                if magnitude:
                    try:
                        wind_speed = int(float(magnitude))
                    except ValueError:
                        pass

                # Skip if below minimum
                if wind_speed is not None and wind_speed < min_speed:
                    continue

                lat = float(r.get('lat', 0))
                lon = float(r.get('lon', 0))

                if lat == 0 and lon == 0:
                    continue

                wind_reports.append({
                    'lat': lat,
                    'lon': lon,
                    'city': r.get('city', ''),
                    'county': r.get('county', ''),
                    'state': r.get('state', ''),
                    'wind_speed_mph': wind_speed,
                    'remarks': r.get('remark', ''),
                    'valid_time': r.get('valid', ''),
                    'valid_utc': r.get('valid_utc', ''),
                    'source': r.get('source', ''),
                    'wfo': r.get('wfo', ''),
                    'type': type_text,
                })

            except (ValueError, TypeError):
                continue

        # Sort by wind speed (highest first)
        wind_reports.sort(
            key=lambda x: x.get('wind_speed_mph') or 0,
            reverse=True
        )

        return wind_reports

    def get_all_severe_reports(self, hours: int = 24, state: str = None) -> Dict:
        """
        Get all severe weather reports organized by type.

        Args:
            hours: How many hours back to search
            state: Optional state filter

        Returns:
            Dictionary with hail, tornado, and wind reports
        """
        return {
            'hail': self.get_hail_reports(hours, state),
            'tornado': self.get_tornado_reports(hours, state),
            'wind': self.get_wind_reports(hours, state),
            'query_hours': hours,
            'query_state': state,
            'timestamp': datetime.utcnow().isoformat()
        }

    def get_hail_stats(self, hours: int = 24) -> Dict:
        """
        Get hail report statistics.

        Args:
            hours: How many hours back to analyze

        Returns:
            Statistics dictionary
        """
        reports = self.get_hail_reports(hours)

        if not reports:
            return {
                'total_reports': 0,
                'hours_searched': hours,
                'max_size': None,
                'avg_size': None,
                'states_affected': [],
                'by_state': {}
            }

        sizes = [r['hail_size_inches'] for r in reports if r['hail_size_inches']]
        states = {}

        for r in reports:
            state = r.get('state', 'Unknown')
            if state not in states:
                states[state] = []
            states[state].append(r)

        return {
            'total_reports': len(reports),
            'hours_searched': hours,
            'max_size': max(sizes) if sizes else None,
            'avg_size': sum(sizes) / len(sizes) if sizes else None,
            'min_size': min(sizes) if sizes else None,
            'states_affected': list(states.keys()),
            'reports_by_state': {k: len(v) for k, v in states.items()},
            'largest_reports': reports[:5],  # Top 5 by size
        }


# Test function
def test_iowa_mesonet():
    """Test Iowa Mesonet LSR API."""
    print("Testing Iowa Mesonet LSR API...")

    iem = IowaMesonet()

    # Get recent hail reports
    print("\n[Recent Hail Reports - Last 24 hours]")
    hail = iem.get_hail_reports(hours=24)
    print(f"Found {len(hail)} hail reports")

    for report in hail[:10]:
        size = report['hail_size_inches']
        size_str = f"{size}\"" if size else "Unknown size"
        print(f"  - {report['city']}, {report['state']}: {size_str}")
        print(f"    Time: {report['valid_time']}")

    # Get hail stats
    print("\n[Hail Statistics]")
    stats = iem.get_hail_stats(hours=24)
    print(f"Total reports: {stats['total_reports']}")
    print(f"Max size: {stats['max_size']}\"" if stats['max_size'] else "No reports")
    print(f"States affected: {', '.join(stats['states_affected'])}")

    # Get tornado reports
    print("\n[Tornado Reports - Last 24 hours]")
    tornadoes = iem.get_tornado_reports(hours=24)
    print(f"Found {len(tornadoes)} tornado reports")

    # Get wind reports
    print("\n[Damaging Wind Reports - Last 24 hours]")
    wind = iem.get_wind_reports(hours=24)
    print(f"Found {len(wind)} wind reports >= 58 mph")

    print("\nIowa Mesonet test complete!")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_iowa_mesonet()
