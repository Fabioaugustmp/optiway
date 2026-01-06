import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "flight_cache.db"

class FlightCache:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                origin TEXT NOT NULL,
                destination TEXT NOT NULL,
                date TEXT NOT NULL,
                provider TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(origin, destination, date, provider)
            )
        """)
        conn.commit()
        conn.close()

    def get_cached_response(self, origin: str, destination: str, date: str, provider: str = "AMADEUS"):
        """Returns the cached JSON response or None if not found."""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT response_json FROM api_cache 
            WHERE origin = ? AND destination = ? AND date = ? AND provider = ?
        """, (origin, destination, date, provider))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None

    def save_response(self, origin: str, destination: str, date: str, data: dict, provider: str = "AMADEUS"):
        """Saves the JSON response to the cache."""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Serialize data to JSON
        json_str = json.dumps(data)
        created_at = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO api_cache (origin, destination, date, provider, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (origin, destination, date, provider, json_str, created_at))
            conn.commit()
        except Exception as e:
            print(f"Cache Save Error: {e}")
        finally:
            conn.close()
