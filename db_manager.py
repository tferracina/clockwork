"""Database connection management for Clockwork."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Custom exception for database-related errors."""
    pass

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.

    Yields:
        sqlite3.Connection: Database connection object

    Raises:
        DatabaseError: If connection or database operation fails
    """
    conn = None
    try:
        conn = sqlite3.connect(str(Path.home() / ".clockwork" / "timelog.db"))
        conn.row_factory = sqlite3.Row  # Enable row factory for named columns
        yield conn
    except sqlite3.Error as e:
        logger.error("Database connection error: %s", str(e))
        raise DatabaseError(f"Failed to connect to database: {str(e)}") from e
    finally:
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error as e:
                logger.error("Error closing database connection: %s", str(e))

@contextmanager
def get_db_cursor(conn: sqlite3.Connection) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager for database cursors.

    Args:
        conn: Database connection

    Yields:
        sqlite3.Cursor: Database cursor object

    Raises:
        DatabaseError: If cursor operation fails
    """
    cursor = None
    try:
        cursor = conn.cursor()
        yield cursor
    except sqlite3.Error as e:
        logger.error("Database cursor error: %s", str(e))
        raise DatabaseError(f"Failed to create cursor: {str(e)}") from e
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except sqlite3.Error as e:
                logger.error("Error closing cursor: %s", str(e))

def init_db() -> None:
    """Initialize the database with required tables."""
    try:
        db_path = Path.home() / ".clockwork" / "timelog.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS timelog (
                        id INTEGER PRIMARY KEY,
                        category TEXT NOT NULL,
                        activity TEXT NOT NULL,
                        task TEXT NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        duration INTEGER,
                        notes TEXT
                    )
                """)
                # Add indexes for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timelog_dates
                    ON timelog(start_time, end_time)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timelog_category
                    ON timelog(category)
                """)
                conn.commit()
                logger.info("Database initialized successfully")
    except (sqlite3.Error, OSError) as e:
        logger.error("Database initialization error: %s", str(e))
        raise DatabaseError(f"Failed to initialize database: {str(e)}") from e

def execute_query(query: str, params: Optional[tuple] = None) -> list:
    """
    Execute a database query safely.

    Args:
        query: SQL query string
        params: Query parameters (optional)

    Returns:
        list: Query results

    Raises:
        DatabaseError: If query execution fails
    """
    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
    except sqlite3.Error as e:
        logger.error("Query execution error: %s", str(e))
        raise DatabaseError(f"Failed to execute query: {str(e)}") from e

def execute_write_query(query: str, params: Optional[tuple] = None) -> int:
    """
    Execute a write query (INSERT, UPDATE, DELETE) safely.

    Args:
        query: SQL query string
        params: Query parameters (optional)

    Returns:
        int: Last row id for INSERT, or number of affected rows for UPDATE/DELETE

    Raises:
        DatabaseError: If query execution fails
    """
    try:
        with get_db_connection() as conn:
            with get_db_cursor(conn) as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    except sqlite3.Error as e:
        logger.error("Write query execution error: %s", str(e))
        raise DatabaseError(f"Failed to execute write query: {str(e)}") from e