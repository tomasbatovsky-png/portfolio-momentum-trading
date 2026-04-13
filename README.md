# Portfolio Momentum Trading System

A multi-market momentum crossover strategy trading US equity index CFDs (US100, US30, SP500) with adaptive position sizing and compounding equity management.

## Strategy Overview

The system detects momentum breakouts by comparing price momentum against an ATR-scaled threshold, then enters positions filtered by RSI and EMA trend alignment. Position sizing follows a Ross Cameron-inspired risk ladder that scales with account performance.

**Core Logic:**

| Parameter | Value |
|-----------|-------|
| Entry Signal | Momentum(20) > ATR(14) x 0.3 x Lookback(20) |
| Trend Filter | EMA(20) > EMA(50) for longs |
| Volatility Filter | ATR between 15-80 pips |
| Overbought Filter | RSI(14) < 70 |
| Stop Loss | 1.5 x ATR(14) |
| Take Profit | 1.5-2.0 x Risk |
| Timeframes | M5 (primary), M1 (scalp overlay for US30) |

**Adaptive Position Sizing (Ross Cameron Model):**

| Account Stage | Risk per Trade |
|---------------|----------------|
| Starting (no cushion) | 0.5% |
| After +0.5% profit | 1.0% |
| After +1.5% profit | 1.5% |
| After +3.0% profit | 2.0% (max) |
| Daily stop-loss | -2.0% (all positions closed) |

## Portfolio Composition

| Market | Timeframe | Profit Factor | Win Rate | Trades/Month |
|--------|-----------|---------------|----------|--------------|
| US100 (NQ) | M5 | 3.26 | 66% | 1.5 |
| SP500 (ES) | M5 | 2.63 | 69% | 0.7 |
| US30 (YM) | M5 | 2.17 | 66% | 1.4 |
| US30 (YM) | M1 | 2.33 | 60% | 1.4 |

DAX40 was removed during optimization (PF = 0.44, net loser).

## Backtest Results

| Metric | Original | Optimized |
|--------|----------|-----------|
| Starting Capital | EUR 10,000 | EUR 10,000 |
| Final Equity | ~EUR 11,100 | ~EUR 11,500 |
| Profit Factor | ~3.0 | ~3.3 |
| Win Rate | ~65% | ~66% |
| Max Drawdown | ~4.2% | ~3.8% |
| Trades / Month | ~6.5 | ~5.0 |

## Out-of-Sample Validation (Feb-Mar 2026)

Stress-tested during the US tariff-crisis period. Combined portfolio drawdown stayed within -2.7% (50/40/10 allocation with CL-04 and Regime Alpha).

## Architecture

```
portfolio-momentum-trading/
├── portfolio_backtest_final.py        # Original 5-market discovery backtest
├── optimized_portfolio.py             # Optimized version (removed DAX40, added compounding)
├── portfolio_results.csv              # Trade log - original
├── optimized_portfolio_results.csv    # Trade log - optimized
└── README.md
```

## Tech Stack

- **Python 3.9+** - pandas, numpy
- **Data** - CFD broker data (M1/M5 candles) or Databento (CME futures)
- **Deployment** - MetaTrader 5 Python bridge

## Quick Start

```bash
pip install pandas numpy
python optimized_portfolio.py
```

## Disclaimer

Educational and research purposes only. Past performance does not guarantee future results.

## Author

**Tomas Batovsky** - Quantitative trading systems developer
