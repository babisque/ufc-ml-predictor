import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re

EVENTS_URL = "http://ufcstats.com/statistics/events/completed?page=all"
HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

def get_next_event():
        
    response = requests.get(EVENTS_URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')
    next_icon = soup.find('img', src=re.compile(r'next\.png'))

    if next_icon:
        row = next_icon.find_parent('tr')
        
        link_tag = row.find('a', class_='b-link')
        date_tag = row.find('span', class_='b-statistics__date')
        
        event_name = link_tag.text.strip()
        event_link = link_tag['href']
        event_date = date_tag.text.strip()
        
        print(f"Next event found: {event_name} | Date: {event_date}")
        return {
            'name': event_name,
            'link': event_link,
            'date': event_date
        }
    else:
        print("No future events found.")
        return None
    
def get_event_fights(event_link):
    """
    Find the link of the next event and extract the fights list with fighters names and weight class
    """
    try:
        response = requests.get(event_link, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    fights = []

    fights_rows = soup.select('tbody.b-fight-details__table-body tr')

    for row in fights_rows:
        names = row.find_all('a', class_='b-link b-link_style_black')
        if len(names) >= 2:
            lutador_1 = names[0].text.strip()
            lutador_2 = names[1].text.strip()
            
            columns = row.find_all('td')
            categoria_suja = columns[6].text.strip() if len(columns) > 6 else "Catch Weight"
            
            categoria_limpa = categoria_suja.replace(' Bout', '').replace(' Title', '').strip()
            
            fights.append((lutador_1, lutador_2, categoria_limpa))
            
    return fights


def get_all_events():
    """
    Search all UFC events list
    return a DataFrame with: Name, Date, Local and link
    """
    print(f"Downloading event list from: {EVENTS_URL}...")

    try:
        response = requests.get(EVENTS_URL, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.select('tr.b-statistics__table-row')

    events_data = []

    for row in rows[1:]:
        cols = row.find_all('td')

        if not cols:
            continue

        link_tag = cols[0].find('a')

        if link_tag is None:
            continue

        event_name = link_tag.text.strip()
        event_link = link_tag['href']

        date_span = cols[0].find('span')
        event_date = date_span.text.strip() if date_span else "Unknown date"

        event_location = cols[1].text.strip()

        events_data.append({
            'name': event_name,
            'date': event_date,
            'location': event_location,
            'link': event_link
        })

    return pd.DataFrame(events_data)

def save_raw_data(df):
    """Saves DataFrame into `data/raw` folder"""
    os.makedirs('data/raw', exist_ok=True)

    file_path = 'data/raw/all_events.csv'
    df.to_csv(file_path, index=False)
    print(f"Done! {len(df)} events saved in: {file_path}")

if __name__ == "__main__":
    df_events = get_all_events()

    if df_events is not None:
        save_raw_data(df_events)
        print(df_events.head())
