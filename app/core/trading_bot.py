"""
Trading Bot Orchestrator - Main autonomous trading system
"""
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exchange_manager import ExchangeManager, ExchangeFactory
from app.core.portfolio_manager import PortfolioManager
from app.core.order_executor import OrderExecutor
from app.core.event_bus import get_event_bus, EventType
from app.core.error_recovery import CircuitBreaker, RetryPolicy, ErrorTracker, RateLimiter
from app.data.market_data import MarketDataManager
from app.strategies.base import BaseStrategy, Signal
from app.models.database import AsyncSessionLocal
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class TradingBot:
    """
    Main trading bot orchestrator that runs strategies autonomously
    """
    
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.exchange: Optional[ExchangeManager] = None
        self.market_data: Optional[MarketDataManager] = None
        self.portfolio: Optional[PortfolioManager] = None
        self.executor: Optional[OrderExecutor] = None
        self.event_bus = get_event_bus()
        
        # Active strategies
        self.strategies: Dict[str, BaseStrategy] = {}
        
        # Task management
        self.tasks: Set[asyncio.Task] = set()
        
        # Configuration
        self.exchange_name = "binance"
        self.update_interval = 60  # seconds
        self.position_check_interval = 10  # seconds
        
        # Error recovery
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )
        self.retry_policy = RetryPolicy(
            max_attempts=3,
            initial_delay=1.0
        )
        self.error_tracker = ErrorTracker(window_size=3600)
        self.rate_limiter = RateLimiter(max_calls=100, time_window=60)
        
        # Health tracking
        self.last_successful_update = datetime.utcnow()
        self.consecutive_errors = 0
        
        log.info("TradingBot orchestrator initialized")
    
    async def initialize(
        self,
        exchange_name: str = "binance",
        initial_balance: float = 10000.0
    ):
        """Initialize bot with exchange and portfolio"""
        try:
            self.exchange_name = exchange_name
            
            # Initialize exchange
            self.exchange = await ExchangeFactory.get_exchange(exchange_name)
            log.info(f"Connected to {exchange_name} exchange")
            
            # Initialize market data manager
            self.market_data = MarketDataManager(self.exchange)
            
            # Initialize portfolio and executor with database session
            async with AsyncSessionLocal() as db:
                self.portfolio = PortfolioManager(db)
                await self.portfolio.initialize(initial_balance)
                
                self.executor = OrderExecutor(self.exchange, self.portfolio, db)
            
            log.info(f"Bot initialized with ${initial_balance} balance")
            
        except Exception as e:
            log.error(f"Failed to initialize bot: {e}")
            raise
    
    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the bot"""
        key = f"{strategy.name}:{strategy.symbol}"
        self.strategies[key] = strategy
        strategy.is_active = True
        log.info(f"Added strategy: {strategy.name} for {strategy.symbol}")
    
    def remove_strategy(self, strategy_name: str, symbol: str):
        """Remove a strategy from the bot"""
        key = f"{strategy_name}:{symbol}"
        if key in self.strategies:
            self.strategies[key].is_active = False
            del self.strategies[key]
            log.info(f"Removed strategy: {strategy_name} for {symbol}")
    
    async def start(self):
        """Start the trading bot"""
        if self.is_running:
            log.warning("Bot is already running")
            return
        
        if not self.exchange or not self.portfolio:
            raise RuntimeError("Bot not initialized. Call initialize() first")
        
        self.is_running = True
        self.is_paused = False
        
        # Start background tasks
        self.tasks.add(asyncio.create_task(self._strategy_execution_loop()))
        self.tasks.add(asyncio.create_task(self._position_monitoring_loop()))
        self.tasks.add(asyncio.create_task(self._portfolio_update_loop()))
        
        await self.event_bus.emit(
            EventType.BOT_STARTED,
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        log.info("Trading bot started successfully")
    
    async def stop(self):
        """Stop the trading bot"""
        if not self.is_running:
            log.warning("Bot is not running")
            return
        
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        await self.event_bus.emit(
            EventType.BOT_STOPPED,
            {"timestamp": datetime.utcnow().isoformat()}
        )
        
        log.info("Trading bot stopped")
    
    def pause(self):
        """Pause the trading bot (stops new trades but keeps monitoring)"""
        self.is_paused = True
        log.info("Trading bot paused")
    
    def resume(self):
        """Resume the trading bot"""
        self.is_paused = False
        log.info("Trading bot resumed")
    
    async def _strategy_execution_loop(self):
        """Main loop that executes strategies"""
        log.info("Strategy execution loop started")
        
        while self.is_running:
            try:
                if not self.is_paused and self.strategies:
                    await self._run_strategies()
                
                # Wait for next interval
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                log.info("Strategy execution loop cancelled")
                break
            except Exception as e:
                log.error(f"Error in strategy execution loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    async def _run_strategies(self):
        """Run all active strategies"""
        for key, strategy in list(self.strategies.items()):
            try:
                if not strategy.is_active:
                    continue
                
                # Rate limit API calls
                await self.rate_limiter.acquire()
                
                # Fetch market data with retry
                df = await self.retry_policy.execute(
                    self.market_data.get_ohlcv_df,
                    symbol=strategy.symbol,
                    timeframe=strategy.timeframe,
                    limit=200,
                    with_indicators=True
                )
                
                if df.empty:
                    log.warning(f"No data available for {strategy.symbol}")
                    continue
                
                # Generate signal
                signal = await strategy.analyze(df)
                
                # Validate signal
                if not strategy.validate_signal(signal, df):
                    continue
                
                # Execute trade based on signal
                await self._execute_signal(strategy, signal, df)
                
                # Update strategy state
                strategy.update_signal(signal)
                
                # Mark successful update
                self.last_successful_update = datetime.utcnow()
                self.consecutive_errors = 0
                
            except Exception as e:
                self.consecutive_errors += 1
                self.error_tracker.record_error("strategy_execution", str(e))
                log.error(f"Error running strategy {key}: {e}")
                
                # Check if we should stop due to too many errors
                if self.consecutive_errors >= 10:
                    log.critical("Too many consecutive errors, pausing bot")
                    self.pause()
                    await self.event_bus.emit(
                        EventType.ERROR,
                        {
                            "message": "Bot paused due to consecutive errors",
                            "consecutive_errors": self.consecutive_errors
                        }
                    )
    
    async def _execute_signal(self, strategy: BaseStrategy, signal: Signal, df):
        """Execute a trading signal"""
        try:
            async with AsyncSessionLocal() as db:
                # Reinitialize portfolio and executor with new session
                portfolio = PortfolioManager(db)
                await portfolio.initialize(self.portfolio.current_balance)
                executor = OrderExecutor(self.exchange, portfolio, db)
                
                # Check if we have an open position
                position = await portfolio.get_position(
                    self.exchange_name,
                    strategy.symbol
                )
                
                if signal == Signal.BUY and not position:
                    await self._execute_buy(strategy, df, executor, portfolio)
                    
                elif signal == Signal.SELL and position:
                    await self._execute_sell(strategy, position, executor)
                    
        except Exception as e:
            log.error(f"Error executing signal: {e}")
    
    async def _execute_buy(
        self,
        strategy: BaseStrategy,
        df,
        executor: OrderExecutor,
        portfolio: PortfolioManager
    ):
        """Execute a buy order"""
        try:
            entry_price = strategy.get_entry_price(df)
            if not entry_price:
                return
            
            # Calculate position size
            position_size = portfolio.calculate_position_size(
                entry_price=entry_price,
                stop_loss=strategy.get_stop_loss(entry_price, 'long')
            )
            
            # Check if we can open position
            position_value = position_size * entry_price
            can_open, reason = portfolio.can_open_position(position_value)
            
            if not can_open:
                log.warning(f"Cannot open position: {reason}")
                await self.event_bus.emit(
                    EventType.RISK_LIMIT_HIT,
                    {"reason": reason, "symbol": strategy.symbol}
                )
                return
            
            # Calculate stop loss and take profit
            stop_loss = strategy.get_stop_loss(entry_price, 'long')
            take_profit = strategy.get_take_profit(entry_price, 'long')
            
            # Execute buy order
            trade = await executor.execute_market_buy(
                symbol=strategy.symbol,
                amount=position_size,
                strategy_name=strategy.name,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            if trade:
                log.info(f"BUY executed: {position_size} {strategy.symbol} @ ${entry_price:.2f}")
                await self.event_bus.emit(
                    EventType.SIGNAL_BUY,
                    {
                        "strategy": strategy.name,
                        "symbol": strategy.symbol,
                        "price": entry_price,
                        "amount": position_size
                    }
                )
                
        except Exception as e:
            log.error(f"Error executing buy: {e}")
    
    async def _execute_sell(
        self,
        strategy: BaseStrategy,
        position,
        executor: OrderExecutor
    ):
        """Execute a sell order"""
        try:
            trade = await executor.close_position(position, reason="strategy_signal")
            
            if trade:
                log.info(f"SELL executed: {position.amount} {strategy.symbol} | P&L: ${trade.realized_pnl:.2f}")
                await self.event_bus.emit(
                    EventType.SIGNAL_SELL,
                    {
                        "strategy": strategy.name,
                        "symbol": strategy.symbol,
                        "pnl": trade.realized_pnl
                    }
                )
                
        except Exception as e:
            log.error(f"Error executing sell: {e}")
    
    async def _position_monitoring_loop(self):
        """Monitor open positions for stop-loss/take-profit"""
        log.info("Position monitoring loop started")
        
        while self.is_running:
            try:
                await self._check_positions()
                await asyncio.sleep(self.position_check_interval)
                
            except asyncio.CancelledError:
                log.info("Position monitoring loop cancelled")
                break
            except Exception as e:
                log.error(f"Error in position monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _check_positions(self):
        """Check all open positions for exit conditions"""
        try:
            async with AsyncSessionLocal() as db:
                portfolio = PortfolioManager(db)
                await portfolio.load_open_positions()
                
                positions = await portfolio.get_all_positions()
                
                if not positions:
                    return
                
                # Get current prices
                symbols = list(set(p.symbol for p in positions))
                prices = await self.market_data.get_multiple_prices(symbols)
                
                # Update position prices
                await portfolio.update_position_prices(prices)
                
                # Check each position for exit conditions
                executor = OrderExecutor(self.exchange, portfolio, db)
                
                for position in positions:
                    if position.symbol not in prices:
                        continue
                    
                    current_price = prices[position.symbol]
                    should_close, reason = position.should_close()
                    
                    if should_close:
                        log.info(f"Closing position {position.symbol}: {reason}")
                        await executor.close_position(position, reason=reason)
                        
        except Exception as e:
            log.error(f"Error checking positions: {e}")
    
    async def _portfolio_update_loop(self):
        """Periodically update portfolio statistics"""
        log.info("Portfolio update loop started")
        
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Update every 5 minutes
                
                async with AsyncSessionLocal() as db:
                    portfolio = PortfolioManager(db)
                    await portfolio.load_open_positions()
                    
                    stats = await portfolio.get_portfolio_stats()
                    
                    log.info(
                        f"Portfolio: ${stats['current_balance']:.2f} | "
                        f"P&L: ${stats['total_pnl']:.2f} ({stats['total_return_pct']:.2f}%) | "
                        f"Positions: {stats['open_positions']}"
                    )
                    
            except asyncio.CancelledError:
                log.info("Portfolio update loop cancelled")
                break
            except Exception as e:
                log.error(f"Error in portfolio update: {e}")
    
    def get_status(self) -> Dict:
        """Get bot status"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "exchange": self.exchange_name,
            "active_strategies": len(self.strategies),
            "strategies": [
                {
                    "name": strategy.name,
                    "symbol": strategy.symbol,
                    "timeframe": strategy.timeframe,
                    "is_active": strategy.is_active
                }
                for strategy in self.strategies.values()
            ]
        }
    
    def get_health(self) -> Dict:
        """Get bot health status"""
        now = datetime.utcnow()
        time_since_update = (now - self.last_successful_update).total_seconds()
        
        # Determine health status
        if not self.is_running:
            status = "stopped"
        elif self.is_paused:
            status = "paused"
        elif self.consecutive_errors >= 5:
            status = "degraded"
        elif time_since_update > 300:  # 5 minutes
            status = "unhealthy"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "last_successful_update": self.last_successful_update.isoformat(),
            "time_since_update_seconds": time_since_update,
            "consecutive_errors": self.consecutive_errors,
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "error_counts": self.error_tracker.get_all_errors()
        }
    
    def reset_errors(self):
        """Reset error tracking and circuit breaker"""
        self.consecutive_errors = 0
        self.error_tracker.clear()
        self.circuit_breaker.reset()
        log.info("Error tracking reset")


# Global bot instance
_bot_instance: Optional[TradingBot] = None


def get_bot() -> TradingBot:
    """Get global bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = TradingBot()
    return _bot_instance

