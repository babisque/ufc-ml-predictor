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

```text
.
├── .dockerignore
├── .env
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── README.md
├── requirements.txt
├── structure.md
├── data/
│   ├── raw/
│   │   ├── all_events.csv
│   │   ├── all_fights.csv
│   │   ├── fight_details.csv
│   │   └── fighter_details.csv
│   ├── processed/
│   │   ├── balanced_fights.csv
│   │   ├── clean_fight_details.csv
│   │   ├── clean_fighter_details.csv
│   │   ├── historical_df.csv
│   │   └── merged_data.csv
│   └── ufc_predictions.db
├── models/
├── notebooks/
│   └── 01_exploratory_analysis.ipynb
├── scripts/
│   ├── auditor.py
│   └── run_scraper.py
├── src/
│   ├── api/
│   ├── bot/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logger.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── predict.py
│   │   └── train.py
│   ├── processing/
│   │   ├── clean_data.py
│   │   ├── clean_fighters.py
│   │   ├── merge_data.py
│   │   └── shuffle_data.py
│   └── scraper/
│       ├── details.py
│       ├── events.py
│       ├── fighters.py
│       └── fights.py
└── tests/
  ├── test_bot/
  ├── test_ml/
  └── test_scraper/
```

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
python src/ml/pipeline.py
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
- `src/ml/train.py`

### 2) Run a local prediction (CLI)

Edit fighters in `src/ml/predict.py` or keep defaults, then:

```bash
python src/ml/predict.py
```

### 3) Run Discord bot

Create `.env` with:

```env
DISCORD_TOKEN=your_token_here
```

Then run:

```bash
python src/bot/main.py
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
  python src/db/models.py
  ```
- Audit pending predictions (and auto-trigger pipeline on updates):
  ```bash
  python scripts/auditor.py
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
