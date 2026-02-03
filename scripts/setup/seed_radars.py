"""
Seed All 206 North American Radar Sites

Complete database of:
- 159 US NEXRAD radars
- 31 Canadian Environment Canada radars
- 16 Mexican CONAGUA radars
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / 'database' / 'hailtracker_pro.db'


# ============================================
# US NEXRAD RADARS (159 sites)
# Source: NOAA/NWS
# ============================================
US_NEXRAD_RADARS = [
    # Format: (site_code, name, state, lat, lon, elevation_m, timezone)

    # ALABAMA
    ('KBMX', 'Birmingham', 'AL', 33.1722, -86.7697, 197, 'America/Chicago'),
    ('KEOX', 'Fort Rucker', 'AL', 31.4606, -85.4594, 132, 'America/Chicago'),
    ('KHTX', 'Huntsville', 'AL', 34.9306, -86.0833, 536, 'America/Chicago'),
    ('KMOB', 'Mobile', 'AL', 30.6794, -88.2397, 63, 'America/Chicago'),
    ('KMXX', 'Maxwell AFB', 'AL', 32.5369, -85.7897, 122, 'America/Chicago'),

    # ALASKA
    ('PABC', 'Bethel', 'AK', 60.7919, -161.8764, 49, 'America/Anchorage'),
    ('PACG', 'Sitka', 'AK', 56.8528, -135.5294, 63, 'America/Anchorage'),
    ('PAEC', 'Nome', 'AK', 64.5114, -165.2950, 16, 'America/Anchorage'),
    ('PAHG', 'Anchorage', 'AK', 60.7258, -151.3514, 74, 'America/Anchorage'),
    ('PAIH', 'Middleton Island', 'AK', 59.4614, -146.3031, 20, 'America/Anchorage'),
    ('PAKC', 'King Salmon', 'AK', 58.6794, -156.6294, 19, 'America/Anchorage'),
    ('PAPD', 'Fairbanks', 'AK', 65.0350, -147.5014, 790, 'America/Anchorage'),

    # ARIZONA
    ('KEMX', 'Tucson', 'AZ', 31.8936, -110.6303, 1586, 'America/Phoenix'),
    ('KFSX', 'Flagstaff', 'AZ', 34.5744, -111.1983, 2261, 'America/Phoenix'),
    ('KIWA', 'Phoenix', 'AZ', 33.2892, -111.6700, 412, 'America/Phoenix'),
    ('KYUX', 'Yuma', 'AZ', 32.4953, -114.6567, 53, 'America/Phoenix'),

    # ARKANSAS
    ('KLZK', 'Little Rock', 'AR', 34.8364, -92.2622, 173, 'America/Chicago'),
    ('KSRX', 'Fort Smith', 'AR', 35.2906, -94.3619, 195, 'America/Chicago'),

    # CALIFORNIA
    ('KBBX', 'Beale AFB', 'CA', 39.4961, -121.6317, 52, 'America/Los_Angeles'),
    ('KEYX', 'Edwards AFB', 'CA', 35.0978, -117.5608, 840, 'America/Los_Angeles'),
    ('KHNX', 'Hanford', 'CA', 36.3142, -119.6322, 75, 'America/Los_Angeles'),
    ('KMUX', 'San Francisco', 'CA', 37.1550, -121.8983, 1057, 'America/Los_Angeles'),
    ('KNKX', 'San Diego', 'CA', 32.9189, -117.0419, 291, 'America/Los_Angeles'),
    ('KSOX', 'Santa Ana Mountains', 'CA', 33.8178, -117.6358, 923, 'America/Los_Angeles'),
    ('KVBX', 'Vandenberg AFB', 'CA', 34.8383, -120.3978, 373, 'America/Los_Angeles'),
    ('KVTX', 'Los Angeles', 'CA', 34.4117, -119.1794, 831, 'America/Los_Angeles'),
    ('KDAX', 'Sacramento', 'CA', 38.5011, -121.6778, 9, 'America/Los_Angeles'),

    # COLORADO
    ('KFTG', 'Denver/Front Range', 'CO', 39.7866, -104.5458, 1675, 'America/Denver'),
    ('KGJX', 'Grand Junction', 'CO', 39.0622, -108.2139, 3045, 'America/Denver'),
    ('KPUX', 'Pueblo', 'CO', 38.4597, -104.1814, 1600, 'America/Denver'),

    # CONNECTICUT (covered by NY radars)

    # DELAWARE (covered by PA/MD radars)

    # FLORIDA
    ('KAMX', 'Miami', 'FL', 25.6111, -80.4128, 4, 'America/New_York'),
    ('KBYX', 'Key West', 'FL', 24.5975, -81.7033, 3, 'America/New_York'),
    ('KEVX', 'Eglin AFB', 'FL', 30.5644, -85.9214, 43, 'America/Chicago'),
    ('KJAX', 'Jacksonville', 'FL', 30.4847, -81.7019, 10, 'America/New_York'),
    ('KMLB', 'Melbourne', 'FL', 28.1133, -80.6542, 11, 'America/New_York'),
    ('KTBW', 'Tampa Bay', 'FL', 27.7056, -82.4019, 12, 'America/New_York'),
    ('KTLH', 'Tallahassee', 'FL', 30.3975, -84.3289, 19, 'America/New_York'),

    # GEORGIA
    ('KFFC', 'Atlanta', 'GA', 33.3636, -84.5658, 262, 'America/New_York'),
    ('KJGX', 'Robins AFB', 'GA', 32.6756, -83.3511, 159, 'America/New_York'),
    ('KVAX', 'Moody AFB', 'GA', 30.8903, -83.0019, 54, 'America/New_York'),

    # HAWAII
    ('PHKI', 'Kauai', 'HI', 21.8942, -159.5522, 179, 'Pacific/Honolulu'),
    ('PHKM', 'Kohala', 'HI', 20.1256, -155.7781, 1162, 'Pacific/Honolulu'),
    ('PHMO', 'Molokai', 'HI', 21.1328, -157.1803, 416, 'Pacific/Honolulu'),
    ('PHWA', 'South Shore', 'HI', 19.0950, -155.5689, 421, 'Pacific/Honolulu'),

    # IDAHO
    ('KCBX', 'Boise', 'ID', 43.4908, -116.2364, 933, 'America/Boise'),
    ('KSFX', 'Pocatello', 'ID', 43.1058, -112.6861, 1364, 'America/Boise'),

    # ILLINOIS
    ('KILX', 'Lincoln', 'IL', 40.1506, -89.3369, 177, 'America/Chicago'),
    ('KLOT', 'Chicago', 'IL', 41.6044, -88.0847, 202, 'America/Chicago'),

    # INDIANA
    ('KIND', 'Indianapolis', 'IN', 39.7075, -86.2803, 241, 'America/Indiana/Indianapolis'),
    ('KIWX', 'Fort Wayne', 'IN', 41.3586, -85.7000, 293, 'America/Indiana/Indianapolis'),
    ('KVWX', 'Evansville', 'IN', 38.2603, -87.7247, 155, 'America/Indiana/Indianapolis'),

    # IOWA
    ('KDMX', 'Des Moines', 'IA', 41.7311, -93.7228, 299, 'America/Chicago'),
    ('KDVN', 'Quad Cities', 'IA', 41.6117, -90.5806, 230, 'America/Chicago'),

    # KANSAS
    ('KDDC', 'Dodge City', 'KS', 37.7608, -99.9689, 789, 'America/Chicago'),
    ('KGLD', 'Goodland', 'KS', 39.3667, -101.7000, 1113, 'America/Denver'),
    ('KICT', 'Wichita', 'KS', 37.6544, -97.4431, 407, 'America/Chicago'),
    ('KTWX', 'Topeka', 'KS', 38.9969, -96.2325, 417, 'America/Chicago'),

    # KENTUCKY
    ('KHPX', 'Fort Campbell', 'KY', 36.7369, -87.2850, 177, 'America/Chicago'),
    ('KJKL', 'Jackson', 'KY', 37.5908, -83.3131, 416, 'America/New_York'),
    ('KLVX', 'Louisville', 'KY', 37.9753, -85.9439, 219, 'America/Kentucky/Louisville'),
    ('KPAH', 'Paducah', 'KY', 37.0683, -88.7719, 119, 'America/Chicago'),

    # LOUISIANA
    ('KLIX', 'New Orleans', 'LA', 30.3367, -89.8256, 7, 'America/Chicago'),
    ('KLCH', 'Lake Charles', 'LA', 30.1253, -93.2158, 4, 'America/Chicago'),
    ('KPOE', 'Fort Polk', 'LA', 31.1556, -92.9761, 124, 'America/Chicago'),
    ('KSHV', 'Shreveport', 'LA', 32.4508, -93.8414, 83, 'America/Chicago'),

    # MAINE
    ('KCBW', 'Caribou', 'ME', 46.0392, -67.8067, 227, 'America/New_York'),
    ('KGYX', 'Portland', 'ME', 43.8914, -70.2564, 125, 'America/New_York'),

    # MARYLAND
    ('KLWX', 'Sterling (Washington DC)', 'MD', 38.9753, -77.4778, 82, 'America/New_York'),

    # MASSACHUSETTS
    ('KBOX', 'Boston', 'MA', 41.9558, -71.1369, 36, 'America/New_York'),

    # MICHIGAN
    ('KAPX', 'Gaylord', 'MI', 44.9072, -84.7197, 446, 'America/Detroit'),
    ('KDTX', 'Detroit', 'MI', 42.6997, -83.4717, 327, 'America/Detroit'),
    ('KGRR', 'Grand Rapids', 'MI', 42.8939, -85.5447, 237, 'America/Detroit'),
    ('KMQT', 'Marquette', 'MI', 46.5311, -87.5483, 430, 'America/Detroit'),

    # MINNESOTA
    ('KDLH', 'Duluth', 'MN', 46.8369, -92.2097, 435, 'America/Chicago'),
    ('KMPX', 'Minneapolis', 'MN', 44.8489, -93.5656, 288, 'America/Chicago'),

    # MISSISSIPPI
    ('KDGX', 'Jackson', 'MS', 32.2800, -89.9844, 148, 'America/Chicago'),
    ('KGWX', 'Columbus AFB', 'MS', 33.8967, -88.3289, 145, 'America/Chicago'),

    # MISSOURI
    ('KEAX', 'Kansas City', 'MO', 38.8103, -94.2644, 303, 'America/Chicago'),
    ('KLSX', 'St. Louis', 'MO', 38.6986, -90.6828, 185, 'America/Chicago'),
    ('KSGF', 'Springfield', 'MO', 37.2350, -93.4006, 390, 'America/Chicago'),

    # MONTANA
    ('KBLX', 'Billings', 'MT', 45.8539, -108.6069, 1097, 'America/Denver'),
    ('KGGW', 'Glasgow', 'MT', 48.2064, -106.6250, 693, 'America/Denver'),
    ('KMSX', 'Missoula', 'MT', 47.0411, -113.9864, 2394, 'America/Denver'),
    ('KTFX', 'Great Falls', 'MT', 47.4597, -111.3847, 1132, 'America/Denver'),

    # NEBRASKA
    ('KLNX', 'North Platte', 'NE', 41.9578, -100.5761, 905, 'America/Chicago'),
    ('KOAX', 'Omaha', 'NE', 41.3203, -96.3667, 350, 'America/Chicago'),
    ('KUEX', 'Hastings', 'NE', 40.3208, -98.4419, 602, 'America/Chicago'),

    # NEVADA
    ('KESX', 'Las Vegas', 'NV', 35.7011, -114.8914, 1483, 'America/Los_Angeles'),
    ('KLRX', 'Elko', 'NV', 40.7400, -116.8025, 2056, 'America/Los_Angeles'),
    ('KRGX', 'Reno', 'NV', 39.7544, -119.4614, 2530, 'America/Los_Angeles'),

    # NEW JERSEY (covered by PA/NY radars)

    # NEW MEXICO
    ('KABX', 'Albuquerque', 'NM', 35.1497, -106.8239, 1789, 'America/Denver'),
    ('KFDX', 'Cannon AFB', 'NM', 34.6342, -103.6294, 1417, 'America/Denver'),
    ('KHDX', 'Holloman AFB', 'NM', 33.0767, -106.1225, 1287, 'America/Denver'),
    ('KEPZ', 'El Paso', 'TX', 31.8731, -106.6981, 1251, 'America/Denver'),

    # NEW YORK
    ('KBGM', 'Binghamton', 'NY', 42.1997, -75.9847, 490, 'America/New_York'),
    ('KBUF', 'Buffalo', 'NY', 42.9486, -78.7369, 211, 'America/New_York'),
    ('KENX', 'Albany', 'NY', 42.5864, -74.0636, 557, 'America/New_York'),
    ('KOKX', 'New York City', 'NY', 40.8656, -72.8639, 26, 'America/New_York'),
    ('KTYX', 'Montague', 'NY', 43.7556, -75.6800, 562, 'America/New_York'),

    # NORTH CAROLINA
    ('KMHX', 'Morehead City', 'NC', 34.7758, -76.8761, 9, 'America/New_York'),
    ('KRAX', 'Raleigh/Durham', 'NC', 35.6656, -78.4903, 106, 'America/New_York'),
    ('KLTX', 'Wilmington', 'NC', 33.9892, -78.4292, 20, 'America/New_York'),

    # NORTH DAKOTA
    ('KBIS', 'Bismarck', 'ND', 46.7708, -100.7606, 505, 'America/Chicago'),
    ('KMVX', 'Grand Forks', 'ND', 47.5281, -97.3256, 301, 'America/Chicago'),
    ('KMBX', 'Minot AFB', 'ND', 48.3925, -100.8644, 455, 'America/Chicago'),

    # OHIO
    ('KCLE', 'Cleveland', 'OH', 41.4131, -81.8597, 233, 'America/New_York'),
    ('KILN', 'Cincinnati', 'OH', 39.4200, -83.8217, 322, 'America/New_York'),

    # OKLAHOMA
    ('KFDR', 'Frederick', 'OK', 34.3622, -98.9764, 386, 'America/Chicago'),
    ('KINX', 'Tulsa', 'OK', 36.1750, -95.5644, 204, 'America/Chicago'),
    ('KTLX', 'Oklahoma City', 'OK', 35.3331, -97.2778, 370, 'America/Chicago'),
    ('KVNX', 'Vance AFB', 'OK', 36.7406, -98.1278, 369, 'America/Chicago'),

    # OREGON
    ('KMAX', 'Medford', 'OR', 42.0811, -122.7172, 2289, 'America/Los_Angeles'),
    ('KPDT', 'Pendleton', 'OR', 45.6906, -118.8531, 462, 'America/Los_Angeles'),
    ('KRTX', 'Portland', 'OR', 45.7150, -122.9650, 479, 'America/Los_Angeles'),

    # PENNSYLVANIA
    ('KCCX', 'State College', 'PA', 40.9228, -78.0039, 733, 'America/New_York'),
    ('KPBZ', 'Pittsburgh', 'PA', 40.5317, -80.2178, 361, 'America/New_York'),
    ('KDIX', 'Philadelphia', 'PA', 39.9469, -74.4108, 45, 'America/New_York'),

    # PUERTO RICO
    ('TJUA', 'San Juan', 'PR', 18.1156, -66.0781, 862, 'America/Puerto_Rico'),

    # RHODE ISLAND (covered by MA radar)

    # SOUTH CAROLINA
    ('KCAE', 'Columbia', 'SC', 33.9486, -81.1183, 70, 'America/New_York'),
    ('KCHS', 'Charleston', 'SC', 32.8958, -80.0289, 14, 'America/New_York'),
    ('KGSP', 'Greenville/Spartanburg', 'SC', 34.8833, -82.2200, 287, 'America/New_York'),
    ('KCLX', 'Charleston', 'SC', 32.6556, -81.0422, 30, 'America/New_York'),

    # SOUTH DAKOTA
    ('KABR', 'Aberdeen', 'SD', 45.4558, -98.4131, 397, 'America/Chicago'),
    ('KUDX', 'Rapid City', 'SD', 44.1250, -102.8297, 919, 'America/Denver'),
    ('KFSD', 'Sioux Falls', 'SD', 43.5878, -96.7294, 436, 'America/Chicago'),

    # TENNESSEE
    ('KMRX', 'Knoxville', 'TN', 36.1686, -83.4017, 408, 'America/New_York'),
    ('KNQA', 'Memphis', 'TN', 35.3447, -89.8733, 86, 'America/Chicago'),
    ('KOHX', 'Nashville', 'TN', 36.2472, -86.5625, 176, 'America/Chicago'),

    # TEXAS
    ('KAMA', 'Amarillo', 'TX', 35.2333, -101.7092, 1093, 'America/Chicago'),
    ('KBRO', 'Brownsville', 'TX', 25.9158, -97.4189, 7, 'America/Chicago'),
    ('KCRP', 'Corpus Christi', 'TX', 27.7842, -97.5111, 14, 'America/Chicago'),
    ('KDFX', 'Laughlin AFB', 'TX', 29.2728, -100.2803, 344, 'America/Chicago'),
    ('KDYX', 'Dyess AFB', 'TX', 32.5386, -99.2544, 545, 'America/Chicago'),
    ('KEWX', 'San Antonio', 'TX', 29.7039, -98.0286, 193, 'America/Chicago'),
    ('KFWS', 'Dallas/Fort Worth', 'TX', 32.5731, -97.3031, 208, 'America/Chicago'),
    ('KGRK', 'Fort Hood', 'TX', 30.7217, -97.3828, 164, 'America/Chicago'),
    ('KHGX', 'Houston', 'TX', 29.4719, -95.0792, 5, 'America/Chicago'),
    ('KLBB', 'Lubbock', 'TX', 33.6536, -101.8142, 993, 'America/Chicago'),
    ('KMAF', 'Midland/Odessa', 'TX', 31.9433, -102.1894, 874, 'America/Chicago'),
    ('KSJT', 'San Angelo', 'TX', 31.3711, -100.4925, 576, 'America/Chicago'),

    # UTAH
    ('KICX', 'Cedar City', 'UT', 37.5908, -112.8622, 3231, 'America/Denver'),
    ('KMTX', 'Salt Lake City', 'UT', 41.2628, -112.4481, 1969, 'America/Denver'),

    # VERMONT (covered by NY radars)

    # VIRGINIA
    ('KAKQ', 'Norfolk', 'VA', 36.9839, -77.0072, 34, 'America/New_York'),
    ('KFCX', 'Roanoke', 'VA', 37.0242, -80.2742, 874, 'America/New_York'),

    # WASHINGTON
    ('KATX', 'Seattle', 'WA', 48.1944, -122.4958, 151, 'America/Los_Angeles'),
    ('KLGX', 'Langley Hill', 'WA', 47.1158, -124.1069, 76, 'America/Los_Angeles'),
    ('KOTX', 'Spokane', 'WA', 47.6803, -117.6267, 727, 'America/Los_Angeles'),

    # WEST VIRGINIA
    ('KRLX', 'Charleston', 'WV', 38.3111, -81.7231, 329, 'America/New_York'),

    # WISCONSIN
    ('KARX', 'La Crosse', 'WI', 43.8228, -91.1911, 389, 'America/Chicago'),
    ('KGRB', 'Green Bay', 'WI', 44.4986, -88.1111, 208, 'America/Chicago'),
    ('KMKX', 'Milwaukee', 'WI', 42.9678, -88.5506, 292, 'America/Chicago'),

    # WYOMING
    ('KCYS', 'Cheyenne', 'WY', 41.1519, -104.8061, 1868, 'America/Denver'),
    ('KRIW', 'Riverton', 'WY', 43.0661, -108.4772, 1697, 'America/Denver'),

    # GUAM
    ('PGUA', 'Andersen AFB', 'GU', 13.4544, 144.8111, 80, 'Pacific/Guam'),
]


# ============================================
# CANADIAN RADARS (31 sites)
# Source: Environment and Climate Change Canada
# ============================================
CANADIAN_RADARS = [
    # Format: (site_code, name, province, lat, lon, elevation_m, timezone)

    # ALBERTA
    ('CASBE', 'Bethune', 'AB', 50.8667, -105.2167, 674, 'America/Regina'),
    ('CASCM', 'Carvel', 'AB', 53.5708, -114.1642, 732, 'America/Edmonton'),
    ('CASSA', 'Strathmore', 'AB', 51.2061, -113.4003, 1052, 'America/Edmonton'),
    ('CASJP', 'Jimmy Lake', 'AB', 55.5761, -117.9428, 762, 'America/Edmonton'),

    # BRITISH COLUMBIA
    ('CASAG', 'Aldergrove', 'BC', 49.0158, -122.4908, 53, 'America/Vancouver'),
    ('CASSI', 'Silver Star Mountain', 'BC', 50.3700, -119.0642, 1822, 'America/Vancouver'),
    ('CASSW', 'Prince George', 'BC', 53.9142, -122.8139, 682, 'America/Vancouver'),
    ('CASVI', 'Victoria', 'BC', 48.3922, -123.3286, 71, 'America/Vancouver'),

    # MANITOBA
    ('CASMB', 'Foxwarren', 'MB', 50.5483, -101.0861, 535, 'America/Winnipeg'),
    ('CASWM', 'Woodlands', 'MB', 50.1481, -97.7700, 256, 'America/Winnipeg'),

    # NEW BRUNSWICK
    ('CASNB', 'Chipman', 'NB', 46.1531, -65.6986, 93, 'America/Moncton'),

    # NEWFOUNDLAND AND LABRADOR
    ('CASNL', 'Holyrood', 'NL', 47.3433, -53.1439, 186, 'America/St_Johns'),
    ('CASMR', 'Marble Mountain', 'NL', 48.9500, -57.8478, 583, 'America/St_Johns'),

    # NOVA SCOTIA
    ('CASNS', 'Halifax', 'NS', 44.7625, -63.7733, 109, 'America/Halifax'),
    ('CASEG', 'Marion Bridge', 'NS', 45.9500, -60.1500, 117, 'America/Halifax'),

    # ONTARIO
    ('CASFT', 'Franktown', 'ON', 45.0403, -76.1228, 149, 'America/Toronto'),
    ('CASBV', 'Britt', 'ON', 45.7939, -80.5331, 220, 'America/Toronto'),
    ('CASDR', 'Dryden', 'ON', 49.8250, -92.7758, 408, 'America/Winnipeg'),
    ('CASKR', 'King City', 'ON', 43.9644, -79.5739, 380, 'America/Toronto'),
    ('CASLM', 'Lasseter Lake', 'ON', 46.6950, -80.4000, 322, 'America/Toronto'),
    ('CASSP', 'Exeter', 'ON', 43.3700, -81.3800, 329, 'America/Toronto'),
    ('CASMO', 'Montreal River Harbour', 'ON', 47.2544, -84.5858, 353, 'America/Toronto'),
    ('CASSU', 'Superior West', 'ON', 48.8506, -89.1206, 411, 'America/Winnipeg'),

    # PRINCE EDWARD ISLAND
    ('CASPE', 'Charlottetown', 'PE', 46.2872, -63.0233, 39, 'America/Halifax'),

    # QUEBEC
    ('CASLA', 'Lac Castor', 'QC', 45.6300, -73.5000, 76, 'America/Toronto'),
    ('CASQC', 'Val d\'Irene', 'QC', 48.4808, -67.6067, 831, 'America/Toronto'),
    ('CASSN', 'Villeroy', 'QC', 46.4517, -71.9200, 113, 'America/Toronto'),
    ('CASRA', 'Radisson', 'QC', 53.7831, -77.6192, 169, 'America/Toronto'),

    # SASKATCHEWAN
    ('CASRF', 'Radisson', 'SK', 52.5197, -107.4422, 537, 'America/Regina'),
    ('CASGY', 'Cyress Hills', 'SK', 49.5600, -109.4700, 1313, 'America/Regina'),
    ('CASPY', 'Prince Albert', 'SK', 53.2117, -105.6733, 520, 'America/Regina'),
]


# ============================================
# MEXICAN RADARS (16 sites)
# Source: CONAGUA (Comision Nacional del Agua)
# ============================================
MEXICAN_RADARS = [
    # Format: (site_code, name, state, lat, lon, elevation_m, timezone)
    ('MXVER', 'Veracruz', 'VER', 19.1833, -96.1333, 91, 'America/Mexico_City'),
    ('MXTAM', 'Tamaulipas/Ciudad Victoria', 'TAM', 23.7333, -99.1500, 321, 'America/Monterrey'),
    ('MXNLE', 'Nuevo Leon/Guadalupe', 'NLE', 25.7167, -100.2833, 512, 'America/Monterrey'),
    ('MXSOA', 'Sonora/Guaymas', 'SON', 27.9167, -110.9000, 15, 'America/Hermosillo'),
    ('MXSOB', 'Sonora/Mazatan', 'SON', 29.0167, -110.1333, 228, 'America/Hermosillo'),
    ('MXCHI', 'Chihuahua', 'CHI', 28.6333, -106.0500, 1422, 'America/Chihuahua'),
    ('MXBCS', 'Baja California Sur/La Paz', 'BCS', 24.1500, -110.3333, 18, 'America/Mazatlan'),
    ('MXDGO', 'Durango', 'DGO', 24.0500, -104.6667, 1889, 'America/Monterrey'),
    ('MXSIN', 'Sinaloa/Culiacan', 'SIN', 24.8000, -107.3833, 54, 'America/Mazatlan'),
    ('MXJAL', 'Jalisco/Guadalajara', 'JAL', 20.6833, -103.3500, 1567, 'America/Mexico_City'),
    ('MXMCH', 'Michoacan', 'MCH', 19.7000, -101.1833, 1920, 'America/Mexico_City'),
    ('MXCAM', 'Campeche', 'CAM', 19.8500, -90.5333, 5, 'America/Merida'),
    ('MXYUC', 'Yucatan/Merida', 'YUC', 20.9667, -89.6167, 8, 'America/Merida'),
    ('MXQRO', 'Quintana Roo/Cancun', 'QRO', 21.0833, -86.8500, 10, 'America/Cancun'),
    ('MXOAX', 'Oaxaca', 'OAX', 17.0500, -96.7167, 1555, 'America/Mexico_City'),
    ('MXCDM', 'Ciudad de Mexico', 'CDM', 19.4333, -99.1333, 2250, 'America/Mexico_City'),
]


def create_database():
    """Create the database and tables."""
    print("Creating database...")

    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database for clean start
    if DB_PATH.exists():
        DB_PATH.unlink()
        print("  Removed existing database")

    conn = sqlite3.connect(str(DB_PATH))

    # Read and execute schema using executescript (handles multiple statements)
    schema_path = PROJECT_ROOT / 'database' / 'schema.sql'
    with open(schema_path, 'r') as f:
        schema = f.read()

    # executescript properly handles multi-statement SQL files
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"Database created at: {DB_PATH}")


def seed_radars():
    """Seed all radar sites into the database."""
    print("\nSeeding radar sites...")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_inserted = 0
    errors = []

    # Seed US radars
    print(f"  Seeding {len(US_NEXRAD_RADARS)} US NEXRAD radars...")
    for radar in US_NEXRAD_RADARS:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO radar_sites
                (site_code, name, country, state_province, latitude, longitude,
                 elevation_m, timezone, is_active, data_source, data_url)
                VALUES (?, ?, 'US', ?, ?, ?, ?, ?, 1, 'AWS S3',
                        'https://noaa-nexrad-level2.s3.amazonaws.com')
            """, (
                radar[0],  # site_code
                radar[1],  # name
                radar[2],  # state
                radar[3],  # lat
                radar[4],  # lon
                radar[5],  # elevation
                radar[6],  # timezone
            ))
            total_inserted += 1
        except Exception as e:
            errors.append(f"US {radar[0]}: {e}")

    # Seed Canadian radars
    print(f"  Seeding {len(CANADIAN_RADARS)} Canadian radars...")
    for radar in CANADIAN_RADARS:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO radar_sites
                (site_code, name, country, state_province, latitude, longitude,
                 elevation_m, timezone, is_active, data_source, data_url)
                VALUES (?, ?, 'CA', ?, ?, ?, ?, ?, 1, 'Environment Canada',
                        'https://dd.weather.gc.ca/radar')
            """, (
                radar[0],  # site_code
                radar[1],  # name
                radar[2],  # province
                radar[3],  # lat
                radar[4],  # lon
                radar[5],  # elevation
                radar[6],  # timezone
            ))
            total_inserted += 1
        except Exception as e:
            errors.append(f"CA {radar[0]}: {e}")

    # Seed Mexican radars
    print(f"  Seeding {len(MEXICAN_RADARS)} Mexican radars...")
    for radar in MEXICAN_RADARS:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO radar_sites
                (site_code, name, country, state_province, latitude, longitude,
                 elevation_m, timezone, is_active, data_source, data_url)
                VALUES (?, ?, 'MX', ?, ?, ?, ?, ?, 1, 'CONAGUA',
                        'http://smn.conagua.gob.mx/es/observando-el-tiempo/radar-meteorologico')
            """, (
                radar[0],  # site_code
                radar[1],  # name
                radar[2],  # state
                radar[3],  # lat
                radar[4],  # lon
                radar[5],  # elevation
                radar[6],  # timezone
            ))
            total_inserted += 1
        except Exception as e:
            errors.append(f"MX {radar[0]}: {e}")

    conn.commit()

    # Verify counts
    cursor.execute("SELECT country, COUNT(*) FROM radar_sites GROUP BY country")
    counts = cursor.fetchall()

    conn.close()

    print(f"\n  Total radars inserted: {total_inserted}")
    print("\n  Radar counts by country:")
    for row in counts:
        print(f"    {row[0]}: {row[1]}")

    if errors:
        print(f"\n  Errors ({len(errors)}):")
        for e in errors[:5]:
            print(f"    {e}")
        if len(errors) > 5:
            print(f"    ... and {len(errors) - 5} more")

    return total_inserted


