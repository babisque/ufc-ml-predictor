import pandas as pd
import numpy as np

INPUT_FILE = 'data/raw/fight_details.csv'
OUTPUT_FILE = 'data/processed/clean_fight_details.csv'

def clean_percentage(value):
    if value == '---' or pd.isna(value):
        return 0.0
    if isinstance(value, str):
        try:
            return float(value.replace('%', '').strip()) / 100.0
        except ValueError:
            return 0.0
    return 0.0

def clean_seconds(value):
    if value == '--' or value == '---' or pd.isna(value):
        return 0
    if isinstance(value, str):
        try:
            minutes, seconds = value.split(':')
            return int(minutes) * 60 + int(seconds)
        except ValueError:
            return 0
    return 0

def calculate_total_time(row):
    """
    Calculate total fight time in seconds.
    Formule: (total_rounds - 1) * round_duration + last_round_time
    """

    try:
        round_num = int(row['end_round'])
        time_str = str(row['end_time'])
        
        minutes, seconds = map(int, time_str.split(':'))
        last_round_seconds = minutes * 60 + seconds
        rounds_completed_seconds = (round_num - 1) * 5 * 60
        
        return rounds_completed_seconds + last_round_seconds
    except:
        return 0

def clean_data():
    print("Loading dataset...")
    df = pd.read_csv(INPUT_FILE)

    if 'end_round' in df.columns and 'end_time' in df.columns:
        print("Calculating Total Fight Time...")
        df['total_time_seconds'] = df.apply(calculate_total_time, axis=1)

    print("Converting percentages...")
    pct_cols = ['f1_sig_pct', 'f2_sig_pct', 'f1_td_pct', 'f2_td_pct']
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_percentage)

    print("Exploding 'X of Y' columns...")
    strike_cols = ['f1_sig_str', 'f2_sig_str', 'f1_tot_str', 'f2_tot_str', 'f1_td', 'f2_td']
    
    for col in strike_cols:
        if col not in df.columns: continue

        df[col] = df[col].replace('---', '0 of 0')

        temp_df = df[col].str.split(' of ', expand=True)
        
        if temp_df.shape[1] == 2:
            df[f'{col}_landed'] = pd.to_numeric(temp_df[0], errors='coerce').fillna(0).astype(int)
            df[f'{col}_attempted'] = pd.to_numeric(temp_df[1], errors='coerce').fillna(0).astype(int)
        
        df.drop(columns=[col], inplace=True)

    print("Converting time...")
    time_cols = ['f1_ctrl', 'f2_ctrl']
    for col in time_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_seconds)

    if 'method' in df.columns:
        print("Cleaning text in Method column...")
        df['method'] = df['method'].str.replace(r'\s+', ' ', regex=True).str.strip()

    print(f"Saving cleaned file to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("\nPreview of cleaned method column:")
    print(df[['method', 'f1_ctrl']].head())

if __name__ == "__main__":
    clean_data()