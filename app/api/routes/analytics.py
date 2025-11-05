"""
Analytics and performance metrics endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.models.database import get_db
from app.models.trade import Trade
from app.models.position import Position
from app.models.strategy_state import StrategyState
from app.utils.logger import log

router = APIRouter()


class PerformanceMetrics(BaseModel):
    """Performance metrics response"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_fees: float
    average_win: float
    average_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float


@router.get("/performance")
async def get_performance_metrics(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get overall performance metrics"""
    try:
        # Get trades from last N days
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(Trade).where(
                Trade.created_at >= since,
                Trade.status == "closed"
            )
        )
        trades = result.scalars().all()
        
        if not trades:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                total_fees=0.0,
                average_win=0.0,
                average_loss=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                max_drawdown_pct=0.0
            )
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.realized_pnl > 0)
        losing_trades = sum(1 for t in trades if t.realized_pnl < 0)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        total_pnl = sum(t.realized_pnl for t in trades)
        total_fees = sum(t.fee for t in trades if t.fee)
        
        wins = [t.realized_pnl for t in trades if t.realized_pnl > 0]
        losses = [t.realized_pnl for t in trades if t.realized_pnl < 0]
        
        average_win = sum(wins) / len(wins) if wins else 0.0
        average_loss = sum(losses) / len(losses) if losses else 0.0
        
        # Profit factor
        total_wins = sum(wins)
        total_losses = abs(sum(losses))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        # Simplified Sharpe ratio (annualized)
        if trades:
            returns = [t.realized_pnl for t in trades]
            import numpy as np
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (mean_return / std_return * np.sqrt(252)) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        # Max drawdown (simplified)
        cumulative_pnl = 0
        peak = 0
        max_dd = 0
        
        for trade in trades:
            cumulative_pnl += trade.realized_pnl
            if cumulative_pnl > peak:
                peak = cumulative_pnl
            drawdown = peak - cumulative_pnl
            if drawdown > max_dd:
                max_dd = drawdown
        
        max_dd_pct = (max_dd / peak * 100) if peak > 0 else 0.0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            total_pnl=round(total_pnl, 2),
            total_fees=round(total_fees, 2),
            average_win=round(average_win, 2),
            average_loss=round(average_loss, 2),
            profit_factor=round(profit_factor, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            max_drawdown=round(max_dd, 2),
            max_drawdown_pct=round(max_dd_pct, 2)
        )
        
    except Exception as e:
        log.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/strategy/{strategy_name}")
async def get_strategy_performance(
    strategy_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get performance metrics for a specific strategy"""
    try:
        result = await db.execute(
            select(StrategyState).where(
                StrategyState.strategy_name == strategy_name
            )
        )
        strategy_states = result.scalars().all()
        
        if not strategy_states:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        # Aggregate metrics across all instances of this strategy
        total_trades = sum(s.total_trades for s in strategy_states)
        winning_trades = sum(s.winning_trades for s in strategy_states)
        losing_trades = sum(s.losing_trades for s in strategy_states)
        total_pnl = sum(s.total_pnl for s in strategy_states)
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        return {
            "strategy_name": strategy_name,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "instances": len(strategy_states)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/daily-pnl")
async def get_daily_pnl(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get daily P&L over time"""
    try:
        since = datetime.utcnow() - timedelta(days=days)
        
        result = await db.execute(
            select(Trade).where(
                Trade.closed_at >= since,
                Trade.status == "closed"
            ).order_by(Trade.closed_at)
        )
        trades = result.scalars().all()
        
        # Group by day
        daily_pnl: Dict[str, float] = {}
        
        for trade in trades:
            if trade.closed_at:
                day = trade.closed_at.date().isoformat()
                daily_pnl[day] = daily_pnl.get(day, 0) + trade.realized_pnl
        
        # Convert to list format
        pnl_data = [
            {"date": date, "pnl": round(pnl, 2)}
            for date, pnl in sorted(daily_pnl.items())
        ]
        
        return {
            "data": pnl_data,
            "period_days": days
        }
        
    except Exception as e:
        log.error(f"Error fetching daily P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/symbols")
async def get_symbol_performance(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get performance by symbol"""
    try:
        result = await db.execute(
            select(Trade).where(Trade.status == "closed")
        )
        trades = result.scalars().all()
        
        # Group by symbol
        symbol_stats: Dict[str, Dict] = {}
        
        for trade in trades:
            if trade.symbol not in symbol_stats:
                symbol_stats[trade.symbol] = {
                    "symbol": trade.symbol,
                    "trades": 0,
                    "pnl": 0.0,
                    "wins": 0
                }
            
            stats = symbol_stats[trade.symbol]
            stats["trades"] += 1
            stats["pnl"] += trade.realized_pnl
            if trade.realized_pnl > 0:
                stats["wins"] += 1
        
        # Calculate win rates and sort by P&L
        for symbol, stats in symbol_stats.items():
            stats["win_rate"] = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0.0
            stats["pnl"] = round(stats["pnl"], 2)
            stats["win_rate"] = round(stats["win_rate"], 2)
        
        sorted_symbols = sorted(
            symbol_stats.values(),
            key=lambda x: x["pnl"],
            reverse=True
        )[:limit]
        
        return {
            "symbols": sorted_symbols,
            "count": len(sorted_symbols)
        }
        
    except Exception as e:
        log.error(f"Error fetching symbol performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

