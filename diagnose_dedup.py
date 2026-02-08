"""
Diagnose why cross-tile deduplication is only catching 10%
"""

import sys
import os
import sqlite3
import json
import re
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

print("=" * 70)
print("DEDUPLICATION DIAGNOSTIC")
print("=" * 70)
print()

# Get the raw businesses from a quick sample
from src.business.tile_system import SwathTileSystem

db_path = os.path.join(os.path.dirname(__file__), 'data', 'hailtracker_crm.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.execute('''
    SELECT id, swath_polygon FROM hail_events
    WHERE event_date = '2025-10-23'
    AND event_name LIKE '%Oklahoma%'
    AND swath_polygon IS NOT NULL
    LIMIT 3
''')

swaths = []
for row in cursor.fetchall():
    try:
        polygon = json.loads(row['swath_polygon'])
        swaths.append({'event_id': row['id'], 'polygon': polygon, **polygon})
    except:
        pass
conn.close()

# Generate tiles
ts = SwathTileSystem(tile_size_miles=0.25)
tiles = ts.generate_tiles_for_multiple_swaths(swaths)
print(f"Tiles for 3 swaths: {len(tiles)}")

# Search just 20 tiles with Yelp
from src.fleet.apis.yelp_api import YelpAPI
yelp = YelpAPI()

all_businesses = []
print(f"\nSearching 20 tiles with Yelp...")
for i, tile in enumerate(tiles[:20]):
    try:
        radius = int(tile.search_radius_miles * 1609.34)
        results = yelp.search_all_categories(tile.center_lat, tile.center_lon, radius)
        for r in results:
            r['source'] = 'yelp'
            r['tile_id'] = tile.tile_id
        all_businesses.extend(results)
        print(f"  Tile {i+1}: {len(results)} businesses")
    except Exception as e:
        print(f"  Tile {i+1}: ERROR - {e}")

print(f"\nTotal raw: {len(all_businesses)}")
print()

# Analyze the data
print("=" * 70)
print("DATA QUALITY ANALYSIS")
print("=" * 70)
print()

# How many have phones?
with_phone = sum(1 for b in all_businesses if b.get('phone'))
print(f"Businesses with phone: {with_phone} ({with_phone*100/len(all_businesses):.1f}%)")

# How many have coordinates?
with_coords = sum(1 for b in all_businesses if b.get('latitude') and b.get('longitude'))
print(f"Businesses with coords: {with_coords} ({with_coords*100/len(all_businesses):.1f}%)")

# How many have addresses?
with_addr = sum(1 for b in all_businesses if b.get('address'))
print(f"Businesses with address: {with_addr} ({with_addr*100/len(all_businesses):.1f}%)")
print()

# Normalize phone
def normalize_phone(phone):
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) >= 10:
        return digits[-10:]
    return ""

# Count phone duplicates
phones = defaultdict(list)
for i, b in enumerate(all_businesses):
    phone = normalize_phone(b.get('phone', ''))
    if phone:
        phones[phone].append(i)

dupe_phones = {p: idxs for p, idxs in phones.items() if len(idxs) > 1}
print(f"Unique phone numbers: {len(phones)}")
print(f"Phone numbers appearing 2+ times: {len(dupe_phones)}")

total_phone_dupes = sum(len(idxs) - 1 for idxs in dupe_phones.values())
print(f"Total phone-based duplicates: {total_phone_dupes}")
print()

# Show some phone duplicates
print("SAMPLE PHONE DUPLICATES:")
for phone, idxs in list(dupe_phones.items())[:5]:
    print(f"\n  Phone: {phone}")
    for idx in idxs:
        b = all_businesses[idx]
        print(f"    [{b.get('tile_id', '?')[:10]}] {b.get('name', '?')[:40]} | {b.get('address', '?')[:30]}")

print()

# Count name duplicates (exact normalized match)
def normalize_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r'\s*,?\s*(llc|inc|corp|ltd|co|company)\.?$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

names = defaultdict(list)
for i, b in enumerate(all_businesses):
    name = normalize_name(b.get('name', ''))
    if name:
        names[name].append(i)

dupe_names = {n: idxs for n, idxs in names.items() if len(idxs) > 1}
print(f"Unique normalized names: {len(names)}")
print(f"Names appearing 2+ times: {len(dupe_names)}")

total_name_dupes = sum(len(idxs) - 1 for idxs in dupe_names.values())
print(f"Total name-based duplicates: {total_name_dupes}")
print()

# Show some name duplicates
print("SAMPLE NAME DUPLICATES:")
for name, idxs in list(dupe_names.items())[:5]:
    print(f"\n  Name: '{name}'")
    for idx in idxs:
        b = all_businesses[idx]
        phone = normalize_phone(b.get('phone', ''))
        print(f"    [{b.get('tile_id', '?')[:10]}] Phone: {phone or 'NONE'} | {b.get('address', '?')[:40]}")

print()

# Now run the actual deduplication and compare
from src.business.deduplication import deduplicate_businesses, analyze_duplicates

print("=" * 70)
print("DEDUPLICATION RESULTS")
print("=" * 70)
print()

# Analyze first
analysis = analyze_duplicates(all_businesses)
print(f"Analysis of raw data:")
print(f"  Total: {analysis['total']}")
print(f"  Unique phones: {analysis['unique_phones']} (dupes: {analysis['phone_duplicates']})")
print(f"  Unique names: {analysis['unique_names']} (dupes: {analysis['name_duplicates']})")
print(f"  Unique addresses: {analysis['unique_addresses']} (dupes: {analysis['address_duplicates']})")
print(f"  Estimated unique: {analysis['estimated_unique']}")
print()

# Run deduplication
deduped = deduplicate_businesses(all_businesses, merge_data=True)
print(f"After deduplicate_businesses(): {len(deduped)}")
print(f"Duplicates removed: {len(all_businesses) - len(deduped)}")
print(f"Dedup rate: {(len(all_businesses) - len(deduped))*100/len(all_businesses):.1f}%")
print()

# What SHOULD happen?
print("EXPECTED DEDUP:")
print(f"  Phone-based duplicates alone: {total_phone_dupes}")
print(f"  Name-based duplicates alone: {total_name_dupes}")
print(f"  Expected dedup rate: {max(total_phone_dupes, total_name_dupes)*100/len(all_businesses):.1f}%+")
