"""
Grid Trading Strategy
"""
import pandas as pd
from typing import Optional, List
from app.strategies.base import BaseStrategy, Signal
from app.utils.logger import log


class GridTradingStrategy(BaseStrategy):
    """
    Grid Trading Strategy
    
    Places buy and sell orders at predetermined intervals (grid levels)
    Profits from price oscillations in a range
    """
    
    def __init__(self, symbol: str, timeframe: str = "1h", params: Optional[dict] = None):
        default_params = {
            'grid_levels': 10,
            'grid_spacing_pct': 0.01,  # 1% between grid levels
            'base_price': None,  # Will be set to current price if None
            'upper_bound': None,  # Auto-calculate from recent high
            'lower_bound': None,  # Auto-calculate from recent low
            'lookback_period': 100,
            'min_data_points': 50
        }
        
        if params:
            default_params.update(params)
        
        super().__init__(symbol, timeframe, default_params)
        
        self.grid_levels: List[float] = []
        self.buy_levels: List[float] = []
        self.sell_levels: List[float] = []
        self.last_price: Optional[float] = None
    
    def _initialize_grid(self, data: pd.DataFrame):
        """Initialize grid levels based on price range"""
        if self.grid_levels:
            return  # Already initialized
        
        # Get price range
        lookback = self.params.get('lookback_period', 100)
        recent_data = data.tail(lookback)
        
        if self.params.get('lower_bound') and self.params.get('upper_bound'):
            lower = self.params['lower_bound']
            upper = self.params['upper_bound']
        else:
            lower = recent_data['low'].min()
            upper = recent_data['high'].max()
        
        base_price = self.params.get('base_price') or data['close'].iloc[-1]
        
        # Calculate grid levels
        num_levels = self.params.get('grid_levels', 10)
        grid_spacing = (upper - lower) / num_levels
        
        self.grid_levels = [lower + (i * grid_spacing) for i in range(num_levels + 1)]
        
        # Separate into buy and sell levels based on base price
        self.buy_levels = [level for level in self.grid_levels if level < base_price]
        self.sell_levels = [level for level in self.grid_levels if level > base_price]
        
        log.info(f"{self.name}: Initialized grid with {len(self.grid_levels)} levels")
        log.info(f"Range: ${lower:.2f} - ${upper:.2f}, Base: ${base_price:.2f}")
    
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """Analyze data and generate signal"""
        if len(data) < self.params['min_data_points']:
            return Signal.HOLD
        
        # Initialize grid if not done
        if not self.grid_levels:
            self._initialize_grid(data)
        
        current_price = data['close'].iloc[-1]
        
        # First run
        if self.last_price is None:
            self.last_price = current_price
            return Signal.HOLD
        
        # Check if price crossed a buy level (price moved down)
        for buy_level in self.buy_levels:
            if self.last_price > buy_level and current_price <= buy_level:
                log.info(f"{self.name}: Buy signal at grid level ${buy_level:.2f}")
                self.last_price = current_price
                return Signal.BUY
        
        # Check if price crossed a sell level (price moved up)
        for sell_level in self.sell_levels:
            if self.last_price < sell_level and current_price >= sell_level:
                log.info(f"{self.name}: Sell signal at grid level ${sell_level:.2f}")
                self.last_price = current_price
                return Signal.SELL
        
        self.last_price = current_price
        return Signal.HOLD
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price (nearest grid level)"""
        if data.empty or not self.grid_levels:
            return None
        
        current_price = data['close'].iloc[-1]
        
        # Find nearest grid level
        nearest_level = min(self.grid_levels, key=lambda x: abs(x - current_price))
        return nearest_level
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate stop loss (next grid level beyond range)"""
        if not self.grid_levels:
            return None
        
        # Grid trading doesn't typically use stop loss
        # But we can set it beyond the grid range
        if side == 'long':
            return self.grid_levels[0] * 0.95  # 5% below lowest grid
        else:
            return self.grid_levels[-1] * 1.05  # 5% above highest grid
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Calculate take profit (next grid level)"""
        if not self.grid_levels:
            return None
        
        # Find next grid level
        if side == 'long':
            # Next sell level above entry
            higher_levels = [l for l in self.sell_levels if l > entry_price]
            if higher_levels:
                return min(higher_levels)
        else:
            # Next buy level below entry
            lower_levels = [l for l in self.buy_levels if l < entry_price]
            if lower_levels:
                return max(lower_levels)
        
        return None
    
    def get_state(self) -> dict:
        """Get strategy state including grid levels"""
        state = super().get_state()
        state['grid_levels'] = self.grid_levels
        state['buy_levels'] = self.buy_levels
        state['sell_levels'] = self.sell_levels
        state['last_price'] = self.last_price
        return state
    
    def load_state(self, state: dict):
        """Load strategy state including grid levels"""
        super().load_state(state)
        self.grid_levels = state.get('grid_levels', [])
        self.buy_levels = state.get('buy_levels', [])
        self.sell_levels = state.get('sell_levels', [])
        self.last_price = state.get('last_price')

