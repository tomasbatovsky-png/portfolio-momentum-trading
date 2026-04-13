"""
MT5 Data Connector for US100 CFD

For LIVE: connects to MT5 terminal
For BACKTEST: loads CSV exports from MT5
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MT5DataConnector:
    """
    MetaTrader 5 Data Connector
    
    For LIVE trading: connects to MT5 terminal
    For BACKTESTING: loads historical CSV exports from MT5
    """
    
    def __init__(self, mode: str = "backtest"):
        """
        Initialize connector
        
        Args:
            mode: 'live' or 'backtest'
        """
        self.mode = mode
        self.mt5 = None
        
        if mode == "live":
            try:
                import MetaTrader5 as MT5
                self.mt5 = MT5
                logger.info("MT5 connector initialized for LIVE trading")
            except ImportError:
                logger.error(
                    "MetaTrader5 package not installed. "
                    "Install with: pip install MetaTrader5"
                )
                raise
        else:
            logger.info("MT5 connector initialized for BACKTESTING")
    
    def connect_mt5(self) -> bool:
        """Connect to MT5 terminal (for live trading)"""
        if self.mode != "live":
            logger.warning("Not in live mode - skipping MT5 connection")
            return False
        
        if not self.mt5.initialize():
            logger.error("MT5 initialization failed")
            return False
        
        logger.info("✓ Connected to MT5 terminal")
        return True
    
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        if self.mode == "live" and self.mt5:
            self.mt5.shutdown()
            logger.info("Disconnected from MT5")
    
    def load_csv_data(
        self,
        filepath: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Load historical data from CSV (MT5 export)
        
        Args:
            filepath: Path to CSV file
            timeframe: 'M5' or 'M15'
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"Loading {timeframe} data from: {filepath}")
        
        try:
            # Try MT5 standard export format (tab-separated)
            try:
                # First try with UTF-16 encoding (common for MT5)
                try:
                    df = pd.read_csv(
                        filepath,
                        sep='\t',
                        parse_dates=False,
                        encoding='utf-16'
                    )
                except:
                    # Try UTF-8 if UTF-16 fails
                    df = pd.read_csv(
                        filepath,
                        sep='\t',
                        parse_dates=False,
                        encoding='utf-8'
                    )
                
                # MT5 format: <DATE> <TIME> <OPEN> <HIGH> <LOW> <CLOSE> <TICKVOL> <VOL> <SPREAD>
                if '<DATE>' in df.columns and '<TIME>' in df.columns:
                    # Clean the date/time strings
                    df['<DATE>'] = df['<DATE>'].astype(str).str.strip()
                    df['<TIME>'] = df['<TIME>'].astype(str).str.strip()
                    
                    # Combine date and time
                    df['datetime'] = pd.to_datetime(
                        df['<DATE>'] + ' ' + df['<TIME>'],
                        format='%Y.%m.%d %H:%M:%S'
                    )
                    df.set_index('datetime', inplace=True)
                    
                    # Select and rename columns
                    df = df[['<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>', '<TICKVOL>']]
                    df.columns = ['open', 'high', 'low', 'close', 'volume']
                
            except Exception as e:
                logger.warning(f"MT5 format parsing failed: {e}, trying alternative format")
                # Alternative: comma-separated or standard format
                df = pd.read_csv(filepath)
                
                # Try to find datetime column
                if 'datetime' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime'])
                    df.set_index('datetime', inplace=True)
                elif 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'])
                    df.set_index('time', inplace=True)
                elif 'Date' in df.columns and 'Time' in df.columns:
                    df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
                    df.set_index('datetime', inplace=True)
                
                # Standardize column names
                df.columns = [col.lower() for col in df.columns]
            
            # Ensure we have required columns
            required = ['open', 'high', 'low', 'close']
            for col in required:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Add volume if missing
            if 'volume' not in df.columns:
                df['volume'] = 0
            
            # CRITICAL: Filter out fake/test data and future data
            # Only keep data from April 7, 2025 to today
            from datetime import datetime
            start_date = datetime(2025, 4, 7)  # Start from April 7, 2025
            today = datetime.now()
            
            # Filter by date range
            df = df[(df.index >= start_date) & (df.index <= today)]
            
            if len(df) == 0:
                raise ValueError(
                    f"No valid data found in range {start_date.date()} to {today.date()}. "
                    "Check if MT5 exported correct timeframe (M5/M15, not Daily)."
                )
            
            logger.info(
                f"✓ Loaded {len(df)} bars from CSV "
                f"(filtered: {start_date.date()} to {today.date()})"
            )
            
            return df[['open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            raise


def generate_sample_us100_data(
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    timeframe: str = "M5",
    initial_price: float = 17000.0
) -> pd.DataFrame:
    """
    Generate synthetic US100 data for testing
    
    ONLY for initial testing - replace with real MT5 data!
    """
    logger.warning("Using synthetic data - replace with real MT5 data for backtesting!")
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Generate only NY session times (15:30-20:00 CET)
    dates = pd.date_range(start=start, end=end, freq='B')  # Business days
    
    all_times = []
    for date in dates:
        # NY session: 15:30 - 20:00
        session_start = date.replace(hour=15, minute=30)
        session_end = date.replace(hour=20, minute=0)
        
        if timeframe == "M5":
            freq = "5min"
        elif timeframe == "M15":
            freq = "15min"
        else:
            freq = "5min"
        
        day_times = pd.date_range(start=session_start, end=session_end, freq=freq)
        all_times.extend(day_times)
    
    dates = pd.DatetimeIndex(all_times)
    n = len(dates)
    
    # Generate realistic price movement
    np.random.seed(42)
    
    # US100 typical daily volatility ~1-2%
    returns = np.random.normal(0.0001, 0.015, n)
    prices = initial_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame(index=dates)
    df['close'] = prices
    
    # Generate OHLC
    df['open'] = df['close'].shift(1) * (1 + np.random.normal(0, 0.001, n))
    df['open'].iloc[0] = initial_price
    
    daily_range = np.abs(np.random.normal(0, 0.008, n))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + daily_range * np.random.uniform(0.3, 1, n))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - daily_range * np.random.uniform(0.3, 1, n))
    
    df['volume'] = np.random.lognormal(10, 0.5, n).astype(int)
    
    logger.info(f"Generated {len(df)} synthetic {timeframe} bars")
    
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("MT5 DATA CONNECTOR")
    print("=" * 60)
    print()
    print("For LIVE: Connect to MT5 terminal")
    print("For BACKTEST: Load CSV exports")
    print("=" * 60)
