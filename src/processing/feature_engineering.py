import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')

def create_differentials(input_path: str, output_path: str):
    logging.info(f"Loading data from {input_path}")
    df = pd.read_csv(input_path)

    if 'f1_age' in df.columns and 'f2_age' in df.columns:
        df['age_diff'] = df['f1_age'] - df['f2_age']
        logging.info("Feature 'age_diff' created")

    if 'f1_reach' in df.columns and 'f2_reach' in df.columns:
        df['reach_diff'] = df['f1_reach'] - df['f2_reach']
        logging.info("Feature 'reach_diff' created")

    if 'f1_height' in df.columns and 'f2_height' in df.columns:
        df['height_diff'] = df['f1_height'] - df['f2_height']
        logging.info("Feature 'height_diff' created")

    df.to_csv(output_path, index=False)
    logging.info(f"Dataset enriquecido guardado em: {output_path}")

if __name__ == "__main__":
    data_path = Path("data/processed/balanced_fights.csv")
    create_differentials(str(data_path), str(data_path))