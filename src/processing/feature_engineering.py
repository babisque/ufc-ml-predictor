import logging
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

class FeatureEngineer:
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.df = None

    def load_data(self):
        logging.info(f"Loading data from {self.input_path}")
        self.df = pd.read_csv(self.input_path)

    def _create_physical_differentials(self):
        if 'f1_age' in self.df.columns and 'f2_age' in self.df.columns:
            self.df['age_diff'] = self.df['f1_age'] - self.df['f2_age']
            
        if 'f1_reach' in self.df.columns and 'f2_reach' in self.df.columns:
            self.df['reach_diff'] = self.df['f1_reach'] - self.df['f2_reach']
            
        if 'f1_height' in self.df.columns and 'f2_height' in self.df.columns:
            self.df['height_diff'] = self.df['f1_height'] - self.df['f2_height']
            
        logging.info("Physical differentials created successfully.")

    def _create_temporal_and_streak_features(self):
        if 'event_date' in self.df.columns and 'f1_name' in self.df.columns and 'f2_name' in self.df.columns:
            logging.info("Calculating Ring Rust and Streaks for both fighters.")
            self.df['event_date'] = pd.to_datetime(self.df['event_date'])

            if 'target' in self.df.columns:
                f1_wins = (self.df['target'] == 0)
                f2_wins = (self.df['target'] == 1)
            elif 'winner' in self.df.columns:
                if set(self.df['winner'].dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                    f1_wins = (self.df['winner'] == 0)
                    f2_wins = (self.df['winner'] == 1)
                else:
                    f1_wins = (self.df['winner'] == self.df['f1_name'])
                    f2_wins = (self.df['winner'] == self.df['f2_name'])
            else:
                logging.warning("⚠️ None column indicating winner found. Assuming all fights are draws for streak calculation.")
                f1_wins = pd.Series(False, index=self.df.index)
                f2_wins = pd.Series(False, index=self.df.index)

            df_reset = self.df.reset_index()

            f1_df = df_reset[['index', 'event_date', 'f1_name']].rename(columns={'f1_name': 'fighter'})
            f1_df['pos'] = 'f1'
            f1_df['won'] = f1_wins

            f2_df = df_reset[['index', 'event_date', 'f2_name']].rename(columns={'f2_name': 'fighter'})
            f2_df['pos'] = 'f2'
            f2_df['won'] = f2_wins

            long_df = pd.concat([f1_df, f2_df]).sort_values(by=['fighter', 'event_date']).reset_index(drop=True)

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

            self.df['ring_rust_diff'] = self.df['f1_days_since_last'] - self.df['f2_days_since_last']
            self.df['win_streak_diff'] = self.df['f1_win_streak'] - self.df['f2_win_streak']
            self.df['loss_streak_diff'] = self.df['f1_loss_streak'] - self.df['f2_loss_streak']

            logging.info("Temporal and streak features created successfully.")

    def _create_striking_differentials(self):
        cols_lower = {c.lower(): c for c in self.df.columns}
        
        f1_slpm_col = cols_lower.get('f1_slpm')
        f1_sapm_col = cols_lower.get('f1_sapm')
        f2_slpm_col = cols_lower.get('f2_slpm')
        f2_sapm_col = cols_lower.get('f2_sapm')

        if all([f1_slpm_col, f1_sapm_col, f2_slpm_col, f2_sapm_col]):
            logging.info("Calculating striking differentials (SLpM and SApM).")
            self.df['f1_strike_diff'] = self.df[f1_slpm_col] - self.df[f1_sapm_col]
            self.df['f2_strike_diff'] = self.df[f2_slpm_col] - self.df[f2_sapm_col]
            self.df['strike_diff_advantage'] = self.df['f1_strike_diff'] - self.df['f2_strike_diff']
            logging.info("Strike Differential Advantage created successfully.")
        else:
            logging.warning("Columns SLpM and SApM not found. Skipping Strike Differential.")

    def save_data(self):
        self.df.to_csv(self.output_path, index=False)
        logging.info(f"Enriched dataset saved to: {self.output_path}")

    def run_pipeline(self):
        self.load_data()
        self._create_physical_differentials()
        self._create_temporal_and_streak_features()
        self._create_striking_differentials()
        self.save_data()

if __name__ == "__main__":
    data_path = str(Path("data/processed/balanced_fights.csv"))
    engineer = FeatureEngineer(data_path, data_path)
    engineer.run_pipeline()