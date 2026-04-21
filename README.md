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
    ├── run.py                  ← Main loop — ask-price fills (faster fills, paper learning)
    ├── run_live.py             ← Main loop — mid-price fills (live trading discipline)
    └── requirements_rl.txt     ← pip dependencies
```

---

## Setup

```bash
# 1. Install dependencies
pip install -r rl_system/requirements_rl.txt

# 2. Run from your main folder (where options_scanner.py lives)
cd your_folder
python3 rl_system/run.py --live-paper --auto
```

API keys are stored securely in the database — no environment variables needed. On first run you will be prompted to enter your Tradier and Alpaca keys. They are verified against the live APIs before the loop starts.

To update keys at any time:
```powershell
python3 rl_system/run.py --reset-keys
python3 rl_system/run_live.py --reset-keys
```

---

## run.py vs run_live.py

| | run.py | run_live.py |
|---|---|---|
| Limit price | Ask price | Mid price |
| Fill speed | Fast — fills immediately | Patient — may take time |
| Best for | Generating training data quickly | Simulating live trading |
| Alpaca account | Account 1 | Account 2 (separate keys) |
| Database | scanner_data.db | scanner_data_live.db |
| Keys stored as | alpaca_api_key | alpaca_api_key_live |

Both run identical signals, scanner, and RL agent. Use `run_live.py` for clean data and live-trading simulation. Use `run.py` if you need faster fills.

---

## CLI Commands

```bash
# ── Run modes ─────────────────────────────────────────────────────
python3 rl_system/run.py --live-paper --auto             # fully autonomous, no position limit
python3 rl_system/run.py --live-paper --bankroll 5000    # $5k pool, compounds profits
python3 rl_system/run.py --paper                         # manual fills via ThinkorSwim
python3 rl_system/run.py --debug                         # verbose output

# ── Status and diagnostics ────────────────────────────────────────
python3 rl_system/run.py --status             # positions, P&L, capital deployed
python3 rl_system/run.py --weights            # agent weight summary

# ── Position management ───────────────────────────────────────────
python3 rl_system/run.py --close 1            # mark position #1 as manually closed
python3 rl_system/run.py --close-all          # close all open positions
python3 rl_system/run.py --delete 1           # delete position #1 (no record kept)

# ── Reset ─────────────────────────────────────────────────────────
python3 rl_system/run.py --reset              # clear positions/history, keep agent weights
python3 rl_system/run.py --reset-all          # wipe everything including agent weights
python3 rl_system/run.py --reset-keys         # clear stored API keys and re-prompt
```

Same commands work for `run_live.py`.

---

## Key Management

On first run, you will be prompted for:
- **Tradier API key** — shared between run.py and run_live.py
- **Alpaca API key** — separate per file
- **Alpaca secret key** — separate per file

Keys are stored in the SQLite database `system_state` table and verified against live APIs on every startup:

```
Verifying API keys...
Tradier:              OK
Alpaca (mid account): OK — cash $91,534.84
```

Keys are never stored in code or environment variables.

---

## Run Modes Explained

### `--paper` (manual)
Prompts you for confirmation on every entry and exit. You execute trades in ThinkorSwim and confirm fills in the terminal. Max 3 concurrent positions.

### `--auto` (fully autonomous)
No user input required. System enters and exits automatically based on signals. Capped at 10 positions and 40% of account capital by default. Recommended for learning/training phase.

### `--bankroll AMOUNT` (compounding pool)
Specify a fixed dollar pool. System trades autonomously using only that pool — always 1 contract per trade. Profits from closes flow back into the pool. Entries stop when the pool can't cover the next premium.

Bankroll is persisted to DB across restarts. If the system restarts mid-session, the remaining balance is restored automatically.

### `--live-paper` (Alpaca paper execution)
Combines with `--auto` or `--bankroll`. Sends real limit orders to your Alpaca paper account. Positions visible at:

```
https://app.alpaca.markets/paper-trading/overview
```

Data source split:
- **Market data** → Tradier production API (real-time)
- **Order execution** → Alpaca paper API

---

## Order Execution Flow

Orders are placed as limit orders at ask price (`run.py`) or mid price (`run_live.py`) and immediately queued for reconciliation. The loop does not block waiting for fills.

```
Order placed → queued for reconciliation
     ↓
Every tick: check Alpaca for fills
     ↓
