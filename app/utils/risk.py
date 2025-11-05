"""
Risk management utilities
"""
from typing import Optional
from decimal import Decimal


class RiskManager:
    """Risk management calculations"""
    
    def __init__(
        self,
        max_position_size: float,
        risk_per_trade: float,
        max_daily_loss: float,
        max_open_positions: int
    ):
        self.max_position_size = Decimal(str(max_position_size))
        self.risk_per_trade = Decimal(str(risk_per_trade))
        self.max_daily_loss = Decimal(str(max_daily_loss))
        self.max_open_positions = max_open_positions
        self.daily_pnl = Decimal('0')
    
    def calculate_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        method: str = "percentage"
    ) -> float:
        """
        Calculate position size based on risk parameters
        
        Args:
            portfolio_value: Total portfolio value
            entry_price: Entry price for position
            stop_loss: Stop loss price (if applicable)
            method: Sizing method - 'fixed', 'percentage', 'kelly'
        
        Returns:
            Position size in base currency
        """
        portfolio = Decimal(str(portfolio_value))
        
        if method == "fixed":
            # Fixed position size
            size = min(self.max_position_size, portfolio * Decimal('0.1'))
            
        elif method == "percentage":
            # Percentage of portfolio
            size = portfolio * self.risk_per_trade
            size = min(size, self.max_position_size)
            
        elif method == "kelly" and stop_loss:
            # Kelly criterion with stop loss
            entry = Decimal(str(entry_price))
            stop = Decimal(str(stop_loss))
            risk_amount = portfolio * self.risk_per_trade
            
            if stop < entry:  # Long position
                risk_per_unit = entry - stop
            else:  # Short position
                risk_per_unit = stop - entry
            
            if risk_per_unit > 0:
                size = risk_amount / risk_per_unit
                size = min(size, self.max_position_size)
            else:
                size = self.max_position_size * Decimal('0.1')
        else:
            size = self.max_position_size * Decimal('0.1')
        
        return float(size)
    
    def can_open_position(
        self,
        current_positions: int,
        position_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a new position can be opened
        
        Returns:
            (can_open, reason_if_not)
        """
        # Check max open positions
        if current_positions >= self.max_open_positions:
            return False, f"Maximum open positions ({self.max_open_positions}) reached"
        
        # Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            return False, f"Daily loss limit (${self.max_daily_loss}) reached"
        
        # Check position size
        pos_value = Decimal(str(position_value))
        if pos_value > self.max_position_size:
            return False, f"Position size exceeds maximum (${self.max_position_size})"
        
        return True, None
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracker"""
        self.daily_pnl += Decimal(str(pnl))
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of each day)"""
        self.daily_pnl = Decimal('0')
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: str,
        atr: Optional[float] = None,
        percentage: float = 0.02
    ) -> float:
        """
        Calculate stop loss price
        
        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            atr: Average True Range (if available)
            percentage: Stop loss percentage
        
        Returns:
            Stop loss price
        """
        entry = Decimal(str(entry_price))
        
        if atr:
            # ATR-based stop loss (2x ATR)
            stop_distance = Decimal(str(atr)) * Decimal('2')
        else:
            # Percentage-based stop loss
            stop_distance = entry * Decimal(str(percentage))
        
        if side.lower() == 'buy':
            stop_loss = entry - stop_distance
        else:
            stop_loss = entry + stop_distance
        
        return float(stop_loss)
    
    def calculate_take_profit(
        self,
        entry_price: float,
        side: str,
        risk_reward_ratio: float = 2.0
    ) -> float:
        """
        Calculate take profit price based on risk/reward ratio
        
        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
            risk_reward_ratio: Reward to risk ratio
        
        Returns:
            Take profit price
        """
        entry = Decimal(str(entry_price))
        stop_loss = Decimal(str(self.calculate_stop_loss(float(entry), side)))
        
        risk = abs(entry - stop_loss)
        reward = risk * Decimal(str(risk_reward_ratio))
        
        if side.lower() == 'buy':
            take_profit = entry + reward
        else:
            take_profit = entry - reward
        
        return float(take_profit)

