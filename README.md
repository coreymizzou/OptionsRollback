# Options Scanner — RL Decision Layer

A reinforcement learning decision system that wraps your options scanner with a 60-second evaluation loop, position tracking, hard risk rules, and an online-learning agent that improves over time.

---

## File Structure

```
your_folder/
├── options_scanner.py          ← main scanner (add new tickers here)
│
└── rl_system/
    ├── config.py               ← ALL tunable parameters — start here
    ├── database.py             ← SQLite persistence layer
    ├── notifier.py             ← Terminal + toast + Discord alerts
    ├── position_tracker.py     ← Position lifecycle + hard risk rules
    ├── rl_agent.py             ← Contextual bandit decision agent
    ├── broker.py               ← Alpaca paper trading execution layer
    ├── run.py                  ← Main orchestration loop
    └── requirements_rl.txt     ← pip dependencies
```

---

## Setup

```bash
# 1. Install dependencies
pip install -r rl_system/requirements_rl.txt

# 2. Set API keys (Mac/Linux)
export TRADIER_API_KEY="your_tradier_production_key"
export FRED_API_KEY="your_fred_key"

# For live paper trading (optional)
export ALPACA_API_KEY="your_alpaca_paper_key"
export ALPACA_SECRET_KEY="your_alpaca_paper_secret"

# Mac — make permanent
echo 'export TRADIER_API_KEY="your_key"' >> ~/.zshrc
echo 'export ALPACA_API_KEY="your_key"' >> ~/.zshrc
echo 'export ALPACA_SECRET_KEY="your_key"' >> ~/.zshrc
source ~/.zshrc

# Windows PowerShell — set for session
$env:TRADIER_API_KEY = "your_key"

# Windows — make permanent
# Search "Environment Variables" in Windows settings → User Variables → New

# 3. Run from your main folder (where options_scanner.py lives)
cd your_folder
python3 rl_system/run.py --paper
```

---

## CLI Commands

```bash
# ── Run modes ─────────────────────────────────────────────────────
python3 rl_system/run.py --paper              # paper mode — manual fills via ThinkorSwim
python3 rl_system/run.py --auto               # fully autonomous — no user input, % based limits
python3 rl_system/run.py --bankroll 5000      # bankroll mode — $5k pool, compounds profits
python3 rl_system/run.py --live-paper --bankroll 5000  # live paper — real Alpaca fills + web dashboard
python3 rl_system/run.py --live-paper --auto  # live paper with no position limit
python3 rl_system/run.py --debug              # verbose output

# ── Status and diagnostics ────────────────────────────────────────
python3 rl_system/run.py --status             # full status: positions, P&L, capital deployed
python3 rl_system/run.py --weights            # agent weight summary

# ── Position management ───────────────────────────────────────────
python3 rl_system/run.py --close 1            # mark position #1 as manually closed
python3 rl_system/run.py --close-all          # close all open positions
python3 rl_system/run.py --delete 1           # delete position #1 (unfilled order, no record kept)

# ── Reset ─────────────────────────────────────────────────────────
python3 rl_system/run.py --reset              # clear positions/history, keep agent weights
python3 rl_system/run.py --reset-all          # wipe everything including agent weights
```

---

## Run Modes Explained

### `--paper` (manual)
Prompts you for confirmation on every entry and exit. You execute trades in ThinkorSwim and confirm fills in the terminal. Max 3 concurrent positions.

### `--auto` (fully autonomous)
No user input required. System enters and exits automatically based on signals. No position limit — capped at 10 positions and 40% of account capital by default.

```
[AUTO] ENTER GOOGL #1 @ $8.94  (LONG_CALL) conf=68%
[AUTO] EXIT  MSFT  @ $17.23    P&L: +$311.00 (+0.22R)
```

### `--bankroll AMOUNT` (compounding pool)
Specify a fixed dollar pool. System trades autonomously using only that pool — always 1 contract per trade. Profits from closes flow back into the pool and are immediately available for new trades. Entries stop when the pool can't cover the next premium.

```
[BANKROLL] ENTER NVDA #3 @ $6.95  cost=$695.00  remaining=$3,412.00
[BANKROLL] TARGET_HIT closed — proceeds $1,390.00 returned. Bankroll now: $4,802.00
```

### `--live-paper` (Alpaca paper execution)
Combines with `--auto` or `--bankroll`. Sends real orders to your Alpaca paper trading account instead of just tracking at mid price. Gives realistic fills. Positions visible at:

```
https://app.alpaca.markets/paper-trading/overview
```

Data source split:
- **Market data** (scanner, prices, Greeks, flow) → Tradier production API (real-time)
- **Order execution** (entries, exits, fills) → Alpaca paper API

Requires `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` environment variables.

---

## Typical Daily Workflow

