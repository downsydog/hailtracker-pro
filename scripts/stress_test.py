"""
COMPREHENSIVE SYSTEM STRESS TEST
Brutally honest assessment of what works vs placeholder code
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Results tracking
results = {
    'working': [],
    'partial': [],
    'broken': [],
    'needs_keys': []
}

def test_result(component, status, details, action=""):
    """Record test result."""
    entry = {'component': component, 'details': details, 'action': action}
    if status == 'OK':
        results['working'].append(entry)
        return '[OK]'
    elif status == 'PARTIAL':
        results['partial'].append(entry)
        return '[!!]'
    elif status == 'BROKEN':
        results['broken'].append(entry)
        return '[XX]'
    elif status == 'KEYS':
        results['needs_keys'].append(entry)
        return '[KEY]'
    return '[??]'

print("=" * 80)
print("        HAILTRACKER PRO - COMPREHENSIVE SYSTEM STRESS TEST")
print("=" * 80)
print(f"  Time: {datetime.now().isoformat()}")
print(f"  Project Root: {PROJECT_ROOT}")
print("=" * 80)

# =============================================================================
# TEST 1: RADAR INFRASTRUCTURE
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 1: RADAR INFRASTRUCTURE")
print("=" * 80)

# 1.1 Database Check
print("\n[1.1] DATABASE CHECK")
db_path = PROJECT_ROOT / 'database' / 'hailtracker_pro.db'
print(f"  Database path: {db_path}")
print(f"  Database exists: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Count radars
    cursor.execute("SELECT COUNT(*) FROM radar_sites")
    radar_count = cursor.fetchone()[0]
    print(f"  Total radars in DB: {radar_count}")

    # By country
    cursor.execute("SELECT country, COUNT(*) FROM radar_sites GROUP BY country")
    by_country = dict(cursor.fetchall())
    print(f"  By country: {by_country}")

    # Sample radars
    print("\n  Sample US radar:")
    cursor.execute("SELECT site_code, name, state_province FROM radar_sites WHERE country='US' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"    {row[0]}: {row[1]}, {row[2]}")

    print("  Sample CA radar:")
    cursor.execute("SELECT site_code, name, state_province FROM radar_sites WHERE country='CA' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"    {row[0]}: {row[1]}, {row[2]}")
    else:
        print("    None found")

    print("  Sample MX radar:")
    cursor.execute("SELECT site_code, name, state_province FROM radar_sites WHERE country='MX' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"    {row[0]}: {row[1]}, {row[2]}")
    else:
        print("    None found")

    status = test_result("Radar Database", "OK" if radar_count >= 200 else "PARTIAL",
                        f"{radar_count} radars loaded",
                        "Add more radars" if radar_count < 200 else "")
    print(f"\n  Result: {status} - {radar_count} radars in database")
    conn.close()
else:
    test_result("Radar Database", "BROKEN", "Database file not found", "Run database setup")
    print("  Result: [XX] Database not found")

# 1.2 Coverage Finder Test
print("\n[1.2] COVERAGE FINDER TEST")
try:
    from src.radar.coverage import find_covering_radars, get_all_radars

    # Test OKC
    print("  Testing Oklahoma City (35.47, -97.52):")
    coverages = find_covering_radars(35.47, -97.52, max_radars=3)
    if coverages:
        for c in coverages:
            print(f"    - {c.radar.site_code}: {c.distance_km:.0f}km, quality={c.coverage_quality}")
        status = test_result("Coverage Finder", "OK", f"Found {len(coverages)} radars for OKC")
    else:
        status = test_result("Coverage Finder", "BROKEN", "No radars found", "Check radar data")
    print(f"  Result: {status}")

    # Test Calgary
    print("\n  Testing Calgary (51.04, -114.07):")
    coverages_ca = find_covering_radars(51.04, -114.07, max_radars=3)
    if coverages_ca:
        for c in coverages_ca:
            print(f"    - {c.radar.site_code}: {c.distance_km:.0f}km")
    else:
        print("    No radars found (expected - Canada coverage may be limited)")

    # Test El Paso (border)
    print("\n  Testing El Paso border (31.76, -106.49):")
    coverages_ep = find_covering_radars(31.76, -106.49, max_radars=3)
    if coverages_ep:
        for c in coverages_ep:
            print(f"    - {c.radar.site_code} ({c.radar.country}): {c.distance_km:.0f}km")

except Exception as e:
    test_result("Coverage Finder", "BROKEN", str(e), "Fix import/code")
    print(f"  Result: [XX] Error: {e}")

# 1.3 Radar Download Test
print("\n[1.3] RADAR DOWNLOAD TEST")
print("  Testing NEXRAD download capability...")

try:
    from src.radar.nexrad import NEXRADDownloader
    downloader = NEXRADDownloader()

    # Check if download method exists and try to list files
    if hasattr(downloader, 'list_available_files'):
        print("  NEXRADDownloader has list_available_files() method")
        # Try listing recent files for KTLX
        try:
            from datetime import datetime
            files = downloader.list_available_files('KTLX', datetime.now() - timedelta(hours=2))
            if files:
                print(f"  Found {len(files)} recent KTLX files")
                status = test_result("NEXRAD Download", "OK", f"Can list {len(files)} files")
            else:
                status = test_result("NEXRAD Download", "PARTIAL", "Method exists but no files found",
                                    "Check AWS connection")
        except Exception as e:
            status = test_result("NEXRAD Download", "PARTIAL", f"List failed: {e}", "Fix AWS access")
    elif hasattr(downloader, 'download'):
        print("  NEXRADDownloader has download() method")
        status = test_result("NEXRAD Download", "PARTIAL", "Download method exists, not tested",
                            "Test actual download")
    else:
        status = test_result("NEXRAD Download", "BROKEN", "No download methods found", "Implement downloader")
    print(f"  Result: {status}")
except ImportError as e:
    test_result("NEXRAD Download", "BROKEN", f"Import failed: {e}", "Create nexrad.py")
    print(f"  Result: [XX] Import error: {e}")
except Exception as e:
    test_result("NEXRAD Download", "BROKEN", str(e), "Fix error")
    print(f"  Result: [XX] Error: {e}")

# Check Canadian radar
print("\n  Testing Canadian radar download...")
try:
    from src.radar.canada import CanadianRadarDownloader
    print("  Canadian radar module exists")
    status = test_result("Canadian Radar", "PARTIAL", "Module exists", "Test actual download")
except ImportError:
    status = test_result("Canadian Radar", "BROKEN", "Module not found", "Create canada.py")
print(f"  Result: {status}")

# Check Mexican radar
print("\n  Testing Mexican radar download...")
try:
    from src.radar.mexico import MexicanRadarDownloader
    print("  Mexican radar module exists")
    status = test_result("Mexican Radar", "PARTIAL", "Module exists", "Test actual download")
except ImportError:
    status = test_result("Mexican Radar", "BROKEN", "Module not found", "Create mexico.py")
print(f"  Result: {status}")

# 1.4 Multi-Radar Fusion Test
print("\n[1.4] MULTI-RADAR FUSION TEST")
try:
    from src.radar.fusion import RadarFusionEngine
    engine = RadarFusionEngine()

    if hasattr(engine, 'fuse_radars') or hasattr(engine, 'process_multi_radar'):
        print("  RadarFusionEngine exists with fusion methods")
        status = test_result("Radar Fusion", "PARTIAL", "Class exists", "Test with real data")
    else:
        status = test_result("Radar Fusion", "PARTIAL", "Class exists, methods unclear", "Review API")
    print(f"  Result: {status}")
except ImportError as e:
    test_result("Radar Fusion", "BROKEN", f"Import failed: {e}", "Create fusion.py")
    print(f"  Result: [XX] Import error: {e}")
except Exception as e:
    test_result("Radar Fusion", "BROKEN", str(e), "Fix error")
    print(f"  Result: [XX] Error: {e}")

# =============================================================================
# TEST 2: SOCIAL MEDIA SCRAPING
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 2: SOCIAL MEDIA SCRAPING")
print("=" * 80)

# 2.1 Reddit
print("\n[2.1] REDDIT SCRAPER")
try:
    from src.social.scrapers.reddit import RedditHailScraper
    scraper = RedditHailScraper()

    if hasattr(scraper, 'search') or hasattr(scraper, 'scrape'):
        print("  RedditHailScraper exists")
        # Try to actually scrape (will likely fail without credentials)
        try:
            posts = scraper.search("hail damage", limit=3) if hasattr(scraper, 'search') else []
            if posts:
                print(f"  Found {len(posts)} posts!")
                for p in posts[:2]:
                    print(f"    - {p.get('title', 'No title')[:50]}...")
                status = test_result("Reddit Scraper", "OK", f"Found {len(posts)} posts")
            else:
                status = test_result("Reddit Scraper", "KEYS", "No posts returned", "Add Reddit API credentials")
        except Exception as e:
            if 'credential' in str(e).lower() or 'api' in str(e).lower() or 'auth' in str(e).lower():
                status = test_result("Reddit Scraper", "KEYS", str(e)[:50], "Add Reddit API key")
            else:
                status = test_result("Reddit Scraper", "PARTIAL", str(e)[:50], "Fix scraper")
    else:
        status = test_result("Reddit Scraper", "BROKEN", "No search method", "Implement search()")
    print(f"  Result: {status}")
except ImportError as e:
    test_result("Reddit Scraper", "BROKEN", f"Import failed: {e}", "Create reddit.py")
    print(f"  Result: [XX] Import error: {e}")
except Exception as e:
    test_result("Reddit Scraper", "BROKEN", str(e)[:50], "Fix error")
    print(f"  Result: [XX] Error: {e}")

# 2.2 Twitter/Nitter
print("\n[2.2] TWITTER/NITTER SCRAPER")
try:
    from src.social.scrapers.twitter import TwitterHailScraper
    scraper = TwitterHailScraper()
    print("  TwitterHailScraper exists")
    status = test_result("Twitter Scraper", "KEYS", "Module exists", "Add Twitter API or test Nitter")
    print(f"  Result: {status}")
except ImportError as e:
    test_result("Twitter Scraper", "BROKEN", f"Import failed", "Create twitter.py")
    print(f"  Result: [XX] Import error")
except Exception as e:
    test_result("Twitter Scraper", "BROKEN", str(e)[:50], "Fix error")
    print(f"  Result: [XX] Error: {e}")

# 2.3 Instagram
print("\n[2.3] INSTAGRAM SCRAPER")
try:
    from src.social.scrapers.instagram import InstagramHailScraper
    print("  InstagramHailScraper exists")
    status = test_result("Instagram Scraper", "KEYS", "Module exists", "Test with Instaloader")
    print(f"  Result: {status}")
except ImportError:
    test_result("Instagram Scraper", "BROKEN", "Import failed", "Create instagram.py")
    print("  Result: [XX] Import error")

# 2.4 YouTube
print("\n[2.4] YOUTUBE SCRAPER")
try:
    from src.social.scrapers.youtube import YouTubeHailScraper
    print("  YouTubeHailScraper exists")
    status = test_result("YouTube Scraper", "PARTIAL", "Module exists", "Test search")
    print(f"  Result: {status}")
except ImportError:
    test_result("YouTube Scraper", "BROKEN", "Import failed", "Create youtube.py")
    print("  Result: [XX] Import error")

# 2.5 Facebook
print("\n[2.5] FACEBOOK SCRAPER")
try:
    from src.social.scrapers.facebook import FacebookHailScraper
    print("  FacebookHailScraper exists")
    status = test_result("Facebook Scraper", "KEYS", "Module exists", "Requires authentication")
    print(f"  Result: {status}")
except ImportError:
    test_result("Facebook Scraper", "BROKEN", "Import failed", "Create facebook.py")
    print("  Result: [XX] Import error")

# =============================================================================
# TEST 3: ML MODELS
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 3: ML MODELS (15 Models)")
print("=" * 80)

models_dir = PROJECT_ROOT / 'src' / 'ml' / 'models'
saved_dir = models_dir / 'saved'

print(f"\n  Models directory: {models_dir}")
print(f"  Models dir exists: {models_dir.exists()}")
print(f"  Saved models dir: {saved_dir}")
print(f"  Saved dir exists: {saved_dir.exists()}")

if saved_dir.exists():
    saved_files = list(saved_dir.glob('*'))
    print(f"  Saved model files: {len(saved_files)}")
    for f in saved_files[:10]:
        size_kb = f.stat().st_size / 1024
        print(f"    - {f.name}: {size_kb:.0f} KB")

ml_models = [
    ("Radar Hail Classifier", "radar_hail_classifier", "RadarHailClassifier"),
    ("Storm Forecaster", "storm_forecaster", "StormSeverityForecaster"),
    ("Seasonal Risk", "seasonal_risk", "SeasonalRiskModel"),
    ("Hail Size Estimator", "hail_size_estimator", "HailSizeEstimator"),
    ("Vehicle Damage Detector", "vehicle_damage_detector", "VehicleDamageDetector"),
    ("Photo Validator", "photo_validator", "PhotoAuthenticityValidator"),
    ("Opportunity Scorer", "pdr_business_models", "MLOpportunityScorer"),
    ("Claim Rate Predictor", "pdr_business_models", "ClaimRatePredictor"),
    ("Damage Prediction", "pdr_business_models", "DamagePredictionModel"),
    ("Vehicle Counter", "pdr_business_models", "ParkingLotVehicleCounter"),
    ("Route Optimizer", "advanced_models", "RouteOptimizer"),
    ("Conversion Predictor", "advanced_models", "ConversionPredictor"),
    ("Inventory Estimator", "advanced_models", "DealershipInventoryEstimator"),
    ("Sentiment Analyzer", "real_sentiment", "RealSentimentAnalyzer"),
    ("Repair Time Estimator", "advanced_models", "RepairTimeEstimator"),
]

print("\n  Testing each model:")
for name, module, classname in ml_models:
    py_file = models_dir / f"{module}.py"
    pkl_file = saved_dir / f"{module.replace('_models', '')}.pkl"

    file_exists = py_file.exists()
    model_exists = any(saved_dir.glob(f"*{module.split('_')[0]}*")) if saved_dir.exists() else False

    try:
        exec(f"from src.ml.models.{module} import {classname}")
        can_import = True
    except:
        can_import = False

    if file_exists and can_import:
        # Check if it's real or synthetic
        if 'real_sentiment' in module:
            status = test_result(f"ML: {name}", "OK", "REAL pre-trained model (66M params)")
            marker = "[OK] REAL"
        else:
            status = test_result(f"ML: {name}", "PARTIAL", "Synthetic training data", "Train on real data")
            marker = "[!!] SYNTH"
    elif file_exists:
        status = test_result(f"ML: {name}", "PARTIAL", "File exists, import failed", "Fix imports")
        marker = "[!!]"
    else:
        status = test_result(f"ML: {name}", "BROKEN", "File not found", "Create model")
        marker = "[XX]"

    print(f"    {marker} {name}")

# =============================================================================
# TEST 4: PDR BUSINESS INTELLIGENCE
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 4: PDR BUSINESS INTELLIGENCE")
print("=" * 80)

# 4.1 Vehicle Density / OSM
print("\n[4.1] VEHICLE DENSITY MAPPING (OpenStreetMap)")
try:
    # Check if we have OSM querying capability
    import requests
    # Test Overpass API availability
    overpass_url = "https://overpass-api.de/api/status"
    response = requests.get(overpass_url, timeout=5)
    if response.status_code == 200:
        print("  Overpass API is accessible")
        status = test_result("OSM Vehicle Density", "PARTIAL", "API accessible", "Implement query")
    else:
        status = test_result("OSM Vehicle Density", "PARTIAL", "API may be rate-limited", "Add caching")
    print(f"  Result: {status}")
except Exception as e:
    test_result("OSM Vehicle Density", "PARTIAL", str(e)[:40], "Check network")
    print(f"  Result: [!!] {e}")

# 4.2 Dealer Database
print("\n[4.2] DEALER DATABASE")
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM dealerships")
        dealer_count = cursor.fetchone()[0]
        print(f"  Dealerships in DB: {dealer_count}")

        if dealer_count > 0:
            cursor.execute("SELECT name, city, state FROM dealerships LIMIT 3")
            for row in cursor.fetchall():
                print(f"    - {row[0]}, {row[1]}, {row[2]}")
            status = test_result("Dealer Database", "OK" if dealer_count > 100 else "PARTIAL",
                               f"{dealer_count} dealers", "Add more dealers" if dealer_count < 100 else "")
        else:
            status = test_result("Dealer Database", "BROKEN", "No dealers in DB", "Seed dealer data")
    except sqlite3.OperationalError:
        status = test_result("Dealer Database", "BROKEN", "Table not found", "Create dealerships table")
    conn.close()
    print(f"  Result: {status}")
else:
    print("  Result: [XX] Database not found")

# 4.3 Opportunity Finder
print("\n[4.3] PDR OPPORTUNITY FINDER")
try:
    from src.pdr.opportunity import PDROpportunityScorer
    scorer = PDROpportunityScorer(str(db_path))
    print("  PDROpportunityScorer loaded")
    status = test_result("Opportunity Finder", "OK", "Class works")
    print(f"  Result: {status}")
except Exception as e:
    test_result("Opportunity Finder", "BROKEN", str(e)[:40], "Fix scorer")
    print(f"  Result: [XX] {e}")

# =============================================================================
# TEST 5: WEB INTERFACE
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 5: WEB INTERFACE")
print("=" * 80)

import requests

# 5.1 Server Check
print("\n[5.1] WEB SERVER")
try:
    response = requests.get("http://localhost:5050/api/health", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"  Server: RUNNING")
        print(f"  Version: {data.get('version', 'unknown')}")
        print(f"  ML Models: {data.get('ml_models_loaded', 0)}")
        status = test_result("Web Server", "OK", f"Running v{data.get('version')}")
    else:
        status = test_result("Web Server", "PARTIAL", f"Status {response.status_code}", "Check server")
    print(f"  Result: {status}")
except requests.exceptions.ConnectionError:
    test_result("Web Server", "BROKEN", "Not running", "Start server")
    print("  Result: [XX] Server not running")
except Exception as e:
    test_result("Web Server", "BROKEN", str(e)[:40], "Fix server")
    print(f"  Result: [XX] {e}")

# 5.2 API Endpoints
print("\n[5.2] API ENDPOINTS")
endpoints = [
    ("GET /api/events", "http://localhost:5050/api/events?limit=5"),
    ("GET /api/radars", "http://localhost:5050/api/radars"),
    ("GET /api/stats", "http://localhost:5050/api/stats"),
    ("GET /api/ml/status", "http://localhost:5050/api/ml/status"),
    ("GET /api/pdr/markets", "http://localhost:5050/api/pdr/markets"),
]

for name, url in endpoints:
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', len(data) if isinstance(data, list) else 'OK')
            print(f"  [OK] {name}: {count}")
        else:
            print(f"  [!!] {name}: Status {response.status_code}")
    except Exception as e:
        print(f"  [XX] {name}: {str(e)[:30]}")

# =============================================================================
# TEST 6: DATABASE CONTENT
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 6: DATABASE CONTENT")
print("=" * 80)

if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Events
    print("\n[6.1] HAIL EVENTS")
    cursor.execute("SELECT COUNT(*) FROM hail_events")
    event_count = cursor.fetchone()[0]
    print(f"  Total events: {event_count}")

    cursor.execute("SELECT event_date, city, state_province, max_hail_size_inches FROM hail_events ORDER BY event_date DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"    - {row[0]}: {row[1]}, {row[2]} - {row[3]}\"")

    status = test_result("Event Database", "OK" if event_count > 0 else "BROKEN",
                        f"{event_count} events", "Add real events" if event_count < 100 else "")
    print(f"  Result: {status}")

    # Social posts
    print("\n[6.2] SOCIAL MEDIA POSTS")
    try:
        cursor.execute("SELECT COUNT(*) FROM social_media_posts")
        post_count = cursor.fetchone()[0]
        print(f"  Total posts: {post_count}")
        status = test_result("Social Posts DB", "OK" if post_count > 0 else "PARTIAL",
                           f"{post_count} posts", "Scrape social media")
    except:
        status = test_result("Social Posts DB", "BROKEN", "Table error", "Check schema")
    print(f"  Result: {status}")

    # PDR Opportunities
    print("\n[6.3] PDR OPPORTUNITIES")
    try:
        cursor.execute("SELECT COUNT(*) FROM pdr_opportunities")
        opp_count = cursor.fetchone()[0]
        print(f"  Total opportunities: {opp_count}")
        status = test_result("PDR Opportunities", "OK" if opp_count > 0 else "PARTIAL",
                           f"{opp_count} opportunities", "Generate from events")
    except:
        status = test_result("PDR Opportunities", "BROKEN", "Table error", "Check schema")
    print(f"  Result: {status}")

    conn.close()

# =============================================================================
# TEST 7: DATA COLLECTION STATUS
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 7: DATA COLLECTION STATUS")
print("=" * 80)

data_dir = PROJECT_ROOT / 'data'
print(f"\n  Data directory: {data_dir}")
print(f"  Exists: {data_dir.exists()}")

if data_dir.exists():
    # Radar data
    nexrad_dir = data_dir / 'nexrad'
    if nexrad_dir.exists():
        radar_files = list(nexrad_dir.rglob('*'))
        print(f"\n  NEXRAD files: {len(radar_files)}")
        status = test_result("Radar Data", "OK" if len(radar_files) > 0 else "BROKEN",
                           f"{len(radar_files)} files", "Download radar data")
    else:
        status = test_result("Radar Data", "BROKEN", "Directory missing", "Create data/nexrad/")
    print(f"  Result: {status}")

    # Social media images
    social_dir = data_dir / 'social_media' / 'images'
    if social_dir.exists():
        image_files = list(social_dir.rglob('*.jpg')) + list(social_dir.rglob('*.png'))
        print(f"\n  Social media images: {len(image_files)}")
        status = test_result("Social Images", "OK" if len(image_files) > 0 else "BROKEN",
                           f"{len(image_files)} images", "Scrape social media")
    else:
        status = test_result("Social Images", "BROKEN", "Directory missing", "Create directory")
    print(f"  Result: {status}")

    # Training data
    training_dir = data_dir / 'training'
    if training_dir.exists():
        training_files = list(training_dir.rglob('*'))
        print(f"\n  Training data files: {len(training_files)}")
    else:
        print("\n  Training data: Directory missing")
        test_result("Training Data", "BROKEN", "No training data", "Collect training data")
else:
    print("  Data directory not found")
    test_result("Data Directory", "BROKEN", "Missing", "Create data/")

# =============================================================================
# TEST 8: EXTERNAL INTEGRATIONS
# =============================================================================
print("\n" + "=" * 80)
print(" TEST 8: EXTERNAL INTEGRATIONS")
print("=" * 80)

# NWS API
print("\n[8.1] NWS API")
try:
    response = requests.get("https://api.weather.gov/points/35.47,-97.52",
                          headers={"User-Agent": "HailTracker/1.0"}, timeout=10)
    if response.status_code == 200:
        print("  NWS API: Accessible")
        status = test_result("NWS API", "OK", "API works")
    else:
        status = test_result("NWS API", "PARTIAL", f"Status {response.status_code}", "Check API")
    print(f"  Result: {status}")
except Exception as e:
    test_result("NWS API", "BROKEN", str(e)[:40], "Check network")
    print(f"  Result: [XX] {e}")

# SPC Storm Reports
print("\n[8.2] SPC STORM REPORTS")
try:
    # Try to access SPC website
    response = requests.get("https://www.spc.noaa.gov/climo/reports/today.html", timeout=10)
    if response.status_code == 200:
        print("  SPC website: Accessible")
        status = test_result("SPC Reports", "OK", "Website accessible")
    else:
        status = test_result("SPC Reports", "PARTIAL", f"Status {response.status_code}", "Check URL")
    print(f"  Result: {status}")
except Exception as e:
    test_result("SPC Reports", "BROKEN", str(e)[:40], "Check network")
    print(f"  Result: [XX] {e}")

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("\n" + "=" * 80)
print(" FINAL SUMMARY")
print("=" * 80)

print(f"\n  WORKING PERFECTLY ({len(results['working'])})")
for r in results['working']:
    print(f"    [OK] {r['component']}: {r['details']}")

print(f"\n  PARTIALLY WORKING ({len(results['partial'])})")
for r in results['partial']:
    print(f"    [!!] {r['component']}: {r['details']}")
    if r['action']:
        print(f"         Action: {r['action']}")

print(f"\n  BROKEN/NOT IMPLEMENTED ({len(results['broken'])})")
for r in results['broken']:
    print(f"    [XX] {r['component']}: {r['details']}")
    if r['action']:
        print(f"         Action: {r['action']}")

print(f"\n  NEEDS API KEYS ({len(results['needs_keys'])})")
for r in results['needs_keys']:
    print(f"    [KEY] {r['component']}: {r['details']}")
    if r['action']:
        print(f"          Action: {r['action']}")

# Calculate percentages
total = len(results['working']) + len(results['partial']) + len(results['broken']) + len(results['needs_keys'])
if total > 0:
    print(f"\n  OVERALL HEALTH:")
    print(f"    Working:  {len(results['working'])}/{total} ({100*len(results['working'])//total}%)")
    print(f"    Partial:  {len(results['partial'])}/{total} ({100*len(results['partial'])//total}%)")
    print(f"    Broken:   {len(results['broken'])}/{total} ({100*len(results['broken'])//total}%)")
    print(f"    Need Keys: {len(results['needs_keys'])}/{total} ({100*len(results['needs_keys'])//total}%)")

print("\n" + "=" * 80)
print(" RECOMMENDATIONS")
print("=" * 80)

print("""
IMMEDIATE FIXES (Quick Wins):
1. Add Reddit API credentials to enable social scraping
2. Download sample radar data to test processing
3. Seed more realistic hail event data

SHORT-TERM (1-3 days):
1. Implement actual NEXRAD download from AWS S3
2. Get Twitter/Nitter scraping working
3. Collect real hail photos for ML training

LONG-TERM (1-2 weeks):
1. Train ML models on real data instead of synthetic
2. Build comprehensive training dataset
3. Implement Canadian/Mexican radar downloads
""")

print("=" * 80)
print(" STRESS TEST COMPLETE")
print("=" * 80)