Fill confirmed → write to DB → track position → deduct bankroll
```

**Pending order management** (runs every tick):
- **Price drift check** — if live ask moves >20% above your limit, order is cancelled and ticker put on 4-hour cooldown
- **Age check** — orders older than 6.5 hours are cancelled at EOD
- **Bankroll check** — when a fill is accepted and bankroll drops, remaining pending orders that would overdraw are immediately cancelled at Alpaca

**Startup sync** — on every startup, open Alpaca positions are compared against the DB. Any fills that happened while the system was offline are recovered and tracked automatically.

**Duplicate protection** — if a ticker already has an open order at Alpaca, no second order is placed.

---

## How It Works

### Every 60 seconds (one tick)

1. **Hard rules evaluated first** — stop loss, profit target, DTE expiry. Always fire.
2. **Reconciliation loop** — checks pending orders for fills, drift, age, and bankroll overdraft.
3. **Open positions scored** — agent outputs HOLD or EXIT with confidence.
4. **New candidates scored** — agent outputs ENTER or WAIT for top 5 scanner results.
5. **Tick status bar printed** — time, regime, VIX, all open position P&L.

### During market hours only (10am–3:30pm ET)

- Full scanner runs on all 19 watchlist tickers every 5 minutes (~2 minutes to complete)
- Results sorted by confluence score
- Live price refresh from Tradier immediately before each order placement

### Outside market hours

- Scanner skipped entirely — no unnecessary API calls
- Position monitoring continues — stops and targets still fire
- Reconciliation loop still runs — late fills still get picked up

### When a position closes

- Reward computed and agent weights updated
- 24-hour cooldown set on that ticker
- In bankroll mode: proceeds credited back to pool
- In live-paper mode: closing order sent to Alpaca

---

## Hard Risk Rules

| Rule | Default | Config Key |
|------|---------|------------|
| Stop loss | Down 33% from entry | `STOP_LOSS_PCT` |
| Profit target | Up 66% from entry | `PROFIT_TARGET_PCT` |
| DTE force-close | 7 days to expiry | `CLOSE_BEFORE_DTE` |
| Max concurrent (paper) | 3 positions | `MAX_CONCURRENT_POSITIONS` |
| Max concurrent (auto) | 10 positions | `AUTO_MAX_POSITIONS` |
| Max capital (auto) | 40% of account | `AUTO_MAX_CAPITAL_PCT` |
| Daily drawdown | Down 6% of account | `MAX_DAILY_DRAWDOWN_PCT` |
| Cooldown | 24 hours post-close | `COOLDOWN_HOURS` |

**R/R ratio:** 2:1 — risk 33% to make 66%.

**Grace period:** Hard rules suppressed for the first 10 minutes after entry.

---

## Exit Strategy

Three layers, in priority order:

**Layer 1 — Hard rules** (always fire)
Stop loss at -33%, profit target at +66%, DTE force-close at 7 days.

**Layer 2 — Agent exit scoring**
Rule-based scoring that pushes toward exit when multiple signals confirm. Exit fires when total score ≥ 0.55.

**Layer 3 — Manual** (`--close ID` or `--close-all`)

---

## The Learning Agent

Starts pure rule-based. After 10 closed trades, begins blending learned weights (up to 60%).

**Features per decision:** unrealized_r, dte_fraction, theta_decay_fraction, iv_rank_normalized, spy_trend, rsi_normalized, flow_score_normalized, above_vwap, regime_score, ticks_held_normalized, spread_vs_target, days_since_entry_norm.

**Reward:** `realized_R - 0.5 (stop hit) - 0.3 (drawdown) - 0.2 (churn)`

Losses are as valuable as wins for learning — they teach the agent which signal combinations predict bad entries. Check learning progress in `--status`:

```
Agent learning:
  Enter model: 14 updates  mean reward +0.12R
  Exit model:  14 updates  mean reward +0.08R
```

Check in after 10, 20, and 40 closed trades to evaluate signal quality and tune parameters.

---

## Bankroll Mode Details

- Bankroll is persisted to DB — survives restarts
- Re-checks against live price after Tradier refresh (prevents stale scanner prices from bypassing budget)
- When a fill is accepted, immediately cancels all remaining pending orders that would overdraw the balance
- Does NOT sell positions after they fill — only prevents future fills from exceeding budget
- Proceeds from closes are credited back and immediately available for new entries

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
  Live price refresh → immediately before every order placement

Order execution:
  Alpaca paper API → entries, exits, fill prices, web dashboard

Price fetching for P&L:
  1. Tradier live bid/ask mid (primary)
  2. yfinance option chain mid (fallback)
  3. Entry price (last resort)
```

---

## Database

All data persists in `scanner_data.db` (run.py) and `scanner_data_live.db` (run_live.py). Both are SQLite and gitignored.

| Table | Contents |
|-------|----------|
| `positions` | All open and closed positions with P&L |
| `tick_snapshots` | Every 60-second evaluation per position |
| `recommendations` | Every user-facing alert sent |
| `trade_journal` | Human-readable event log |
| `agent_weights` | Learned model weights |
| `cooldowns` | Active ticker cooldowns |
| `system_state` | API keys, bankroll, pending orders, action state |

---

## Notifications

| Channel | How to enable |
|---------|--------------|
| Terminal | Always on |
| Windows toast | `pip install winotify` |
| Discord | Set `NOTIFY_DISCORD_WEBHOOK_URL` in config.py |

---

## Troubleshooting

**"OUTSIDE market hours"** — correct before 10am or after 3:30pm ET. Scanner paused, position monitoring continues.

**Keys not saving** — run `--reset-keys` and re-enter. Keys are verified against live APIs on entry.

**Alpaca 401 unauthorized** — keys may be for live account not paper. Go to app.alpaca.markets, toggle to Paper account, regenerate keys there.

**Orders timing out** — normal for mid-price limits in volatile markets. Orders stay live at Alpaca until 3pm. Reconciliation loop picks up fills automatically.

**Bankroll went negative** — set it manually:
```powershell
python3 -c "import sys; sys.path.insert(0,'rl_system'); import database as db; db.initialize_database(); db.set_state('bankroll_remaining', 0); print('Reset to 0')"
```

**Scanner not importing** — run from the folder containing `options_scanner.py`. Command must be `python3 rl_system/run.py` not `python3 run.py`.

**git pull fails with DB conflict** — run:
```bash
git checkout -- scanner_data.db scanner_data_live.db
git pull
```

**Loop won't stop** — close the terminal window entirely. The scanner has long timeouts when yfinance fails. This is normal.

**Duplicate order rejected (422)** — ticker already has an open order at Alpaca. System will skip re-entry automatically until the existing order fills, cancels, or expires.
