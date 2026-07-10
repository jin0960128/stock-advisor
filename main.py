"""
main.py
單一股票分析 + 決策建議系統
================================
用法:
    python main.py analyze 2330.TW                  # 分析單一股票並產生建議(用預設策略)
    python main.py analyze 2330.TW --strategy news_focused
    python main.py update                            # 回顧所有到期的歷史建議,計算實際結果
    python main.py stats                              # 顯示各策略的長期績效統計
    python main.py history 2330.TW                    # 查看某股票過去的建議紀錄

代號格式:
    台股: 2330.TW (台積電)、2317.TW (鴻海)
    美股: AAPL、TSLA、NVDA
"""
import argparse
import os
import warnings

import yfinance as yf

import config
import storage
from indicators import add_all_indicators
from model import predict_horizons
from news import analyze_news_sentiment
from decision import technical_score, ml_score, build_recommendation, candlestick_score, chip_score
from report import build_report

warnings.filterwarnings("ignore")

OUTPUT_DIR = "reports"


def _download_and_prepare(ticker: str):
    raw = yf.download(ticker, period=config.PRICE_HISTORY_PERIOD, progress=False, auto_adjust=True)
    if raw.empty:
        raise ValueError(f"無法取得 {ticker} 的股價資料,請確認代號是否正確。")
    if isinstance(raw.columns, __import__("pandas").MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    df = add_all_indicators(raw)
    return df


def cmd_analyze(ticker: str, strategy_name: str, fee_deducted: bool = None,
                buy_fee_rate: float = None, sell_fee_rate: float = None,
                sell_tax_rate: float = None):
    if strategy_name not in config.STRATEGIES:
        raise ValueError(f"找不到策略 '{strategy_name}',可用策略: {list(config.STRATEGIES.keys())}")
    strategy = config.STRATEGIES[strategy_name]

    print(f"\n{'=' * 60}\n分析 {ticker}(策略: {strategy_name}）\n{'=' * 60}")

    # 1. 股價 + 技術指標
    print("下載股價資料並計算技術指標...")
    df = _download_and_prepare(ticker)
    tech_score_val = technical_score(df)
    print(f"技術面分數: {tech_score_val:+.3f}")

    kline_score_val, kline_signals = candlestick_score(df)
    chip_score_val, chip_signals = chip_score(df)
    print(f"K線分數: {kline_score_val:+.3f} ({' / '.join(kline_signals[:3])})")
    print(f"籌碼/量價分數: {chip_score_val:+.3f} ({' / '.join(chip_signals[:3])})")

    # 2. 機器學習模型預測
    print("訓練多期間機器學習模型...")
    horizon_predictions = predict_horizons(df, horizons=config.PREDICTION_HORIZONS.keys())
    for horizon, label in config.PREDICTION_HORIZONS.items():
        pred = horizon_predictions.get(horizon, {})
        if pred.get("up_probability") is None:
            print(f"  {label}: N/A({pred.get('reason') or '資料不足'})")
        else:
            print(f"  {label}: 上漲機率 {pred['up_probability']:.1%}, 測試準確率 {pred['accuracy']:.1%}")

    day1_prediction = horizon_predictions.get(1, {})
    if day1_prediction.get("up_probability") is not None:
        up_prob = day1_prediction["up_probability"]
        acc = day1_prediction["accuracy"]
        ml_score_val = ml_score(up_prob)
    else:
        print("[警告] 資料量不足,跳過 ML 模型,視為中性訊號。")
        ml_score_val = 0.0

    # 3. 新聞情緒分析
    print("搜尋近期新聞並分析情緒...")
    news_score_val, news_items = analyze_news_sentiment(ticker)
    print(f"新聞面分數: {news_score_val:+.3f}(共 {len(news_items)} 則新聞)")

    # 4. 綜合決策
    recommendation = build_recommendation(
        tech_score_val, ml_score_val, news_score_val, strategy,
        kline_score_val=kline_score_val, chip_score_val=chip_score_val,
    )
    print(f"\n{'-' * 60}")
    print(f"綜合建議: 買入 {recommendation['buy_pct']}%　"
          f"觀望 {recommendation['hold_pct']}%　"
          f"賣出 {recommendation['sell_pct']}%")
    print(f"最可能操作: {recommendation['top_action']}")
    print(f"{'-' * 60}")

    # 5. 存入資料庫,供未來回顧績效
    latest_price = float(df["Close"].iloc[-1])
    record_id = storage.save_recommendation(
        ticker, strategy_name, latest_price, recommendation, strategy["holding_days"],
        fee_deducted=fee_deducted,
        buy_fee_rate=buy_fee_rate,
        sell_fee_rate=sell_fee_rate,
        sell_tax_rate=sell_tax_rate,
    )
    print(f"已記錄本次建議(紀錄編號 #{record_id}),"
          f"將於 {strategy['holding_days']} 個交易日後可回顧結果。")

    # 6. 產生 HTML 報告
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{ticker.replace('.', '_')}_report.html")
    build_report(ticker, df.tail(250), recommendation, news_items, strategy_name, output_path)
    print(f"互動式報告已產生: {output_path}")


def cmd_update():
    pending = storage.get_pending_reviews()
    if not pending:
        print("目前沒有到期需要回顧的建議紀錄。")
        return

    print(f"找到 {len(pending)} 筆到期待回顧的建議,開始查詢實際股價...")
    for rec in pending:
        ticker = rec["ticker"]
        try:
            recent = yf.download(ticker, period="5d", progress=False, auto_adjust=True)
            if recent.empty:
                print(f"[跳過] 無法取得 {ticker} 最新股價")
                continue
            latest_price = float(recent["Close"].iloc[-1])
            returns = storage.update_outcome(rec["id"], latest_price)
            print(f"#{rec['id']} {ticker} [{rec['strategy']}] "
                  f"建議={rec['top_action']}　價格漲跌={returns['gross_price_return']:+.2f}%　"
                  f"扣費後報酬={returns['net_return']:+.2f}%")
        except Exception as e:
            print(f"[錯誤] 回顧 {ticker} #{rec['id']} 時發生問題: {e}")


def cmd_stats():
    stats = storage.get_strategy_stats()
    if not stats:
        print("目前還沒有已回顧的建議紀錄可供統計。先用 analyze 產生建議、"
              "等持有天數到期後跑 update,累積足夠資料後再來看 stats。")
        return

    print(f"\n{'=' * 60}\n策略長期績效統計\n{'=' * 60}")
    for strategy_name, s in sorted(
        stats.items(), key=lambda kv: (kv[1]["avg_actual_return_pct"] or -999), reverse=True
    ):
        print(f"\n策略: {strategy_name}")
        print(f"  已回顧建議數: {s['total_recommendations']}")
        print(f"  有方向建議數: {s['directional_recommendations']}")
        print(f"  方向判斷勝率: {s['directional_win_rate_pct']}%" if s['directional_win_rate_pct'] is not None else "  方向判斷勝率: N/A")
        print(f"  平均價格漲跌: {s['avg_price_return_pct']}%" if s['avg_price_return_pct'] is not None else "  平均價格漲跌: N/A")
        print(f"  平均方向毛報酬: {s['avg_action_return_pct']}%" if s['avg_action_return_pct'] is not None else "  平均方向毛報酬: N/A")
        print(f"  平均扣費後報酬: {s['avg_net_return_pct']}%" if s['avg_net_return_pct'] is not None else "  平均扣費後報酬: N/A")

    best = max(stats.items(), key=lambda kv: (kv[1]["avg_actual_return_pct"] or -999))
    print(f"\n目前平均扣費後報酬率最優的策略: {best[0]}")

    breakdown = storage.get_accuracy_breakdown("strategy")
    if breakdown:
        print("\n長期預測準確率比較(依策略):")
        for row in breakdown:
            print(f"  {row['group']}: 勝率 {row['accuracy_pct']}%, "
                  f"有方向筆數 {row['directional_count']}, "
                  f"平均扣費後報酬 {row['avg_net_return_pct']}%")


def cmd_history(ticker: str):
    records = storage.get_history(ticker)
    if not records:
        print(f"目前沒有 {ticker} 的歷史建議紀錄。")
        return
    print(f"\n{ticker} 歷史建議紀錄(最新 {len(records)} 筆):")
    for r in records:
        status = "已回顧" if r["outcome_checked"] else "待回顧"
        line = f"  [{r['created_at']}] 策略={r['strategy']} 建議={r['top_action']} " \
               f"(買{r['buy_pct']}%/觀{r['hold_pct']}%/賣{r['sell_pct']}%) 狀態={status}"
        if r["outcome_checked"]:
            line += f" 扣費後報酬={r['actual_return']:+.2f}% 判斷正確={r['was_correct']}"
        print(line)


def main():
    parser = argparse.ArgumentParser(description="單一股票分析 + 決策建議系統")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_analyze = subparsers.add_parser("analyze", help="分析單一股票並產生建議")
    p_analyze.add_argument("ticker", help="股票代號,例如 2330.TW 或 AAPL")
    p_analyze.add_argument("--strategy", default=config.DEFAULT_STRATEGY,
                            help=f"策略名稱,可用: {list(config.STRATEGIES.keys())}")
    p_analyze.add_argument("--no-fee-deduct", action="store_true",
                           help="持有紀錄回顧時不內扣交易成本")
    p_analyze.add_argument("--buy-fee-rate", type=float, default=config.DEFAULT_BUY_FEE_RATE,
                           help="買進手續費百分比")
    p_analyze.add_argument("--sell-fee-rate", type=float, default=config.DEFAULT_SELL_FEE_RATE,
                           help="賣出手續費百分比")
    p_analyze.add_argument("--sell-tax-rate", type=float, default=config.DEFAULT_SELL_TAX_RATE,
                           help="賣出交易稅/其他成本百分比")

    subparsers.add_parser("update", help="回顧所有到期的歷史建議")
    subparsers.add_parser("stats", help="顯示各策略的長期績效統計")

    p_history = subparsers.add_parser("history", help="查看某股票的歷史建議紀錄")
    p_history.add_argument("ticker", help="股票代號")

    args = parser.parse_args()

    print("提醒: 本工具僅供學習與研究參考,任何建議皆不構成投資建議,請自行判斷風險。")

    if args.command == "analyze":
        cmd_analyze(
            args.ticker, args.strategy,
            fee_deducted=not args.no_fee_deduct,
            buy_fee_rate=args.buy_fee_rate,
            sell_fee_rate=args.sell_fee_rate,
            sell_tax_rate=args.sell_tax_rate,
        )
    elif args.command == "update":
        cmd_update()
    elif args.command == "stats":
        cmd_stats()
    elif args.command == "history":
        cmd_history(args.ticker)


if __name__ == "__main__":
    main()
