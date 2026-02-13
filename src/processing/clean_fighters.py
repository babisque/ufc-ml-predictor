import pandas as pd
import numpy as np
import os
import re

INPUT_FILE = 'data/raw/fighter_details.csv'
OUTPUT_FILE = 'data/processed/clean_fighter_details.csv'

def clean_name(name_str):
    """
    Cleans the name by removing newlines and the text of Record.
    Ex: "Colby Covington \n Record: 17-3" -> "Colby Covington"
    """
    if pd.isna(name_str):
        return ""
    
    text = str(name_str).replace('\n', ' ')
    text = re.sub(r'Record:.*', '', text)    
    return " ".join(text.split())

def clean_height(height_str):
    """Converts 5' 10" to 178.0 cm"""
    if pd.isna(height_str) or height_str == '--':
        return np.nan
    try:
        clean_str = str(height_str).replace('"', '').strip()
        feet, inches = clean_str.split("'")
        return (int(feet) * 30.48) + (int(inches) * 2.54)
    except Exception:
        return np.nan

def clean_weight(weight_str):
    """Converts 155 lbs. to 70.3 kg"""
    if pd.isna(weight_str) or weight_str == '--':
        return np.nan
    try:
        lbs = float(weight_str.split()[0])
        return lbs * 0.453592
    except Exception:
        return np.nan

def clean_reach(reach_str):
    """Converts 70" to 178.0 cm"""
    if pd.isna(reach_str) or reach_str == '--':
        return np.nan
    try:
        inches = float(str(reach_str).replace('"', '').strip())
        return inches * 2.54
    except Exception:
        return np.nan

def parse_dob(dob_str):
    """Converts Jul 21, 1991 to datetime"""
    if pd.isna(dob_str) or dob_str == '--':
        return pd.NaT
    try:
        return pd.to_datetime(dob_str, format='%b %d, %Y', errors='coerce')
    except Exception:
        return pd.NaT

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File {INPUT_FILE} not found. Run the fighter scraper first.")
        return

    print("Loading raw fighter data...")
    df = pd.read_csv(INPUT_FILE)
    
    df.drop_duplicates(subset=['url'], keep='first', inplace=True)

    print("Cleaning Names...")
    df['name'] = df['name'].apply(clean_name)

    print("Cleaning Height...")
    df['height_cm'] = df['height'].apply(clean_height)

    print("Cleaning Weight...")
    df['weight_kg'] = df['weight'].apply(clean_weight)

    print("Cleaning Reach...")
    df['reach_cm'] = df['reach'].apply(clean_reach)

    print("Converting Date of Birth (DOB)...")
    df['dob'] = df['dob'].apply(parse_dob)

    if 'stance' in df.columns:
        df['stance'] = df['stance'].fillna('Orthodox').str.strip()

    cols_to_keep = ['name', 'url', 'height_cm', 'weight_kg', 'reach_cm', 'stance', 'dob']
    df_clean = df[cols_to_keep]

    print(f"Saving {len(df_clean)} cleaned fighters to {OUTPUT_FILE}...")
    
    os.makedirs('data/processed', exist_ok=True)
    df_clean.to_csv(OUTPUT_FILE, index=False)
    
    print("Sample of cleaned data:")
    print(df_clean.head())

if __name__ == "__main__":
    main()