# S&P 500 Strategy Backtest

This project downloads the current S&P 500 tickers, fetches historical OHLCV data, applies a technical-indicator-based strategy (RSI, MACD, EMAs, and volume), runs a backtest with explicit entry/exit rules, and computes profitability and risk metrics (Sharpe, Sortino, drawdown, etc.).

The workflow is split into 4 Python scripts that must be executed in order.

## Requirements

- Python 3.10 or higher
- Libraries:
  - `pandas`
  - `requests`
  - `yfinance`
  - `openpyxl`
  - `numpy`

Install them with:

```bash
pip install pandas requests yfinance openpyxl numpy
```

## Execution order

Run the scripts in this order, from the project folder:

### 1. Download S&P 500 tickers

```bash
python get_sp500.py
```

- Downloads the current list of S&P 500 tickers from Wikipedia.
- Generates:
  - `sp500_tickers.csv`

### 2. Download data, apply strategy, and run backtest

```bash
python get_hold_days.py
```

- Reads `sp500_tickers.csv`.
- Downloads 5 years of daily OHLCV data using `yfinance`.
- Calculates indicators:
  - RSI (14)
  - MACD (12, 26, 9)
  - EMA 20 and EMA 50
  - Relative volume (10-day average)
- Generates signals:
  - `buy_signal` and `true_buy_signal` for entries.
  - `sell_signal` for exits, with:
    - Dynamic stop loss (lowest low of the last 6 days).
    - Check at day 5 (if `Close < entry_price` → exit).
    - Forced exit at day 10.
- Saves results to:
  - `backtest_resultados.xlsx`
    - Sheet `RESUMEN`: per-ticker statistics (number of trades, win rate, average PnL, etc.).
    - One sheet per ticker with the days where a position was open (`hold = 1`).

### 3. Compute total returns per ticker

```bash
python get_returns.py
```

- Reads `backtest_resultados.xlsx`.
- For each ticker, computes:
  - `return_pct = 1 + pnl_pct` per trade.
  - Compounded total return: product of all `return_pct`.
- Generates:
  - `retornos_por_ticker.xlsx`
    - Sheet `RESUMEN`: all tickers sorted by total return.
    - Sheet `TOP_20`: best 20 tickers.
    - Sheet `BOTTOM_20`: worst 20 tickers.
  - Adds sheet `RETORNOS` to `backtest_resultados.xlsx`.

### 4. Compute profitability and risk metrics (Top 20)

```bash
python get_metrics.py
```

- Reads:
  - `retornos_por_ticker.xlsx` (sheet `TOP_20`).
  - `backtest_resultados.xlsx` (per-ticker sheets).
- For each ticker in the Top 20, computes metrics using only closed trades (`sell_signal = 1`):
  - Number of trades, winners/losers.
  - Win rate.
  - Average PnL, average win, average loss.
  - Profit Factor.
  - Compounded total return.
  - Maximum drawdown.
  - Sharpe, Sortino, Calmar, and Recovery Factor.
  - Maximum consecutive wins and losses.
  - Largest single gain and largest single loss.
- Saves results to:
  - `metricas_top20_corregidas.xlsx`
    - Sheet `RESUMEN_METRICAS`: full metrics table per ticker.
    - Sheet `TOP_10_SHARPE`: 10 tickers with highest Sharpe.
    - One sheet per ticker with:
      - Only rows corresponding to closed trades.
      - Columns: `return_pct`, `equity_curve`, etc.

## Generated files

After running the full workflow, you will have:

- `sp500_tickers.csv`  
  List of S&P 500 tickers.

- `backtest_resultados.xlsx`  
  - `RESUMEN`: basic statistics per ticker.
  - One sheet per ticker with days in position.
  - `RETORNOS`: total returns per ticker.

- `retornos_por_ticker.xlsx`  
  - `RESUMEN`: all tickers sorted by return.
  - `TOP_20` and `BOTTOM_20`.

- `metricas_top20_corregidas.xlsx`  
  - `RESUMEN_METRICAS`: complete metrics for the Top 20.
  - `TOP_10_SHARPE`.
  - Individual sheets per ticker with closed trades and equity curve.

## Project structure

- `get_sp500.py` – Downloads S&P 500 tickers.
- `get_hold_days.py` – Downloads data, computes indicators, generates signals, and runs the backtest.
- `get_returns.py` – Computes total returns per ticker.
- `get_metrics.py` – Computes profitability and risk metrics for the Top 20.

## Author

Ghery Jorge Cárdenas L.