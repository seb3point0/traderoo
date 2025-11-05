"""
Exchange manager using CCXT for unified exchange interface
"""
import ccxt.async_support as ccxt
from typing import Optional, Dict, List, Any
from datetime import datetime
from app.config import get_settings
from app.utils.logger import log

settings = get_settings()


class ExchangeManager:
    """Manages exchange connections and operations"""
    
    def __init__(self, exchange_name: str, api_key: str = "", api_secret: str = ""):
        self.exchange_name = exchange_name.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange: Optional[ccxt.Exchange] = None
        self.markets: Dict = {}
        
    async def initialize(self):
        """Initialize exchange connection"""
        try:
            # Get exchange class
            exchange_class = getattr(ccxt, self.exchange_name)
            
            # Configure exchange
            config = {
                'enableRateLimit': True,
                'asyncio_loop': None,
            }
            
            if self.api_key and self.api_secret:
                config['apiKey'] = self.api_key
                config['secret'] = self.api_secret
            
            self.exchange = exchange_class(config)
            
            # Load markets
            self.markets = await self.exchange.load_markets()
            
            log.info(f"Initialized {self.exchange_name} exchange with {len(self.markets)} markets")
            
        except Exception as e:
            log.error(f"Failed to initialize {self.exchange_name}: {e}")
            raise
    
    async def close(self):
        """Close exchange connection"""
        if self.exchange:
            await self.exchange.close()
            log.info(f"Closed {self.exchange_name} connection")
    
    # Market Data Methods
    
    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker data"""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            log.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: Optional[int] = None
    ) -> List[List]:
        """Fetch OHLCV (candlestick) data"""
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, since, limit)
            return ohlcv
        except Exception as e:
            log.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    async def fetch_orderbook(self, symbol: str, limit: int = 20) -> Dict:
        """Fetch order book data"""
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)
            return orderbook
        except Exception as e:
            log.error(f"Error fetching orderbook for {symbol}: {e}")
            raise
    
    async def fetch_trades(self, symbol: str, limit: int = 50) -> List[Dict]:
        """Fetch recent trades"""
        try:
            trades = await self.exchange.fetch_trades(symbol, limit=limit)
            return trades
        except Exception as e:
            log.error(f"Error fetching trades for {symbol}: {e}")
            raise
    
    # Account Methods
    
    async def fetch_balance(self) -> Dict:
        """Fetch account balance"""
        try:
            balance = await self.exchange.fetch_balance()
            return balance
        except Exception as e:
            log.error(f"Error fetching balance: {e}")
            raise
    
    async def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """Fetch open positions (for futures)"""
        try:
            if hasattr(self.exchange, 'fetch_positions'):
                positions = await self.exchange.fetch_positions(symbols)
                return positions
            return []
        except Exception as e:
            log.error(f"Error fetching positions: {e}")
            raise
    
    # Order Methods - Spot Trading
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """Create a market order"""
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params or {}
            )
            log.info(f"Created market order: {side} {amount} {symbol}")
            return order
        except Exception as e:
            log.error(f"Error creating market order: {e}")
            raise
    
    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """Create a limit order"""
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )
            log.info(f"Created limit order: {side} {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            log.error(f"Error creating limit order: {e}")
            raise
    
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """Create a stop loss order"""
        try:
            params = params or {}
            params['stopPrice'] = stop_price
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='stop_loss',
                side=side,
                amount=amount,
                params=params
            )
            log.info(f"Created stop loss order: {side} {amount} {symbol} @ {stop_price}")
            return order
        except Exception as e:
            log.error(f"Error creating stop loss order: {e}")
            raise
    
    # Order Methods - Futures Trading
    
    async def create_futures_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> Dict:
        """Create a futures market order"""
        try:
            # Set leverage
            if hasattr(self.exchange, 'set_leverage'):
                await self.exchange.set_leverage(leverage, symbol)
            
            params = {
                'reduceOnly': reduce_only
            }
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params
            )
            log.info(f"Created futures market order: {side} {amount} {symbol} (leverage: {leverage}x)")
            return order
        except Exception as e:
            log.error(f"Error creating futures market order: {e}")
            raise
    
    async def create_futures_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        leverage: int = 1,
        reduce_only: bool = False
    ) -> Dict:
        """Create a futures limit order"""
        try:
            # Set leverage
            if hasattr(self.exchange, 'set_leverage'):
                await self.exchange.set_leverage(leverage, symbol)
            
            params = {
                'reduceOnly': reduce_only
            }
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=price,
                params=params
            )
            log.info(f"Created futures limit order: {side} {amount} {symbol} @ {price} (leverage: {leverage}x)")
            return order
        except Exception as e:
            log.error(f"Error creating futures limit order: {e}")
            raise
    
    async def set_margin_mode(self, symbol: str, margin_mode: str = 'isolated'):
        """Set margin mode (isolated or cross)"""
        try:
            if hasattr(self.exchange, 'set_margin_mode'):
                await self.exchange.set_margin_mode(margin_mode, symbol)
                log.info(f"Set margin mode to {margin_mode} for {symbol}")
        except Exception as e:
            log.warning(f"Could not set margin mode: {e}")
    
    # Order Management
    
    async def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """Cancel an order"""
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            log.info(f"Cancelled order {order_id} for {symbol}")
            return result
        except Exception as e:
            log.error(f"Error cancelling order {order_id}: {e}")
            raise
    
    async def cancel_all_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Cancel all orders for a symbol"""
        try:
            if hasattr(self.exchange, 'cancel_all_orders'):
                result = await self.exchange.cancel_all_orders(symbol)
                log.info(f"Cancelled all orders for {symbol or 'all symbols'}")
                return result
            return []
        except Exception as e:
            log.error(f"Error cancelling all orders: {e}")
            raise
    
    async def fetch_order(self, order_id: str, symbol: str) -> Dict:
        """Fetch order status"""
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            log.error(f"Error fetching order {order_id}: {e}")
            raise
    
    async def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """Fetch open orders"""
        try:
            orders = await self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            log.error(f"Error fetching open orders: {e}")
            raise
    
    async def fetch_closed_orders(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Fetch closed orders"""
        try:
            if hasattr(self.exchange, 'fetch_closed_orders'):
                orders = await self.exchange.fetch_closed_orders(symbol, since, limit)
                return orders
            return []
        except Exception as e:
            log.error(f"Error fetching closed orders: {e}")
            raise
    
    # Utility Methods
    
    def get_market_info(self, symbol: str) -> Optional[Dict]:
        """Get market information"""
        return self.markets.get(symbol)
    
    def calculate_fee(self, amount: float, price: float, side: str) -> float:
        """Calculate trading fee"""
        if symbol_info := self.get_market_info(symbol):
            fee_rate = symbol_info.get('taker' if side == 'market' else 'maker', 0.001)
            return amount * price * fee_rate
        return amount * price * 0.001  # Default 0.1%
    
    def is_futures_market(self, symbol: str) -> bool:
        """Check if symbol is a futures market"""
        market_info = self.get_market_info(symbol)
        if market_info:
            return market_info.get('type') == 'future' or market_info.get('future', False)
        return False
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


class ExchangeFactory:
    """Factory for creating exchange managers"""
    
    _instances: Dict[str, ExchangeManager] = {}
    
    @classmethod
    async def get_exchange(cls, exchange_name: str) -> ExchangeManager:
        """Get or create exchange manager instance"""
        key = exchange_name.lower()
        
        if key not in cls._instances:
            # Get API credentials from settings
            api_key = ""
            api_secret = ""
            
            if key == 'binance':
                api_key = settings.binance_api_key
                api_secret = settings.binance_api_secret
            elif key == 'bybit':
                api_key = settings.bybit_api_key
                api_secret = settings.bybit_api_secret
            
            manager = ExchangeManager(exchange_name, api_key, api_secret)
            await manager.initialize()
            cls._instances[key] = manager
        
        return cls._instances[key]
    
    @classmethod
    async def close_all(cls):
        """Close all exchange connections"""
        for manager in cls._instances.values():
            await manager.close()
        cls._instances.clear()

