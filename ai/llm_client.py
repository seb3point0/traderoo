"""
LLM client for AI-powered market analysis
"""
from typing import Optional, Dict, List
from enum import Enum
import json

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from app.config import get_settings
from app.utils.logger import log

settings = get_settings()


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMClient:
    """Client for LLM-powered market analysis"""
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        api_key: Optional[str] = None
    ):
        self.provider = provider
        self.client = None
        
        if provider == LLMProvider.OPENAI and OPENAI_AVAILABLE:
            api_key = api_key or settings.openai_api_key
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key)
        elif provider == LLMProvider.ANTHROPIC and ANTHROPIC_AVAILABLE:
            api_key = api_key or settings.anthropic_api_key
            if api_key:
                self.client = AsyncAnthropic(api_key=api_key)
        
        if not self.client:
            log.warning(f"LLM client not initialized for {provider.value}")
    
    async def analyze_market_conditions(
        self,
        symbol: str,
        price_data: Dict,
        indicators: Dict,
        sentiment: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Analyze market conditions using LLM
        
        Args:
            symbol: Trading pair symbol
            price_data: Current price data (open, high, low, close, volume)
            indicators: Technical indicators
            sentiment: Market sentiment data
        
        Returns:
            Analysis with trading suggestion
        """
        if not self.client:
            return None
        
        try:
            # Prepare context
            context = self._prepare_market_context(symbol, price_data, indicators, sentiment)
            
            # Get analysis from LLM
            if self.provider == LLMProvider.OPENAI:
                response = await self._openai_analysis(context)
            else:
                response = await self._anthropic_analysis(context)
            
            return response
            
        except Exception as e:
            log.error(f"Error in LLM market analysis: {e}")
            return None
    
    def _prepare_market_context(
        self,
        symbol: str,
        price_data: Dict,
        indicators: Dict,
        sentiment: Optional[Dict]
    ) -> str:
        """Prepare market data context for LLM"""
        context = f"""Analyze the following market data for {symbol}:

Current Price Data:
- Open: ${price_data.get('open', 0):.2f}
- High: ${price_data.get('high', 0):.2f}
- Low: ${price_data.get('low', 0):.2f}
- Close: ${price_data.get('close', 0):.2f}
- Volume: {price_data.get('volume', 0):.2f}

Technical Indicators:
"""
        
        # Add indicators
        for key, value in indicators.items():
            if value is not None:
                context += f"- {key}: {value:.2f}\n"
        
        # Add sentiment if available
        if sentiment:
            context += f"\nMarket Sentiment:\n"
            context += f"- Fear & Greed Index: {sentiment.get('score', 'N/A')}\n"
            context += f"- Classification: {sentiment.get('classification', 'N/A')}\n"
        
        context += """
Based on this data, provide:
1. Market trend analysis (bullish/bearish/neutral)
2. Key support and resistance levels
3. Trading recommendation (buy/sell/hold) with confidence level (0-1)
4. Risk assessment (low/medium/high)
5. Brief reasoning (max 2 sentences)

Respond in JSON format:
{
    "trend": "bullish|bearish|neutral",
    "support": <price>,
    "resistance": <price>,
    "recommendation": "buy|sell|hold",
    "confidence": <0-1>,
    "risk": "low|medium|high",
    "reasoning": "explanation"
}
"""
        return context
    
    async def _openai_analysis(self, context: str) -> Optional[Dict]:
        """Get analysis from OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency trading analyst. Provide concise, data-driven analysis."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                # Extract JSON from markdown code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                log.warning("Failed to parse LLM response as JSON")
                return {"raw_response": content}
            
        except Exception as e:
            log.error(f"OpenAI API error: {e}")
            return None
    
    async def _anthropic_analysis(self, context: str) -> Optional[Dict]:
        """Get analysis from Anthropic Claude"""
        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": context
                    }
                ]
            )
            
            content = response.content[0].text
            
            # Try to parse JSON response
            try:
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                log.warning("Failed to parse LLM response as JSON")
                return {"raw_response": content}
            
        except Exception as e:
            log.error(f"Anthropic API error: {e}")
            return None
    
    async def generate_trade_summary(self, trades: List[Dict]) -> Optional[str]:
        """Generate a summary of recent trades"""
        if not self.client or not trades:
            return None
        
        try:
            trades_text = "\n".join([
                f"- {t['side'].upper()} {t['amount']} {t['symbol']} @ ${t['price']:.2f} | P&L: ${t.get('realized_pnl', 0):.2f}"
                for t in trades[:10]
            ])
            
            prompt = f"""Summarize these recent trades and provide insights:

{trades_text}

Provide:
1. Overall performance
2. Win/loss ratio
3. Key observations
4. Suggestions for improvement

Keep it concise (max 5 sentences).
"""
            
            if self.provider == LLMProvider.OPENAI:
                response = await self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5,
                    max_tokens=300
                )
                return response.choices[0].message.content
            else:
                response = await self.client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            
        except Exception as e:
            log.error(f"Error generating trade summary: {e}")
            return None

