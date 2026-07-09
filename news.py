"""
news.py
抓取股票近期新聞,並判斷每則新聞是利多還是利空。

新聞來源(會一起抓、一起送去做情緒分析):
  1. Yahoo Finance(yfinance 內建)
  2. 聯合新聞網(udn.com 搜尋結果)
  3. 台灣證券交易所(TWSE)重大訊息公告 —— 僅台股上市代號(.TW)適用

情緒分析提供兩種模式:
  1. Claude API 模式(較準確):需要設定環境變數 ANTHROPIC_API_KEY
  2. 關鍵字模式(免費、離線):作為沒有 API Key 時的 fallback
"""
import os
import re
import json
from urllib.parse import quote

import requests
import yfinance as yf
from bs4 import BeautifulSoup

import config

UDN_SEARCH_URL = "https://udn.com/search/word/2/{query}"
TWSE_ANNOUNCEMENT_API = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockAdvisorBot/1.0)"}

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


def _extract_search_keyword(ticker: str) -> str:
    """
    把 yfinance 代號轉換成適合在中文新聞來源搜尋的關鍵字。
    優先用股票資料庫查出的中文名稱(例如 2330.TW -> 台積電),
    查不到資料庫就直接把代號的市場後綴去掉當關鍵字(例如 2330.TW -> 2330)。
    """
    try:
        from stock_db import STOCK_DB
        for code, yf_code, name, market in STOCK_DB:
            if yf_code.upper() == ticker.upper():
                return name
    except Exception:
        pass
    return re.sub(r"\.(TW|TWO)$", "", ticker, flags=re.IGNORECASE)


def _extract_twse_code(ticker: str) -> str:
    """把 yfinance 代號轉換成證交所用的純數字代號(去掉 .TW/.TWO 後綴)。"""
    return re.sub(r"\.(TW|TWO)$", "", ticker, flags=re.IGNORECASE)


def fetch_udn_news(ticker: str, limit: int = None):
    """
    從聯合新聞網(udn.com)搜尋該股票相關新聞。
    回傳 list of dict: {title, publisher, link}

    註:udn.com 沒有公開 API,這裡用它的搜尋結果頁面解析標題與連結,
       若 udn 網站改版導致抓不到內容,這裡會直接回傳空清單,不影響其他新聞來源。
    """
    limit = limit or config.NEWS_LOOKBACK_COUNT
    keyword = _extract_search_keyword(ticker)
    if not keyword:
        return []

    url = UDN_SEARCH_URL.format(query=quote(keyword))
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[警告] 抓取聯合新聞網失敗: {e}")
        return []

    items = []
    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        # udn 搜尋結果頁的新聞標題連結,用比較寬鬆的選擇器,
        # 盡量涵蓋不同版型(改版時可能需要調整這裡的 selector)
        candidates = soup.select("a.story-list__text, a.story-list__link, h2 a, h3 a")
        seen_links = set()
        for a_tag in candidates:
            title = a_tag.get_text(strip=True)
            link = a_tag.get("href", "")
            if not title or not link or link in seen_links:
                continue
            if link.startswith("/"):
                link = "https://udn.com" + link
            if "udn.com" not in link:
                continue
            seen_links.add(link)
            items.append({"title": title, "publisher": "聯合新聞網", "link": link})
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"[警告] 解析聯合新聞網內容失敗: {e}")
        return []

    return items


def fetch_twse_announcements(ticker: str, limit: int = None):
    """
    從台灣證券交易所(TWSE)Open API 抓取該股票的上市公司重大訊息公告。
    僅適用於台股上市代號(.TW 結尾),美股或上櫃(.TWO)一律回傳空清單。
    回傳 list of dict: {title, publisher, link}

    註:此為證交所當日/近期滾動快照,非歷史查詢;非交易日或無公告時可能為空清單。
       欄位名稱以證交所實際回傳為準,這裡用多組候選鍵名以提高相容性。
    """
    limit = limit or config.NEWS_LOOKBACK_COUNT
    if not ticker.upper().endswith(".TW"):
        return []

    code = _extract_twse_code(ticker)

    try:
        resp = requests.get(TWSE_ANNOUNCEMENT_API, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[警告] 抓取證交所重大訊息失敗: {e}")
        return []

    def _get(row, keys):
        for k in keys:
            v = row.get(k)
            if v:
                return v
        return None

    code_keys = ["公司代號", "Code", "companyCode", "co_id"]
    title_keys = ["主旨", "Subject", "title", "說明"]
    date_keys = ["發言日期", "Date", "date"]

    items = []
    if not isinstance(data, list):
        return []

    for row in data:
        if not isinstance(row, dict):
            continue
        row_code = str(_get(row, code_keys) or "").strip()
        if row_code != code:
            continue
        title = _get(row, title_keys)
        if not title:
            continue
        date = _get(row, date_keys) or ""
        items.append({
            "title": f"[重大訊息 {date}] {title}" if date else f"[重大訊息] {title}",
            "publisher": "台灣證券交易所",
            "link": "https://mops.twse.com.tw/mops/web/t05st02",
        })
        if len(items) >= limit:
            break

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
    抓新聞並分析情緒(整合 Yahoo Finance、聯合新聞網、證交所重大訊息三個來源)。
    回傳: (平均分數 -1~1, 新聞明細 list,每筆含 title/publisher/link/score)
    """
    news_items = fetch_news(ticker)
    news_items += fetch_udn_news(ticker)
    news_items += fetch_twse_announcements(ticker)

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
