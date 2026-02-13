import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
from tqdm import tqdm

INPUT_EVENTS_FILE = 'data/raw/all_events.csv'
OUTPUT_FIGHTS_FILE = 'data/raw/all_fights.csv'
SAVE_INTERVAL = 10 

def get_fight_details(event_url):
    """
    Enters in fight page and scrap every fight
    """
    try:
        response = requests.get(event_url, timeout=10)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.select('tr.b-fight-details__table-row')

        fights = []

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 7: continue

            fighters = cols[1].find_all('a')
            if len(fighters) < 2: continue

            winner = fighters[0].text.strip()
            winner_link = fighters[0]['href']

            loser = fighters[1].text.strip()
            loser_link = fighters[1]['href']
    
            fight_link = cols[0].find('a')['href'] if cols[0].find('a') else None
            if not fight_link:
                fight_link = row.get('data-link')

            weight_class = cols[6].text.strip()
            method = cols[7].text.strip()

            fights.append({
                'winner': winner,
                'winner_link': winner_link,
                'loser': loser,
                'loser_link': loser_link,
                'weight_class': weight_class,
                'method': method,
                'fight_link': fight_link
            })

        return fights

    except Exception as e:
        print(f"Error in event {event_url}: {e}")
        return []

def main():
    if not os.path.exists(INPUT_EVENTS_FILE):
        print(f"Event files {INPUT_EVENTS_FILE} not found.")
        return

    events_df = pd.read_csv(INPUT_EVENTS_FILE)
    
    processed_events = set()
    if os.path.exists(OUTPUT_FIGHTS_FILE):
        try:
            existing_fights = pd.read_csv(OUTPUT_FIGHTS_FILE)
            if 'event_name' in existing_fights.columns:
                processed_events = set(existing_fights['event_name'].unique())
                print(f"Resuming... {len(processed_events)} events already processed.")
        except pd.errors.EmptyDataError:
            print("Output file exists but is empty. Starting from scratch.")

    events_to_process = events_df[~events_df['name'].isin(processed_events)]

    print(f"Starting scrape of {len(events_to_process)} remaining events...")

    if len(events_to_process) == 0:
        print("All events have already been processed!")
        return

    os.makedirs('data/raw', exist_ok=True)

    batch_fights = []
    
    for i, (index, row) in enumerate(tqdm(events_to_process.iterrows(), total=len(events_to_process))):
        event_url = row['link']
        event_name = row['name']
        event_date = row['date']

        fights = get_fight_details(event_url)

        for f in fights:
            f['event_name'] = event_name
            f['event_date'] = event_date
            batch_fights.append(f)

        time.sleep(0.1)

        if (i + 1) % SAVE_INTERVAL == 0 or (i + 1) == len(events_to_process):
            if batch_fights:
                new_df = pd.DataFrame(batch_fights)
                
                header_mode = not os.path.exists(OUTPUT_FIGHTS_FILE)
                
                new_df.to_csv(OUTPUT_FIGHTS_FILE, mode='a', header=header_mode, index=False)
                
                batch_fights = []

    print("Scrape completed successfully!")

if __name__ == "__main__":
    main()