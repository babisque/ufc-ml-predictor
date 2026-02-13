import pandas as pd
import numpy as np
import os

INPUT_FILE = 'data/processed/clean_fight_details.csv'
OUTPUT_FILE = 'data/processed/balanced_fights.csv'

def create_balanced_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: File {INPUT_FILE} not found.")
        return

    print("Loading clean dataset...")
    df = pd.read_csv(INPUT_FILE)

    df_winner = df.copy()
    df_winner['target'] = 1
    
    df_winner.rename(columns={'winner': 'f1', 'loser': 'f2'}, inplace=True)

    print("Creating mirror dataset (Data Augmentation)...")
    df_loser = df.copy()
    new_column_names = {}
    
    for col in df.columns:
        if col.startswith('f1_'):
            new_column_names[col] = col.replace('f1_', 'f2_')
        elif col.startswith('f2_'):
            new_column_names[col] = col.replace('f2_', 'f1_')
        elif col == 'winner':
            new_column_names[col] = 'f2'
        elif col == 'loser':
            new_column_names[col] = 'f1'
        else:
            new_column_names[col] = col

    df_loser.rename(columns=new_column_names, inplace=True)
    df_loser['target'] = 0

    print("Concatenating and shuffling...")
    df_final = pd.concat([df_winner, df_loser], ignore_index=True)
    
    cols = ['f1', 'f2', 'target'] + [c for c in df_final.columns if c not in ['f1', 'f2', 'target']]
    df_final = df_final[cols]

    df_final = df_final.sample(frac=1, random_state=42).reset_index(drop=True)

    print("-" * 30)
    print(f"Total: {len(df_final)} rows")
    print(f"Renamed columns: {list(df_final.columns[:5])}...")
    print(f"Target distribution: \n{df_final['target'].value_counts(normalize=True)}")
    print("-" * 30)

    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"File saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    create_balanced_dataset()