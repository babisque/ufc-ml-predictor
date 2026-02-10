import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import os
from tqdm import tqdm

INPUT_FILE = 'data/raw/all_fights.csv'
OUTPUT_FILE = 'data/raw/fight_details.csv'

def clean_text(text):
    return text.strip().replace('\n', ' ').replace('  ', ' ')

def extract_values(td):
    """
    Function to handle with cells with two values
    Returns a tuple (fighter_1, fighter_2)
    """
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

        tables = soup.find_all('table', style=False)

        if not tables:
            return None

        rows = tables[0].find_all('tr', class_='b-fight-details__table-row')
        if len(rows) < 2: return None

        data_row = rows[1]
        cols = data_row.find_all('td')

        # fighters
        f1_name, f2_name = extract_values(cols[0])

        # Knockdowns
        f1_kd, f2_kd = extract_values(cols[1])
        
        # Significant Strikes (ex: "10 of 20")
        f1_sig_str, f2_sig_str = extract_values(cols[2])
        
        # Sig Str %
        f1_sig_pct, f2_sig_pct = extract_values(cols[3])
        
        # Total Strikes
        f1_tot_str, f2_tot_str = extract_values(cols[4])
        
        # Takedowns (ex: "1 of 3")
        f1_td, f2_td = extract_values(cols[5])
        
        # Td %
        f1_td_pct, f2_td_pct = extract_values(cols[6])
        
        # Sub Attempts
        f1_sub_att, f2_sub_att = extract_values(cols[7])
        
        # Reversals
        f1_rev, f2_rev = extract_values(cols[8])
        
        # Control Time
        f1_ctrl, f2_ctrl = extract_values(cols[9])

        return {
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
        print(f"Error in {url}: {e}")
        return None

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"{INPUT_FILE} not found")
        return

    fights_df = pd.read_csv(INPUT_FILE)
    total_fights = len(fights_df)

    if os.path.exists(OUTPUT_FILE):
        existing_data = pd.read_csv(OUTPUT_FILE)
        processed_links = set(existing_data['fight_link'].unique())
        print(f"Resuming... {len(processed_links)} fights processed")
    else:
        existing_data = pd.DataFrame()
        processed_links = set()

    print(f"Scrape starting for {total_fights} fight details")

    new_rows = []
    save_interval = 50

    for index, row in tqdm(fights_df.iterrows(), total=total_fights):
        link = row['fight_link']

        if link in processed_links:
            continue

        stats = get_fight_stats(link)

        if stats:
            full_record = row.to_dict()
            new_rows.append(full_record)
            processed_links.add(link)

        if len(new_rows) >= save_interval:
            chunk_df = pd.DataFrame(new_rows)
            header = not os.path.exists(OUTPUT_FILE)
            chunk_df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False)

            new_rows = []
            time.sleep(0.1)

    if new_rows:
        chunk_df = pd.DataFrame(new_rows)
        header = not os.path.exists(OUTPUT_FILE)
        chunk_df.to_csv(OUTPUT_FILE, mode='a', header=header, index=False)

    print("Scrape done")


if __name__ == "__main__":
    main()
