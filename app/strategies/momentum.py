"""
Momentum Breakout Strategy
"""
import pandas as pd
from typing import Optional
from app.strategies.base import BaseStrategy, Signal
from app.utils.logger import log


class MomentumStrategy(BaseStrategy):
    """
    Momentum Breakout Strategy
    
    Buys when price breaks above resistance with high volume
    Sells when price breaks below support with high volume
    Uses ADX for trend strength confirmation
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", params: Optional[dict] = None):
        default_params = {
            'breakout_period': 20,
            'volume_multiplier': 1.5,  # Volume must be 1.5x average
            'adx_threshold': 25,  # Minimum ADX for strong trend
            'atr_multiplier': 2.0,
            'risk_reward_ratio': 2.5,
            'min_data_points': 50
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(symbol, timeframe, default_params)
    
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """Analyze data and generate signal"""
        if len(data) < self.params['min_data_points']:
            return Signal.HOLD
        
        period = self.params['breakout_period']
        
        # Calculate support and resistance
        resistance = data['high'].rolling(window=period).max().iloc[-2]
        support = data['low'].rolling(window=period).min().iloc[-2]
        
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1] if 'volume' in data.columns else 0
        avg_volume = data['volume'].rolling(window=period).mean().iloc[-1] if 'volume' in data.columns else 1
        
        # Check volume confirmation
        volume_multiplier = self.params['volume_multiplier']
        high_volume = current_volume >= (avg_volume * volume_multiplier)
        
        # Check ADX for trend strength (if available)
        strong_trend = True
        if 'adx' in data.columns:
            adx = data['adx'].iloc[-1]
            if not pd.isna(adx):
                strong_trend = adx >= self.params['adx_threshold']
        
        # Bullish breakout: price breaks above resistance with high volume
        if current_price > resistance and high_volume and strong_trend:
            log.info(f"{self.name}: Bullish breakout for {self.symbol} at ${current_price:.2f} (resistance: ${resistance:.2f})")
            return Signal.BUY
        
        # Bearish breakdown: price breaks below support with high volume
        elif current_price < support and high_volume and strong_trend:
            log.info(f"{self.name}: Bearish breakdown for {self.symbol} at ${current_price:.2f} (support: ${support:.2f})")
            return Signal.SELL
        
        return Signal.HOLD
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price"""
        if data.empty:
            return None
        return data['close'].iloc[-1]
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss using ATR"""
        # Use ATR-based stop loss for volatility adjustment
        atr_multiplier = self.params.get('atr_multiplier', 2.0)
        
        # Default to 2% if ATR not available
        stop_loss_pct = 0.02
        
        if side == 'long':
            return entry_price * (1 - stop_loss_pct)
        else:
            return entry_price * (1 + stop_loss_pct)
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit"""
        stop_loss = self.get_stop_loss(entry_price, side)
        risk = abs(entry_price - stop_loss)
        reward = risk * self.params.get('risk_reward_ratio', 2.5)
        
        if side == 'long':
            return entry_price + reward
        else:
            return entry_price - reward

