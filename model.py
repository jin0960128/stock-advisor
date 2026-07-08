"""
model.py
用技術指標當特徵,訓練模型預測「隔天股價是漲還是跌」(分類問題)。
採用時間序列切分(不能隨機打亂,否則會用未來資料預測過去 = 資料洩漏)。
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

FEATURE_COLUMNS = [
    "SMA_5", "SMA_20", "SMA_60",
    "EMA_12", "EMA_26",
    "RSI_14",
    "MACD", "MACD_signal", "MACD_hist",
    "BB_upper", "BB_mid", "BB_lower",
    "Volume_MA_20",
    "Return_1d", "Volatility_10d",
]


def build_dataset(df: pd.DataFrame):
    """
    產生特徵 X 與標籤 y。
    y = 1 表示「明天收盤價 > 今天收盤價」,反之為 0。
    """
    data = df.copy()
    data["Target"] = (data["Close"].shift(-1) > data["Close"]).astype(int)

    data = data.dropna(subset=FEATURE_COLUMNS + ["Target"])

    X = data[FEATURE_COLUMNS]
    y = data["Target"]
    return X, y, data


def time_series_split(X, y, test_ratio: float = 0.2):
    """
    依時間順序切分訓練/測試集(不可用 train_test_split 隨機切,會造成資料洩漏)。
    """
    split_idx = int(len(X) * (1 - test_ratio))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
    return X_train, X_test, y_train, y_test


def train_direction_model(X_train, y_train) -> RandomForestClassifier:
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=10,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(model, X_test, y_test):
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    report = classification_report(y_test, preds, target_names=["跌/平", "漲"], zero_division=0)
    return acc, report, preds


def predict_next_day(model, latest_features: pd.DataFrame):
    """
    用最新一天的技術指標,預測「下一個交易日」上漲的機率。
    """
    proba = model.predict_proba(latest_features)[0]
    # proba[1] 對應類別 1 (漲) 的機率
    up_probability = proba[1] if len(proba) > 1 else proba[0]
    return up_probability


def feature_importance(model, feature_names=FEATURE_COLUMNS) -> pd.Series:
    importances = pd.Series(model.feature_importances_, index=feature_names)
    return importances.sort_values(ascending=False)
