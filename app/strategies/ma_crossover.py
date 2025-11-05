"""
Moving Average Crossover Strategy
"""
import pandas as pd
from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from app.utils.logger import log


class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Generates buy signal when fast MA crosses above slow MA (golden cross)
    Generates sell signal when fast MA crosses below slow MA (death cross)
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", params: Optional[dict] = None):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'ma_type': 'ema',  # 'sma' or 'ema'
            'atr_multiplier': 2.0,  # For stop loss
            'risk_reward_ratio': 2.0,
            'min_data_points': 50
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(symbol, timeframe, default_params)
    
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """Analyze data and generate signal"""
        if len(data) < self.params['min_data_points']:
            return Signal.HOLD
        
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        ma_type = self.params['ma_type']
        
        # Get the appropriate MA columns
        fast_col = f"{ma_type}_{fast_period}"
        slow_col = f"{ma_type}_{slow_period}"
        
        # If columns don't exist, calculate them
        if fast_col not in data.columns:
            if ma_type == 'ema':
                data[fast_col] = data['close'].ewm(span=fast_period, adjust=False).mean()
            else:
                data[fast_col] = data['close'].rolling(window=fast_period).mean()
        
        if slow_col not in data.columns:
            if ma_type == 'ema':
                data[slow_col] = data['close'].ewm(span=slow_period, adjust=False).mean()
            else:
                data[slow_col] = data['close'].rolling(window=slow_period).mean()
        
        # Get last two values for crossover detection
        fast_current = data[fast_col].iloc[-1]
        fast_prev = data[fast_col].iloc[-2]
        slow_current = data[slow_col].iloc[-1]
        slow_prev = data[slow_col].iloc[-2]
        
        # Check for NaN values
        if pd.isna(fast_current) or pd.isna(slow_current):
            return Signal.HOLD
        
        # Detect golden cross (bullish)
        if fast_prev <= slow_prev and fast_current > slow_current:
            log.info(f"{self.name}: Golden cross detected for {self.symbol}")
            return Signal.BUY
        
        # Detect death cross (bearish)
        elif fast_prev >= slow_prev and fast_current < slow_current:
            log.info(f"{self.name}: Death cross detected for {self.symbol}")
            return Signal.SELL
        
        return Signal.HOLD
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price (current close price)"""
        if data.empty:
            return None
        return data['close'].iloc[-1]
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss using ATR"""
        # Note: This requires ATR to be calculated in the data
        # For now, use a simple percentage-based stop loss
        atr_multiplier = self.params.get('atr_multiplier', 2.0)
        stop_loss_pct = 0.02  # 2% default
        
        if side == 'long':
            return entry_price * (1 - stop_loss_pct)
        else:
            return entry_price * (1 + stop_loss_pct)
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit using risk/reward ratio"""
        stop_loss = self.get_stop_loss(entry_price, side)
        risk = abs(entry_price - stop_loss)
        reward = risk * self.params.get('risk_reward_ratio', 2.0)
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward

