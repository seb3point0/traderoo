"""
Trading bot control endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.utils.logger import log

router = APIRouter()

# Global bot state
bot_state = {
    "running": False,
    "active_strategies": [],
    "start_time": None
}


class BotStartRequest(BaseModel):
    """Request to start the bot"""
    exchange: str = "binance"
    symbols: list[str] = ["BTC/USDT"]
    strategies: list[str] = ["MACrossoverStrategy"]
    initial_balance: float = 10000.0


class BotStatusResponse(BaseModel):
    """Bot status response"""
    running: bool
    paper_trading: bool
    active_strategies: list[str]
    start_time: Optional[str]
    uptime_seconds: Optional[float]


@router.post("/bot/start")
async def start_bot(
    request: BotStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start the trading bot"""
    if bot_state["running"]:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        from datetime import datetime
        
        bot_state["running"] = True
        bot_state["active_strategies"] = request.strategies
        bot_state["start_time"] = datetime.utcnow().isoformat()
        
        log.info(f"Bot started with strategies: {request.strategies}")
        
        return {
            "message": "Trading bot started successfully",
            "exchange": request.exchange,
            "symbols": request.symbols,
            "strategies": request.strategies,
            "initial_balance": request.initial_balance
        }
        
    except Exception as e:
        log.error(f"Error starting bot: {e}")
        bot_state["running"] = False
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    if not bot_state["running"]:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    try:
        bot_state["running"] = False
        bot_state["active_strategies"] = []
        
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
    from datetime import datetime
    from app.config import get_settings
    
    settings = get_settings()
    
    uptime = None
    if bot_state["start_time"]:
        start = datetime.fromisoformat(bot_state["start_time"])
        uptime = (datetime.utcnow() - start).total_seconds()
    
    return BotStatusResponse(
        running=bot_state["running"],
        paper_trading=settings.paper_trading,
        active_strategies=bot_state["active_strategies"],
        start_time=bot_state["start_time"],
        uptime_seconds=uptime
    )


@router.post("/bot/restart")
async def restart_bot():
    """Restart the trading bot"""
    try:
        if bot_state["running"]:
            await stop_bot()
        
        # Wait a moment
        import asyncio
        await asyncio.sleep(1)
        
        # TODO: Restart with previous configuration
        
        return {"message": "Bot restart initiated"}
        
    except Exception as e:
        log.error(f"Error restarting bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

