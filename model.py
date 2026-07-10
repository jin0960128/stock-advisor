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
    "Volume_Ratio_20", "MFI_14",
    "OBV_10d_change", "ADL_10d_change", "VPT_10d_change",
    "Return_1d", "Volatility_10d",
    "HL_Range_Pct", "Candle_Body_Pct",
]


def build_dataset(df: pd.DataFrame, horizon: int = 1):
    """
    產生特徵 X 與標籤 y。
    y = 1 表示「horizon 個交易日後收盤價 > 今天收盤價」,反之為 0。
    """
    data = df.copy()
    data["Future_Close"] = data["Close"].shift(-horizon)
    data["Target"] = (data["Future_Close"] > data["Close"]).astype(int)

    data = data.dropna(subset=FEATURE_COLUMNS + ["Future_Close", "Target"])

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
    report = classification_report(
        y_test, preds, labels=[0, 1], target_names=["跌/平", "漲"], zero_division=0
    )
    return acc, report, preds


def predict_next_day(model, latest_features: pd.DataFrame):
    """
    用最新一天的技術指標,預測「下一個交易日」上漲的機率。
    """
    proba = model.predict_proba(latest_features)[0]
    classes = list(getattr(model, "classes_", []))
    if 1 in classes:
        return proba[classes.index(1)]
    return 0.0


def predict_horizons(df: pd.DataFrame, horizons=(1, 5, 20), min_samples: int = 80):
    """
    針對多個持有期間分別訓練方向模型。
    回傳格式:
      {horizon: {"up_probability": float|None, "accuracy": float|None,
                 "sample_count": int, "reason": str}}
    """
    results = {}
    for horizon in horizons:
        X, y, _ = build_dataset(df, horizon=horizon)
        result = {
            "up_probability": None,
            "accuracy": None,
            "sample_count": len(X),
            "reason": "",
        }
        if len(X) < min_samples:
            result["reason"] = "資料量不足"
            results[horizon] = result
            continue

        X_train, X_test, y_train, y_test = time_series_split(X, y, test_ratio=0.2)
        if y_train.nunique() < 2 or len(X_test) == 0:
            result["reason"] = "訓練資料方向過於單一"
            results[horizon] = result
            continue

        model = train_direction_model(X_train, y_train)
        acc, _, _ = evaluate_model(model, X_test, y_test)
        result["accuracy"] = acc
        result["up_probability"] = predict_next_day(model, X.iloc[[-1]])
        results[horizon] = result
    return results


def feature_importance(model, feature_names=FEATURE_COLUMNS) -> pd.Series:
    importances = pd.Series(model.feature_importances_, index=feature_names)
    return importances.sort_values(ascending=False)
