"""
Tests for risk management
"""
import pytest
from app.utils.risk import RiskManager


def test_risk_manager_initialization():
    """Test risk manager initialization"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    assert rm.max_position_size == 1000.0
    assert rm.risk_per_trade == 0.02
    assert rm.max_daily_loss == 500.0
    assert rm.max_open_positions == 5


def test_position_size_calculation():
    """Test position size calculation"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    portfolio_value = 10000.0
    entry_price = 100.0
    stop_loss = 98.0
    
    # Percentage method
    size = rm.calculate_position_size(
        portfolio_value,
        entry_price,
        stop_loss,
        method="percentage"
    )
    
    assert size > 0
    assert size <= rm.max_position_size


def test_can_open_position():
    """Test position opening checks"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=3
    )
    
    # Should allow opening position
    can_open, reason = rm.can_open_position(
        current_positions=2,
        position_value=500.0
    )
    
    assert can_open == True
    assert reason is None
    
    # Should not allow - too many positions
    can_open, reason = rm.can_open_position(
        current_positions=3,
        position_value=500.0
    )
    
    assert can_open == False
    assert "Maximum open positions" in reason


def test_daily_loss_limit():
    """Test daily loss limit"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    # Update with losses
    rm.update_daily_pnl(-400.0)
    
    # Should still allow
    can_open, _ = rm.can_open_position(1, 500.0)
    assert can_open == True
    
    # Update with more losses
    rm.update_daily_pnl(-200.0)
    
    # Should not allow - daily limit hit
    can_open, reason = rm.can_open_position(1, 500.0)
    assert can_open == False
    assert "Daily loss limit" in reason


def test_stop_loss_calculation():
    """Test stop loss calculation"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    entry_price = 100.0
    
    # Long position
    stop_loss_long = rm.calculate_stop_loss(entry_price, 'buy', percentage=0.02)
    assert stop_loss_long < entry_price
    assert abs(entry_price - stop_loss_long) / entry_price == pytest.approx(0.02, rel=0.01)
    
    # Short position
    stop_loss_short = rm.calculate_stop_loss(entry_price, 'sell', percentage=0.02)
    assert stop_loss_short > entry_price
    assert abs(stop_loss_short - entry_price) / entry_price == pytest.approx(0.02, rel=0.01)


def test_take_profit_calculation():
    """Test take profit calculation"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    entry_price = 100.0
    risk_reward_ratio = 2.0
    
    # Long position
    tp_long = rm.calculate_take_profit(entry_price, 'buy', risk_reward_ratio)
    assert tp_long > entry_price
    
    # Short position
    tp_short = rm.calculate_take_profit(entry_price, 'sell', risk_reward_ratio)
    assert tp_short < entry_price


def test_daily_pnl_reset():
    """Test daily P&L reset"""
    rm = RiskManager(
        max_position_size=1000.0,
        risk_per_trade=0.02,
        max_daily_loss=500.0,
        max_open_positions=5
    )
    
    rm.update_daily_pnl(-300.0)
    assert rm.daily_pnl == -300.0
    
    rm.reset_daily_pnl()
    assert rm.daily_pnl == 0.0

