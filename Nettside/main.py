import argparse
import datetime as dt
from typing import Dict, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


def download_price_data(ticker: str, years: int = 10) -> pd.DataFrame:
    """Download daily OHLCV data using yfinance for the last `years` years."""
    end = dt.date.today()
    start = end - dt.timedelta(days=365 * years)
    df = yf.download(ticker, start=start, end=end, auto_adjust=False)

    if df.empty:
        raise ValueError(f"No data downloaded for ticker {ticker}.")

    # Flatten potential MultiIndex columns (can happen with some yfinance versions)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.dropna(inplace=True)
    return df


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add technical indicators to the price DataFrame."""
    close = df["Close"]
    # Ensure close is a 1D Series (yfinance can sometimes return a DataFrame)
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    df["Close"] = close

    # Moving averages (simple)
    df["MA50"] = close.rolling(window=50, min_periods=1).mean()
    df["MA100"] = close.rolling(window=100, min_periods=1).mean()

    # RSI(14) implementation
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=14).mean()
    avg_loss = loss.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands (20-day)
    mavg = close.rolling(window=20, min_periods=20).mean()
    mstd = close.rolling(window=20, min_periods=20).std()
    df["BB_mavg"] = mavg
    df["BB_high"] = mavg + 2 * mstd
    df["BB_low"] = mavg - 2 * mstd

    # Daily returns
    df["daily_return"] = close.pct_change()

    # Next-day return (from today's close to next day's close)
    df["next_day_return"] = close.shift(-1) / close - 1.0

    # Rolling volatility (20-day standard deviation of returns)
    df["volatility_20"] = df["daily_return"].rolling(window=20).std()

    return df


def build_features_and_target(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.Series, pd.Series, list, pd.Series]:
    """Create feature matrix X, target y, and return full df with indicators."""
    df = add_technical_indicators(df.copy())

    # Feature engineering
    df["price_ma100_ratio"] = df["Close"] / df["MA100"]
    df["price_ma50_ratio"] = df["Close"] / df["MA50"]
    df["rsi_14"] = df["RSI14"]
    df["macd_signal_diff"] = df["MACD"] - df["MACD_signal"]

    # Bollinger band position: 0 = lower band, 1 = upper band
    bb_range = df["BB_high"] - df["BB_low"]
    df["bb_position"] = (df["Close"] - df["BB_low"]) / bb_range

    # Volume change
    df["volume_change"] = df["Volume"].pct_change()

    # Target: 1 if next day's close > today's close, else 0
    df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)

    feature_cols = [
        "price_ma100_ratio",
        "price_ma50_ratio",
        "rsi_14",
        "macd_signal_diff",
        "bb_position",
        "daily_return",
        "volatility_20",
        "volume_change",
    ]

    # Replace infinities (e.g., from division by zero) with NaN, then drop
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    # Training data: drop rows where any feature or target is NaN
    df_model = df.dropna(subset=feature_cols + ["target"]).copy()

    X = df_model[feature_cols].copy()
    y = df_model["target"].copy()

    # Next-day returns aligned with X/y (used for backtesting)
    next_day_returns = df_model["next_day_return"].copy()

    # Keep the original index (dates) for plotting
    dates = df_model.index

    return X, y, dates, feature_cols, next_day_returns


def make_models(random_state: int = 42) -> Dict[str, Pipeline]:
    """Create dictionary of models wrapped in sklearn Pipelines."""
    models: Dict[str, Pipeline] = {
        "logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=1000,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=300,
                        max_depth=None,
                        min_samples_leaf=5,
                        n_jobs=-1,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "xgboost": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=300,
                        max_depth=4,
                        learning_rate=0.05,
                        subsample=0.8,
                        colsample_bytree=0.8,
                        objective="binary:logistic",
                        eval_metric="logloss",
                        tree_method="hist",
                        n_jobs=-1,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
    }
    return models


def evaluate_models(
    models: Dict[str, Pipeline],
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> Tuple[Dict[str, dict], str]:
    """Train and evaluate models, return metrics and best model name."""
    results: Dict[str, dict] = {}
    best_model_name = None
    best_auc = -np.inf

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        if hasattr(model, "predict_proba"):
            y_proba = model.predict_proba(X_test)[:, 1]
        else:
            # Fallback for models without predict_proba (not expected here)
            y_proba = y_pred.astype(float)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        try:
            auc = roc_auc_score(y_test, y_proba)
        except ValueError:
            auc = float("nan")

        results[name] = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "roc_auc": auc,
            "y_pred": y_pred,
            "y_proba": y_proba,
        }

        if not np.isnan(auc) and auc > best_auc:
            best_auc = auc
            best_model_name = name

    return results, best_model_name


def compute_feature_importance(model: Pipeline, feature_names: list) -> pd.DataFrame:
    """Extract feature importances or coefficients from the trained model."""
    # Last step in the pipeline is the underlying model
    base_model = model.named_steps["model"]

    importances = None

    if hasattr(base_model, "feature_importances_"):
        importances = base_model.feature_importances_
    elif hasattr(base_model, "coef_"):
        # For logistic regression, use absolute value of coefficients
        coefs = base_model.coef_.ravel()
        importances = np.abs(coefs)
    else:
        raise ValueError("Model does not expose feature importances.")

    importance_df = pd.DataFrame(
        {"feature": feature_names, "importance": importances}
    ).sort_values("importance", ascending=False)

    return importance_df


def plot_prediction_vs_actual(
    dates: pd.DatetimeIndex,
    y_test: pd.Series,
    y_proba: np.ndarray,
    ticker: str,
    output_path: str = "prediction_vs_actual.png",
) -> None:
    """Create a simple graph of predicted probability vs actual direction."""
    plt.figure(figsize=(12, 6))
    plt.plot(dates, y_proba, label="Predicted probability (up)", color="blue")
    plt.scatter(
        dates,
        y_test.values,
        label="Actual direction (1=up, 0=down)",
        color="orange",
        s=15,
        alpha=0.7,
    )
    plt.title(f"Predicted probability vs actual direction for {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Probability / Actual")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def backtest_threshold_strategy(
    dates: pd.DatetimeIndex,
    y_proba: np.ndarray,
    next_day_returns: pd.Series,
    threshold: float,
    ticker: str,
    output_path: str = "strategy_vs_buyhold.png",
) -> Dict[str, float]:
    """
    Simple long-only backtest:
    - Go long if predicted probability of "up" > threshold.
    - Hold for one day: realize next_day_return.
    - Compare against buy & hold over the same period.
    """
    if len(dates) != len(y_proba) or len(dates) != len(next_day_returns):
        raise ValueError("Dates, probabilities, and returns must have the same length.")

    bt_df = pd.DataFrame(
        {
            "date": dates,
            "proba_up": y_proba,
            "next_day_return": next_day_returns.values,
        }
    ).set_index("date")

    # Clean infinities/NaNs (especially last row with no next-day return)
    bt_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    bt_df.dropna(subset=["proba_up", "next_day_return"], inplace=True)

    bt_df["signal"] = (bt_df["proba_up"] > threshold).astype(int)
    bt_df["strategy_return"] = bt_df["signal"] * bt_df["next_day_return"]
    bt_df["bh_return"] = bt_df["next_day_return"]

    bt_df["strategy_equity"] = (1 + bt_df["strategy_return"]).cumprod()
    bt_df["bh_equity"] = (1 + bt_df["bh_return"]).cumprod()

    total_return_strategy = bt_df["strategy_equity"].iloc[-1] - 1.0
    total_return_bh = bt_df["bh_equity"].iloc[-1] - 1.0
    hit_rate = (bt_df["strategy_return"] > 0).mean()

    plt.figure(figsize=(12, 6))
    plt.plot(
        bt_df.index,
        bt_df["strategy_equity"],
        label=f"Strategy (thr={threshold:.2f})",
        color="blue",
    )
    plt.plot(
        bt_df.index,
        bt_df["bh_equity"],
        label="Buy & hold",
        color="gray",
        linestyle="--",
    )
    plt.title(f"Strategy vs Buy & Hold on test set for {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Equity (start=1.0)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    return {
        "total_return_strategy": float(total_return_strategy),
        "total_return_buy_hold": float(total_return_bh),
        "hit_rate": float(hit_rate),
    }


def predict_next_day(
    model: Pipeline,
    df_with_features: pd.DataFrame,
    feature_cols: list,
) -> Tuple[float, int]:
    """
    Predict probability of next day's close being up vs down.

    Uses the most recent available row of features.
    """
    latest_row = df_with_features.iloc[-1]
    latest_features = latest_row[feature_cols]

    if latest_features.isna().any():
        raise ValueError("Latest feature row contains NaN values, cannot predict.")

    proba_up = float(model.predict_proba([latest_features.values])[0, 1])
    pred_label = int(proba_up >= 0.5)
    return proba_up, pred_label


def run_single_ticker(ticker: str, years: int, threshold: float) -> Dict[str, float]:
    """Run the full pipeline (training, evaluation, backtest, next-day prediction) for one ticker."""
    print(f"Downloading {years} years of daily data for {ticker}...")
    raw_df = download_price_data(ticker, years=years)
    print(f"Downloaded {len(raw_df)} rows of data.")

    # Build features and target
    X, y, dates, feature_cols, next_day_returns = build_features_and_target(raw_df)
    print(f"Prepared dataset with {X.shape[0]} samples and {X.shape[1]} features.")

    # Time-series split: 80% train, 20% test (no shuffling)
    (
        X_train,
        X_test,
        y_train,
        y_test,
        dates_train,
        dates_test,
        next_ret_train,
        next_ret_test,
    ) = train_test_split(
        X,
        y,
        dates,
        next_day_returns,
        test_size=0.2,
        shuffle=False,
    )

    models = make_models()
    print("Training and evaluating models...")
    results, best_model_name = evaluate_models(
        models, X_train, X_test, y_train, y_test
    )

    print("\nModel performance on test set:")
    for name, metrics in results.items():
        print(f"\n{name}:")
        print(f"  Accuracy : {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall   : {metrics['recall']:.4f}")
        print(f"  ROC-AUC  : {metrics['roc_auc']:.4f}")

    if best_model_name is None:
        raise RuntimeError("No valid model was trained (all ROC-AUC are NaN).")

    print(f"\nBest model based on ROC-AUC: {best_model_name}")
    best_model = models[best_model_name]

    # Feature importance from best model
    try:
        importance_df = compute_feature_importance(best_model, feature_cols)
        print("\nFeature importance (best model):")
        for _, row in importance_df.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")
    except ValueError:
        print("\nBest model does not expose feature importances.")

    # Plot prediction vs actual for the best model
    best_proba = results[best_model_name]["y_proba"]
    plot_prediction_vs_actual(
        dates_test,
        y_test,
        best_proba,
        ticker=ticker,
        output_path=f"prediction_vs_actual_{ticker}.png",
    )
    print(
        f'Saved plot "prediction_vs_actual_{ticker}.png" to current directory.'
    )

    # Backtest strategy with probability threshold
    bt_metrics = backtest_threshold_strategy(
        dates_test,
        best_proba,
        next_ret_test,
        threshold=threshold,
        ticker=ticker,
        output_path=f"strategy_vs_buyhold_{ticker}.png",
    )
    print(f"\nBacktest on test set with threshold {threshold:.2f}:")
    print(f"  Strategy total return : {bt_metrics['total_return_strategy']:.2%}")
    print(f"  Buy & hold total return: {bt_metrics['total_return_buy_hold']:.2%}")
    print(f"  Hit rate (strategy)   : {bt_metrics['hit_rate']:.2%}")
    print(
        f'Saved plot "strategy_vs_buyhold_{ticker}.png" to current directory.'
    )

    # Use full feature DataFrame (including last row) for next-day prediction
    full_df = add_technical_indicators(raw_df.copy())
    full_df["price_ma100_ratio"] = full_df["Close"] / full_df["MA100"]
    full_df["price_ma50_ratio"] = full_df["Close"] / full_df["MA50"]
    full_df["rsi_14"] = full_df["RSI14"]
    full_df["macd_signal_diff"] = full_df["MACD"] - full_df["MACD_signal"]
    bb_range_full = full_df["BB_high"] - full_df["BB_low"]
    full_df["bb_position"] = (full_df["Close"] - full_df["BB_low"]) / bb_range_full
    full_df["daily_return"] = full_df["Close"].pct_change()
    full_df["volatility_20"] = full_df["daily_return"].rolling(window=20).std()
    full_df["volume_change"] = full_df["Volume"].pct_change()

    # Ensure we don't pass infinities into the model for the latest row
    full_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    try:
        proba_up, pred_label = predict_next_day(best_model, full_df, feature_cols)
        direction = "UP" if pred_label == 1 else "DOWN"
        trade_action = (
            "BUY (signal active)" if proba_up >= threshold else "NO TRADE (signal inactive)"
        )
        print(
            f"\nPredicted probability that {ticker} will go UP next day: "
            f"{proba_up:.4f} -> predicted direction: {direction}\n"
            f"Trade rule with threshold {threshold:.2f}: {trade_action}"
        )
    except ValueError as e:
        print(f"\nCould not compute next-day prediction: {e}")

    return {
        "best_model_name": best_model_name,
        "best_model_auc": float(results[best_model_name]["roc_auc"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train ML models to predict next-day stock direction."
    )
    parser.add_argument(
        "--ticker",
        type=str,
        default="AAPL",
        help="Single ticker symbol to run (default: AAPL).",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=10,
        help="Number of years of historical data to download (default: 10).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Probability threshold for going long in backtest and trade rule (default: 0.6).",
    )
    parser.add_argument(
        "--multi_tickers",
        type=str,
        default="",
        help=(
            "Optional comma-separated list of tickers to run in batch "
            "(for example: 'EQNR.OL,NEL.OL,ORK.OL'). If provided, overrides --ticker."
        ),
    )
    args = parser.parse_args()

    years = args.years
    threshold = args.threshold

    if args.multi_tickers:
        tickers = [
            t.strip().upper() for t in args.multi_tickers.split(",") if t.strip()
        ]
        model_win_counts: Dict[str, int] = {}

        for tk in tickers:
            print("\n==============================")
            print(f"Running pipeline for ticker {tk}")
            print("==============================\n")
            metrics = run_single_ticker(tk, years, threshold)
            best_name = metrics["best_model_name"]
            model_win_counts[best_name] = model_win_counts.get(best_name, 0) + 1

        print("\nSummary of best models across tickers:")
        for model_name, count in model_win_counts.items():
            print(f"  {model_name}: best for {count} tickers")
    else:
        ticker = args.ticker.upper()
        run_single_ticker(ticker, years, threshold)


if __name__ == "__main__":
    main()

