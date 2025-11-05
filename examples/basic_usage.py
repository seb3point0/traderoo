"""
Example usage of the trading bot
"""
import asyncio
from app.core.exchange_manager import ExchangeFactory
from app.data.market_data import MarketDataManager
from app.strategies.ma_crossover import MACrossoverStrategy
from app.backtesting.engine import BacktestEngine


async def example_backtest():
    """Example: Run a backtest on historical data"""
    print("=== Example: Backtesting MA Crossover Strategy ===\n")
    
    # Initialize exchange
    exchange = await ExchangeFactory.get_exchange('binance')
    
    # Get historical data
    market_data = MarketDataManager(exchange)
    df = await market_data.get_ohlcv_df(
        symbol='BTC/USDT',
        timeframe='1h',
        limit=500,
        with_indicators=True
    )
    
    print(f"Loaded {len(df)} candles of data")
    print(f"Date range: {df.index[0]} to {df.index[-1]}\n")
    
    # Create strategy
    strategy = MACrossoverStrategy(
        symbol='BTC/USDT',
        timeframe='1h',
        params={
            'fast_period': 12,
            'slow_period': 26,
            'ma_type': 'ema'
        }
    )
    
    # Run backtest
    backtest = BacktestEngine(
        strategy=strategy,
        initial_capital=10000.0,
        commission=0.001
    )
    
    results = await backtest.run(df, verbose=True)
    
    # Print results
    print("\n=== Backtest Results ===")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Total P&L: ${results['total_pnl']:.2f}")
    print(f"Total Return: {results['total_return_pct']:.2f}%")
    print(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    
    await ExchangeFactory.close_all()


async def example_live_data():
    """Example: Fetch live market data and indicators"""
    print("\n=== Example: Live Market Data ===\n")
    
    # Initialize exchange
    exchange = await ExchangeFactory.get_exchange('binance')
    
    # Get current ticker
    ticker = await exchange.fetch_ticker('BTC/USDT')
    print(f"BTC/USDT Current Price: ${ticker['last']:.2f}")
    print(f"24h Change: {ticker.get('percentage', 0):.2f}%")
    print(f"24h Volume: {ticker.get('quoteVolume', 0):,.0f} USDT\n")
    
    # Get market data with indicators
    market_data = MarketDataManager(exchange)
    df = await market_data.get_ohlcv_df(
        symbol='BTC/USDT',
        timeframe='1h',
        limit=100,
        with_indicators=True
    )
    
    # Show latest indicators
    latest = df.iloc[-1]
    print("Latest Technical Indicators:")
    print(f"RSI: {latest.get('rsi', 0):.2f}")
    print(f"MACD: {latest.get('macd', 0):.4f}")
    print(f"BB Upper: ${latest.get('bb_upper', 0):.2f}")
    print(f"BB Lower: ${latest.get('bb_lower', 0):.2f}")
    print(f"ATR: {latest.get('atr', 0):.2f}")
    
    await ExchangeFactory.close_all()


async def example_data_sources():
    """Example: Use external data sources"""
    print("\n=== Example: External Data Sources ===\n")
    
    # CoinGecko
    from app.data.sources.coingecko import CoinGeckoClient
    
    async with CoinGeckoClient() as cg:
        # Get trending coins
        trending = await cg.get_trending()
        if trending and 'coins' in trending:
            print("Trending Coins:")
            for coin in trending['coins'][:5]:
                item = coin.get('item', {})
                print(f"  - {item.get('name')} ({item.get('symbol', '').upper()})")
        
        # Get global market data
        global_data = await cg.get_global_data()
        if global_data:
            print(f"\nGlobal Market Cap: ${global_data.get('total_market_cap', {}).get('usd', 0):,.0f}")
            print(f"Bitcoin Dominance: {global_data.get('market_cap_percentage', {}).get('btc', 0):.2f}%")
    
    # Sentiment Analysis
    from app.data.sources.sentiment import SentimentAnalyzer
    
    async with SentimentAnalyzer() as sentiment:
        data = await sentiment.get_comprehensive_sentiment()
        if data:
            print(f"\nMarket Sentiment:")
            print(f"  Fear & Greed Index: {data['score']:.0f}")
            print(f"  Classification: {data['classification']}")
            print(f"  Trading Signal: {data['trading_signal']['signal']}")
            print(f"  Reasoning: {data['trading_signal']['reason']}")


async def example_ai_analysis():
    """Example: AI-powered market analysis"""
    print("\n=== Example: AI Market Analysis ===\n")
    
    from app.ai.llm_client import LLMClient, LLMProvider
    from app.config import get_settings
    
    settings = get_settings()
    
    if not settings.openai_api_key and not settings.anthropic_api_key:
        print("No AI API keys configured. Skipping AI analysis example.")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env to use this feature.")
        return
    
    # Initialize LLM client
    provider = LLMProvider.OPENAI if settings.openai_api_key else LLMProvider.ANTHROPIC
    llm = LLMClient(provider=provider)
    
    # Prepare market data
    exchange = await ExchangeFactory.get_exchange('binance')
    ticker = await exchange.fetch_ticker('BTC/USDT')
    
    price_data = {
        'open': ticker.get('open', 0),
        'high': ticker.get('high', 0),
        'low': ticker.get('low', 0),
        'close': ticker.get('last', 0),
        'volume': ticker.get('quoteVolume', 0)
    }
    
    indicators = {
        'rsi': 55.0,  # Example values
        'macd': 0.05,
        'sma_20': ticker.get('last', 0) * 0.98,
        'sma_50': ticker.get('last', 0) * 0.96
    }
    
    # Get AI analysis
    print("Requesting AI analysis...")
    analysis = await llm.analyze_market_conditions(
        symbol='BTC/USDT',
        price_data=price_data,
        indicators=indicators
    )
    
    if analysis:
        print("\nAI Analysis Results:")
        print(f"Trend: {analysis.get('trend', 'N/A')}")
        print(f"Recommendation: {analysis.get('recommendation', 'N/A')}")
        print(f"Confidence: {analysis.get('confidence', 0):.0%}")
        print(f"Risk Level: {analysis.get('risk', 'N/A')}")
        print(f"Reasoning: {analysis.get('reasoning', 'N/A')}")
    
    await ExchangeFactory.close_all()


async def main():
    """Run all examples"""
    try:
        # Example 1: Backtesting
        await example_backtest()
        
        # Example 2: Live data
        await example_live_data()
        
        # Example 3: External data sources
        await example_data_sources()
        
        # Example 4: AI analysis (requires API keys)
        await example_ai_analysis()
        
        print("\n=== All examples completed successfully! ===")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())

