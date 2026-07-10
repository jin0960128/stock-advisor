"""
indicators.py
計算常用技術指標: SMA, EMA, RSI, MACD, 布林通道, 成交量均線
"""
import pandas as pd
import numpy as np


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    rsi_val = rsi_val.fillna(50)  # 無漲跌時中性值
    return rsi_val


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def bollinger_bands(series: pd.Series, window: int = 20, num_std: float = 2.0):
    mid = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume.fillna(0)).cumsum()


def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series,
                     volume: pd.Series, window: int = 14) -> pd.Series:
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    direction = np.sign(typical_price.diff()).fillna(0)

    positive_flow = money_flow.where(direction > 0, 0.0)
    negative_flow = money_flow.where(direction < 0, 0.0)
    positive_sum = positive_flow.rolling(window=window, min_periods=window).sum()
    negative_sum = negative_flow.rolling(window=window, min_periods=window).sum()

    money_ratio = positive_sum / negative_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + money_ratio))
    return mfi.fillna(50)


def accumulation_distribution(high: pd.Series, low: pd.Series, close: pd.Series,
                              volume: pd.Series) -> pd.Series:
    price_range = (high - low).replace(0, np.nan)
    money_flow_multiplier = ((close - low) - (high - close)) / price_range
    money_flow_multiplier = money_flow_multiplier.fillna(0)
    return (money_flow_multiplier * volume.fillna(0)).cumsum()


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    輸入含有 Open/High/Low/Close/Volume 欄位的 DataFrame,
    回傳附加技術指標欄位後的 DataFrame。
    """
    out = df.copy()
    close = out["Close"]

    out["SMA_5"] = sma(close, 5)
    out["SMA_20"] = sma(close, 20)
    out["SMA_60"] = sma(close, 60)
    out["EMA_12"] = ema(close, 12)
    out["EMA_26"] = ema(close, 26)

    out["RSI_14"] = rsi(close, 14)

    macd_line, signal_line, hist = macd(close)
    out["MACD"] = macd_line
    out["MACD_signal"] = signal_line
    out["MACD_hist"] = hist

    upper, mid, lower = bollinger_bands(close)
    out["BB_upper"] = upper
    out["BB_mid"] = mid
    out["BB_lower"] = lower

    # 每日報酬率 / 波動率,常拿來當 ML 特徵
    out["Return_1d"] = close.pct_change()
    out["Volatility_10d"] = out["Return_1d"].rolling(10).std()

    out["Volume_MA_20"] = sma(out["Volume"], 20)
    out["Volume_Ratio_20"] = out["Volume"] / out["Volume_MA_20"].replace(0, np.nan)

    out["OBV"] = on_balance_volume(close, out["Volume"])
    out["OBV_10d_change"] = out["OBV"].diff(10)
    out["MFI_14"] = money_flow_index(out["High"], out["Low"], close, out["Volume"], 14)
    out["ADL"] = accumulation_distribution(out["High"], out["Low"], close, out["Volume"])
    out["ADL_10d_change"] = out["ADL"].diff(10)
    out["VPT"] = (out["Return_1d"].fillna(0) * out["Volume"].fillna(0)).cumsum()
    out["VPT_10d_change"] = out["VPT"].diff(10)

    out["HL_Range_Pct"] = (out["High"] - out["Low"]) / close.replace(0, np.nan)
    out["Candle_Body_Pct"] = (out["Close"] - out["Open"]) / out["Open"].replace(0, np.nan)

    return out