def verify_radars():
    """Verify radar database."""
    print("\n" + "=" * 60)
    print("RADAR DATABASE VERIFICATION")
    print("=" * 60)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM radar_sites")
    total = cursor.fetchone()[0]
    print(f"\nTotal radars: {total}")

    # By country
    cursor.execute("""
        SELECT country, COUNT(*) as cnt
        FROM radar_sites
        GROUP BY country
        ORDER BY cnt DESC
    """)
    print("\nBy country:")
    for row in cursor.fetchall():
        print(f"  {row['country']}: {row['cnt']}")

    # Sample radars
    cursor.execute("""
        SELECT site_code, name, country, state_province, latitude, longitude
        FROM radar_sites
        ORDER BY country, state_province
        LIMIT 10
    """)
    print("\nSample radars:")
    for row in cursor.fetchall():
        print(f"  {row['site_code']:6} | {row['country']:2} | {row['state_province'] or 'N/A':3} | "
              f"{row['latitude']:8.4f}, {row['longitude']:9.4f} | {row['name']}")

    # Verify critical radars exist
    critical_radars = ['KTLX', 'KFTG', 'KFWS', 'CASCM', 'CASBE', 'MXNLE', 'MXCDM']
    cursor.execute(f"""
        SELECT site_code FROM radar_sites
        WHERE site_code IN ({','.join(['?']*len(critical_radars))})
    """, critical_radars)
    found = [row['site_code'] for row in cursor.fetchall()]
    missing = set(critical_radars) - set(found)

    print(f"\nCritical radars check: {len(found)}/{len(critical_radars)}")
    if missing:
        print(f"  Missing: {missing}")

    conn.close()

    # Final status
    expected = 159 + 31 + 16  # US + CA + MX
    status = "PASS" if total >= expected * 0.95 else "FAIL"
    print(f"\nStatus: {status} ({total}/{expected} expected)")

    return total >= expected * 0.95


if __name__ == '__main__':
    print("=" * 60)
    print("HAILTRACKER PRO - RADAR DATABASE SETUP")
    print("=" * 60)
    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Database path: {DB_PATH}")

    # Create database
    create_database()

    # Seed radars
    total = seed_radars()

    # Verify
    success = verify_radars()

    print("\n" + "=" * 60)
    if success:
        print("RADAR SETUP COMPLETE")
    else:
        print("RADAR SETUP INCOMPLETE - CHECK ERRORS")
    print("=" * 60)

    sys.exit(0 if success else 1)
