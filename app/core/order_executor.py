"""
Order execution with paper trading and live trading modes
"""
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exchange_manager import ExchangeManager
from app.models.trade import Trade
from app.models.position import Position
from app.core.portfolio_manager import PortfolioManager
from app.core.event_bus import EventType, get_event_bus
from app.utils.logger import log
from app.config import get_settings

settings = get_settings()


class OrderExecutor:
    """Handles order execution in paper or live trading mode"""
    
    def __init__(
        self,
        exchange: ExchangeManager,
        portfolio_manager: PortfolioManager,
        db: AsyncSession
    ):
        self.exchange = exchange
        self.portfolio = portfolio_manager
        self.db = db
        self.event_bus = get_event_bus()
        self.paper_trading = settings.paper_trading
        
        log.info(f"OrderExecutor initialized in {'PAPER' if self.paper_trading else 'LIVE'} trading mode")
    
    async def execute_market_buy(
        self,
        symbol: str,
        amount: float,
        strategy_name: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Optional[Trade]:
        """Execute a market buy order"""
        try:
            if self.paper_trading:
                return await self._paper_market_buy(
                    symbol, amount, strategy_name, stop_loss, take_profit
                )
            else:
                return await self._live_market_buy(
                    symbol, amount, strategy_name, stop_loss, take_profit
                )
        except Exception as e:
            log.error(f"Error executing market buy: {e}")
            await self.event_bus.emit(
                EventType.ORDER_FAILED,
                {'symbol': symbol, 'side': 'buy', 'error': str(e)}
            )
            return None
    
    async def execute_market_sell(
        self,
        symbol: str,
        amount: float,
        strategy_name: str
    ) -> Optional[Trade]:
        """Execute a market sell order"""
        try:
            if self.paper_trading:
                return await self._paper_market_sell(symbol, amount, strategy_name)
            else:
                return await self._live_market_sell(symbol, amount, strategy_name)
        except Exception as e:
            log.error(f"Error executing market sell: {e}")
            await self.event_bus.emit(
                EventType.ORDER_FAILED,
                {'symbol': symbol, 'side': 'sell', 'error': str(e)}
            )
            return None
    
    async def _paper_market_buy(
        self,
        symbol: str,
        amount: float,
        strategy_name: str,
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> Trade:
        """Execute paper trading buy order"""
        # Get current market price
        ticker = await self.exchange.fetch_ticker(symbol)
        price = ticker.get('last') or ticker.get('close')
        
        if not price:
            raise ValueError(f"Could not get price for {symbol}")
        
        # Calculate cost
        cost = amount * price
        fee = cost * 0.001  # 0.1% fee
        
        # Create trade record
        trade = Trade(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            order_id=f"paper_{datetime.utcnow().timestamp()}",
            side='buy',
            order_type='market',
            amount=amount,
            price=price,
            cost=cost,
            fee=fee,
            fee_currency=symbol.split('/')[1],
            position_side='long',
            strategy_name=strategy_name,
            status='open',
            is_paper_trade=True,
            executed_at=datetime.utcnow()
        )
        
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        # Open position
        await self.portfolio.open_position(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            side='long',
            amount=amount,
            entry_price=price,
            strategy_name=strategy_name,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trade_id=trade.id
        )
        
        log.info(f"PAPER: Bought {amount} {symbol} @ ${price:.2f} | Cost: ${cost:.2f}")
        
        await self.event_bus.emit(
            EventType.ORDER_FILLED,
            {'trade_id': trade.id, 'symbol': symbol, 'side': 'buy', 'price': price}
        )
        
        return trade
    
    async def _paper_market_sell(
        self,
        symbol: str,
        amount: float,
        strategy_name: str
    ) -> Trade:
        """Execute paper trading sell order"""
        # Get current market price
        ticker = await self.exchange.fetch_ticker(symbol)
        price = ticker.get('last') or ticker.get('close')
        
        if not price:
            raise ValueError(f"Could not get price for {symbol}")
        
        # Calculate proceeds
        cost = amount * price
        fee = cost * 0.001  # 0.1% fee
        
        # Create trade record
        trade = Trade(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            order_id=f"paper_{datetime.utcnow().timestamp()}",
            side='sell',
            order_type='market',
            amount=amount,
            price=price,
            cost=cost,
            fee=fee,
            fee_currency=symbol.split('/')[1],
            position_side='short',
            strategy_name=strategy_name,
            status='closed',
            is_paper_trade=True,
            executed_at=datetime.utcnow(),
            closed_at=datetime.utcnow()
        )
        
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        # Check if closing a position
        position = await self.portfolio.get_position(self.exchange.exchange_name, symbol)
        if position:
            realized_pnl = await self.portfolio.close_position(position, price, trade.id)
            trade.realized_pnl = realized_pnl
            await self.db.commit()
            
            log.info(f"PAPER: Sold {amount} {symbol} @ ${price:.2f} | P&L: ${realized_pnl:.2f}")
        else:
            log.info(f"PAPER: Sold {amount} {symbol} @ ${price:.2f}")
        
        await self.event_bus.emit(
            EventType.ORDER_FILLED,
            {'trade_id': trade.id, 'symbol': symbol, 'side': 'sell', 'price': price}
        )
        
        return trade
    
    async def _live_market_buy(
        self,
        symbol: str,
        amount: float,
        strategy_name: str,
        stop_loss: Optional[float],
        take_profit: Optional[float]
    ) -> Trade:
        """Execute live market buy order"""
        log.warning(f"LIVE TRADING: Executing real market buy for {amount} {symbol}")
        
        # Execute order on exchange
        order = await self.exchange.create_market_order(symbol, 'buy', amount)
        
        # Parse order response
        price = order.get('average') or order.get('price')
        filled_amount = order.get('filled', amount)
        cost = order.get('cost', filled_amount * price)
        fee = order.get('fee', {}).get('cost', 0)
        
        # Create trade record
        trade = Trade(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            order_id=order['id'],
            side='buy',
            order_type='market',
            amount=filled_amount,
            price=price,
            cost=cost,
            fee=fee,
            fee_currency=order.get('fee', {}).get('currency', symbol.split('/')[1]),
            position_side='long',
            strategy_name=strategy_name,
            status='open',
            is_paper_trade=False,
            executed_at=datetime.utcnow()
        )
        
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        # Open position
        await self.portfolio.open_position(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            side='long',
            amount=filled_amount,
            entry_price=price,
            strategy_name=strategy_name,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trade_id=trade.id
        )
        
        # Place stop loss and take profit orders if specified
        if stop_loss:
            try:
                await self.exchange.create_stop_loss_order(symbol, 'sell', filled_amount, stop_loss)
                log.info(f"Placed stop loss at ${stop_loss:.2f}")
            except Exception as e:
                log.warning(f"Could not place stop loss: {e}")
        
        log.info(f"LIVE: Bought {filled_amount} {symbol} @ ${price:.2f} | Cost: ${cost:.2f}")
        
        await self.event_bus.emit(
            EventType.ORDER_FILLED,
            {'trade_id': trade.id, 'symbol': symbol, 'side': 'buy', 'price': price}
        )
        
        return trade
    
    async def _live_market_sell(
        self,
        symbol: str,
        amount: float,
        strategy_name: str
    ) -> Trade:
        """Execute live market sell order"""
        log.warning(f"LIVE TRADING: Executing real market sell for {amount} {symbol}")
        
        # Execute order on exchange
        order = await self.exchange.create_market_order(symbol, 'sell', amount)
        
        # Parse order response
        price = order.get('average') or order.get('price')
        filled_amount = order.get('filled', amount)
        cost = order.get('cost', filled_amount * price)
        fee = order.get('fee', {}).get('cost', 0)
        
        # Create trade record
        trade = Trade(
            exchange=self.exchange.exchange_name,
            symbol=symbol,
            order_id=order['id'],
            side='sell',
            order_type='market',
            amount=filled_amount,
            price=price,
            cost=cost,
            fee=fee,
            fee_currency=order.get('fee', {}).get('currency', symbol.split('/')[1]),
            position_side='short',
            strategy_name=strategy_name,
            status='closed',
            is_paper_trade=False,
            executed_at=datetime.utcnow(),
            closed_at=datetime.utcnow()
        )
        
        self.db.add(trade)
        await self.db.commit()
        await self.db.refresh(trade)
        
        # Check if closing a position
        position = await self.portfolio.get_position(self.exchange.exchange_name, symbol)
        if position:
            realized_pnl = await self.portfolio.close_position(position, price, trade.id)
            trade.realized_pnl = realized_pnl
            await self.db.commit()
            
            log.info(f"LIVE: Sold {filled_amount} {symbol} @ ${price:.2f} | P&L: ${realized_pnl:.2f}")
        else:
            log.info(f"LIVE: Sold {filled_amount} {symbol} @ ${price:.2f}")
        
        await self.event_bus.emit(
            EventType.ORDER_FILLED,
            {'trade_id': trade.id, 'symbol': symbol, 'side': 'sell', 'price': price}
        )
        
        return trade
    
    async def close_position(
        self,
        position: Position,
        reason: str = "manual"
    ) -> Optional[Trade]:
        """Close an open position"""
        try:
            log.info(f"Closing position: {position.symbol} ({reason})")
            
            # Execute sell order to close
            trade = await self.execute_market_sell(
                symbol=position.symbol,
                amount=position.amount,
                strategy_name=position.strategy_name
            )
            
            if trade:
                await self.event_bus.emit(
                    EventType.POSITION_CLOSED,
                    {
                        'position_id': position.id,
                        'symbol': position.symbol,
                        'pnl': trade.realized_pnl,
                        'reason': reason
                    }
                )
            
            return trade
            
        except Exception as e:
            log.error(f"Error closing position: {e}")
            return None

