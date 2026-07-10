"""
decision.py
把技術指標、機器學習模型、新聞情緒三種訊號,合成為最終的
「買入 / 觀望 / 賣出」建議百分比。

技術指標與 ML 之後都可以在這裡替換或擴充規則,
不影響 decision 合成與紀錄的邏輯。
"""
import math

import config


def technical_score(df) -> float:
    """
    用最新一筆技術指標資料,算出一個 -1(偏空)~ +1(偏多) 的規則式分數。
    目前納入: RSI 超買超賣、MACD 交叉、價格相對均線位置。
    之後決定要用哪些指標時,只要調整這個函式內的規則即可。
    """
    latest = df.iloc[-1]
    scores = []

    # RSI: <30 超賣(偏多訊號), >70 超買(偏空訊號)
    rsi = latest.get("RSI_14")
    if rsi is not None and not math.isnan(rsi):
        if rsi < 30:
            scores.append(1.0)
        elif rsi > 70:
            scores.append(-1.0)
        else:
            # 30~70 之間線性映射到 -0.3~0.3 之間的弱訊號
            scores.append((50 - rsi) / 20 * 0.3)

    # MACD: MACD 在訊號線之上偏多,之下偏空
    macd, macd_signal = latest.get("MACD"), latest.get("MACD_signal")
    if macd is not None and macd_signal is not None and not math.isnan(macd) and not math.isnan(macd_signal):
        diff = macd - macd_signal
        scores.append(max(-1.0, min(1.0, diff * 2)))

    # 價格 vs 均線: 站上短中期均線偏多,跌破偏空
    close, sma20, sma60 = latest.get("Close"), latest.get("SMA_20"), latest.get("SMA_60")
    if all(v is not None and not (isinstance(v, float) and math.isnan(v)) for v in [close, sma20, sma60]):
        above = int(close > sma20) + int(close > sma60)
        scores.append({0: -1.0, 1: 0.0, 2: 1.0}[above])

    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def ml_score(up_probability: float) -> float:
    """把 ML 模型輸出的『上漲機率』(0~1) 轉成 -1~1 的分數。"""
    return (up_probability - 0.5) * 2


