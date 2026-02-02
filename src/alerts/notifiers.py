"""
Alert Notifiers - Various notification delivery methods

Supports:
- Console output (with colors)
- Webhook (Slack, Discord, custom)
- Email (SMTP)
- Sound alerts
- Desktop notifications
"""

import json
import os
import smtplib
import urllib.request
import urllib.error
import urllib.parse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dataclasses import dataclass

from .alert_manager import Alert, AlertLevel


class ConsoleNotifier:
    """
    Print alerts to console with color coding.
    """

    # ANSI color codes
    COLORS = {
        AlertLevel.CRITICAL: '\033[91m',  # Red
        AlertLevel.WARNING: '\033[93m',   # Yellow
        AlertLevel.WATCH: '\033[94m',     # Blue
        AlertLevel.INFO: '\033[92m',      # Green
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def __init__(self, use_colors: bool = True, verbose: bool = True):
        """
        Initialize console notifier.

        Args:
            use_colors: Use ANSI color codes
            verbose: Show full alert details
        """
        self.use_colors = use_colors
        self.verbose = verbose

    def __call__(self, alert: Alert):
        """Send alert to console."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Print alert to console."""
        color = self.COLORS.get(alert.level, '') if self.use_colors else ''
        reset = self.RESET if self.use_colors else ''
        bold = self.BOLD if self.use_colors else ''

        # Header
        print(f"\n{'='*70}")
        print(f"{color}{bold}*** {alert.level.name} ALERT - {alert.event_name} ***{reset}")
        print(f"{'='*70}")

        print(f"ID: {alert.id}")
        print(f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Location: ({alert.location[0]:.4f}, {alert.location[1]:.4f})")
        print(f"Radar: {alert.radar_id}")

        print(f"\n{color}HAIL ANALYSIS:{reset}")
        hail_status = f"{color}{bold}YES{reset}" if alert.hail_detected else "NO"
        print(f"  Detected: {hail_status}")
        print(f"  Probability: {alert.hail_probability:.0f}%")
        print(f"  Size: {alert.hail_size_mm:.0f} mm ({alert.hail_size_mm/25.4:.2f}\")")
        print(f"  Severity: {color}{alert.severity.upper()}{reset}")

        print(f"\n{color}PDR SCORE: {bold}{alert.pdr_score:.0f}/100{reset}")

        if self.verbose:
            print(f"\nRADAR DATA:")
            print(f"  Max Reflectivity: {alert.max_reflectivity:.0f} dBZ")
            print(f"  MESH: {alert.mesh_mm:.0f} mm")
            print(f"  POSH: {alert.posh:.0f}%")

            if alert.message:
                print(f"\n{color}MESSAGE:{reset}")
                print(f"  {alert.message}")

            if alert.recommendations:
                print(f"\n{color}RECOMMENDATIONS:{reset}")
                for rec in alert.recommendations:
                    print(f"  - {rec}")

        print(f"{'='*70}\n")


class WebhookNotifier:
    """
    Send alerts via webhook (Slack, Discord, custom endpoints).
    """

    def __init__(
        self,
        webhook_url: str,
        platform: str = 'slack',
        mention_on_critical: Optional[str] = None
    ):
        """
        Initialize webhook notifier.

        Args:
            webhook_url: Webhook URL
            platform: 'slack', 'discord', or 'custom'
            mention_on_critical: User/role to mention for critical alerts
        """
        self.webhook_url = webhook_url
        self.platform = platform.lower()
        self.mention_on_critical = mention_on_critical

    def __call__(self, alert: Alert):
        """Send alert via webhook."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send alert to webhook."""
        if self.platform == 'slack':
            payload = self._format_slack(alert)
        elif self.platform == 'discord':
            payload = self._format_discord(alert)
        else:
            payload = alert.to_dict()

        try:
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    print(f"Webhook returned status {response.status}")
        except urllib.error.URLError as e:
            print(f"Webhook error: {e}")
        except Exception as e:
            print(f"Webhook error: {e}")

    def _format_slack(self, alert: Alert) -> Dict:
        """Format alert for Slack."""
        color_map = {
            AlertLevel.CRITICAL: '#FF0000',
            AlertLevel.WARNING: '#FFA500',
            AlertLevel.WATCH: '#0000FF',
            AlertLevel.INFO: '#00FF00'
        }

        emoji_map = {
            AlertLevel.CRITICAL: ':rotating_light:',
            AlertLevel.WARNING: ':warning:',
            AlertLevel.WATCH: ':eyes:',
            AlertLevel.INFO: ':information_source:'
        }

        mention = ""
        if alert.level == AlertLevel.CRITICAL and self.mention_on_critical:
            mention = f"<{self.mention_on_critical}> "

        return {
            'text': f"{mention}{emoji_map.get(alert.level, '')} {alert.level.name}: {alert.event_name}",
            'attachments': [{
                'color': color_map.get(alert.level, '#808080'),
                'title': f"{alert.level.name} - {alert.event_name}",
                'fields': [
                    {'title': 'Location', 'value': f"({alert.location[0]:.4f}, {alert.location[1]:.4f})", 'short': True},
                    {'title': 'Radar', 'value': alert.radar_id, 'short': True},
                    {'title': 'Hail Size', 'value': f"{alert.hail_size_mm:.0f}mm ({alert.hail_size_mm/25.4:.2f}\")", 'short': True},
                    {'title': 'PDR Score', 'value': f"{alert.pdr_score:.0f}/100", 'short': True},
                    {'title': 'Probability', 'value': f"{alert.hail_probability:.0f}%", 'short': True},
                    {'title': 'Severity', 'value': alert.severity.upper(), 'short': True},
                ],
                'text': alert.message,
                'footer': f"HailTracker Pro | {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }]
        }

    def _format_discord(self, alert: Alert) -> Dict:
        """Format alert for Discord."""
        color_map = {
            AlertLevel.CRITICAL: 16711680,  # Red
            AlertLevel.WARNING: 16753920,   # Orange
            AlertLevel.WATCH: 255,          # Blue
            AlertLevel.INFO: 65280          # Green
        }

        return {
            'content': f"*** **{alert.level.name}** - {alert.event_name}",
            'embeds': [{
                'title': alert.event_name,
                'description': alert.message,
                'color': color_map.get(alert.level, 8421504),
                'fields': [
                    {'name': 'Location', 'value': f"({alert.location[0]:.4f}, {alert.location[1]:.4f})", 'inline': True},
                    {'name': 'Radar', 'value': alert.radar_id, 'inline': True},
                    {'name': 'Hail Size', 'value': f"{alert.hail_size_mm:.0f}mm", 'inline': True},
                    {'name': 'PDR Score', 'value': f"{alert.pdr_score:.0f}/100", 'inline': True},
                    {'name': 'Probability', 'value': f"{alert.hail_probability:.0f}%", 'inline': True},
                    {'name': 'Severity', 'value': alert.severity.upper(), 'inline': True},
                ],
                'footer': {'text': f"HailTracker Pro | ID: {alert.id}"},
                'timestamp': alert.timestamp.isoformat()
            }]
        }


class EmailNotifier:
    """
    Send alerts via email (SMTP).

    Supports Gmail, Outlook, custom SMTP servers, and more.

    Common SMTP settings:
        Gmail: smtp.gmail.com:587 (TLS) - requires App Password
        Outlook: smtp.office365.com:587 (TLS)
        Yahoo: smtp.mail.yahoo.com:587 (TLS)
        SendGrid: smtp.sendgrid.net:587 (TLS)
        Custom: your-smtp.server.com:587

    For Gmail, you need to:
        1. Enable 2-Factor Authentication
        2. Generate an App Password at https://myaccount.google.com/apppasswords
        3. Use the App Password (not your regular password)
    """

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_address: str,
        to_addresses: List[str],
        use_tls: bool = True,
        min_level: AlertLevel = AlertLevel.WARNING,
        max_emails_per_hour: int = 20,
        include_map_link: bool = True
    ):
        """
        Initialize email notifier.

        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP port (587 for TLS, 465 for SSL)
            username: SMTP username
            password: SMTP password (or App Password for Gmail)
            from_address: From email address
            to_addresses: List of recipient addresses
            use_tls: Use TLS encryption (True for port 587, False for SSL/465)
            min_level: Minimum alert level to send email (default: WARNING)
            max_emails_per_hour: Rate limit (default: 20)
            include_map_link: Include Google Maps link in email
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.use_tls = use_tls
        self.min_level = min_level
        self.max_emails_per_hour = max_emails_per_hour
        self.include_map_link = include_map_link

        # Rate limiting
        self._email_times: List[datetime] = []

        # Validate configuration
        self.enabled = self._validate_config()

    def _validate_config(self) -> bool:
        """Validate email configuration."""
        if not self.smtp_server or not self.username or not self.password:
            print("Email notifier disabled: missing SMTP credentials")
            return False
        if not self.to_addresses:
            print("Email notifier disabled: no recipients configured")
            return False
        print(f"Email notifier initialized: {len(self.to_addresses)} recipient(s)")
        return True

    def __call__(self, alert: Alert):
        """Send alert via email."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send email alert."""
        if not self.enabled:
            return

        # Check minimum level
        if alert.level.value < self.min_level.value:
            return

        # Check rate limit
        if not self._check_rate_limit():
            print(f"Email rate limit reached ({self.max_emails_per_hour}/hour)")
            return

        msg = MIMEMultipart('alternative')
        msg['Subject'] = self._format_subject(alert)
        msg['From'] = self.from_address
        msg['To'] = ', '.join(self.to_addresses)

        # Plain text version
        text_content = self._format_text(alert)

        # HTML version
        html_content = self._format_html(alert)

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.username, self.password)
            server.sendmail(self.from_address, self.to_addresses, msg.as_string())
            server.quit()

            # Track for rate limiting
            self._email_times.append(datetime.now())

            print(f"Email alert sent to {len(self.to_addresses)} recipient(s)")
        except smtplib.SMTPAuthenticationError as e:
            print(f"Email auth error: {e}. For Gmail, use an App Password.")
        except Exception as e:
            print(f"Email error: {e}")

    def _check_rate_limit(self) -> bool:
        """Check if we can send another email."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self._email_times = [t for t in self._email_times if t > one_hour_ago]

        # Check limit
        return len(self._email_times) < self.max_emails_per_hour

    def _format_subject(self, alert: Alert) -> str:
        """Format email subject line."""
        level_prefix = {
            AlertLevel.CRITICAL: "[!!!CRITICAL!!!]",
            AlertLevel.WARNING: "[WARNING]",
            AlertLevel.WATCH: "[WATCH]",
            AlertLevel.INFO: "[INFO]"
        }
        prefix = level_prefix.get(alert.level, "[ALERT]")
        return f"{prefix} HailTracker: {alert.event_name} - {alert.hail_size_mm:.0f}mm hail"

    def _format_text(self, alert: Alert) -> str:
        """Format plain text email body."""
        lines = [
            f"{'='*60}",
            f"HAILTRACKER PRO - {alert.level.name} ALERT",
            f"{'='*60}",
            "",
            f"Event: {alert.event_name}",
            f"Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Location: ({alert.location[0]:.4f}, {alert.location[1]:.4f})",
            f"Radar: {alert.radar_id}",
            "",
            "HAIL ANALYSIS:",
            f"  Detected: {'YES' if alert.hail_detected else 'NO'}",
            f"  Probability: {alert.hail_probability:.0f}%",
            f"  Size: {alert.hail_size_mm:.0f} mm ({alert.hail_size_mm/25.4:.2f}\")",
            f"  Severity: {alert.severity.upper()}",
            "",
            f"PDR SCORE: {alert.pdr_score:.0f}/100",
            "",
            "RADAR DATA:",
            f"  Max Reflectivity: {alert.max_reflectivity:.0f} dBZ",
            f"  MESH: {alert.mesh_mm:.0f} mm",
            f"  POSH: {alert.posh:.0f}%",
            "",
        ]

        if self.include_map_link:
            lat, lon = alert.location
            lines.append(f"View on Map: https://maps.google.com/?q={lat:.4f},{lon:.4f}")
            lines.append("")

        if alert.message:
            lines.extend(["Message:", alert.message, ""])

        if alert.recommendations:
            lines.append("Recommendations:")
            for rec in alert.recommendations:
                lines.append(f"  - {rec}")

        lines.extend(["", f"{'='*60}", "HailTracker Pro - Real-Time Storm Monitoring"])

        return "\n".join(lines)

    def _format_html(self, alert: Alert) -> str:
        """Format alert as HTML email."""
        color_map = {
            AlertLevel.CRITICAL: '#FF0000',
            AlertLevel.WARNING: '#FFA500',
            AlertLevel.WATCH: '#0066CC',
            AlertLevel.INFO: '#00AA00'
        }
        color = color_map.get(alert.level, '#808080')

        recommendations_html = ""
        if alert.recommendations:
            recommendations_html = "<ul>" + "".join(f"<li>{r}</li>" for r in alert.recommendations) + "</ul>"

        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: {color}; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0;">*** {alert.level.name} ALERT</h1>
                <h2 style="margin: 10px 0 0 0;">{alert.event_name}</h2>
            </div>

            <div style="padding: 20px; background-color: #f5f5f5;">
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Location:</strong> ({alert.location[0]:.4f}, {alert.location[1]:.4f})</p>
                <p><strong>Radar:</strong> {alert.radar_id}</p>
            </div>

            <div style="padding: 20px;">
                <h3 style="color: {color};">Hail Analysis</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Detected:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{'YES' if alert.hail_detected else 'NO'}</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Probability:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert.hail_probability:.0f}%</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Size:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert.hail_size_mm:.0f} mm ({alert.hail_size_mm/25.4:.2f}")</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Severity:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; color: {color}; font-weight: bold;">{alert.severity.upper()}</td></tr>
                </table>

                <div style="background-color: {color}; color: white; padding: 15px; margin: 20px 0; text-align: center; border-radius: 5px;">
                    <h2 style="margin: 0;">PDR SCORE: {alert.pdr_score:.0f}/100</h2>
                </div>

                <h3>Message</h3>
                <p style="background-color: #f0f0f0; padding: 15px; border-left: 4px solid {color};">{alert.message}</p>

                <h3>Recommendations</h3>
                {recommendations_html}

                <h3>Radar Data</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>Max Reflectivity:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert.max_reflectivity:.0f} dBZ</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>MESH:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert.mesh_mm:.0f} mm</td></tr>
                    <tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>POSH:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{alert.posh:.0f}%</td></tr>
                </table>
            </div>

            <div style="background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px;">
                <p>HailTracker Pro - Real-Time Storm Monitoring</p>
                <p>Alert ID: {alert.id}</p>
            </div>
        </body>
        </html>
        """

    def get_status(self) -> Dict:
        """Get notifier status."""
        return {
            'enabled': self.enabled,
            'smtp_server': self.smtp_server,
            'recipients': len(self.to_addresses),
            'min_level': self.min_level.name,
            'emails_sent_this_hour': len(self._email_times)
        }


class EmailNotifierFromEnv(EmailNotifier):
    """
    Email notifier that reads configuration from environment variables.

    Environment variables:
        EMAIL_SMTP_SERVER: SMTP server (e.g., smtp.gmail.com)
        EMAIL_SMTP_PORT: SMTP port (default: 587)
        EMAIL_USERNAME: SMTP username (usually your email)
        EMAIL_PASSWORD: SMTP password (or App Password for Gmail)
        EMAIL_FROM: From address (defaults to EMAIL_USERNAME)
        EMAIL_TO: Comma-separated recipient addresses

    Optional:
        EMAIL_USE_TLS: Use TLS (default: true)
        EMAIL_MIN_LEVEL: Minimum alert level (default: WARNING)

    Example setup for Gmail:
        export EMAIL_SMTP_SERVER=smtp.gmail.com
        export EMAIL_SMTP_PORT=587
        export EMAIL_USERNAME=yourname@gmail.com
        export EMAIL_PASSWORD=your-app-password  # NOT your regular password
        export EMAIL_TO=alerts@company.com,manager@company.com
    """

    def __init__(
        self,
        min_level: AlertLevel = AlertLevel.WARNING,
        max_emails_per_hour: int = 20
    ):
        """Initialize from environment variables."""
        smtp_server = os.environ.get('EMAIL_SMTP_SERVER', '')
        smtp_port = int(os.environ.get('EMAIL_SMTP_PORT', '587'))
        username = os.environ.get('EMAIL_USERNAME', '')
        password = os.environ.get('EMAIL_PASSWORD', '')
        from_address = os.environ.get('EMAIL_FROM', username)
        to_addresses_str = os.environ.get('EMAIL_TO', '')
        use_tls = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('true', '1', 'yes')

        # Parse min_level from env if set
        env_min_level = os.environ.get('EMAIL_MIN_LEVEL', '').upper()
        if env_min_level in ('INFO', 'WATCH', 'WARNING', 'CRITICAL'):
            min_level = AlertLevel[env_min_level]

        if not all([smtp_server, username, password, to_addresses_str]):
            print("WARNING: Email environment variables not fully configured")
            print("Required: EMAIL_SMTP_SERVER, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_TO")
            to_addresses = []
        else:
            to_addresses = [addr.strip() for addr in to_addresses_str.split(',') if addr.strip()]

        super().__init__(
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            username=username,
            password=password,
            from_address=from_address,
            to_addresses=to_addresses,
            use_tls=use_tls,
            min_level=min_level,
            max_emails_per_hour=max_emails_per_hour
        )


class SoundNotifier:
    """
    Play sound alerts for different severity levels.
    """

    def __init__(self, sounds_dir: Optional[str] = None):
        """
        Initialize sound notifier.

        Args:
            sounds_dir: Directory containing sound files
        """
        self.sounds_dir = sounds_dir or "data/sounds"
        self.enabled = self._check_audio_support()

    def _check_audio_support(self) -> bool:
        """Check if audio playback is available."""
        try:
            # Try Windows
            import winsound
            return True
        except ImportError:
            pass

        try:
            # Try cross-platform
            import playsound
            return True
        except ImportError:
            pass

        print("Sound alerts disabled (no audio library available)")
        return False

    def __call__(self, alert: Alert):
        """Play alert sound."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Play sound based on alert level."""
        if not self.enabled:
            return

        try:
            # Try Windows beep
            import winsound

            if alert.level == AlertLevel.CRITICAL:
                # Urgent - multiple high beeps
                for _ in range(3):
                    winsound.Beep(1000, 300)
                    winsound.Beep(1500, 300)
            elif alert.level == AlertLevel.WARNING:
                # Warning - two medium beeps
                winsound.Beep(800, 500)
                winsound.Beep(800, 500)
            elif alert.level == AlertLevel.WATCH:
                # Watch - single beep
                winsound.Beep(600, 400)
            else:
                # Info - soft beep
                winsound.Beep(400, 200)

        except ImportError:
            # Fallback - print bell character
            print('\a')  # Terminal bell
        except Exception as e:
            print(f"Sound error: {e}")


class FileNotifier:
    """
    Write alerts to a log file.
    """

    def __init__(self, log_path: str = "data/alerts/alerts.log"):
        """
        Initialize file notifier.

        Args:
            log_path: Path to log file
        """
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

    def __call__(self, alert: Alert):
        """Write alert to file."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Append alert to log file."""
        try:
            with open(self.log_path, 'a') as f:
                f.write(f"\n{'='*70}\n")
                f.write(alert.format_text())
                f.write(f"\n{'='*70}\n")
        except Exception as e:
            print(f"File logging error: {e}")


class TwilioNotifier:
    """
    Send SMS alerts via Twilio.

    Requires twilio package: pip install twilio

    Get credentials from https://console.twilio.com/
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_numbers: List[str],
        min_level: AlertLevel = AlertLevel.WARNING,
        include_map_link: bool = True,
        max_messages_per_hour: int = 10
    ):
        """
        Initialize Twilio SMS notifier.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number to send from (e.g., '+15551234567')
            to_numbers: List of phone numbers to send to (e.g., ['+15559876543'])
            min_level: Minimum alert level to send SMS (default: WARNING)
            include_map_link: Include Google Maps link in message
            max_messages_per_hour: Rate limit per recipient (default: 10)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_numbers = to_numbers
        self.min_level = min_level
        self.include_map_link = include_map_link
        self.max_messages_per_hour = max_messages_per_hour

        # Rate limiting
        self._message_times: Dict[str, List[datetime]] = {num: [] for num in to_numbers}

        # Check if twilio is available
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initialize Twilio client."""
        try:
            from twilio.rest import Client
            self.client = Client(self.account_sid, self.auth_token)
            print(f"Twilio SMS notifier initialized for {len(self.to_numbers)} recipient(s)")
        except ImportError:
            print("WARNING: twilio package not installed. Install with: pip install twilio")
            self.client = None
        except Exception as e:
            print(f"Twilio initialization error: {e}")
            self.client = None

    def __call__(self, alert: Alert):
        """Send SMS alert."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send SMS to all configured numbers."""
        if not self.client:
            return

        # Check minimum level
        if alert.level.value < self.min_level.value:
            return

        # Format message
        message = self._format_message(alert)

        # Send to each number
        for to_number in self.to_numbers:
            if self._check_rate_limit(to_number):
                self._send_sms(to_number, message)
            else:
                print(f"SMS rate limit reached for {to_number[-4:]}")

    def _check_rate_limit(self, to_number: str) -> bool:
        """Check if we can send to this number (rate limiting)."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self._message_times[to_number] = [
            t for t in self._message_times[to_number]
            if t > one_hour_ago
        ]

        # Check limit
        if len(self._message_times[to_number]) >= self.max_messages_per_hour:
            return False

        return True

    def _format_message(self, alert: Alert) -> str:
        """Format alert as SMS message."""
        # Level indicator
        level_indicator = {
            AlertLevel.CRITICAL: "!!! CRITICAL",
            AlertLevel.WARNING: "!! WARNING",
            AlertLevel.WATCH: "! WATCH",
            AlertLevel.INFO: "INFO"
        }

        # Build message (SMS has ~160 char limit per segment)
        lines = [
            f"HAILTRACKER {level_indicator.get(alert.level, 'ALERT')}",
            f"{alert.event_name}",
            f"Hail: {alert.hail_size_mm:.0f}mm ({alert.hail_size_mm/25.4:.1f}\")",
            f"PDR Score: {alert.pdr_score:.0f}/100",
            f"Prob: {alert.hail_probability:.0f}%",
            f"Radar: {alert.radar_id}",
        ]

        # Add map link if enabled
        if self.include_map_link:
            lat, lon = alert.location
            map_link = f"https://maps.google.com/?q={lat:.4f},{lon:.4f}"
            lines.append(f"Map: {map_link}")

        return "\n".join(lines)

    def _send_sms(self, to_number: str, message: str):
        """Send SMS via Twilio."""
        try:
            result = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number
            )

            # Track for rate limiting
            self._message_times[to_number].append(datetime.now())

            print(f"SMS sent to ...{to_number[-4:]} (SID: {result.sid[:8]}...)")

        except Exception as e:
            print(f"SMS error to {to_number[-4:]}: {e}")

    def get_status(self) -> Dict:
        """Get notifier status."""
        return {
            'enabled': self.client is not None,
            'from_number': self.from_number[-4:] if self.from_number else None,
            'recipients': len(self.to_numbers),
            'min_level': self.min_level.name,
            'messages_sent': sum(len(times) for times in self._message_times.values())
        }


class TwilioNotifierFromEnv(TwilioNotifier):
    """
    Twilio notifier that reads credentials from environment variables.

    Environment variables:
        TWILIO_ACCOUNT_SID: Twilio Account SID
        TWILIO_AUTH_TOKEN: Twilio Auth Token
        TWILIO_FROM_NUMBER: Twilio phone number
        TWILIO_TO_NUMBERS: Comma-separated list of recipient numbers

    Example:
        export TWILIO_ACCOUNT_SID=ACxxxxx
        export TWILIO_AUTH_TOKEN=xxxxx
        export TWILIO_FROM_NUMBER=+15551234567
        export TWILIO_TO_NUMBERS=+15559876543,+15551112222
    """

    def __init__(
        self,
        min_level: AlertLevel = AlertLevel.WARNING,
        include_map_link: bool = True,
        max_messages_per_hour: int = 10
    ):
        """Initialize from environment variables."""
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID', '')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        from_number = os.environ.get('TWILIO_FROM_NUMBER', '')
        to_numbers_str = os.environ.get('TWILIO_TO_NUMBERS', '')

        if not all([account_sid, auth_token, from_number, to_numbers_str]):
            print("WARNING: Twilio environment variables not set")
            print("Required: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, TWILIO_TO_NUMBERS")
            # Initialize with empty values (will be disabled)
            to_numbers = []
        else:
            to_numbers = [n.strip() for n in to_numbers_str.split(',') if n.strip()]

        super().__init__(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
            to_numbers=to_numbers,
            min_level=min_level,
            include_map_link=include_map_link,
            max_messages_per_hour=max_messages_per_hour
        )


class PushoverNotifier:
    """
    Send push notifications via Pushover.

    Pushover is a simple push notification service for iOS, Android, and Desktop.
    Get credentials at https://pushover.net/

    Requires: pip install requests (or uses urllib)
    """

    # Pushover priority levels
    PRIORITY_LOWEST = -2
    PRIORITY_LOW = -1
    PRIORITY_NORMAL = 0
    PRIORITY_HIGH = 1
    PRIORITY_EMERGENCY = 2  # Requires acknowledgment

    def __init__(
        self,
        user_key: str,
        api_token: str,
        devices: Optional[List[str]] = None,
        min_level: AlertLevel = AlertLevel.WARNING,
        sound_critical: str = 'siren',
        sound_warning: str = 'pushover',
        sound_default: str = 'pushover'
    ):
        """
        Initialize Pushover notifier.

        Args:
            user_key: Pushover user key (or group key)
            api_token: Pushover application API token
            devices: List of device names to send to (None = all devices)
            min_level: Minimum alert level to send push
            sound_critical: Sound for CRITICAL alerts
            sound_warning: Sound for WARNING alerts
            sound_default: Sound for other alerts
        """
        self.user_key = user_key
        self.api_token = api_token
        self.devices = devices
        self.min_level = min_level
        self.sounds = {
            AlertLevel.CRITICAL: sound_critical,
            AlertLevel.WARNING: sound_warning,
            AlertLevel.WATCH: sound_default,
            AlertLevel.INFO: sound_default
        }
        self.api_url = 'https://api.pushover.net/1/messages.json'

    def __call__(self, alert: Alert):
        """Send push notification."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send push notification via Pushover."""
        if alert.level.value < self.min_level.value:
            return

        # Build message
        title = f"[{alert.level.name}] {alert.event_name}"
        message = self._format_message(alert)

        # Determine priority
        priority = self._get_priority(alert.level)

        # Build payload
        payload = {
            'token': self.api_token,
            'user': self.user_key,
            'title': title,
            'message': message,
            'priority': priority,
            'sound': self.sounds.get(alert.level, 'pushover'),
            'url': f"https://maps.google.com/?q={alert.location[0]:.4f},{alert.location[1]:.4f}",
            'url_title': 'View on Map'
        }

        # Add device filter if specified
        if self.devices:
            payload['device'] = ','.join(self.devices)

        # Emergency priority requires retry/expire
        if priority == self.PRIORITY_EMERGENCY:
            payload['retry'] = 60  # Retry every 60 seconds
            payload['expire'] = 3600  # Expire after 1 hour

        # Send request
        try:
            data = urllib.parse.urlencode(payload).encode('utf-8')
            req = urllib.request.Request(self.api_url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print(f"Pushover notification sent: {alert.level.name}")
                else:
                    print(f"Pushover error: status {response.status}")
        except Exception as e:
            print(f"Pushover error: {e}")

    def _format_message(self, alert: Alert) -> str:
        """Format alert message for push notification."""
        lines = [
            f"Hail: {alert.hail_size_mm:.0f}mm ({alert.hail_size_mm/25.4:.1f}\")",
            f"PDR Score: {alert.pdr_score:.0f}/100",
            f"Probability: {alert.hail_probability:.0f}%",
            f"Radar: {alert.radar_id}",
            f"Location: ({alert.location[0]:.2f}, {alert.location[1]:.2f})",
            "",
            alert.message
        ]
        return "\n".join(lines)

    def _get_priority(self, level: AlertLevel) -> int:
        """Map alert level to Pushover priority."""
        return {
            AlertLevel.CRITICAL: self.PRIORITY_EMERGENCY,
            AlertLevel.WARNING: self.PRIORITY_HIGH,
            AlertLevel.WATCH: self.PRIORITY_NORMAL,
            AlertLevel.INFO: self.PRIORITY_LOW
        }.get(level, self.PRIORITY_NORMAL)


class NtfyNotifier:
    """
    Send push notifications via ntfy.sh.

    ntfy is a free, open-source push notification service.
    No account required! Just subscribe to a topic in the ntfy app.

    Website: https://ntfy.sh/
    Apps: iOS, Android, Web, CLI

    Usage:
        1. Install ntfy app on your phone
        2. Subscribe to a topic (e.g., "hailtracker-alerts-abc123")
        3. Use that topic name here
    """

    def __init__(
        self,
        topic: str,
        server: str = 'https://ntfy.sh',
        min_level: AlertLevel = AlertLevel.WARNING,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize ntfy notifier.

        Args:
            topic: Topic name to publish to (subscribers receive notifications)
            server: ntfy server URL (default: https://ntfy.sh, or self-hosted)
            min_level: Minimum alert level to send push
            username: Optional username for authenticated topics
            password: Optional password for authenticated topics
        """
        self.topic = topic
        self.server = server.rstrip('/')
        self.min_level = min_level
        self.username = username
        self.password = password

    def __call__(self, alert: Alert):
        """Send push notification."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send push notification via ntfy."""
        if alert.level.value < self.min_level.value:
            return

        url = f"{self.server}/{self.topic}"

        # Message body
        message = self._format_message(alert)

        # Build headers (ntfy uses custom headers for metadata)
        headers = {
            'Content-Type': 'text/plain; charset=utf-8',
            'Title': f"{alert.level.name}: {alert.event_name}",
            'Priority': self._get_priority(alert.level),
            'Tags': self._get_tags(alert),
            'Click': f"https://maps.google.com/?q={alert.location[0]:.4f},{alert.location[1]:.4f}",
        }

        # Add auth if provided
        if self.username and self.password:
            import base64
            auth = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers['Authorization'] = f'Basic {auth}'

        try:
            req = urllib.request.Request(
                url,
                data=message.encode('utf-8'),
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print(f"ntfy notification sent to topic '{self.topic}'")
                else:
                    print(f"ntfy error: status {response.status}")
        except urllib.error.HTTPError as e:
            print(f"ntfy error: {e.code} - {e.reason}")
        except Exception as e:
            print(f"ntfy error: {e}")

    def _format_message(self, alert: Alert) -> str:
        """Format alert message."""
        lines = [
            f"Hail Size: {alert.hail_size_mm:.0f}mm ({alert.hail_size_mm/25.4:.1f}\")",
            f"PDR Score: {alert.pdr_score:.0f}/100",
            f"Probability: {alert.hail_probability:.0f}%",
            f"Severity: {alert.severity.upper()}",
            f"Radar: {alert.radar_id}",
            "",
            alert.message
        ]
        return "\n".join(lines)

    def _get_priority(self, level: AlertLevel) -> str:
        """Map alert level to ntfy priority."""
        return {
            AlertLevel.CRITICAL: 'urgent',
            AlertLevel.WARNING: 'high',
            AlertLevel.WATCH: 'default',
            AlertLevel.INFO: 'low'
        }.get(level, 'default')

    def _get_tags(self, alert: Alert) -> str:
        """Get emoji tags for notification."""
        tags = {
            AlertLevel.CRITICAL: 'rotating_light,cloud,zap',
            AlertLevel.WARNING: 'warning,cloud',
            AlertLevel.WATCH: 'eyes,cloud',
            AlertLevel.INFO: 'information_source'
        }
        return tags.get(alert.level, 'cloud')


class FCMNotifier:
    """
    Send push notifications via Firebase Cloud Messaging (FCM).

    FCM is Google's push notification service for Android, iOS, and Web.

    Setup:
        1. Create Firebase project at https://console.firebase.google.com/
        2. Generate a service account key (JSON file)
        3. Set up your mobile app with FCM SDK
        4. Get device registration tokens from your app

    Requires: pip install google-auth requests
    """

    def __init__(
        self,
        credentials_path: str,
        device_tokens: List[str],
        project_id: str,
        min_level: AlertLevel = AlertLevel.WARNING
    ):
        """
        Initialize FCM notifier.

        Args:
            credentials_path: Path to Firebase service account JSON file
            device_tokens: List of FCM device registration tokens
            project_id: Firebase project ID
            min_level: Minimum alert level to send push
        """
        self.credentials_path = credentials_path
        self.device_tokens = device_tokens
        self.project_id = project_id
        self.min_level = min_level
        self.fcm_url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

        self._access_token = None
        self._token_expiry = None

    def __call__(self, alert: Alert):
        """Send push notification."""
        self.notify(alert)

    def notify(self, alert: Alert):
        """Send push notification via FCM."""
        if alert.level.value < self.min_level.value:
            return

        # Get access token
        access_token = self._get_access_token()
        if not access_token:
            print("FCM error: Could not get access token")
            return

        # Send to each device
        for token in self.device_tokens:
            self._send_to_device(token, alert, access_token)

    def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token for FCM."""
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            # Check if we have a valid cached token
            if self._access_token and self._token_expiry:
                if datetime.now() < self._token_expiry:
                    return self._access_token

            # Get new token
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=['https://www.googleapis.com/auth/firebase.messaging']
            )
            credentials.refresh(Request())

            self._access_token = credentials.token
            self._token_expiry = credentials.expiry

            return self._access_token

        except ImportError:
            print("FCM error: google-auth not installed. Install with: pip install google-auth")
            return None
        except Exception as e:
            print(f"FCM auth error: {e}")
            return None

    def _send_to_device(self, device_token: str, alert: Alert, access_token: str):
        """Send notification to a specific device."""
        # Build FCM message
        message = {
            'message': {
                'token': device_token,
                'notification': {
                    'title': f"{alert.level.name}: {alert.event_name}",
                    'body': f"Hail: {alert.hail_size_mm:.0f}mm | PDR: {alert.pdr_score:.0f}/100 | {alert.radar_id}"
                },
                'data': {
                    'alert_id': alert.id,
                    'level': alert.level.name,
                    'lat': str(alert.location[0]),
                    'lon': str(alert.location[1]),
                    'pdr_score': str(alert.pdr_score),
                    'hail_size_mm': str(alert.hail_size_mm),
                    'radar_id': alert.radar_id
                },
                'android': {
                    'priority': 'high' if alert.level.value >= AlertLevel.WARNING.value else 'normal',
                    'notification': {
                        'channel_id': 'hailtracker_alerts',
                        'sound': 'default'
                    }
                },
                'apns': {
                    'payload': {
                        'aps': {
                            'sound': 'default',
                            'badge': 1
                        }
                    }
                }
            }
        }

        try:
            data = json.dumps(message).encode('utf-8')
            req = urllib.request.Request(
                self.fcm_url,
                data=data,
                headers={
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    print(f"FCM notification sent to device ...{device_token[-6:]}")
                else:
                    print(f"FCM error: status {response.status}")
        except Exception as e:
            print(f"FCM error: {e}")


class PushoverNotifierFromEnv(PushoverNotifier):
    """
    Pushover notifier using environment variables.

    Environment variables:
        PUSHOVER_USER_KEY: Pushover user/group key
        PUSHOVER_API_TOKEN: Pushover application API token
        PUSHOVER_DEVICES: Comma-separated device names (optional)
    """

    def __init__(self, min_level: AlertLevel = AlertLevel.WARNING):
        user_key = os.environ.get('PUSHOVER_USER_KEY', '')
        api_token = os.environ.get('PUSHOVER_API_TOKEN', '')
        devices_str = os.environ.get('PUSHOVER_DEVICES', '')

        if not user_key or not api_token:
            print("WARNING: Pushover environment variables not set")
            print("Required: PUSHOVER_USER_KEY, PUSHOVER_API_TOKEN")

        devices = [d.strip() for d in devices_str.split(',') if d.strip()] if devices_str else None

        super().__init__(
            user_key=user_key,
            api_token=api_token,
            devices=devices,
            min_level=min_level
        )


class NtfyNotifierFromEnv(NtfyNotifier):
    """
    ntfy notifier using environment variables.

    Environment variables:
        NTFY_TOPIC: Topic name (required)
        NTFY_SERVER: Server URL (optional, default: https://ntfy.sh)
        NTFY_USERNAME: Username for auth (optional)
        NTFY_PASSWORD: Password for auth (optional)
    """

    def __init__(self, min_level: AlertLevel = AlertLevel.WARNING):
        topic = os.environ.get('NTFY_TOPIC', '')
        server = os.environ.get('NTFY_SERVER', 'https://ntfy.sh')
        username = os.environ.get('NTFY_USERNAME')
        password = os.environ.get('NTFY_PASSWORD')

        if not topic:
            print("WARNING: NTFY_TOPIC environment variable not set")

        super().__init__(
            topic=topic,
            server=server,
            min_level=min_level,
            username=username,
            password=password
        )
