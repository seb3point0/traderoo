"""
Backtesting engine for strategy validation
"""
import pandas as pd
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass

from app.strategies.base import BaseStrategy, Signal
from app.backtesting.metrics import PerformanceCalculator
from app.utils.logger import log


@dataclass
class BacktestTrade:
    """Trade record for backtesting"""
    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    price: float
    cost: float
    fee: float
    pnl: float = 0.0
    entry_price: float = 0.0


class BacktestEngine:
    """Backtesting engine for strategy validation"""
    
    def __init__(
        self,
        strategy: BaseStrategy,
        initial_capital: float = 10000.0,
        commission: float = 0.001  # 0.1%
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        
        # Portfolio state
        self.cash = initial_capital
        self.position_size = 0.0
        self.position_entry_price = 0.0
        self.position_side: Optional[str] = None
        
        # Trading history
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Dict] = []
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        log.info(f"Initialized backtesting engine for {strategy.name} with ${initial_capital}")
    
    async def run(
        self,
        data: pd.DataFrame,
        verbose: bool = False
    ) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: DataFrame with OHLCV data and indicators
            verbose: Print detailed logs
        
        Returns:
            Backtest results with metrics
        """
        log.info(f"Starting backtest for {self.strategy.name} on {len(data)} bars")
        
        # Reset state
        self._reset()
        
        # Iterate through historical data
        for i in range(len(data)):
            # Get data up to current point
            current_data = data.iloc[:i+1]
            
            if len(current_data) < 50:  # Need minimum data for indicators
                continue
            
            # Get current price
            current_price = current_data['close'].iloc[-1]
            timestamp = current_data.index[-1] if isinstance(current_data.index, pd.DatetimeIndex) else datetime.utcnow()
            
            # Check if we should close existing position
            if self.position_size > 0:
                should_close, reason = await self.strategy.should_close_position(
                    current_data,
                    self.position_side,
                    self.position_entry_price
                )
                
                if should_close:
                    self._close_position(
                        timestamp,
                        current_price,
                        reason
                    )
                    
                    if verbose:
                        log.info(f"Closed position at ${current_price:.2f} ({reason})")
            
            # Generate signal
            signal = await self.strategy.analyze(current_data)
            
            # Execute trade based on signal
            if signal == Signal.BUY and self.position_size == 0:
                # Calculate position size
                position_value = self.cash * 0.95  # Use 95% of available cash
                amount = position_value / current_price
                
                self._open_position(
                    timestamp,
                    'long',
                    amount,
                    current_price
                )
                
                if verbose:
                    log.info(f"Opened LONG at ${current_price:.2f} | Amount: {amount:.4f}")
            
            elif signal == Signal.SELL and self.position_size == 0:
                # For simplicity, we skip short positions in backtest
                # Could be implemented for futures trading
                pass
            
            # Record equity
            portfolio_value = self._calculate_portfolio_value(current_price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': portfolio_value,
                'cash': self.cash,
                'position_value': self.position_size * current_price if self.position_size > 0 else 0
            })
        
        # Close any open position at the end
        if self.position_size > 0:
            final_price = data['close'].iloc[-1]
            final_timestamp = data.index[-1] if isinstance(data.index, pd.DatetimeIndex) else datetime.utcnow()
            self._close_position(final_timestamp, final_price, "backtest_end")
        
        # Calculate performance metrics
        results = self._generate_results()
        
        log.info(f"Backtest completed: {results['total_trades']} trades, "
                f"{results['win_rate']:.2f}% win rate, "
                f"${results['total_pnl']:.2f} P&L")
        
        return results
    
    def _reset(self):
        """Reset backtest state"""
        self.cash = self.initial_capital
        self.position_size = 0.0
        self.position_entry_price = 0.0
        self.position_side = None
        self.trades = []
        self.equity_curve = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
    
    def _open_position(
        self,
        timestamp: datetime,
        side: str,
        amount: float,
        price: float
    ):
        """Open a position"""
        cost = amount * price
        fee = cost * self.commission
        total_cost = cost + fee
        
        if total_cost > self.cash:
            log.warning(f"Insufficient cash for position: ${total_cost:.2f} > ${self.cash:.2f}")
            return
        
        self.cash -= total_cost
        self.position_size = amount
        self.position_entry_price = price
        self.position_side = side
        
        # Record trade
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=self.strategy.symbol,
            side='buy',
            amount=amount,
            price=price,
            cost=cost,
            fee=fee,
            entry_price=price
        )
        self.trades.append(trade)
        self.total_trades += 1
    
    def _close_position(
        self,
        timestamp: datetime,
        price: float,
        reason: str
    ):
        """Close a position"""
        if self.position_size == 0:
            return
        
        proceeds = self.position_size * price
        fee = proceeds * self.commission
        net_proceeds = proceeds - fee
        
        # Calculate P&L
        cost = self.position_size * self.position_entry_price
        pnl = net_proceeds - cost
        
        self.cash += net_proceeds
        
        # Record trade
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=self.strategy.symbol,
            side='sell',
            amount=self.position_size,
            price=price,
            cost=proceeds,
            fee=fee,
            pnl=pnl,
            entry_price=self.position_entry_price
        )
        self.trades.append(trade)
        
        # Update stats
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Reset position
        self.position_size = 0.0
        self.position_entry_price = 0.0
        self.position_side = None
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calculate total portfolio value"""
        position_value = self.position_size * current_price if self.position_size > 0 else 0
        return self.cash + position_value
    
    def _generate_results(self) -> Dict:
        """Generate backtest results"""
        # Calculate metrics using PerformanceCalculator
        equity_df = pd.DataFrame(self.equity_curve)
        
        if not equity_df.empty:
            equity_df.set_index('timestamp', inplace=True)
        
        calculator = PerformanceCalculator(
            trades=self.trades,
            equity_curve=equity_df,
            initial_capital=self.initial_capital
        )
        
        metrics = calculator.calculate_all_metrics()
        
        # Add trade list to results
        metrics['trades'] = [
            {
                'timestamp': t.timestamp.isoformat(),
                'side': t.side,
                'price': round(t.price, 2),
                'amount': round(t.amount, 4),
                'pnl': round(t.pnl, 2),
                'fee': round(t.fee, 2)
            }
            for t in self.trades
        ]
        
        # Add equity curve
        if not equity_df.empty:
            metrics['equity_curve'] = equity_df.to_dict('records')
        
        return metrics

