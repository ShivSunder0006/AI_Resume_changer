"""
Simple SQLite-based memory store for conversation/session history.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger


class MemoryStore:
    """Persistent memory for job application sessions."""

    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialise database tables."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                resume_path TEXT,
                job_description TEXT,
                output_path TEXT,
                validation_result TEXT,
                evaluation_scores TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        conn.commit()
        conn.close()
        logger.debug(f"Memory store initialised: {self.db_path}")

    def create_session(self, session_id: str, resume_path: str, jd: str) -> str:
        """Create a new tailoring session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, created_at, resume_path, job_description) "
            "VALUES (?, ?, ?, ?)",
            (session_id, datetime.now(timezone.utc).isoformat(), resume_path, jd),
        )
        conn.commit()
        conn.close()
        return session_id

    def update_session(self, session_id: str, **kwargs):
        """Update session fields."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            cursor.execute(
                f"UPDATE sessions SET {key} = ? WHERE id = ?",
                (value, session_id),
            )
        conn.commit()
        conn.close()

    def get_session(self, session_id: str) -> dict | None:
        """Retrieve a session by ID."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        columns = [
            "id", "created_at", "resume_path", "job_description",
            "output_path", "validation_result", "evaluation_scores", "status"
        ]
        session = dict(zip(columns, row))

        # Parse JSON fields
        for field in ("validation_result", "evaluation_scores"):
            if session.get(field):
                try:
                    session[field] = json.loads(session[field])
                except json.JSONDecodeError:
                    pass

        return session

    def list_sessions(self, limit: int = 20) -> list[dict]:
        """List recent sessions."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, created_at, status FROM sessions "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {"id": r[0], "created_at": r[1], "status": r[2]}
            for r in rows
        ]

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to a session."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        conn.close()
