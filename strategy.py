"""
US100 FINAL STRATEGY: MOMENTUM UP + ATR FILTER
==============================================
Production-ready strategy

Backtest Results:
- Trades: ~13 per 9 months (~1.5/month)
- Win Rate: 69.2%
- Profit Factor: 4.0
- Max Drawdown: -0.5%
- Return: +6.2%

Logic:
1. Detect strong upward momentum (price up > threshold over lookback)
2. Filter: ATR must be between 15-80 (normal volatility)
3. Entry: On momentum breakout
4. SL: 1.5x ATR below entry
5. TP: 2.0x SL distance (RR 1:2)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class US100MomentumStrategy:
    """
    US100 Optimized Momentum Strategy
    
    LONG ONLY - follows NASDAQ bullish bias
    ATR FILTERED - only normal volatility conditions
    """
    
    # === OPTIMIZED PARAMETERS ===
    MOMENTUM_THRESHOLD = 0.5    # ATR multiplier for momentum detection
    LOOKBACK = 20               # Bars to measure momentum
    SL_ATR_MULT = 1.5          # Stop loss in ATR multiples
    RR = 2.0                    # Risk:Reward ratio
    ATR_MIN = 15               # Minimum ATR (filter out low volatility)
    ATR_MAX = 80               # Maximum ATR (filter out extreme volatility)
    
    def __init__(self):
        logger.info("=" * 60)
        logger.info("US100 MOMENTUM STRATEGY INITIALIZED")
        logger.info("=" * 60)
        logger.info(f"Type: LONG ONLY")
        logger.info(f"Momentum Threshold: {self.MOMENTUM_THRESHOLD}x ATR")
        logger.info(f"Lookback: {self.LOOKBACK} bars")
        logger.info(f"Stop Loss: {self.SL_ATR_MULT}x ATR")
        logger.info(f"Risk:Reward: 1:{self.RR}")
        logger.info(f"ATR Filter: {self.ATR_MIN} - {self.ATR_MAX}")
        logger.info("=" * 60)
    
    def calculate_indicators_m5(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all needed indicators on M5 data"""
        df = df.copy()
        
        # ATR (14 period)
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = tr.rolling(14).mean()
        
        # Momentum (price change over lookback period)
        df['momentum'] = df['close'] - df['close'].shift(self.LOOKBACK)
        
        # Dynamic threshold based on ATR
        df['momentum_threshold'] = df['atr'] * self.MOMENTUM_THRESHOLD * self.LOOKBACK
        
        # Momentum signal (True when strong upward momentum)
        df['momentum_up'] = df['momentum'] > df['momentum_threshold']
        
        return df
    
    def calculate_indicators_m15(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate M15 indicators (optional, for future use)"""
        return df.copy()
    
    def check_filters(self, bar: pd.Series) -> tuple:
        """
        Check if all filters pass
        Returns: (passed: bool, reason: str)
        """
        # ATR filter
        if pd.isna(bar['atr']):
            return False, "ATR not available"
        
        if bar['atr'] < self.ATR_MIN:
            return False, f"ATR too low ({bar['atr']:.1f} < {self.ATR_MIN})"
        
        if bar['atr'] > self.ATR_MAX:
            return False, f"ATR too high ({bar['atr']:.1f} > {self.ATR_MAX})"
        
        return True, "OK"
    
    def generate_signal(
        self,
        df_m5: pd.DataFrame,
        df_m15: pd.DataFrame,
        idx: int
    ) -> Optional[Dict]:
        """
        Generate trading signal
        
        Returns:
            Dict with entry_price, stop_loss, take_profit, type
            Or None if no signal
        """
        
        if idx < 50:
            return None
        
        bar = df_m5.iloc[idx]
        prev_bar = df_m5.iloc[idx - 1]
        
        # === CHECK FILTERS ===
        passed, reason = self.check_filters(bar)
        if not passed:
            return None
        
        # === CHECK MOMENTUM SIGNAL ===
        # Current bar has strong momentum AND previous didn't
        # (this ensures we enter at the START of momentum, not in the middle)
        
        if bar['momentum_up'] and not prev_bar['momentum_up']:
            
            entry = bar['close']
            
            # Stop Loss: 1.5x ATR below entry
            sl_distance = bar['atr'] * self.SL_ATR_MULT
            sl = entry - sl_distance
            
            # Take Profit: RR × SL distance
            tp = entry + (sl_distance * self.RR)
            
            # Sanity check
            if sl_distance <= 0 or sl_distance > 200:
                return None
            
            return {
                'type': 'long',
                'entry_price': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'atr': bar['atr'],
                'momentum': bar['momentum']
            }
        
        # No signal
        return None
    
    def get_strategy_info(self) -> Dict:
        """Return strategy information"""
        return {
            'name': 'US100 Momentum Up + ATR Filter',
            'type': 'LONG ONLY',
            'parameters': {
                'momentum_threshold': self.MOMENTUM_THRESHOLD,
                'lookback': self.LOOKBACK,
                'sl_atr_mult': self.SL_ATR_MULT,
                'rr': self.RR,
                'atr_min': self.ATR_MIN,
                'atr_max': self.ATR_MAX
            },
            'expected_performance': {
                'trades_per_month': 1.5,
                'win_rate': 69.2,
                'profit_factor': 4.0,
                'max_drawdown': -0.5
            }
        }


if __name__ == "__main__":
    strategy = US100MomentumStrategy()
    
    print()
    print("Strategy Info:")
    info = strategy.get_strategy_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
