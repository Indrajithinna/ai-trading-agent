"""
Backtest Analytics — Rich HTML Report Generator
=================================================
Generates an interactive, self-contained HTML report with charts
from the backtest results dictionary.
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime

from ai_trading_agent.utils.logger import get_logger

logger = get_logger("BacktestAnalytics")


def generate_html_report(report: Dict[str, Any], output_path: str):
    """
    Render the backtest report dict into a stunning single-file HTML page
    with embedded Chart.js visualisations.
    """
    meta = report["meta"]
    s = report["summary"]
    sb = report["strategy_breakdown"]
    exit_reasons = report["exit_reason_breakdown"]
    monthly_pnl = report.get("monthly_pnl", {})
    yearly_pnl = report.get("yearly_pnl", {})
    eq = report.get("equity_curve", {"dates": [], "values": []})
    trades = report.get("trades", [])

    # ── helpers for conditionally colouring numbers ──────────────────────
    def colour(val, fmt=",.2f"):
        c = "#00e676" if val >= 0 else "#ff5252"
        return f'<span style="color:{c}">₹{val:{fmt}}</span>'

    def pct_colour(val, fmt=".2f"):
        c = "#00e676" if val >= 0 else "#ff5252"
        return f'<span style="color:{c}">{val:{fmt}}%</span>'

    # ── monthly heatmap data ─────────────────────────────────────────────
    years_set = sorted({k[:4] for k in monthly_pnl})
    months_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    heatmap_rows = ""
    for yr in years_set:
        cells = ""
        for m in range(1, 13):
            key = f"{yr}-{m:02d}"
            val = monthly_pnl.get(key, 0)
            bg = (
                f"rgba(0,230,118,{min(abs(val)/500, 1):.2f})"
                if val >= 0
                else f"rgba(255,82,82,{min(abs(val)/500, 1):.2f})"
            )
            cells += f'<td style="background:{bg};text-align:center;padding:6px 4px;font-size:12px;">₹{val:,.0f}</td>'
        heatmap_rows += f"<tr><td style='font-weight:700;padding:6px 10px;'>{yr}</td>{cells}</tr>"

    # ── Trade log (last 100) ─────────────────────────────────────────────
    trade_rows = ""
    for t in trades[-200:]:
        pnl_c = "#00e676" if t.get("pnl", 0) >= 0 else "#ff5252"
        trade_rows += (
            f"<tr>"
            f"<td>{t.get('trade_id','')}</td>"
            f"<td>{t.get('symbol','')}</td>"
            f"<td>{t.get('strategy','')}</td>"
            f"<td>{t.get('direction','')}</td>"
            f"<td>₹{t.get('entry_price',0):,.2f}</td>"
            f"<td>₹{t.get('exit_price',0):,.2f}</td>"
            f"<td style='color:{pnl_c}'>₹{t.get('pnl',0):,.2f}</td>"
            f"<td>{t.get('exit_reason','')}</td>"
            f"<td>{t.get('entry_date','')}</td>"
            f"<td>{t.get('exit_date','')}</td>"
            f"<td>{t.get('bars_held',0)}</td>"
            f"</tr>"
        )

    # ── strategy chart data ──────────────────────────────────────────────
    strat_names = list(sb.keys())
    strat_pnls = [sb[n]["net_pnl"] for n in strat_names]
    strat_wr = [sb[n]["win_rate"] for n in strat_names]
    strat_trades_cnt = [sb[n]["total_trades"] for n in strat_names]

    # ── yearly bar data ──────────────────────────────────────────────────
    yr_labels = list(yearly_pnl.keys())
    yr_values = list(yearly_pnl.values())
    yr_colours = ["#00e676" if v >= 0 else "#ff5252" for v in yr_values]

    # ── exit pie data ────────────────────────────────────────────────────
    exit_labels = list(exit_reasons.keys())
    exit_values = list(exit_reasons.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Trading Agent — Backtest Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #00e676; --red: #ff5252; --gold: #ffc107;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); line-height: 1.6;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

  /* ── Header ─────────────────────────────────── */
  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: 16px; padding: 36px 40px; margin-bottom: 28px;
    border: 1px solid var(--border);
    box-shadow: 0 8px 32px rgba(0,0,0,.35);
  }}
  .header h1 {{ font-size: 28px; font-weight: 700; }}
  .header h1 span {{ color: var(--accent); }}
  .header .meta {{ color: var(--muted); margin-top: 8px; font-size: 14px; }}

  /* ── KPI grid ───────────────────────────────── */
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px; margin-bottom: 28px;
  }}
  .kpi {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px;
    transition: transform .15s;
  }}
  .kpi:hover {{ transform: translateY(-3px); }}
  .kpi .label {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }}
  .kpi .value {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}

  /* ── Cards ──────────────────────────────────── */
  .card {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }}
  .card h2 {{ font-size: 18px; margin-bottom: 16px; color: var(--accent); }}

  /* ── Table ──────────────────────────────────── */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #21262d; padding: 10px 8px; text-align: left; font-weight: 600;
       color: var(--muted); text-transform: uppercase; letter-spacing: .5px; font-size: 11px; }}
  td {{ padding: 8px; border-bottom: 1px solid var(--border); }}
  tr:hover {{ background: rgba(88,166,255,.06); }}

  /* ── Charts row ─────────────────────────────── */
  .chart-row {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;
  }}
  @media (max-width: 900px) {{ .chart-row {{ grid-template-columns: 1fr; }} }}
  .chart-box {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px;
  }}
  .chart-box h3 {{ font-size: 15px; color: var(--muted); margin-bottom: 12px; }}
  canvas {{ width: 100% !important; }}

  /* ── Heatmap ────────────────────────────────── */
  .heatmap table {{ border-spacing: 2px; border-collapse: separate; }}
  .heatmap th {{ font-size: 11px; padding: 6px 4px; }}
</style>
</head>
<body>
<div class="container">

<!-- ═══ HEADER ════════════════════════════════════════ -->
<div class="header">
  <h1>📊 AI Trading Agent — <span>Backtest Report</span></h1>
  <div class="meta">
    Symbols: {', '.join(meta['symbols'])} &nbsp;|&nbsp;
    Period: {meta['years']} years &nbsp;|&nbsp;
    Bars: {meta['total_bars_processed']:,} &nbsp;|&nbsp;
    Generated: {meta['generated_at'][:19]}
  </div>
</div>

<!-- ═══ KPI GRID ═════════════════════════════════════ -->
<div class="kpi-grid">
  <div class="kpi"><div class="label">Total Return</div><div class="value">{pct_colour(s['total_return_pct'])}</div></div>
  <div class="kpi"><div class="label">Net P&amp;L</div><div class="value">{colour(s['net_pnl'])}</div></div>
  <div class="kpi"><div class="label">Win Rate</div><div class="value">{pct_colour(s['win_rate'])}</div></div>
  <div class="kpi"><div class="label">Profit Factor</div><div class="value" style="color:var(--gold)">{s['profit_factor']:.2f}</div></div>
  <div class="kpi"><div class="label">Total Trades</div><div class="value" style="color:var(--accent)">{s['total_trades']}</div></div>
  <div class="kpi"><div class="label">Sharpe Ratio</div><div class="value" style="color:var(--gold)">{s['sharpe_ratio']:.2f}</div></div>
  <div class="kpi"><div class="label">Sortino Ratio</div><div class="value" style="color:var(--gold)">{s['sortino_ratio']:.2f}</div></div>
  <div class="kpi"><div class="label">Max Drawdown</div><div class="value" style="color:var(--red)">₹{s['max_drawdown']:,.0f} ({s['max_drawdown_pct']:.1f}%)</div></div>
  <div class="kpi"><div class="label">Final Capital</div><div class="value">{colour(s['final_capital'], ',.0f')}</div></div>
  <div class="kpi"><div class="label">Expectancy</div><div class="value">{colour(s['expectancy'])}</div></div>
  <div class="kpi"><div class="label">Avg Win</div><div class="value" style="color:var(--green)">₹{s['avg_win']:,.2f}</div></div>
  <div class="kpi"><div class="label">Avg Loss</div><div class="value" style="color:var(--red)">₹{s['avg_loss']:,.2f}</div></div>
</div>

<!-- ═══ CHARTS ROW 1 ═════════════════════════════════ -->
<div class="chart-row">
  <div class="chart-box">
    <h3>📈 Equity Curve</h3>
    <canvas id="equityChart" height="260"></canvas>
  </div>
  <div class="chart-box">
    <h3>📊 Yearly P&amp;L</h3>
    <canvas id="yearlyChart" height="260"></canvas>
  </div>
</div>

<!-- ═══ CHARTS ROW 2 ═════════════════════════════════ -->
<div class="chart-row">
  <div class="chart-box">
    <h3>🎯 Strategy Win-Rate &amp; P&amp;L</h3>
    <canvas id="stratChart" height="260"></canvas>
  </div>
  <div class="chart-box">
    <h3>🚪 Exit Reasons</h3>
    <canvas id="exitPieChart" height="260"></canvas>
  </div>
</div>

<!-- ═══ STRATEGY BREAKDOWN TABLE ═════════════════════ -->
<div class="card">
  <h2>📈 Strategy Breakdown</h2>
  <table>
    <thead><tr><th>Strategy</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>Net P&amp;L</th><th>Avg P&amp;L</th><th>Best</th><th>Worst</th></tr></thead>
    <tbody>
    {"".join(
        f"<tr>"
        f"<td style='font-weight:600'>{name}</td>"
        f"<td>{data['total_trades']}</td>"
        f"<td style='color:var(--green)'>{data['wins']}</td>"
        f"<td style='color:var(--red)'>{data['losses']}</td>"
        f"<td>{data['win_rate']:.1f}%</td>"
        f"<td>{colour(data['net_pnl'])}</td>"
        f"<td>{colour(data['avg_pnl'])}</td>"
        f"<td style='color:var(--green)'>₹{data['largest_win']:,.2f}</td>"
        f"<td style='color:var(--red)'>₹{data['largest_loss']:,.2f}</td>"
        f"</tr>"
        for name, data in sb.items()
    )}
    </tbody>
  </table>
</div>

<!-- ═══ MONTHLY HEATMAP ══════════════════════════════ -->
<div class="card heatmap">
  <h2>🗓️ Monthly P&amp;L Heatmap</h2>
  <div style="overflow-x:auto">
  <table>
    <thead><tr><th>Year</th>{"".join(f'<th>{m}</th>' for m in months_labels)}</tr></thead>
    <tbody>{heatmap_rows}</tbody>
  </table>
  </div>
</div>

<!-- ═══ TRADE LOG ════════════════════════════════════ -->
<div class="card">
  <h2>📝 Trade Log (last 200)</h2>
  <div style="overflow-x:auto; max-height:500px; overflow-y:auto;">
  <table>
    <thead><tr><th>#</th><th>Symbol</th><th>Strategy</th><th>Dir</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>Reason</th><th>Entry Date</th><th>Exit Date</th><th>Bars</th></tr></thead>
    <tbody>{trade_rows}</tbody>
  </table>
  </div>
</div>

</div><!-- /container -->

<!-- ═══ CHART.JS SCRIPTS ═════════════════════════════ -->
<script>
const darkGrid = {{ color: 'rgba(255,255,255,.06)' }};
const darkTick = {{ color: '#8b949e', font: {{ size: 11 }} }};

// ── Equity Curve ──────────────────────────────────
new Chart(document.getElementById('equityChart'), {{
  type: 'line',
  data: {{
    labels: {json.dumps(eq['dates'])},
    datasets: [{{
      label: 'Equity (₹)',
      data: {json.dumps(eq['values'])},
      borderColor: '#58a6ff',
      backgroundColor: 'rgba(88,166,255,.08)',
      fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ display: true, ticks: {{ ...darkTick, maxTicksLimit: 12 }}, grid: darkGrid }},
      y: {{ ticks: darkTick, grid: darkGrid }}
    }}
  }}
}});

// ── Yearly P&L Bar ────────────────────────────────
new Chart(document.getElementById('yearlyChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(yr_labels)},
    datasets: [{{
      label: 'P&L (₹)',
      data: {json.dumps(yr_values)},
      backgroundColor: {json.dumps(yr_colours)},
      borderRadius: 6
    }}]
  }},
  options: {{
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: darkTick, grid: darkGrid }},
      y: {{ ticks: darkTick, grid: darkGrid }}
    }}
  }}
}});

// ── Strategy Grouped Bar ──────────────────────────
new Chart(document.getElementById('stratChart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps(strat_names)},
    datasets: [
      {{
        label: 'Net P&L (₹)',
        data: {json.dumps(strat_pnls)},
        backgroundColor: 'rgba(88,166,255,.7)',
        borderRadius: 6, yAxisID: 'y'
      }},
      {{
        label: 'Win Rate (%)',
        data: {json.dumps(strat_wr)},
        backgroundColor: 'rgba(0,230,118,.6)',
        borderRadius: 6, yAxisID: 'y1'
      }}
    ]
  }},
  options: {{
    plugins: {{ legend: {{ labels: {{ color: '#8b949e' }} }} }},
    scales: {{
      x: {{ ticks: darkTick, grid: darkGrid }},
      y: {{ position: 'left', ticks: darkTick, grid: darkGrid, title: {{ display: true, text: 'P&L (₹)', color: '#8b949e' }} }},
      y1: {{ position: 'right', ticks: darkTick, grid: {{ display: false }}, title: {{ display: true, text: 'Win Rate %', color: '#8b949e' }}, min: 0, max: 100 }}
    }}
  }}
}});

// ── Exit Pie ──────────────────────────────────────
new Chart(document.getElementById('exitPieChart'), {{
  type: 'doughnut',
  data: {{
    labels: {json.dumps(exit_labels)},
    datasets: [{{
      data: {json.dumps(exit_values)},
      backgroundColor: ['#58a6ff','#00e676','#ff5252','#ffc107','#ce93d8','#4dd0e1','#ff8a65'],
      borderWidth: 0
    }}]
  }},
  options: {{
    plugins: {{
      legend: {{ position: 'bottom', labels: {{ color: '#8b949e', padding: 14 }} }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"✅ HTML report written to {output_path}")
