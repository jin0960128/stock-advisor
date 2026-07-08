"""
report.py
產生單一股票的互動式 HTML 報告:K 線圖 + 技術指標 + 新聞列表 + 綜合建議。
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def build_figure(ticker: str, df):
    """
    只產生 K線+指標的 Plotly 圖表物件(不含建議標題),
    讓 CLI 版(輸出 HTML 檔)跟網頁版(Streamlit 直接顯示)可以共用。
    """
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        row_heights=[0.45, 0.15, 0.2, 0.2],
        vertical_spacing=0.03,
        subplot_titles=(
            f"{ticker} 股價 K 線圖 + 布林通道",
            "成交量",
            "RSI (14)",
            "MACD",
        ),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="K線",
    ), row=1, col=1)

    for col, name, dash in [
        ("SMA_20", "SMA 20", None),
        ("SMA_60", "SMA 60", None),
        ("BB_upper", "布林上軌", "dot"),
        ("BB_lower", "布林下軌", "dot"),
    ]:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], name=name, line=dict(width=1, dash=dash),
        ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="成交量", marker_color="rgba(100,100,200,0.5)",
    ), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI 14"), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_signal"], name="訊號線"), row=4, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["MACD_hist"], name="MACD 柱狀"), row=4, col=1)

    fig.update_layout(
        height=1000,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02),
        template="plotly_white",
    )
    return fig


def build_report(ticker: str, df, recommendation: dict, news_items: list, strategy_name: str, output_path: str):
    fig = build_figure(ticker, df)

    title = (
        f"{ticker} 綜合建議(策略:{strategy_name})　|　"
        f"<b>買入 {recommendation['buy_pct']}%　觀望 {recommendation['hold_pct']}%　"
        f"賣出 {recommendation['sell_pct']}%</b><br>"
        f"<sub>技術面分數 {recommendation['technical_score']}　"
        f"ML分數 {recommendation['ml_score']}　新聞面分數 {recommendation['news_score']}　"
        f"綜合分數 {recommendation['final_score']}</sub>"
    )

    fig.update_layout(
        title=title,
        height=1100,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", y=1.02),
        template="plotly_white",
    )

    fig.write_html(output_path)

    # 在 HTML 檔案尾端附加新聞列表(簡單的 HTML 片段,不需要額外套件)
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
