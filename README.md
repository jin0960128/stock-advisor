# 單一股票分析 + 決策建議系統

輸入一支股票代號,自動:
1. 抓取近期相關新聞,判斷是利多還是利空
2. 計算技術指標(RSI、MACD、均線等),並加入 K 線型態與籌碼/量價代理指標
3. 用機器學習模型預測隔日、5日、20日漲跌機率
4. 綜合技術面、K線、籌碼、ML、新聞五種訊號,給出「買入 X% / 觀望 X% / 賣出 X%」的建議
5. **把每次建議記錄下來**,持有天數到期後自動回顧「當初建議 vs 實際結果」,並可內扣手續費/交易稅
6. 長期累積後,統計策略、建議動作與個股的方向準確率與扣費後報酬

⚠️ **重要提醒**:這是學習/研究用的輔助分析工具,不是穩賺不賠的系統。任何輸出都不構成投資建議,
請務必自行判斷風險、謹慎操作。

## 檔案結構

```
stock_advisor/
├── web_app.py       ← 新版自訂網頁介面(不使用 Streamlit)
├── main.py          ← 主程式,用指令執行不同功能
├── app.py           ← 舊版 Streamlit 介面(可選)
├── config.py         ← 策略權重、資料庫路徑等設定,之後想調整指標權重改這裡
├── indicators.py      ← 技術指標計算 (SMA/EMA/RSI/MACD/布林通道)
├── decision.py         ← 訊號合成邏輯 (技術面 + ML + 新聞面 → 買賣觀望百分比)
├── model.py             ← 機器學習模型 (隨機森林,預測隔天漲跌機率)
├── news.py                ← 新聞抓取 + 情緒分析 (關鍵字模式 / Claude API 模式)
├── storage.py               ← SQLite 資料庫,記錄每次建議與回顧結果
├── report.py                  ← 產生互動式 HTML 報告
├── requirements.txt            ← 需要安裝的套件
└── data/advisor_records.db      ← 執行後自動產生的紀錄資料庫
```

## 安裝

```bash
pip install -r requirements.txt
```

## 🌐 網頁介面(推薦,不用碰指令)

裝好套件後,直接執行:

```bash
python web_app.py
```

終端機會顯示一個網址(通常是 `http://localhost:8000`),用瀏覽器打開即可。
之後每次要用,重複這行指令即可,不需要再打 `analyze` / `update` / `stats` 這些指令——
網頁介面裡有四個分頁:

- **🔍 分析**:選市場(台股/美股/日本/韓國/歐洲)、輸入股票代號、選策略、按「開始分析」,結果(K線圖、多期間預測、新聞、建議百分比)都會直接顯示在網頁上
- **🔄 回顧更新**:按一個按鈕,自動回顧所有到期的建議
- **📊 績效統計**:表格呈現各策略的長期勝率、扣費後報酬,並比較策略/動作/個股準確率
- **🕘 歷史紀錄**:查詢某支股票過去的所有建議

要關閉網頁伺服器,回到終端機按 `Ctrl + C` 即可。

> 這個網頁只在你自己的電腦上執行(local),不會被其他人存取到,資料庫檔案也只存在你自己的電腦裡。
> 如果之後想放到網路上讓手機也能開、或多人共用,可以再改成正式雲端部署版本。

### 舊版 Streamlit 介面

專案仍保留 `app.py`,但新版自訂介面已不需要 Streamlit。若要使用舊版介面,需另外安裝
`streamlit` 與 `streamlit-searchbox`,再執行:

```bash
streamlit run app.py
```

如果想啟用 Claude API 做更準確的新聞情緒判斷(而不是陽春的關鍵字比對),
額外設定環境變數:

```bash
export ANTHROPIC_API_KEY="你的 API Key"        # macOS/Linux
setx ANTHROPIC_API_KEY "你的 API Key"           # Windows
```

沒有設定也完全可以正常運作,只是新聞情緒判斷會用內建的關鍵字模式(較粗略但免費、不需要額外設定)。

## 使用方式

### 1. 分析一支股票,產生建議

```bash
python main.py analyze 2330.TW
```

台股代號要加 `.TW`(上市)或 `.TWO`(上櫃),美股直接用代號,例如:

