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


def combine_signals(tech_score: float, ml_score_val: float, news_score: float, strategy: dict) -> float:
    """依照策略權重,把三種訊號加權平均成一個 -1~1 的綜合分數。"""
    w_tech = strategy["technical_weight"]
    w_ml = strategy["ml_weight"]
    w_news = strategy["news_weight"]
    total_w = w_tech + w_ml + w_news
    if total_w == 0:
        return 0.0
    combined = (tech_score * w_tech + ml_score_val * w_ml + news_score * w_news) / total_w
    return max(-1.0, min(1.0, combined))


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


def build_recommendation(tech_score_val: float, ml_score_val: float, news_score_val: float, strategy: dict):
    final_score = combine_signals(tech_score_val, ml_score_val, news_score_val, strategy)
    percentages = score_to_percentages(final_score)
    top_action = max(percentages, key=percentages.get)
    return {
        "technical_score": round(tech_score_val, 3),
        "ml_score": round(ml_score_val, 3),
        "news_score": round(news_score_val, 3),
        "final_score": round(final_score, 3),
        "buy_pct": percentages["買入"],
        "hold_pct": percentages["觀望"],
        "sell_pct": percentages["賣出"],
        "top_action": top_action,
    }
