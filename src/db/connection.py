import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("DATABASE_URL", "data/ufc_predictions.db")

@contextmanager
def get_db_connection():
    """
    Creates a safe, self-closing database connection.
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # do stuff
    """
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()