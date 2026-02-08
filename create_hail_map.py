"""
Create Interactive Map Visualization of Hail Events

Generates an HTML map showing all processed hail events with:
- Color-coded markers by severity
- Popup details for each event
- Radar coverage circles
- Storm tracks
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np

# Check and install dependencies
print("Checking dependencies...")

try:
    import folium
    from folium import plugins
    print("  folium: OK")
except ImportError:
    print("  folium: Installing...")
    os.system("pip install folium")
    import folium
    from folium import plugins

try:
    import nexradaws
    print("  nexradaws: OK")
except ImportError:
    print("  nexradaws: NOT FOUND")
    sys.exit(1)

try:
    import pyart
    print("  pyart: OK")
except ImportError:
    print("  pyart: NOT FOUND")
    sys.exit(1)

print()

# Local imports
from src.ml.hail_classifier import HailClassifier
from src.radar.radar_network import RadarNetwork


class HailEventMapper:
    """Create map visualizations of hail events."""

    def __init__(self):
        self.conn = nexradaws.NexradAwsInterface()
        self.classifier = HailClassifier(simulation_mode=True)
        self.radar_network = RadarNetwork()
        self.temp_dir = tempfile.mkdtemp()
        self.events_data = []

    def fetch_and_analyze(self, event: Dict) -> Optional[Dict]:
        """Fetch radar data and analyze for hail."""
        try:
            start_time = event['date'] - timedelta(minutes=10)
            end_time = event['date'] + timedelta(minutes=10)

            scans = self.conn.get_avail_scans_in_range(start_time, end_time, event['radar'])

            if not scans:
                return None

            def time_diff(s):
                st = s.scan_time
                if st.tzinfo is not None:
                    st = st.replace(tzinfo=None)
                return abs((st - event['date']).total_seconds())

            closest = min(scans, key=time_diff)
            results = self.conn.download(closest, self.temp_dir)

            if not results.success:
                return None

            filepath = results.success[0].filepath
            radar = pyart.io.read_nexrad_archive(filepath)

            # Get radar location
            radar_lat = radar.latitude['data'][0]
            radar_lon = radar.longitude['data'][0]

            # Find storm
            storm_data = self._find_storm(radar)

            if storm_data['max_reflectivity'] < 40:
                return None

            # Calculate MESH
            mesh_data = self._calculate_mesh(radar)

            # ML Classification
            hail_event = self.classifier.classify(
                lat=storm_data.get('storm_lat', radar_lat),
                lon=storm_data.get('storm_lon', radar_lon),
                timestamp=event['date'],
                radar_data={
                    'max_reflectivity': storm_data['max_reflectivity'],
                    'mesh': mesh_data['mesh_mm'],
                    'posh': mesh_data['posh'],
                    'zdr_min': storm_data.get('zdr_min', 0.5),
                    'cc_min': storm_data.get('cc_min', 0.95),
                    'vil': mesh_data['shi'] / 4 if mesh_data['shi'] else 20
                },
                environmental_data={
                    'freezing_level': 3.5,
                    'cape': 2500,
                    'shear_0_6km': 30,
                    'srh': 250
                }
            )

            return {
                'event': event,
                'radar_lat': float(radar_lat),
                'radar_lon': float(radar_lon),
                'storm_lat': storm_data.get('storm_lat', float(radar_lat)),
                'storm_lon': storm_data.get('storm_lon', float(radar_lon)),
                'max_reflectivity': storm_data['max_reflectivity'],
                'mesh_mm': mesh_data['mesh_mm'],
                'posh': mesh_data['posh'],
                'zdr_min': storm_data.get('zdr_min'),
                'cc_min': storm_data.get('cc_min'),
                'hail_detected': hail_event.hail_detected,
                'probability': hail_event.hail_probability,
                'size_mm': hail_event.estimated_size_mm,
                'severity': hail_event.severity,
                'pdr_score': hail_event.pdr_opportunity_score
            }

        except Exception as e:
            print(f"    Error: {e}")
            return None

    def _find_storm(self, radar) -> Dict:
        """Find strongest storm in radar scan."""
        try:
            for sweep_idx in [0, 1, 2]:
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            max_val = np.max(data)
                            if max_val < 40:
                                continue

                            max_idx = np.unravel_index(np.argmax(data), data.shape)
                            az_idx, rng_idx = max_idx

                            sweep_slice = radar.get_slice(sweep_idx)
                            azimuths = radar.azimuth['data'][sweep_slice]
                            ranges = radar.range['data'] / 1000.0

                            az = azimuths[az_idx]
                            rng = ranges[rng_idx]

                            radar_lat = radar.latitude['data'][0]
                            radar_lon = radar.longitude['data'][0]
                            storm_lat, storm_lon = self._az_range_to_latlon(
                                radar_lat, radar_lon, az, rng
                            )

                            # Area analysis
                            search_radius = 50
                            az_min = max(0, az_idx - search_radius)
                            az_max = min(data.shape[0], az_idx + search_radius)
                            rng_min = max(0, rng_idx - search_radius)
                            rng_max = min(data.shape[1], rng_idx + search_radius)

                            result = {
                                'max_reflectivity': float(max_val),
                                'storm_lat': storm_lat,
                                'storm_lon': storm_lon
                            }

                            # ZDR
                            for zdr_field in ['differential_reflectivity', 'ZDR']:
                                if zdr_field in radar.fields:
                                    zdr_data = radar.get_field(sweep_idx, zdr_field)
                                    zdr_area = zdr_data[az_min:az_max, rng_min:rng_max]
                                    if zdr_area.count() > 0:
                                        result['zdr_min'] = float(np.min(zdr_area))
                                    break

                            # CC
                            for cc_field in ['cross_correlation_ratio', 'RHOHV']:
                                if cc_field in radar.fields:
                                    cc_data = radar.get_field(sweep_idx, cc_field)
                                    cc_area = cc_data[az_min:az_max, rng_min:rng_max]
                                    if cc_area.count() > 0:
                                        result['cc_min'] = float(np.min(cc_area))
                                    break

                            return result

            return {'max_reflectivity': 0}
        except:
            return {'max_reflectivity': 0}

    def _calculate_mesh(self, radar) -> Dict:
        """Calculate MESH from vertical profile."""
        try:
            max_refs = []
            heights = []

            for sweep_idx in range(min(radar.nsweeps, 14)):
                for field_name in ['reflectivity', 'REF', 'DBZ']:
                    if field_name in radar.fields:
                        data = radar.get_field(sweep_idx, field_name)
                        if data.count() > 0:
                            max_ref = float(np.max(data))
                            sweep_slice = radar.get_slice(sweep_idx)
                            elev = np.mean(radar.elevation['data'][sweep_slice])
                            height = 50 * np.tan(np.radians(elev)) + (50**2) / (2 * 8500)
                            max_refs.append(max_ref)
                            heights.append(height)
                        break

            if not max_refs:
                return {'mesh_mm': 0, 'shi': 0, 'posh': 0}

            freezing_level = 3.5
            above_freezing = [(h, r) for h, r in zip(heights, max_refs) if h > freezing_level]

            if above_freezing:
                max_above = max(r for h, r in above_freezing)
                if max_above >= 40:
                    mesh_mm = 2.54 * np.exp(0.1 * (max_above - 40))
                    mesh_mm = min(mesh_mm, 120)
                else:
                    mesh_mm = 0
            else:
                mesh_mm = 0

            shi = mesh_mm * 4 if mesh_mm > 0 else 0
            posh = min(99, 50 + mesh_mm) if mesh_mm >= 25 else (30 + mesh_mm if mesh_mm >= 10 else mesh_mm * 2)

            return {'mesh_mm': round(mesh_mm, 1), 'shi': round(shi, 0), 'posh': round(posh, 0)}
        except:
            return {'mesh_mm': 0, 'shi': 0, 'posh': 0}

    def _az_range_to_latlon(self, radar_lat, radar_lon, azimuth, range_km):
        """Convert radar azimuth/range to lat/lon."""
        import math
        R = 6371.0
        bearing = math.radians(azimuth)
        lat1 = math.radians(radar_lat)
        lon1 = math.radians(radar_lon)

        lat2 = math.asin(
            math.sin(lat1) * math.cos(range_km / R) +
            math.cos(lat1) * math.sin(range_km / R) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(range_km / R) * math.cos(lat1),
            math.cos(range_km / R) - math.sin(lat1) * math.sin(lat2)
        )

        return math.degrees(lat2), math.degrees(lon2)

    def create_map(self, events_data: List[Dict], output_file: str = "hail_events_map.html"):
        """Create interactive folium map."""

        # Center map on central US
        center_lat = np.mean([e['storm_lat'] for e in events_data])
        center_lon = np.mean([e['storm_lon'] for e in events_data])

        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=5,
            tiles='cartodbpositron'
        )

        # Add tile layer options
        folium.TileLayer('openstreetmap', name='OpenStreetMap').add_to(m)
        folium.TileLayer('cartodbdark_matter', name='Dark Mode').add_to(m)

        # Create feature groups for layers
        hail_layer = folium.FeatureGroup(name='Hail Events')
        radar_layer = folium.FeatureGroup(name='Radar Sites')
        no_hail_layer = folium.FeatureGroup(name='No Hail Events')

        # Color mapping for severity
        severity_colors = {
            'catastrophic': '#8B0000',  # Dark red
            'severe': '#FF0000',         # Red
            'moderate': '#FFA500',       # Orange
            'light': '#FFD700',          # Gold
            'none': '#808080'            # Gray
        }

        # PDR score to icon size
        def get_icon_size(pdr_score):
            if pdr_score >= 80:
                return 20
            elif pdr_score >= 60:
                return 16
            elif pdr_score >= 40:
                return 12
            else:
                return 8

        # Add events to map
        for event in events_data:
            color = severity_colors.get(event['severity'], '#808080')
            size = get_icon_size(event['pdr_score'])

            # Create popup content
            popup_html = f"""
            <div style="font-family: Arial; width: 280px;">
                <h4 style="margin: 0 0 10px 0; color: {color};">{event['event']['name']}</h4>
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><b>Date:</b></td><td>{event['event']['date'].strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
                    <tr><td><b>Radar:</b></td><td>{event['event']['radar']}</td></tr>
                    <tr><td><b>Location:</b></td><td>({event['storm_lat']:.3f}, {event['storm_lon']:.3f})</td></tr>
                    <tr><td colspan="2"><hr style="margin: 5px 0;"></td></tr>
                    <tr><td><b>Max Reflectivity:</b></td><td>{event['max_reflectivity']:.0f} dBZ</td></tr>
                    <tr><td><b>MESH:</b></td><td>{event['mesh_mm']:.0f} mm ({event['mesh_mm']/25.4:.2f}")</td></tr>
                    <tr><td><b>POSH:</b></td><td>{event['posh']:.0f}%</td></tr>
            """

            if event.get('zdr_min') is not None:
                popup_html += f"""
                    <tr><td><b>ZDR min:</b></td><td>{event['zdr_min']:.1f} dB</td></tr>
                """
            if event.get('cc_min') is not None:
                popup_html += f"""
                    <tr><td><b>CC min:</b></td><td>{event['cc_min']:.2f}</td></tr>
                """

            popup_html += f"""
                    <tr><td colspan="2"><hr style="margin: 5px 0;"></td></tr>
                    <tr><td><b>Hail Detected:</b></td><td style="color: {'green' if event['hail_detected'] else 'gray'};">{'YES' if event['hail_detected'] else 'NO'}</td></tr>
                    <tr><td><b>Probability:</b></td><td>{event['probability']:.0f}%</td></tr>
                    <tr><td><b>Est. Size:</b></td><td>{event['size_mm']:.0f} mm ({event['size_mm']/25.4:.2f}")</td></tr>
                    <tr><td><b>Severity:</b></td><td style="color: {color};"><b>{event['severity'].upper()}</b></td></tr>
                    <tr><td colspan="2"><hr style="margin: 5px 0;"></td></tr>
                    <tr><td><b>PDR Score:</b></td><td><b style="font-size: 14px;">{event['pdr_score']:.0f}/100</b></td></tr>
                </table>
            </div>
            """

            popup = folium.Popup(popup_html, max_width=300)

            # Create marker
            if event['hail_detected']:
                # Hail detected - circle marker with size based on PDR score
                folium.CircleMarker(
                    location=[event['storm_lat'], event['storm_lon']],
                    radius=size,
                    color=color,
                    fill=True,
                    fillColor=color,
                    fillOpacity=0.7,
                    popup=popup,
                    tooltip=f"{event['event']['name']}: {event['severity'].upper()} ({event['pdr_score']:.0f} PDR)"
                ).add_to(hail_layer)

                # Add pulsing marker for high PDR scores
                if event['pdr_score'] >= 70:
                    plugins.BeautifyIcon(
                        icon='cloud',
                        icon_shape='marker',
                        border_color=color,
                        background_color=color
                    )
            else:
                # No hail - smaller gray marker
                folium.CircleMarker(
                    location=[event['storm_lat'], event['storm_lon']],
                    radius=6,
                    color='#808080',
                    fill=True,
                    fillColor='#808080',
                    fillOpacity=0.4,
                    popup=popup,
                    tooltip=f"{event['event']['name']}: No Hail"
                ).add_to(no_hail_layer)

            # Add radar site marker
            folium.CircleMarker(
                location=[event['radar_lat'], event['radar_lon']],
                radius=4,
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.8,
                tooltip=f"Radar: {event['event']['radar']}"
            ).add_to(radar_layer)

            # Draw line from radar to storm
            folium.PolyLine(
                locations=[
                    [event['radar_lat'], event['radar_lon']],
                    [event['storm_lat'], event['storm_lon']]
                ],
                color=color,
                weight=1,
                opacity=0.5,
                dash_array='5, 5'
            ).add_to(hail_layer if event['hail_detected'] else no_hail_layer)

        # Add layers to map
        hail_layer.add_to(m)
        no_hail_layer.add_to(m)
        radar_layer.add_to(m)

        # Add layer control
        folium.LayerControl().add_to(m)

        # Add legend
        legend_html = """
        <div style="position: fixed; bottom: 50px; left: 50px; z-index: 1000;
                    background-color: white; padding: 15px; border-radius: 5px;
                    border: 2px solid gray; font-family: Arial;">
            <h4 style="margin: 0 0 10px 0;">Hail Severity</h4>
            <div><span style="background-color: #8B0000; width: 20px; height: 12px; display: inline-block; margin-right: 5px;"></span> Catastrophic (2.5"+)</div>
            <div><span style="background-color: #FF0000; width: 20px; height: 12px; display: inline-block; margin-right: 5px;"></span> Severe (1.75"+)</div>
            <div><span style="background-color: #FFA500; width: 20px; height: 12px; display: inline-block; margin-right: 5px;"></span> Moderate (1.0"+)</div>
            <div><span style="background-color: #FFD700; width: 20px; height: 12px; display: inline-block; margin-right: 5px;"></span> Light (0.5"+)</div>
            <div><span style="background-color: #808080; width: 20px; height: 12px; display: inline-block; margin-right: 5px;"></span> None</div>
            <hr style="margin: 10px 0;">
            <div style="font-size: 11px;">Marker size = PDR Score</div>
            <div style="font-size: 11px;">Blue dots = Radar sites</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Add title
        title_html = """
        <div style="position: fixed; top: 10px; left: 50px; z-index: 1000;
                    background-color: white; padding: 10px 20px; border-radius: 5px;
                    border: 2px solid #333; font-family: Arial;">
            <h2 style="margin: 0; color: #333;">HailTracker Pro - Event Map</h2>
            <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">Real NEXRAD Radar Analysis</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(title_html))

        # Save map
        m.save(output_file)
        print(f"\nMap saved to: {output_file}")

        return m


def main():
    print("\n" + "=" * 70)
    print("HAILTRACKER PRO - HAIL EVENT MAP VISUALIZATION")
    print("=" * 70 + "\n")

    mapper = HailEventMapper()

    # Historical events to map
    events = [
        {"name": "TX Panhandle Supercell", "date": datetime(2024, 5, 28, 22, 30), "radar": "KAMA", "region": "TX"},
        {"name": "OK Tornado Outbreak", "date": datetime(2024, 5, 6, 23, 0), "radar": "KTLX", "region": "OK"},
        {"name": "DFW Hail Storm", "date": datetime(2024, 4, 26, 21, 0), "radar": "KFWS", "region": "TX"},
        {"name": "Kansas Derecho", "date": datetime(2024, 5, 21, 0, 30), "radar": "KICT", "region": "KS"},
        {"name": "Nebraska Supercell", "date": datetime(2024, 6, 21, 22, 0), "radar": "KOAX", "region": "NE"},
        {"name": "South Dakota Storm", "date": datetime(2024, 7, 11, 23, 30), "radar": "KABR", "region": "SD"},
        {"name": "Colorado Front Range", "date": datetime(2024, 6, 18, 21, 0), "radar": "KFTG", "region": "CO"},
        {"name": "Missouri Valley", "date": datetime(2024, 5, 7, 2, 0), "radar": "KEAX", "region": "MO"},
        {"name": "TX Panhandle 2023", "date": datetime(2023, 6, 15, 23, 0), "radar": "KAMA", "region": "TX"},
        {"name": "OK Moore Storm", "date": datetime(2023, 5, 19, 22, 30), "radar": "KTLX", "region": "OK"},
        {"name": "KS Dodge City", "date": datetime(2023, 5, 17, 0, 0), "radar": "KDDC", "region": "KS"},
        {"name": "NE Grand Island", "date": datetime(2023, 6, 22, 23, 0), "radar": "KUEX", "region": "NE"},
        {"name": "Wichita Storm", "date": datetime(2024, 4, 27, 22, 0), "radar": "KICT", "region": "KS"},
        {"name": "Lubbock Storm", "date": datetime(2024, 5, 23, 22, 30), "radar": "KLBB", "region": "TX"},
        {"name": "San Angelo Event", "date": datetime(2024, 5, 29, 21, 0), "radar": "KSJT", "region": "TX"},
    ]

    print(f"Processing {len(events)} events for map visualization...\n")

    events_data = []

    for i, event in enumerate(events, 1):
        print(f"[{i}/{len(events)}] {event['name']}...", end=" ")

        result = mapper.fetch_and_analyze(event)

        if result:
            events_data.append(result)
            status = "HAIL" if result['hail_detected'] else "no hail"
            print(f"{result['max_reflectivity']:.0f} dBZ, {result['mesh_mm']:.0f}mm MESH, {status}")
        else:
            print("NO DATA")

    if not events_data:
        print("\nNo events to map!")
        return

    # Create summary
    print(f"\n{'='*70}")
    print("MAP SUMMARY")
    print(f"{'='*70}")

    hail_events = [e for e in events_data if e['hail_detected']]
    print(f"Total Events: {len(events_data)}")
    print(f"Hail Detected: {len(hail_events)}")
    print(f"No Hail: {len(events_data) - len(hail_events)}")

    if hail_events:
        print(f"\nHail Events by Severity:")
        for sev in ['catastrophic', 'severe', 'moderate', 'light']:
            count = len([e for e in hail_events if e['severity'] == sev])
            if count > 0:
                print(f"  {sev.upper()}: {count}")

        print(f"\nTop PDR Opportunities:")
        sorted_events = sorted(hail_events, key=lambda x: x['pdr_score'], reverse=True)[:5]
        for i, e in enumerate(sorted_events, 1):
            print(f"  {i}. {e['event']['name']}: {e['pdr_score']:.0f}/100 ({e['size_mm']:.0f}mm)")

    # Create map
    print(f"\n{'='*70}")
    print("CREATING MAP...")
    print(f"{'='*70}")

    output_file = os.path.join(os.path.dirname(__file__), "hail_events_map.html")
    mapper.create_map(events_data, output_file)

    print(f"\nOpen the map in your browser:")
    print(f"  {output_file}")

    # Try to open in browser
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(output_file))
        print("\nMap opened in browser!")
    except:
        pass

    print("\n" + "=" * 70)
    print("MAP CREATION COMPLETE")
    print("=" * 70)


if __name__ == '__main__':
    main()
