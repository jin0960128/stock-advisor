"""
storage.py
用 SQLite 記錄每次的分析建議,並在持有天數到期後,
回頭查實際股價變化,計算這次建議是否『猜對方向』與報酬率。
長期累積後可以用 get_strategy_stats() 統計各策略的表現。
"""
import os
import sqlite3
from datetime import datetime, timedelta

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    strategy TEXT NOT NULL,
    created_at TEXT NOT NULL,          -- 建議產生時間 (ISO 格式)
    price_at_reco REAL NOT NULL,       -- 建議當下的收盤價
    technical_score REAL,
    kline_score REAL,
    chip_score REAL,
    ml_score REAL,
    news_score REAL,
    final_score REAL,
    buy_pct REAL,
    hold_pct REAL,
    sell_pct REAL,
    top_action TEXT,                   -- 買入 / 觀望 / 賣出
    holding_days INTEGER NOT NULL,
    fee_deducted INTEGER DEFAULT 1,    -- 1=回顧報酬率內扣交易成本
    buy_fee_rate REAL DEFAULT 0.1425,  -- 買進手續費(%)
    sell_fee_rate REAL DEFAULT 0.1425, -- 賣出手續費(%)
    sell_tax_rate REAL DEFAULT 0.3,    -- 賣出交易稅/其他成本(%)
    outcome_checked INTEGER DEFAULT 0, -- 0=尚未回顧, 1=已回顧
    price_after REAL,                  -- 持有天數到期後的實際價格
    gross_price_return REAL,           -- 單純價格漲跌幅(%)
    action_return REAL,                -- 依買/賣方向換算後的毛報酬(%)
    net_return REAL,                   -- 內扣交易成本後的報酬(%)
    total_fee_rate REAL,               -- 本次回顧扣除的總費率(%)
    actual_return REAL,                -- 相容舊欄位:同 net_return
    was_correct INTEGER                -- 建議方向是否正確 (1/0),觀望不計入對錯
);
"""

OPTIONAL_COLUMNS = {
    "kline_score": "REAL",
    "chip_score": "REAL",
    "fee_deducted": "INTEGER DEFAULT 1",
    "buy_fee_rate": f"REAL DEFAULT {config.DEFAULT_BUY_FEE_RATE}",
    "sell_fee_rate": f"REAL DEFAULT {config.DEFAULT_SELL_FEE_RATE}",
    "sell_tax_rate": f"REAL DEFAULT {config.DEFAULT_SELL_TAX_RATE}",
    "gross_price_return": "REAL",
    "action_return": "REAL",
    "net_return": "REAL",
    "total_fee_rate": "REAL",
}


def _ensure_schema(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)").fetchall()}
    for column_name, column_type in OPTIONAL_COLUMNS.items():
        if column_name not in existing:
            conn.execute(f"ALTER TABLE recommendations ADD COLUMN {column_name} {column_type}")
    conn.commit()


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(SCHEMA)
    _ensure_schema(conn)
    return conn


def save_recommendation(ticker: str, strategy_name: str, price_at_reco: float,
                         recommendation: dict, holding_days: int,
                         fee_deducted: bool = None, buy_fee_rate: float = None,
                         sell_fee_rate: float = None, sell_tax_rate: float = None) -> int:
    if fee_deducted is None:
        fee_deducted = config.DEFAULT_FEE_DEDUCTED
    if buy_fee_rate is None:
        buy_fee_rate = config.DEFAULT_BUY_FEE_RATE
    if sell_fee_rate is None:
        sell_fee_rate = config.DEFAULT_SELL_FEE_RATE
    if sell_tax_rate is None:
        sell_tax_rate = config.DEFAULT_SELL_TAX_RATE

    conn = _connect()
    cur = conn.execute(
        """INSERT INTO recommendations
           (ticker, strategy, created_at, price_at_reco, technical_score, kline_score,
            chip_score, ml_score, news_score, final_score, buy_pct, hold_pct, sell_pct,
            top_action, holding_days, fee_deducted, buy_fee_rate, sell_fee_rate, sell_tax_rate)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ticker, strategy_name, datetime.now().isoformat(timespec="seconds"), price_at_reco,
            recommendation["technical_score"], recommendation.get("kline_score", 0.0),
            recommendation.get("chip_score", 0.0), recommendation["ml_score"],
            recommendation["news_score"], recommendation["final_score"], recommendation["buy_pct"],
            recommendation["hold_pct"], recommendation["sell_pct"], recommendation["top_action"],
            holding_days, int(bool(fee_deducted)), buy_fee_rate, sell_fee_rate, sell_tax_rate,
        ),
    )
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id


def get_pending_reviews():
    """找出『持有天數已到期,但還沒回顧結果』的建議紀錄。"""
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE outcome_checked = 0"
    ).fetchall()
    conn.close()

    due = []
    for row in rows:
        created = datetime.fromisoformat(row["created_at"])
        due_date = created + timedelta(days=row["holding_days"])
        if datetime.now() >= due_date:
            due.append(dict(row))
    return due


