import pandas as pd
import requests
from bs4 import BeautifulSoup
import os
from tqdm import tqdm
import time

INPUT_FILE = 'data/raw/all_fights.csv'
OUTPUT_FILE = 'data/raw/fighter_details.csv'
SAVE_INTERVAL = 50 

def clean_text(text):
    return text.replace('\n', ' ').strip()

def get_fighter_details(fighter_url):
    try:
        response = requests.get(fighter_url, timeout=10)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')
        
        name_tag = soup.find('h2', class_='b-content__title')
        if not name_tag: return None
        name = name_tag.text.strip()

        info_box = soup.find('div', class_='b-list__info-box')
        if not info_box: return None
        
        stats = {'name': name, 'url': fighter_url}
        
        for li in info_box.find_all('li'):
            label_tag = li.find('i')
            if not label_tag: continue
            
            label = label_tag.text.strip().replace(':', '')
            value = li.text.replace(label_tag.text, '').strip()
            
            if label == 'Height':
                stats['height'] = value
            elif label == 'Weight':
                stats['weight'] = value
            elif label == 'Reach':
                stats['reach'] = value
            elif label == 'STANCE':
                stats['stance'] = value
            elif label == 'DOB':
                stats['dob'] = value

        return stats

    except Exception as e:
        print(f"Error extracting {fighter_url}: {e}")
        return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Input file {INPUT_FILE} not found.")
        return

    print("Reading fight list to find fighters...")
    fights_df = pd.read_csv(INPUT_FILE)
    
    if 'winner_link' not in fights_df.columns:
        print("ERROR: The fights file does not have links! Update and run fights.py first.")
        return

    all_links = set(fights_df['winner_link'].unique()) | set(fights_df['loser_link'].unique())
    print(f"Total fighters found in the database: {len(all_links)}")

    processed_links = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing = pd.read_csv(OUTPUT_FILE)
            if 'url' in existing.columns:
                processed_links = set(existing['url'].unique())
                print(f"Resuming... {len(processed_links)} fighters already processed.")
        except pd.errors.EmptyDataError:
            print("Output file is empty. Starting from scratch.")

    links_to_process = list(all_links - processed_links)

    print(f"Starting scrape of {len(links_to_process)} remaining fighters...")

    if not links_to_process:
        print("All fighters have already been processed!")
        return

    fighters_data = []
    
    for i, link in enumerate(tqdm(links_to_process)):
        details = get_fighter_details(link)
        
        if details:
            fighters_data.append(details)
        
        time.sleep(0.05)
        
        if len(fighters_data) >= SAVE_INTERVAL or (i + 1) == len(links_to_process):
            if fighters_data:
                df_chunk = pd.DataFrame(fighters_data)
                
                header = not os.path.exists(OUTPUT_FILE)
                
                df_chunk.to_csv(OUTPUT_FILE, mode='a', header=header, index=False)
                
                fighters_data = []

    print("Scrape of fighters completed successfully!")

if __name__ == "__main__":
    main()