"""
Main FastAPI application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.utils.logger import log
from app.models.database import init_db
from app.core.event_bus import get_event_bus
from app.core.trading_bot import get_bot
from app.api.routes import trading, strategies, portfolio, analytics
from app.api import websocket

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    log.info("Starting Trading Bot API...")
    
    # Initialize database
    await init_db()
    log.info("Database initialized")
    
    # Start event bus
    event_bus = get_event_bus()
    await event_bus.start()
    log.info("Event bus started")
    
    # Initialize trading bot
    bot = get_bot()
    log.info("Trading bot instance created")
    
    yield
    
    # Shutdown
    log.info("Shutting down Trading Bot API...")
    
    # Stop bot if running
    bot = get_bot()
    if bot.is_running:
        await bot.stop()
        log.info("Trading bot stopped")
    
    # Stop event bus
    await event_bus.stop()
    log.info("Event bus stopped")


# Create FastAPI app
app = FastAPI(
    title="Algorithmic Trading Bot API",
    description="Professional algorithmic trading bot backend with AI integration",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://trading-frontend:3000",
        "*"  # Allow all for development - configure appropriately for production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(trading.router, prefix="/api/v1", tags=["Trading Bot"])
app.include_router(strategies.router, prefix="/api/v1", tags=["Strategies"])
app.include_router(portfolio.router, prefix="/api/v1", tags=["Portfolio"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(websocket.router, prefix="", tags=["WebSocket"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Algorithmic Trading Bot API",
        "version": "0.1.0",
        "status": "running",
        "paper_trading": settings.paper_trading
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