```bash
python main.py analyze AAPL
python main.py analyze TSLA
python main.py analyze 7203.T       # 日本 Toyota
python main.py analyze 005930.KS    # 韓國 Samsung Electronics
python main.py analyze ASML.AS      # 荷蘭 ASML
```

執行後會:
- 在終端機印出技術面 / ML面 / 新聞面各自的分數,以及最終買賣觀望百分比
- 在終端機印出 K線型態、籌碼/量價訊號,以及隔日/5日/20日上漲機率
- 把這次建議與手續費內扣設定存進 `data/advisor_records.db`
- 在 `reports/` 資料夾產生一份互動式 HTML 報告(K線圖+指標+新聞列表+建議),用瀏覽器打開即可

若要調整命令列模式的交易成本,可使用:

```bash
python main.py analyze 2330.TW --buy-fee-rate 0.1425 --sell-fee-rate 0.1425 --sell-tax-rate 0.3
python main.py analyze AAPL --no-fee-deduct
```

### 2. 換不同策略分析(權重不同)

`config.py` 裡預先設定了幾組策略,網頁會顯示中文名稱,命令列也可以直接使用中文策略名:

```bash
python main.py analyze 2330.TW --strategy 新聞導向策略
python main.py analyze 2330.TW --strategy 技術導向策略
python main.py analyze 2330.TW --strategy 長期預測策略
```

### 3. 回顧歷史建議的實際結果

每筆建議都有一個「持有天數」(策略設定裡的 `holding_days`),
到期後執行以下指令,程式會自動查詢最新股價,計算這次建議的實際報酬率、判斷方向對不對:

```bash
python main.py update
```

建議每天或每隔幾天執行一次 `update`,讓歷史紀錄持續累積更新。

### 4. 查看策略長期績效統計

累積一定數量的已回顧紀錄後,可以看整體表現:

```bash
python main.py stats
```

會列出各策略的:
- 已回顧建議數
- 方向判斷勝率(買入/賣出建議中,猜對漲跌方向的比例;觀望不計入)
- 平均價格漲跌、方向毛報酬、扣費後報酬
- 長期預測準確率比較(依策略)

長期下來就能看出哪一組策略(權重組合)表現最好,再考慮把 `config.py` 裡的權重調整成表現最好的那組。

### 5. 查看某股票的歷史建議紀錄

```bash
python main.py history 2330.TW
```

## 調整技術指標權重 / 新增策略

打開 `config.py`,可以直接調整現有策略的權重,或是新增一組全新的策略:

```python
STRATEGIES = {
    "my_strategy": {
        "technical_weight": 0.5,
        "ml_weight": 0.2,
        "news_weight": 0.3,
        "holding_days": 7,
    },
}
```

如果你之後決定好要用哪些額外的技術指標(例如 KD、成交量爆量、乖離率等),
可以到 `indicators.py` 新增計算函式,再到 `decision.py` 的 `technical_score()` 裡加入對應規則。
這個架構的目的就是讓你**只改規則,不用動整個系統**。

## 常見問題

**Q: 新聞抓不到東西怎麼辦?**
A: 目前用 `yfinance` 內建的新聞功能,是 Yahoo Finance 自己整理的新聞,不一定每支股票都有,
   也可能因為 Yahoo 改版而失效。若常常抓不到,可以考慮改接 NewsAPI 等專門的新聞 API(需要另外申請 Key)。

**Q: 為什麼同一支股票,不同時間執行 analyze,分數會不一樣?**
A: 因為股價、新聞都是即時變動的,每次執行都是用「當下」最新的資料重新分析,這是正常現象。

**Q: `update` 說沒有到期的紀錄,是不是壞了?**
A: 沒有壞,是因為預設持有天數是 5~10 個交易日,建議產生之後要等那麼多天才會「到期」可回顧。
   剛開始使用的前幾天執行 `update` 本來就不會有結果。

**Q: 買入/觀望/賣出的百分比是怎麼算出來的?**
A: 是一個**可解釋的規則式模型**,不是黑箱 ML:先把技術面、ML面、新聞面各自轉成 -1(偏空)到
   +1(偏多)的分數,依策略權重加權平均成一個綜合分數,再用這個分數離「買入(+1)/觀望(0)/賣出(-1)」
   三個錨點的距離,算出對應的百分比。分數越極端,建議就越傾向該方向。
