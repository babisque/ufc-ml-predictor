import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
from tqdm import tqdm

def get_fight_details(event_url):
    """
Enters in fight page and scrap every fight
    """
    try:
        response = requests.get(event_url)
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
            loser = fighters[1].text.strip()

            fight_link = cols[0].find('a')['href'] if cols[0].find('a') else None
            if not fight_link:
                fight_link = row.get('data-link')

            weight_class = cols[6].text.strip()
            method = cols[7].text.strip()

            fights.append({
                'winner': winner,
                'loser': loser,
                'weight_class': weight_class,
                'method': method,
                'fight_link': fight_link
            })

        return fights

    except Exception as e:
        print(f"Error in event {event_url}: {e}")
        return []

def main():
    events_df = pd.read_csv('data/raw/all_events.csv')
    # events_df = events_df.head(5)

    all_fights = []

    print(f"Starting scrape of {len(events_df)} events")

    for index, row in tqdm(events_df.iterrows(), total=len(events_df)):
        event_url = row['link']
        event_name = row['name']
        event_date = row['date']

        fights = get_fight_details(event_url)

        for f in fights:
            f['event_name'] = event_name
            f['event_date'] = event_date
            all_fights.append(f)

        time.sleep(0.1)

    fights_df = pd.DataFrame(all_fights)
    os.makedirs('data/processed', exist_ok=True)
    fights_df.to_csv('data/raw/all_fights.csv', index=False)

    print(f"{len(fights_df)} fights saved.")

if __name__ == "__main__":
    main()
