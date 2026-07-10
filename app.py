# update
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
from stock_db import MARKET_OPTIONS, search_stocks
from indicators import add_all_indicators
from model import predict_horizons
from news import analyze_news_sentiment
from decision import technical_score, ml_score, build_recommendation, candlestick_score, chip_score
from report import build_figure

warnings.filterwarnings("ignore")

st.set_page_config(page_title="股票分析建議系統", page_icon="📈", layout="wide")

st.title("股票分析 + 決策建議系統")
st.caption("⚠️ 本工具僅供學習與研究參考,任何建議皆不構成投資建議,請務必自行判斷風險。")

tab_analyze, tab_update, tab_stats, tab_history = st.tabs(
    ["🔍 分析", "🔄 回顧更新", "📊 績效統計", "🕘 歷史紀錄"]
)


def _stock_search_options(searchterm: str, market_filter: str = "全部市場"):
    """
    給 st_searchbox 用的搜尋函式。
    輸入部分代號或名稱(例如 "23"、"台積"、"aapl"),
    回傳給下拉選單顯示的候選清單。
    每個候選項是 (顯示文字, 實際回傳值) 的 tuple。
    """
    if not searchterm:
        return []
    results = search_stocks(searchterm, limit=10, market_filter=market_filter)
    return [
        (f"{code}　{name}　［{market}］", yf_code)
        for code, yf_code, name, market in results
    ]


def _strategy_label(strategy_name: str) -> str:
    return config.get_strategy_label(strategy_name)


# ============ 分析頁 ============
with tab_analyze:
    col_market, col1, col2, col3 = st.columns([1, 2, 1, 1])
    with col_market:
        market_filter = st.selectbox("市場", MARKET_OPTIONS, index=0)
    with col1:
        def _market_stock_options(searchterm: str):
            return _stock_search_options(searchterm, market_filter=market_filter)

        ticker = st_searchbox(
            _market_stock_options,
            placeholder="輸入代號或名稱,例如 23、台積電、AAPL、7203...",
            label="股票代號",
            key=f"ticker_searchbox_{market_filter}",
            clear_on_submit=False,
            rerun_on_update=True,
        )
        ticker = (ticker or "").strip()
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

    with st.expander("💰 持有紀錄手續費內扣設定", expanded=False):
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
        st.caption("費率會寫入本次建議紀錄；日股、韓股、歐股可依券商實際費率調整。")

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
            m1, m2, m3 = st.columns(3)
            m1.metric("買入", f"{recommendation['buy_pct']}%")
            m2.metric("觀望", f"{recommendation['hold_pct']}%")
            m3.metric("賣出", f"{recommendation['sell_pct']}%")

            action_emoji = {"買入": "🟢", "觀望": "⚪", "賣出": "🔴"}
            st.info(
                f"{action_emoji.get(recommendation['top_action'], '')} "
                f"**最可能操作: {recommendation['top_action']}**\n\n"
                f"技術面 `{recommendation['technical_score']:+.2f}` ／ "
                f"K線 `{recommendation['kline_score']:+.2f}` ／ "
                f"籌碼 `{recommendation['chip_score']:+.2f}` ／ "
                f"ML面 `{recommendation['ml_score']:+.2f}` "
                + (f"(隔日上漲機率 {up_prob:.1%}, 模型歷史準確率 {acc:.1%})" if up_prob is not None else "(資料不足,略過)")
                + f" ／ 新聞面 `{recommendation['news_score']:+.2f}` ／ "
                f"綜合分數 `{recommendation['final_score']:+.2f}`"
            )

            st.subheader("多期間預測")
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

            s1, s2 = st.columns(2)
            with s1:
                st.subheader("K線訊號")
                for signal in kline_signals[:5]:
                    st.write(f"- {signal}")
            with s2:
                st.subheader("籌碼/量價訊號")
                for signal in chip_signals[:5]:
                    st.write(f"- {signal}")

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