### Manual mode (`--paper`)
```
1. Start loop at 10am:
   python3 rl_system/run.py --paper

2. Watch for ENTER alerts → place trade in ThinkorSwim → say y after fill confirmed

3. Monitor tick bar every 60 seconds:
   [10:05 ET] tick=12 RISK_OFF VIX=31  |  CRWD#1 +$124 +0.25R  |  MU#2 +$47 +0.09R

4. When EXIT/TARGET_HIT fires → close in ThinkorSwim → confirm fill price in terminal

5. End of day:
   python3 rl_system/run.py --status
```

### Autonomous mode (`--auto` / `--bankroll` / `--live-paper`)
```
1. Start and leave running:
   python3 rl_system/run.py --live-paper --bankroll 5000

2. Check in anytime without stopping:
   python3 rl_system/run.py --status

3. Watch Alpaca dashboard for real-time position visibility:
   https://app.alpaca.markets/paper-trading/overview
```

---

## How It Works

### Every 60 seconds (one tick)

1. **Hard rules evaluated first** — stop loss, profit target, DTE expiry. Always fire, cannot be overridden.
2. **Open positions scored** — agent outputs HOLD or EXIT with confidence.
3. **New candidates scored** — agent outputs ENTER or WAIT for top 5 scanner results.
4. **Tick status bar printed** — time, regime, VIX, all open position P&L.

### Every 5 minutes

- Full scanner runs on all 19 watchlist tickers (~2 minutes)
- Results sorted by confluence score
- OI compared to previous scan for flow validation

### When a position closes

- Reward computed and agent weights updated
- 24-hour cooldown set on that ticker
- In bankroll mode: proceeds credited back to pool
- In live-paper mode: closing order sent to Alpaca

---

## Hard Risk Rules

These fire regardless of agent confidence. Cannot be disabled.

| Rule | Default | Config Key |
|------|---------|------------|
| Stop loss | Down 50% from entry | `STOP_LOSS_PCT` |
| Profit target | Up 100% (2x) | `PROFIT_TARGET_PCT` |
| DTE force-close | 7 days to expiry | `CLOSE_BEFORE_DTE` |
| Max concurrent (paper) | 3 positions | `MAX_CONCURRENT_POSITIONS` |
| Max concurrent (auto) | 10 positions | `AUTO_MAX_POSITIONS` |
| Max capital (auto) | 40% of account | `AUTO_MAX_CAPITAL_PCT` |
| Daily drawdown | Down 6% of account | `MAX_DAILY_DRAWDOWN_PCT` |
| Cooldown | 24 hours post-close | `COOLDOWN_HOURS` |

**Grace period:** Hard rules suppressed for the first 10 minutes after entry.

**Price sanity check:** If fetched price is >2.2x entry price in the first 30 minutes, hard rules skip that tick to protect against bad data.

---

## Exit Strategy

Three layers, in priority order:

**Layer 1 — Hard rules** (always fire)
Stop loss at -50%, profit target at +100%, DTE force-close at 7 days.

**Layer 2 — Agent exit scoring**
Rule-based scoring that pushes toward exit when multiple signals confirm:

| Condition | Score added |
|-----------|------------|
| Gain ≥ 0.75R | +0.45 |
| Gain ≥ 0.50R | +0.42 |
| Gain ≥ 0.50R held overnight | +0.08 bonus |
| Gain ≥ 0.40R held overnight | +0.35 |
| Loss ≤ -0.40R | +0.42 |
| DTE 14-21 days | +0.10 |
| DTE 7-14 days | +0.20 |
| Theta >4%/day after day 7 | +0.18 |
| Stalled >10 days near breakeven | +0.15 |
| Market reversal >1% against | +0.15 |
| Multiple signals confirming | +0.12 bonus |

Exit fires when total score ≥ 0.55.

**Layer 3 — Manual** (`--close ID` or `--close-all`)

---

## Tier 1 Features

### Time-of-Day Filter
New entries blocked before 10:00am ET and after 3:30pm ET. Hard exits always fire.

### Action State Expiry
Action states expire after 20 hours so yesterday's signals don't suppress today's.

### Live Tick Status Bar
```
[10:05 ET] tick=12 RISK_OFF VIX=31  |  CRWD#1 +$124 +0.25R  |  MU#2 +$47 +0.09R
```
Suppressed overnight when no positions are open.

---

## Tier 2 Features

### Earnings Calendar
Warns within 5 days, blocks entry within 2 days of earnings report. Uses Tradier API with yfinance fallback. Cached 6 hours.

### Sector Correlation
Warns when adding a position creates too much concentration in one sector or direction. Warns but does not block.

### OI Change Detection
Compares open interest between scans. Closing flow (OI decreasing) reduces confidence 25%.

---

## The Learning Agent

