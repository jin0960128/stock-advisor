"""
web_app.py
自訂股票分析網頁介面,不使用 Streamlit。

執行方式:
    python web_app.py

開啟:
    http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
import plotly
import yfinance as yf

import config
import storage
from decision import (
    build_recommendation,
    candlestick_score,
    chip_score,
    ml_score,
    technical_score,
)
from indicators import add_all_indicators
from model import predict_horizons
from news import analyze_news_sentiment
from report import build_figure
from stock_db import MARKET_OPTIONS, list_stocks


APP_HTML = r"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>股票分析決策系統</title>
  <script src="/plotly.min.js"></script>
  <style>
    :root {
      --bg: #f4f7fb;
      --surface: #ffffff;
      --surface-2: #f8fafc;
      --line: #d9e2ec;
      --text: #17212b;
      --muted: #697586;
      --teal: #176b73;
      --teal-2: #e6f3f4;
      --green: #137a46;
      --green-2: #e7f6ee;
      --red: #b42318;
      --red-2: #fdeceb;
      --amber: #a76713;
      --amber-2: #fff5d6;
      --blue: #2458a6;
      --blue-2: #edf4ff;
      --shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", "Noto Sans TC", "Microsoft JhengHei", Arial, sans-serif;
      letter-spacing: 0;
    }

    button, input, select {
      font: inherit;
      letter-spacing: 0;
    }

    .shell {
      width: min(1280px, calc(100% - 32px));
      margin: 0 auto;
      padding: 22px 0 34px;
    }

    .topbar {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 20px 24px;
      box-shadow: var(--shadow);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 20px;
    }

    .eyebrow {
      color: var(--teal);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
      margin-bottom: 5px;
    }

    h1 {
      margin: 0;
      font-size: 30px;
      line-height: 1.2;
      font-weight: 850;
    }

    .subtitle {
      color: var(--muted);
      margin: 8px 0 0;
      font-size: 15px;
      line-height: 1.6;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      min-width: 260px;
    }

    .chip, .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 8px;
      border: 1px solid var(--line);
      background: var(--surface-2);
      color: var(--text);
      font-size: 13px;
      font-weight: 700;
      padding: 7px 10px;
      white-space: nowrap;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin: 18px 0 14px;
      border-bottom: 1px solid var(--line);
    }

    .tab {
      border: 1px solid transparent;
      border-bottom: none;
      background: transparent;
      color: var(--muted);
      padding: 12px 16px;
      border-radius: 8px 8px 0 0;
      font-weight: 800;
      cursor: pointer;
    }

    .tab.active {
      background: var(--surface);
      border-color: var(--line);
      color: var(--teal);
    }

    .view { display: none; }
    .view.active { display: block; }

    .section-title {
      font-size: 18px;
      font-weight: 850;
      margin: 22px 0 12px;
    }

    .toolbar {
      display: grid;
      grid-template-columns: 1fr 2fr 1fr 1fr auto;
      gap: 12px;
      align-items: end;
    }

    .field label {
      display: block;
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
      margin: 0 0 7px;
    }

    .input, select {
      width: 100%;
      height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface-2);
      color: var(--text);
      padding: 0 12px;
      outline: none;
    }

    .input:focus, select:focus {
      border-color: var(--teal);
      box-shadow: 0 0 0 3px rgba(23, 107, 115, 0.14);
    }

    .button {
      height: 42px;
      border: 1px solid var(--teal);
      border-radius: 8px;
      color: #fff;
      background: var(--teal);
      padding: 0 18px;
      font-weight: 850;
      cursor: pointer;
      box-shadow: 0 8px 18px rgba(23, 107, 115, 0.18);
      white-space: nowrap;
    }

    .button.secondary {
      background: var(--surface);
      color: var(--teal);
      box-shadow: none;
    }

    .button:disabled {
      cursor: not-allowed;
      border-color: var(--line);
      background: #e5e7eb;
      color: #9ca3af;
      box-shadow: none;
    }

    .options {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      margin-top: 14px;
    }

    details {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.035);
    }

    summary {
      cursor: pointer;
      font-weight: 850;
      color: var(--text);
    }

    .check-grid, .fee-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px 14px;
      margin-top: 14px;
    }

    .fee-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .checkbox {
      display: flex;
      gap: 8px;
      align-items: center;
      color: var(--text);
      font-size: 14px;
      font-weight: 650;
    }

    .status {
      display: none;
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 12px 14px;
      color: var(--muted);
    }

    .status.show { display: block; }
    .status.error {
      border-color: #fac7c2;
      color: var(--red);
      background: var(--red-2);
    }

    .metrics {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    .metric, .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
      padding: 14px 16px;
    }

    .metric-label {
      color: var(--muted);
      font-size: 13px;
      font-weight: 800;
    }

    .metric-value {
      margin-top: 5px;
      font-size: 27px;
      font-weight: 850;
    }

    .decision {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-top: 14px;
      border-radius: 8px;
      border: 1px solid var(--line);
      border-left-width: 5px;
      background: var(--surface);
      padding: 16px 18px;
      box-shadow: var(--shadow);
    }

    .decision.buy { border-left-color: var(--green); background: var(--green-2); }
    .decision.sell { border-left-color: var(--red); background: var(--red-2); }
    .decision.hold { border-left-color: var(--amber); background: var(--amber-2); }

    .decision small {
      display: block;
      color: var(--muted);
      font-weight: 800;
      margin-bottom: 4px;
    }

    .decision strong {
      display: block;
      font-size: 26px;
      line-height: 1.2;
    }

    .decision-meta {
      text-align: right;
      color: var(--muted);
      line-height: 1.6;
      font-weight: 650;
    }

    .score-strip {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .pill.positive { color: var(--green); background: var(--green-2); border-color: #b7e3cc; }
    .pill.negative { color: var(--red); background: var(--red-2); border-color: #fac7c2; }
    .pill.neutral { color: var(--blue); background: var(--blue-2); border-color: #c8daf8; }

    .two-col {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    .panel-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
      font-weight: 850;
    }

    .signal-list {
      display: grid;
      gap: 8px;
    }

    .signal-item {
      background: var(--surface-2);
      border: 1px solid #edf1f6;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 14px;
      line-height: 1.45;
    }

    #chart {
      min-height: 720px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
      padding: 8px;
      margin-top: 12px;
    }

    .news-list {
      display: grid;
      gap: 8px;
      margin-top: 12px;
    }

    .news-row {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: 0 6px 16px rgba(15, 23, 42, 0.035);
    }

    .news-row a {
      color: var(--text);
      text-decoration: none;
      font-weight: 800;
    }

    .news-row a:hover {
      color: var(--teal);
      text-decoration: underline;
    }

    .news-meta {
      color: var(--muted);
      font-size: 13px;
      margin-top: 6px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
    }

    th, td {
      padding: 11px 12px;
      border-bottom: 1px solid #edf1f6;
      text-align: left;
      font-size: 14px;
    }

    th {
      color: var(--muted);
      background: var(--surface-2);
      font-weight: 850;
    }

    .table-wrap {
      overflow: auto;
      margin-top: 12px;
    }

    .history-filter {
      display: flex;
      gap: 10px;
      align-items: end;
      max-width: 520px;
    }

    @media (max-width: 900px) {
      .topbar, .decision { flex-direction: column; align-items: flex-start; }
      .chips, .decision-meta { justify-content: flex-start; text-align: left; }
      .toolbar, .options, .two-col, .metrics, .check-grid, .fee-grid {
        grid-template-columns: 1fr;
      }
      h1 { font-size: 24px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div>
        <div class="eyebrow">Investment Research Console</div>
        <h1>股票分析決策系統</h1>
        <p class="subtitle">自訂網頁介面，沿用既有分析模型與歷史紀錄。</p>
      </div>
      <div class="chips">
        <span class="chip">技術面</span>
        <span class="chip">K線</span>
        <span class="chip">籌碼</span>
        <span class="chip">ML</span>
        <span class="chip">新聞</span>
      </div>
    </header>

    <nav class="tabs">
      <button class="tab active" data-view="analyze">分析</button>
      <button class="tab" data-view="update">回顧更新</button>
      <button class="tab" data-view="stats">績效統計</button>
      <button class="tab" data-view="history">歷史紀錄</button>
    </nav>

    <section id="view-analyze" class="view active">
      <div class="section-title">分析條件</div>
      <div class="toolbar">
        <div class="field">
          <label for="market">市場</label>
          <select id="market"></select>
        </div>
        <div class="field">
          <label for="stock-search">股票代碼</label>
          <input id="stock-search" class="input" placeholder="搜尋代號或名稱">
        </div>
        <div class="field">
          <label for="strategy">使用策略</label>
          <select id="strategy"></select>
        </div>
        <div class="field">
          <label for="history-period">歷史資料範圍</label>
          <select id="history-period"></select>
        </div>
        <button id="analyze-btn" class="button" disabled>開始分析</button>
      </div>
      <div class="field" style="margin-top: 8px;">
        <select id="stock"></select>
      </div>

      <div class="options">
        <details>
          <summary>圖表顯示設定</summary>
          <div class="check-grid">
            <label class="checkbox"><input type="checkbox" id="show-sma20" checked>20日均線</label>
            <label class="checkbox"><input type="checkbox" id="show-sma60" checked>60日均線</label>
            <label class="checkbox"><input type="checkbox" id="show-bb" checked>布林通道</label>
            <label class="checkbox"><input type="checkbox" id="show-volume" checked>成交量</label>
            <label class="checkbox"><input type="checkbox" id="show-volume-ma" checked>成交量均量</label>
            <label class="checkbox"><input type="checkbox" id="show-rsi" checked>RSI 指標</label>
            <label class="checkbox"><input type="checkbox" id="show-macd" checked>MACD 指標</label>
          </div>
        </details>
        <details>
          <summary>持有紀錄手續費內扣設定</summary>
          <label class="checkbox" style="margin-top:14px;"><input type="checkbox" id="fee-deducted" checked>回顧報酬率內扣交易成本</label>
          <div class="fee-grid">
            <div class="field">
              <label for="buy-fee">買進手續費(%)</label>
              <input id="buy-fee" class="input" type="number" min="0" step="0.0001">
            </div>
            <div class="field">
              <label for="sell-fee">賣出手續費(%)</label>
              <input id="sell-fee" class="input" type="number" min="0" step="0.0001">
            </div>
            <div class="field">
              <label for="sell-tax">賣出交易稅/其他成本(%)</label>
              <input id="sell-tax" class="input" type="number" min="0" step="0.0001">
            </div>
          </div>
        </details>
      </div>

      <div id="analyze-status" class="status"></div>
      <div id="results"></div>
    </section>

    <section id="view-update" class="view">
      <div class="section-title">回顧更新</div>
      <button id="update-btn" class="button">執行回顧更新</button>
      <div id="update-status" class="status"></div>
      <div id="update-table" class="table-wrap"></div>
    </section>

    <section id="view-stats" class="view">
      <div class="section-title">績效統計</div>
      <button id="refresh-stats" class="button secondary">重新整理</button>
      <div id="stats-status" class="status"></div>
      <div id="stats-content"></div>
    </section>

    <section id="view-history" class="view">
      <div class="section-title">歷史紀錄</div>
      <div class="history-filter">
        <div class="field" style="flex:1;">
          <label for="history-ticker">股票代號</label>
          <input id="history-ticker" class="input" placeholder="留空看全部">
        </div>
        <button id="history-btn" class="button secondary">查詢</button>
      </div>
      <div id="history-status" class="status"></div>
      <div id="history-table" class="table-wrap"></div>
    </section>
  </main>

  <script>
    const state = {
      stocks: [],
      filteredStocks: [],
      bootstrap: null,
    };

    const $ = (id) => document.getElementById(id);

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function tone(score) {
      if (Number(score) >= 0.2) return "positive";
      if (Number(score) <= -0.2) return "negative";
      return "neutral";
    }

    function setStatus(id, text, isError = false) {
      const node = $(id);
      node.textContent = text || "";
      node.className = `status ${text ? "show" : ""} ${isError ? "error" : ""}`;
    }

    async function api(path, options = {}) {
      const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const payload = await res.json();
      if (!res.ok || payload.ok === false) {
        throw new Error(payload.error || `HTTP ${res.status}`);
      }
      return payload;
    }

    function populateSelect(select, rows, getValue, getLabel) {
      select.innerHTML = rows.map((row) => (
        `<option value="${escapeHtml(getValue(row))}">${escapeHtml(getLabel(row))}</option>`
      )).join("");
    }

    function stockLabel(stock) {
      return `${stock.code}　${stock.name}　［${stock.market}］`;
    }

    function renderStockOptions() {
      const q = $("stock-search").value.trim().toLowerCase();
      state.filteredStocks = state.stocks.filter((stock) => {
        const haystack = `${stock.code} ${stock.yf_code} ${stock.name} ${stock.market}`.toLowerCase();
        return !q || haystack.includes(q);
      });
      populateSelect($("stock"), state.filteredStocks, (s) => s.yf_code, stockLabel);
      $("analyze-btn").disabled = state.filteredStocks.length === 0;
    }

    async function loadStocks() {
      const market = $("market").value;
      const payload = await api(`/api/stocks?market=${encodeURIComponent(market)}`);
      state.stocks = payload.stocks;
      renderStockOptions();
    }

    function metric(label, value) {
      return `<div class="metric"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-value">${escapeHtml(value)}</div></div>`;
    }

    function scorePill(label, value) {
      const score = Number(value || 0);
      return `<span class="pill ${tone(score)}">${escapeHtml(label)} <strong>${score >= 0 ? "+" : ""}${score.toFixed(2)}</strong></span>`;
    }

    function renderSignals(title, score, items) {
      const rows = (items || []).slice(0, 5).map((item) => (
        `<div class="signal-item">${escapeHtml(item)}</div>`
      )).join("");
      return `<div class="panel">
        <div class="panel-head"><span>${escapeHtml(title)}</span><span class="pill ${tone(score)}">${Number(score).toFixed(2)}</span></div>
        <div class="signal-list">${rows}</div>
      </div>`;
    }

    function renderTable(rows, emptyText = "沒有資料") {
      if (!rows || rows.length === 0) {
        return `<div class="status show">${escapeHtml(emptyText)}</div>`;
      }
      const keys = Object.keys(rows[0]);
      const head = keys.map((key) => `<th>${escapeHtml(key)}</th>`).join("");
      const body = rows.map((row) => `<tr>${keys.map((key) => `<td>${escapeHtml(row[key])}</td>`).join("")}</tr>`).join("");
      return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    }

    function renderAnalyzeResult(data) {
      const rec = data.recommendation;
      const actionClass = rec.top_action === "買入" ? "buy" : rec.top_action === "賣出" ? "sell" : "hold";
      const predictions = data.predictions.map((p) => (
        metric(`${p.label}上漲機率`, p.up_probability == null ? "N/A" : `${(p.up_probability * 100).toFixed(1)}%`)
      )).join("");
      const newsRows = (data.news_items || []).map((item) => (
        `<div class="news-row">
          <span class="pill ${tone(item.score)}">${Number(item.score || 0) >= 0 ? "+" : ""}${Number(item.score || 0).toFixed(2)}</span>
          <a href="${escapeHtml(item.link || "#")}" target="_blank">${escapeHtml(item.title || "未命名新聞")}</a>
          <div class="news-meta">${escapeHtml(item.publisher || "")}</div>
        </div>`
      )).join("") || `<div class="status show">目前無法取得相關新聞。</div>`;

      $("results").innerHTML = `
        <div class="section-title">建議摘要</div>
        <div class="metrics">
          ${metric("買入", `${rec.buy_pct}%`)}
          ${metric("觀望", `${rec.hold_pct}%`)}
          ${metric("賣出", `${rec.sell_pct}%`)}
        </div>
        <div class="decision ${actionClass}">
          <div><small>最可能操作</small><strong>${escapeHtml(rec.top_action)}</strong></div>
          <div class="decision-meta">${escapeHtml(data.strategy_label)} · 持有 ${data.holding_days} 個交易日<br>綜合分數 ${Number(rec.final_score).toFixed(2)}</div>
        </div>
        <div class="score-strip">
          ${scorePill("技術面", rec.technical_score)}
          ${scorePill("K線", rec.kline_score)}
          ${scorePill("籌碼", rec.chip_score)}
          ${scorePill("ML", rec.ml_score)}
          ${scorePill("新聞", rec.news_score)}
          ${scorePill("綜合", rec.final_score)}
        </div>
        <div class="section-title">多期間預測</div>
        <div class="metrics">${predictions}</div>
        <div class="section-title">訊號摘要</div>
        <div class="two-col">
          ${renderSignals("K線訊號", data.kline_score, data.kline_signals)}
          ${renderSignals("籌碼/量價訊號", data.chip_score, data.chip_signals)}
        </div>
        <div class="section-title">價格圖表</div>
        <div id="chart"></div>
        <div class="section-title">近期新聞</div>
        <div class="news-list">${newsRows}</div>
      `;

      const chart = JSON.parse(data.chart_json);
      chart.layout = chart.layout || {};
      chart.layout.autosize = true;
      Plotly.newPlot("chart", chart.data, chart.layout, { responsive: true, displaylogo: false });
    }

    function analyzePayload() {
      return {
        ticker: $("stock").value,
        strategy_name: $("strategy").value,
        history_period: $("history-period").value,
        show_sma20: $("show-sma20").checked,
        show_sma60: $("show-sma60").checked,
        show_bb: $("show-bb").checked,
        show_volume: $("show-volume").checked,
        show_volume_ma: $("show-volume-ma").checked,
        show_rsi: $("show-rsi").checked,
        show_macd: $("show-macd").checked,
        fee_deducted: $("fee-deducted").checked,
        buy_fee_rate: Number($("buy-fee").value || 0),
        sell_fee_rate: Number($("sell-fee").value || 0),
        sell_tax_rate: Number($("sell-tax").value || 0),
      };
    }

    async function runAnalyze() {
      if (!$("stock").value) return;
      $("analyze-btn").disabled = true;
      $("results").innerHTML = "";
      setStatus("analyze-status", "分析中，正在下載股價、訓練模型並整理圖表...");
      try {
        const data = await api("/api/analyze", {
          method: "POST",
          body: JSON.stringify(analyzePayload()),
        });
        setStatus("analyze-status", `分析完成，已記錄本次建議 #${data.record_id}`);
        renderAnalyzeResult(data);
      } catch (err) {
        setStatus("analyze-status", err.message, true);
      } finally {
        $("analyze-btn").disabled = !$("stock").value;
      }
    }

    async function runUpdate() {
      setStatus("update-status", "回顧更新中...");
      $("update-table").innerHTML = "";
      try {
        const data = await api("/api/update", { method: "POST", body: "{}" });
        setStatus("update-status", `已回顧 ${data.reviewed_count} 筆紀錄`);
        $("update-table").innerHTML = renderTable(data.rows, "目前沒有到期需要回顧的建議紀錄。");
      } catch (err) {
        setStatus("update-status", err.message, true);
      }
    }

    async function loadStats() {
      setStatus("stats-status", "讀取統計中...");
      try {
        const data = await api("/api/stats");
        setStatus("stats-status", "");
        $("stats-content").innerHTML = `
          <div class="section-title">策略表現</div>
          <div class="table-wrap">${renderTable(data.strategy_rows, "目前還沒有已回顧的建議紀錄。")}</div>
          <div class="section-title">長期預測準確率比較</div>
          <div class="two-col">
            <div>${renderTable(data.accuracy_by_strategy, "尚無策略準確率資料。")}</div>
            <div>${renderTable(data.accuracy_by_action, "尚無建議動作資料。")}</div>
          </div>
          <div class="section-title">依股票</div>
          <div class="table-wrap">${renderTable(data.accuracy_by_ticker, "同一股票累積 2 筆以上有方向紀錄後才會顯示。")}</div>
        `;
      } catch (err) {
        setStatus("stats-status", err.message, true);
      }
    }

    async function loadHistory() {
      setStatus("history-status", "讀取紀錄中...");
      try {
        const ticker = $("history-ticker").value.trim();
        const data = await api(`/api/history?ticker=${encodeURIComponent(ticker)}`);
        setStatus("history-status", "");
        $("history-table").innerHTML = renderTable(data.rows, "沒有找到歷史紀錄。");
      } catch (err) {
        setStatus("history-status", err.message, true);
      }
    }

    function switchView(viewName) {
      document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === viewName));
      document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${viewName}`));
      if (viewName === "stats") loadStats();
      if (viewName === "history") loadHistory();
    }

    async function init() {
      state.bootstrap = await api("/api/bootstrap");
      populateSelect($("market"), state.bootstrap.markets, (m) => m, (m) => m);
      populateSelect($("strategy"), state.bootstrap.strategies, (s) => s.name, (s) => s.label);
      populateSelect($("history-period"), state.bootstrap.periods, (p) => p.value, (p) => p.label);
      $("history-period").value = state.bootstrap.default_period;
      $("fee-deducted").checked = state.bootstrap.default_fee_deducted;
      $("buy-fee").value = state.bootstrap.default_buy_fee_rate;
      $("sell-fee").value = state.bootstrap.default_sell_fee_rate;
      $("sell-tax").value = state.bootstrap.default_sell_tax_rate;
      await loadStocks();

      $("market").addEventListener("change", loadStocks);
      $("stock-search").addEventListener("input", renderStockOptions);
      $("stock").addEventListener("change", () => $("analyze-btn").disabled = !$("stock").value);
      $("analyze-btn").addEventListener("click", runAnalyze);
      $("update-btn").addEventListener("click", runUpdate);
      $("refresh-stats").addEventListener("click", loadStats);
      $("history-btn").addEventListener("click", loadHistory);
      document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchView(tab.dataset.view)));
    }

    init().catch((err) => setStatus("analyze-status", err.message, true));
  </script>
</body>
</html>
"""


