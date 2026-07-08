"""
news.py
抓取股票近期新聞,並判斷每則新聞是利多還是利空。

情緒分析提供兩種模式:
  1. Claude API 模式(較準確):需要設定環境變數 ANTHROPIC_API_KEY
  2. 關鍵字模式(免費、離線):作為沒有 API Key 時的 fallback
"""
import os
import json

import yfinance as yf

import config

# ---- 關鍵字情緒判斷用的詞庫(中英文皆有,可自行擴充) ----
BULLISH_KEYWORDS = [
    "上漲", "大漲", "利多", "優於預期", "超乎預期", "成長", "獲利", "買超", "創新高",
    "強勁需求", "調升目標價", "上修財測", "訂單增加", "業績亮眼",
    "beat expectations", "surge", "rally", "bullish", "outperform", "record high",
    "strong demand", "upgrade", "raises guidance", "growth", "profit jump",
]
BEARISH_KEYWORDS = [
    "下跌", "大跌", "利空", "不如預期", "低於預期", "虧損", "裁員", "賣超", "創新低",
    "需求疲弱", "調降目標價", "下修財測", "訂單減少", "業績衰退", "訴訟", "召回",
    "miss expectations", "plunge", "sell-off", "bearish", "downgrade", "record low",
    "weak demand", "cuts guidance", "lawsuit", "recall", "layoffs", "decline",
]


def fetch_news(ticker: str, limit: int = None):
    """
    用 yfinance 抓取該股票近期新聞。
    回傳 list of dict: {title, publisher, link, publish_time}
    """
    limit = limit or config.NEWS_LOOKBACK_COUNT
    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception as e:
        print(f"[警告] 抓取新聞失敗: {e}")
        return []

    items = []
    for entry in raw_news[:limit]:
        # yfinance 新版把欄位包在 "content" 裡,舊版是扁平結構,兩種都相容處理
        content = entry.get("content", entry)
        title = content.get("title") or entry.get("title", "")
        publisher = (content.get("provider") or {}).get("displayName") \
            if isinstance(content.get("provider"), dict) else entry.get("publisher", "")
        link = (content.get("canonicalUrl") or {}).get("url") \
            if isinstance(content.get("canonicalUrl"), dict) else entry.get("link", "")
        if title:
            items.append({"title": title, "publisher": publisher or "未知來源", "link": link or ""})
    return items


def _keyword_sentiment(text: str) -> float:
    """關鍵字判斷法:回傳 -1(極度利空) ~ +1(極度利多) 的分數。"""
    text_lower = text.lower()
    bull_hits = sum(1 for kw in BULLISH_KEYWORDS if kw.lower() in text_lower)
    bear_hits = sum(1 for kw in BEARISH_KEYWORDS if kw.lower() in text_lower)
    if bull_hits == 0 and bear_hits == 0:
        return 0.0
    score = (bull_hits - bear_hits) / (bull_hits + bear_hits)
    return max(-1.0, min(1.0, score))


def _claude_sentiment(headlines: list) -> list:
    """
    用 Claude API 一次判斷多則新聞標題的情緒分數。
    回傳與 headlines 等長的分數 list ( -1 ~ +1 )。
    若呼叫失敗,回傳 None,呼叫端會自動 fallback 到關鍵字模式。
    """
    try:
        import anthropic
    except ImportError:
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        numbered = "\n".join(f"{i+1}. {h}" for i, h in enumerate(headlines))
        prompt = (
            "你是股市新聞情緒分析器。以下是幾則新聞標題,請針對「對股價短期(未來幾天)的影響」"
            "逐一評分,分數範圍 -1(非常利空)到 1(非常利多),0 代表中性/無明顯影響。\n"
            "只回傳 JSON 陣列,例如 [0.6, -0.3, 0.0],不要有其他文字。\n\n"
            f"{numbered}"
        )
        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        text = text.strip().strip("`").replace("json", "", 1) if text.strip().startswith("```") else text.strip()
        scores = json.loads(text)
        if isinstance(scores, list) and len(scores) == len(headlines):
            return [max(-1.0, min(1.0, float(s))) for s in scores]
        return None
    except Exception as e:
        print(f"[提示] Claude 情緒分析失敗,改用關鍵字模式。原因: {e}")
        return None


def analyze_news_sentiment(ticker: str):
    """
    抓新聞並分析情緒。
    回傳: (平均分數 -1~1, 新聞明細 list,每筆含 title/publisher/link/score)
    """
    news_items = fetch_news(ticker)
    if not news_items:
        return 0.0, []

    titles = [item["title"] for item in news_items]

    scores = None
    if config.USE_CLAUDE_SENTIMENT:
        scores = _claude_sentiment(titles)

    if scores is None:
        scores = [_keyword_sentiment(t) for t in titles]

    for item, score in zip(news_items, scores):
        item["score"] = round(score, 2)

    avg_score = sum(scores) / len(scores) if scores else 0.0
    return avg_score, news_items
