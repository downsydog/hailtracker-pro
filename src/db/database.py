"""
Simple Database wrapper for CRM operations
"""

import sqlite3
from datetime import datetime


class Database:
    """Simple SQLite database wrapper with common operations"""

    def __init__(self, db_path='data/hailtracker_crm.db'):
        self.db_path = db_path

    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def execute(self, query, params=None):
        """Execute query and return results as list of dicts"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith(('SELECT', 'WITH')):
                results = [dict(row) for row in cursor.fetchall()]
                conn.close()
                return results
            else:
                conn.commit()
                conn.close()
                return cursor.lastrowid
        except Exception as e:
            conn.close()
            raise e

    def insert(self, table, data, auto_timestamps=True):
        """Insert a row into table and return the new ID

        Args:
            table: Table name
            data: Dictionary of column: value pairs
            auto_timestamps: If True, auto-add created_at/updated_at (default True)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # Add timestamps if not present and auto_timestamps is enabled
        if auto_timestamps:
            if 'created_at' not in data:
                data['created_at'] = datetime.now().isoformat()
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now().isoformat()

        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            cursor.execute(query, list(data.values()))
            conn.commit()
            row_id = cursor.lastrowid
            conn.close()
            return row_id
        except Exception as e:
            conn.close()
            raise e

    def update(self, table, row_id, data):
        """Update a row by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Add updated_at if not present
        if 'updated_at' not in data:
            data['updated_at'] = datetime.now().isoformat()

        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"

        try:
            cursor.execute(query, list(data.values()) + [row_id])
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected
        except Exception as e:
            conn.close()
            raise e

    def delete(self, table, row_id, soft=True):
        """Delete a row by ID (soft delete by default)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            if soft:
                cursor.execute(
                    f"UPDATE {table} SET deleted_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), row_id)
                )
            else:
                cursor.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))

            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected
        except Exception as e:
            conn.close()
            raise e

    def get_by_id(self, table, row_id):
        """Get a single row by ID"""
        results = self.execute(
            f"SELECT * FROM {table} WHERE id = ? AND (deleted_at IS NULL OR deleted_at = '')",
            (row_id,)
        )
        return results[0] if results else None
