"""
Input validation utilities
"""
from typing import Optional
from pydantic import BaseModel, Field, validator


class OrderRequest(BaseModel):
    """Order request validation"""
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Order side: buy or sell")
    order_type: str = Field(..., description="Order type: market or limit")
    amount: float = Field(..., gt=0, description="Order amount")
    price: Optional[float] = Field(None, gt=0, description="Limit price")
    
    @validator('side')
    def validate_side(cls, v):
        if v.lower() not in ['buy', 'sell']:
            raise ValueError('Side must be buy or sell')
        return v.lower()
    
    @validator('order_type')
    def validate_order_type(cls, v):
        if v.lower() not in ['market', 'limit']:
            raise ValueError('Order type must be market or limit')
        return v.lower()


class StrategyConfig(BaseModel):
    """Strategy configuration validation"""
    name: str = Field(..., description="Strategy name")
    symbol: str = Field(..., description="Trading pair")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    params: dict = Field(default_factory=dict, description="Strategy parameters")
    
    @validator('timeframe')
    def validate_timeframe(cls, v):
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        if v not in valid_timeframes:
            raise ValueError(f'Timeframe must be one of {valid_timeframes}')
        return v


class PositionSize(BaseModel):
    """Position sizing validation"""
    method: str = Field(..., description="Sizing method: fixed, percentage, kelly")
    value: float = Field(..., gt=0, description="Position size value")
    
    @validator('method')
    def validate_method(cls, v):
        valid_methods = ['fixed', 'percentage', 'kelly']
        if v.lower() not in valid_methods:
            raise ValueError(f'Method must be one of {valid_methods}')
        return v.lower()


def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format"""
    if '/' not in symbol:
        return False
    base, quote = symbol.split('/')
    return len(base) > 0 and len(quote) > 0


def validate_exchange(exchange: str) -> bool:
    """Validate exchange name"""
    supported_exchanges = ['binance', 'bybit', 'coinbase', 'kraken', 'okx']
    return exchange.lower() in supported_exchanges

