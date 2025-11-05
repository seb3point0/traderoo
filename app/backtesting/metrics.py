"""
Performance metrics calculation for backtesting
"""
import pandas as pd
import numpy as np
from typing import List, Dict
from app.backtesting.engine import BacktestTrade


class PerformanceCalculator:
    """Calculate performance metrics from backtest results"""
    
    def __init__(
        self,
        trades: List[BacktestTrade],
        equity_curve: pd.DataFrame,
        initial_capital: float
    ):
        self.trades = trades
        self.equity_curve = equity_curve
        self.initial_capital = initial_capital
    
    def calculate_all_metrics(self) -> Dict:
        """Calculate all performance metrics"""
        return {
            # Trade metrics
            'total_trades': self.total_trades(),
            'winning_trades': self.winning_trades(),
            'losing_trades': self.losing_trades(),
            'win_rate': self.win_rate(),
            
            # P&L metrics
            'total_pnl': self.total_pnl(),
            'total_fees': self.total_fees(),
            'net_pnl': self.net_pnl(),
            'average_pnl': self.average_pnl(),
            'average_win': self.average_win(),
            'average_loss': self.average_loss(),
            
            # Returns
            'total_return_pct': self.total_return_pct(),
            'annualized_return_pct': self.annualized_return_pct(),
            
            # Risk metrics
            'max_drawdown': self.max_drawdown(),
            'max_drawdown_pct': self.max_drawdown_pct(),
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'calmar_ratio': self.calmar_ratio(),
            
            # Other metrics
            'profit_factor': self.profit_factor(),
            'expectancy': self.expectancy(),
            'max_consecutive_wins': self.max_consecutive_wins(),
            'max_consecutive_losses': self.max_consecutive_losses(),
            
            # Final values
            'final_capital': self.final_capital(),
            'peak_capital': self.peak_capital()
        }
    
    # Trade Metrics
    
    def total_trades(self) -> int:
        """Total number of closed trades"""
        return sum(1 for t in self.trades if t.side == 'sell')
    
    def winning_trades(self) -> int:
        """Number of winning trades"""
        return sum(1 for t in self.trades if t.side == 'sell' and t.pnl > 0)
    
    def losing_trades(self) -> int:
        """Number of losing trades"""
        return sum(1 for t in self.trades if t.side == 'sell' and t.pnl < 0)
    
    def win_rate(self) -> float:
        """Win rate percentage"""
        total = self.total_trades()
        if total == 0:
            return 0.0
        return (self.winning_trades() / total) * 100
    
    # P&L Metrics
    
    def total_pnl(self) -> float:
        """Total P&L"""
        return sum(t.pnl for t in self.trades if t.side == 'sell')
    
    def total_fees(self) -> float:
        """Total fees paid"""
        return sum(t.fee for t in self.trades)
    
    def net_pnl(self) -> float:
        """Net P&L after fees"""
        return self.total_pnl()  # Fees already deducted in pnl calculation
    
    def average_pnl(self) -> float:
        """Average P&L per trade"""
        total = self.total_trades()
        if total == 0:
            return 0.0
        return self.total_pnl() / total
    
    def average_win(self) -> float:
        """Average winning trade P&L"""
        wins = [t.pnl for t in self.trades if t.side == 'sell' and t.pnl > 0]
        return np.mean(wins) if wins else 0.0
    
    def average_loss(self) -> float:
        """Average losing trade P&L"""
        losses = [t.pnl for t in self.trades if t.side == 'sell' and t.pnl < 0]
        return np.mean(losses) if losses else 0.0
    
    # Returns
    
    def total_return_pct(self) -> float:
        """Total return percentage"""
        if self.initial_capital == 0:
            return 0.0
        return (self.total_pnl() / self.initial_capital) * 100
    
    def annualized_return_pct(self) -> float:
        """Annualized return percentage"""
        if self.equity_curve.empty:
            return 0.0
        
        # Calculate number of years
        time_diff = self.equity_curve.index[-1] - self.equity_curve.index[0]
        years = time_diff.days / 365.25
        
        if years == 0:
            return 0.0
        
        total_return = self.total_return_pct() / 100
        return ((1 + total_return) ** (1 / years) - 1) * 100
    
    # Risk Metrics
    
    def max_drawdown(self) -> float:
        """Maximum drawdown in dollar amount"""
        if self.equity_curve.empty:
            return 0.0
        
        equity = self.equity_curve['equity']
        cummax = equity.cummax()
        drawdown = equity - cummax
        return abs(drawdown.min())
    
    def max_drawdown_pct(self) -> float:
        """Maximum drawdown percentage"""
        if self.equity_curve.empty:
            return 0.0
        
        equity = self.equity_curve['equity']
        cummax = equity.cummax()
        drawdown_pct = ((equity - cummax) / cummax) * 100
        return abs(drawdown_pct.min())
    
    def sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Sharpe ratio (annualized)"""
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        
        returns = self.equity_curve['equity'].pct_change().dropna()
        
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        sharpe = excess_returns.mean() / returns.std()
        
        return sharpe * np.sqrt(252)  # Annualize
    
    def sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """Sortino ratio (annualized)"""
        if self.equity_curve.empty or len(self.equity_curve) < 2:
            return 0.0
        
        returns = self.equity_curve['equity'].pct_change().dropna()
        
        if len(returns) == 0:
            return 0.0
        
        excess_returns = returns - (risk_free_rate / 252)
        downside_returns = returns[returns < 0]
        
        if len(downside_returns) == 0 or downside_returns.std() == 0:
            return 0.0
        
        sortino = excess_returns.mean() / downside_returns.std()
        
        return sortino * np.sqrt(252)  # Annualize
    
    def calmar_ratio(self) -> float:
        """Calmar ratio (annualized return / max drawdown)"""
        max_dd = self.max_drawdown_pct()
        
        if max_dd == 0:
            return 0.0
        
        return self.annualized_return_pct() / max_dd
    
    # Other Metrics
    
    def profit_factor(self) -> float:
        """Profit factor (gross profit / gross loss)"""
        wins = sum(t.pnl for t in self.trades if t.side == 'sell' and t.pnl > 0)
        losses = abs(sum(t.pnl for t in self.trades if t.side == 'sell' and t.pnl < 0))
        
        if losses == 0:
            return float('inf') if wins > 0 else 0.0
        
        return wins / losses
    
    def expectancy(self) -> float:
        """Expected value per trade"""
        return self.average_pnl()
    
    def max_consecutive_wins(self) -> int:
        """Maximum consecutive winning trades"""
        closed_trades = [t for t in self.trades if t.side == 'sell']
        
        max_wins = 0
        current_wins = 0
        
        for trade in closed_trades:
            if trade.pnl > 0:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    def max_consecutive_losses(self) -> int:
        """Maximum consecutive losing trades"""
        closed_trades = [t for t in self.trades if t.side == 'sell']
        
        max_losses = 0
        current_losses = 0
        
        for trade in closed_trades:
            if trade.pnl < 0:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def final_capital(self) -> float:
        """Final capital after all trades"""
        if self.equity_curve.empty:
            return self.initial_capital
        return self.equity_curve['equity'].iloc[-1]
    
    def peak_capital(self) -> float:
        """Peak capital reached"""
        if self.equity_curve.empty:
            return self.initial_capital
        return self.equity_curve['equity'].max()

