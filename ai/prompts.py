"""
Optimized prompts for AI market analysis and signal validation
"""
from typing import Dict, Optional
from app.strategies.base import Signal


def get_signal_validation_prompt(
    strategy_name: str,
    signal: Signal,
    symbol: str,
    technical_data: Dict,
    sentiment_data: Dict,
    news_data: Dict,
    social_data: Dict,
    onchain_data: Dict,
    entry_price: Optional[float] = None
) -> str:
    """
    Generate comprehensive prompt for signal validation
    
    Args:
        strategy_name: Name of the strategy generating the signal
        signal: Trading signal (BUY/SELL/HOLD)
        symbol: Trading symbol
        technical_data: Technical indicators
        sentiment_data: Market sentiment data
        news_data: News sentiment data
        social_data: Social sentiment data
        onchain_data: On-chain metrics
        entry_price: Suggested entry price
    
    Returns:
        Formatted prompt for LLM
    """
    
    prompt = f"""You are an expert cryptocurrency trading analyst. Analyze this trading signal:

====== TRADING SIGNAL ======
Strategy: {strategy_name}
Signal: {signal.value.upper()}
Symbol: {symbol}
Entry Price: ${entry_price:.2f if entry_price else 0}

====== TECHNICAL ANALYSIS ======
"""
    
    # Add technical indicators
    if technical_data:
        prompt += f"Current Price: ${technical_data.get('price', 0):.2f}\n"
        
        if 'price_change_pct' in technical_data:
            prompt += f"Price Change (24h): {technical_data['price_change_pct']:.2f}%\n"
        
        if 'rsi' in technical_data:
            rsi = technical_data['rsi']
            rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
            prompt += f"RSI: {rsi:.1f} ({rsi_status})\n"
        
        if 'macd' in technical_data and 'macd_signal' in technical_data:
            macd = technical_data['macd']
            signal_line = technical_data['macd_signal']
            macd_status = "Bullish" if macd > signal_line else "Bearish"
            prompt += f"MACD: {macd:.2f}, Signal: {signal_line:.2f} ({macd_status})\n"
        
        if 'bb_upper' in technical_data and 'bb_lower' in technical_data:
            price = technical_data.get('price', 0)
            bb_upper = technical_data['bb_upper']
            bb_lower = technical_data['bb_lower']
            if price > bb_upper:
                bb_status = "Above upper band (overbought)"
            elif price < bb_lower:
                bb_status = "Below lower band (oversold)"
            else:
                bb_status = "Within bands (normal)"
            prompt += f"Bollinger Bands: ${bb_lower:.2f} - ${bb_upper:.2f} ({bb_status})\n"
        
        if 'volume_vs_avg' in technical_data:
            vol_ratio = technical_data['volume_vs_avg']
            vol_status = "High" if vol_ratio > 1.5 else "Low" if vol_ratio < 0.7 else "Normal"
            prompt += f"Volume vs Average: {vol_ratio:.2f}x ({vol_status})\n"
        
        if 'adx' in technical_data:
            adx = technical_data['adx']
            trend_strength = "Strong trend" if adx > 25 else "Weak trend"
            prompt += f"ADX: {adx:.1f} ({trend_strength})\n"
    
    # Add market sentiment
    prompt += "\n====== MARKET SENTIMENT ======\n"
    if sentiment_data:
        score = sentiment_data.get('score', 50)
        classification = sentiment_data.get('classification', 'Neutral')
        prompt += f"Fear & Greed Index: {score}/100 ({classification})\n"
        
        if 'trend' in sentiment_data and sentiment_data['trend']:
            trend_info = sentiment_data['trend']
            prompt += f"Sentiment Trend: {trend_info.get('trend', 'stable').capitalize()}\n"
    else:
        prompt += "No sentiment data available\n"
    
    # Add news sentiment
    prompt += "\n====== NEWS SENTIMENT ======\n"
    if news_data:
        total_news = news_data.get('total_news', 0)
        news_sentiment = news_data.get('overall_sentiment', 'neutral')
        breaking = news_data.get('breaking_news_count', 0)
        
        prompt += f"Total News (24h): {total_news}\n"
        prompt += f"Overall Sentiment: {news_sentiment.capitalize()}\n"
        prompt += f"Breaking News: {breaking}\n"
        
        if 'recent_headlines' in news_data:
            prompt += "\nRecent Headlines:\n"
            for i, headline in enumerate(news_data['recent_headlines'][:3], 1):
                prompt += f"{i}. {headline['title']} ({headline['sentiment']})\n"
    else:
        prompt += "No news data available\n"
    
    # Add social sentiment
    prompt += "\n====== SOCIAL SENTIMENT ======\n"
    if social_data:
        social_sentiment = social_data.get('sentiment', 'neutral')
        social_score = social_data.get('social_score', 0)
        
        prompt += f"Social Sentiment: {social_sentiment.capitalize()}\n"
        prompt += f"Social Activity Score: {social_score:.2f}\n"
        
        if 'metrics' in social_data:
            metrics = social_data['metrics']
            if 'reddit' in metrics:
                reddit = metrics['reddit']
                prompt += f"Reddit Subscribers: {reddit.get('subscribers', 0):,}\n"
                prompt += f"Reddit Engagement (48h): {reddit.get('engagement_score', 0)}\n"
    else:
        prompt += "No social data available\n"
    
    # Add on-chain metrics
    prompt += "\n====== ON-CHAIN METRICS ======\n"
    if onchain_data:
        onchain_sentiment = onchain_data.get('overall_sentiment', 'neutral')
        prompt += f"On-chain Sentiment: {onchain_sentiment.capitalize()}\n"
        
        metrics = onchain_data.get('metrics', {})
        
        if 'exchange_flows' in metrics:
            flows = metrics['exchange_flows']
            flow_direction = flows.get('flow_direction', 'neutral')
            vol_change = flows.get('volume_change_pct', 0)
            prompt += f"Exchange Flows: {flow_direction.capitalize()} ({vol_change:+.1f}% volume change)\n"
        
        if 'whale_activity' in metrics:
            whale = metrics['whale_activity']
            whale_activity = whale.get('whale_activity', 'low')
            prompt += f"Whale Activity: {whale_activity.capitalize()}\n"
    else:
        prompt += "No on-chain data available\n"
    
    # Add validation instructions
    prompt += f"""
====== YOUR TASK ======
Validate the {signal.value.upper()} signal from {strategy_name} for {symbol}.

Consider:
1. Does the technical setup support this signal?
2. Is market sentiment aligned or opposed?
3. Are there any red flags in news or social sentiment?
4. What do on-chain metrics suggest?
5. What are the key risks?

Provide your analysis in JSON format:
{{
  "validation": "agree|disagree|partial",
  "confidence": 0-100,
  "position_multiplier": 0.5-1.5,
  "adjusted_entry": <price or null>,
  "adjusted_stop_loss": <price or null>,
  "adjusted_take_profit": <price or null>,
  "key_risks": ["risk1", "risk2", "risk3"],
  "reasoning": "2-3 sentence explanation",
  "time_horizon": "short|medium|long",
  "data_quality_score": 0-10
}}

Guidelines:
- "agree": Signal looks good, execute it
- "disagree": Signal is risky, avoid it
- "partial": Mixed signals, proceed with caution
- confidence: 0-100 (60+ recommended for execution)
- position_multiplier: 0.5-1.5 (scale position size)
- data_quality_score: How complete/reliable is the data (10=perfect)

Respond with ONLY the JSON, no other text.
"""
    
    return prompt