def _download_and_prepare(ticker: str, period: str) -> pd.DataFrame:
    raw = yf.download(ticker, period=period, progress=False, auto_adjust=True)
    if raw.empty:
        raise ValueError(f"無法取得 {ticker} 的股價資料,請確認代號是否正確。")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    return add_all_indicators(raw)


def _json_safe(value):
    if value is None:
        return None
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _stock_dict(row):
    code, yf_code, name, market = row
    return {"code": code, "yf_code": yf_code, "name": name, "market": market}


def _history_row(row):
    return {
        "時間": row.get("created_at"),
        "代號": row.get("ticker"),
        "策略": config.get_strategy_label(row.get("strategy")),
        "建議": row.get("top_action"),
        "買入%": row.get("buy_pct"),
        "觀望%": row.get("hold_pct"),
        "賣出%": row.get("sell_pct"),
        "狀態": "已回顧" if row.get("outcome_checked") else "待回顧",
        "扣費後報酬%": row.get("actual_return"),
    }


def api_bootstrap():
    return {
        "markets": MARKET_OPTIONS,
        "strategies": [
            {"name": name, "label": config.get_strategy_label(name)}
            for name in config.STRATEGIES
        ],
        "periods": [
            {"value": period, "label": config.PRICE_HISTORY_PERIOD_LABELS.get(period, period)}
            for period in config.PRICE_HISTORY_PERIOD_OPTIONS
        ],
        "default_period": config.PRICE_HISTORY_PERIOD,
        "default_fee_deducted": config.DEFAULT_FEE_DEDUCTED,
        "default_buy_fee_rate": config.DEFAULT_BUY_FEE_RATE,
        "default_sell_fee_rate": config.DEFAULT_SELL_FEE_RATE,
        "default_sell_tax_rate": config.DEFAULT_SELL_TAX_RATE,
    }


