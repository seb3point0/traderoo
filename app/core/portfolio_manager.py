"""
Portfolio and position management
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import Position
from app.models.trade import Trade
from app.utils.logger import log
from app.utils.risk import RiskManager
from app.config import get_settings

settings = get_settings()


class PortfolioManager:
    """Manages portfolio, positions, and P&L tracking"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.risk_manager = RiskManager(
            max_position_size=settings.max_position_size,
            risk_per_trade=settings.risk_per_trade,
            max_daily_loss=settings.max_daily_loss,
            max_open_positions=settings.max_open_positions
        )
        self.positions: Dict[str, Position] = {}
        self.initial_balance = 0.0
        self.current_balance = 0.0
    
    async def initialize(self, initial_balance: float):
        """Initialize portfolio with starting balance"""
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        
        # Load open positions from database
        await self.load_open_positions()
        
        log.info(f"Initialized portfolio with ${initial_balance}")
    
    async def load_open_positions(self):
        """Load open positions from database"""
        try:
            result = await self.db.execute(
                select(Position).where(Position.is_open == True)
            )
            positions = result.scalars().all()
            
            for position in positions:
                key = f"{position.exchange}:{position.symbol}"
                self.positions[key] = position
            
            log.info(f"Loaded {len(self.positions)} open positions")
        except Exception as e:
            log.error(f"Error loading positions: {e}")
    
    async def open_position(
        self,
        exchange: str,
        symbol: str,
        side: str,
        amount: float,
        entry_price: float,
        strategy_name: str,
        leverage: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trade_id: Optional[int] = None
    ) -> Position:
        """Open a new position"""
        try:
            position = Position(
                exchange=exchange,
                symbol=symbol,
                side=side,
                amount=amount,
                entry_price=entry_price,
                current_price=entry_price,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                strategy_name=strategy_name,
                is_open=True,
                is_paper_trade=settings.paper_trading,
                entry_trade_id=trade_id,
                opened_at=datetime.utcnow()
            )
            
            # Calculate initial values
            position.update_pnl(entry_price)
            
            # Add to database
            self.db.add(position)
            await self.db.commit()
            await self.db.refresh(position)
            
            # Add to local positions
            key = f"{exchange}:{symbol}"
            self.positions[key] = position
            
            log.info(f"Opened position: {side} {amount} {symbol} @ {entry_price}")
            
            return position
            
        except Exception as e:
            log.error(f"Error opening position: {e}")
            await self.db.rollback()
            raise
    
    async def close_position(
        self,
        position: Position,
        exit_price: float,
        trade_id: Optional[int] = None
    ) -> float:
        """Close an existing position and return realized P&L"""
        try:
            # Calculate final P&L
            position.update_pnl(exit_price)
            realized_pnl = position.unrealized_pnl
            
            # Update position
            position.is_open = False
            position.closed_at = datetime.utcnow()
            position.exit_trade_id = trade_id
            
            await self.db.commit()
            
            # Remove from local positions
            key = f"{position.exchange}:{position.symbol}"
            if key in self.positions:
                del self.positions[key]
            
            # Update balance
            self.current_balance += realized_pnl
            
            # Update risk manager
            self.risk_manager.update_daily_pnl(realized_pnl)
            
            log.info(f"Closed position: {position.symbol} | P&L: ${realized_pnl:.2f}")
            
            return realized_pnl
            
        except Exception as e:
            log.error(f"Error closing position: {e}")
            await self.db.rollback()
            raise
    
    async def update_position_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions"""
        for key, position in self.positions.items():
            symbol = position.symbol
            if symbol in prices:
                position.update_pnl(prices[symbol])
                
                # Check if position should be closed (stop loss/take profit)
                should_close, reason = position.should_close()
                if should_close:
                    log.warning(f"Position {symbol} triggered {reason}")
                    # Note: Actual closing should be handled by order executor
        
        await self.db.commit()
    
    async def get_position(self, exchange: str, symbol: str) -> Optional[Position]:
        """Get position by exchange and symbol"""
        key = f"{exchange}:{symbol}"
        return self.positions.get(key)
    
    async def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
    
    async def get_portfolio_value(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """Calculate total portfolio value including unrealized P&L"""
        total_value = self.current_balance
        
        if current_prices:
            for position in self.positions.values():
                if position.symbol in current_prices:
                    position.update_pnl(current_prices[position.symbol])
                    total_value += position.unrealized_pnl
        
        return total_value
    
    async def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        # Calculate total unrealized P&L
        total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        
        # Calculate total realized P&L
        result = await self.db.execute(
            select(Trade).where(Trade.status == "closed")
        )
        trades = result.scalars().all()
        total_realized_pnl = sum(t.realized_pnl for t in trades)
        
        # Calculate returns
        total_pnl = total_realized_pnl + total_unrealized_pnl
        total_return = (total_pnl / self.initial_balance * 100) if self.initial_balance > 0 else 0.0
        
        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "unrealized_pnl": total_unrealized_pnl,
            "realized_pnl": total_realized_pnl,
            "total_pnl": total_pnl,
            "total_return_pct": total_return,
            "open_positions": len(self.positions),
            "total_trades": len(trades)
        }
    
    def can_open_position(self, position_value: float) -> tuple[bool, Optional[str]]:
        """Check if a new position can be opened based on risk management"""
        current_positions = len(self.positions)
        return self.risk_manager.can_open_position(current_positions, position_value)
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: Optional[float] = None,
        method: str = "percentage"
    ) -> float:
        """Calculate position size based on risk management"""
        portfolio_value = self.current_balance
        return self.risk_manager.calculate_position_size(
            portfolio_value, entry_price, stop_loss, method
        )
    
    async def get_daily_pnl(self) -> float:
        """Get today's P&L"""
        today = datetime.utcnow().date()
        
        result = await self.db.execute(
            select(Trade).where(
                Trade.closed_at >= datetime.combine(today, datetime.min.time())
            )
        )
        trades = result.scalars().all()
        
        return sum(t.realized_pnl for t in trades)
    
    def reset_daily_limits(self):
        """Reset daily risk limits (call at start of each day)"""
        self.risk_manager.reset_daily_pnl()
        log.info("Reset daily risk limits")

