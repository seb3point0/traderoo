"""
Base strategy class for all trading strategies
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum
import pandas as pd
from datetime import datetime

from app.utils.logger import log


class Signal(Enum):
    """Trading signals"""
    BUY = "buy"
    SELL = "sell"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"
    HOLD = "hold"


class BaseStrategy(ABC):
    """Abstract base class for trading strategies"""
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        params: Optional[Dict[str, Any]] = None
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.params = params or {}
        self.name = self.__class__.__name__
        
        # Strategy state
        self.is_active = False
        self.last_signal = Signal.HOLD
        self.last_signal_time: Optional[datetime] = None
        self.position_side: Optional[str] = None  # 'long', 'short', None
        
        # Performance tracking
        self.signals_generated = 0
        self.trades_executed = 0
        
        log.info(f"Initialized {self.name} for {symbol} ({timeframe})")
    
    @abstractmethod
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data and generate trading signal
        
        Args:
            data: DataFrame with OHLCV data and indicators
        
        Returns:
            Trading signal (BUY, SELL, CLOSE, HOLD)
        """
        pass
    
    @abstractmethod
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get suggested entry price"""
        pass
    
    @abstractmethod
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss price"""
        pass
    
    @abstractmethod
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit price"""
        pass
    
    def get_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on risk management
        
        Can be overridden by specific strategies
        """
        risk_per_trade = self.params.get('risk_per_trade', 0.02)  # 2% default
        
        if stop_loss and entry_price:
            # Calculate position size based on stop loss
            risk_amount = portfolio_value * risk_per_trade
            price_risk = abs(entry_price - stop_loss)
            position_size = risk_amount / price_risk if price_risk > 0 else 0
        else:
            # Fixed percentage of portfolio
            position_size = (portfolio_value * risk_per_trade) / entry_price if entry_price > 0 else 0
        
        return position_size
    
    async def should_close_position(
        self,
        data: pd.DataFrame,
        position_side: str,
        entry_price: float
    ) -> tuple[bool, str]:
        """
        Check if position should be closed
        
        Returns:
            (should_close, reason)
        """
        # Get latest data
        if data.empty:
            return False, ""
        
        current_price = data['close'].iloc[-1]
        
        # Check stop loss
        stop_loss = self.get_stop_loss(entry_price, position_side)
        if stop_loss:
            if position_side == 'long' and current_price <= stop_loss:
                return True, "stop_loss"
            elif position_side == 'short' and current_price >= stop_loss:
                return True, "stop_loss"
        
        # Check take profit
        take_profit = self.get_take_profit(entry_price, position_side)
        if take_profit:
            if position_side == 'long' and current_price >= take_profit:
                return True, "take_profit"
            elif position_side == 'short' and current_price <= take_profit:
                return True, "take_profit"
        
        # Check strategy-specific exit conditions
        signal = await self.analyze(data)
        if position_side == 'long' and signal == Signal.SELL:
            return True, "signal"
        elif position_side == 'short' and signal == Signal.BUY:
            return True, "signal"
        
        return False, ""
    
    def validate_signal(self, signal: Signal, data: pd.DataFrame) -> bool:
        """
        Validate trading signal before execution
        
        Can be overridden for custom validation
        """
        if data.empty:
            return False
        
        # Check minimum data requirement
        min_data_points = self.params.get('min_data_points', 50)
        if len(data) < min_data_points:
            log.warning(f"Insufficient data for {self.name}: {len(data)} < {min_data_points}")
            return False
        
        # Avoid duplicate signals
        if signal == self.last_signal:
            return False
        
        # Check cooldown period (prevent overtrading)
        cooldown_minutes = self.params.get('cooldown_minutes', 60)
        if self.last_signal_time:
            time_since_last = (datetime.utcnow() - self.last_signal_time).total_seconds() / 60
            if time_since_last < cooldown_minutes:
                return False
        
        return True
    
    def update_signal(self, signal: Signal):
        """Update last signal and timestamp"""
        self.last_signal = signal
        self.last_signal_time = datetime.utcnow()
        self.signals_generated += 1
    
    def get_state(self) -> Dict:
        """Get strategy state for persistence"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'is_active': self.is_active,
            'last_signal': self.last_signal.value,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'position_side': self.position_side,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'params': self.params
        }
    
    def load_state(self, state: Dict):
        """Load strategy state from persistence"""
        self.is_active = state.get('is_active', False)
        self.last_signal = Signal(state.get('last_signal', 'hold'))
        
        last_signal_time_str = state.get('last_signal_time')
        if last_signal_time_str:
            self.last_signal_time = datetime.fromisoformat(last_signal_time_str)
        
        self.position_side = state.get('position_side')
        self.signals_generated = state.get('signals_generated', 0)
        self.trades_executed = state.get('trades_executed', 0)
        
        log.info(f"Loaded state for {self.name}")
    
    def get_description(self) -> str:
        """Get strategy description"""
        return f"{self.name} strategy for {self.symbol} on {self.timeframe} timeframe"
    
    def get_parameters(self) -> Dict:
        """Get strategy parameters"""
        return self.params.copy()
    
    def update_parameters(self, new_params: Dict):
        """Update strategy parameters"""
        self.params.update(new_params)
        log.info(f"Updated parameters for {self.name}: {new_params}")
    
    def __repr__(self):
        return f"<{self.name} {self.symbol} {self.timeframe}>"

