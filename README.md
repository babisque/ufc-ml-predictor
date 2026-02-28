# UFC ML Predictor

Machine learning + scraping pipeline to predict UFC fight outcomes and serve predictions through a Discord bot.

## Overview

This project:

- Scrapes UFC event, fight, fighter, and fight-detail data
- Cleans and merges data into training-ready datasets
- Trains a Random Forest model
- Saves model artifacts for inference
- Exposes predictions via CLI and Discord bot
- Stores predictions/results in SQLite for auditing and stats

## Repository Structure

- `src/scraper/` → data collection scripts
- `src/processing/` → cleaning/merging/balancing scripts
- `train.py` → feature engineering + model training
- `predict.py` → inference helpers and CLI prediction
- `bot.py` → Discord commands (`predict`, `nextEvent`, `stats`, `lastEvent`, `profile`)
- `database.py` → SQLite storage for predictions
- `auditor.py` → updates pending predictions with real results
- `pipeline.py` → end-to-end MLOps pipeline runner

## Data Flow

1. **Scraping**
   - Events → `data/raw/all_events.csv`
   - Fights → `data/raw/all_fights.csv`
   - Fighters → `data/raw/fighter_details.csv`
   - Fight stats/details → `data/raw/fight_details.csv`

2. **Processing**
   - Clean fights → `data/processed/clean_fight_details.csv`
   - Clean fighters → `data/processed/clean_fighter_details.csv`
   - Merge → `data/processed/merged_data.csv`
   - Balance/shuffle → `data/processed/balanced_fights.csv`

3. **Training**
   - Feature engineering output → `data/processed/historical_df.csv`
   - Model artifacts:
     - `models/ufc_random_forest.pkl`
     - `models/ufc_imputer.pkl`
     - `models/ufc_model_columns.pkl`

## Requirements

- Python 3.10+ (Dockerfile uses Python 3.13 slim)
- pip
- Discord bot token (for bot usage)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1) Run full pipeline

```bash
python pipeline.py
```

This executes:

- `src/scraper/events.py`
- `src/scraper/fights.py`
- `src/scraper/fighters.py`
- `src/scraper/details.py`
- `src/processing/clean_data.py`
- `src/processing/clean_fighters.py`
- `src/processing/merge_data.py`
- `src/processing/shuffle_data.py`
- `train.py`

### 2) Run a local prediction (CLI)

Edit fighters in `predict.py` or keep defaults, then:

```bash
python predict.py
```

### 3) Run Discord bot

Create `.env` with:

```env
DISCORD_TOKEN=your_token_here
```

Then run:

```bash
python bot.py
```

## Bot Commands

- `!predict <Fighter 1> , <Fighter 2> , <Weight Class>`
- `!nextEvent`
- `!stats`
- `!lastEvent`
- `!profile <Fighter Name>`

## Database & Auditing

- DB path: `data/ufc_predictions.db`
- Initialize manually (optional):
  ```bash
  python database.py
  ```
- Audit pending predictions (and auto-trigger pipeline on updates):
  ```bash
  python auditor.py
  ```

## Docker

Build and run:

```bash
docker compose up --build
```

Or directly with Dockerfile:

```bash
docker build -t ufc-ml-predictor .
docker run --rm --env-file .env ufc-ml-predictor
```

## Notes

- First full pipeline run may take time due to scraping.
- Scrapers support resume behavior when output files already exist.
- Prediction quality depends on historical data freshness and data completeness.
