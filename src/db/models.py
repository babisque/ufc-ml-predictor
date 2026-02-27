from datetime import datetime
from .connection import get_db_connection

def init_db():
    """Creates the database and table if they don't exist."""
    with get_db_connection() as conn:
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
        print("✅ Database initialized successfully!")

def save_prediction(event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence):
    """Saves a new prediction to the database, skipping if the fight already exists for the event."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*) FROM predictions
            WHERE event_name = ? AND fighter_1 = ? AND fighter_2 = ?
        ''', (event_name, fighter_1, fighter_2))
        
        if cursor.fetchone()[0] > 0:
            return 

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO predictions (event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence, prediction_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (event_name, fighter_1, fighter_2, weight_class, predicted_winner, confidence, now))
        conn.commit()

def get_event_predictions(event_name):
    """Returns cached predictions for a given event name."""
    with get_db_connection() as conn:
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
        return cursor.fetchall()

def get_statistics():
    """Queries the database and returns the numbers of correct predictions, errors, and pending ones."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct IS NOT NULL")
        total_resolved = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE is_correct = 1")
        total_correct = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM predictions WHERE actual_winner IS NULL AND event_name != 'Individual Fight'")
        total_pending = cursor.fetchone()[0]
        
        return total_resolved, total_correct, total_pending

def get_last_event_predictions():
    """Fetches the predictions for the last resolved event."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT event_name 
            FROM predictions 
            WHERE is_correct IS NOT NULL AND event_name != 'Luta Individual'
            ORDER BY id DESC LIMIT 1
        ''')
        row = cursor.fetchone()

        if not row:
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

        return last_event_name, total_resolved, total_correct, fights

if __name__ == "__main__":
    init_db()