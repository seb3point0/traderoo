"""
Trading bot control endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.database import get_db
from app.utils.logger import log
from app.core.trading_bot import get_bot

# Import strategy classes
from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.grid_trading import GridTradingStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.macd_bb import MACDBBStrategy

router = APIRouter()

# Strategy registry
STRATEGY_REGISTRY = {
    "MACrossoverStrategy": MACrossoverStrategy,
    "RSIStrategy": RSIStrategy,
    "GridTradingStrategy": GridTradingStrategy,
    "MomentumStrategy": MomentumStrategy,
    "MACDBBStrategy": MACDBBStrategy,
}


class BotStartRequest(BaseModel):
    """Request to start the bot"""
    exchange: str = "binance"
    initial_balance: float = 10000.0


class StrategyAddRequest(BaseModel):
    """Request to add a strategy"""
    strategy_name: str
    symbol: str
    timeframe: str = "1h"
    params: Optional[Dict[str, Any]] = None


class BotStatusResponse(BaseModel):
    """Bot status response"""
    running: bool
    paused: bool
    paper_trading: bool
    exchange: str
    active_strategies: int
    strategies: List[Dict[str, Any]]


@router.post("/bot/start")
async def start_bot(
    request: BotStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start the trading bot"""
    bot = get_bot()
    
    if bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        # Initialize bot with exchange
        await bot.initialize(
            exchange_name=request.exchange,
            initial_balance=request.initial_balance
        )
        
        # Start bot
        await bot.start()
        
        log.info(f"Bot started on {request.exchange} with ${request.initial_balance}")
        
        return {
            "message": "Trading bot started successfully",
            "exchange": request.exchange,
            "initial_balance": request.initial_balance,
            "status": bot.get_status()
        }
        
    except Exception as e:
        log.error(f"Error starting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    bot = get_bot()
    
    if not bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    try:
        await bot.stop()
        
        log.info("Bot stopped")
        
        return {
            "message": "Trading bot stopped successfully"
        }
        
    except Exception as e:
        log.error(f"Error stopping bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot/status", response_model=BotStatusResponse)
async def get_bot_status():
    """Get bot status"""
    from app.config import get_settings
    
    bot = get_bot()
    settings = get_settings()
    status = bot.get_status()
    
    return BotStatusResponse(
        running=status["is_running"],
        paused=status["is_paused"],
        paper_trading=settings.paper_trading,
        exchange=status["exchange"],
        active_strategies=status["active_strategies"],
        strategies=status["strategies"]
    )


@router.post("/bot/pause")
async def pause_bot():
    """Pause the trading bot"""
    bot = get_bot()
    
    if not bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    if bot.is_paused:
        raise HTTPException(status_code=400, detail="Bot is already paused")
    
    try:
        bot.pause()
        return {"message": "Trading bot paused"}
    except Exception as e:
        log.error(f"Error pausing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/resume")
async def resume_bot():
    """Resume the trading bot"""
    bot = get_bot()
    
    if not bot.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    if not bot.is_paused:
        raise HTTPException(status_code=400, detail="Bot is not paused")
    
    try:
        bot.resume()
        return {"message": "Trading bot resumed"}
    except Exception as e:
        log.error(f"Error resuming bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/strategy/add")
async def add_strategy(request: StrategyAddRequest):
    """Add a strategy to the bot"""
    bot = get_bot()
    
    if not bot.is_running:
        raise HTTPException(status_code=400, detail="Bot must be running to add strategies")
    
    if request.strategy_name not in STRATEGY_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown strategy: {request.strategy_name}. Available: {list(STRATEGY_REGISTRY.keys())}"
        )
    
    try:
        # Create strategy instance
        strategy_class = STRATEGY_REGISTRY[request.strategy_name]
        
        if request.params:
            strategy = strategy_class(
                symbol=request.symbol,
                timeframe=request.timeframe,
                **request.params
            )
        else:
            strategy = strategy_class(
                symbol=request.symbol,
                timeframe=request.timeframe
            )
        
        # Add to bot
        bot.add_strategy(strategy)
        
        return {
            "message": f"Strategy {request.strategy_name} added for {request.symbol}",
            "strategy": {
                "name": strategy.name,
                "symbol": strategy.symbol,
                "timeframe": strategy.timeframe
            }
        }
        
    except Exception as e:
        log.error(f"Error adding strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/bot/strategy/remove/{strategy_name}/{symbol}")
async def remove_strategy(strategy_name: str, symbol: str):
    """Remove a strategy from the bot"""
    bot = get_bot()
    
    try:
        bot.remove_strategy(strategy_name, symbol)
        
        return {
            "message": f"Strategy {strategy_name} removed for {symbol}"
        }
        
    except Exception as e:
        log.error(f"Error removing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot/strategies/available")
async def get_available_strategies():
    """Get list of available strategies"""
    return {
        "strategies": [
            {
                "name": name,
                "class": cls.__name__,
                "description": cls.__doc__.strip() if cls.__doc__ else ""
            }
            for name, cls in STRATEGY_REGISTRY.items()
        ]
    }


@router.get("/bot/health")
async def get_bot_health():
    """Get bot health status with error tracking"""
    bot = get_bot()
    return bot.get_health()


@router.post("/bot/reset-errors")
async def reset_bot_errors():
    """Reset error tracking and circuit breaker"""
    bot = get_bot()
    
    try:
        bot.reset_errors()
        return {
            "message": "Error tracking reset successfully"
        }
    except Exception as e:
        log.error(f"Error resetting errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

