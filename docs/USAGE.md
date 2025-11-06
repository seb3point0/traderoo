# Usage Guide

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Run with Docker (Recommended)

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f trading-api

# Stop containers
docker-compose down
```

The API will be available at `http://localhost:8000`

### 3. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Install TA-Lib (macOS)
brew install ta-lib
pip install TA-Lib

# Run the API
uvicorn app.main:app --reload
```

## API Usage

### Start the Bot

```bash
curl -X POST http://localhost:8000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "strategies": ["MACrossoverStrategy", "RSIStrategy"],
    "initial_balance": 10000.0
  }'
```

### Check Bot Status

```bash
curl http://localhost:8000/api/v1/bot/status
```

### Activate a Strategy

```bash
curl -X POST http://localhost:8000/api/v1/strategies/activate \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "MACrossoverStrategy",
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timeframe": "1h",
    "parameters": {
      "fast_period": 12,
      "slow_period": 26,
      "ma_type": "ema"
    }
  }'
```

### View Portfolio

```bash
curl http://localhost:8000/api/v1/portfolio
```

### Get Open Positions

```bash
curl http://localhost:8000/api/v1/positions
```

### View Trade History

```bash
curl http://localhost:8000/api/v1/trades?limit=50
```

### Performance Metrics

```bash
curl http://localhost:8000/api/v1/performance?days=30
```

## WebSocket Connection

Connect to real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/updates');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};

// Send ping to keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);
```

## Python Usage

### Backtesting

```python
import asyncio
from app.core.exchange_manager import ExchangeFactory
from app.data.market_data import MarketDataManager
from app.strategies.ma_crossover import MACrossoverStrategy
from app.backtesting.engine import BacktestEngine

async def run_backtest():
    # Initialize
    exchange = await ExchangeFactory.get_exchange('binance')
    market_data = MarketDataManager(exchange)
    
    # Get historical data
    df = await market_data.get_ohlcv_df(
        symbol='BTC/USDT',
        timeframe='1h',
        limit=500,
        with_indicators=True
    )
    
    # Create strategy
    strategy = MACrossoverStrategy(
        symbol='BTC/USDT',
        params={'fast_period': 12, 'slow_period': 26}
    )
    
    # Run backtest
    backtest = BacktestEngine(strategy, initial_capital=10000.0)
    results = await backtest.run(df, verbose=True)
    
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate']:.2f}%")
    print(f"Total P&L: ${results['total_pnl']:.2f}")
    
    await ExchangeFactory.close_all()

asyncio.run(run_backtest())
```

### Custom Strategy

```python
from app.strategies.base import BaseStrategy, Signal

class MyCustomStrategy(BaseStrategy):
    async def analyze(self, data):
        # Your strategy logic
        if data['rsi'].iloc[-1] < 30:
            return Signal.BUY
        elif data['rsi'].iloc[-1] > 70:
            return Signal.SELL
        return Signal.HOLD
    
    def get_entry_price(self, data):
        return data['close'].iloc[-1]
    
    def get_stop_loss(self, entry_price, side):
        return entry_price * 0.98 if side == 'long' else entry_price * 1.02
    
    def get_take_profit(self, entry_price, side):
        return entry_price * 1.04 if side == 'long' else entry_price * 0.96
```

## Available Strategies

### 1. MA Crossover
- **Description**: Moving average crossover trend following
- **Parameters**: `fast_period`, `slow_period`, `ma_type` (sma/ema)
- **Best for**: Trending markets

### 2. RSI Strategy
- **Description**: RSI mean reversion
- **Parameters**: `rsi_period`, `oversold_level`, `overbought_level`
- **Best for**: Range-bound markets

### 3. Grid Trading
- **Description**: Buy/sell at fixed price intervals
- **Parameters**: `grid_levels`, `grid_spacing_pct`
- **Best for**: Sideways markets with volatility

### 4. Momentum
- **Description**: Breakout strategy with volume confirmation
- **Parameters**: `breakout_period`, `volume_multiplier`, `adx_threshold`
- **Best for**: Strong trending markets

### 5. MACD + Bollinger Bands
- **Description**: Confluence strategy combining MACD and BB
- **Parameters**: `macd_fast`, `macd_slow`, `bb_period`
- **Best for**: Identifying high-probability entries

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_strategies.py

# Run with coverage
pytest --cov=app tests/
```

## AI Integration

Enable AI analysis by setting API keys in `.env`:

```bash
OPENAI_API_KEY=your_openai_key
# or
ANTHROPIC_API_KEY=your_anthropic_key

USE_AI_ANALYSIS=true
```

## Safety Tips

1. **Always start with paper trading**: Set `PAPER_TRADING=true` in `.env`
2. **Set conservative risk limits**: `RISK_PER_TRADE=0.01` (1%)
3. **Use stop losses**: All strategies support stop-loss orders
4. **Monitor daily**: Check `MAX_DAILY_LOSS` setting
5. **Test thoroughly**: Run backtests before live trading
6. **Start small**: Begin with minimal capital
7. **Review regularly**: Check performance metrics frequently

## Troubleshooting

### API Connection Issues
- Check exchange API keys are correct
- Verify API keys have trading permissions
- Check IP whitelist on exchange

### Database Errors
- Delete `trading.db` to reset database
- Run `alembic upgrade head` for migrations

### Docker Issues
- Check logs: `docker-compose logs trading-api`
- Rebuild: `docker-compose build --no-cache`
- Reset: `docker-compose down -v && docker-compose up -d`

## Support

For issues and questions:
1. Check logs in `logs/trading_bot.log`
2. Review API documentation at `http://localhost:8000/docs`
3. Open a GitHub issue with details