def _clip_score(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _safe_float(value, default=None):
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(numeric):
        return default
    return numeric


def candlestick_score(df):
    """
    用最近 K 棒型態估計短線偏多/偏空分數。
    回傳 (分數, 訊號列表),分數範圍 -1~+1。
    """
    if len(df) < 3:
        return 0.0, ["K線資料不足"]

    latest = df.iloc[-1]
    prev = df.iloc[-2]
    recent = df.tail(3)
    signals = []
    scores = []

    open_price = _safe_float(latest.get("Open"))
    high = _safe_float(latest.get("High"))
    low = _safe_float(latest.get("Low"))
    close = _safe_float(latest.get("Close"))
    prev_open = _safe_float(prev.get("Open"))
    prev_close = _safe_float(prev.get("Close"))

    if None not in [open_price, high, low, close, prev_open, prev_close]:
        candle_range = max(high - low, 1e-9)
        body = close - open_price
        body_abs = abs(body)
        upper_shadow = high - max(open_price, close)
        lower_shadow = min(open_price, close) - low

        if body_abs / candle_range < 0.1:
            signals.append("十字線: 多空拉鋸")
            scores.append(0.0)
        if lower_shadow > body_abs * 2 and upper_shadow < body_abs * 1.2:
            signals.append("錘子線: 下檔承接偏多")
            scores.append(0.55)
        if upper_shadow > body_abs * 2 and lower_shadow < body_abs * 1.2:
            signals.append("長上影線: 上檔賣壓偏空")
            scores.append(-0.55)

        prev_bearish = prev_close < prev_open
        prev_bullish = prev_close > prev_open
        bullish = close > open_price
        bearish = close < open_price
        if prev_bearish and bullish and close >= prev_open and open_price <= prev_close:
            signals.append("多方吞噬: K線反轉偏多")
            scores.append(0.85)
        if prev_bullish and bearish and open_price >= prev_close and close <= prev_open:
            signals.append("空方吞噬: K線反轉偏空")
            scores.append(-0.85)

    closes = recent["Close"].tolist()
    opens = recent["Open"].tolist()
    if len(closes) == 3 and all(_safe_float(v) is not None for v in closes + opens):
        if closes[0] < closes[1] < closes[2] and all(c > o for c, o in zip(closes, opens)):
            signals.append("三日連陽: 短線動能偏多")
            scores.append(0.45)
        elif closes[0] > closes[1] > closes[2] and all(c < o for c, o in zip(closes, opens)):
            signals.append("三日連陰: 短線動能偏空")
            scores.append(-0.45)

    if not scores:
        return 0.0, ["未偵測到明確K線型態"]
    return round(_clip_score(sum(scores) / len(scores)), 3), signals


def chip_score(df):
    """
    用 OHLCV 推估籌碼/量價面。若未接交易所三大法人資料,
    先以量比、MFI、OBV、ADL、VPT 做可跨市場使用的代理指標。
    """
    if df.empty:
        return 0.0, ["籌碼資料不足"]

    latest = df.iloc[-1]
    signals = []
    scores = []

    close = _safe_float(latest.get("Close"))
    prev_close = _safe_float(df["Close"].iloc[-2] if len(df) >= 2 else None)
    volume_ratio = _safe_float(latest.get("Volume_Ratio_20"))
    mfi = _safe_float(latest.get("MFI_14"))
    obv_change = _safe_float(latest.get("OBV_10d_change"))
    adl_change = _safe_float(latest.get("ADL_10d_change"))
    vpt_change = _safe_float(latest.get("VPT_10d_change"))

    if None not in [close, prev_close, volume_ratio] and volume_ratio >= 1.5:
        if close > prev_close:
            signals.append(f"放量上漲: 量比 {volume_ratio:.2f}")
            scores.append(0.55)
        elif close < prev_close:
            signals.append(f"放量下跌: 量比 {volume_ratio:.2f}")
            scores.append(-0.55)

    if mfi is not None:
        if mfi < 20:
            signals.append(f"MFI {mfi:.1f}: 資金流低檔反彈機會")
            scores.append(0.35)
        elif mfi > 80:
            signals.append(f"MFI {mfi:.1f}: 資金流過熱")
            scores.append(-0.35)
        else:
            scores.append((mfi - 50) / 50 * 0.35)

    for label, change in [
        ("OBV", obv_change),
        ("ADL", adl_change),
        ("VPT", vpt_change),
    ]:
        if change is None:
            continue
        if change > 0:
            signals.append(f"{label} 10日走升")
            scores.append(0.30)
        elif change < 0:
            signals.append(f"{label} 10日走弱")
            scores.append(-0.30)

    if not scores:
        return 0.0, ["未偵測到明確籌碼訊號"]
    return round(_clip_score(sum(scores) / len(scores)), 3), signals[:5]


def combine_signals(tech_score: float, ml_score_val: float, news_score: float, strategy: dict,
                    kline_score_val: float = 0.0, chip_score_val: float = 0.0) -> float:
    """依照策略權重,把各種訊號加權平均成一個 -1~1 的綜合分數。"""
    signals = [
        (tech_score, strategy.get("technical_weight", 0.0)),
        (kline_score_val, strategy.get("kline_weight", 0.0)),
        (chip_score_val, strategy.get("chip_weight", 0.0)),
        (ml_score_val, strategy.get("ml_weight", 0.0)),
        (news_score, strategy.get("news_weight", 0.0)),
    ]
    total_w = sum(weight for _, weight in signals)
    if total_w == 0:
        return 0.0
    combined = sum(score * weight for score, weight in signals) / total_w
    return _clip_score(combined)


def score_to_percentages(final_score: float):
    """
    把綜合分數轉成 買入/觀望/賣出 三種機率百分比(總和 100%)。
    用「距離三個錨點(買=+1, 觀望=0, 賣=-1)越近,權重越高」的 softmax 方式計算,
    DECISION_TEMPERATURE 越大,分數差異會被放大得越明顯。
    """
    anchors = {"買入": 1.0, "觀望": 0.0, "賣出": -1.0}
    t = config.DECISION_TEMPERATURE

    raw_weights = {}
    for label, anchor in anchors.items():
        distance = abs(final_score - anchor)
        raw_weights[label] = math.exp(-t * distance)

    total = sum(raw_weights.values())
    percentages = {label: round(w / total * 100, 1) for label, w in raw_weights.items()}

    # 修正四捨五入誤差,確保加總剛好 100
    diff = round(100 - sum(percentages.values()), 1)
    top_label = max(percentages, key=percentages.get)
    percentages[top_label] = round(percentages[top_label] + diff, 1)

    return percentages


def build_recommendation(tech_score_val: float, ml_score_val: float, news_score_val: float, strategy: dict,
                         kline_score_val: float = 0.0, chip_score_val: float = 0.0):
    final_score = combine_signals(
        tech_score_val, ml_score_val, news_score_val, strategy,
        kline_score_val=kline_score_val, chip_score_val=chip_score_val,
    )
    percentages = score_to_percentages(final_score)
    top_action = max(percentages, key=percentages.get)
    return {
        "technical_score": round(tech_score_val, 3),
        "kline_score": round(kline_score_val, 3),
        "chip_score": round(chip_score_val, 3),
        "ml_score": round(ml_score_val, 3),
        "news_score": round(news_score_val, 3),
        "final_score": round(final_score, 3),
        "buy_pct": percentages["買入"],
        "hold_pct": percentages["觀望"],
        "sell_pct": percentages["賣出"],
        "top_action": top_action,
    }
