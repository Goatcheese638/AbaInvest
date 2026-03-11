# Stock Direction Prediction (AAPL example)

This project trains machine learning models to predict the **next-day price direction** (up or down) for a given stock based on historical OHLCV data and technical indicators.

The default ticker is `AAPL`, but you can easily change it via command-line arguments.

## Features

- Data source: `yfinance` (daily OHLCV)
- Technical indicators:
  - 50-day and 100-day moving averages
  - RSI(14)
  - MACD
  - Bollinger Bands
  - Daily returns
  - 20-day rolling volatility
- Engineered features like:
  - Price / MA ratios
  - MACD vs signal difference
  - Bollinger band position
  - Volume change
- Models:
  - Logistic Regression
  - Random Forest
  - XGBoost
- Evaluation metrics:
  - Accuracy
  - Precision
  - Recall
  - ROC-AUC
- Output:
  - Metrics for each model
  - Feature importance for the best model
  - Plot: `prediction_vs_actual.png`
  - Predicted probability that the stock will go **up** the next trading day

## Installation

1. Create and activate a virtual environment (recommended).

2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

From the project directory, run:

```bash
python main.py
```

To specify a different ticker or number of years of history:

```bash
python main.py --ticker MSFT --years 10
```

After running, you will see:

- Metrics for all models in the console
- A PNG file `prediction_vs_actual.png` showing predicted probability vs actual direction on the test set
- A printed next-day prediction with probability for the chosen ticker

