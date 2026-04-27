import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

def create_differentials(input_path: str, output_path: str):
    logging.info(f"Loading data from {input_path}")
    df = pd.read_csv(input_path)

    if 'f1_age' in df.columns and 'f2_age' in df.columns:
        df['age_diff'] = df['f1_age'] - df['f2_age']

    if 'f1_reach' in df.columns and 'f2_reach' in df.columns:
        df['reach_diff'] = df['f1_reach'] - df['f2_reach']

    if 'f1_height' in df.columns and 'f2_height' in df.columns:
        df['height_diff'] = df['f1_height'] - df['f2_height']

    logging.info("Fisical differentials created successfully.")

    if 'date' in df.columns and 'f1_name' in df.columns and 'f2_name' in df.columns:
        logging.info("Calculating the 'Ring Rust' (Days since last fight) for both fighters.")

        df['date'] = pd.to_datetime(df['date'])

        df_reset = df.reset_index()

        f1_df = df_reset[['index', 'date', 'f1_name']].rename(columns={'f1_name': 'fighter'})
        f1_df['pos'] = 'f1'
        
        f2_df = df_reset[['index', 'date', 'f2_name']].rename(columns={'f2_name': 'fighter'})
        f2_df['pos'] = 'f2'

        long_df = pd.concat([f1_df, f2_df]).sort_values(by=['fighter', 'date'])

        long_df['days_since_last_fight'] = long_df.groupby('fighter')['date'].diff().dt.days
        
        long_df['days_since_last_fight'] = long_df['days_since_last_fight'].fillna(180)
        
        f1_mapping = long_df[long_df['pos'] == 'f1'].set_index('index')['days_since_last_fight']
        f2_mapping = long_df[long_df['pos'] == 'f2'].set_index('index')['days_since_last_fight']
        
        df['f1_days_since_last'] = df_reset['index'].map(f1_mapping)
        df['f2_days_since_last'] = df_reset['index'].map(f2_mapping)
        
        df['ring_rust_diff'] = df['f1_days_since_last'] - df['f2_days_since_last']
        
        logging.info("Inativty differentials created successfully.")

        cols_lower = {c.lower(): c for c in df.columns}
    
    f1_slpm_col = cols_lower.get('f1_slpm')
    f1_sapm_col = cols_lower.get('f1_sapm')
    f2_slpm_col = cols_lower.get('f2_slpm')
    f2_sapm_col = cols_lower.get('f2_sapm')

    if all([f1_slpm_col, f1_sapm_col, f2_slpm_col, f2_sapm_col]):
        logging.info("Calculating striking differentials (SLpM and SApM).")
        
        df['f1_strike_diff'] = df[f1_slpm_col] - df[f1_sapm_col]
        df['f2_strike_diff'] = df[f2_slpm_col] - df[f2_sapm_col]
        
        df['strike_diff_advantage'] = df['f1_strike_diff'] - df['f2_strike_diff']
        logging.info("Strike Differential Advantage created successfully.")
    else:
        logging.warning("Columns SLpM and SApM not found. Please check the column names for striking stats in your merge_data.py.")

    df.to_csv(output_path, index=False)
    logging.info(f"Enriched dataset saved to: {output_path}")

if __name__ == "__main__":
    data_path = Path("data/processed/balanced_fights.csv")
    create_differentials(str(data_path), str(data_path))