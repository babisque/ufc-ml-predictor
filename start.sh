#!/bin/bash

echo "Verifying database..."
python -c "from src.db.models import init_db; init_db()"

echo "🔍 Verifying Models and Historical Data..."
if [ ! -f "models/ufc_random_forest.pkl" ] || [ ! -f "data/processed/historical_df.csv" ]; then
    echo "Essential files missing! Starting Scraper and Training (This may take a few minutes)..."
    python -m src.ml.pipeline
else
    echo "✅ Model and Historical Data found! Skipping training phase."
fi

echo "🤖 Starting the Oracle (Discord Bot)..."
python -m src.bot.main