Starts pure rule-based. After 10 closed trades, begins blending learned weights (up to 60%).

**12 features per decision:** unrealized_r, dte_fraction, theta_decay_fraction, iv_rank_normalized, spy_trend, rsi_normalized, flow_score_normalized, above_vwap, regime_score, ticks_held_normalized, spread_vs_target, days_since_entry_norm.

**Reward:** `realized_R - 0.5 (stop hit) - 0.3 (drawdown) - 0.2 (churn)`

---

## Watchlist (19 tickers)

| Ticker | Sector |
|--------|--------|
| NVDA, AMD, MU | Semiconductors |
| AAPL, MSFT, GOOGL, META, AMZN | Mega-cap tech |
| CRWD | Cybersecurity |
| CRM, PLTR | Cloud software |
| NFLX | Media tech |
| TSLA | EV / Auto |
| COIN, MSTR | Crypto-adjacent |
| GS | Financials |
| XOM | Energy |
| GLD | Commodities |
| MELI | International growth |

To add tickers: add to `WATCHLIST` in `options_scanner.py` AND to `SECTOR_MAP` in `config.py`.

---

## Data Architecture

```
Market data (real-time):
  Tradier production API → options chains, Greeks, flow, IV, prices

Order execution:
  Alpaca paper API → entries, exits, fill prices, web dashboard

Price fetching for P&L:
  1. Tradier live bid/ask mid (primary)
  2. yfinance option chain mid (fallback)
  3. Entry price (last resort)
```

For spreads, both legs are fetched independently and net value computed: `long_mid - short_mid`.

---

## Notifications

| Channel | How to enable |
|---------|--------------|
| Terminal | Always on |
| Windows toast | `pip install winotify` |
| Mac notifications | `pip install pyobjus` — or disable: `NOTIFY_WINDOWS_TOAST = False` |
| Discord | Set `NOTIFY_DISCORD_WEBHOOK_URL` in config.py |

---

## Database

All data persists in `scanner_data.db` (SQLite, gitignored).

| Table | Contents |
|-------|----------|
| `positions` | All open and closed positions with P&L |
| `tick_snapshots` | Every 60-second evaluation per position |
| `recommendations` | Every user-facing alert sent |
| `trade_journal` | Human-readable event log |
| `agent_weights` | Learned model weights |
| `cooldowns` | Active ticker cooldowns |
| `system_state` | Action state and persistent loop state |

```bash
# On Mac/Linux use Python since sqlite3 CLI may not be installed
python3 -c "
import sqlite3
conn = sqlite3.connect('scanner_data.db')
conn.row_factory = sqlite3.Row

# Open positions
rows = conn.execute('SELECT ticker, strategy, entry_price, stop_price, target_price FROM positions WHERE status=\'OPEN\'').fetchall()
for r in rows: print(dict(r))

# Closed trades
rows = conn.execute('SELECT ticker, realized_r, realized_pnl, exit_reason FROM positions WHERE status=\'CLOSED\' ORDER BY exit_time DESC').fetchall()
for r in rows: print(dict(r))
"
```

---

## Architecture Notes

- Hard risk rules in `position_tracker.py` cannot be overridden by the agent
- Three-layer false-exit protection: 10-min grace period + correct contract pricing + price sanity check
- Spread P&L fetches both legs (long_mid - short_mid) to match ThinkorSwim
- Agent learning is additive — `--reset` clears history but keeps weights
- All state survives a restart — positions, weights, cooldowns, action states
- Weights saved every 10 ticks and on every position close
- `scanner_data.db` and `logs/` are gitignored — never committed

---

## Troubleshooting

**"OUTSIDE market hours"** — correct before 10am or after 3:30pm ET. No entries until market hours.

**"Windows toast failed"** — set `NOTIFY_WINDOWS_TOAST = False` in config.py. Terminal alerts still work.

**P&L doesn't match ThinkorSwim** — system uses mid price, ThinkorSwim shows bid. Difference is normal bid/ask slippage (~$5-20 per contract). In `--live-paper` mode fills are at actual Alpaca prices.

**Tradier API key returning 401** — verify key with: `echo $TRADIER_API_KEY` (Mac) or `$env:TRADIER_API_KEY` (Windows PowerShell).

**Scanner not importing** — run from the folder containing `options_scanner.py`. Command must be `python3 rl_system/run.py` not `python3 run.py`.

**git pull fails with scanner_data.db conflict** — run:
```bash
git checkout -- logs/run.log scanner_data.db
git pull
```

**Alpaca orders not appearing in dashboard** — verify `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` are set. Check startup banner shows `✓ Sandbox connected — account balance: $100,000.00`.

**Loop won't stop (stuck on scanner)** — close the terminal window entirely. The scanner has long timeouts when yfinance fails. This is normal — yfinance errors are harmless and the loop recovers automatically.
