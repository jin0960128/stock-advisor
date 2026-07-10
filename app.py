# update
"""
app.py
股票分析建議系統 —— 網頁介面(用 Streamlit 打造)

執行方式:
    streamlit run app.py

執行後會自動在瀏覽器打開一個網頁,不需要碰終端機指令,
輸入股票代號、按按鈕就能看到分析結果、K線圖、新聞與建議。
"""
import html
import warnings

import pandas as pd
import streamlit as st
import yfinance as yf

import config
import storage
try:
    from stock_db import MARKET_OPTIONS, list_stocks
except ImportError:
    from stock_db import MARKET_GROUPS, MARKET_OPTIONS, STOCK_DB

    def list_stocks(market_filter: str = "全部市場"):
        allowed_markets = MARKET_GROUPS.get(market_filter)
        rows = [
            row for row in STOCK_DB
            if allowed_markets is None or row[3] in allowed_markets
        ]
        return sorted(rows, key=lambda row: (row[3], row[0]))
from indicators import add_all_indicators
from model import predict_horizons
from news import analyze_news_sentiment
from decision import technical_score, ml_score, build_recommendation, candlestick_score, chip_score
from report import build_figure

warnings.filterwarnings("ignore")

st.set_page_config(page_title="股票分析建議系統", page_icon="📈", layout="wide")


