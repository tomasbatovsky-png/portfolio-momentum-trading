"""
================================================================================
🏆 OPTIMALIZOVANÉ PORTFÓLIO - BEZ DAX40!
================================================================================

Výsledky z backtestu:
│ SP500_M5 │ PF 2.63 │ +€2,390 │ 🏆 NAJLEPŠIA
│ US30_M5  │ PF 2.17 │ +€1,374 │ ✅ DOBRÁ
│ US100_M5 │ PF 1.45 │ +€3,220 │ ⚠️ OK
│ DAX40_M5 │ PF 0.44 │ -€662   │ ❌ VYHODENÉ!

Parametre: LB=20, T=0.3, SL=1.5×ATR
Session: 15:30-22:00 CET (NY session)

✅ COMPOUNDING ZAPNUTÝ - každý trade počíta z aktuálnej balance!
================================================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, time, date
from typing import List, Optional
import os
import sys


# =============================================================================
# DATA LOADER
# =============================================================================

def load_mt5_csv(filename: str) -> Optional[pd.DataFrame]:
    if not os.path.exists(filename):
        return None
    
    df = pd.read_csv(filename, sep='\t')
    
    date_col = time_col = None
    for col in df.columns:
        c = col.strip('<>').strip().upper()
        if c == 'DATE': date_col = col
        elif c == 'TIME': time_col = col
    
    if date_col is None:
        return None
    
    datetime_str = df[date_col].astype(str) + ' ' + df[time_col].astype(str)
    df['datetime'] = pd.to_datetime(datetime_str, format='%Y.%m.%d %H:%M:%S')
    df = df.set_index('datetime')
    
    rename = {}
    for col in df.columns:
        c = col.strip('<>').strip().upper()
        if c == 'OPEN': rename[col] = 'open'
        elif c == 'HIGH': rename[col] = 'high'
        elif c == 'LOW': rename[col] = 'low'
        elif c == 'CLOSE': rename[col] = 'close'
    
    df = df.rename(columns=rename)
    return df[['open', 'high', 'low', 'close']].copy()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # ATR
    tr = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = tr.rolling(14).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # EMAs for trend
    df['ema_20'] = df['close'].ewm(span=20).mean()
    df['ema_50'] = df['close'].ewm(span=50).mean()
    df['uptrend'] = df['ema_20'] > df['ema_50']
    
    # Momentum
    df['mom_10'] = df['close'] - df['close'].shift(10)
    df['mom_20'] = df['close'] - df['close'].shift(20)
    
    return df


# =============================================================================
# OPTIMALIZOVANÉ STRATÉGIE - BEZ DAX40!
# =============================================================================

STRATEGIES = {
    'SP500_M5': {  # 🏆 NAJLEPŠIA - PF 2.63
        'file': 'sp500_m5_data.csv',
        'session': (time(15, 30), time(22, 0)),
        'lb': 20, 'thresh': 0.3, 'sl': 1.5, 'rr': 2.0,
        'filter': 'rsi',
        'spread': 0.5,
        'expected_pf': 2.63,
    },
    'US30_M5': {  # ✅ DOBRÁ - PF 2.17
        'file': 'us30_m5_data.csv',
        'session': (time(15, 30), time(22, 0)),
        'lb': 20, 'thresh': 0.3, 'sl': 1.5, 'rr': 1.5,
        'filter': 'rsi',
        'spread': 3.0,
        'expected_pf': 2.17,
    },
    'US100_M5': {  # ⚠️ OK - PF 1.45
        'file': 'us100_m5_data.csv',
        'session': (time(15, 30), time(22, 0)),
        'lb': 20, 'thresh': 0.3, 'sl': 1.5, 'rr': 2.0,
        'filter': 'atr',
        'atr_min': 15, 'atr_max': 80,
        'spread': 2.0,
        'expected_pf': 1.45,
    },
    # DAX40 VYHODENÝ - PF 0.44 = STRATOVÝ!
}


# =============================================================================
# ROSS CAMERON POSITION SIZING
# =============================================================================

class PositionManager:
    """
    Ross Cameron štýl:
    - Začni s 0.5% risk (starter)
    - Po zisku +0.5% prejdi na 2% (full)
    - Po strate späť na 0.5%
    - Max denná strata -2% = STOP
    """
    def __init__(self):
        self.starter = 0.5
        self.full = 2.0
        self.cushion = 0.5
        self.max_loss = 2.0
        
        self.current_date = None
        self.daily_pnl = 0.0
        self.is_full = False
        self.halted = False
    
    def new_day(self, d):
        if d != self.current_date:
            self.current_date = d
            self.daily_pnl = 0.0
            self.is_full = False
            self.halted = False
    
    def get_risk(self):
        if self.halted:
            return 0.0
        if self.daily_pnl <= -self.max_loss:
            self.halted = True
            return 0.0
        if self.daily_pnl >= self.cushion:
            self.is_full = True
        if self.daily_pnl < 0 and self.is_full:
            self.is_full = False
        return self.full if self.is_full else self.starter
    
    def record(self, pnl):
        self.daily_pnl += pnl


# =============================================================================
# BACKTEST ENGINE
# =============================================================================

class OptimizedBacktest:
    
    def __init__(self, balance=10000.0):
        self.initial = balance
        self.balance = balance
        self.pm = PositionManager()
        self.trades = []
        self.signals = []
        self.data = {}
        self.equity_curve = [(None, balance)]
    
    def run(self):
        self._header()
        self._load()
        self._generate()
        self._execute()
        self._results()
    
    def _header(self):
        print()
        print("=" * 70)
        print("🏆 OPTIMALIZOVANÉ PORTFÓLIO - BEZ DAX40!")
        print("=" * 70)
        print(f"\n💰 Štartovací kapitál: €{self.initial:,.2f}")
        print()
        print("┌────────────┬──────┬──────┬─────────────────────────┐")
        print("│ Stratégia  │ PF   │ RR   │ Status                  │")
        print("├────────────┼──────┼──────┼─────────────────────────┤")
        print("│ SP500_M5   │ 2.63 │ 2.0  │ 🏆 NAJLEPŠIA            │")
        print("│ US30_M5    │ 2.17 │ 1.5  │ ✅ DOBRÁ                │")
        print("│ US100_M5   │ 1.45 │ 2.0  │ ⚠️ OK                   │")
        print("│ DAX40_M5   │ 0.44 │ -    │ ❌ VYHODENÁ (stratová)  │")
        print("└────────────┴──────┴──────┴─────────────────────────┘")
        print()
        print("📊 Parametre: LB=20, T=0.3, SL=1.5×ATR")
        print("⏰ Session: 15:30-22:00 CET (NY session)")
        print("💹 COMPOUNDING: ÁNO (risk z aktuálnej balance)")
    
    def _load(self):
        print("\n📁 LOADING DATA...")
        print("-" * 50)
        
        for name, cfg in STRATEGIES.items():
            df = load_mt5_csv(cfg['file'])
            if df is None:
                print(f"  ❌ {name}: {cfg['file']} not found")
                continue
            
            df = add_indicators(df)
            self.data[name] = df
            
            days = (df.index[-1] - df.index[0]).days
            print(f"  ✅ {name}: {len(df)} bars ({days} dní)")
    
    def _generate(self):
        print("\n📊 GENERATING SIGNALS...")
        print("-" * 50)
        
        for name, cfg in STRATEGIES.items():
            if name not in self.data:
                continue
            
            df = self.data[name]
            lb = cfg['lb']
            thresh = cfg['thresh']
            sl_mult = cfg['sl']
            rr = cfg['rr']
            spread = cfg['spread']
            session_start, session_end = cfg['session']
            filter_type = cfg['filter']
            
            mom_col = f'mom_{lb}'
            count = 0
            
            for i in range(50, len(df) - 100):
                bar = df.iloc[i]
                ts = df.index[i]
                
                # Session check
                if not (session_start <= ts.time() <= session_end):
                    continue
                
                # ATR check
                atr = bar['atr']
                if pd.isna(atr) or atr <= 0:
                    continue
                
                # Momentum cross
                threshold = atr * thresh * lb
                mom = bar[mom_col]
                prev_bar = df.iloc[i-1]
                prev_mom = prev_bar[mom_col]
                prev_thresh = prev_bar['atr'] * thresh * lb if not pd.isna(prev_bar['atr']) else threshold
                
                if not (mom > threshold and prev_mom <= prev_thresh):
                    continue
                
                # === FILTERS ===
                if filter_type == 'atr':
                    atr_min = cfg.get('atr_min', 0)
                    atr_max = cfg.get('atr_max', 999)
                    if not (atr_min <= atr <= atr_max):
                        continue
                
                elif filter_type == 'rsi':
                    if pd.isna(bar['rsi']) or bar['rsi'] >= 70:
                        continue
                
                # Calculate entry/SL/TP
                entry = bar['close'] + spread
                sl = entry - atr * sl_mult
                tp = entry + atr * sl_mult * rr
                
                self.signals.append({
                    'ts': ts,
                    'name': name,
                    'entry': entry,
                    'sl': sl,
                    'tp': tp,
                    'rr': rr,
                })
                count += 1
            
            months = (df.index[-1] - df.index[0]).days / 30
            per_mo = count / months if months > 0 else 0
            print(f"  {name}: {count} signals ({per_mo:.1f}/mo)")
        
        self.signals.sort(key=lambda x: x['ts'])
        print(f"\n  TOTAL: {len(self.signals)} signals")
    
    def _execute(self):
        print("\n🚀 EXECUTING TRADES (s COMPOUNDING!)...")
        print("-" * 50)
        
        for sig in self.signals:
            df = self.data.get(sig['name'])
            if df is None:
                continue
            
            self.pm.new_day(sig['ts'].date())
            risk_pct = self.pm.get_risk()
            if risk_pct == 0:
                continue
            
            # Simulate trade
            try:
                future = df.loc[sig['ts']:].iloc[1:200]
            except:
                continue
            
            if len(future) == 0:
                continue
            
            result = None
            exit_time = None
            
            for i in range(len(future)):
                bar = future.iloc[i]
                
                if bar['low'] <= sig['sl']:
                    result = 'SL'
                    exit_time = future.index[i]
                    break
                
                if bar['high'] >= sig['tp']:
                    result = 'TP'
                    exit_time = future.index[i]
                    break
            
            if result is None:
                continue
            
            # === COMPOUNDING! ===
            # Risk sa počíta z AKTUÁLNEJ balance, nie z pôvodnej!
            if result == 'SL':
                pnl_pct = -risk_pct
            else:
                pnl_pct = risk_pct * sig['rr']
            
            pnl_eur = self.balance * (pnl_pct / 100)  # Z aktuálnej balance!
            self.balance += pnl_eur                    # Aktualizuj balance!
            self.pm.record(pnl_pct)
            
            self.trades.append({
                'entry': sig['ts'],
                'exit': exit_time,
                'name': sig['name'],
                'result': result,
                'pnl_eur': pnl_eur,
                'pnl_pct': pnl_pct,
                'balance': self.balance,
            })
            
            self.equity_curve.append((exit_time, self.balance))
        
        print(f"  Executed: {len(self.trades)} trades")
        print(f"  Final: €{self.balance:,.2f}")
    
    def _results(self):
        print()
        print("=" * 70)
        print("📊 VÝSLEDKY - OPTIMALIZOVANÉ PORTFÓLIO")
        print("=" * 70)
        
        if not self.trades:
            print("\n❌ Žiadne obchody!")
            return
        
        wins = [t for t in self.trades if t['result'] == 'TP']
        losses = [t for t in self.trades if t['result'] == 'SL']
        
        total = len(self.trades)
        wr = len(wins) / total * 100
        
        gross_profit = sum(t['pnl_eur'] for t in wins)
        gross_loss = abs(sum(t['pnl_eur'] for t in losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else 99
        
        net = self.balance - self.initial
        ret = (net / self.initial) * 100
        
        days = (self.trades[-1]['exit'] - self.trades[0]['entry']).days
        months = max(1, days / 30)
        
        # Max drawdown
        peak = self.initial
        max_dd = 0
        for _, bal in self.equity_curve:
            if bal is None:
                continue
            if bal > peak:
                peak = bal
            dd = (peak - bal) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        print()
        print("💰 ÚČET:")
        print(f"   Začiatok:  €{self.initial:>12,.2f}")
        print(f"   Koniec:    €{self.balance:>12,.2f}")
        print(f"   Zisk:      €{net:>12,.2f}")
        print(f"   Return:     {ret:>12.1f}%")
        print(f"   Max DD:     {max_dd:>12.1f}%")
        print()
        print("📈 VÝKONNOSŤ:")
        print(f"   Obchody:    {total:>12}")
        print(f"   Výhry:      {len(wins):>12}")
        print(f"   Prehry:     {len(losses):>12}")
        print(f"   Win Rate:   {wr:>12.1f}%")
        print(f"   PF:         {pf:>12.2f}")
        print()
        print("📅 OBDOBIE:")
        print(f"   Dní:        {days:>12}")
        print(f"   Mesiacov:   {months:>12.1f}")
        print(f"   Obchody/mes:{total/months:>12.1f}")
        print(f"   Mesačný %:  {ret/months:>12.1f}%")
        print()
        
        # By strategy
        print("📋 PODĽA STRATÉGIE:")
        print("-" * 70)
        print(f"   {'Stratégia':<12} {'Obch':>5} {'WR':>7} {'PF':>7} {'Expect':>7} {'P&L':>12}")
        print("-" * 70)
        
        for name, cfg in STRATEGIES.items():
            strat_trades = [t for t in self.trades if t['name'] == name]
            if strat_trades:
                sw = len([t for t in strat_trades if t['result'] == 'TP'])
                spnl = sum(t['pnl_eur'] for t in strat_trades)
                swr = sw / len(strat_trades) * 100
                
                sp = sum(t['pnl_eur'] for t in strat_trades if t['result'] == 'TP')
                sl = abs(sum(t['pnl_eur'] for t in strat_trades if t['result'] == 'SL'))
                spf = sp / sl if sl > 0 else 99
                
                exp = cfg['expected_pf']
                status = "🏆" if spf >= 2.0 else "✅" if spf >= 1.5 else "⚠️" if spf >= 1.0 else "❌"
                
                print(f"   {status} {name:<10} {len(strat_trades):>5} {swr:>6.1f}% "
                      f"{spf:>6.2f} {exp:>6.2f} €{spnl:>+10,.2f}")
        print()
        
        # Last 10 trades
        print("📝 POSLEDNÝCH 10 OBCHODOV:")
        print("-" * 70)
        for t in self.trades[-10:]:
            icon = "✅" if t['result'] == 'TP' else "❌"
            print(f"   {icon} {t['entry'].strftime('%Y-%m-%d %H:%M')} "
                  f"{t['name']:<12} €{t['pnl_eur']:>+8.2f} → €{t['balance']:>10,.2f}")
        print()
        
        # Verdict
        print("=" * 70)
        if pf >= 2.0 and wr >= 50:
            print(f"🏆🏆 VÝBORNÉ! €{self.initial:,.0f} → €{self.balance:,.0f} ({ret:+.1f}%)")
        elif pf >= 1.5:
            print(f"✅ DOBRÉ - Profitabilné! PF={pf:.2f}, WR={wr:.1f}%")
        elif pf >= 1.2:
            print(f"⚠️ MARGINÁLNE - Malý edge (PF={pf:.2f})")
        else:
            print(f"❌ NEPROFITABILNÉ (PF={pf:.2f})")
        print("=" * 70)
        
        # Export
        pd.DataFrame(self.trades).to_csv('optimized_portfolio_results.csv', index=False)
        print(f"\n📁 Exportované: optimized_portfolio_results.csv")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    balance = 10000.0
    if len(sys.argv) > 1:
        try:
            balance = float(sys.argv[1])
        except:
            pass
    
    print("\n📋 USAGE:")
    print("  python optimized_portfolio.py         # €10,000")
    print("  python optimized_portfolio.py 5000    # €5,000")
    
    bt = OptimizedBacktest(balance)
    bt.run()
