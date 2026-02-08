"""
Configuration File Handler for HailTracker Pro

Load and save configuration from YAML or JSON files.

Supported formats:
- YAML (.yaml, .yml) - recommended for readability
- JSON (.json)

Usage:
    from src.alerts.config import load_config, save_config, get_default_config

    # Load config from file
    config = load_config('config.yaml')

    # Save config to file
    save_config(config, 'config.yaml')

    # Get default configuration
    defaults = get_default_config()
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import asdict
from pathlib import Path


# Try to import YAML support
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Default config file locations (in order of priority)
DEFAULT_CONFIG_PATHS = [
    'hailtracker.yaml',
    'hailtracker.yml',
    'hailtracker.json',
    'config/hailtracker.yaml',
    'config/hailtracker.yml',
    'config/hailtracker.json',
    '~/.hailtracker/config.yaml',
    '~/.hailtracker/config.json',
]


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration with all available options.

    Returns:
        Dictionary with all configuration options and their defaults.
    """
    return {
        # Radar monitoring settings
        'radars': ['KFWS', 'KDFW', 'KTLX', 'KVNX', 'KICT', 'KDDC'],
        'scan_interval': 300,  # seconds
        'lookback_minutes': 15,

        # Alert thresholds
        'thresholds': {
            'min_reflectivity_dbz': 50.0,
            'min_mesh_mm': 15.0,
            'min_pdr_score': 40.0,
        },

        # Geographic coverage
        'coverage': {
            # Option 1: Named region(s)
            'region': None,  # e.g., 'dallas_fort_worth', 'texas'
            'regions': [],   # e.g., ['dallas_fort_worth', 'oklahoma_city']

            # Option 2: Radius from center point
            'center': None,  # e.g., [32.7767, -96.7970] (lat, lon)
            'radius_miles': None,  # e.g., 50

            # Option 3: Bounding box
            'bounds': None,  # e.g., [32.0, 34.0, -98.0, -96.0] (lat_min, lat_max, lon_min, lon_max)

            # Auto-select radars based on coverage area
            'auto_select_radars': False,
        },

        # Notification settings
        'notifications': {
            'console': True,
            'sound': True,
            'file_log': True,
        },

        # Webhook (Slack/Discord)
        'webhook': {
            'enabled': False,
            'url': None,
            'platform': 'slack',  # 'slack', 'discord', 'custom'
        },

        # SMS (Twilio)
        'sms': {
            'enabled': False,
            'use_env': False,  # Use environment variables
            'account_sid': None,
            'auth_token': None,
            'from_number': None,
            'to_numbers': [],
            'min_level': 'WARNING',
        },

        # Push notifications
        'push': {
            # ntfy.sh (free, no account required)
            'ntfy': {
                'enabled': False,
                'topic': None,
                'server': 'https://ntfy.sh',
            },
            # Pushover
            'pushover': {
                'enabled': False,
                'user_key': None,
                'api_token': None,
            },
            'min_level': 'WARNING',
        },

        # Email
        'email': {
            'enabled': False,
            'use_env': False,  # Use environment variables
            'smtp_server': None,  # e.g., 'smtp.gmail.com'
            'smtp_port': 587,
            'username': None,
            'password': None,  # For Gmail, use App Password
            'from_address': None,
            'to_addresses': [],
            'min_level': 'WARNING',
        },

        # Database storage
        'database': {
            'enabled': True,
            'url': 'sqlite:///data/alerts/alerts.db',
        },

        # Web dashboard
        'dashboard': {
            'enabled': False,
            'host': '127.0.0.1',
            'port': 5000,
        },
    }


def load_config(filepath: str) -> Dict[str, Any]:
    """
    Load configuration from a file.

    Args:
        filepath: Path to config file (YAML or JSON)

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is unsupported
    """
    filepath = os.path.expanduser(filepath)

    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Config file not found: {filepath}")

    ext = Path(filepath).suffix.lower()

    with open(filepath, 'r', encoding='utf-8') as f:
        if ext in ('.yaml', '.yml'):
            if not YAML_AVAILABLE:
                raise ValueError("YAML support not available. Install with: pip install pyyaml")
            config = yaml.safe_load(f)
        elif ext == '.json':
            config = json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {ext}. Use .yaml, .yml, or .json")

    return config or {}


def save_config(config: Dict[str, Any], filepath: str, include_comments: bool = True):
    """
    Save configuration to a file.

    Args:
        config: Configuration dictionary
        filepath: Path to save config file
        include_comments: Include helpful comments (YAML only)
    """
    filepath = os.path.expanduser(filepath)

    # Create directory if needed
    os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)

    ext = Path(filepath).suffix.lower()

    with open(filepath, 'w', encoding='utf-8') as f:
        if ext in ('.yaml', '.yml'):
            if not YAML_AVAILABLE:
                raise ValueError("YAML support not available. Install with: pip install pyyaml")
            if include_comments:
                f.write(generate_yaml_with_comments(config))
            else:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        elif ext == '.json':
            json.dump(config, f, indent=2)
        else:
            raise ValueError(f"Unsupported config format: {ext}")

    print(f"Configuration saved to: {filepath}")


