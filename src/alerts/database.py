"""
Database Storage for HailTracker Alerts

Provides persistent storage for alert history with support for:
- SQLite (default, no external dependencies)
- PostgreSQL (for production/scalability)

Usage:
    # SQLite (default)
    db = AlertDatabase()

    # SQLite with custom path
    db = AlertDatabase('sqlite:///path/to/alerts.db')

    # PostgreSQL
    db = AlertDatabase('postgresql://user:pass@localhost/hailtracker')
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from dataclasses import asdict

from .alert_manager import Alert, AlertLevel


class AlertDatabase:
    """
    Database storage for alerts.

    Routes through src.db.engine when DATABASE_URL is PostgreSQL.
    Falls back to local SQLite when DATABASE_URL is SQLite.
    """

    def __init__(
        self,
        connection_string: str = None,
        auto_create: bool = True
    ):
        """
        Initialize database connection.

        When the global DATABASE_URL is PostgreSQL, the connection_string
        parameter is ignored and all connections use the central engine pool.
        """
        from src.db.engine import is_postgres as _engine_pg

        if _engine_pg():
            self.db_type = 'postgresql'
            self.connection_string = None
            self.db_path = None
        else:
            self.connection_string = connection_string or 'sqlite:///data/alerts/alerts.db'
            self.db_type = 'sqlite' if self.connection_string.startswith('sqlite') else 'postgresql'

            if self.db_type == 'sqlite':
                self.db_path = self.connection_string.replace('sqlite:///', '')
                if not self.db_path:
                    self.db_path = 'data/alerts/alerts.db'
                os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)

        # Legacy pool (only used when AlertDatabase has its own PG connection string)
        self._pg_pool = None

        if auto_create:
            self._create_tables()

    @contextmanager
    def _get_connection(self):
        """Get database connection (routes through engine when PG)."""
        from src.db.engine import is_postgres as _engine_pg

        if _engine_pg():
            from src.db.engine import get_connection as _engine_conn
            with _engine_conn() as conn:
                yield conn
        elif self.db_type == 'sqlite':
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(self.db_path)
            conn.row_factory = _sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        else:
            conn = self._get_pg_connection()
            try:
                yield conn
                conn.commit()
            finally:
                self._release_pg_connection(conn)

    def _get_pg_connection(self):
        """Get PostgreSQL connection (legacy: own pool)."""
        try:
            import psycopg2
            import psycopg2.extras

            if self._pg_pool is None:
                from psycopg2 import pool
                self._pg_pool = pool.SimpleConnectionPool(
                    1, 10,
                    self.connection_string
                )

            conn = self._pg_pool.getconn()
            conn.cursor_factory = psycopg2.extras.RealDictCursor
            return conn

        except ImportError:
            raise ImportError("psycopg2 not installed. Install with: pip install psycopg2-binary")

    def _release_pg_connection(self, conn):
        """Release PostgreSQL connection back to pool."""
        if self._pg_pool:
            self._pg_pool.putconn(conn)

    def _create_tables(self):
        """Create database tables."""
        if self.db_type == 'sqlite':
            self._create_sqlite_tables()
        else:
            self._create_pg_tables()

    def _create_sqlite_tables(self):
        """Create SQLite tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    radar_id TEXT NOT NULL,
                    hail_detected INTEGER NOT NULL,
                    hail_probability REAL NOT NULL,
                    hail_size_mm REAL NOT NULL,
                    severity TEXT NOT NULL,
                    pdr_score REAL NOT NULL,
                    max_reflectivity REAL NOT NULL,
                    mesh_mm REAL NOT NULL,
                    posh REAL NOT NULL,
                    message TEXT,
                    recommendations TEXT,
                    expires TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_radar ON alerts(radar_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_pdr ON alerts(pdr_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(lat, lon)')

            # Alert statistics table (for aggregations)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_stats (
                    date TEXT PRIMARY KEY,
                    total_alerts INTEGER DEFAULT 0,
                    critical_count INTEGER DEFAULT 0,
                    warning_count INTEGER DEFAULT 0,
                    watch_count INTEGER DEFAULT 0,
                    info_count INTEGER DEFAULT 0,
                    avg_pdr_score REAL DEFAULT 0,
                    max_hail_size REAL DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def _create_pg_tables(self):
        """Create PostgreSQL tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    level TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    lat DOUBLE PRECISION NOT NULL,
                    lon DOUBLE PRECISION NOT NULL,
                    radar_id TEXT NOT NULL,
                    hail_detected BOOLEAN NOT NULL,
                    hail_probability DOUBLE PRECISION NOT NULL,
                    hail_size_mm DOUBLE PRECISION NOT NULL,
                    severity TEXT NOT NULL,
                    pdr_score DOUBLE PRECISION NOT NULL,
                    max_reflectivity DOUBLE PRECISION NOT NULL,
                    mesh_mm DOUBLE PRECISION NOT NULL,
                    posh DOUBLE PRECISION NOT NULL,
                    message TEXT,
                    recommendations JSONB,
                    expires TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_radar ON alerts(radar_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_pdr ON alerts(pdr_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_location ON alerts(lat, lon)')

            # Alert statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_stats (
                    date DATE PRIMARY KEY,
                    total_alerts INTEGER DEFAULT 0,
                    critical_count INTEGER DEFAULT 0,
                    warning_count INTEGER DEFAULT 0,
                    watch_count INTEGER DEFAULT 0,
                    info_count INTEGER DEFAULT 0,
                    avg_pdr_score DOUBLE PRECISION DEFAULT 0,
                    max_hail_size DOUBLE PRECISION DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def save_alert(self, alert: Alert) -> bool:
        """
        Save an alert to the database.

        Args:
            alert: Alert object to save

        Returns:
            True if saved successfully
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Prepare data
                recommendations = json.dumps(alert.recommendations) if self.db_type == 'sqlite' else alert.recommendations

                if self.db_type == 'sqlite':
                    cursor.execute('''
                        INSERT OR REPLACE INTO alerts (
                            id, timestamp, level, event_name, lat, lon, radar_id,
                            hail_detected, hail_probability, hail_size_mm, severity,
                            pdr_score, max_reflectivity, mesh_mm, posh,
                            message, recommendations, expires
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        alert.id,
                        alert.timestamp.isoformat(),
                        alert.level.name,
                        alert.event_name,
                        alert.location[0],
                        alert.location[1],
                        alert.radar_id,
                        1 if alert.hail_detected else 0,
                        alert.hail_probability,
                        alert.hail_size_mm,
                        alert.severity,
                        alert.pdr_score,
                        alert.max_reflectivity,
                        alert.mesh_mm,
                        alert.posh,
                        alert.message,
                        recommendations,
                        alert.expires.isoformat() if alert.expires else None
                    ))
                else:
                    cursor.execute('''
                        INSERT INTO alerts (
                            id, timestamp, level, event_name, lat, lon, radar_id,
                            hail_detected, hail_probability, hail_size_mm, severity,
                            pdr_score, max_reflectivity, mesh_mm, posh,
                            message, recommendations, expires
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            level = EXCLUDED.level,
                            message = EXCLUDED.message
                    ''', (
                        alert.id,
                        alert.timestamp,
                        alert.level.name,
                        alert.event_name,
                        alert.location[0],
                        alert.location[1],
                        alert.radar_id,
                        alert.hail_detected,
                        alert.hail_probability,
                        alert.hail_size_mm,
                        alert.severity,
                        alert.pdr_score,
                        alert.max_reflectivity,
                        alert.mesh_mm,
                        alert.posh,
                        alert.message,
                        json.dumps(recommendations),
                        alert.expires
                    ))

                # Update daily stats
                self._update_daily_stats(cursor, alert)

            return True

        except Exception as e:
            print(f"Database error saving alert: {e}")
            return False

    def _update_daily_stats(self, cursor, alert: Alert):
        """Update daily statistics."""
        date_str = alert.timestamp.strftime('%Y-%m-%d')

        if self.db_type == 'sqlite':
            # Get current stats
            cursor.execute('SELECT * FROM alert_stats WHERE date = ?', (date_str,))
            row = cursor.fetchone()

            if row:
                # Update existing
                level_col = f"{alert.level.name.lower()}_count"
                cursor.execute(f'''
                    UPDATE alert_stats SET
                        total_alerts = total_alerts + 1,
                        {level_col} = {level_col} + 1,
                        avg_pdr_score = (avg_pdr_score * total_alerts + ?) / (total_alerts + 1),
                        max_hail_size = MAX(max_hail_size, ?),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                ''', (alert.pdr_score, alert.hail_size_mm, date_str))
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO alert_stats (
                        date, total_alerts, critical_count, warning_count,
                        watch_count, info_count, avg_pdr_score, max_hail_size
                    ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str,
                    1 if alert.level == AlertLevel.CRITICAL else 0,
                    1 if alert.level == AlertLevel.WARNING else 0,
                    1 if alert.level == AlertLevel.WATCH else 0,
                    1 if alert.level == AlertLevel.INFO else 0,
                    alert.pdr_score,
                    alert.hail_size_mm
                ))

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get a single alert by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            placeholder = '?' if self.db_type == 'sqlite' else '%s'
            cursor.execute(f'SELECT * FROM alerts WHERE id = {placeholder}', (alert_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_alert(row)
            return None

    def get_alerts(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        level: AlertLevel = None,
        radar_id: str = None,
        min_pdr_score: float = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'timestamp',
        order_desc: bool = True
    ) -> List[Alert]:
        """
        Query alerts with filters.

        Args:
            start_time: Filter by start time
            end_time: Filter by end time
            level: Filter by alert level
            radar_id: Filter by radar ID
            min_pdr_score: Filter by minimum PDR score
            limit: Maximum results to return
            offset: Offset for pagination
            order_by: Column to order by
            order_desc: Order descending

        Returns:
            List of Alert objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Build query
            conditions = []
            params = []
            placeholder = '?' if self.db_type == 'sqlite' else '%s'

            if start_time:
                conditions.append(f'timestamp >= {placeholder}')
                params.append(start_time.isoformat() if self.db_type == 'sqlite' else start_time)

            if end_time:
                conditions.append(f'timestamp <= {placeholder}')
                params.append(end_time.isoformat() if self.db_type == 'sqlite' else end_time)

            if level:
                conditions.append(f'level = {placeholder}')
                params.append(level.name)

            if radar_id:
                conditions.append(f'radar_id = {placeholder}')
                params.append(radar_id)

            if min_pdr_score:
                conditions.append(f'pdr_score >= {placeholder}')
                params.append(min_pdr_score)

            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            order_dir = 'DESC' if order_desc else 'ASC'

            query = f'''
                SELECT * FROM alerts
                WHERE {where_clause}
                ORDER BY {order_by} {order_dir}
                LIMIT {placeholder} OFFSET {placeholder}
            '''
            params.extend([limit, offset])

            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [self._row_to_alert(row) for row in rows]

    def get_recent_alerts(self, hours: int = 24, limit: int = 50) -> List[Alert]:
        """Get alerts from the last N hours."""
        start_time = datetime.now() - timedelta(hours=hours)
        return self.get_alerts(start_time=start_time, limit=limit)

    def get_alerts_by_location(
        self,
        lat: float,
        lon: float,
        radius_km: float = 50,
        limit: int = 50
    ) -> List[Alert]:
        """
        Get alerts near a location.

        Args:
            lat: Latitude
            lon: Longitude
            radius_km: Search radius in kilometers
            limit: Maximum results

        Returns:
            List of alerts within radius
        """
        # Approximate degree distance (1 degree ~ 111 km)
        lat_range = radius_km / 111.0
        lon_range = radius_km / (111.0 * abs(cos(radians(lat))))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholder = '?' if self.db_type == 'sqlite' else '%s'

            cursor.execute(f'''
                SELECT * FROM alerts
                WHERE lat BETWEEN {placeholder} AND {placeholder}
                AND lon BETWEEN {placeholder} AND {placeholder}
                ORDER BY timestamp DESC
                LIMIT {placeholder}
            ''', (
                lat - lat_range, lat + lat_range,
                lon - lon_range, lon + lon_range,
                limit
            ))

            return [self._row_to_alert(row) for row in cursor.fetchall()]

    def get_statistics(self, days: int = 30) -> Dict:
        """
        Get alert statistics for the last N days.

        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholder = '?' if self.db_type == 'sqlite' else '%s'

            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            # Get aggregated stats
            if self.db_type == 'sqlite':
                cursor.execute('''
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN level = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
                        SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END) as warning,
                        SUM(CASE WHEN level = 'WATCH' THEN 1 ELSE 0 END) as watch,
                        SUM(CASE WHEN level = 'INFO' THEN 1 ELSE 0 END) as info,
                        AVG(pdr_score) as avg_pdr,
                        MAX(hail_size_mm) as max_hail,
                        AVG(hail_size_mm) as avg_hail,
                        COUNT(DISTINCT radar_id) as radars_count,
                        COUNT(DISTINCT date(timestamp)) as days_with_alerts
                    FROM alerts
                    WHERE timestamp >= ?
                ''', (start_date,))
            else:
                cursor.execute('''
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN level = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
                        SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END) as warning,
                        SUM(CASE WHEN level = 'WATCH' THEN 1 ELSE 0 END) as watch,
                        SUM(CASE WHEN level = 'INFO' THEN 1 ELSE 0 END) as info,
                        AVG(pdr_score) as avg_pdr,
                        MAX(hail_size_mm) as max_hail,
                        AVG(hail_size_mm) as avg_hail,
                        COUNT(DISTINCT radar_id) as radars_count,
                        COUNT(DISTINCT DATE(timestamp)) as days_with_alerts
                    FROM alerts
                    WHERE timestamp >= %s
                ''', (start_date,))

            row = cursor.fetchone()

            stats = {
                'period_days': days,
                'total_alerts': row['total'] or 0,
                'by_level': {
                    'critical': row['critical'] or 0,
                    'warning': row['warning'] or 0,
                    'watch': row['watch'] or 0,
                    'info': row['info'] or 0
                },
                'avg_pdr_score': round(row['avg_pdr'] or 0, 1),
                'max_hail_size_mm': round(row['max_hail'] or 0, 1),
                'avg_hail_size_mm': round(row['avg_hail'] or 0, 1),
                'unique_radars': row['radars_count'] or 0,
                'days_with_alerts': row['days_with_alerts'] or 0
            }

            # Get top radars
            cursor.execute(f'''
                SELECT radar_id, COUNT(*) as count
                FROM alerts
                WHERE timestamp >= {placeholder}
                GROUP BY radar_id
                ORDER BY count DESC
                LIMIT 5
            ''', (start_date,))

            stats['top_radars'] = [
                {'radar': row['radar_id'], 'count': row['count']}
                for row in cursor.fetchall()
            ]

            # Get daily trend
            cursor.execute(f'''
                SELECT date(timestamp) as date, COUNT(*) as count
                FROM alerts
                WHERE timestamp >= {placeholder}
                GROUP BY date(timestamp)
                ORDER BY date
            ''', (start_date,))

            stats['daily_trend'] = [
                {'date': row['date'], 'count': row['count']}
                for row in cursor.fetchall()
            ]

            return stats

    def delete_old_alerts(self, days: int = 90) -> int:
        """
        Delete alerts older than N days.

        Args:
            days: Delete alerts older than this many days

        Returns:
            Number of deleted alerts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            placeholder = '?' if self.db_type == 'sqlite' else '%s'

            cutoff = (datetime.now() - timedelta(days=days)).isoformat()

            cursor.execute(f'SELECT COUNT(*) as count FROM alerts WHERE timestamp < {placeholder}', (cutoff,))
            count = cursor.fetchone()['count']

            cursor.execute(f'DELETE FROM alerts WHERE timestamp < {placeholder}', (cutoff,))

            print(f"Deleted {count} alerts older than {days} days")
            return count

    def export_to_json(self, filepath: str, **query_params) -> int:
        """
        Export alerts to JSON file.

        Args:
            filepath: Output file path
            **query_params: Filters to pass to get_alerts()

        Returns:
            Number of exported alerts
        """
        alerts = self.get_alerts(**query_params)

        data = {
            'exported_at': datetime.now().isoformat(),
            'count': len(alerts),
            'alerts': [alert.to_dict() for alert in alerts]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Exported {len(alerts)} alerts to {filepath}")
        return len(alerts)

    def export_to_csv(self, filepath: str, **query_params) -> int:
        """
        Export alerts to CSV file.

        Args:
            filepath: Output file path
            **query_params: Filters to pass to get_alerts()

        Returns:
            Number of exported alerts
        """
        import csv

        alerts = self.get_alerts(**query_params)

        if not alerts:
            print("No alerts to export")
            return 0

        fieldnames = [
            'id', 'timestamp', 'level', 'event_name', 'lat', 'lon',
            'radar_id', 'hail_detected', 'hail_probability', 'hail_size_mm',
            'severity', 'pdr_score', 'max_reflectivity', 'mesh_mm', 'posh', 'message'
        ]

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for alert in alerts:
                writer.writerow({
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'level': alert.level.name,
                    'event_name': alert.event_name,
                    'lat': alert.location[0],
                    'lon': alert.location[1],
                    'radar_id': alert.radar_id,
                    'hail_detected': alert.hail_detected,
                    'hail_probability': alert.hail_probability,
                    'hail_size_mm': alert.hail_size_mm,
                    'severity': alert.severity,
                    'pdr_score': alert.pdr_score,
                    'max_reflectivity': alert.max_reflectivity,
                    'mesh_mm': alert.mesh_mm,
                    'posh': alert.posh,
                    'message': alert.message
                })

        print(f"Exported {len(alerts)} alerts to {filepath}")
        return len(alerts)

    def _row_to_alert(self, row) -> Alert:
        """Convert database row to Alert object."""
        # Handle both sqlite Row and psycopg2 dict
        if hasattr(row, 'keys'):
            data = dict(row)
        else:
            data = row

        # Parse recommendations
        recommendations = data.get('recommendations', '[]')
        if isinstance(recommendations, str):
            recommendations = json.loads(recommendations)

        # Parse timestamps
        timestamp = data['timestamp']
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        expires = data.get('expires')
        if expires and isinstance(expires, str):
            expires = datetime.fromisoformat(expires)

        return Alert(
            id=data['id'],
            timestamp=timestamp,
            level=AlertLevel[data['level']],
            event_name=data['event_name'],
            location=(data['lat'], data['lon']),
            radar_id=data['radar_id'],
            hail_detected=bool(data['hail_detected']),
            hail_probability=data['hail_probability'],
            hail_size_mm=data['hail_size_mm'],
            severity=data['severity'],
            pdr_score=data['pdr_score'],
            max_reflectivity=data['max_reflectivity'],
            mesh_mm=data['mesh_mm'],
            posh=data['posh'],
            message=data.get('message', ''),
            recommendations=recommendations,
            expires=expires
        )

    def get_count(self) -> int:
        """Get total number of alerts in database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM alerts')
            return cursor.fetchone()['count']

    def close(self):
        """Close database connections."""
        if self._pg_pool:
            self._pg_pool.closeall()


class DatabaseNotifier:
    """
    Notifier that saves alerts to database.

    Use this as a notifier in AlertManager to automatically
    save all alerts to the database.
    """

    def __init__(self, database: AlertDatabase):
        """
        Initialize database notifier.

        Args:
            database: AlertDatabase instance
        """
        self.database = database

    def __call__(self, alert: Alert):
        """Save alert to database."""
        self.database.save_alert(alert)


# Helper function for location queries
from math import cos, radians
