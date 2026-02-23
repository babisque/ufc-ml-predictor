import sqlite3
import requests
import subprocess
from bs4 import BeautifulSoup

DB_PATH = "data/ufc_predictions.db"

def get_recent_results():
    """
    Goes to UFC Stats to get the link of the last COMPLETED event
    and extracts who actually won the fights.
    """
    url_base = "http://ufcstats.com/statistics/events/completed"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    resp = requests.get(url_base, headers=headers)
    soup = BeautifulSoup(resp.content, 'html.parser')
    
    rows = soup.select('tr.b-statistics__table-row')[1:]
    
    completed_event_link = None
    for row in rows:
        if not row.find('img', src=lambda s: s and 'next.png' in s):
            tag_link = row.find('a', class_='b-link')

            if tag_link is not None:
                completed_event_link = tag_link['href']
                break
            else:
                continue
            
    if not completed_event_link:
        return {}

    resp_event = requests.get(completed_event_link, headers=headers)
    soup_event = BeautifulSoup(resp_event.content, 'html.parser')
    
    results = {}
    fight_rows = soup_event.select('tbody.b-fight-details__table-body tr')
    
    for row in fight_rows:
        names = row.find_all('a', class_='b-link b-link_style_black')
        if len(names) >= 2:
            winner = names[0].text.strip()
            loser = names[1].text.strip()
            
            results[winner] = winner
            results[loser] = winner
            
    return results

def audit_predictions():
    """Checks pending predictions and updates them with actual results."""
    print("🔍 Starting audit of results...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, fighter_1, fighter_2, predicted_winner FROM predictions WHERE actual_winner IS NULL AND event_name != 'Individual Fight'")
    pending = cursor.fetchall()
    
    if not pending:
        print("✅ No predictions pending audit.")
        conn.close()
        return

    actual_results = get_recent_results()
    if not actual_results:
        print("❌ Could not load results from the last event.")
        conn.close()
        return

    updates = 0
    for bet_id, f1, f2, predicted in pending:
        actual_winner = actual_results.get(f1) or actual_results.get(f2)
        
        if actual_winner:
            is_correct = 1 if predicted == actual_winner else 0
            
            cursor.execute('''
                UPDATE predictions 
                SET actual_winner = ?, is_correct = ? 
                WHERE id = ?
            ''', (actual_winner, is_correct, bet_id))
            updates += 1

    conn.commit()
    conn.close()
    print(f"✅ Audit completed! {updates} predictions updated in the database.")
    
    if updates > 0:
        print("🔄 Re-running the pipeline to update the model with new results...")
        try:
            subprocess.Popen(["python", "pipeline.py"])
            print("🚀 Pipeline triggered successfully.")

        except Exception as e:
            print(f"❌ Failed to trigger pipeline: {e}")

if __name__ == "__main__":
    audit_predictions()