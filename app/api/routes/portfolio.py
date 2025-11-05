"""
Portfolio and position management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.database import get_db
from app.models.position import Position
from app.models.trade import Trade
from app.utils.logger import log

router = APIRouter()


class PortfolioResponse(BaseModel):
    """Portfolio response"""
    initial_balance: float
    current_balance: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    total_return_pct: float
    open_positions: int
    total_trades: int


class PositionResponse(BaseModel):
    """Position response"""
    id: int
    symbol: str
    side: str
    amount: float
    entry_price: float
    current_price: Optional[float]
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    opened_at: str


@router.get("/portfolio")
async def get_portfolio(db: AsyncSession = Depends(get_db)):
    """Get portfolio overview"""
    try:
        # Get open positions
        positions_result = await db.execute(
            select(Position).where(Position.is_open == True)
        )
        positions = positions_result.scalars().all()
        
        # Get all trades
        trades_result = await db.execute(select(Trade))
        trades = trades_result.scalars().all()
        
        # Calculate metrics
        total_unrealized_pnl = sum(p.unrealized_pnl for p in positions)
        total_realized_pnl = sum(t.realized_pnl for t in trades if t.realized_pnl)
        
        # Get initial and current balance from config or calculate
        from app.config import get_settings
        settings = get_settings()
        
        initial_balance = 10000.0  # Default, should be stored in DB
        current_balance = initial_balance + total_realized_pnl
        
        total_pnl = total_realized_pnl + total_unrealized_pnl
        total_return = (total_pnl / initial_balance * 100) if initial_balance > 0 else 0.0
        
        return PortfolioResponse(
            initial_balance=initial_balance,
            current_balance=current_balance,
            unrealized_pnl=total_unrealized_pnl,
            realized_pnl=total_realized_pnl,
            total_pnl=total_pnl,
            total_return_pct=total_return,
            open_positions=len(positions),
            total_trades=len(trades)
        )
        
    except Exception as e:
        log.error(f"Error fetching portfolio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions(
    open_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get all positions"""
    try:
        query = select(Position).order_by(desc(Position.opened_at))
        
        if open_only:
            query = query.where(Position.is_open == True)
        
        result = await db.execute(query)
        positions = result.scalars().all()
        
        return {
            "positions": [p.to_dict() for p in positions],
            "count": len(positions)
        }
        
    except Exception as e:
        log.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions/{position_id}")
async def get_position(
    position_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific position"""
    try:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = result.scalar_one_or_none()
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        return position.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching position: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/positions/{position_id}/close")
async def close_position(
    position_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Manually close a position"""
    try:
        result = await db.execute(
            select(Position).where(Position.id == position_id)
        )
        position = result.scalar_one_or_none()
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        if not position.is_open:
            raise HTTPException(status_code=400, detail="Position is already closed")
        
        # TODO: Execute actual close order via OrderExecutor
        # For now, just mark as closed
        from datetime import datetime
        position.is_open = False
        position.closed_at = datetime.utcnow()
        await db.commit()
        
        log.info(f"Manually closed position {position_id}")
        
        return {
            "message": "Position closed successfully",
            "position_id": position_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error closing position: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
async def get_trades(
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get trade history"""
    try:
        query = select(Trade).order_by(desc(Trade.created_at))
        
        if symbol:
            query = query.where(Trade.symbol == symbol)
        
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
        # Get total count
        count_result = await db.execute(select(Trade))
        total_count = len(count_result.scalars().all())
        
        return {
            "trades": [t.to_dict() for t in trades],
            "count": len(trades),
            "total": total_count
        }
        
    except Exception as e:
        log.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/{trade_id}")
async def get_trade(
    trade_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get specific trade"""
    try:
        result = await db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        
        return trade.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

