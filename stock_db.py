"""
stock_db.py
股票代號資料庫 + 搜尋函式

收錄範圍(截至維護時的最佳整理,非即時全量清單):
    - 台股上市主要個股 (.TW)
    - 台股上櫃主要個股 (.TWO)
    - 常見台股 ETF (.TW)
    - 美股熱門個股與 ETF (無需代號後綴)

⚠️ 興櫃股票由於大多沒有被 Yahoo Finance 收錄,即使列入資料庫也常常
   抓不到股價資料,因此本資料庫暫不收錄。若你需要分析特定興櫃股票,
   建議先確認 Yahoo Finance 是否有其資料。

想要新增/修改股票,直接在下方 STOCK_DB 這個 list 裡加一行即可,格式為:
    (顯示代號, yfinance用代號, 中文/英文名稱, 市場標籤)

之後想加更多檔,也可以把想加的代號名稱丟給 Claude,請它幫你直接加進這個檔案。
"""

# (顯示代號, yfinance代號, 名稱, 市場標籤)
STOCK_DB = [
    # ---------------- 台股上市 (.TW) ----------------
    ("2330", "2330.TW", "台積電", "上市"),
    ("2317", "2317.TW", "鴻海", "上市"),
    ("2454", "2454.TW", "聯發科", "上市"),
    ("2308", "2308.TW", "台達電", "上市"),
    ("2382", "2382.TW", "廣達", "上市"),
    ("2412", "2412.TW", "中華電", "上市"),
    ("2881", "2881.TW", "富邦金", "上市"),
    ("2882", "2882.TW", "國泰金", "上市"),
    ("2886", "2886.TW", "兆豐金", "上市"),
    ("2891", "2891.TW", "中信金", "上市"),
    ("2884", "2884.TW", "玉山金", "上市"),
    ("2885", "2885.TW", "元大金", "上市"),
    ("2892", "2892.TW", "第一金", "上市"),
    ("2880", "2880.TW", "華南金", "上市"),
    ("2883", "2883.TW", "開發金", "上市"),
    ("2887", "2887.TW", "台新金", "上市"),
    ("2890", "2890.TW", "永豐金", "上市"),
    ("5880", "5880.TW", "合庫金", "上市"),
    ("2801", "2801.TW", "彰銀", "上市"),
    ("1301", "1301.TW", "台塑", "上市"),
    ("1303", "1303.TW", "南亞", "上市"),
    ("1326", "1326.TW", "台化", "上市"),
    ("6505", "6505.TW", "台塑化", "上市"),
    ("1216", "1216.TW", "統一", "上市"),
    ("2002", "2002.TW", "中鋼", "上市"),
    ("2207", "2207.TW", "和泰車", "上市"),
    ("2603", "2603.TW", "長榮", "上市"),
    ("2609", "2609.TW", "陽明", "上市"),
    ("2615", "2615.TW", "萬海", "上市"),
    ("3008", "3008.TW", "大立光", "上市"),
    ("2303", "2303.TW", "聯電", "上市"),
    ("2379", "2379.TW", "瑞昱", "上市"),
    ("2357", "2357.TW", "華碩", "上市"),
    ("2377", "2377.TW", "微星", "上市"),
    ("2395", "2395.TW", "研華", "上市"),
    ("2408", "2408.TW", "南亞科", "上市"),
    ("2409", "2409.TW", "友達", "上市"),
    ("2474", "2474.TW", "可成", "上市"),
    ("2492", "2492.TW", "華新科", "上市"),
    ("2618", "2618.TW", "長榮航", "上市"),
    ("2610", "2610.TW", "華航", "上市"),
    ("1101", "1101.TW", "台泥", "上市"),
    ("1102", "1102.TW", "亞泥", "上市"),
    ("1590", "1590.TW", "亞德客-KY", "上市"),
    ("1476", "1476.TW", "儒鴻", "上市"),
    ("2201", "2201.TW", "裕隆", "上市"),
    ("2323", "2323.TW", "中環", "上市"),
    ("2324", "2324.TW", "仁寶", "上市"),
    ("2327", "2327.TW", "國巨", "上市"),
    ("2354", "2354.TW", "鴻準", "上市"),
    ("2356", "2356.TW", "英業達", "上市"),
    ("2360", "2360.TW", "致茂", "上市"),
    ("2371", "2371.TW", "大同", "上市"),
    ("2376", "2376.TW", "技嘉", "上市"),
    ("2385", "2385.TW", "群光", "上市"),
    ("2392", "2392.TW", "正崴", "上市"),
    ("2401", "2401.TW", "凌陽", "上市"),
    ("2404", "2404.TW", "漢唐", "上市"),
    ("2439", "2439.TW", "美律", "上市"),
    ("2449", "2449.TW", "京元電子", "上市"),
    ("2451", "2451.TW", "創見", "上市"),
    ("2455", "2455.TW", "全新", "上市"),
    ("2458", "2458.TW", "義隆", "上市"),
    ("2481", "2481.TW", "強茂", "上市"),
    ("3231", "3231.TW", "緯創", "上市"),
    ("3711", "3711.TW", "日月光投控", "上市"),
    ("3037", "3037.TW", "欣興", "上市"),
    ("3045", "3045.TW", "台灣大", "上市"),
    ("3034", "3034.TW", "聯詠", "上市"),
    ("3661", "3661.TW", "世芯-KY", "上市"),
    ("3443", "3443.TW", "創意", "上市"),
    ("3529", "3529.TW", "力旺", "上市"),
    ("3533", "3533.TW", "嘉澤", "上市"),
    ("3653", "3653.TW", "健策", "上市"),
    ("4904", "4904.TW", "遠傳", "上市"),
    ("4938", "4938.TW", "和碩", "上市"),
    ("4958", "4958.TW", "臻鼎-KY", "上市"),
    ("6415", "6415.TW", "矽力*-KY", "上市"),
    ("6488", "6488.TW", "環球晶", "上市"),
    ("6669", "6669.TW", "緯穎", "上市"),
    ("6770", "6770.TW", "力積電", "上市"),
    ("8046", "8046.TW", "南電", "上市"),
    ("8069", "8069.TW", "元太", "上市"),
    ("9910", "9910.TW", "豐泰", "上市"),
    ("9921", "9921.TW", "巨大", "上市"),
    ("9945", "9945.TW", "潤泰新", "上市"),
    ("1102", "1102.TW", "亞泥", "上市"),
    ("2027", "2027.TW", "大成鋼", "上市"),
    ("2105", "2105.TW", "正新", "上市"),
    ("2049", "2049.TW", "上銀", "上市"),
    ("1504", "1504.TW", "東元", "上市"),
    ("1513", "1513.TW", "中興電", "上市"),
    ("1519", "1519.TW", "华城", "上市"),
    ("1519", "1519.TW", "華城", "上市"),
    ("2059", "2059.TW", "川湖", "上市"),
    ("6216", "6216.TW", "居易", "上市"),
    ("8464", "8464.TW", "億豐", "上市"),
    ("9904", "9904.TW", "寶成", "上市"),
    ("9941", "9941.TW", "裕融", "上市"),
    ("2912", "2912.TW", "統一超", "上市"),
    ("2915", "2915.TW", "潤泰全", "上市"),
    ("1229", "1229.TW", "聯華", "上市"),
    ("1210", "1210.TW", "大成", "上市"),
    ("1227", "1227.TW", "佳格", "上市"),
    ("9945", "9945.TW", "潤泰新", "上市"),
    ("5871", "5871.TW", "中租-KY", "上市"),
    ("5876", "5876.TW", "上海商銀", "上市"),
    ("2887", "2887.TW", "台新金", "上市"),
    ("6others", "6others", "placeholder", "上市"),  # will be removed below

    # ---------------- 台股上櫃 (.TWO) ----------------
    ("6547", "6547.TWO", "高端疫苗", "上櫃"),
    ("5347", "5347.TWO", "世界先進", "上市"),
    ("3105", "3105.TWO", "穩懋", "上櫃"),
    ("6180", "6180.TWO", "橘子", "上櫃"),
    ("4991", "4991.TWO", "環宇-KY", "上櫃"),
    ("6491", "6491.TWO", "晶碩", "上櫃"),
    ("8299", "8299.TWO", "群聯", "上市"),
    ("3227", "3227.TWO", "原相", "上櫃"),

    # ---------------- 台股 ETF (.TW) ----------------
    ("0050", "0050.TW", "元大台灣50", "ETF"),
    ("0056", "0056.TW", "元大高股息", "ETF"),
    ("006208", "006208.TW", "富邦台50", "ETF"),
    ("00878", "00878.TW", "國泰永續高股息", "ETF"),
    ("00919", "00919.TW", "群益台灣精選高息", "ETF"),
    ("00929", "00929.TW", "復華台灣科技優息", "ETF"),
    ("00713", "00713.TW", "元大台灣高息低波", "ETF"),
    ("00646", "00646.TW", "元大S&P500", "ETF"),
    ("00757", "00757.TW", "統一FANG+", "ETF"),
    ("00830", "00830.TW", "國泰費城半導體", "ETF"),
    ("00881", "00881.TW", "國泰台灣5G+", "ETF"),
    ("00892", "00892.TW", "富邦台灣半導體", "ETF"),
    ("00900", "00900.TW", "富邦特選高股息30", "ETF"),
    ("006204", "006204.TW", "永豐臺灣加權", "ETF"),
    ("00940", "00940.TW", "元大台灣價值高息", "ETF"),
    ("00631L", "00631L.TW", "元大台灣50正2", "ETF"),
    ("00632R", "00632R.TW", "元大台灣50反1", "ETF"),
    ("00631L", "00631L.TW", "元大台灣50正2", "ETF"),

    # ---------------- 美股熱門個股 ----------------
    ("AAPL", "AAPL", "蘋果 Apple", "美股"),
    ("MSFT", "MSFT", "微軟 Microsoft", "美股"),
    ("GOOGL", "GOOGL", "Alphabet(Google) A股", "美股"),
    ("GOOG", "GOOG", "Alphabet(Google) C股", "美股"),
    ("AMZN", "AMZN", "亞馬遜 Amazon", "美股"),
    ("META", "META", "Meta(Facebook)", "美股"),
    ("TSLA", "TSLA", "特斯拉 Tesla", "美股"),
    ("NVDA", "NVDA", "輝達 Nvidia", "美股"),
    ("NFLX", "NFLX", "網飛 Netflix", "美股"),
    ("AMD", "AMD", "超微 AMD", "美股"),
    ("INTC", "INTC", "英特爾 Intel", "美股"),
    ("QCOM", "QCOM", "高通 Qualcomm", "美股"),
    ("AVGO", "AVGO", "博通 Broadcom", "美股"),
    ("ORCL", "ORCL", "甲骨文 Oracle", "美股"),
    ("CRM", "CRM", "Salesforce", "美股"),
    ("ADBE", "ADBE", "Adobe", "美股"),
    ("PYPL", "PYPL", "PayPal", "美股"),
    ("UBER", "UBER", "優步 Uber", "美股"),
    ("LYFT", "LYFT", "Lyft", "美股"),
    ("SNAP", "SNAP", "Snap", "美股"),
    ("PINS", "PINS", "Pinterest", "美股"),
    ("SPOT", "SPOT", "Spotify", "美股"),
    ("SQ", "SQ", "Block(前Square)", "美股"),
    ("SHOP", "SHOP", "Shopify", "美股"),
    ("BABA", "BABA", "阿里巴巴 Alibaba", "美股"),
    ("JD", "JD", "京東 JD.com", "美股"),
    ("PDD", "PDD", "拼多多 PDD", "美股"),
    ("NIO", "NIO", "蔚來汽車 NIO", "美股"),
    ("XPEV", "XPEV", "小鵬汽車 XPeng", "美股"),
    ("LI", "LI", "理想汽車 Li Auto", "美股"),
    ("F", "F", "福特 Ford", "美股"),
    ("GM", "GM", "通用汽車 GM", "美股"),
    ("DIS", "DIS", "迪士尼 Disney", "美股"),
    ("WMT", "WMT", "沃爾瑪 Walmart", "美股"),
    ("TGT", "TGT", "塔吉特 Target", "美股"),
    ("COST", "COST", "好市多 Costco", "美股"),
    ("HD", "HD", "家得寶 Home Depot", "美股"),
    ("LOW", "LOW", "勞氏 Lowe's", "美股"),
    ("MCD", "MCD", "麥當勞 McDonald's", "美股"),
    ("SBUX", "SBUX", "星巴克 Starbucks", "美股"),
    ("KO", "KO", "可口可樂 Coca-Cola", "美股"),
    ("PEP", "PEP", "百事 PepsiCo", "美股"),
    ("PG", "PG", "寶僑 Procter & Gamble", "美股"),
    ("JNJ", "JNJ", "嬌生 Johnson & Johnson", "美股"),
    ("PFE", "PFE", "輝瑞 Pfizer", "美股"),
    ("MRNA", "MRNA", "莫德納 Moderna", "美股"),
    ("UNH", "UNH", "聯合健康 UnitedHealth", "美股"),
    ("V", "V", "威士卡 Visa", "美股"),
    ("MA", "MA", "萬事達卡 Mastercard", "美股"),
    ("JPM", "JPM", "摩根大通 JPMorgan", "美股"),
    ("BAC", "BAC", "美國銀行 Bank of America", "美股"),
    ("GS", "GS", "高盛 Goldman Sachs", "美股"),
    ("MS", "MS", "摩根士丹利 Morgan Stanley", "美股"),
    ("WFC", "WFC", "富國銀行 Wells Fargo", "美股"),
    ("C", "C", "花旗 Citigroup", "美股"),
    ("BRK-B", "BRK-B", "波克夏海瑟威 Berkshire Hathaway", "美股"),
    ("XOM", "XOM", "埃克森美孚 ExxonMobil", "美股"),
    ("CVX", "CVX", "雪佛龍 Chevron", "美股"),
    ("BA", "BA", "波音 Boeing", "美股"),
    ("CAT", "CAT", "開拓重工 Caterpillar", "美股"),
    ("GE", "GE", "奇異 General Electric", "美股"),
    ("IBM", "IBM", "IBM", "美股"),
    ("CSCO", "CSCO", "思科 Cisco", "美股"),
    ("TXN", "TXN", "德州儀器 Texas Instruments", "美股"),
    ("MU", "MU", "美光 Micron", "美股"),
    ("AMAT", "AMAT", "應用材料 Applied Materials", "美股"),
    ("LRCX", "LRCX", "科林研發 Lam Research", "美股"),
    ("ASML", "ASML", "艾司摩爾 ASML", "美股"),
    ("TSM", "TSM", "台積電ADR TSMC", "美股"),
    ("SMCI", "SMCI", "美超微 Super Micro", "美股"),
    ("PLTR", "PLTR", "Palantir", "美股"),
    ("SNOW", "SNOW", "Snowflake", "美股"),
    ("CRWD", "CRWD", "CrowdStrike", "美股"),
    ("PANW", "PANW", "Palo Alto Networks", "美股"),
    ("NOW", "NOW", "ServiceNow", "美股"),
    ("ZM", "ZM", "Zoom", "美股"),
    ("DOCU", "DOCU", "DocuSign", "美股"),
    ("ABNB", "ABNB", "Airbnb", "美股"),
    ("DASH", "DASH", "DoorDash", "美股"),
    ("RIVN", "RIVN", "Rivian", "美股"),
    ("LCID", "LCID", "Lucid", "美股"),
    ("ARM", "ARM", "Arm Holdings", "美股"),

    # ---------------- 美股常見 ETF ----------------
    ("SPY", "SPY", "S&P 500 ETF", "美股ETF"),
    ("QQQ", "QQQ", "那斯達克100 ETF", "美股ETF"),
    ("VOO", "VOO", "Vanguard S&P 500 ETF", "美股ETF"),
    ("VTI", "VTI", "Vanguard 整體股市 ETF", "美股ETF"),
    ("DIA", "DIA", "道瓊工業 ETF", "美股ETF"),
    ("IWM", "IWM", "羅素2000 ETF", "美股ETF"),
    ("ARKK", "ARKK", "方舟創新 ETF", "美股ETF"),
]

