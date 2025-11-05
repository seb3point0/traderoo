"""
Strategy management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.strategy_state import StrategyState
from app.utils.logger import log

router = APIRouter()


class StrategyActivateRequest(BaseModel):
    """Request to activate a strategy"""
    strategy_name: str
    symbol: str
    exchange: str = "binance"
    timeframe: str = "1h"
    parameters: Dict[str, Any] = {}


class StrategyResponse(BaseModel):
    """Strategy response"""
    id: int
    strategy_name: str
    symbol: str
    exchange: str
    timeframe: str
    is_active: bool
    parameters: Dict[str, Any]
    total_trades: int
    win_rate: float
    total_pnl: float


@router.get("/strategies")
async def list_strategies():
    """List all available strategies"""
    available_strategies = [
        {
            "name": "MACrossoverStrategy",
            "description": "Moving Average Crossover - Trend following strategy",
            "default_params": {
                "fast_period": 12,
                "slow_period": 26,
                "ma_type": "ema"
            }
        },
        {
            "name": "RSIStrategy",
            "description": "RSI Mean Reversion - Oversold/overbought signals",
            "default_params": {
                "rsi_period": 14,
                "oversold_level": 30,
                "overbought_level": 70
            }
        },
        {
            "name": "GridTradingStrategy",
            "description": "Grid Trading - Profit from range-bound markets",
            "default_params": {
                "grid_levels": 10,
                "grid_spacing_pct": 0.01
            }
        },
        {
            "name": "MomentumStrategy",
            "description": "Momentum Breakout - Capitalize on strong trends",
            "default_params": {
                "breakout_period": 20,
                "volume_multiplier": 1.5
            }
        },
        {
            "name": "MACDBBStrategy",
            "description": "MACD + Bollinger Bands - Confluence strategy",
            "default_params": {
                "macd_fast": 12,
                "macd_slow": 26,
                "bb_period": 20
            }
        }
    ]
    
    return {"strategies": available_strategies}


@router.post("/strategies/activate")
async def activate_strategy(
    request: StrategyActivateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Activate a trading strategy"""
    try:
        # Check if strategy already exists
        result = await db.execute(
            select(StrategyState).where(
                StrategyState.strategy_name == request.strategy_name,
                StrategyState.symbol == request.symbol,
                StrategyState.exchange == request.exchange
            )
        )
        strategy_state = result.scalar_one_or_none()
        
        if strategy_state:
            # Update existing strategy
            strategy_state.is_active = True
            strategy_state.parameters = request.parameters
            strategy_state.timeframe = request.timeframe
        else:
            # Create new strategy state
            strategy_state = StrategyState(
                strategy_name=request.strategy_name,
                symbol=request.symbol,
                exchange=request.exchange,
                timeframe=request.timeframe,
                is_active=True,
                parameters=request.parameters
            )
            db.add(strategy_state)
        
        await db.commit()
        await db.refresh(strategy_state)
        
        log.info(f"Activated strategy: {request.strategy_name} for {request.symbol}")
        
        return {
            "message": "Strategy activated successfully",
            "strategy": strategy_state.to_dict()
        }
        
    except Exception as e:
        log.error(f"Error activating strategy: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/strategies/{strategy_id}/deactivate")
async def deactivate_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a trading strategy"""
    try:
        result = await db.execute(
            select(StrategyState).where(StrategyState.id == strategy_id)
        )
        strategy_state = result.scalar_one_or_none()
        
        if not strategy_state:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy_state.is_active = False
        await db.commit()
        
        log.info(f"Deactivated strategy: {strategy_state.strategy_name}")
        
        return {"message": "Strategy deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error deactivating strategy: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/active")
async def get_active_strategies(db: AsyncSession = Depends(get_db)):
    """Get all active strategies"""
    try:
        result = await db.execute(
            select(StrategyState).where(StrategyState.is_active == True)
        )
        strategies = result.scalars().all()
        
        return {
            "strategies": [s.to_dict() for s in strategies],
            "count": len(strategies)
        }
        
    except Exception as e:
        log.error(f"Error fetching active strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/strategies/{strategy_id}")
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get strategy details"""
    try:
        result = await db.execute(
            select(StrategyState).where(StrategyState.id == strategy_id)
        )
        strategy_state = result.scalar_one_or_none()
        
        if not strategy_state:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return strategy_state.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/strategies/{strategy_id}/parameters")
async def update_strategy_parameters(
    strategy_id: int,
    parameters: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update strategy parameters"""
    try:
        result = await db.execute(
            select(StrategyState).where(StrategyState.id == strategy_id)
        )
        strategy_state = result.scalar_one_or_none()
        
        if not strategy_state:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        strategy_state.parameters.update(parameters)
        await db.commit()
        
        log.info(f"Updated parameters for strategy {strategy_id}")
        
        return {
            "message": "Parameters updated successfully",
            "parameters": strategy_state.parameters
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error updating strategy parameters: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

