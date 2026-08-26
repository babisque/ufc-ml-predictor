import logging
import numpy as np
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

STAT_COLS = ['kd', 'sig_str_landed', 'td_landed', 'ctrl', 'sig_pct']

def categorize_method(method_str):
    """Normalize the raw scraped 'method' string (e.g. 'KO/TKO Punches', 'U-DEC',
    'SUB Rear Naked Choke') into a coarse KO / SUB / DEC / OTHER bucket."""
    if pd.isna(method_str):
        return 'OTHER'
    m = str(method_str).strip().upper()
    if m.startswith('KO/TKO'):
        return 'KO'
    if m.startswith('SUB'):
        return 'SUB'
    if m.endswith('DEC'):
        return 'DEC'
    return 'OTHER'

class FeatureEngineer:
    """
    Computes per-fighter career-history features. Must run on merged_data.csv
    (one row per real fight) BEFORE shuffle_data.py duplicates each fight into
    two mirrored rows -- running this after shuffling would count every real
    fight twice per fighter and corrupt streaks/ring-rust/every other history feature.

    Note: on merged_data.csv, a fighter's f1-vs-f2 slot for a given fight is
    arbitrary scrape order (not winner/loser-based), so a fighter's real career
    history is split unpredictably across the f1_name and f2_name columns. Every
    method below melts f1_name/f2_name together into one per-fighter chronological
    sequence before computing anything trailing -- grouping by 'f1_name' alone
    would only see the arbitrary subset of a fighter's fights where they were
    scraped as f1, not their full history.
    """

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.df = None

    def load_data(self):
        logging.info(f"Loading data from {self.input_path}")
        self.df = pd.read_csv(self.input_path)

    def _infer_win_indicators(self):
        """Returns (f1_wins, f2_wins) boolean Series from whichever outcome column is present."""
        if 'winner' in self.df.columns:
            if set(self.df['winner'].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                f1_wins = (self.df['winner'] == 0)
                f2_wins = (self.df['winner'] == 1)
            else:
                f1_wins = (self.df['winner'] == self.df['f1_name'])
                f2_wins = (self.df['winner'] == self.df['f2_name'])
        elif 'target' in self.df.columns:
            # target == 1 means f1_name is the winner (see shuffle_data.py's df_a/df_b convention).
            f1_wins = (self.df['target'] == 1)
            f2_wins = (self.df['target'] == 0)
        else:
            logging.warning("No column indicating winner found. Assuming all fights are draws for streak calculation.")
            f1_wins = pd.Series(False, index=self.df.index)
            f2_wins = pd.Series(False, index=self.df.index)
        return f1_wins, f2_wins

    def _create_temporal_and_streak_features(self):
        if 'event_date' in self.df.columns and 'f1_name' in self.df.columns and 'f2_name' in self.df.columns:
            logging.info("Calculating Ring Rust and Streaks for both fighters.")
            self.df['event_date'] = pd.to_datetime(self.df['event_date'])

            f1_wins, f2_wins = self._infer_win_indicators()

            df_reset = self.df.reset_index()

            f1_df = df_reset[['index', 'event_date', 'f1_name']].rename(columns={'f1_name': 'fighter'})
            f1_df['pos'] = 'f1'
            f1_df['won'] = f1_wins

            f2_df = df_reset[['index', 'event_date', 'f2_name']].rename(columns={'f2_name': 'fighter'})
            f2_df['pos'] = 'f2'
            f2_df['won'] = f2_wins

            long_df = pd.concat([f1_df, f2_df]).sort_values(by=['fighter', 'event_date'], kind='mergesort').reset_index(drop=True)

            long_df['days_since_last_fight'] = long_df.groupby('fighter')['event_date'].diff().dt.days
            long_df['days_since_last_fight'] = long_df['days_since_last_fight'].fillna(180)

            long_df['prev_won'] = long_df.groupby('fighter')['won'].shift(1)
            long_df['block'] = (long_df['prev_won'] != long_df.groupby('fighter')['prev_won'].shift(1)).cumsum()
            long_df['streak_length'] = long_df.groupby(['fighter', 'block']).cumcount() + 1
            long_df.loc[long_df['prev_won'].isna(), 'streak_length'] = 0

            long_df['win_streak'] = 0
            long_df['loss_streak'] = 0

            long_df.loc[long_df['prev_won'] == True, 'win_streak'] = long_df['streak_length']
            long_df.loc[long_df['prev_won'] == False, 'loss_streak'] = long_df['streak_length']

            for pos in ['f1', 'f2']:
                mask = long_df['pos'] == pos
                self.df[f'{pos}_days_since_last'] = df_reset['index'].map(long_df[mask].set_index('index')['days_since_last_fight'])
                self.df[f'{pos}_win_streak'] = df_reset['index'].map(long_df[mask].set_index('index')['win_streak']).fillna(0)
                self.df[f'{pos}_loss_streak'] = df_reset['index'].map(long_df[mask].set_index('index')['loss_streak']).fillna(0)

            logging.info("Temporal and streak features created successfully.")

    def _create_elo_features(self, k_factor=32.0, start_rating=1500.0):
        """Standard Elo rating (K=32, start=1500), one chronological pass across each
        fighter's whole career. f1_elo/f2_elo record the PRE-fight rating (knowable
        ahead of a future matchup), then the rating is updated by this fight's result."""
        if not {'f1_name', 'f2_name', 'event_date'}.issubset(self.df.columns):
            return

        logging.info("Calculating Elo ratings.")
        f1_wins, _ = self._infer_win_indicators()

        order = self.df.sort_values('event_date', kind='mergesort').index.to_numpy()
        f1_names = self.df['f1_name'].to_numpy()
        f2_names = self.df['f2_name'].to_numpy()
        f1_won_arr = f1_wins.to_numpy()

        ratings = {}
        f1_elo = np.empty(len(self.df))
        f2_elo = np.empty(len(self.df))

        for idx in order:
            n1, n2 = f1_names[idx], f2_names[idx]
            r1 = ratings.get(n1, start_rating)
            r2 = ratings.get(n2, start_rating)

            f1_elo[idx] = r1
            f2_elo[idx] = r2

            expected1 = 1.0 / (1.0 + 10 ** ((r2 - r1) / 400.0))
            actual1 = 1.0 if f1_won_arr[idx] else 0.0

            ratings[n1] = r1 + k_factor * (actual1 - expected1)
            ratings[n2] = r2 + k_factor * ((1.0 - actual1) - (1.0 - expected1))

        self.df['f1_elo'] = f1_elo
        self.df['f2_elo'] = f2_elo
        logging.info("Elo ratings created successfully.")

    def _create_career_history_features(self):
        """Finish-method rates (over wins only), trailing average fight duration,
        prior-fight count/debut flag, trailing stat averages, and trailing strike
        rate -- all computed leak-safe (shift(1) before any aggregation) over one
        unified per-fighter chronological history."""
        if not {'event_date', 'f1_name', 'f2_name'}.issubset(self.df.columns):
            return

        logging.info("Calculating finish-rate, duration, prior-fights, and stat-history features.")

        f1_wins, f2_wins = self._infer_win_indicators()
        method_category = (self.df['method'].apply(categorize_method)
                            if 'method' in self.df.columns
                            else pd.Series('OTHER', index=self.df.index))
        duration = (self.df['total_time_seconds'] if 'total_time_seconds' in self.df.columns
                    else pd.Series(np.nan, index=self.df.index))

        have_stats = all(f'{p}_{c}' in self.df.columns for p in ['f1', 'f2'] for c in STAT_COLS)

        df_reset = self.df.reset_index()

        def build_side(prefix, opp_prefix, won):
            data = {
                'orig_index': df_reset['index'],
                'event_date': df_reset['event_date'],
                'fighter': df_reset[f'{prefix}_name'],
                'won': won.to_numpy(),
                'method_category': method_category.to_numpy(),
                'duration': duration.to_numpy(),
            }
            if have_stats:
                for c in STAT_COLS:
                    data[c] = df_reset[f'{prefix}_{c}']
                data['sig_str_landed_against'] = df_reset[f'{opp_prefix}_sig_str_landed']
            side = pd.DataFrame(data)
            side['pos'] = prefix
            return side

        long_df = pd.concat([
            build_side('f1', 'f2', f1_wins),
            build_side('f2', 'f1', f2_wins),
        ], ignore_index=True)
        long_df = long_df.sort_values(by=['fighter', 'event_date'], kind='mergesort').reset_index(drop=True)

        long_df['is_ko_win'] = long_df['won'] & (long_df['method_category'] == 'KO')
        long_df['is_sub_win'] = long_df['won'] & (long_df['method_category'] == 'SUB')
        long_df['is_dec_win'] = long_df['won'] & (long_df['method_category'] == 'DEC')

        grouped_fighter = long_df.groupby('fighter')

        long_df['won_prior'] = grouped_fighter['won'].shift(1).fillna(False).astype(int)
        long_df['ko_win_prior'] = grouped_fighter['is_ko_win'].shift(1).fillna(False).astype(int)
        long_df['sub_win_prior'] = grouped_fighter['is_sub_win'].shift(1).fillna(False).astype(int)
        long_df['dec_win_prior'] = grouped_fighter['is_dec_win'].shift(1).fillna(False).astype(int)

        long_df['cum_wins_prior'] = long_df.groupby('fighter')['won_prior'].cumsum()
        long_df['cum_ko_prior'] = long_df.groupby('fighter')['ko_win_prior'].cumsum()
        long_df['cum_sub_prior'] = long_df.groupby('fighter')['sub_win_prior'].cumsum()
        long_df['cum_dec_prior'] = long_df.groupby('fighter')['dec_win_prior'].cumsum()

        has_prior_wins = long_df['cum_wins_prior'] > 0
        long_df['ko_rate'] = (long_df['cum_ko_prior'] / long_df['cum_wins_prior']).where(has_prior_wins, 0.0)
        long_df['sub_rate'] = (long_df['cum_sub_prior'] / long_df['cum_wins_prior']).where(has_prior_wins, 0.0)
        long_df['dec_rate'] = (long_df['cum_dec_prior'] / long_df['cum_wins_prior']).where(has_prior_wins, 0.0)

        long_df['avg_fight_time'] = long_df.groupby('fighter')['duration'].transform(lambda s: s.shift(1).expanding().mean())
        long_df['num_prior_fights'] = long_df.groupby('fighter').cumcount()

        if have_stats:
            for c in STAT_COLS:
                long_df[f'{c}_hist_avg'] = long_df.groupby('fighter')[c].transform(lambda s: s.shift(1).expanding().mean())

            minutes_for = long_df.groupby('fighter')['duration'].transform(lambda s: s.shift(1).expanding().sum()) / 60.0
            strikes_for = long_df.groupby('fighter')['sig_str_landed'].transform(lambda s: s.shift(1).expanding().sum())
            strikes_against = long_df.groupby('fighter')['sig_str_landed_against'].transform(lambda s: s.shift(1).expanding().sum())

            has_minutes = minutes_for > 0
            long_df['slpm_hist'] = (strikes_for / minutes_for).where(has_minutes, 0.0)
            long_df['sapm_hist'] = (strikes_against / minutes_for).where(has_minutes, 0.0)
            long_df['strike_diff'] = long_df['slpm_hist'] - long_df['sapm_hist']

        for pos in ['f1', 'f2']:
            sub = long_df[long_df['pos'] == pos].set_index('orig_index')

            self.df[f'{pos}_ko_rate'] = df_reset['index'].map(sub['ko_rate']).fillna(0.0)
            self.df[f'{pos}_sub_rate'] = df_reset['index'].map(sub['sub_rate']).fillna(0.0)
            self.df[f'{pos}_dec_rate'] = df_reset['index'].map(sub['dec_rate']).fillna(0.0)
            self.df[f'{pos}_avg_fight_time'] = df_reset['index'].map(sub['avg_fight_time'])
            self.df[f'{pos}_num_prior_fights'] = df_reset['index'].map(sub['num_prior_fights']).fillna(0).astype(int)
            self.df[f'{pos}_is_debut'] = self.df[f'{pos}_num_prior_fights'] == 0

            if have_stats:
                for c in STAT_COLS:
                    self.df[f'{pos}_{c}_hist_avg'] = df_reset['index'].map(sub[f'{c}_hist_avg']).fillna(0.0)
                self.df[f'{pos}_slpm_hist'] = df_reset['index'].map(sub['slpm_hist']).fillna(0.0)
                self.df[f'{pos}_sapm_hist'] = df_reset['index'].map(sub['sapm_hist']).fillna(0.0)
                self.df[f'{pos}_strike_diff'] = df_reset['index'].map(sub['strike_diff']).fillna(0.0)

        logging.info("Career history features created successfully.")

    def save_data(self):
        self.df.to_csv(self.output_path, index=False)
        logging.info(f"Enriched dataset saved to: {self.output_path}")

    def run_pipeline(self):
        self.load_data()
        self._create_temporal_and_streak_features()
        self._create_elo_features()
        self._create_career_history_features()
        self.save_data()

if __name__ == "__main__":
    data_path = str(Path("data/processed/merged_data.csv"))
    engineer = FeatureEngineer(data_path, data_path)
    engineer.run_pipeline()
