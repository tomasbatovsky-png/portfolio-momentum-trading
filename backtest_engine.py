"""
US100 CFD BACKTEST ENGINE
=========================
Clean, simple, working backtester
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging

from core_framework import (
    SessionManager,
    RiskManager,
    MarketConditionFilter,
    Trade,
    OrderSide
)

logger = logging.getLogger(__name__)


class US100Backtester:
    """
    Backtest engine for US100 CFD
    
    Features:
    - Bar-by-bar execution
    - Risk-based position sizing
    - Leverage control
    - Session management
    - No look-ahead bias
    """
    
    def __init__(
        self,
        df_m5: pd.DataFrame,
        df_m15: pd.DataFrame,
        strategy,
        initial_equity: float = 10000,
        risk_per_trade_pct: float = 0.5,
        leverage: float = 10.0,
        spread_points: float = 2.0,
        slippage_points: float = 1.0
    ):
        # Data
        self.df_m5 = df_m5.copy()
        self.df_m15 = df_m15.copy()
        
        # Strategy
        self.strategy = strategy
        
        # Execution costs
        self.spread = spread_points
        self.slippage = slippage_points
        
        # Risk management
        self.session_mgr = SessionManager()
        self.risk_mgr = RiskManager(
            initial_equity=initial_equity,
            risk_per_trade_pct=risk_per_trade_pct,
            leverage=leverage
        )
        self.market_filter = MarketConditionFilter()
        
        # State
        self.initial_equity = initial_equity
        self.trades: List[Trade] = []
        self.open_trade: Optional[Trade] = None
        
        print("=" * 60)
        print("US100 BACKTESTER INITIALIZED")
        print("=" * 60)
        print(f"Initial Equity: ${initial_equity:,.2f}")
        print(f"Risk/Trade: {risk_per_trade_pct}%")
        print(f"Leverage: 1:{int(leverage)}")
        print(f"M5 bars: {len(df_m5)}")
        print(f"M15 bars: {len(df_m15)}")
        print("=" * 60)
    
    def _apply_costs(self, price: float, side: OrderSide) -> float:
        """Apply spread and slippage"""
        cost = self.spread + self.slippage
        if side == OrderSide.BUY:
            return price + cost
        else:
            return price - cost
    
    def run(self) -> Dict:
        """Run backtest"""
        print("\nRunning backtest...")
        
        # Calculate indicators
        self.df_m5 = self.strategy.calculate_indicators_m5(self.df_m5)
        self.df_m15 = self.strategy.calculate_indicators_m15(self.df_m15)
        
        trade_count = 0
        
        # Bar-by-bar loop
        for i in range(50, len(self.df_m5)):
            bar = self.df_m5.iloc[i]
            timestamp = self.df_m5.index[i]
            date = timestamp.date()
            
            # Reset daily counters
            self.risk_mgr.reset_daily_counters(date)
            
            # Manage open trade first
            if self.open_trade:
                self._check_exit(bar, timestamp)
                continue
            
            # Check if we can trade
            can_trade, _ = self.risk_mgr.can_trade(date)
            if not can_trade:
                continue
            
            # Check ATR filter
            if pd.isna(bar.get('atr')):
                continue
            
            valid, _ = self.market_filter.is_valid_market_condition(
                bar['atr'],
                self.spread
            )
            if not valid:
                continue
            
            # Generate signal
            signal = self.strategy.generate_signal(self.df_m5, self.df_m15, i)
            
            if signal:
                self._open_trade(signal, timestamp)
                trade_count += 1
                
                if trade_count % 100 == 0:
                    print(f"  Trades: {trade_count}...")
        
        # Close any remaining position
        if self.open_trade:
            self._force_close(self.df_m5.iloc[-1], self.df_m5.index[-1])
        
        print(f"\nBacktest complete. Total trades: {len(self.trades)}")
        
        return self._calculate_stats()
    
    def _open_trade(self, signal: Dict, timestamp: datetime):
        """Open a new trade"""
        side = OrderSide.BUY if signal['type'] == 'long' else OrderSide.SELL
        
        entry = self._apply_costs(signal['entry_price'], side)
        
        size = self.risk_mgr.calculate_position_size(
            entry,
            signal['stop_loss'],
            side
        )
        
        if size <= 0:
            return
        
        self.open_trade = Trade(
            entry_time=timestamp,
            entry_price=entry,
            side=side,
            size=size,
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit']
        )
        
        self.risk_mgr.register_trade_opened()
    
    def _check_exit(self, bar: pd.Series, timestamp: datetime):
        """Check if trade should be closed"""
        t = self.open_trade
        if not t:
            return
        
        # Check SL
        if t.side == OrderSide.BUY:
            if bar['low'] <= t.stop_loss:
                self._close_trade(t.stop_loss, timestamp, 'SL')
                return
            if bar['high'] >= t.take_profit:
                self._close_trade(t.take_profit, timestamp, 'TP')
                return
        else:  # SELL
            if bar['high'] >= t.stop_loss:
                self._close_trade(t.stop_loss, timestamp, 'SL')
                return
            if bar['low'] <= t.take_profit:
                self._close_trade(t.take_profit, timestamp, 'TP')
                return
    
    def _close_trade(self, price: float, timestamp: datetime, reason: str):
        """Close current trade"""
        t = self.open_trade
        if not t:
            return
        
        exit_side = OrderSide.SELL if t.side == OrderSide.BUY else OrderSide.BUY
        exit_price = self._apply_costs(price, exit_side)
        
        t.close_trade(exit_price, timestamp, reason)
        self.trades.append(t)
        self.risk_mgr.register_trade_closed(t.pnl_usd)
        self.open_trade = None
    
    def _force_close(self, bar: pd.Series, timestamp: datetime):
        """Force close at end of data"""
        if self.open_trade:
            self._close_trade(bar['close'], timestamp, 'END')
    
    def _calculate_stats(self) -> Dict:
        """Calculate performance statistics"""
        if not self.trades:
            return {'trades': 0, 'message': 'No trades executed'}
        
        # Build trades dataframe
        data = []
        for t in self.trades:
            data.append({
                'pnl': t.pnl_usd,
                'pnl_pct': t.pnl_pct,
                'reason': t.exit_reason,
                'win': t.pnl_usd > 0
            })
        
        df = pd.DataFrame(data)
        
        # Calculate metrics
        total_trades = len(df)
        wins = df['win'].sum()
        losses = total_trades - wins
        
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        total_pnl = df['pnl'].sum()
        avg_win = df[df['win']]['pnl'].mean() if wins > 0 else 0
        avg_loss = df[~df['win']]['pnl'].mean() if losses > 0 else 0
        
        profit_factor = abs(avg_win * wins / (avg_loss * losses)) if losses > 0 and avg_loss != 0 else 0
        
        # Equity curve and drawdown
        equity = df['pnl'].cumsum()
        running_max = equity.cummax()
        drawdown = equity - running_max
        max_dd = drawdown.min()
        max_dd_pct = (max_dd / self.initial_equity) * 100
        
        total_return = (self.risk_mgr.current_equity / self.initial_equity - 1) * 100
        
        # Exit reasons
        tp_count = len(df[df['reason'] == 'TP'])
        sl_count = len(df[df['reason'] == 'SL'])
        
        stats = {
            'trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'total_return_pct': round(total_return, 1),
            'max_drawdown_pct': round(max_dd_pct, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'tp_exits': tp_count,
            'sl_exits': sl_count,
            'final_equity': round(self.risk_mgr.current_equity, 2)
        }
        
        # Print results
        print("\n" + "=" * 60)
        print("BACKTEST RESULTS")
        print("=" * 60)
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Total Return: {total_return:+.1f}%")
        print(f"Max Drawdown: {max_dd_pct:.1f}%")
        print(f"Final Equity: ${self.risk_mgr.current_equity:,.2f}")
        print("-" * 60)
        print(f"Exits - TP: {tp_count}, SL: {sl_count}")
        print("=" * 60)
        
        return stats


if __name__ == "__main__":
    print("Backtest Engine ready")
