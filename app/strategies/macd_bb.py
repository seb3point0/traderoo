"""
MACD + Bollinger Bands Confluence Strategy
"""
import pandas as pd
from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from app.utils.logger import log


class MACDBBStrategy(BaseStrategy):
    """
    MACD + Bollinger Bands Confluence Strategy
    
    Combines MACD crossovers with Bollinger Bands for confirmation
    Buys when MACD crosses up AND price touches lower BB
    Sells when MACD crosses down AND price touches upper BB
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", params: Optional[dict] = None):
        default_params = {
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'bb_touch_threshold': 0.01,  # Within 1% of BB
            'stop_loss_pct': 0.025,
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
        
        # Check for required indicators
        if 'macd' not in data.columns or 'macd_signal' not in data.columns:
            return Signal.HOLD
        
        if 'bb_upper' not in data.columns or 'bb_lower' not in data.columns:
            return Signal.HOLD
        
        # Get latest values
        macd = data['macd'].iloc[-1]
        macd_prev = data['macd'].iloc[-2]
        signal = data['macd_signal'].iloc[-1]
        signal_prev = data['macd_signal'].iloc[-2]
        
        current_price = data['close'].iloc[-1]
        bb_upper = data['bb_upper'].iloc[-1]
        bb_lower = data['bb_lower'].iloc[-1]
        bb_middle = data['bb_middle'].iloc[-1] if 'bb_middle' in data.columns else (bb_upper + bb_lower) / 2
        
        # Check for NaN
        if pd.isna(macd) or pd.isna(signal) or pd.isna(bb_upper) or pd.isna(bb_lower):
            return Signal.HOLD
        
        # Detect MACD crossover
        macd_bullish_cross = macd_prev < signal_prev and macd > signal
        macd_bearish_cross = macd_prev > signal_prev and macd < signal
        
        # Check Bollinger Bands position
        threshold = self.params['bb_touch_threshold']
        price_at_lower_bb = abs(current_price - bb_lower) / bb_lower <= threshold
        price_at_upper_bb = abs(current_price - bb_upper) / bb_upper <= threshold
        
        # Additional confirmation: price should be on correct side of middle BB
        price_below_middle = current_price < bb_middle
        price_above_middle = current_price > bb_middle
        
        # Buy signal: MACD bullish cross + price near/at lower BB
        if macd_bullish_cross and (price_at_lower_bb or price_below_middle):
            log.info(f"{self.name}: Bullish confluence signal for {self.symbol}")
            log.info(f"MACD: {macd:.4f}, Signal: {signal:.4f}, Price: ${current_price:.2f}, BB Lower: ${bb_lower:.2f}")
            return Signal.BUY
        
        # Sell signal: MACD bearish cross + price near/at upper BB
        elif macd_bearish_cross and (price_at_upper_bb or price_above_middle):
            log.info(f"{self.name}: Bearish confluence signal for {self.symbol}")
            log.info(f"MACD: {macd:.4f}, Signal: {signal:.4f}, Price: ${current_price:.2f}, BB Upper: ${bb_upper:.2f}")
            return Signal.SELL
        
        return Signal.HOLD
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price"""
        if data.empty:
            return None
        return data['close'].iloc[-1]
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss"""
        stop_loss_pct = self.params.get('stop_loss_pct', 0.025)
        
        if side == 'long':
            return entry_price * (1 - stop_loss_pct)
        else:
            return entry_price * (1 + stop_loss_pct)
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit"""
        stop_loss = self.get_stop_loss(entry_price, side)
        risk = abs(entry_price - stop_loss)
        reward = risk * self.params.get('risk_reward_ratio', 2.0)
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward

