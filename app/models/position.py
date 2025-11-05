"""
Position model for tracking open positions
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from app.models.database import Base


class Position(Base):
    """Open position tracking"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Exchange info
    exchange = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    
    # Position details
    side = Column(String, nullable=False)  # long, short
    amount = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float)
    
    # Futures specific
    leverage = Column(Float, default=1.0)
    margin = Column(Float)
    liquidation_price = Column(Float)
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trailing_stop = Column(Float)
    
    # PnL
    unrealized_pnl = Column(Float, default=0.0)
    unrealized_pnl_percentage = Column(Float, default=0.0)
    
    # Strategy
    strategy_name = Column(String, index=True)
    
    # Status
    is_open = Column(Boolean, default=True, index=True)
    is_paper_trade = Column(Boolean, default=True)
    
    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)
    
    # Related trades
    entry_trade_id = Column(Integer)
    exit_trade_id = Column(Integer)
    
    # Additional metadata
    meta = Column(JSON, default={})
    notes = Column(String)
    
    def __repr__(self):
        return f"<Position {self.symbol} {self.side} {self.amount} @ {self.entry_price}>"
    
    def calculate_pnl(self) -> tuple[float, float]:
        """
        Calculate unrealized PnL
        Returns (pnl_value, pnl_percentage)
        """
        if not self.current_price:
            return 0.0, 0.0
        
        position_value = self.amount * self.entry_price
        current_value = self.amount * self.current_price
        
        if self.side == "long":
            pnl = current_value - position_value
        else:  # short
            pnl = position_value - current_value
        
        pnl_pct = (pnl / position_value) * 100 if position_value > 0 else 0.0
        
        return pnl, pnl_pct
    
    def update_pnl(self, current_price: float):
        """Update current price and recalculate PnL"""
        self.current_price = current_price
        self.unrealized_pnl, self.unrealized_pnl_percentage = self.calculate_pnl()
        self.updated_at = datetime.utcnow()
    
    def should_close(self) -> tuple[bool, str]:
        """
        Check if position should be closed based on stop loss/take profit
        Returns (should_close, reason)
        """
        if not self.current_price:
            return False, ""
        
        # Check stop loss
        if self.stop_loss:
            if self.side == "long" and self.current_price <= self.stop_loss:
                return True, "stop_loss"
            elif self.side == "short" and self.current_price >= self.stop_loss:
                return True, "stop_loss"
        
        # Check take profit
        if self.take_profit:
            if self.side == "long" and self.current_price >= self.take_profit:
                return True, "take_profit"
            elif self.side == "short" and self.current_price <= self.take_profit:
                return True, "take_profit"
        
        return False, ""
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "side": self.side,
            "amount": self.amount,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "leverage": self.leverage,
            "margin": self.margin,
            "liquidation_price": self.liquidation_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "trailing_stop": self.trailing_stop,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_percentage": self.unrealized_pnl_percentage,
            "strategy_name": self.strategy_name,
            "is_open": self.is_open,
            "is_paper_trade": self.is_paper_trade,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "entry_trade_id": self.entry_trade_id,
            "exit_trade_id": self.exit_trade_id,
            "meta": self.meta,
            "notes": self.notes,
        }

