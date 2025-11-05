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
    enable_ai_validation: bool = True  # Enable AI validation by default


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
    """Add a strategy to the bot with optional AI validation"""
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
        
        # Wrap with AI validator if enabled
        if request.enable_ai_validation:
            from app.strategies.ai_validator import AIValidatorStrategy
            strategy = AIValidatorStrategy(strategy)
            await strategy.initialize()
            
            log.info(f"AI validation ENABLED for {request.strategy_name}")
        else:
            log.info(f"AI validation DISABLED for {request.strategy_name}")
        
        # Add to bot
        bot.add_strategy(strategy)
        
        return {
            "message": f"Strategy {request.strategy_name} added for {request.symbol}",
            "strategy": {
                "name": strategy.name,
                "symbol": strategy.symbol,
                "timeframe": strategy.timeframe,
                "ai_enabled": request.enable_ai_validation
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


@router.get("/bot/ai-insights/{symbol}")
async def get_ai_insights(symbol: str):
    """Get AI market insights for a symbol"""
    try:
        from ai.ai_market_analyzer import AIMarketAnalyzer
        
        analyzer = AIMarketAnalyzer()
        await analyzer.initialize()
        
        # Get market overview
        overview = await analyzer.get_market_overview(symbol)
        
        await analyzer.close()
        
        if not overview:
            raise HTTPException(status_code=404, detail=f"No AI insights available for {symbol}")
        
        return overview
        
    except Exception as e:
        log.error(f"Error getting AI insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bot/ai-stats")
async def get_ai_stats():
    """Get AI validation statistics for all strategies"""
    bot = get_bot()
    
    try:
        from app.strategies.ai_validator import AIValidatorStrategy
        
        ai_stats = []
        
        for strategy in bot.strategies.values():
            if isinstance(strategy, AIValidatorStrategy):
                stats = strategy.get_ai_stats()
                ai_stats.append(stats)
        
        # Calculate totals
        total_approvals = sum(s['ai_approvals'] for s in ai_stats)
        total_rejections = sum(s['ai_rejections'] for s in ai_stats)
        total_validations = total_approvals + total_rejections
        
        overall_approval_rate = (
            (total_approvals / total_validations * 100) 
            if total_validations > 0 else 0
        )
        
        return {
            "ai_enabled_strategies": len(ai_stats),
            "total_approvals": total_approvals,
            "total_rejections": total_rejections,
            "overall_approval_rate": overall_approval_rate,
            "strategies": ai_stats
        }
        
    except Exception as e:
        log.error(f"Error getting AI stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/ai-cache/invalidate/{symbol}")
async def invalidate_ai_cache(symbol: str):
    """Invalidate AI cache for a symbol"""
    try:
        from app.core.cache_manager import get_cache_manager
        
        cache_manager = await get_cache_manager()
        await cache_manager.invalidate_symbol(symbol)
        
        return {
            "message": f"AI cache invalidated for {symbol}"
        }
        
    except Exception as e:
        log.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

