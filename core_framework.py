"""
US100 CFD CORE FRAMEWORK
========================
Base classes for trading system
"""

import pandas as pd
import numpy as np
from datetime import datetime, time
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Trade:
    """Single trade record"""
    entry_time: datetime
    entry_price: float
    side: OrderSide
    size: float
    stop_loss: float
    take_profit: float
    
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_usd: float = 0.0
    pnl_pct: float = 0.0
    
    def close_trade(self, exit_price: float, exit_time: datetime, reason: str):
        """Close the trade and calculate PnL"""
        self.exit_price = exit_price
        self.exit_time = exit_time
        self.exit_reason = reason
        
        # Calculate PnL
        if self.side == OrderSide.BUY:
            self.pnl_usd = (exit_price - self.entry_price) * self.size
        else:
            self.pnl_usd = (self.entry_price - exit_price) * self.size
        
        self.pnl_pct = (self.pnl_usd / (self.entry_price * self.size)) * 100


class SessionManager:
    """Manages trading session hours"""
    
    def __init__(
        self,
        session_start: time = time(15, 30),  # 15:30 CET
        session_end: time = time(20, 0)       # 20:00 CET
    ):
        self.session_start = session_start
        self.session_end = session_end
    
    def is_trading_session(self, dt: datetime) -> bool:
        """Check if time is within trading session"""
        current_time = dt.time()
        return self.session_start <= current_time <= self.session_end
    
    def should_close_positions(self, dt: datetime) -> bool:
        """Check if we should close positions (end of session)"""
        current_time = dt.time()
        # Close 5 minutes before session end
        close_time = time(self.session_end.hour, self.session_end.minute - 5)
        return current_time >= close_time


class RiskManager:
    """Manages risk and position sizing"""
    
    def __init__(
        self,
        initial_equity: float = 10000,
        risk_per_trade_pct: float = 0.5,
        leverage: float = 10.0,
        max_daily_loss_pct: float = 2.0,
        max_trades_per_day: int = 3
    ):
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.risk_per_trade_pct = risk_per_trade_pct
        self.leverage = leverage
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_trades_per_day = max_trades_per_day
        
        # Daily tracking
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.current_date = None
    
    def reset_daily_counters(self, date):
        """Reset counters for new day"""
        if self.current_date != date:
            self.current_date = date
            self.daily_pnl = 0.0
            self.daily_trades = 0
    
    def can_trade(self, date) -> tuple:
        """Check if trading is allowed"""
        self.reset_daily_counters(date)
        
        # Check daily loss limit
        daily_loss_pct = (self.daily_pnl / self.initial_equity) * 100
        if daily_loss_pct <= -self.max_daily_loss_pct:
            return False, "Daily loss limit reached"
        
        # Check trade count
        if self.daily_trades >= self.max_trades_per_day:
            return False, "Max trades per day reached"
        
        return True, "OK"
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        side: OrderSide
    ) -> float:
        """Calculate position size based on risk"""
        
        # Risk amount in USD
        risk_usd = self.current_equity * (self.risk_per_trade_pct / 100)
        
        # Stop distance in points
        stop_distance = abs(entry_price - stop_loss)
        
        if stop_distance == 0:
            return 0
        
        # Position size based on risk
        size = risk_usd / stop_distance
        
        # Leverage limit
        max_position_value = self.current_equity * self.leverage
        max_size = max_position_value / entry_price
        
        return min(size, max_size)
    
    def register_trade_opened(self):
        """Register that a trade was opened"""
        self.daily_trades += 1
    
    def register_trade_closed(self, pnl_usd: float):
        """Register trade result"""
        self.current_equity += pnl_usd
        self.daily_pnl += pnl_usd


class MarketConditionFilter:
    """Filters market conditions"""
    
    def __init__(
        self,
        min_atr: float = 0.0,      # Changed to 0 - let strategy handle ATR filtering
        max_atr: float = 99999.0,  # Changed to high value - let strategy handle
        max_spread: float = 100.0  # Changed to high value
    ):
        self.min_atr = min_atr
        self.max_atr = max_atr
        self.max_spread = max_spread
    
    def is_valid_market_condition(
        self,
        current_atr: float,
        current_spread: float
    ) -> tuple:
        """Check if market conditions are suitable"""
        
        # ATR filtering is now handled by individual strategies
        # This filter is mostly disabled to allow different markets
        
        if current_atr < self.min_atr:
            return False, "ATR too low"
        
        if current_atr > self.max_atr:
            return False, "ATR too high"
        
        if current_spread > self.max_spread:
            return False, "Spread too wide"
        
        return True, "OK"


if __name__ == "__main__":
    print("Core Framework loaded successfully")
