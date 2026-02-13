import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
from tqdm import tqdm

INPUT_FILE = 'data/raw/all_fights.csv'
OUTPUT_FILE = 'data/raw/fight_details.csv'
SAVE_INTERVAL = 10

def extract_header_stats(soup):
    """
    Extracts header data like Round, Time, Method, Referee and details
    """
    stats = {
        'total_rounds': None,
        'last_round_time': None,
        'time_format': None,
        'referee': None,
        'win_method_details': None
    }

    content_div = soup.find('div', class_='b-fight-details__content')
    if not content_div:
        return stats
    
    for item in content_div.find_all('i', class_='b-fight-details__text-item'):
        label_tag = item.find('i', class_='b-fight-details__label')
        if not label_tag:
            continue
            
        label = label_tag.text.strip().replace(':', '')
        value = item.text.replace(label_tag.text, '').strip()
        
        if label == 'Round':
            stats['total_rounds'] = value
        elif label == 'Time':
            stats['last_round_time'] = value
        elif label == 'Time format':
            stats['time_format'] = value
        elif label == 'Referee':
            stats['referee'] = value

    text_paragraphs = content_div.find_all('p', class_='b-fight-details__text')
    if len(text_paragraphs) >= 2:
        details_text = text_paragraphs[1].text.strip()
        if 'Details:' in details_text:
             stats['win_method_details'] = details_text.replace('Details:', '').strip()

    return stats

def clean_text(text):
    return text.strip().replace('\n', ' ').replace('  ', ' ')

def extract_values(td):
    p_tags = td.find_all('p')
    if len(p_tags) == 2:
        return clean_text(p_tags[0].text), clean_text(p_tags[1].text)
    return None, None

def get_fight_stats(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')

        header_stats = extract_header_stats(soup)        

        tables = soup.find_all('table') 
        if not tables: return None

        rows = tables[0].find_all('tr', class_='b-fight-details__table-row')
        if len(rows) < 2: return None

        data_row = rows[1]
        cols = data_row.find_all('td')

        f1_name, f2_name = extract_values(cols[0])
        f1_kd, f2_kd = extract_values(cols[1])
        f1_sig_str, f2_sig_str = extract_values(cols[2])
        f1_sig_pct, f2_sig_pct = extract_values(cols[3])
        f1_tot_str, f2_tot_str = extract_values(cols[4])
        f1_td, f2_td = extract_values(cols[5])
        f1_td_pct, f2_td_pct = extract_values(cols[6])
        f1_sub_att, f2_sub_att = extract_values(cols[7])
        f1_rev, f2_rev = extract_values(cols[8])
        f1_ctrl, f2_ctrl = extract_values(cols[9])

        return {
            'end_round': header_stats['total_rounds'],
            'end_time': header_stats['last_round_time'],
            'time_format': header_stats['time_format'],
            'referee': header_stats['referee'],
            'method_detail': header_stats['win_method_details'],
            'f1_name': f1_name, 'f2_name': f2_name,
            'f1_kd': f1_kd, 'f2_kd': f2_kd,
            'f1_sig_str': f1_sig_str, 'f2_sig_str': f2_sig_str,
            'f1_sig_pct': f1_sig_pct, 'f2_sig_pct': f2_sig_pct,
            'f1_tot_str': f1_tot_str, 'f2_tot_str': f2_tot_str,
            'f1_td': f1_td, 'f2_td': f2_td,
            'f1_td_pct': f1_td_pct, 'f2_td_pct': f2_td_pct,
            'f1_sub_att': f1_sub_att, 'f2_sub_att': f2_sub_att,
            'f1_rev': f1_rev, 'f2_rev': f2_rev,
            'f1_ctrl': f1_ctrl, 'f2_ctrl': f2_ctrl
        }

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found.")
        return

    fights_df = pd.read_csv(INPUT_FILE)
    
    processed_links = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            existing_data = pd.read_csv(OUTPUT_FILE)
            if 'fight_link' in existing_data.columns:
                processed_links = set(existing_data['fight_link'].unique())
                print(f"Resuming... {len(processed_links)} processed fights found.")
        except pd.errors.EmptyDataError:
            print("Output file is empty. Starting from scratch.")

    fights_to_process = fights_df[~fights_df['fight_link'].isin(processed_links)]

    print(f"Starting scrape of details for {len(fights_to_process)} remaining fights...")

    if len(fights_to_process) == 0:
        print("All fights have already been processed!")
        return

    new_rows = []

    for i, (index, row) in enumerate(tqdm(fights_to_process.iterrows(), total=len(fights_to_process))):
        link = row['fight_link']
        stats = get_fight_stats(link)

        if stats:
            full_record = row.to_dict() | stats 
            new_rows.append(full_record)

        time.sleep(0.05)

        if len(new_rows) >= SAVE_INTERVAL or (i + 1) == len(fights_to_process):
            if new_rows:
                chunk_df = pd.DataFrame(new_rows)
                
                header = not os.path.exists(OUTPUT_FILE)
                
                chunk_df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False)
                new_rows = []

    print("Scrape completed successfully!")

if __name__ == "__main__":
    main()