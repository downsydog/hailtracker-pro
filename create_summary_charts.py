"""
Create Summary Charts and Static Visualizations

Generates matplotlib charts summarizing the hail event analysis.
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

# Event data from the analysis
events_data = [
    {"name": "TX Panhandle Supercell", "date": "2024-05-28", "radar": "KAMA",
     "lat": 35.19, "lon": -101.44, "max_ref": 74, "mesh": 32, "posh": 83,
     "hail": True, "prob": 74, "size": 29, "severity": "moderate", "pdr": 77},

    {"name": "OK Tornado Outbreak", "date": "2024-05-06", "radar": "KTLX",
     "lat": 36.07, "lon": -98.66, "max_ref": 72, "mesh": 17, "posh": 47,
     "hail": False, "prob": 46, "size": 0, "severity": "none", "pdr": 0},

    {"name": "DFW Hail Storm", "date": "2024-04-26", "radar": "KFWS",
     "lat": 31.04, "lon": -98.75, "max_ref": 67, "mesh": 28, "posh": 78,
     "hail": True, "prob": 65, "size": 25, "severity": "light", "pdr": 76},

    {"name": "Kansas Derecho", "date": "2024-05-21", "radar": "KICT",
     "lat": 40.87, "lon": -98.49, "max_ref": 54, "mesh": 0, "posh": 0,
     "hail": False, "prob": 20, "size": 0, "severity": "none", "pdr": 0},

    {"name": "Nebraska Supercell", "date": "2024-06-21", "radar": "KOAX",
     "lat": 43.21, "lon": -95.28, "max_ref": 62, "mesh": 29, "posh": 79,
     "hail": True, "prob": 68, "size": 26, "severity": "moderate", "pdr": 76},

    {"name": "South Dakota Storm", "date": "2024-07-11", "radar": "KABR",
     "lat": 45.20, "lon": -97.89, "max_ref": 54, "mesh": 0, "posh": 0,
     "hail": False, "prob": 20, "size": 0, "severity": "none", "pdr": 0},

    {"name": "Colorado Front Range", "date": "2024-06-18", "radar": "KFTG",
     "lat": 38.22, "lon": -100.51, "max_ref": 62, "mesh": 0, "posh": 0,
     "hail": False, "prob": 20, "size": 0, "severity": "none", "pdr": 0},

    {"name": "Missouri Valley", "date": "2024-05-07", "radar": "KEAX",
     "lat": 37.60, "lon": -96.10, "max_ref": 62, "mesh": 15, "posh": 45,
     "hail": False, "prob": 43, "size": 0, "severity": "none", "pdr": 0},

    {"name": "TX Panhandle 2023", "date": "2023-06-15", "radar": "KAMA",
     "lat": 36.32, "lon": -100.31, "max_ref": 68, "mesh": 9, "posh": 18,
     "hail": False, "prob": 31, "size": 0, "severity": "none", "pdr": 0},

    {"name": "OK Moore Storm", "date": "2023-05-19", "radar": "KTLX",
     "lat": 33.82, "lon": -95.72, "max_ref": 67, "mesh": 22, "posh": 52,
     "hail": True, "prob": 54, "size": 20, "severity": "light", "pdr": 63},

    {"name": "KS Dodge City", "date": "2023-05-17", "radar": "KDDC",
     "lat": 37.63, "lon": -100.28, "max_ref": 62, "mesh": 0, "posh": 0,
     "hail": False, "prob": 20, "size": 0, "severity": "none", "pdr": 0},

    {"name": "NE Grand Island", "date": "2023-06-22", "radar": "KUEX",
     "lat": 40.09, "lon": -99.87, "max_ref": 57, "mesh": 12, "posh": 42,
     "hail": False, "prob": 37, "size": 0, "severity": "none", "pdr": 0},

    {"name": "Wichita Storm", "date": "2024-04-27", "radar": "KICT",
     "lat": 36.89, "lon": -96.91, "max_ref": 68, "mesh": 48, "posh": 99,
     "hail": True, "prob": 98, "size": 44, "severity": "moderate", "pdr": 82},

    {"name": "Lubbock Storm", "date": "2024-05-23", "radar": "KLBB",
     "lat": 32.88, "lon": -100.23, "max_ref": 68, "mesh": 4, "posh": 9,
     "hail": False, "prob": 23, "size": 0, "severity": "none", "pdr": 0},

    {"name": "San Angelo Event", "date": "2024-05-29", "radar": "KSJT",
     "lat": 31.16, "lon": -100.61, "max_ref": 66, "mesh": 0, "posh": 0,
     "hail": False, "prob": 20, "size": 0, "severity": "none", "pdr": 0},
]


def create_summary_dashboard():
    """Create a comprehensive summary dashboard."""

    fig = plt.figure(figsize=(16, 12))
    fig.suptitle('HailTracker Pro - Multi-Event Analysis Summary\nReal NEXRAD Radar Data',
                 fontsize=16, fontweight='bold', y=0.98)

    # Create grid
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3,
                          left=0.08, right=0.95, top=0.92, bottom=0.08)

    # 1. Hail Detection Pie Chart
    ax1 = fig.add_subplot(gs[0, 0])
    hail_count = sum(1 for e in events_data if e['hail'])
    no_hail_count = len(events_data) - hail_count

    colors = ['#FF6B6B', '#4ECDC4']
    explode = (0.05, 0)
    ax1.pie([hail_count, no_hail_count], labels=['Hail Detected', 'No Hail'],
            colors=colors, explode=explode, autopct='%1.0f%%',
            shadow=True, startangle=90)
    ax1.set_title('Detection Results', fontweight='bold')

    # 2. Severity Distribution
    ax2 = fig.add_subplot(gs[0, 1])
    severities = ['moderate', 'light', 'none']
    sev_counts = [sum(1 for e in events_data if e['severity'] == s) for s in severities]
    sev_colors = ['#FFA500', '#FFD700', '#808080']

    bars = ax2.barh(severities, sev_counts, color=sev_colors, edgecolor='black')
    ax2.set_xlabel('Number of Events')
    ax2.set_title('Severity Distribution', fontweight='bold')
    for i, (bar, count) in enumerate(zip(bars, sev_counts)):
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                 str(count), va='center', fontweight='bold')

    # 3. PDR Score Distribution
    ax3 = fig.add_subplot(gs[0, 2])
    pdr_scores = [e['pdr'] for e in events_data]
    pdr_colors = ['#FF0000' if p >= 70 else '#FFA500' if p >= 40 else '#808080' for p in pdr_scores]

    ax3.bar(range(len(pdr_scores)), pdr_scores, color=pdr_colors, edgecolor='black')
    ax3.axhline(y=70, color='red', linestyle='--', label='High Priority (70+)')
    ax3.axhline(y=40, color='orange', linestyle='--', label='Medium Priority (40+)')
    ax3.set_ylabel('PDR Score')
    ax3.set_xlabel('Event Index')
    ax3.set_title('PDR Opportunity Scores', fontweight='bold')
    ax3.legend(loc='upper right', fontsize=8)
    ax3.set_ylim(0, 100)

    # 4. MESH vs Max Reflectivity Scatter
    ax4 = fig.add_subplot(gs[1, 0])
    hail_events = [e for e in events_data if e['hail']]
    no_hail_events = [e for e in events_data if not e['hail']]

    ax4.scatter([e['max_ref'] for e in no_hail_events],
                [e['mesh'] for e in no_hail_events],
                c='gray', s=80, alpha=0.6, label='No Hail', edgecolors='black')
    ax4.scatter([e['max_ref'] for e in hail_events],
                [e['mesh'] for e in hail_events],
                c='red', s=120, alpha=0.8, label='Hail', edgecolors='black', marker='s')

    ax4.set_xlabel('Max Reflectivity (dBZ)')
    ax4.set_ylabel('MESH (mm)')
    ax4.set_title('MESH vs Reflectivity', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Top 5 PDR Opportunities
    ax5 = fig.add_subplot(gs[1, 1])
    sorted_events = sorted(events_data, key=lambda x: x['pdr'], reverse=True)[:5]
    names = [e['name'][:20] for e in sorted_events]
    scores = [e['pdr'] for e in sorted_events]
    sizes = [e['size'] for e in sorted_events]

    colors = ['#FF0000' if s >= 70 else '#FFA500' if s >= 40 else '#808080' for s in scores]
    bars = ax5.barh(range(len(names)), scores, color=colors, edgecolor='black')
    ax5.set_yticks(range(len(names)))
    ax5.set_yticklabels(names, fontsize=9)
    ax5.set_xlabel('PDR Score')
    ax5.set_title('Top 5 PDR Opportunities', fontweight='bold')
    ax5.set_xlim(0, 100)

    for i, (bar, score, size) in enumerate(zip(bars, scores, sizes)):
        ax5.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                 f'{score:.0f} ({size}mm)', va='center', fontsize=9)

    # 6. Geographic Distribution (Simple)
    ax6 = fig.add_subplot(gs[1, 2])

    lons = [e['lon'] for e in events_data]
    lats = [e['lat'] for e in events_data]
    colors_geo = ['red' if e['hail'] else 'gray' for e in events_data]
    sizes_geo = [e['pdr']*3 + 50 if e['hail'] else 50 for e in events_data]

    ax6.scatter(lons, lats, c=colors_geo, s=sizes_geo, alpha=0.7, edgecolors='black')
    ax6.set_xlabel('Longitude')
    ax6.set_ylabel('Latitude')
    ax6.set_title('Geographic Distribution', fontweight='bold')
    ax6.grid(True, alpha=0.3)

    # Add state labels approximately
    ax6.text(-101, 35, 'TX', fontsize=10, alpha=0.5)
    ax6.text(-97, 36, 'OK', fontsize=10, alpha=0.5)
    ax6.text(-98, 38, 'KS', fontsize=10, alpha=0.5)
    ax6.text(-99, 41, 'NE', fontsize=10, alpha=0.5)

    # 7. Probability Distribution
    ax7 = fig.add_subplot(gs[2, 0])
    probs = [e['prob'] for e in events_data]
    ax7.hist(probs, bins=10, color='steelblue', edgecolor='black', alpha=0.7)
    ax7.axvline(x=50, color='red', linestyle='--', label='50% Threshold')
    ax7.set_xlabel('Hail Probability (%)')
    ax7.set_ylabel('Number of Events')
    ax7.set_title('Probability Distribution', fontweight='bold')
    ax7.legend()

    # 8. Hail Size Distribution (Hail Events Only)
    ax8 = fig.add_subplot(gs[2, 1])
    hail_sizes = [e['size'] for e in events_data if e['hail'] and e['size'] > 0]
    hail_names = [e['name'][:15] for e in events_data if e['hail'] and e['size'] > 0]

    colors_size = []
    for size in hail_sizes:
        if size >= 45:
            colors_size.append('#8B0000')  # Severe
        elif size >= 25:
            colors_size.append('#FFA500')  # Moderate
        else:
            colors_size.append('#FFD700')  # Light

    bars = ax8.bar(range(len(hail_sizes)), hail_sizes, color=colors_size, edgecolor='black')
    ax8.set_xticks(range(len(hail_names)))
    ax8.set_xticklabels(hail_names, rotation=45, ha='right', fontsize=8)
    ax8.set_ylabel('Hail Size (mm)')
    ax8.set_title('Hail Sizes by Event', fontweight='bold')

    # Add inch labels
    for bar, size in zip(bars, hail_sizes):
        ax8.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{size/25.4:.1f}"', ha='center', fontsize=9)

    # 9. Summary Statistics Text
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    stats_text = f"""
    SUMMARY STATISTICS
    ══════════════════════════════

    Total Events Analyzed: {len(events_data)}
    Hail Detected: {hail_count} ({hail_count/len(events_data)*100:.0f}%)

    Reflectivity Range: {min(e['max_ref'] for e in events_data)}-{max(e['max_ref'] for e in events_data)} dBZ
    MESH Range: {min(e['mesh'] for e in events_data)}-{max(e['mesh'] for e in events_data)} mm

    Highest PDR Score: {max(e['pdr'] for e in events_data):.0f}/100
    Average PDR (Hail Events): {np.mean([e['pdr'] for e in events_data if e['hail']]):.0f}/100

    Largest Hail: {max(e['size'] for e in events_data):.0f} mm ({max(e['size'] for e in events_data)/25.4:.2f}")

    ══════════════════════════════
    Data Source: AWS NEXRAD Archive
    Processing: HailTracker Pro ML
    """

    ax9.text(0.1, 0.95, stats_text, transform=ax9.transAxes, fontsize=10,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

    # Save
    output_file = os.path.join(os.path.dirname(__file__), 'hail_analysis_summary.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"Summary chart saved to: {output_file}")

    plt.close()
    return output_file


def create_pdr_priority_chart():
    """Create a PDR priority recommendation chart."""

    fig, ax = plt.subplots(figsize=(12, 8))

    # Sort by PDR score
    sorted_events = sorted(events_data, key=lambda x: x['pdr'], reverse=True)

    names = [f"{e['name']}\n({e['date']})" for e in sorted_events]
    scores = [e['pdr'] for e in sorted_events]
    sizes = [e['size'] for e in sorted_events]

    # Color by priority
    colors = []
    for score in scores:
        if score >= 70:
            colors.append('#FF4444')  # High - Red
        elif score >= 40:
            colors.append('#FFAA00')  # Medium - Orange
        else:
            colors.append('#888888')  # Low - Gray

    y_pos = range(len(names))
    bars = ax.barh(y_pos, scores, color=colors, edgecolor='black', height=0.7)

    # Add score labels
    for i, (bar, score, size) in enumerate(zip(bars, scores, sizes)):
        if score > 0:
            label = f'{score:.0f}'
            if size > 0:
                label += f' ({size}mm)'
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                   label, va='center', fontsize=9, fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel('PDR Opportunity Score', fontsize=12)
    ax.set_title('HailTracker Pro - PDR Priority Rankings\nBased on Real NEXRAD Analysis',
                 fontsize=14, fontweight='bold')
    ax.set_xlim(0, 100)

    # Add priority zones
    ax.axvline(x=70, color='red', linestyle='--', alpha=0.5)
    ax.axvline(x=40, color='orange', linestyle='--', alpha=0.5)

    ax.text(85, len(names)-1, 'HIGH\nPRIORITY', ha='center', va='top',
            fontsize=10, color='red', fontweight='bold')
    ax.text(55, len(names)-1, 'MEDIUM', ha='center', va='top',
            fontsize=10, color='orange', fontweight='bold')
    ax.text(20, len(names)-1, 'LOW', ha='center', va='top',
            fontsize=10, color='gray', fontweight='bold')

    # Legend
    high_patch = mpatches.Patch(color='#FF4444', label='High Priority (70+)')
    med_patch = mpatches.Patch(color='#FFAA00', label='Medium Priority (40-69)')
    low_patch = mpatches.Patch(color='#888888', label='Low Priority (<40)')
    ax.legend(handles=[high_patch, med_patch, low_patch], loc='lower right')

    ax.grid(True, axis='x', alpha=0.3)

    # Save
    output_file = os.path.join(os.path.dirname(__file__), 'pdr_priority_chart.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"PDR priority chart saved to: {output_file}")

    plt.close()
    return output_file


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CREATING SUMMARY VISUALIZATIONS")
    print("=" * 60 + "\n")

    summary_file = create_summary_dashboard()
    pdr_file = create_pdr_priority_chart()

    print("\n" + "=" * 60)
    print("VISUALIZATION COMPLETE")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  1. {summary_file}")
    print(f"  2. {pdr_file}")
    print(f"  3. hail_events_map.html (interactive map)")
