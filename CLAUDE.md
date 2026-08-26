# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Discord bot that predicts UFC fight outcomes using a Random Forest model trained on scraped ufcstats.com data. All commands below assume the repo root as the working directory (scripts use relative paths like `data/...` and `models/...`).

## Commands

```bash
pip install -r requirements.txt        # deps (pytest is NOT listed — `pip install pytest` separately to run tests)

python src/ml/pipeline.py              # full pipeline: scrape -> clean -> merge -> feature-engineer (pre-shuffle) -> shuffle -> pairwise-features (post-shuffle) -> train
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
2. **Clean** (`src/processing/clean_data.py`, `clean_fighters.py`) → `data/processed/clean_fight_details.csv`, `clean_fighter_details.csv`. `clean_data.py` also drops fights with no genuine winner/loser (`method` is `CNC` or contains `Overturned`) via `filter_invalid_outcomes` — `DQ` is kept since it has a real winner. Unparseable/missing stat values become `NaN` (not `0`), so `SimpleImputer` in `train.py` can actually impute them.
3. **Merge** (`src/processing/merge_data.py`) — joins fight and fighter tables on `winner_link`/`loser_link` → URL, computes `winner_age`/`loser_age` at fight time → `data/processed/merged_data.csv` (one row per real fight; `f1_name`/`f2_name` are arbitrary scrape-order identities, not winner/loser).
4. **Feature engineering, pre-shuffle** (`src/processing/feature_engineering.py`, `FeatureEngineer` class) — runs on `merged_data.csv` **before** shuffling, in place. Every per-fighter career-history feature lives here and is computed leak-safe (`shift(1)` before any aggregation/expanding window) over a melted `f1_name`+`f2_name` long-format history, since on `merged_data.csv` a fighter's f1-vs-f2 slot per fight is arbitrary, not a complete mirrored split — grouping by `f1_name` alone would only see a subset of a fighter's real history. Produces: `f{1,2}_days_since_last`/`win_streak`/`loss_streak` (ring-rust/streaks), `f{1,2}_elo` (standard Elo, K=32, start=1500, one chronological pass — pre-fight rating only), `f{1,2}_ko_rate`/`sub_rate`/`dec_rate` (finish-method rate over wins only, via `categorize_method`), `f{1,2}_avg_fight_time`, `f{1,2}_num_prior_fights`/`is_debut`, `f{1,2}_{kd,sig_str_landed,td_landed,ctrl,sig_pct}_hist_avg`, and `f{1,2}_slpm_hist`/`sapm_hist`/`strike_diff` (trailing strike rate for/against).
5. **Shuffle/balance** (`src/processing/shuffle_data.py`) — the critical step: each fight row is duplicated with fighters (and every history feature computed in step 4, since it generically swaps any `f1_*`/`f2_*`-prefixed column) swapped between `f1_*`/`f2_*` slots (`target=1` when `f1_name` is the winner, `target=0` otherwise). This exists specifically so the model can't learn a "f1 always wins" positional bias → `data/processed/balanced_fights.csv`. **Any new per-fighter history feature must be computed before this step, not after** — running per-fighter aggregation after shuffling double-counts every real fight (each contributes two mirrored rows).
6. **Pairwise features, post-shuffle** (`src/processing/pairwise_features.py`) — runs on `balanced_fights.csv` after shuffling. Computes `f1_X - f2_X` comparison diffs (`age_diff`, `height_diff`, `reach_diff`, `ring_rust_diff`, `win_streak_diff`, `loss_streak_diff`, `elo_diff`, `ko_rate_diff`, `sub_rate_diff`, `dec_rate_diff`, `avg_fight_time_diff`, `num_prior_fights_diff`, `strike_diff_advantage`) and one-hot encodes `weight_class`/`f1_stance`/`f2_stance`, persisted to disk. **Diffs must be computed after shuffle, not before** — they aren't `f1_`/`f2_`-prefixed, so shuffle's generic swap can't reorient them; only post-shuffle is `f1_`/`f2_` already guaranteed correct.
7. **Train** (`src/ml/train.py`) — loads the now-fully-engineered `balanced_fights.csv` directly (no feature engineering of its own), drops "spoiler" columns (raw in-fight stats that wouldn't be known pre-fight, e.g. `sig_str_landed`, `td_landed`, `ctrl`) and identity columns, then fits a `RandomForestClassifier`. Uses a **temporal** train/test split (chronological cutoff at the last ~20% of `event_date`s, not random) and reports accuracy/precision/recall/F1/ROC-AUC/Brier score plus two baselines (majority-class, and "higher Elo wins"). A promotion gate compares the new run's accuracy against `models/metrics.json` (±0.5pp tolerance) before overwriting the deployed model files — a worse candidate's metrics go to `models/metrics_candidate.json` instead, and `train.py` still exits 0 in that case so `pipeline.py` doesn't abort.

`predict.py`'s `get_fighter_profile()` generically copies any `f1_`/`f2_`-prefixed column (except ones containing `name`/`link`/`id`) into the live prediction row — so any new per-fighter feature added in step 4 needs no corresponding `predict.py` code as long as it's persisted with the right prefix; only new *diff* features (step 6) need an explicit line in `prepare_data_prevision()`, since diffs are cross-fighter and can't be looked up from a single fighter's profile.

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

- `f1_*` / `f2_*` prefixes denote "fighter in slot 1/2" for a given row — not literal winner/loser (see shuffle step above). On `merged_data.csv` (pre-shuffle) this slot is arbitrary scrape order; only post-shuffle does `target` give it winner/loser meaning.
- `winner_*` / `loser_*` prefixes appear only in `merged_data.csv`, before the shuffle step converts them to `f1_*`/`f2_*` + `target`.
- Weight class and stance are one-hot encoded in `pairwise_features.py` (`weight_class_*`, `f1_stance_*`/`f2_stance_*`); `predict.py` sets `weight_col = f'weight_class_{weight_class}'` directly on the prediction row, so the string passed to `!predict` must match a weight class value seen during training.
