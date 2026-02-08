"""
Alert Manager - Handle alert creation and dispatch

Manages alert levels, throttling, and notification dispatch.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import json
import os


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = 1        # Informational - storm detected
    WATCH = 2       # Watch - potential hail
    WARNING = 3     # Warning - hail likely
    CRITICAL = 4    # Critical - severe hail, immediate action


@dataclass
class Alert:
    """Individual alert object."""

    # Alert identification
    id: str
    timestamp: datetime
    level: AlertLevel

    # Event details
    event_name: str
    location: tuple  # (lat, lon)
    radar_id: str

    # Hail analysis
    hail_detected: bool
    hail_probability: float
    hail_size_mm: float
    severity: str
    pdr_score: float

    # Radar data
    max_reflectivity: float
    mesh_mm: float
    posh: float

    # Additional context
    message: str = ""
    recommendations: List[str] = field(default_factory=list)
    expires: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.name,
            'event_name': self.event_name,
            'location': {
                'lat': self.location[0],
                'lon': self.location[1]
            },
            'radar_id': self.radar_id,
            'hail': {
                'detected': self.hail_detected,
                'probability': round(self.hail_probability, 1),
                'size_mm': round(self.hail_size_mm, 1),
                'size_inches': round(self.hail_size_mm / 25.4, 2),
                'severity': self.severity
            },
            'pdr_score': round(self.pdr_score, 1),
            'radar': {
                'max_reflectivity': round(self.max_reflectivity, 1),
                'mesh_mm': round(self.mesh_mm, 1),
                'posh': round(self.posh, 1)
            },
            'message': self.message,
            'recommendations': self.recommendations,
            'expires': self.expires.isoformat() if self.expires else None
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def format_text(self) -> str:
        """Format as human-readable text."""
        level_emoji = {
            AlertLevel.INFO: "[INFO]",
            AlertLevel.WATCH: "[WATCH]",
            AlertLevel.WARNING: "[WARNING]",
            AlertLevel.CRITICAL: "[CRITICAL]"
        }

        lines = [
            f"{level_emoji.get(self.level, '')} {self.level.name} ALERT - {self.event_name}",
            f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Location: ({self.location[0]:.4f}, {self.location[1]:.4f})",
            f"Radar: {self.radar_id}",
            "",
            f"HAIL ANALYSIS:",
            f"  Detected: {'YES' if self.hail_detected else 'NO'}",
            f"  Probability: {self.hail_probability:.0f}%",
            f"  Size: {self.hail_size_mm:.0f} mm ({self.hail_size_mm/25.4:.2f}\")",
            f"  Severity: {self.severity.upper()}",
            "",
            f"PDR OPPORTUNITY: {self.pdr_score:.0f}/100",
            "",
            f"RADAR DATA:",
            f"  Max Reflectivity: {self.max_reflectivity:.0f} dBZ",
            f"  MESH: {self.mesh_mm:.0f} mm",
            f"  POSH: {self.posh:.0f}%",
        ]

        if self.message:
            lines.extend(["", f"MESSAGE: {self.message}"])

        if self.recommendations:
            lines.extend(["", "RECOMMENDATIONS:"])
            for rec in self.recommendations:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


class AlertManager:
    """
    Manage alerts and notification dispatch.

    Handles:
    - Alert creation and validation
    - Duplicate/throttling logic
    - Notification dispatch to multiple channels
    - Alert history and logging
    """

    def __init__(
        self,
        alert_log_path: Optional[str] = None,
        throttle_minutes: int = 15,
        min_pdr_score: float = 40.0
    ):
        """
        Initialize alert manager.

        Args:
            alert_log_path: Path to save alert history
            throttle_minutes: Minimum time between alerts for same location
            min_pdr_score: Minimum PDR score to generate alert
        """
        self.alert_log_path = alert_log_path or "data/alerts/alert_history.json"
        self.throttle_minutes = throttle_minutes
        self.min_pdr_score = min_pdr_score

        self.notifiers: List[Callable[[Alert], None]] = []
        self.alert_history: List[Alert] = []
        self.recent_alerts: Dict[str, datetime] = {}  # location_key -> last_alert_time

        self._alert_counter = 0

        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.alert_log_path), exist_ok=True)

    def add_notifier(self, notifier: Callable[[Alert], None]):
        """Add a notification handler."""
        self.notifiers.append(notifier)

    def create_alert(
        self,
        event_data: Dict,
        classification: Dict,
        radar_data: Dict
    ) -> Optional[Alert]:
        """
        Create an alert from analysis results.

        Args:
            event_data: Event details (name, location, radar_id, timestamp)
            classification: ML classification results
            radar_data: Raw radar analysis data

        Returns:
            Alert object or None if below threshold
        """
        pdr_score = classification.get('pdr_score', 0)
        hail_detected = classification.get('hail_detected', False)

        # Check minimum threshold
        if pdr_score < self.min_pdr_score and not hail_detected:
            return None

        # Check throttling
        location_key = f"{event_data['location'][0]:.2f},{event_data['location'][1]:.2f}"
        if location_key in self.recent_alerts:
            last_alert = self.recent_alerts[location_key]
            if datetime.now() - last_alert < timedelta(minutes=self.throttle_minutes):
                return None  # Throttled

        # Determine alert level
        level = self._determine_level(classification)

        # Generate alert ID
        self._alert_counter += 1
        alert_id = f"HAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"

        # Generate recommendations
        recommendations = self._generate_recommendations(classification, pdr_score)

        # Create alert
        alert = Alert(
            id=alert_id,
            timestamp=datetime.now(),
            level=level,
            event_name=event_data.get('name', 'Storm Event'),
            location=event_data['location'],
            radar_id=event_data.get('radar_id', 'UNKNOWN'),
            hail_detected=hail_detected,
            hail_probability=classification.get('probability', 0),
            hail_size_mm=classification.get('size_mm', 0),
            severity=classification.get('severity', 'none'),
            pdr_score=pdr_score,
            max_reflectivity=radar_data.get('max_reflectivity', 0),
            mesh_mm=radar_data.get('mesh_mm', 0),
            posh=radar_data.get('posh', 0),
            message=self._generate_message(classification, level),
            recommendations=recommendations,
            expires=datetime.now() + timedelta(hours=2)
        )

        # Update tracking
        self.recent_alerts[location_key] = datetime.now()
        self.alert_history.append(alert)

        return alert

    def dispatch_alert(self, alert: Alert):
        """Send alert to all registered notifiers."""
        for notifier in self.notifiers:
            try:
                notifier(alert)
            except Exception as e:
                print(f"Notifier error: {e}")

        # Log alert
        self._log_alert(alert)

    def _determine_level(self, classification: Dict) -> AlertLevel:
        """Determine alert level from classification."""
        severity = classification.get('severity', 'none')
        pdr_score = classification.get('pdr_score', 0)
        probability = classification.get('probability', 0)

        if severity in ['catastrophic', 'severe'] or pdr_score >= 80:
            return AlertLevel.CRITICAL
        elif severity == 'moderate' or pdr_score >= 60:
            return AlertLevel.WARNING
        elif classification.get('hail_detected') or pdr_score >= 40:
            return AlertLevel.WATCH
        else:
            return AlertLevel.INFO

    def _generate_message(self, classification: Dict, level: AlertLevel) -> str:
        """Generate alert message."""
        severity = classification.get('severity', 'none')
        size_mm = classification.get('size_mm', 0)
        size_in = size_mm / 25.4

        if level == AlertLevel.CRITICAL:
            return f"SEVERE HAIL DETECTED! Estimated {size_mm:.0f}mm ({size_in:.1f}\") hail. Immediate PDR deployment recommended."
        elif level == AlertLevel.WARNING:
            return f"Hail likely. Estimated {size_mm:.0f}mm ({size_in:.1f}\"). Monitor closely and prepare for deployment."
        elif level == AlertLevel.WATCH:
            return f"Potential hail event. {classification.get('probability', 0):.0f}% probability. Continue monitoring."
        else:
            return "Storm activity detected. No significant hail expected."

    def _generate_recommendations(self, classification: Dict, pdr_score: float) -> List[str]:
        """Generate action recommendations."""
        recommendations = []

        if pdr_score >= 80:
            recommendations.extend([
                "Deploy PDR team immediately",
                "Contact local dealerships and body shops",
                "Set up temporary repair stations",
                "Document storm path for insurance claims"
            ])
        elif pdr_score >= 60:
            recommendations.extend([
                "Prepare PDR team for potential deployment",
                "Monitor storm progression",
                "Pre-contact key accounts in affected area"
            ])
        elif pdr_score >= 40:
            recommendations.extend([
                "Continue monitoring radar updates",
                "Review coverage area for potential impacts"
            ])

        severity = classification.get('severity', 'none')
        if severity in ['severe', 'catastrophic']:
            recommendations.append("Expect significant vehicle damage - multiple dents per panel")
        elif severity == 'moderate':
            recommendations.append("Expect moderate damage - good PDR opportunity")

        return recommendations

    def _log_alert(self, alert: Alert):
        """Log alert to file."""
        try:
            # Load existing
            if os.path.exists(self.alert_log_path):
                with open(self.alert_log_path, 'r') as f:
                    history = json.load(f)
            else:
                history = []

            # Append new alert
            history.append(alert.to_dict())

            # Keep last 1000 alerts
            if len(history) > 1000:
                history = history[-1000:]

            # Save
            with open(self.alert_log_path, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            print(f"Error logging alert: {e}")

    def get_active_alerts(self) -> List[Alert]:
        """Get alerts that haven't expired."""
        now = datetime.now()
        return [a for a in self.alert_history if a.expires and a.expires > now]

    def get_alert_stats(self) -> Dict:
        """Get alert statistics."""
        if not self.alert_history:
            return {'total': 0}

        levels = [a.level.name for a in self.alert_history]
        return {
            'total': len(self.alert_history),
            'critical': levels.count('CRITICAL'),
            'warning': levels.count('WARNING'),
            'watch': levels.count('WATCH'),
            'info': levels.count('INFO'),
            'avg_pdr_score': sum(a.pdr_score for a in self.alert_history) / len(self.alert_history)
        }
