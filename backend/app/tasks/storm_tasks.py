"""
Storm Processing Tasks
======================
Background tasks for discovering businesses in storm swaths.
"""

import os
from datetime import datetime, timedelta
from app.celery_app import celery_app
from app.extensions import db
from app.models.master.storm import Storm
from app.models.master.swath import Swath
from app.models.master.business import Business, StormBusiness
from app.services.usage_service import UsageService


@celery_app.task(bind=True, max_retries=3)
def process_storm(self, storm_id):
    """
    Process a storm - discover all businesses in the swaths.
    This is the main background job.

    Args:
        storm_id: Storm ID to process

    Returns:
        Result dictionary with processing stats
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        storm = Storm.query.get(storm_id)
        if not storm:
            return {'error': 'Storm not found'}

        if storm.status == 'ready':
            return {'message': 'Storm already processed'}

        try:
            # Mark as processing
            storm.status = 'processing'
            db.session.commit()

            self.update_state(state='PROGRESS', meta={'status': 'Starting discovery...'})

            # Get swaths
            swaths = Swath.query.filter_by(storm_id=storm_id).all()
            if not swaths:
                storm.status = 'failed'
                db.session.commit()
                return {'error': 'No swaths found for storm'}

            total_businesses = 0

            # Prepare swath data
            swath_data = []
            for swath in swaths:
                if swath.polygon and swath.center_lat and swath.center_lon:
                    swath_data.append({
                        'id': swath.id,
                        'polygon': swath.polygon,
                        'center_lat': float(swath.center_lat),
                        'center_lon': float(swath.center_lon),
                        'city': swath.city,
                        'state': swath.state
                    })

            if not swath_data:
                storm.status = 'failed'
                db.session.commit()
                return {'error': 'No valid swath polygons'}

            self.update_state(state='PROGRESS', meta={
                'status': f'Processing {len(swath_data)} swaths...',
                'swaths': len(swath_data)
            })

            # Discover businesses
            businesses = discover_businesses_for_swaths(swath_data, self)

            self.update_state(state='PROGRESS', meta={
                'status': f'Saving {len(businesses)} businesses...',
                'businesses_found': len(businesses)
            })

            # Save to database
            saved_count = save_businesses_to_db(storm_id, businesses)

            # Update storm status
            storm.status = 'ready'
            storm.processed_at = datetime.utcnow()
            storm.expires_at = datetime.utcnow() + timedelta(days=29)
            storm.business_count = saved_count
            db.session.commit()

            return {
                'success': True,
                'storm_id': storm_id,
                'businesses_found': len(businesses),
                'businesses_saved': saved_count,
                'swaths_processed': len(swath_data)
            }

        except Exception as e:
            storm.status = 'failed'
            db.session.commit()

            # Retry with exponential backoff
            self.retry(exc=e, countdown=60)


def discover_businesses_for_swaths(swath_data, task=None):
    """
    Run business discovery across all configured APIs.

    Args:
        swath_data: List of swath dictionaries
        task: Optional Celery task for progress updates

    Returns:
        List of discovered businesses
    """
    from app import create_app
    app = create_app()

    all_businesses = []

    with app.app_context():
        # Calculate bounding box
        min_lat = min(s['center_lat'] for s in swath_data)
        max_lat = max(s['center_lat'] for s in swath_data)
        min_lon = min(s['center_lon'] for s in swath_data)
        max_lon = max(s['center_lon'] for s in swath_data)

        center_lat = (min_lat + max_lat) / 2
        center_lon = (min_lon + max_lon) / 2

        # Calculate search radius
        lat_diff = max_lat - min_lat
        lon_diff = max_lon - min_lon
        radius_meters = int(max(lat_diff, lon_diff) * 111000 / 2)
        radius_meters = min(radius_meters, 40000)  # Cap at 40km

        # Search OSM (always free)
        if task:
            task.update_state(state='PROGRESS', meta={'status': 'Searching OSM...'})
        osm_results = search_osm(min_lat, min_lon, max_lat, max_lon)
        all_businesses.extend(osm_results)
        UsageService.log_api_call('osm', 1)

        # Search Yelp (if available and under limit)
        if UsageService.check_can_use_api('yelp'):
            if task:
                task.update_state(state='PROGRESS', meta={'status': 'Searching Yelp...'})
            yelp_results = search_yelp(center_lat, center_lon, radius_meters)
            all_businesses.extend(yelp_results)
            UsageService.log_api_call('yelp', len(yelp_results) // 50 + 1)

        # Search HERE (if available)
        if UsageService.check_can_use_api('here'):
            if task:
                task.update_state(state='PROGRESS', meta={'status': 'Searching HERE...'})
            here_results = search_here(center_lat, center_lon, radius_meters)
            all_businesses.extend(here_results)
            UsageService.log_api_call('here', len(here_results) // 50 + 1)

        # Search TomTom (if available)
        if UsageService.check_can_use_api('tomtom'):
            if task:
                task.update_state(state='PROGRESS', meta={'status': 'Searching TomTom...'})
            tomtom_results = search_tomtom(center_lat, center_lon, radius_meters)
            all_businesses.extend(tomtom_results)
            UsageService.log_api_call('tomtom', len(tomtom_results) // 50 + 1)

        # Search Google (if available - most expensive, use sparingly)
        if UsageService.check_can_use_api('google'):
            if task:
                task.update_state(state='PROGRESS', meta={'status': 'Searching Google...'})
            google_results = search_google(center_lat, center_lon, radius_meters)
            all_businesses.extend(google_results)
            UsageService.log_api_call('google', len(google_results) // 20 + 1)

        # Deduplicate
        unique_businesses = deduplicate_businesses(all_businesses)

        return unique_businesses


def search_osm(min_lat, min_lon, max_lat, max_lon):
    """Search OpenStreetMap via Overpass API."""
    import requests

    query = f"""
    [out:json][timeout:60];
    (
      node["shop"](({min_lat},{min_lon},{max_lat},{max_lon}));
      node["office"](({min_lat},{min_lon},{max_lat},{max_lon}));
      node["craft"](({min_lat},{min_lon},{max_lat},{max_lon}));
      node["amenity"~"car_rental|fuel|car_wash|police|fire_station|veterinary"](({min_lat},{min_lon},{max_lat},{max_lon}));
      way["shop"](({min_lat},{min_lon},{max_lat},{max_lon}));
      way["office"](({min_lat},{min_lon},{max_lat},{max_lon}));
      way["amenity"~"car_rental|fuel|car_wash|police|fire_station"](({min_lat},{min_lon},{max_lat},{max_lon}));
    );
    out center;
    """

    servers = [
        'https://overpass-api.de/api/interpreter',
        'https://overpass.kumi.systems/api/interpreter',
    ]

    for server in servers:
        try:
            response = requests.post(server, data={'data': query}, timeout=60)
            if response.status_code == 200:
                data = response.json()
                return parse_osm_results(data.get('elements', []))
        except Exception:
            continue

    return []


def parse_osm_results(elements):
    """Parse OSM response into standard format."""
    results = []

    for el in elements:
        tags = el.get('tags', {})
        name = tags.get('name')
        if not name:
            continue

        lat = el.get('lat') or el.get('center', {}).get('lat')
        lon = el.get('lon') or el.get('center', {}).get('lon')

        category = (tags.get('shop') or tags.get('office') or
                    tags.get('craft') or tags.get('amenity') or 'other')

        results.append({
            'name': name,
            'category': category,
            'address': f"{tags.get('addr:housenumber', '')} {tags.get('addr:street', '')}".strip(),
            'city': tags.get('addr:city', ''),
            'state': tags.get('addr:state', ''),
            'zip': tags.get('addr:postcode', ''),
            'phone': tags.get('phone', ''),
            'email': tags.get('email', ''),
            'website': tags.get('website', ''),
            'lat': lat,
            'lon': lon,
            'source': 'osm',
            'source_id': f"osm_{el.get('id')}"
        })

    return results


def search_yelp(lat, lon, radius_meters):
    """Search Yelp API."""
    import requests

    api_key = os.getenv('YELP_API_KEY')
    if not api_key:
        return []

    headers = {'Authorization': f'Bearer {api_key}'}

    categories = [
        'hvac,plumbing,electricians',
        'landscaping,lawn_services,tree_services',
        'roofing,contractors,pest_control',
        'towing,auto_repair,car_dealers'
    ]

    all_results = []

    for cat_group in categories:
        try:
            response = requests.get(
                'https://api.yelp.com/v3/businesses/search',
                headers=headers,
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'radius': min(radius_meters, 40000),
                    'categories': cat_group,
                    'limit': 50
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                for biz in data.get('businesses', []):
                    loc = biz.get('location', {})
                    coords = biz.get('coordinates', {})

                    all_results.append({
                        'name': biz.get('name', ''),
                        'category': biz.get('categories', [{}])[0].get('title', ''),
                        'address': loc.get('address1', ''),
                        'city': loc.get('city', ''),
                        'state': loc.get('state', ''),
                        'zip': loc.get('zip_code', ''),
                        'phone': biz.get('phone', ''),
                        'email': '',
                        'website': biz.get('url', ''),
                        'lat': coords.get('latitude'),
                        'lon': coords.get('longitude'),
                        'source': 'yelp',
                        'source_id': f"yelp_{biz.get('id')}"
                    })
        except Exception:
            continue

    return all_results


def search_here(lat, lon, radius_meters):
    """Search HERE Places API."""
    import requests

    api_key = os.getenv('HERE_API_KEY')
    if not api_key:
        return []

    search_terms = ['hvac', 'plumber', 'electrician', 'landscaping', 'roofing', 'towing']
    all_results = []

    for term in search_terms:
        try:
            response = requests.get(
                'https://discover.search.hereapi.com/v1/discover',
                params={
                    'at': f'{lat},{lon}',
                    'q': term,
                    'limit': 50,
                    'apiKey': api_key
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get('items', []):
                    address = item.get('address', {})
                    position = item.get('position', {})

                    all_results.append({
                        'name': item.get('title', ''),
                        'category': term,
                        'address': address.get('label', ''),
                        'city': address.get('city', ''),
                        'state': address.get('state', ''),
                        'zip': address.get('postalCode', ''),
                        'phone': '',
                        'email': '',
                        'website': '',
                        'lat': position.get('lat'),
                        'lon': position.get('lng'),
                        'source': 'here',
                        'source_id': f"here_{item.get('id')}"
                    })
        except Exception:
            continue

    return all_results


def search_tomtom(lat, lon, radius_meters):
    """Search TomTom API."""
    import requests

    api_key = os.getenv('TOMTOM_API_KEY')
    if not api_key:
        return []

    search_terms = ['hvac', 'plumber', 'electrician', 'landscaping', 'roofing', 'towing']
    all_results = []

    for term in search_terms:
        try:
            response = requests.get(
                f'https://api.tomtom.com/search/2/poiSearch/{term}.json',
                params={
                    'key': api_key,
                    'lat': lat,
                    'lon': lon,
                    'radius': radius_meters,
                    'limit': 50
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get('results', []):
                    address = item.get('address', {})
                    position = item.get('position', {})
                    poi = item.get('poi', {})

                    all_results.append({
                        'name': poi.get('name', ''),
                        'category': term,
                        'address': address.get('freeformAddress', ''),
                        'city': address.get('municipality', ''),
                        'state': address.get('countrySubdivision', ''),
                        'zip': address.get('postalCode', ''),
                        'phone': poi.get('phone', ''),
                        'email': '',
                        'website': poi.get('url', ''),
                        'lat': position.get('lat'),
                        'lon': position.get('lon'),
                        'source': 'tomtom',
                        'source_id': f"tomtom_{item.get('id')}"
                    })
        except Exception:
            continue

    return all_results


def search_google(lat, lon, radius_meters):
    """Search Google Places API."""
    import requests

    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        return []

    keywords = ['hvac contractor', 'plumber', 'electrician', 'landscaping', 'roofing', 'towing']
    all_results = []

    for keyword in keywords:
        try:
            response = requests.get(
                'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
                params={
                    'location': f'{lat},{lon}',
                    'radius': min(radius_meters, 50000),
                    'keyword': keyword,
                    'key': api_key
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                for place in data.get('results', []):
                    location = place.get('geometry', {}).get('location', {})

                    all_results.append({
                        'name': place.get('name', ''),
                        'category': keyword,
                        'address': place.get('vicinity', ''),
                        'city': '',
                        'state': '',
                        'zip': '',
                        'phone': '',
                        'email': '',
                        'website': '',
                        'lat': location.get('lat'),
                        'lon': location.get('lng'),
                        'source': 'google',
                        'source_id': f"google_{place.get('place_id')}"
                    })
        except Exception:
            continue

    return all_results


def deduplicate_businesses(businesses):
    """Remove duplicate businesses based on name and location."""
    seen = set()
    unique = []

    for biz in businesses:
        # Create key from normalized name and location
        name_key = ''.join(c for c in biz['name'].lower() if c.isalnum())[:20]
        lat_key = round(biz.get('lat') or 0, 3)
        lon_key = round(biz.get('lon') or 0, 3)
        key = f"{name_key}_{lat_key}_{lon_key}"

        if key not in seen:
            seen.add(key)
            unique.append(biz)

    return unique


def save_businesses_to_db(storm_id, businesses):
    """Save discovered businesses to database."""
    from app import create_app
    app = create_app()

    saved = 0

    with app.app_context():
        for biz_data in businesses:
            # Check if business exists
            existing = Business.query.filter_by(
                source=biz_data['source'],
                source_id=biz_data['source_id']
            ).first()

            if existing:
                business = existing
            else:
                business = Business(
                    name=biz_data['name'],
                    category=biz_data.get('category'),
                    address=biz_data.get('address'),
                    city=biz_data.get('city'),
                    state=biz_data.get('state'),
                    zip=biz_data.get('zip'),
                    phone=biz_data.get('phone'),
                    email=biz_data.get('email'),
                    website=biz_data.get('website'),
                    lat=biz_data.get('lat'),
                    lon=biz_data.get('lon'),
                    source=biz_data['source'],
                    source_id=biz_data['source_id']
                )
                db.session.add(business)
                db.session.flush()

            # Link to storm
            existing_link = StormBusiness.query.filter_by(
                storm_id=storm_id,
                business_id=business.id
            ).first()

            if not existing_link:
                link = StormBusiness(
                    storm_id=storm_id,
                    business_id=business.id,
                    in_swath=True
                )
                db.session.add(link)
                saved += 1

        db.session.commit()

    return saved


@celery_app.task(bind=True)
def reprocess_storm(self, storm_id):
    """
    Reprocess an expired or failed storm.
    Clears existing data and runs discovery again.

    Args:
        storm_id: Storm ID to reprocess

    Returns:
        Result from process_storm
    """
    from app import create_app
    app = create_app()

    with app.app_context():
        storm = Storm.query.get(storm_id)
        if not storm:
            return {'error': 'Storm not found'}

        # Clear existing links
        StormBusiness.query.filter_by(storm_id=storm_id).delete()

        # Reset status
        storm.status = 'pending'
        storm.processed_at = None
        storm.expires_at = None
        storm.business_count = 0
        db.session.commit()

        # Process again
        return process_storm(storm_id)
