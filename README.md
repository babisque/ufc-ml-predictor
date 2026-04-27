# UFC ML Predictor

A comprehensive Machine Learning pipeline and Discord bot designed to predict UFC fight outcomes. This project automates the entire lifecycle from data scraping and processing to model training and real-time inference.

## 🚀 Features

- **Automated Scraping**: Extracts event, fight, and fighter data directly from UFC sources.
- **Data Engineering**: Robust cleaning and merging pipeline to prepare datasets for training.
- **ML Engine**: Random Forest model optimized for fight prediction.
- **Discord Integration**: Interactive bot to query predictions, fighter stats, and event info.
- **Audit System**: SQLite-backed auditing to track prediction accuracy over time.
- **Dockerized**: Fully containerized environment for easy deployment.

## 📁 Repository Structure

```text
.
├── data/               # Raw and processed datasets (ignored by git)
├── models/             # Trained model artifacts (.pkl files)
├── notebooks/          # Exploratory Data Analysis (EDA)
├── scripts/            # Utility scripts (auditor, scraper runner)
├── src/
│   ├── bot/            # Discord bot implementation
│   ├── core/           # Configuration and logging
│   ├── db/             # Database models and connection logic
│   ├── ml/             # Training and prediction pipelines
│   ├── processing/     # Data cleaning and feature engineering
│   └── scraper/        # Web scraping modules
├── tests/              # Comprehensive test suite
├── Dockerfile          # Container definition
├── docker-compose.yml  # Multi-container orchestration
└── requirements.txt    # Python dependencies
```

## 🛠️ Installation

### Prerequisites

- Python 3.10+
- [Optional] Docker & Docker Compose

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/ufc-ml-predictor.git
   cd ufc-ml-predictor
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   Create a `.env` file in the root directory:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   ```

## 📖 Usage

### 1. Run the Full Pipeline
Scrapes data, processes it, and trains the model:
```bash
python src/ml/pipeline.py
```

### 2. Local Prediction (CLI)
Test predictions for specific fighters:
```bash
python src/ml/predict.py
```

### 3. Start the Discord Bot
```bash
python src/bot/main.py
```

### 4. Database Auditing
Monitor and update predictions with actual results:
```bash
python scripts/auditor.py
```

## 🤖 Bot Commands

- `!predict <Fighter 1> , <Fighter 2> , <Weight Class>`: Predict outcome.
- `!nextEvent`: Show details for the upcoming UFC event.
- `!lastEvent`: Summary of the most recent event.
- `!profile <Fighter Name>`: Get detailed fighter statistics.
- `!stats`: Global prediction accuracy and bot stats.

## 🐳 Docker Support

To run the entire stack using Docker:

```bash
docker-compose up --build
```

## 🧪 Testing

Run the test suite to ensure everything is working correctly:
```bash
pytest
```

## 📝 License

This project is for educational and research purposes. Data usage should comply with UFC's terms of service.
