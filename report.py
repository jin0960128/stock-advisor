"""
report.py
產生單一股票的互動式 HTML 報告:K 線圖 + 技術指標 + 新聞列表 + 綜合建議。

build_figure 支援:
  - 時間軸(可拖曳滑軌 + 快速按鈕:6個月/1年/5年/10年/全部),方便在最多10年的
    歷史資料中自由縮放查看
  - 每條線都有完整中文名稱
  - 每個指標都可以用參數開關要不要顯示(對應網頁上的核取方塊)
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config

# 時間軸快速按鈕(下方會加在圖表最上方的 x 軸)
_RANGE_SELECTOR_BUTTONS = [
    dict(count=6, label="6個月", step="month", stepmode="backward"),
    dict(count=1, label="1年", step="year", stepmode="backward"),
    dict(count=5, label="5年", step="year", stepmode="backward"),
    dict(count=10, label="10年", step="year", stepmode="backward"),
    dict(step="all", label="全部"),
]


def build_figure(
    ticker: str,
    df,
    show_sma20: bool = True,
    show_sma60: bool = True,
    show_bb: bool = True,
    show_volume: bool = True,
    show_volume_ma: bool = True,
    show_rsi: bool = True,
    show_macd: bool = True,
):
    """
    產生 K線+指標的 Plotly 圖表物件。
    每個 show_xxx 參數對應網頁上的一個開關核取方塊,設為 False 就不會畫出該線條/面板。

    K線本身、股價主圖一定會顯示(這是圖表的核心),其餘面板(成交量/RSI/MACD)
    若關閉,會直接把該面板整列拿掉,不會留空白。
    """
    panels = [("price", f"{ticker} 股價 K 線圖 + 均線 + 布林通道", 0.45)]
    if show_volume:
        panels.append(("volume", "成交量", 0.15))
    if show_rsi:
        panels.append(("rsi", "RSI 相對強弱指標(14日)", 0.2))
    if show_macd:
        panels.append(("macd", "MACD 指標(平滑異同移動平均線)", 0.2))

    row_heights = [h for _, _, h in panels]
    total_h = sum(row_heights)
    row_heights = [h / total_h for h in row_heights]
    titles = [t for _, t, _ in panels]
    row_of = {name: i + 1 for i, (name, _, _) in enumerate(panels)}
    n_rows = len(panels)

    fig = make_subplots(
        rows=n_rows, cols=1,
        shared_xaxes=True,
        row_heights=row_heights,
        vertical_spacing=0.04,
        subplot_titles=titles,
    )

    price_row = row_of["price"]

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="K線(開高低收)",
    ), row=price_row, col=1)

    if show_sma20:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_20"], name="20日均線(SMA20)",
            line=dict(width=1.3),
        ), row=price_row, col=1)
    if show_sma60:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["SMA_60"], name="60日均線(SMA60)",
            line=dict(width=1.3),
        ), row=price_row, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"], name="布林通道上軌",
            line=dict(width=1, dash="dot"),
        ), row=price_row, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"], name="布林通道下軌",
            line=dict(width=1, dash="dot"),
        ), row=price_row, col=1)

    if show_volume:
        vol_row = row_of["volume"]
        fig.add_trace(go.Bar(
            x=df.index, y=df["Volume"], name="成交量",
            marker_color="rgba(100,100,200,0.5)",
        ), row=vol_row, col=1)
        if show_volume_ma and "Volume_MA_20" in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df["Volume_MA_20"], name="成交量20日均量",
                line=dict(width=1.3, color="orange"),
            ), row=vol_row, col=1)

    if show_rsi:
        rsi_row = row_of["rsi"]
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI_14"], name="RSI相對強弱指標(14日)",
        ), row=rsi_row, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=rsi_row, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=rsi_row, col=1)

    if show_macd:
        macd_row = row_of["macd"]
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"], name="MACD差離值",
        ), row=macd_row, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"], name="訊號線(Signal)",
        ), row=macd_row, col=1)
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_hist"], name="MACD柱狀圖",
        ), row=macd_row, col=1)

    fig.update_layout(
        height=1000,
        legend=dict(orientation="h", y=1.02),
        template="plotly_white",
        hovermode="x unified",
    )

    fig.update_xaxes(
        rangeselector=dict(buttons=_RANGE_SELECTOR_BUTTONS),
        row=1, col=1,
    )
    fig.update_xaxes(
        rangeslider=dict(visible=True),
        row=n_rows, col=1,
    )
    for r in range(1, n_rows):
        fig.update_xaxes(rangeslider=dict(visible=False), row=r, col=1)

    return fig


def build_report(
    ticker: str, df, recommendation: dict, news_items: list,
    strategy_name: str, output_path: str, **figure_options,
):
    fig = build_figure(ticker, df, **figure_options)
    strategy_label = config.get_strategy_label(strategy_name)

    title = (
        f"{ticker} 綜合建議(策略:{strategy_label})　|　"
        f"<b>買入 {recommendation['buy_pct']}%　觀望 {recommendation['hold_pct']}%　"
        f"賣出 {recommendation['sell_pct']}%</b><br>"
        f"<sub>技術面分數 {recommendation['technical_score']}　"
        f"K線分數 {recommendation.get('kline_score', 0)}　"
        f"籌碼分數 {recommendation.get('chip_score', 0)}　"
        f"ML分數 {recommendation['ml_score']}　新聞面分數 {recommendation['news_score']}　"
        f"綜合分數 {recommendation['final_score']}</sub>"
    )

    fig.update_layout(title=title, height=1100)

    fig.write_html(output_path)

    news_html = "<div style='font-family:sans-serif; max-width:900px; margin:20px auto;'>"
    news_html += "<h2>近期相關新聞與情緒評分</h2><ul>"
    if news_items:
        for item in news_items:
            score = item.get("score", 0)
            color = "green" if score > 0.1 else ("red" if score < -0.1 else "gray")
            news_html += (
                f"<li style='margin-bottom:8px;'>"
                f"<span style='color:{color}; font-weight:bold;'>[{score:+.2f}]</span> "
                f"<a href='{item.get('link', '#')}' target='_blank'>{item['title']}</a> "
                f"<span style='color:#888;'>— {item.get('publisher', '')}</span></li>"
            )
    else:
        news_html += "<li>近期無法取得相關新聞</li>"
    news_html += "</ul></div>"

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(news_html)

    return output_path