# 移除建置時用的佔位資料
STOCK_DB = [row for row in STOCK_DB if row[0] != "6others"]

# ---------------- 國際市場:日本 / 韓國 / 歐洲 ----------------
# Yahoo Finance 的日股常用 .T,韓國上市常用 .KS、KOSDAQ 常用 .KQ,
# 歐洲各交易所依國家有不同後綴(.L/.DE/.PA/.AS/.SW/.MI/.MC)。
INTERNATIONAL_STOCKS = [
    # 日本
    ("7203", "7203.T", "Toyota Motor 豐田汽車", "日本"),
    ("6758", "6758.T", "Sony Group 索尼", "日本"),
    ("9984", "9984.T", "SoftBank Group 軟銀集團", "日本"),
    ("8306", "8306.T", "Mitsubishi UFJ 三菱日聯", "日本"),
    ("9432", "9432.T", "NTT 日本電信電話", "日本"),
    ("6861", "6861.T", "Keyence 基恩斯", "日本"),
    ("7974", "7974.T", "Nintendo 任天堂", "日本"),
    ("8035", "8035.T", "Tokyo Electron 東京威力科創", "日本"),
    ("4063", "4063.T", "Shin-Etsu 信越化學", "日本"),
    ("9983", "9983.T", "Fast Retailing 迅銷", "日本"),
    ("6098", "6098.T", "Recruit Holdings", "日本"),
    ("6501", "6501.T", "Hitachi 日立", "日本"),

    # 韓國
    ("005930", "005930.KS", "Samsung Electronics 三星電子", "韓國"),
    ("000660", "000660.KS", "SK Hynix SK海力士", "韓國"),
    ("035420", "035420.KS", "NAVER", "韓國"),
    ("035720", "035720.KS", "Kakao", "韓國"),
    ("005380", "005380.KS", "Hyundai Motor 現代汽車", "韓國"),
    ("000270", "000270.KS", "Kia 起亞", "韓國"),
    ("051910", "051910.KS", "LG Chem LG化學", "韓國"),
    ("373220", "373220.KS", "LG Energy Solution", "韓國"),
    ("207940", "207940.KS", "Samsung Biologics 三星生物製劑", "韓國"),
    ("068270", "068270.KS", "Celltrion 賽特瑞恩", "韓國"),
    ("247540", "247540.KQ", "Ecopro BM", "韓國"),

    # 英國
    ("HSBA", "HSBA.L", "HSBC Holdings 匯豐控股", "英國"),
    ("SHEL", "SHEL.L", "Shell 殼牌", "英國"),
    ("BP", "BP.L", "BP", "英國"),
    ("AZN", "AZN.L", "AstraZeneca 阿斯特捷利康", "英國"),
    ("GSK", "GSK.L", "GSK 葛蘭素史克", "英國"),
    ("ULVR", "ULVR.L", "Unilever 聯合利華", "英國"),
    ("RIO", "RIO.L", "Rio Tinto 力拓", "英國"),

    # 德國
    ("SAP", "SAP.DE", "SAP", "德國"),
    ("SIE", "SIE.DE", "Siemens 西門子", "德國"),
    ("ALV", "ALV.DE", "Allianz 安聯", "德國"),
    ("BMW", "BMW.DE", "BMW", "德國"),
    ("MBG", "MBG.DE", "Mercedes-Benz Group", "德國"),
    ("VOW3", "VOW3.DE", "Volkswagen 福斯汽車", "德國"),
    ("DTE", "DTE.DE", "Deutsche Telekom 德國電信", "德國"),
    ("BAS", "BAS.DE", "BASF 巴斯夫", "德國"),

    # 法國
    ("MC", "MC.PA", "LVMH", "法國"),
    ("OR", "OR.PA", "L'Oreal 萊雅", "法國"),
    ("AIR", "AIR.PA", "Airbus 空中巴士", "法國"),
    ("TTE", "TTE.PA", "TotalEnergies 道達爾能源", "法國"),
    ("SAN", "SAN.PA", "Sanofi 賽諾菲", "法國"),
    ("BNP", "BNP.PA", "BNP Paribas 法國巴黎銀行", "法國"),
    ("AI", "AI.PA", "Air Liquide 液化空氣", "法國"),

    # 荷蘭 / 瑞士 / 義大利 / 西班牙
    ("ASML", "ASML.AS", "ASML Holding", "荷蘭"),
    ("ADYEN", "ADYEN.AS", "Adyen", "荷蘭"),
    ("INGA", "INGA.AS", "ING Group 荷蘭國際集團", "荷蘭"),
    ("NESN", "NESN.SW", "Nestle 雀巢", "瑞士"),
    ("NOVN", "NOVN.SW", "Novartis 諾華", "瑞士"),
    ("ROG", "ROG.SW", "Roche 羅氏", "瑞士"),
    ("UBSG", "UBSG.SW", "UBS 瑞銀", "瑞士"),
    ("ZURN", "ZURN.SW", "Zurich Insurance 蘇黎世保險", "瑞士"),
    ("ENEL", "ENEL.MI", "Enel 義大利國家電力", "義大利"),
    ("ENI", "ENI.MI", "Eni 義大利埃尼", "義大利"),
    ("ISP", "ISP.MI", "Intesa Sanpaolo 義大利聯合聖保羅銀行", "義大利"),
    ("SAN", "SAN.MC", "Banco Santander 桑坦德銀行", "西班牙"),
    ("BBVA", "BBVA.MC", "BBVA 西班牙對外銀行", "西班牙"),
    ("ITX", "ITX.MC", "Inditex", "西班牙"),

    # 國際 ETF
    ("EWJ", "EWJ", "iShares MSCI Japan ETF", "日本ETF"),
    ("EWY", "EWY", "iShares MSCI South Korea ETF", "韓國ETF"),
    ("VGK", "VGK", "Vanguard FTSE Europe ETF", "歐洲ETF"),
    ("FEZ", "FEZ", "SPDR EURO STOXX 50 ETF", "歐洲ETF"),
]

