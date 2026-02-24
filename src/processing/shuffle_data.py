import pandas as pd
import numpy as np
import os

INPUT_FILE = 'data/processed/merged_data.csv'
OUTPUT_FILE = 'data/processed/balanced_fights.csv'

def create_balanced_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: file {INPUT_FILE} not found. Please run the data processing steps first.")
        return

    print("Loading entire dataset...")
    df = pd.read_csv(INPUT_FILE)

    stat_cols = [c for c in df.columns if c.startswith('f1_') and 'name' not in c and 'link' not in c and 'id' not in c]
    base_stats = [c.replace('f1_', '') for c in stat_cols]

    bio_cols = ['height', 'weight', 'reach', 'stance', 'age']

    print("Standardizing stats for Winner vs Loser...")
    
    mask_f1_winner = df['f1_name'] == df['winner']

    for stat in base_stats:
        df[f'winner_{stat}'] = np.where(mask_f1_winner, df[f'f1_{stat}'], df[f'f2_{stat}'])
        df[f'loser_{stat}']  = np.where(mask_f1_winner, df[f'f2_{stat}'], df[f'f1_{stat}'])

    df_a = df.copy()
    
    cols_to_drop = [f'f1_{s}' for s in base_stats] + [f'f2_{s}' for s in base_stats]
    cols_to_drop += ['f1_name', 'f2_name', 'f1_link', 'f2_link']
    cols_to_drop = [c for c in cols_to_drop if c in df_a.columns]
    df_a.drop(columns=cols_to_drop, inplace=True)

    map_a = {
        'winner': 'f1_name', 'loser': 'f2_name',
        'winner_link': 'f1_link', 'loser_link': 'f2_link',
    }
    
    for stat in base_stats:
        map_a[f'winner_{stat}'] = f'f1_{stat}'
        map_a[f'loser_{stat}'] = f'f2_{stat}'
    for bio in bio_cols:
        map_a[f'winner_{bio}'] = f'f1_{bio}'
        map_a[f'loser_{bio}'] = f'f2_{bio}'

    df_a = df_a.rename(columns=map_a)
    df_a['target'] = 1

    df_b = df.copy()
    
    df_b.drop(columns=cols_to_drop, inplace=True)

    map_b = {
        'loser': 'f1_name', 'winner': 'f2_name',
        'loser_link': 'f1_link', 'winner_link': 'f2_link',
    }

    for stat in base_stats:
        map_b[f'loser_{stat}'] = f'f1_{stat}'
        map_b[f'winner_{stat}'] = f'f2_{stat}'
    for bio in bio_cols:
        map_b[f'loser_{bio}'] = f'f1_{bio}'
        map_b[f'winner_{bio}'] = f'f2_{bio}'

    df_b = df_b.rename(columns=map_b)
    df_b['target'] = 0

    print("Concatenating and removing excess columns...")
    
    df_final = pd.concat([df_a, df_b], ignore_index=True)
    
    keep_cols = [
        'f1_name', 'f2_name', 'f1_link', 'f2_link', 'target', 
        'weight_class', 'total_time_seconds', 'method_detail', 'referee', 'event_date'
    ]
    
    stats_final = [c for c in df_final.columns if c.startswith('f1_') or c.startswith('f2_')]
    
    final_cols_list = list(set(keep_cols + stats_final))
    
    final_cols_list = [c for c in final_cols_list if c in df_final.columns]
    
    df_final = df_final[final_cols_list]

    df_final = df_final.loc[:, ~df_final.columns.duplicated()]

    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"Total rows for training: {len(df_final)}")
    print(f"Final column ({len(df_final.columns)}): {list(df_final.columns[:5])}...")
    
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"File saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_balanced_dataset()