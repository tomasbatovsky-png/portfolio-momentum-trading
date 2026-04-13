"""
US100 MOMENTUM TRADING SYSTEM - FINAL VERSION
==============================================

Optimized strategy ready for:
1. Final backtest verification
2. Observation mode
3. Live trading (future)

Expected: ~1.5 trades/month, 69% WR, PF 4.0
"""

import pandas as pd
import logging

from data_connector import MT5DataConnector
from strategy import US100MomentumStrategy
from backtest_engine import US100Backtester

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_backtest():
    """Run final backtest"""
    
    print()
    print("=" * 70)
    print("US100 MOMENTUM STRATEGY - FINAL BACKTEST")
    print("=" * 70)
    print()
    
    # === CONFIGURATION ===
    INITIAL_EQUITY = 10_000
    RISK_PER_TRADE = 2.0  # % (aggressive but OK with PF > 2)
    LEVERAGE = 10
    
    # === LOAD DATA ===
    print("Loading data...")
    connector = MT5DataConnector(mode="backtest")
    
    df_m5 = connector.load_csv_data("us100_m5_data.csv", "M5")
    df_m15 = connector.load_csv_data("us100_m15_data.csv", "M15")
    
    print(f"  M5:  {len(df_m5)} bars")
    print(f"  M15: {len(df_m15)} bars")
    print(f"  Period: {df_m5.index[0].date()} to {df_m5.index[-1].date()}")
    print()
    
    # === CREATE STRATEGY ===
    strategy = US100MomentumStrategy()
    
    # === RUN BACKTEST ===
    backtester = US100Backtester(
        df_m5=df_m5,
        df_m15=df_m15,
        strategy=strategy,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_pct=RISK_PER_TRADE,
        leverage=LEVERAGE,
        spread_points=2.0,
        slippage_points=1.0
    )
    
    results = backtester.run()
    
    # === EVALUATION ===
    print()
    print("=" * 70)
    print("STRATEGY EVALUATION")
    print("=" * 70)
    print()
    
    pf = results.get('profit_factor', 0)
    trades = results.get('trades', 0)
    wr = results.get('win_rate', 0)
    dd = results.get('max_drawdown_pct', 0)
    
    if pf >= 2.0 and trades >= 10:
        print("✅✅ EXCELLENT!")
        print("   Strategy is production-ready.")
        print("   Next step: Observation mode for 2-4 weeks.")
        status = "READY"
    elif pf >= 1.5 and trades >= 5:
        print("✅ GOOD")
        print("   Strategy shows positive edge.")
        print("   Consider observation mode with caution.")
        status = "OK"
    elif pf >= 1.0:
        print("⚠️ MARGINAL")
        print("   Break-even. Needs more optimization.")
        status = "NEEDS_WORK"
    else:
        print("❌ NOT PROFITABLE")
        print("   Do not use for live trading.")
        status = "FAIL"
    
    print()
    print("-" * 70)
    print("SUMMARY")
    print("-" * 70)
    print(f"  Status: {status}")
    print(f"  Trades: {trades}")
    print(f"  Win Rate: {wr}%")
    print(f"  Profit Factor: {pf}")
    print(f"  Max Drawdown: {dd}%")
    print(f"  Final Equity: ${results.get('final_equity', 0):,.2f}")
    print()
    print("=" * 70)
    
    return results, status


def main():
    """Main entry point"""
    
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " US100 MOMENTUM TRADING SYSTEM ".center(68) + "║")
    print("║" + " Part of Multi-Market Portfolio ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    
    print("MENU:")
    print("-" * 40)
    print("1. Run Backtest")
    print("2. Strategy Info")
    print("3. Exit")
    print("-" * 40)
    
    choice = input("Select (1-3): ").strip()
    
    if choice == "1":
        run_backtest()
    
    elif choice == "2":
        strategy = US100MomentumStrategy()
        info = strategy.get_strategy_info()
        print()
        print("Strategy Information:")
        print("-" * 40)
        for key, value in info.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
    
    elif choice == "3":
        print("Goodbye!")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
