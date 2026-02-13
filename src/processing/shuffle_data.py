import pandas as pd
import numpy as np
import os

INPUT_FILE = 'data/processed/merged_data.csv'
OUTPUT_FILE = 'data/processed/balanced_fights.csv'

def create_balanced_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File {INPUT_FILE} not found. Run merge_data.py first.")
        return

    print("Loading complete dataset...")
    df = pd.read_csv(INPUT_FILE)

    stat_cols = [c for c in df.columns if c.startswith('f1_') and 'name' not in c and 'link' not in c]
    base_stats = [c.replace('f1_', '') for c in stat_cols]

    bio_cols = ['height', 'weight', 'reach', 'stance', 'age']

    print(f"Standardizing Winner vs Loser stats...")
    
    mask_f1_winner = df['f1_name'] == df['winner']

    for stat in base_stats:
        df[f'winner_{stat}'] = np.where(mask_f1_winner, df[f'f1_{stat}'], df[f'f2_{stat}'])
        df[f'loser_{stat}']  = np.where(mask_f1_winner, df[f'f2_{stat}'], df[f'f1_{stat}'])

    map_a = {
        'winner_name': 'f1_name', 'loser_name': 'f2_name',
        'winner_link': 'f1_link', 'loser_link': 'f2_link',
    }
    for stat in base_stats:
        map_a[f'winner_{stat}'] = f'f1_{stat}'
        map_a[f'loser_{stat}'] = f'f2_{stat}'
    for bio in bio_cols:
        map_a[f'winner_{bio}'] = f'f1_{bio}'
        map_a[f'loser_{bio}'] = f'f2_{bio}'

    df_a = df.copy()
    df_a = df_a.rename(columns=map_a)
    df_a['target'] = 1

    map_b = {
        'loser_name': 'f1_name', 'winner_name': 'f2_name',
        'loser_link': 'f1_link', 'winner_link': 'f2_link',
    }
    for stat in base_stats:
        map_b[f'loser_{stat}'] = f'f1_{stat}'
        map_b[f'winner_{stat}'] = f'f2_{stat}'
    for bio in bio_cols:
        map_b[f'loser_{bio}'] = f'f1_{bio}'
        map_b[f'winner_{bio}'] = f'f2_{bio}'

    df_b = df.copy()
    df_b = df_b.rename(columns=map_b)
    df_b['target'] = 0

    print("Concatenating and shuffling...")
    
    cols_to_keep = [
        'f1_name', 'f2_name', 'f1_link', 'f2_link', 'target', 
        'weight_class', 'total_time_seconds', 'method_detail', 'referee', 'event_date'
    ]
    dynamic_cols = [c for c in df_a.columns if c.startswith('f1_') or c.startswith('f2_')]
    final_columns = list(set(cols_to_keep + dynamic_cols))
    
    final_columns = [c for c in final_columns if c in df_a.columns]

    df_final = pd.concat([df_a[final_columns], df_b[final_columns]], ignore_index=True)
    
    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"Total rows for training: {len(df_final)}")
    
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"Final file generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_balanced_dataset()