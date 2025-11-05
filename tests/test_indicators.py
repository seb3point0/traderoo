"""
Tests for technical indicators
"""
import pytest
import pandas as pd
import numpy as np

from app.data.indicators import TechnicalIndicators


@pytest.fixture
def sample_price_data():
    """Generate sample price data"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
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


def test_sma_calculation(sample_price_data):
    """Test Simple Moving Average"""
    sma = TechnicalIndicators.calculate_sma(sample_price_data['close'], period=20)
    
    assert len(sma) == len(sample_price_data)
    assert not sma.iloc[-1] != sma.iloc[-1]  # Not NaN
    assert sma.iloc[-1] > 0


def test_ema_calculation(sample_price_data):
    """Test Exponential Moving Average"""
    ema = TechnicalIndicators.calculate_ema(sample_price_data['close'], period=20)
    
    assert len(ema) == len(sample_price_data)
    assert not ema.iloc[-1] != ema.iloc[-1]  # Not NaN
    assert ema.iloc[-1] > 0


def test_rsi_calculation(sample_price_data):
    """Test RSI"""
    rsi = TechnicalIndicators.calculate_rsi(sample_price_data['close'], period=14)
    
    assert len(rsi) == len(sample_price_data)
    # RSI should be between 0 and 100
    valid_rsi = rsi.dropna()
    assert all(valid_rsi >= 0) and all(valid_rsi <= 100)


def test_macd_calculation(sample_price_data):
    """Test MACD"""
    macd, signal, hist = TechnicalIndicators.calculate_macd(sample_price_data['close'])
    
    assert len(macd) == len(sample_price_data)
    assert len(signal) == len(sample_price_data)
    assert len(hist) == len(sample_price_data)


def test_bollinger_bands(sample_price_data):
    """Test Bollinger Bands"""
    upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(
        sample_price_data['close'],
        period=20
    )
    
    assert len(upper) == len(sample_price_data)
    
    # Upper should be above middle, middle above lower
    valid_idx = ~upper.isna()
    assert all(upper[valid_idx] >= middle[valid_idx])
    assert all(middle[valid_idx] >= lower[valid_idx])


def test_atr_calculation(sample_price_data):
    """Test ATR"""
    atr = TechnicalIndicators.calculate_atr(
        sample_price_data['high'],
        sample_price_data['low'],
        sample_price_data['close'],
        period=14
    )
    
    assert len(atr) == len(sample_price_data)
    # ATR should be positive
    valid_atr = atr.dropna()
    assert all(valid_atr >= 0)


def test_crossover_detection():
    """Test crossover detection"""
    fast = pd.Series([1, 2, 3, 4, 5])
    slow = pd.Series([3, 3, 3, 3, 3])
    
    crossover = TechnicalIndicators.detect_crossover(fast, slow)
    
    # Crossover should occur at index 3 (fast crosses above slow)
    assert crossover.iloc[3] == True


def test_crossunder_detection():
    """Test crossunder detection"""
    fast = pd.Series([5, 4, 3, 2, 1])
    slow = pd.Series([3, 3, 3, 3, 3])
    
    crossunder = TechnicalIndicators.detect_crossunder(fast, slow)
    
    # Crossunder should occur at index 3 (fast crosses below slow)
    assert crossunder.iloc[3] == True


def test_add_all_indicators(sample_price_data):
    """Test adding all indicators"""
    df = TechnicalIndicators.add_all_indicators(sample_price_data)
    
    # Check that indicators were added
    assert 'sma_20' in df.columns
    assert 'ema_12' in df.columns
    assert 'rsi' in df.columns
    assert 'macd' in df.columns
    assert 'bb_upper' in df.columns
    assert 'atr' in df.columns
    
    # Check that data isn't empty
    assert len(df) > 0