def find_config_file() -> Optional[str]:
    """
    Find config file in default locations.

    Returns:
        Path to config file if found, None otherwise
    """
    for path in DEFAULT_CONFIG_PATHS:
        expanded = os.path.expanduser(path)
        if os.path.exists(expanded):
            return expanded
    return None


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two configuration dictionaries.

    Args:
        base: Base configuration
        override: Override values (takes precedence)

    Returns:
        Merged configuration
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value

    return result


def config_to_monitor_args(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert config dictionary to MonitorConfig arguments.

    Args:
        config: Configuration dictionary

    Returns:
        Dictionary of arguments for MonitorConfig
    """
    args = {}

    # Radars
    if config.get('radars'):
        args['radar_ids'] = config['radars']

    # Timing
    if config.get('scan_interval'):
        args['scan_interval_seconds'] = config['scan_interval']
    if config.get('lookback_minutes'):
        args['lookback_minutes'] = config['lookback_minutes']

    # Thresholds
    thresholds = config.get('thresholds', {})
    if thresholds.get('min_reflectivity_dbz'):
        args['min_reflectivity_dbz'] = thresholds['min_reflectivity_dbz']
    if thresholds.get('min_mesh_mm'):
        args['min_mesh_mm'] = thresholds['min_mesh_mm']
    if thresholds.get('min_pdr_score'):
        args['min_pdr_score'] = thresholds['min_pdr_score']

    # Coverage
    coverage = config.get('coverage', {})
    if coverage.get('region'):
        args['coverage_region'] = coverage['region']
    if coverage.get('regions'):
        args['coverage_regions'] = coverage['regions']
    if coverage.get('center'):
        args['coverage_center_lat'] = coverage['center'][0]
        args['coverage_center_lon'] = coverage['center'][1]
    if coverage.get('radius_miles'):
        args['coverage_radius_miles'] = coverage['radius_miles']
    if coverage.get('bounds'):
        bounds = coverage['bounds']
        args['lat_min'] = bounds[0]
        args['lat_max'] = bounds[1]
        args['lon_min'] = bounds[2]
        args['lon_max'] = bounds[3]
    if coverage.get('auto_select_radars'):
        args['auto_select_radars'] = coverage['auto_select_radars']

    # Notifications
    notifications = config.get('notifications', {})
    args['enable_console'] = notifications.get('console', True)
    args['enable_sound'] = notifications.get('sound', True)
    args['enable_file_log'] = notifications.get('file_log', True)

    # Webhook
    webhook = config.get('webhook', {})
    if webhook.get('enabled') and webhook.get('url'):
        args['webhook_url'] = webhook['url']
        args['webhook_platform'] = webhook.get('platform', 'slack')

    # SMS
    sms = config.get('sms', {})
    if sms.get('enabled'):
        args['sms_enabled'] = True
        args['sms_use_env'] = sms.get('use_env', False)
        if not sms.get('use_env'):
            args['sms_account_sid'] = sms.get('account_sid')
            args['sms_auth_token'] = sms.get('auth_token')
            args['sms_from_number'] = sms.get('from_number')
            args['sms_to_numbers'] = sms.get('to_numbers', [])
        args['sms_min_level'] = sms.get('min_level', 'WARNING')

    # Push
    push = config.get('push', {})
    ntfy = push.get('ntfy', {})
    if ntfy.get('enabled') and ntfy.get('topic'):
        args['ntfy_topic'] = ntfy['topic']
        args['ntfy_server'] = ntfy.get('server', 'https://ntfy.sh')

    pushover = push.get('pushover', {})
    if pushover.get('enabled'):
        args['pushover_user'] = pushover.get('user_key')
        args['pushover_token'] = pushover.get('api_token')

    args['push_min_level'] = push.get('min_level', 'WARNING')

    # Email
    email = config.get('email', {})
    if email.get('enabled'):
        args['email_enabled'] = True
        args['email_use_env'] = email.get('use_env', False)
        if not email.get('use_env'):
            args['email_smtp_server'] = email.get('smtp_server')
            args['email_smtp_port'] = email.get('smtp_port', 587)
            args['email_username'] = email.get('username')
            args['email_password'] = email.get('password')
            args['email_from'] = email.get('from_address')
            args['email_to'] = email.get('to_addresses', [])
        args['email_min_level'] = email.get('min_level', 'WARNING')

    # Database
    database = config.get('database', {})
    args['database_enabled'] = database.get('enabled', True)
    args['database_url'] = database.get('url', 'sqlite:///data/alerts/alerts.db')

    return args


def generate_yaml_with_comments(config: Dict[str, Any]) -> str:
    """
    Generate YAML with helpful comments.

    Args:
        config: Configuration dictionary

    Returns:
        YAML string with comments
    """
    lines = [
        "# HailTracker Pro Configuration",
        "# ==============================",
        "#",
        "# This file contains all settings for the HailTracker Pro alert system.",
        "# Edit this file to customize your monitoring and notification preferences.",
        "#",
        "# For documentation, run: python run_realtime_alerts.py --help",
        "",
        "# ============================================================================",
        "# RADAR MONITORING",
        "# ============================================================================",
        "",
        "# NEXRAD radar stations to monitor",
        "# Common stations: KFWS (Dallas), KTLX (OKC), KICT (Wichita), KAMA (Amarillo)",
        f"radars: {json.dumps(config.get('radars', []))}",
        "",
        "# Scan interval in seconds (default: 300 = 5 minutes)",
        f"scan_interval: {config.get('scan_interval', 300)}",
        "",
        "# How far back to look for radar scans (minutes)",
        f"lookback_minutes: {config.get('lookback_minutes', 15)}",
        "",
        "# ============================================================================",
        "# ALERT THRESHOLDS",
        "# ============================================================================",
        "",
        "thresholds:",
        "  # Minimum reflectivity to analyze (dBZ)",
        f"  min_reflectivity_dbz: {config.get('thresholds', {}).get('min_reflectivity_dbz', 50.0)}",
        "",
        "  # Minimum MESH to trigger alert (mm)",
        f"  min_mesh_mm: {config.get('thresholds', {}).get('min_mesh_mm', 15.0)}",
        "",
        "  # Minimum PDR score to trigger alert (0-100)",
        f"  min_pdr_score: {config.get('thresholds', {}).get('min_pdr_score', 40.0)}",
        "",
        "# ============================================================================",
        "# GEOGRAPHIC COVERAGE",
        "# ============================================================================",
        "#",
        "# Define your coverage area using ONE of these methods:",
        "#   1. Named region (e.g., 'dallas_fort_worth', 'texas', 'hail_alley_core')",
        "#   2. Radius from center point (great for single shop location)",
        "#   3. Bounding box coordinates",
        "#",
        "# Run 'python run_realtime_alerts.py --list-regions' for available regions",
        "",
        "coverage:",
        "  # Option 1: Named region",
        f"  region: {json.dumps(config.get('coverage', {}).get('region'))}",
        "",
        "  # Multiple regions (alerts for any of these areas)",
        f"  regions: {json.dumps(config.get('coverage', {}).get('regions', []))}",
        "",
        "  # Option 2: Radius from center point",
        "  # center: [32.7767, -96.7970]  # [latitude, longitude]",
        "  # radius_miles: 50",
        f"  center: {json.dumps(config.get('coverage', {}).get('center'))}",
        f"  radius_miles: {json.dumps(config.get('coverage', {}).get('radius_miles'))}",
        "",
        "  # Option 3: Bounding box [lat_min, lat_max, lon_min, lon_max]",
        "  # bounds: [32.0, 34.0, -98.0, -96.0]",
        f"  bounds: {json.dumps(config.get('coverage', {}).get('bounds'))}",
        "",
        "  # Automatically select radars for your coverage area",
        f"  auto_select_radars: {str(config.get('coverage', {}).get('auto_select_radars', False)).lower()}",
        "",
        "# ============================================================================",
        "# BASIC NOTIFICATIONS",
        "# ============================================================================",
        "",
        "notifications:",
        f"  console: {str(config.get('notifications', {}).get('console', True)).lower()}",
        f"  sound: {str(config.get('notifications', {}).get('sound', True)).lower()}",
        f"  file_log: {str(config.get('notifications', {}).get('file_log', True)).lower()}",
        "",
        "# ============================================================================",
        "# WEBHOOK (Slack/Discord)",
        "# ============================================================================",
        "",
        "webhook:",
        f"  enabled: {str(config.get('webhook', {}).get('enabled', False)).lower()}",
        f"  url: {json.dumps(config.get('webhook', {}).get('url'))}",
        f"  platform: {config.get('webhook', {}).get('platform', 'slack')}  # slack, discord, custom",
        "",
        "# ============================================================================",
        "# SMS ALERTS (Twilio)",
        "# ============================================================================",
        "#",
        "# Get credentials at https://console.twilio.com/",
        "# Set use_env: true to use environment variables instead:",
        "#   TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_TO_NUMBERS",
        "",
        "sms:",
        f"  enabled: {str(config.get('sms', {}).get('enabled', False)).lower()}",
        f"  use_env: {str(config.get('sms', {}).get('use_env', False)).lower()}",
        f"  account_sid: {json.dumps(config.get('sms', {}).get('account_sid'))}",
        f"  auth_token: {json.dumps(config.get('sms', {}).get('auth_token'))}",
        f"  from_number: {json.dumps(config.get('sms', {}).get('from_number'))}",
        f"  to_numbers: {json.dumps(config.get('sms', {}).get('to_numbers', []))}",
        f"  min_level: {config.get('sms', {}).get('min_level', 'WARNING')}  # INFO, WATCH, WARNING, CRITICAL",
        "",
        "# ============================================================================",
        "# PUSH NOTIFICATIONS",
        "# ============================================================================",
        "",
        "push:",
        "  # ntfy.sh - Free, no account required!",
        "  # 1. Install ntfy app on your phone",
        "  # 2. Subscribe to your topic (e.g., 'my-hailtracker-alerts')",
        "  # 3. Set the topic name below",
        "  ntfy:",
        f"    enabled: {str(config.get('push', {}).get('ntfy', {}).get('enabled', False)).lower()}",
        f"    topic: {json.dumps(config.get('push', {}).get('ntfy', {}).get('topic'))}",
        f"    server: {config.get('push', {}).get('ntfy', {}).get('server', 'https://ntfy.sh')}",
        "",
        "  # Pushover - https://pushover.net/",
        "  pushover:",
        f"    enabled: {str(config.get('push', {}).get('pushover', {}).get('enabled', False)).lower()}",
        f"    user_key: {json.dumps(config.get('push', {}).get('pushover', {}).get('user_key'))}",
        f"    api_token: {json.dumps(config.get('push', {}).get('pushover', {}).get('api_token'))}",
        "",
        f"  min_level: {config.get('push', {}).get('min_level', 'WARNING')}",
        "",
        "# ============================================================================",
        "# EMAIL ALERTS",
        "# ============================================================================",
        "#",
        "# For Gmail: Use smtp.gmail.com:587 with an App Password",
        "#   1. Enable 2-Factor Authentication on your Google account",
        "#   2. Generate App Password: https://myaccount.google.com/apppasswords",
        "#   3. Use the App Password here (NOT your regular password)",
        "#",
        "# Set use_env: true to use environment variables instead:",
        "#   EMAIL_SMTP_SERVER, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO",
        "",
        "email:",
        f"  enabled: {str(config.get('email', {}).get('enabled', False)).lower()}",
        f"  use_env: {str(config.get('email', {}).get('use_env', False)).lower()}",
        f"  smtp_server: {json.dumps(config.get('email', {}).get('smtp_server'))}  # e.g., smtp.gmail.com",
        f"  smtp_port: {config.get('email', {}).get('smtp_port', 587)}  # 587 for TLS, 465 for SSL",
        f"  username: {json.dumps(config.get('email', {}).get('username'))}",
        f"  password: {json.dumps(config.get('email', {}).get('password'))}  # Use App Password for Gmail",
        f"  from_address: {json.dumps(config.get('email', {}).get('from_address'))}  # Defaults to username",
        f"  to_addresses: {json.dumps(config.get('email', {}).get('to_addresses', []))}",
        f"  min_level: {config.get('email', {}).get('min_level', 'WARNING')}",
        "",
        "# ============================================================================",
        "# DATABASE STORAGE",
        "# ============================================================================",
        "#",
        "# Store alert history in a database for analysis and reporting.",
        "# Default: SQLite (no setup required)",
        "# PostgreSQL: postgresql://user:password@localhost/hailtracker",
        "",
        "database:",
        f"  enabled: {str(config.get('database', {}).get('enabled', True)).lower()}",
        f"  url: {config.get('database', {}).get('url', 'sqlite:///data/alerts/alerts.db')}",
        "",
        "# ============================================================================",
        "# WEB DASHBOARD",
        "# ============================================================================",
        "",
        "dashboard:",
        f"  enabled: {str(config.get('dashboard', {}).get('enabled', False)).lower()}",
        f"  host: {config.get('dashboard', {}).get('host', '127.0.0.1')}",
        f"  port: {config.get('dashboard', {}).get('port', 5000)}",
    ]

    return "\n".join(lines)


def create_sample_config(filepath: str = 'hailtracker.yaml'):
    """
    Create a sample configuration file with all options.

    Args:
        filepath: Path to create config file
    """
    config = get_default_config()
    save_config(config, filepath, include_comments=True)
    print(f"\nSample configuration created: {filepath}")
    print("Edit this file to customize your settings.")
