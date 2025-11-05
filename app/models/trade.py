"""
Trade model for recording executed trades
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from app.models.database import Base


class Trade(Base):
    """Trade execution record"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Exchange info
    exchange = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    
    # Order details
    order_id = Column(String, unique=True, index=True)
    side = Column(String, nullable=False)  # buy, sell
    order_type = Column(String, nullable=False)  # market, limit
    
    # Trade execution
    amount = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)  # amount * price
    fee = Column(Float, default=0.0)
    fee_currency = Column(String)
    
    # Position details
    position_side = Column(String)  # long, short (for futures)
    leverage = Column(Float, default=1.0)
    
    # Strategy
    strategy_name = Column(String, index=True)
    
    # Status
    status = Column(String, default="open")  # open, closed, cancelled
    is_paper_trade = Column(Boolean, default=True)
    
    # PnL (calculated when position closed)
    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    executed_at = Column(DateTime)
    closed_at = Column(DateTime)
    
    # Additional metadata
    meta = Column(JSON, default={})
    notes = Column(String)
    
    def __repr__(self):
        return f"<Trade {self.symbol} {self.side} {self.amount} @ {self.price}>"
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "order_id": self.order_id,
            "side": self.side,
            "order_type": self.order_type,
            "amount": self.amount,
            "price": self.price,
            "cost": self.cost,
            "fee": self.fee,
            "fee_currency": self.fee_currency,
            "position_side": self.position_side,
            "leverage": self.leverage,
            "strategy_name": self.strategy_name,
            "status": self.status,
            "is_paper_trade": self.is_paper_trade,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "meta": self.meta,
            "notes": self.notes,
        }

