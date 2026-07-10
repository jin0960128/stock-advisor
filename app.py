"""
app.py
股票分析建議系統 —— 網頁介面(用 Streamlit 打造)

執行方式:
    streamlit run app.py

執行後會自動在瀏覽器打開一個網頁,不需要碰終端機指令,
輸入股票代號、按按鈕就能看到分析結果、K線圖、新聞與建議。
"""
import warnings

import pandas as pd
import streamlit as st
import yfinance as yf
from streamlit_searchbox import st_searchbox

import config
import storage
from stock_db import search_stocks
from indicators import add_all_indicators
from model import build_dataset, time_series_split, train_direction_model, \
    evaluate_model, predict_next_day
from news import analyze_news_sentiment
from decision import technical_score, ml_score, build_recommendation
from report import build_figure

warnings.filterwarnings("ignore")

st.set_page_config(page_title="股票分析建議系統", page_icon="📈", layout="wide")

st.title("股票分析 + 決策建議系統")
st.caption("⚠️ 本工具僅供學習與研究參考,任何建議皆不構成投資建議,請務必自行判斷風險。")

tab_analyze, tab_update, tab_stats, tab_history = st.tabs(
    ["🔍 分析", "🔄 回顧更新", "📊 績效統計", "🕘 歷史紀錄"]
)


def _stock_search_options(searchterm: str):
    """
    給 st_searchbox 用的搜尋函式。
    輸入部分代號或名稱(例如 "23"、"台積"、"aapl"),
    回傳給下拉選單顯示的候選清單。
    每個候選項是 (顯示文字, 實際回傳值) 的 tuple。
    """
    if not searchterm:
        return []
    results = search_stocks(searchterm, limit=10)
    return [
        (f"{code}　{name}　［{market}］", yf_code)
        for code, yf_code, name, market in results
    ]


# ============ 分析頁 ============
with tab_analyze:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        ticker = st_searchbox(
            _stock_search_options,
            placeholder="輸入代號或名稱,例如 23、台積電、AAPL...",
            label="股票代號",
            key="ticker_searchbox",
            clear_on_submit=False,
            rerun_on_update=True,
        )
        ticker = (ticker or "").strip()
    with col2:
        strategy_name = st.selectbox("使用策略", list(config.STRATEGIES.keys()))
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

    with st.expander("🎛️ 圖表顯示設定(勾選要顯示的線條/面板)", expanded=False):
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
        st.caption("💡 圖表下方也有時間軸滑軌與快速按鈕(6個月/1年/5年/10年/全部),可自由縮放查看不同區間。")

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

            with st.spinner("訓練機器學習模型..."):
                X, y, _ = build_dataset(df)
                if len(X) >= 60:
                    X_train, X_test, y_train, y_test = time_series_split(X, y, test_ratio=0.2)
                    model = train_direction_model(X_train, y_train)
                    acc, _, _ = evaluate_model(model, X_test, y_test)
                    up_prob = predict_next_day(model, X.iloc[[-1]])
                    ml_score_val = ml_score(up_prob)
                else:
                    acc, up_prob = None, None
                    ml_score_val = 0.0

            with st.spinner("搜尋近期新聞並分析情緒..."):
                news_score_val, news_items = analyze_news_sentiment(ticker)

            strategy = config.STRATEGIES[strategy_name]
            recommendation = build_recommendation(
                tech_score_val, ml_score_val, news_score_val, strategy
            )

            latest_price = float(df["Close"].iloc[-1])
            record_id = storage.save_recommendation(
                ticker, strategy_name, latest_price, recommendation, strategy["holding_days"],
            )

            st.success(
                f"分析完成,已記錄本次建議(編號 #{record_id}),"
                f"{strategy['holding_days']} 個交易日後可到「回顧更新」頁查看結果。"
            )

            # --- 建議摘要 ---
            m1, m2, m3 = st.columns(3)
            m1.metric("買入", f"{recommendation['buy_pct']}%")
            m2.metric("觀望", f"{recommendation['hold_pct']}%")
            m3.metric("賣出", f"{recommendation['sell_pct']}%")

            action_emoji = {"買入": "🟢", "觀望": "⚪", "賣出": "🔴"}
            st.info(
                f"{action_emoji.get(recommendation['top_action'], '')} "
                f"**最可能操作: {recommendation['top_action']}**\n\n"
                f"技術面 `{recommendation['technical_score']:+.2f}` ／ "
                f"ML面 `{recommendation['ml_score']:+.2f}` "
                + (f"(隔日上漲機率 {up_prob:.1%}, 模型歷史準確率 {acc:.1%})" if up_prob is not None else "(資料不足,略過)")
                + f" ／ 新聞面 `{recommendation['news_score']:+.2f}` ／ "
                f"綜合分數 `{recommendation['final_score']:+.2f}`"
            )

            # --- 圖表 ---
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
            st.subheader("📰 近期相關新聞與情緒評分")
            if news_items:
                for item in news_items:
                    score = item.get("score", 0)
                    emoji = "🟢" if score > 0.1 else ("🔴" if score < -0.1 else "⚪")
                    st.markdown(
                        f"{emoji} `{score:+.2f}` "
                        f"[{item['title']}]({item.get('link', '#')}) "
                        f"— *{item.get('publisher', '')}*"
                    )
            else:
                st.write("目前無法取得相關新聞。")

        except Exception as e:
            st.error(f"分析過程發生錯誤: {e}")


# ============ 回顧更新頁 ============
with tab_update:
    st.write("回顧所有「持有天數已到期」的歷史建議,自動查詢最新股價並計算實際結果。")
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
                        storage.update_outcome(rec["id"], latest_price)
                        actual_return = (
                            (latest_price - rec["price_at_reco"]) / rec["price_at_reco"] * 100
                        )
                        results.append({
                            "編號": rec["id"], "代號": rec["ticker"], "策略": rec["strategy"],
                            "建議": rec["top_action"], "實際報酬%": round(actual_return, 2),
                        })
                except Exception as e:
                    st.warning(f"回顧 {rec['ticker']} #{rec['id']} 時發生問題: {e}")
                progress.progress((i + 1) / len(pending))

            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            st.success(f"已回顧 {len(pending)} 筆紀錄。")


# ============ 績效統計頁 ============
with tab_stats:
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
                "策略": name,
                "已回顧建議數": s["total_recommendations"],
                "方向勝率%": s["directional_win_rate_pct"],
                "平均實際報酬%": s["avg_actual_return_pct"],
            })
        stats_df = pd.DataFrame(rows).sort_values(
            "平均實際報酬%", ascending=False, na_position="last"
        )
        st.dataframe(stats_df, use_container_width=True)

        best = stats_df.iloc[0]
        st.success(f"🏆 目前平均報酬率最優的策略: **{best['策略']}**")


# ============ 歷史紀錄頁 ============
with tab_history:
    hist_ticker = st.text_input(
        "輸入股票代號查詢(留空看全部)", key="hist_ticker_input"
    ).strip()
    records = storage.get_history(hist_ticker or None)
    if not records:
        st.info("沒有找到歷史紀錄。")
    else:
        st.dataframe(pd.DataFrame(records), use_container_width=True)
