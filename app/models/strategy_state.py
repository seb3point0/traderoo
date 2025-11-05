"""
Strategy state model for persisting strategy data
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON
from app.models.database import Base


class StrategyState(Base):
    """Strategy state and performance tracking"""
    __tablename__ = "strategy_states"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Strategy identification
    strategy_name = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False, index=True)
    exchange = Column(String, nullable=False)
    timeframe = Column(String, default="1h")
    
    # Status
    is_active = Column(Boolean, default=False, index=True)
    is_paper_trade = Column(Boolean, default=True)
    
    # Strategy parameters
    parameters = Column(JSON, default={})
    
    # State data (for strategies that need to persist state)
    state_data = Column(JSON, default={})
    
    # Performance metrics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    total_pnl = Column(Float, default=0.0)
    total_fees = Column(Float, default=0.0)
    
    max_drawdown = Column(Float, default=0.0)
    max_drawdown_percentage = Column(Float, default=0.0)
    
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    # Capital tracking
    initial_capital = Column(Float)
    current_capital = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    deactivated_at = Column(DateTime)
    last_trade_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional metadata
    meta = Column(JSON, default={})
    notes = Column(String)
    
    def __repr__(self):
        return f"<StrategyState {self.strategy_name} {self.symbol}>"
    
    def update_performance(self, trade_pnl: float, is_winner: bool):
        """Update performance metrics after a trade"""
        self.total_trades += 1
        self.total_pnl += trade_pnl
        
        if is_winner:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Calculate win rate
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        # Update timestamps
        self.last_trade_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def calculate_profit_factor(self, total_wins: float, total_losses: float):
        """Calculate profit factor (gross profit / gross loss)"""
        if total_losses != 0:
            self.profit_factor = abs(total_wins / total_losses)
        else:
            self.profit_factor = float('inf') if total_wins > 0 else 0.0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timeframe": self.timeframe,
            "is_active": self.is_active,
            "is_paper_trade": self.is_paper_trade,
            "parameters": self.parameters,
            "state_data": self.state_data,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": self.total_pnl,
            "total_fees": self.total_fees,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percentage": self.max_drawdown_percentage,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "sharpe_ratio": self.sharpe_ratio,
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "last_trade_at": self.last_trade_at.isoformat() if self.last_trade_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "meta": self.meta,
            "notes": self.notes,
        }

