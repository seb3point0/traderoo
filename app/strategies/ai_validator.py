"""
AI Validator Strategy - Wraps traditional strategies with AI validation
"""
from typing import Optional, Dict
import pandas as pd

from app.strategies.base import BaseStrategy, Signal
from ai.ai_market_analyzer import AIMarketAnalyzer
from ai.llm_client import LLMProvider
from app.utils.logger import log


class AIValidatorStrategy(BaseStrategy):
    """
    AI-enhanced strategy wrapper that validates traditional strategy signals
    
    This strategy wraps an existing strategy and uses AI to validate signals
    before execution. It also adjusts position sizing based on AI confidence.
    """
    
    def __init__(
        self,
        wrapped_strategy: BaseStrategy,
        min_confidence: int = 60,
        llm_provider: LLMProvider = LLMProvider.OPENAI,
        enable_cache: bool = True
    ):
        """
        Initialize AI Validator Strategy
        
        Args:
            wrapped_strategy: The traditional strategy to wrap
            min_confidence: Minimum AI confidence (0-100) to execute trades
            llm_provider: LLM provider to use
            enable_cache: Enable caching for routine analysis
        """
        # Initialize base class with wrapped strategy's parameters
        super().__init__(
            symbol=wrapped_strategy.symbol,
            timeframe=wrapped_strategy.timeframe,
            params=wrapped_strategy.params
        )
        
        self.wrapped_strategy = wrapped_strategy
        self.min_confidence = min_confidence
        
        # AI components
        self.ai_analyzer = AIMarketAnalyzer(
            llm_provider=llm_provider,
            enable_cache=enable_cache
        )
        
        # Track AI validation history
        self.last_ai_validation: Optional[Dict] = None
        self.ai_approvals = 0
        self.ai_rejections = 0
        
        # Update name to indicate AI validation
        self.name = f"AI_{wrapped_strategy.name}"
        
        log.info(
            f"Initialized AI Validator for {wrapped_strategy.name} | "
            f"Min Confidence: {min_confidence}%"
        )
    
    async def initialize(self):
        """Initialize AI analyzer"""
        await self.ai_analyzer.initialize()
    
    async def analyze(self, data: pd.DataFrame) -> Signal:
        """
        Analyze market data with AI validation
        
        Process:
        1. Get signal from wrapped strategy
        2. If signal is HOLD, return HOLD
        3. Get AI validation for the signal
        4. Apply confidence threshold
        5. Return validated signal
        
        Args:
            data: DataFrame with OHLCV data and indicators
        
        Returns:
            Validated trading signal
        """
        try:
            # Step 1: Get traditional strategy signal
            traditional_signal = await self.wrapped_strategy.analyze(data)
            
            # Step 2: If HOLD, no need for AI validation
            if traditional_signal == Signal.HOLD:
                log.info(f"{self.wrapped_strategy.name} generated HOLD signal")
                return Signal.HOLD
            
            log.info(
                f"{self.wrapped_strategy.name} generated {traditional_signal.value.upper()} signal | "
                f"Validating with AI..."
            )
            
            # Step 3: Get entry price from wrapped strategy
            entry_price = self.wrapped_strategy.get_entry_price(data)
            
            # Step 4: Get AI validation
            validation = await self.ai_analyzer.validate_signal(
                strategy_name=self.wrapped_strategy.name,
                signal=traditional_signal,
                symbol=self.symbol,
                df=data,
                entry_price=entry_price
            )
            
            # Store validation for position sizing
            self.last_ai_validation = validation
            
            # Step 5: Check if trade should be executed
            should_execute = self.ai_analyzer.should_execute_trade(validation)
            
            # Log AI decision
            self._log_ai_decision(traditional_signal, validation, should_execute)
            
            # Step 6: Return validated signal
            if should_execute:
                self.ai_approvals += 1
                return traditional_signal
            else:
                self.ai_rejections += 1
                return Signal.HOLD
                
        except Exception as e:
            log.error(f"Error in AI validation: {e}")
            # On error, be conservative and return HOLD
            return Signal.HOLD
    
    def _log_ai_decision(
        self,
        signal: Signal,
        validation: Dict,
        should_execute: bool
    ):
        """Log AI validation decision"""
        confidence = validation['confidence']
        validation_status = validation['validation']
        reasoning = validation.get('reasoning', 'No reasoning')
        mode = validation.get('analysis_mode', 'unknown')
        
        status = "APPROVED" if should_execute else "REJECTED"
        
        log.info(
            f"AI {status}: {signal.value.upper()} | "
            f"Confidence: {confidence}% | "
            f"Validation: {validation_status} | "
            f"Mode: {mode}"
        )
        log.info(f"AI Reasoning: {reasoning}")
        
        if validation.get('is_high_impact'):
            reasons = validation.get('high_impact_reasons', [])
            log.warning(f"High-impact event detected: {', '.join(reasons)}")
        
        # Log key risks
        risks = validation.get('key_risks', [])
        if risks:
            log.info(f"Key risks: {', '.join(risks)}")
    
    def get_entry_price(self, data: pd.DataFrame) -> Optional[float]:
        """Get entry price from wrapped strategy"""
        entry = self.wrapped_strategy.get_entry_price(data)
        
        # Optionally adjust entry based on AI recommendation
        if self.last_ai_validation and self.last_ai_validation.get('adjusted_entry'):
            adjusted = self.last_ai_validation['adjusted_entry']
            log.info(f"AI adjusted entry: {entry} -> {adjusted}")
            return adjusted
        
        return entry
    
    def get_stop_loss(self, entry_price: float, side: str) -> Optional[float]:
        """Get stop loss from wrapped strategy"""
        stop_loss = self.wrapped_strategy.get_stop_loss(entry_price, side)
        
        # Optionally adjust stop loss based on AI recommendation
        if self.last_ai_validation and self.last_ai_validation.get('adjusted_stop_loss'):
            adjusted = self.last_ai_validation['adjusted_stop_loss']
            log.info(f"AI adjusted stop loss: {stop_loss} -> {adjusted}")
            return adjusted
        
        return stop_loss
    
    def get_take_profit(self, entry_price: float, side: str) -> Optional[float]:
        """Get take profit from wrapped strategy"""
        take_profit = self.wrapped_strategy.get_take_profit(entry_price, side)
        
        # Optionally adjust take profit based on AI recommendation
        if self.last_ai_validation and self.last_ai_validation.get('adjusted_take_profit'):
            adjusted = self.last_ai_validation['adjusted_take_profit']
            log.info(f"AI adjusted take profit: {take_profit} -> {adjusted}")
            return adjusted
        
        return take_profit
    
    def get_position_size(
        self,
        portfolio_value: float,
        entry_price: float,
        stop_loss: Optional[float] = None
    ) -> float:
        """
        Get AI-adjusted position size
        
        Applies AI confidence multiplier to base position size:
        - 60% confidence -> 0.6x position
        - 80% confidence -> 1.0x position
        - 95% confidence -> 1.5x position
        """
        # Get base position size from wrapped strategy
        base_size = self.wrapped_strategy.get_position_size(
            portfolio_value,
            entry_price,
            stop_loss
        )
        
        # Apply AI multiplier if available
        if self.last_ai_validation:
            multiplier = self._calculate_position_multiplier()
            adjusted_size = base_size * multiplier
            
            log.info(
                f"Position size: {base_size:.4f} -> {adjusted_size:.4f} "
                f"(AI multiplier: {multiplier:.2f}x)"
            )
            
            return adjusted_size
        
        return base_size
    
    def _calculate_position_multiplier(self) -> float:
        """
        Calculate position size multiplier based on AI confidence
        
        Returns:
            Float between 0.5 and 1.5
        """
        if not self.last_ai_validation:
            return 1.0
        
        confidence = self.last_ai_validation['confidence']
        ai_multiplier = self.last_ai_validation.get('position_multiplier', 1.0)
        
        # Scale confidence (60-100%) to multiplier (0.6-1.5)
        # Formula: (confidence - 50) / 50
        # 60% -> 0.6x, 75% -> 1.0x, 100% -> 1.5x (capped)
        confidence_factor = max(0.6, min((confidence - 50) / 50, 1.5))
        
        # Combine with AI's suggested multiplier
        final_multiplier = confidence_factor * ai_multiplier
        
        # Ensure within bounds
        return max(0.5, min(1.5, final_multiplier))
    
    def get_ai_stats(self) -> Dict:
        """Get AI validation statistics"""
        total = self.ai_approvals + self.ai_rejections
        approval_rate = (self.ai_approvals / total * 100) if total > 0 else 0
        
        return {
            'strategy': self.wrapped_strategy.name,
            'ai_approvals': self.ai_approvals,
            'ai_rejections': self.ai_rejections,
            'approval_rate': approval_rate,
            'total_validations': total,
            'last_validation': self.last_ai_validation
        }
    
    async def should_close_position(
        self,
        data: pd.DataFrame,
        position_side: str,
        entry_price: float
    ) -> tuple[bool, str]:
        """Check if position should be closed (delegates to wrapped strategy)"""
        return await self.wrapped_strategy.should_close_position(
            data,
            position_side,
            entry_price
        )
    
    def validate_signal(self, signal: Signal, data: pd.DataFrame) -> bool:
        """Validate signal (delegates to wrapped strategy)"""
        return self.wrapped_strategy.validate_signal(signal, data)
    
    def get_description(self) -> str:
        """Get strategy description"""
        return (
            f"AI-Enhanced {self.wrapped_strategy.get_description()} | "
            f"Min Confidence: {self.min_confidence}%"
        )
    
    async def close(self):
        """Cleanup resources"""
        await self.ai_analyzer.close()
    
    def __repr__(self):
        return f"<AI_{self.wrapped_strategy.name} {self.symbol} {self.timeframe}>"

