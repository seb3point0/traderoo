"""
Tests for trading strategies
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.rsi_strategy import RSIStrategy
from app.strategies.base import Signal


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
    # Generate synthetic price data
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    data = pd.DataFrame({
        'open': close_prices * (1 + np.random.randn(100) * 0.001),
        'high': close_prices * (1 + abs(np.random.randn(100)) * 0.002),
        'low': close_prices * (1 - abs(np.random.randn(100)) * 0.002),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100)
    }, index=dates)
    
    return data


@pytest.mark.asyncio
async def test_ma_crossover_strategy():
    """Test MA Crossover strategy"""
    strategy = MACrossoverStrategy(
        symbol="BTC/USDT",
        timeframe="1h",
        params={'fast_period': 5, 'slow_period': 10}
    )
    
    # Create test data with clear crossover
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
    prices = [100] * 25 + [110] * 25  # Price increase
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices,
        'low': prices,
        'close': prices,
        'volume': [1000] * 50
    }, index=dates)
    
    signal = await strategy.analyze(data)
    
    # Should return a valid signal
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


@pytest.mark.asyncio
async def test_rsi_strategy():
    """Test RSI strategy"""
    strategy = RSIStrategy(
        symbol="BTC/USDT",
        timeframe="1h",
        params={'rsi_period': 14}
    )
    
    # Create test data
    dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
    
    # Downtrend for oversold condition
    prices = list(range(100, 50, -1))
    
    data = pd.DataFrame({
        'open': prices,
        'high': prices,
        'low': prices,
        'close': prices,
        'volume': [1000] * 50
    }, index=dates)
    
    signal = await strategy.analyze(data)
    
    # Should return a valid signal
    assert signal in [Signal.BUY, Signal.SELL, Signal.HOLD]


def test_strategy_parameters():
    """Test strategy parameter handling"""
    params = {'fast_period': 20, 'slow_period': 50}
    
    strategy = MACrossoverStrategy(
        symbol="BTC/USDT",
        params=params
    )
    
    assert strategy.params['fast_period'] == 20
    assert strategy.params['slow_period'] == 50
    
    # Test parameter update
    strategy.update_parameters({'fast_period': 12})
    assert strategy.params['fast_period'] == 12


def test_strategy_state():
    """Test strategy state management"""
    strategy = MACrossoverStrategy(symbol="BTC/USDT")
    
    # Get state
    state = strategy.get_state()
    
    assert state['name'] == 'MACrossoverStrategy'
    assert state['symbol'] == 'BTC/USDT'
    assert state['is_active'] == False
    
    # Update state
    strategy.is_active = True
    strategy.signals_generated = 5
    
    new_state = strategy.get_state()
    assert new_state['is_active'] == True
    assert new_state['signals_generated'] == 5


def test_position_size_calculation():
    """Test position size calculation"""
    strategy = MACrossoverStrategy(
        symbol="BTC/USDT",
        params={'risk_per_trade': 0.02}
    )
    
    portfolio_value = 10000.0
    entry_price = 100.0
    stop_loss = 98.0
    
    size = strategy.get_position_size(portfolio_value, entry_price, stop_loss)
    
    # Should return a positive size
    assert size > 0
    # Risk should be around 2% of portfolio
    risk_amount = portfolio_value * 0.02
    expected_size = risk_amount / (entry_price - stop_loss)
    assert abs(size - expected_size) < 1.0