def get_market_analysis_prompt(
    symbol: str,
    comprehensive_data: Dict
) -> str:
    """
    Generate prompt for general market analysis (non-signal specific)
    
    Args:
        symbol: Trading symbol
        comprehensive_data: All aggregated data
    
    Returns:
        Formatted prompt for LLM
    """
    
    technical = comprehensive_data.get('technical', {})
    sentiment = comprehensive_data.get('sentiment', {})
    news = comprehensive_data.get('news', {})
    social = comprehensive_data.get('social', {})
    onchain = comprehensive_data.get('onchain', {})
    
    prompt = f"""Analyze the current market conditions for {symbol}:

PRICE: ${technical.get('price', 0):.2f}
CHANGE: {technical.get('price_change_pct', 0):+.2f}%

SENTIMENT:
- Fear & Greed: {sentiment.get('score', 50)}/100
- News: {news.get('overall_sentiment', 'neutral')}
- Social: {social.get('sentiment', 'neutral')}
- On-chain: {onchain.get('overall_sentiment', 'neutral')}

Provide a concise market overview in JSON format:
{{
  "market_phase": "accumulation|markup|distribution|markdown",
  "trend": "bullish|bearish|neutral",
  "strength": 1-10,
  "key_levels": {{
    "support": <price>,
    "resistance": <price>
  }},
  "outlook": "2-3 sentence summary",
  "confidence": 0-100
}}

Respond with ONLY the JSON.
"""
    
    return prompt

