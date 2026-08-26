import logging
import pandas as pd
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

INPUT_FILE = 'data/processed/balanced_fights.csv'
OUTPUT_FILE = 'data/processed/balanced_fights.csv'

def create_pairwise_features():
    """
    Computes f1-vs-f2 comparison features and one-hot encodes categorical columns.
    Must run AFTER shuffle_data.py, since f1_/f2_ are only meaningful (winner/loser
    correctly split into both mirrored rows) once shuffling has happened.
    """
    if not os.path.exists(INPUT_FILE):
        logging.error(f"File {INPUT_FILE} not found. Run shuffle_data.py first.")
        return

    logging.info(f"Loading data from {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)

    logging.info("Calculating physical and temporal differentials.")
    if 'f1_age' in df.columns and 'f2_age' in df.columns:
        df['age_diff'] = df['f1_age'] - df['f2_age']
    if 'f1_reach' in df.columns and 'f2_reach' in df.columns:
        df['reach_diff'] = df['f1_reach'] - df['f2_reach']
    if 'f1_height' in df.columns and 'f2_height' in df.columns:
        df['height_diff'] = df['f1_height'] - df['f2_height']

    if 'f1_days_since_last' in df.columns and 'f2_days_since_last' in df.columns:
        df['ring_rust_diff'] = df['f1_days_since_last'] - df['f2_days_since_last']
    if 'f1_win_streak' in df.columns and 'f2_win_streak' in df.columns:
        df['win_streak_diff'] = df['f1_win_streak'] - df['f2_win_streak']
    if 'f1_loss_streak' in df.columns and 'f2_loss_streak' in df.columns:
        df['loss_streak_diff'] = df['f1_loss_streak'] - df['f2_loss_streak']

    logging.info("Calculating career-history differentials (Elo, finish rate, duration, experience).")
    if 'f1_elo' in df.columns and 'f2_elo' in df.columns:
        df['elo_diff'] = df['f1_elo'] - df['f2_elo']
    if 'f1_ko_rate' in df.columns and 'f2_ko_rate' in df.columns:
        df['ko_rate_diff'] = df['f1_ko_rate'] - df['f2_ko_rate']
    if 'f1_sub_rate' in df.columns and 'f2_sub_rate' in df.columns:
        df['sub_rate_diff'] = df['f1_sub_rate'] - df['f2_sub_rate']
    if 'f1_dec_rate' in df.columns and 'f2_dec_rate' in df.columns:
        df['dec_rate_diff'] = df['f1_dec_rate'] - df['f2_dec_rate']
    if 'f1_avg_fight_time' in df.columns and 'f2_avg_fight_time' in df.columns:
        df['avg_fight_time_diff'] = df['f1_avg_fight_time'] - df['f2_avg_fight_time']
    if 'f1_num_prior_fights' in df.columns and 'f2_num_prior_fights' in df.columns:
        df['num_prior_fights_diff'] = df['f1_num_prior_fights'] - df['f2_num_prior_fights']
    if 'f1_strike_diff' in df.columns and 'f2_strike_diff' in df.columns:
        df['strike_diff_advantage'] = df['f1_strike_diff'] - df['f2_strike_diff']

    logging.info("Encoding weight_class and stance.")
    encoding_columns = [c for c in ['weight_class', 'f1_stance', 'f2_stance'] if c in df.columns]
    df = pd.get_dummies(df, columns=encoding_columns, drop_first=True)

    logging.info(f"Saving enriched dataset to {OUTPUT_FILE}")
    df.to_csv(OUTPUT_FILE, index=False)

if __name__ == "__main__":
    create_pairwise_features()