STOCK_DB.extend(INTERNATIONAL_STOCKS)

MARKET_OPTIONS = ["全部市場", "台股", "美股", "日本", "韓國", "歐洲"]
MARKET_GROUPS = {
    "全部市場": None,
    "台股": {"上市", "上櫃", "ETF"},
    "美股": {"美股", "美股ETF"},
    "日本": {"日本", "日本ETF"},
    "韓國": {"韓國", "韓國ETF"},
    "歐洲": {"英國", "德國", "法國", "荷蘭", "瑞士", "義大利", "西班牙", "歐洲ETF"},
}

# 去除重複(同代號同市場只留一筆)
_seen = set()
_deduped = []
for row in STOCK_DB:
    key = (row[0], row[3])
    if key not in _seen:
        _seen.add(key)
        _deduped.append(row)
STOCK_DB = _deduped


def search_stocks(query: str, limit: int = 10, market_filter: str = "全部市場"):
    """
    依輸入字串搜尋股票資料庫。
    支援:代號開頭比對(例如 "23" 會比對出 2330、2317、2327...)、
         名稱包含比對(例如 "台積" 會比對出台積電)、
         美股代號不分大小寫比對(例如 "aapl" 會比對出 AAPL)。

    回傳: list of (顯示代號, yfinance代號, 名稱, 市場標籤),依相關性排序,最多 limit 筆。
    """
    q = (query or "").strip()
    if not q:
        return []

    q_lower = q.lower()
    allowed_markets = MARKET_GROUPS.get(market_filter)
    matched = []
    for code, yf_code, name, market in STOCK_DB:
        if allowed_markets is not None and market not in allowed_markets:
            continue
        code_lower = code.lower()
        yf_code_lower = yf_code.lower()
        name_lower = name.lower()
        if code_lower.startswith(q_lower):
            rank = 0
        elif yf_code_lower.startswith(q_lower):
            rank = 0
        elif name_lower.startswith(q_lower):
            rank = 1
        elif q_lower in code_lower:
            rank = 2
        elif q_lower in yf_code_lower:
            rank = 2
        elif q_lower in name_lower:
            rank = 3
        else:
            continue
        matched.append((rank, code, yf_code, name, market))

    matched.sort(key=lambda x: (x[0], x[1]))
    return [(code, yf_code, name, market) for _, code, yf_code, name, market in matched[:limit]]


def list_stocks(market_filter: str = "全部市場"):
    """回傳指定市場下的股票清單,供原生選單顯示使用。"""
    allowed_markets = MARKET_GROUPS.get(market_filter)
    rows = [
        row for row in STOCK_DB
        if allowed_markets is None or row[3] in allowed_markets
    ]
    return sorted(rows, key=lambda row: (row[3], row[0]))
