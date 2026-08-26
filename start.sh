#!/bin/bash

echo "Verifying database..."
python -c "from src.db.models import init_db; init_db()"

echo "🔍 Verifying Models..."
if [ ! -f "models/ufc_random_forest.pkl" ] || [ ! -f "models/metrics.json" ]; then
    echo "Essential files missing! Starting Scraper and Training (This may take a few minutes)..."
    python -m src.ml.pipeline
else
    echo "✅ Model found! Skipping training phase."
fi

echo "🤖 Starting the Oracle (Discord Bot)..."
python -m src.bot.main