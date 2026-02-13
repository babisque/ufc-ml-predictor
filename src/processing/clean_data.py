import pandas as pd
import numpy as np
import re
import os

INPUT_FILE = 'data/raw/fight_details.csv'
OUTPUT_FILE = 'data/processed/clean_fight_details.csv'

def clean_text_nuclear(text):
    """
    Remove any line breaks (\n, \r) and extra spaces.
    Transform: "Herb Dean \n \n   " to "Herb Dean"
    Transform: "SUB \n Rear Naked Choke" to "SUB Rear Naked Choke"
    """
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    text = text.replace('\n', ' ').replace('\r', ' ')
    
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def clean_seconds(value):
    """Convert '4:31' to 271 seconds"""
    if pd.isna(value) or str(value).strip() in ['--', '---']:
        return 0
    try:
        val_str = str(value).strip()
        if ':' in val_str:
            parts = val_str.split(':')
            return int(parts[0]) * 60 + int(parts[1])
        return int(float(val_str))
    except:
        return 0

def split_stats(val):
    """Split '31 of 55' into (31, 55)"""
    val_str = str(val).strip()
    if pd.isna(val) or val_str in ['---', '--'] or 'of' not in val_str:
        return 0, 0
    try:
        landed, attempted = val_str.split(' of ')
        return int(landed), int(attempted)
    except:
        return 0, 0

def clean_percentage(val):
    """Convert '55%' to 0.55"""
    val_str = str(val).strip()
    if '%' in val_str:
        try:
            return float(val_str.replace('%', '')) / 100.0
        except:
            return 0.0
    return 0.0

def clean_data():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File {INPUT_FILE} not found!")
        return

    print("Loading dataset...")
    df = pd.read_csv(INPUT_FILE)

    df = df.loc[:, ~df.columns.duplicated()]

    print("Applying nuclear cleaning to all text columns...")
    str_cols = df.select_dtypes(include=['object']).columns
    
    for col in str_cols:
        df[col] = df[col].apply(clean_text_nuclear)

    print("Converting percentages...")
    pct_cols = ['f1_sig_pct', 'f2_sig_pct', 'f1_td_pct', 'f2_td_pct']
    for col in pct_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_percentage)

    print("Splitting stats (X of Y)...")
    cols_to_split = [
        'f1_sig_str', 'f2_sig_str', 
        'f1_tot_str', 'f2_tot_str', 
        'f1_td', 'f2_td'
    ]

    for col in cols_to_split:
        if col in df.columns:
            new_data = df[col].apply(split_stats)
            df[f'{col}_landed'] = new_data.apply(lambda x: x[0])
            df[f'{col}_attempted'] = new_data.apply(lambda x: x[1])
            df.drop(columns=[col], inplace=True)

    print("Converting times...")
    time_cols = ['f1_ctrl', 'f2_ctrl']
    for col in time_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_seconds)

    if 'end_round' in df.columns and 'end_time' in df.columns:
        def calc_total_time(row):
            try:
                r_val = str(row['end_round']).strip()
                if not r_val.isdigit(): return 0
                
                r = int(r_val)
                last_r_seconds = clean_seconds(row['end_time'])
                
                return ((r - 1) * 300) + last_r_seconds
            except:
                return 0
        df['total_time_seconds'] = df.apply(calc_total_time, axis=1)

    print(f"Saving cleaned dataset to {OUTPUT_FILE}...")
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("\nPreview of cleaned text columns:")
    print(df[['event_name', 'method', 'method_detail']].head(3))

if __name__ == "__main__":
    clean_data()