def api_stocks(query):
    market = query.get("market", ["全部市場"])[0]
    return {"stocks": [_stock_dict(row) for row in list_stocks(market)]}


def api_analyze(payload):
    ticker = (payload.get("ticker") or "").strip()
    if not ticker:
        raise ValueError("請先選擇股票代碼。")

    strategy_name = config.resolve_strategy_name(payload.get("strategy_name") or config.DEFAULT_STRATEGY)
    if strategy_name not in config.STRATEGIES:
        raise ValueError("找不到指定策略。")
    strategy = config.STRATEGIES[strategy_name]

    df = _download_and_prepare(ticker, payload.get("history_period") or config.PRICE_HISTORY_PERIOD)
    tech_score_val = technical_score(df)
    kline_score_val, kline_signals = candlestick_score(df)
    chip_score_val, chip_signals = chip_score(df)

    horizon_predictions = predict_horizons(df, horizons=config.PREDICTION_HORIZONS.keys())
    day1_prediction = horizon_predictions.get(1, {})
    if day1_prediction.get("up_probability") is not None:
        ml_score_val = ml_score(day1_prediction["up_probability"])
    else:
        ml_score_val = 0.0

    news_score_val, news_items = analyze_news_sentiment(ticker)
    recommendation = build_recommendation(
        tech_score_val,
        ml_score_val,
        news_score_val,
        strategy,
        kline_score_val=kline_score_val,
        chip_score_val=chip_score_val,
    )

    latest_price = float(df["Close"].iloc[-1])
    record_id = storage.save_recommendation(
        ticker,
        strategy_name,
        latest_price,
        recommendation,
        strategy["holding_days"],
        fee_deducted=bool(payload.get("fee_deducted", config.DEFAULT_FEE_DEDUCTED)),
        buy_fee_rate=float(payload.get("buy_fee_rate", config.DEFAULT_BUY_FEE_RATE)),
        sell_fee_rate=float(payload.get("sell_fee_rate", config.DEFAULT_SELL_FEE_RATE)),
        sell_tax_rate=float(payload.get("sell_tax_rate", config.DEFAULT_SELL_TAX_RATE)),
    )

    fig = build_figure(
        ticker,
        df,
        show_sma20=bool(payload.get("show_sma20", True)),
        show_sma60=bool(payload.get("show_sma60", True)),
        show_bb=bool(payload.get("show_bb", True)),
        show_volume=bool(payload.get("show_volume", True)),
        show_volume_ma=bool(payload.get("show_volume_ma", True)),
        show_rsi=bool(payload.get("show_rsi", True)),
        show_macd=bool(payload.get("show_macd", True)),
    )

    predictions = []
    for horizon, label in config.PREDICTION_HORIZONS.items():
        pred = horizon_predictions.get(horizon, {})
        predictions.append({
            "horizon": horizon,
            "label": label,
            "up_probability": pred.get("up_probability"),
            "accuracy": pred.get("accuracy"),
            "reason": pred.get("reason"),
        })

    return {
        "record_id": record_id,
        "ticker": ticker,
        "strategy_label": config.get_strategy_label(strategy_name),
        "holding_days": strategy["holding_days"],
        "recommendation": recommendation,
        "kline_score": kline_score_val,
        "chip_score": chip_score_val,
        "kline_signals": kline_signals,
        "chip_signals": chip_signals,
        "predictions": predictions,
        "news_items": news_items,
        "chart_json": fig.to_json(),
    }


