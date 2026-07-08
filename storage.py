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
    ml_score REAL,
    news_score REAL,
    final_score REAL,
    buy_pct REAL,
    hold_pct REAL,
    sell_pct REAL,
    top_action TEXT,                   -- 買入 / 觀望 / 賣出
    holding_days INTEGER NOT NULL,
    outcome_checked INTEGER DEFAULT 0, -- 0=尚未回顧, 1=已回顧
    price_after REAL,                  -- 持有天數到期後的實際價格
    actual_return REAL,                -- 實際報酬率 (%)
    was_correct INTEGER                -- 建議方向是否正確 (1/0),觀望不計入對錯
);
"""


def _connect():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(SCHEMA)
    return conn


def save_recommendation(ticker: str, strategy_name: str, price_at_reco: float,
                         recommendation: dict, holding_days: int) -> int:
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO recommendations
           (ticker, strategy, created_at, price_at_reco, technical_score, ml_score,
            news_score, final_score, buy_pct, hold_pct, sell_pct, top_action, holding_days)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ticker, strategy_name, datetime.now().isoformat(timespec="seconds"), price_at_reco,
            recommendation["technical_score"], recommendation["ml_score"], recommendation["news_score"],
            recommendation["final_score"], recommendation["buy_pct"], recommendation["hold_pct"],
            recommendation["sell_pct"], recommendation["top_action"], holding_days,
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


def update_outcome(record_id: int, price_after: float):
    conn = _connect()
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM recommendations WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        conn.close()
        return

    price_at_reco = row["price_at_reco"]
    top_action = row["top_action"]
    actual_return = (price_after - price_at_reco) / price_at_reco * 100

    if top_action == "買入":
        was_correct = int(actual_return > 0)
    elif top_action == "賣出":
        was_correct = int(actual_return < 0)
    else:  # 觀望不計入對錯統計
        was_correct = None

    conn.execute(
        """UPDATE recommendations
           SET outcome_checked = 1, price_after = ?, actual_return = ?, was_correct = ?
           WHERE id = ?""",
        (price_after, actual_return, was_correct, record_id),
    )
    conn.commit()
    conn.close()


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
        stats.setdefault(strategy, {"count": 0, "correct": 0, "directional_count": 0, "returns": []})
        s = stats[strategy]
        s["count"] += 1
        s["returns"].append(row["actual_return"])
        if row["was_correct"] is not None:
            s["directional_count"] += 1
            s["correct"] += row["was_correct"]

    summary = {}
    for strategy, s in stats.items():
        win_rate = (s["correct"] / s["directional_count"] * 100) if s["directional_count"] else None
        avg_return = sum(s["returns"]) / len(s["returns"]) if s["returns"] else None
        summary[strategy] = {
            "total_recommendations": s["count"],
            "directional_win_rate_pct": round(win_rate, 1) if win_rate is not None else None,
            "avg_actual_return_pct": round(avg_return, 2) if avg_return is not None else None,
        }
    return summary


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