def _inject_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg: #f5f7fb;
            --surface: #ffffff;
            --surface-muted: #f8fafc;
            --border: #d9e2ec;
            --text: #17212b;
            --muted: #667085;
            --teal: #17717b;
            --teal-soft: #e8f5f6;
            --green: #14804a;
            --green-soft: #e7f6ee;
            --red: #b42318;
            --red-soft: #fdeceb;
            --amber: #b7791f;
            --amber-soft: #fff6db;
            --blue: #2458a6;
            --blue-soft: #edf4ff;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        .app-header {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px 24px;
            margin-bottom: 18px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        }

        .app-header__row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 18px;
        }

        .app-eyebrow {
            color: var(--teal);
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .app-title {
            color: var(--text);
            font-size: 1.85rem;
            font-weight: 800;
            margin: 0;
            letter-spacing: 0;
            line-height: 1.2;
        }

        .app-note {
            color: var(--muted);
            font-size: 0.94rem;
            margin-top: 8px;
            margin-bottom: 0;
            line-height: 1.55;
        }

        .app-status {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: flex-end;
            min-width: 220px;
        }

        .app-status span,
        .score-pill,
        .signal-tag {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--surface-muted);
            color: var(--text);
            font-size: 0.84rem;
            font-weight: 650;
            padding: 7px 10px;
            white-space: nowrap;
        }

        div[data-testid="stTabs"] button {
            border-radius: 8px 8px 0 0;
            padding: 10px 18px;
            font-weight: 700;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: var(--teal);
            border-bottom-color: var(--teal);
        }

        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-size: 0.86rem;
            font-weight: 700;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text);
            font-weight: 800;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
        div[data-testid="stTextInput"] input,
        div[data-testid="stNumberInput"] input {
            min-height: 42px;
            border-radius: 8px;
            border-color: var(--border);
            background: var(--surface-muted);
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] input {
            background: transparent;
        }

        div[data-testid="stSelectbox"] [data-baseweb="select"] > div:hover,
        div[data-testid="stTextInput"] input:hover,
        div[data-testid="stNumberInput"] input:hover {
            border-color: #a9b8c9;
        }

        .stButton > button {
            border-radius: 8px;
            border: 1px solid var(--teal);
            background: var(--teal);
            color: #fff;
            font-weight: 750;
            min-height: 42px;
            box-shadow: 0 8px 18px rgba(23, 113, 123, 0.18);
        }

        .stButton > button:hover {
            border-color: #125f68;
            background: #125f68;
            color: #fff;
        }

        .stButton > button:disabled {
            border-color: var(--border);
            background: #e5e7eb;
            color: #9ca3af;
            box-shadow: none;
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--border);
        }

        .section-title {
            color: var(--text);
            font-size: 1.08rem;
            font-weight: 800;
            margin: 22px 0 10px;
            letter-spacing: 0;
        }

        .decision-banner {
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--surface);
            padding: 16px 18px;
            margin: 14px 0 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        }

        .decision-banner.buy {
            border-left: 5px solid var(--green);
            background: var(--green-soft);
        }

        .decision-banner.sell {
            border-left: 5px solid var(--red);
            background: var(--red-soft);
        }

        .decision-banner.hold {
            border-left: 5px solid var(--amber);
            background: var(--amber-soft);
        }

        .decision-kicker {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 800;
            margin-bottom: 2px;
        }

        .decision-action {
            color: var(--text);
            font-size: 1.45rem;
            font-weight: 850;
            line-height: 1.2;
        }

        .decision-meta {
            color: var(--muted);
            font-size: 0.9rem;
            text-align: right;
        }

        .score-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0 12px;
        }

        .score-pill.positive {
            color: var(--green);
            border-color: #b7e3cc;
            background: var(--green-soft);
        }

        .score-pill.negative {
            color: var(--red);
            border-color: #fac7c2;
            background: var(--red-soft);
        }

        .score-pill.neutral {
            color: var(--blue);
            border-color: #c8daf8;
            background: var(--blue-soft);
        }

        .signal-panel {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 16px;
            min-height: 142px;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
        }

        .signal-panel__head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            margin-bottom: 10px;
        }

        .signal-panel__title {
            font-size: 0.98rem;
            font-weight: 800;
            color: var(--text);
        }

        .signal-list {
            display: grid;
            gap: 8px;
        }

        .signal-item {
            color: var(--text);
            background: var(--surface-muted);
            border: 1px solid #edf1f6;
            border-radius: 8px;
            padding: 8px 10px;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .news-row {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px 14px;
            margin-bottom: 8px;
            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.035);
        }

        .news-row a {
            color: var(--text);
            font-weight: 700;
            text-decoration: none;
        }

        .news-row a:hover {
            color: var(--teal);
            text-decoration: underline;
        }

        .news-meta {
            color: var(--muted);
            font-size: 0.84rem;
            margin-top: 4px;
        }

        .stDataFrame,
        div[data-testid="stDataFrame"] {
            border-radius: 8px;
            overflow: hidden;
        }

        @media (max-width: 760px) {
            .app-header__row,
            .decision-banner {
                flex-direction: column;
                align-items: flex-start;
            }
            .app-status,
            .decision-meta {
                justify-content: flex-start;
                text-align: left;
            }
            .app-title {
                font-size: 1.45rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header():
    st.markdown(
        """
        <div class="app-header">
            <div class="app-header__row">
                <div>
                    <div class="app-eyebrow">Investment Research Console</div>
                    <h1 class="app-title">股票分析決策系統</h1>
                    <p class="app-note">本工具僅供學習與研究參考，任何輸出都不構成投資建議。</p>
                </div>
                <div class="app-status">
                    <span>技術面</span>
                    <span>K線</span>
                    <span>籌碼</span>
                    <span>ML</span>
                    <span>新聞</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _tone(score: float) -> str:
    if score >= 0.2:
        return "positive"
    if score <= -0.2:
        return "negative"
    return "neutral"


def _score_pill(label: str, score: float) -> str:
    return (
        f'<span class="score-pill {_tone(score)}">'
        f'{html.escape(label)} <strong>{score:+.2f}</strong>'
        "</span>"
    )


def _render_score_strip(recommendation: dict):
    pills = [
        _score_pill("技術面", recommendation["technical_score"]),
        _score_pill("K線", recommendation["kline_score"]),
        _score_pill("籌碼", recommendation["chip_score"]),
        _score_pill("ML", recommendation["ml_score"]),
        _score_pill("新聞", recommendation["news_score"]),
        _score_pill("綜合", recommendation["final_score"]),
    ]
    st.markdown(f'<div class="score-strip">{"".join(pills)}</div>', unsafe_allow_html=True)


def _render_decision_banner(recommendation: dict, strategy_label: str, holding_days: int):
    action_class = {
        "買入": "buy",
        "賣出": "sell",
        "觀望": "hold",
    }.get(recommendation["top_action"], "hold")
    st.markdown(
        f"""
        <div class="decision-banner {action_class}">
            <div>
                <div class="decision-kicker">最可能操作</div>
                <div class="decision-action">{html.escape(recommendation["top_action"])}</div>
            </div>
            <div class="decision-meta">
                {html.escape(strategy_label)} · 持有 {holding_days} 個交易日<br>
                綜合分數 {recommendation["final_score"]:+.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_section_title(title: str):
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)


def _render_signal_panel(title: str, score: float, signals: list):
    signal_items = "".join(
        f'<div class="signal-item">{html.escape(str(signal))}</div>'
        for signal in signals[:5]
    )
    st.markdown(
        f"""
        <div class="signal-panel">
            <div class="signal-panel__head">
                <div class="signal-panel__title">{html.escape(title)}</div>
                <span class="signal-tag">{score:+.2f}</span>
            </div>
            <div class="signal-list">{signal_items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_news_item(item: dict):
    score = item.get("score", 0)
    tone = _tone(score)
    title = html.escape(str(item.get("title", "未命名新聞")))
    link = html.escape(str(item.get("link", "#")))
    publisher = html.escape(str(item.get("publisher", "")))
    st.markdown(
        f"""
        <div class="news-row">
            <div>
                <span class="score-pill {tone}">{score:+.2f}</span>
                <a href="{link}" target="_blank">{title}</a>
            </div>
            <div class="news-meta">{publisher}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_inject_theme()
_render_header()

tab_analyze, tab_update, tab_stats, tab_history = st.tabs(
    ["🔍 分析", "🔄 回顧更新", "📊 績效統計", "🕘 歷史紀錄"]
)


def _stock_label(stock: tuple) -> str:
    if stock is None:
        return ""
    code, yf_code, name, market = stock
    return f"{code}　{name}　［{market}］"


def _strategy_label(strategy_name: str) -> str:
    return config.get_strategy_label(strategy_name)


# ============ 分析頁 ============
with tab_analyze:
    _render_section_title("分析條件")
    col_market, col1, col2, col3 = st.columns([1, 2, 1, 1])
    with col_market:
        market_filter = st.selectbox("市場", MARKET_OPTIONS, index=0)
    with col1:
        stock_option = st.selectbox(
            "股票代碼",
            list_stocks(market_filter),
            index=None,
            placeholder="選擇或搜尋股票代碼",
            format_func=_stock_label,
            key=f"ticker_select_{market_filter}",
        )
        ticker = stock_option[1] if stock_option else ""
    with col2:
        strategy_name = st.selectbox(
            "使用策略",
            list(config.STRATEGIES.keys()),
            format_func=_strategy_label,
        )
    with col3:
        period_options = config.PRICE_HISTORY_PERIOD_OPTIONS
        period_labels = config.PRICE_HISTORY_PERIOD_LABELS
        history_period = st.selectbox(
            "歷史資料範圍",
            period_options,
            index=period_options.index(config.PRICE_HISTORY_PERIOD)
            if config.PRICE_HISTORY_PERIOD in period_options else 0,
            format_func=lambda p: period_labels.get(p, p),
        )

    with st.expander("圖表顯示設定", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            show_sma20 = st.checkbox("20日均線", value=True)
            show_sma60 = st.checkbox("60日均線", value=True)
        with c2:
            show_bb = st.checkbox("布林通道", value=True)
            show_volume = st.checkbox("成交量", value=True)
        with c3:
            show_volume_ma = st.checkbox("成交量均量", value=True, disabled=not show_volume)
            show_rsi = st.checkbox("RSI 指標", value=True)
        with c4:
            show_macd = st.checkbox("MACD 指標", value=True)

    with st.expander("持有紀錄手續費內扣設定", expanded=False):
        fee_deducted = st.checkbox(
            "回顧報酬率內扣交易成本",
            value=config.DEFAULT_FEE_DEDUCTED,
            help="產生持有紀錄時保存此設定,到期回顧會用同一組費率計算扣費後報酬。",
        )
        f1, f2, f3 = st.columns(3)
        with f1:
            buy_fee_rate = st.number_input(
                "買進手續費(%)", min_value=0.0, max_value=5.0,
                value=float(config.DEFAULT_BUY_FEE_RATE), step=0.001, format="%.4f",
            )
        with f2:
            sell_fee_rate = st.number_input(
                "賣出手續費(%)", min_value=0.0, max_value=5.0,
                value=float(config.DEFAULT_SELL_FEE_RATE), step=0.001, format="%.4f",
            )
        with f3:
            sell_tax_rate = st.number_input(
                "賣出交易稅/其他成本(%)", min_value=0.0, max_value=5.0,
                value=float(config.DEFAULT_SELL_TAX_RATE), step=0.001, format="%.4f",
            )

    analyze_clicked = st.button("開始分析", type="primary", disabled=not ticker)

    if analyze_clicked:
        try:
            with st.spinner("下載股價資料並計算技術指標..."):
                raw = yf.download(
                    ticker, period=history_period,
                    progress=False, auto_adjust=True,
                )
                if raw.empty:
                    st.error(f"無法取得 {ticker} 的股價資料,請確認代號是否正確。")
                    st.stop()
                if isinstance(raw.columns, pd.MultiIndex):
                    raw.columns = raw.columns.get_level_values(0)
                df = add_all_indicators(raw)

            tech_score_val = technical_score(df)
            kline_score_val, kline_signals = candlestick_score(df)
            chip_score_val, chip_signals = chip_score(df)

            with st.spinner("訓練多期間機器學習模型..."):
                horizon_predictions = predict_horizons(
                    df, horizons=config.PREDICTION_HORIZONS.keys()
                )
                day1_prediction = horizon_predictions.get(1, {})
                if day1_prediction.get("up_probability") is not None:
                    up_prob = day1_prediction["up_probability"]
                    acc = day1_prediction["accuracy"]
                    ml_score_val = ml_score(up_prob)
                else:
                    acc, up_prob = None, None
                    ml_score_val = 0.0

            with st.spinner("搜尋近期新聞並分析情緒..."):
                news_score_val, news_items = analyze_news_sentiment(ticker)

            strategy = config.STRATEGIES[strategy_name]
            strategy_label = config.get_strategy_label(strategy_name)
            recommendation = build_recommendation(
                tech_score_val, ml_score_val, news_score_val, strategy,
                kline_score_val=kline_score_val, chip_score_val=chip_score_val,
            )

            latest_price = float(df["Close"].iloc[-1])
            record_id = storage.save_recommendation(
                ticker, strategy_name, latest_price, recommendation, strategy["holding_days"],
                fee_deducted=fee_deducted,
                buy_fee_rate=buy_fee_rate,
                sell_fee_rate=sell_fee_rate,
                sell_tax_rate=sell_tax_rate,
            )

            st.success(
                f"分析完成,已記錄本次建議(編號 #{record_id}),"
                f"使用「{strategy_label}」,{strategy['holding_days']} 個交易日後可到「回顧更新」頁查看結果。"
            )

            # --- 建議摘要 ---
            _render_section_title("建議摘要")
            m1, m2, m3 = st.columns(3)
            m1.metric("買入", f"{recommendation['buy_pct']}%")
            m2.metric("觀望", f"{recommendation['hold_pct']}%")
            m3.metric("賣出", f"{recommendation['sell_pct']}%")

            _render_decision_banner(recommendation, strategy_label, strategy["holding_days"])
            _render_score_strip(recommendation)

            _render_section_title("多期間預測")
            pred_cols = st.columns(len(config.PREDICTION_HORIZONS))
            for col, (horizon, label) in zip(pred_cols, config.PREDICTION_HORIZONS.items()):
                pred = horizon_predictions.get(horizon, {})
                prob = pred.get("up_probability")
                accuracy = pred.get("accuracy")
                with col:
                    if prob is None:
                        st.metric(f"{label}上漲機率", "N/A")
                        st.caption(pred.get("reason") or "資料不足")
                    else:
                        delta = f"測試準確率 {accuracy:.1%}" if accuracy is not None else None
                        st.metric(f"{label}上漲機率", f"{prob:.1%}", delta=delta)

            _render_section_title("訊號摘要")
            s1, s2 = st.columns(2)
            with s1:
                _render_signal_panel("K線訊號", kline_score_val, kline_signals)
            with s2:
                _render_signal_panel("籌碼/量價訊號", chip_score_val, chip_signals)

            # --- 圖表 ---
            _render_section_title("價格圖表")
            fig = build_figure(
                ticker, df,
                show_sma20=show_sma20,
                show_sma60=show_sma60,
                show_bb=show_bb,
                show_volume=show_volume,
                show_volume_ma=show_volume_ma,
                show_rsi=show_rsi,
                show_macd=show_macd,
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- 新聞列表 ---
            _render_section_title("近期新聞")
            if news_items:
                for item in news_items:
                    _render_news_item(item)
            else:
                st.write("目前無法取得相關新聞。")

        except Exception as e:
            st.error(f"分析過程發生錯誤: {e}")


# ============ 回顧更新頁 ============
with tab_update:
    _render_section_title("回顧更新")
    if st.button("執行回顧更新"):
        pending = storage.get_pending_reviews()
        if not pending:
            st.info("目前沒有到期需要回顧的建議紀錄。")
        else:
            progress = st.progress(0.0)
            results = []
            for i, rec in enumerate(pending):
                try:
                    recent = yf.download(rec["ticker"], period="5d", progress=False, auto_adjust=True)
                    if not recent.empty:
                        latest_price = float(recent["Close"].iloc[-1])
                        returns = storage.update_outcome(rec["id"], latest_price)
                        results.append({
                            "編號": rec["id"], "代號": rec["ticker"],
                            "策略": config.get_strategy_label(rec["strategy"]),
                            "建議": rec["top_action"],
                            "價格漲跌%": round(returns["gross_price_return"], 2),
                            "方向毛報酬%": round(returns["action_return"], 2),
                            "扣費後報酬%": round(returns["net_return"], 2),
                            "扣除費率%": round(returns["total_fee_rate"], 4),
                        })
                except Exception as e:
                    st.warning(f"回顧 {rec['ticker']} #{rec['id']} 時發生問題: {e}")
                progress.progress((i + 1) / len(pending))

            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            st.success(f"已回顧 {len(pending)} 筆紀錄。")


# ============ 績效統計頁 ============
with tab_stats:
    _render_section_title("績效統計")
    stats = storage.get_strategy_stats()
    if not stats:
        st.info(
            "目前還沒有已回顧的建議紀錄。先到「分析」頁產生建議,"
            "等持有天數到期後到「回顧更新」頁更新,累積資料後再回來看這裡。"
        )
    else:
        rows = []
        for name, s in stats.items():
            rows.append({
                "策略": config.get_strategy_label(name),
                "已回顧建議數": s["total_recommendations"],
                "有方向建議數": s["directional_recommendations"],
                "長期方向勝率%": s["directional_win_rate_pct"],
                "平均價格漲跌%": s["avg_price_return_pct"],
                "平均方向毛報酬%": s["avg_action_return_pct"],
                "平均扣費後報酬%": s["avg_net_return_pct"],
            })
        stats_df = pd.DataFrame(rows).sort_values(
            "平均扣費後報酬%", ascending=False, na_position="last"
        )
        st.dataframe(stats_df, use_container_width=True)

        best = stats_df.iloc[0]
        st.success(f"🏆 目前平均扣費後報酬率最優的策略: **{best['策略']}**")

        st.subheader("長期預測準確率比較")
        acc_strategy = pd.DataFrame(storage.get_accuracy_breakdown("strategy"))
        if not acc_strategy.empty:
            acc_strategy["group"] = acc_strategy["group"].map(config.get_strategy_label)
            acc_strategy = acc_strategy.rename(columns={"group": "策略"})
        acc_action = pd.DataFrame(storage.get_accuracy_breakdown("top_action"))
        acc_ticker = pd.DataFrame(storage.get_accuracy_breakdown("ticker", min_count=2))
        a1, a2 = st.columns(2)
        with a1:
            st.write("依策略")
            st.dataframe(acc_strategy, use_container_width=True)
        with a2:
            st.write("依建議動作")
            st.dataframe(acc_action, use_container_width=True)
        st.write("依股票(至少 2 筆有方向紀錄)")
        if acc_ticker.empty:
            st.info("同一股票累積 2 筆以上已回顧買入/賣出紀錄後,會在這裡比較。")
        else:
            st.dataframe(acc_ticker, use_container_width=True)


# ============ 歷史紀錄頁 ============
with tab_history:
    _render_section_title("歷史紀錄")
    hist_ticker = st.text_input(
        "輸入股票代號查詢(留空看全部)", key="hist_ticker_input"
    ).strip()
    records = storage.get_history(hist_ticker or None)
    if not records:
        st.info("沒有找到歷史紀錄。")
    else:
        history_df = pd.DataFrame(records)
        if "strategy" in history_df.columns:
            history_df["strategy"] = history_df["strategy"].map(config.get_strategy_label)
            history_df = history_df.rename(columns={"strategy": "策略"})
        st.dataframe(history_df, use_container_width=True)
