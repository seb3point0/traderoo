"""
RSI Mean Reversion Strategy
"""
import pandas as pd
from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from app.utils.logger import log


class RSIStrategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy
    
    Buys when RSI is oversold (< 30)
    Sells when RSI is overbought (> 70)
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", params: Optional[dict] = None):
        default_params = {
            'rsi_period': 14,
            'oversold_level': 30,
            'overbought_level': 70,
            'extreme_oversold': 20,
            'extreme_overbought': 80,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'min_data_points': 50
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(symbol, timeframe, default_params)
    
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """Analyze data and generate signal"""
        if len(data) < self.params['min_data_points']:
            return Signal.HOLD
        
        # Get RSI
        if 'rsi' not in data.columns:
            # Calculate RSI if not present
            period = self.params['rsi_period']
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
        
        rsi_current = data['rsi'].iloc[-1]
        rsi_prev = data['rsi'].iloc[-2]
        
        if pd.isna(rsi_current):
            return Signal.HOLD
        
        oversold = self.params['oversold_level']
        overbought = self.params['overbought_level']
        
        # Buy signal: RSI crosses above oversold level from below
        if rsi_prev < oversold and rsi_current >= oversold:
            log.info(f"{self.name}: RSI oversold signal for {self.symbol} (RSI: {rsi_current:.2f})")
            return Signal.BUY
        
        # Sell signal: RSI crosses below overbought level from above
        elif rsi_prev > overbought and rsi_current <= overbought:
            log.info(f"{self.name}: RSI overbought signal for {self.symbol} (RSI: {rsi_current:.2f})")
            return Signal.SELL
        
        return Signal.HOLD
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price"""
        if data.empty:
            return None
        return data['close'].iloc[-1]
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss"""
        stop_loss_pct = self.params.get('stop_loss_pct', 0.02)
        
        if side == 'long':
            return entry_price * (1 - stop_loss_pct)
        else:
            return entry_price * (1 + stop_loss_pct)
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit"""
        take_profit_pct = self.params.get('take_profit_pct', 0.04)
        
        if side == 'long':
            return entry_price * (1 + take_profit_pct)
        else:
            return entry_price * (1 - take_profit_pct)

