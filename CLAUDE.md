# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Discord bot that predicts UFC fight outcomes using a Random Forest model trained on scraped ufcstats.com data. All commands below assume the repo root as the working directory (scripts use relative paths like `data/...` and `models/...`).

## Commands

```bash
pip install -r requirements.txt        # deps (pytest is NOT listed — `pip install pytest` separately to run tests)

python src/ml/pipeline.py              # full pipeline: scrape -> clean -> merge -> feature-engineer -> train
python src/ml/predict.py               # CLI smoke test of a single prediction (hardcoded fighters in __main__)
python -m src.bot.main                 # start the Discord bot (needs DISCORD_TOKEN in .env)
python scripts/auditor.py              # scrape latest results, mark pending predictions correct/incorrect, retrain if any updated

pytest                                 # run full test suite
pytest tests/test_processing/test_clean_data.py   # single file
pytest tests/test_processing/test_clean_data.py::test_clean_seconds -v  # single test

docker-compose up --build              # containerized run; entrypoint is start.sh, not the Dockerfile CMD
```

There's no pytest.ini/pyproject.toml — tests import `from src....` directly and rely on pytest being invoked from the repo root.

## Pipeline architecture

`src/ml/pipeline.py` runs the stages below in order, each a standalone script with an `if __name__ == "__main__"` entrypoint and hardcoded relative I/O paths (no shared path constants module):

1. **Scrape** (`src/scraper/events.py`, `fights.py`, `fighters.py`, `details.py`) — BeautifulSoup scraping of ufcstats.com → `data/raw/*.csv`. Fragile to markup changes; each `get_*` function targets specific CSS classes/table structures on ufcstats.com.
2. **Clean** (`src/processing/clean_data.py`, `clean_fighters.py`) → `data/processed/clean_fight_details.csv`, `clean_fighter_details.csv`.
3. **Merge** (`src/processing/merge_data.py`) — joins fight and fighter tables on `winner_link`/`loser_link` → URL, computes `winner_age`/`loser_age` at fight time → `data/processed/merged_data.csv`.
4. **Shuffle/balance** (`src/processing/shuffle_data.py`) — the critical step: each fight row is duplicated with fighters swapped between `f1_*`/`f2_*` slots (`target=1` when `f1_name` is the winner, `target=0` otherwise). This exists specifically so the model can't learn a "f1 always wins" positional bias → `data/processed/balanced_fights.csv`.
5. **Feature engineering** (`src/processing/feature_engineering.py`, `FeatureEngineer` class) — adds age/height/reach diffs, ring-rust/win-streak/loss-streak (via a long-format melt + groupby-shift), and SLpM/SApM strike differentials. Writes back to `data/processed/balanced_fights.csv` in place.
6. **Train** (`src/ml/train.py`) — drops "spoiler" columns (raw fight stats that wouldn't be known pre-fight, e.g. `sig_str_landed`, `td_landed`, `ctrl`) and identity columns, then fits a `RandomForestClassifier` → `models/ufc_random_forest.pkl`, `ufc_imputer.pkl`, `ufc_model_columns.pkl`.

**Gotcha:** `src/ml/train.py` has its *own* inline `feature_engineering()` function that duplicates step 5's logic with a narrower feature set (it also writes `data/processed/historical_df.csv`, which `start.sh` checks for). This is a second, divergent implementation from `src/processing/feature_engineering.py`'s `FeatureEngineer` class — when changing feature logic, check whether it needs to change in both places, since only `train.py`'s inline version is actually on the path that `pipeline.py` exercises when running `train.py`.

## Prediction path

`src/ml/predict.py`'s `get_fighter_profile()` looks up a fighter's *most recent* row in `balanced_fights.csv` (by `event_date`) and builds a feature vector by diffing the two fighters' profiles, then reindexes to the training columns (`ufc_model_columns.pkl`) before calling the model. This means predictions are only as fresh as the last successful pipeline run — there's no live/on-demand stat lookup.

## Discord bot (`src/bot/main.py`)

Commands (prefix `!`): `predict`, `nextEvent`, `lastEvent`, `profile`, `stats`. `nextEvent` scrapes the upcoming card, predicts every fight, and caches results in the DB keyed by event name (`get_event_predictions`) so repeat calls don't re-scrape/re-predict. A `tasks.loop` (`weekly_audit`) fires daily at `AUDIT_HOUR:AUDIT_MINUTE` but only acts on Sundays, calling `scripts/auditor.py`'s `audit_predictions()`.

## Auditing & retraining loop (`scripts/auditor.py`)

Scrapes the most recently completed event's actual results, fills in `actual_winner`/`is_correct` for pending DB rows, and — if anything was updated — fires `python -m src.ml.pipeline` as a detached subprocess to retrain on the new outcome data. This is the only automatic retraining trigger; there's no scheduled retrain independent of new confirmed results.

## Database (`src/db/`)

Raw `sqlite3` (no ORM), one `predictions` table. `save_prediction` dedupes on `(event_name, fighter_1, fighter_2)`. `event_name == 'Individual Fight'` marks ad-hoc `!predict` calls, which are excluded from audit queries and pending counts since there's no future event to audit them against.

**Gotcha:** `src/core/config.py`'s `Settings.DATABASE_URL` (default `sqlite:///ufc_predictions.db`) is not what's actually used for connections — `src/db/connection.py` reads its own `DATABASE_URL` env var independently with a different default (`data/ufc_predictions.db`) and treats it as a raw file path, not a SQLAlchemy-style URL. `scripts/auditor.py` also hardcodes its own `DB_PATH = "data/ufc_predictions.db"` rather than importing from either.

## Data column conventions

- `f1_*` / `f2_*` prefixes denote "fighter in slot 1/2" for a given row — not literal winner/loser (see shuffle step above).
- `winner_*` / `loser_*` prefixes appear only in `merged_data.csv`, before the shuffle step converts them to `f1_*`/`f2_*` + `target`.
- Weight class and stance are one-hot encoded during feature engineering/training (`weight_class_*`, `f1_stance_*`/`f2_stance_*`); `predict.py` sets `weight_col = f'weight_class_{weight_class}'` directly on the prediction row, so the string passed to `!predict` must match a weight class value seen during training.
