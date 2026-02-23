import sqlite3
import os
from datetime import datetime

DB_PATH = "data/ufc_predictions.db"

def init_db():
    """Creates the database and table if they don't exist."""
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT,
            fighter_1 TEXT,
            fighter_2 TEXT,
            weight_class TEXT,
            predicted_winner TEXT,
            confidence REAL,
            prediction_date TEXT,
            actual_winner TEXT,
            is_correct INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def save_prediction(event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence):
    """Saves a new prediction to the database, skipping if the fight already exists for the event."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) FROM predictions
        WHERE event_name = ? AND fighter_1 = ? AND fighter_2 = ?
    ''', (event_name, fighter_1, fighter_2))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO predictions (event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence, prediction_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence, now))

    conn.commit()
    conn.close()

def get_event_predictions(event_name):
    """Returns cached predictions for a given event name.
    Returns a list of tuples: (fighter_1, fighter_2, weight_class, predicted_winner, confidence)
    or an empty list if none exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT fighter_1, fighter_2, weight_class, predicted_winner, confidence
        FROM predictions
        WHERE event_name = ? AND id IN (
            SELECT MIN(id) FROM predictions
            WHERE event_name = ?
            GROUP BY fighter_1, fighter_2
        )
        ORDER BY id ASC
    ''', (event_name, event_name))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_statistics():
    """Queries the database and returns the numbers of correct predictions, errors, and pending ones."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct IS NOT NULL")
    total_resolved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct = 1")
    total_correct = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE actual_winner IS NULL AND event_name != 'Individual Fight'")
    total_pending = cursor.fetchone()[0]
    
    conn.close()
    
    return total_resolved, total_correct, total_pending

def get_last_event_predictions():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT event_name 
        FROM predictions 
        WHERE is_correct IS NOT NULL AND event_name != 'Luta Individual'
        ORDER BY id DESC LIMIT 1
    ''')
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None, 0, 0, []
    
    last_event_name = row[0]
    cursor.execute("SELECT COUNT(*) FROM predictions WHERE event_name = ? AND is_correct IS NOT NULL", (last_event_name,))
    total_resolved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE event_name = ? AND is_correct = 1", (last_event_name,))
    total_correct = cursor.fetchone()[0]

    cursor.execute('''
        SELECT fighter_1, fighter_2, predicted_winner, actual_winner, is_correct, confidence 
        FROM predictions 
        WHERE event_name = ?
    ''', (last_event_name,))
    fights = cursor.fetchall()

    conn.close()

    return last_event_name, total_resolved, total_correct, fights

if __name__ == "__main__":
    init_db()