def api_update():
    pending = storage.get_pending_reviews()
    rows = []
    for rec in pending:
        recent = yf.download(rec["ticker"], period="5d", progress=False, auto_adjust=True)
        if recent.empty:
            continue
        if isinstance(recent.columns, pd.MultiIndex):
            recent.columns = recent.columns.get_level_values(0)
        latest_price = float(recent["Close"].iloc[-1])
        returns = storage.update_outcome(rec["id"], latest_price)
        if returns is None:
            continue
        rows.append({
            "編號": rec["id"],
            "代號": rec["ticker"],
            "策略": config.get_strategy_label(rec["strategy"]),
            "建議": rec["top_action"],
            "價格漲跌%": round(returns["gross_price_return"], 2),
            "方向毛報酬%": round(returns["action_return"], 2),
            "扣費後報酬%": round(returns["net_return"], 2),
            "扣除費率%": round(returns["total_fee_rate"], 4),
        })
    return {"reviewed_count": len(rows), "rows": rows}


def api_stats():
    stats = storage.get_strategy_stats()
    strategy_rows = []
    for name, row in stats.items():
        strategy_rows.append({
            "策略": config.get_strategy_label(name),
            "已回顧建議數": row["total_recommendations"],
            "有方向建議數": row["directional_recommendations"],
            "長期方向勝率%": row["directional_win_rate_pct"],
            "平均價格漲跌%": row["avg_price_return_pct"],
            "平均方向毛報酬%": row["avg_action_return_pct"],
            "平均扣費後報酬%": row["avg_net_return_pct"],
        })

    by_strategy = []
    for row in storage.get_accuracy_breakdown("strategy"):
        by_strategy.append({
            "策略": config.get_strategy_label(row["group"]),
            "有方向筆數": row["directional_count"],
            "正確筆數": row["correct_count"],
            "準確率%": row["accuracy_pct"],
            "平均扣費後報酬%": row["avg_net_return_pct"],
        })

    by_action = []
    for row in storage.get_accuracy_breakdown("top_action"):
        by_action.append({
            "建議動作": row["group"],
            "有方向筆數": row["directional_count"],
            "正確筆數": row["correct_count"],
            "準確率%": row["accuracy_pct"],
            "平均扣費後報酬%": row["avg_net_return_pct"],
        })

    by_ticker = []
    for row in storage.get_accuracy_breakdown("ticker", min_count=2):
        by_ticker.append({
            "代號": row["group"],
            "有方向筆數": row["directional_count"],
            "正確筆數": row["correct_count"],
            "準確率%": row["accuracy_pct"],
            "平均扣費後報酬%": row["avg_net_return_pct"],
        })

    return {
        "strategy_rows": strategy_rows,
        "accuracy_by_strategy": by_strategy,
        "accuracy_by_action": by_action,
        "accuracy_by_ticker": by_ticker,
    }


