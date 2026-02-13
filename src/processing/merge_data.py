import pandas as pd
import numpy as np
import os

FIGHTS_FILE = 'data/processed/clean_fight_details.csv'
FIGHTERS_FILE = 'data/processed/clean_fighter_details.csv'
OUTPUT_FILE = 'data/processed/merged_data.csv'

def calculate_age(row, dob_col, date_col):
    """Calculate age at the time of the fight."""
    if pd.isna(row[dob_col]) or pd.isna(row[date_col]):
        return np.nan
    try:
        born = pd.to_datetime(row[dob_col])
        fight_date = pd.to_datetime(row[date_col])
        return (fight_date - born).days / 365.25
    except:
        return np.nan
    
def merge_data():
    if not os.path.exists(FIGHTS_FILE) or not os.path.exists(FIGHTERS_FILE):
        print("Required files are missing. Please ensure both fight and fighter details CSV files are present.")
        return
    
    print("Loading data...")
    fights = pd.read_csv(FIGHTS_FILE)
    fighters = pd.read_csv(FIGHTERS_FILE)

    fights['event_date'] = pd.to_datetime(fights['event_date'], errors='coerce')

    print("Merging winner deta...")
    fights = fights.merge(
        fighters[['url', 'height_cm', 'weight_kg', 'reach_cm', 'stance', 'dob']], 
        left_on='winner_link', 
        right_on='url', 
        how='left'
    )

    fights.rename(columns={
        'height_cm': 'winner_height',
        'weight_kg': 'winner_weight',
        'reach_cm': 'winner_reach',
        'stance': 'winner_stance',
        'dob': 'winner_dob'
    }, inplace=True)
    fights.drop(columns=['url'], inplace=True)

    print("Merging loser deta...")
    fights = fights.merge(
        fighters[['url', 'height_cm', 'weight_kg', 'reach_cm', 'stance', 'dob']], 
        left_on='loser_link', 
        right_on='url', 
        how='left'
    )

    fights.rename(columns={
        'height_cm': 'loser_height',
        'weight_kg': 'loser_weight',
        'reach_cm': 'loser_reach',
        'stance': 'loser_stance',
        'dob': 'loser_dob'
    }, inplace=True)
    fights.drop(columns=['url'], inplace=True)

    print("Calculating ages at the time of the fight...")
    fights['winner_age'] = fights.apply(lambda x: calculate_age(x, 'winner_dob', 'event_date'), axis=1)
    fights['loser_age'] = fights.apply(lambda x: calculate_age(x, 'loser_dob', 'event_date'), axis=1)

    fights.drop(columns=['winner_dob', 'loser_dob'], inplace=True)
    print("Saving merged data...")
    fights.to_csv(OUTPUT_FILE, index=False)

    missing_age = fights['winner_age'].isna().sum()
    print(f"Total fights: {len(fights)}")
    print(f"Fights missing age data: {missing_age})")
    print(f"New columns sample: {list(fights.columns[-10:])}")

if __name__ == "__main__":
    merge_data()