def _row_value(row, key, default=None):
    try:
        value = row[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


def _calculate_return_fields(row, price_after: float):
    price_at_reco = row["price_at_reco"]
    top_action = row["top_action"]
    gross_price_return = (price_after - price_at_reco) / price_at_reco * 100

    if top_action == "買入":
        action_return = gross_price_return
        was_correct = int(gross_price_return > 0)
    elif top_action == "賣出":
        action_return = -gross_price_return
        was_correct = int(gross_price_return < 0)
    else:
        action_return = 0.0
        was_correct = None

    fee_deducted = bool(_row_value(row, "fee_deducted", int(config.DEFAULT_FEE_DEDUCTED)))
    buy_fee_rate = float(_row_value(row, "buy_fee_rate", config.DEFAULT_BUY_FEE_RATE) or 0)
    sell_fee_rate = float(_row_value(row, "sell_fee_rate", config.DEFAULT_SELL_FEE_RATE) or 0)
    sell_tax_rate = float(_row_value(row, "sell_tax_rate", config.DEFAULT_SELL_TAX_RATE) or 0)
    total_fee_rate = 0.0
    if fee_deducted and top_action in {"買入", "賣出"}:
        total_fee_rate = buy_fee_rate + sell_fee_rate + sell_tax_rate

    net_return = action_return - total_fee_rate
    return {
        "gross_price_return": gross_price_return,
        "action_return": action_return,
        "net_return": net_return,
        "total_fee_rate": total_fee_rate,
        "was_correct": was_correct,
    }


def update_outcome(record_id: int, price_after: float):
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM recommendations WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        conn.close()
        return None

    returns = _calculate_return_fields(row, price_after)
    conn.execute(
        """UPDATE recommendations
           SET outcome_checked = 1, price_after = ?, gross_price_return = ?,
               action_return = ?, net_return = ?, total_fee_rate = ?,
               actual_return = ?, was_correct = ?
           WHERE id = ?""",
        (
            price_after, returns["gross_price_return"], returns["action_return"],
            returns["net_return"], returns["total_fee_rate"], returns["net_return"],
            returns["was_correct"], record_id,
        ),
    )
    conn.commit()
    conn.close()
    return returns


def get_strategy_stats():
    """
    統計每個策略的長期表現:
    - 已回顧的建議數
    - 方向判斷正確率(不含觀望)
    - 平均實際報酬率
    """
    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM recommendations WHERE outcome_checked = 1"
    ).fetchall()
    conn.close()

    stats = {}
    for row in rows:
        strategy = row["strategy"]
        stats.setdefault(strategy, {
            "count": 0,
            "correct": 0,
            "directional_count": 0,
            "price_returns": [],
            "action_returns": [],
            "net_returns": [],
        })
        s = stats[strategy]
        s["count"] += 1
        s["price_returns"].append(_row_value(row, "gross_price_return", row["actual_return"]))
        s["action_returns"].append(_row_value(row, "action_return", row["actual_return"]))
        s["net_returns"].append(_row_value(row, "net_return", row["actual_return"]))
        if row["was_correct"] is not None:
            s["directional_count"] += 1
            s["correct"] += row["was_correct"]

    summary = {}
    for strategy, s in stats.items():
        win_rate = (s["correct"] / s["directional_count"] * 100) if s["directional_count"] else None
        avg_price_return = sum(s["price_returns"]) / len(s["price_returns"]) if s["price_returns"] else None
        avg_action_return = sum(s["action_returns"]) / len(s["action_returns"]) if s["action_returns"] else None
        avg_net_return = sum(s["net_returns"]) / len(s["net_returns"]) if s["net_returns"] else None
        summary[strategy] = {
            "total_recommendations": s["count"],
            "directional_recommendations": s["directional_count"],
            "directional_win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
            "avg_price_return_pct": round(avg_price_return, 2) if avg_price_return is not None else None,
            "avg_action_return_pct": round(avg_action_return, 2) if avg_action_return is not None else None,
            "avg_net_return_pct": round(avg_net_return, 2) if avg_net_return is not None else None,
            "avg_actual_return_pct": round(avg_net_return, 2) if avg_net_return is not None else None,
        }
    return summary


def get_accuracy_breakdown(group_by: str = "strategy", min_count: int = 1):
    """
    依策略、股票、動作或持有天數比較長期方向準確率。
    只計入買入/賣出這類有方向判斷的紀錄,觀望不列入勝率。
    """
    allowed = {
        "strategy": "strategy",
        "ticker": "ticker",
        "top_action": "top_action",
        "holding_days": "holding_days",
    }
    if group_by not in allowed:
        raise ValueError(f"group_by 必須是 {list(allowed)}")

    conn = _connect()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""SELECT {allowed[group_by]} AS group_name, was_correct, net_return, actual_return
            FROM recommendations
            WHERE outcome_checked = 1 AND was_correct IS NOT NULL"""
    ).fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        key = str(row["group_name"])
        grouped.setdefault(key, {"count": 0, "correct": 0, "returns": []})
        item = grouped[key]
        item["count"] += 1
        item["correct"] += int(row["was_correct"])
        item["returns"].append(_row_value(row, "net_return", row["actual_return"]))

    result = []
    for key, item in grouped.items():
        if item["count"] < min_count:
            continue
        avg_return = sum(item["returns"]) / len(item["returns"]) if item["returns"] else None
        result.append({
            "group": key,
            "directional_count": item["count"],
            "correct_count": item["correct"],
            "accuracy_pct": round(item["correct"] / item["count"] * 100, 1),
            "avg_net_return_pct": round(avg_return, 2) if avg_return is not None else None,
        })

    return sorted(result, key=lambda r: (r["accuracy_pct"], r["directional_count"]), reverse=True)


def get_history(ticker: str = None, limit: int = 50):
    conn = _connect()
    conn.row_factory = sqlite3.Row
    if ticker:
        rows = conn.execute(
            "SELECT * FROM recommendations WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
            (ticker, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