def api_history(query):
    ticker = (query.get("ticker", [""])[0] or "").strip()
    rows = [_history_row(row) for row in storage.get_history(ticker or None)]
    return {"rows": rows}


class AppHandler(BaseHTTPRequestHandler):
    server_version = "StockAdvisorHTTP/1.0"

    def log_message(self, fmt, *args):
        return

    def _send_bytes(self, body: bytes, status=HTTPStatus.OK, content_type="text/html; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(_json_safe({"ok": True, **payload}), ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, status=status, content_type="application/json; charset=utf-8")

    def _send_error_json(self, message, status=HTTPStatus.INTERNAL_SERVER_ERROR):
        body = json.dumps({"ok": False, "error": str(message)}, ensure_ascii=False).encode("utf-8")
        self._send_bytes(body, status=status, content_type="application/json; charset=utf-8")

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/":
                self._send_bytes(APP_HTML.encode("utf-8"))
            elif parsed.path == "/plotly.min.js":
                plotly_js = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
                self._send_bytes(plotly_js.read_bytes(), content_type="application/javascript; charset=utf-8")
            elif parsed.path == "/api/bootstrap":
                self._send_json(api_bootstrap())
            elif parsed.path == "/api/stocks":
                self._send_json(api_stocks(query))
            elif parsed.path == "/api/stats":
                self._send_json(api_stats())
            elif parsed.path == "/api/history":
                self._send_json(api_history(query))
            else:
                content_type = mimetypes.guess_type(parsed.path)[0] or "text/plain; charset=utf-8"
                self._send_bytes(b"Not found", status=HTTPStatus.NOT_FOUND, content_type=content_type)
        except Exception as exc:
            traceback.print_exc()
            self._send_error_json(exc)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/analyze":
                self._send_json(api_analyze(payload))
            elif parsed.path == "/api/update":
                self._send_json(api_update())
            else:
                self._send_error_json("Not found", HTTPStatus.NOT_FOUND)
        except Exception as exc:
            traceback.print_exc()
            self._send_error_json(exc)


def run(host: str, port: int):
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"股票分析決策系統已啟動: http://{host}:{port}")
    print("按 Ctrl+C 可停止服務。")
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="不使用 Streamlit 的股票分析網頁介面")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    run(args.host, args.port)


if __name__ == "__main__":
    main()
