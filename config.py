"""
config.py
集中管理設定:策略權重、持有天數、資料庫路徑等。

之後如果你決定好要用哪些技術指標、或想調整各訊號的重要性,
都只要改這裡的權重,不用動到其他程式邏輯。
"""

# ============ 策略設定 ============
# 每個策略是一組權重組合,weight 總和不用剛好是 1,程式會自動正規化。
# 你可以新增多組策略(例如 aggressive / conservative),
# 之後 stats 報表會分別統計每個策略的長期表現,方便比較哪組最好。
STRATEGIES = {
    "default": {
        "technical_weight": 0.30,  # 技術指標訊號的權重
        "kline_weight": 0.15,      # K 線型態訊號的權重
        "chip_weight": 0.15,       # 籌碼/量價訊號的權重
        "ml_weight": 0.25,         # 機器學習模型(隨機森林)訊號的權重
        "news_weight": 0.15,       # 新聞情緒訊號的權重
        "holding_days": 5,         # 建議後多少個交易日,回頭檢查結果
    },
    "news_focused": {
        "technical_weight": 0.15,
        "kline_weight": 0.10,
        "chip_weight": 0.10,
        "ml_weight": 0.20,
        "news_weight": 0.45,
        "holding_days": 5,
    },
    "technical_focused": {
        "technical_weight": 0.45,
        "kline_weight": 0.25,
        "chip_weight": 0.15,
        "ml_weight": 0.10,
        "news_weight": 0.05,
        "holding_days": 10,
    },
    "long_term_focused": {
        "technical_weight": 0.25,
        "kline_weight": 0.10,
        "chip_weight": 0.20,
        "ml_weight": 0.35,
        "news_weight": 0.10,
        "holding_days": 20,
    },
}

DEFAULT_STRATEGY = "default"

# ============ 資料來源設定 ============
PRICE_HISTORY_PERIOD = "10y"    # 抓取歷史股價的區間(預設10年,可在網頁上讓使用者調整)
PRICE_HISTORY_PERIOD_OPTIONS = ["6mo", "1y", "2y", "5y", "10y", "max"]  # 網頁上可選的區間
PRICE_HISTORY_PERIOD_LABELS = {
    "6mo": "近6個月", "1y": "近1年", "2y": "近2年",
    "5y": "近5年", "10y": "近10年", "max": "全部歷史",
}
NEWS_LOOKBACK_COUNT = 10        # 抓取最近幾則新聞來做情緒分析

# ============ 預測設定 ============
# key 是要預測幾個交易日後的方向,value 是畫面顯示名稱。
PREDICTION_HORIZONS = {
    1: "隔日",
    5: "5日",
    20: "20日",
}

# ============ 情緒分析設定 ============
# 若要用 Claude API 做更精準的新聞情緒判斷,設定環境變數 ANTHROPIC_API_KEY 即可。
# 沒有設定的話,會自動退回使用內建的關鍵字判斷法(免費、不需要網路 API,但較粗略)。
USE_CLAUDE_SENTIMENT = True     # 若偵測到 ANTHROPIC_API_KEY 才會啟用,否則自動 fallback

# ============ 決策轉換設定 ============
# 綜合分數 (-1 = 極度看空 ~ +1 = 極度看多) 轉換成 買入/觀望/賣出 百分比時的「敏感度」
# 數字越大,分數些微差異就會讓百分比差異更明顯;數字越小,結果會越平均。
DECISION_TEMPERATURE = 2.5

# ============ 持有紀錄/交易成本設定 ============
# 費率單位皆為百分比。台股常見手續費為 0.1425%,證交稅約 0.3%;
# 若分析其他市場,可在網頁介面依自己的券商費率調整。
DEFAULT_FEE_DEDUCTED = True
DEFAULT_BUY_FEE_RATE = 0.1425
DEFAULT_SELL_FEE_RATE = 0.1425
DEFAULT_SELL_TAX_RATE = 0.3

# ============ 資料庫 ============
DB_PATH = "data/advisor_records.db"
