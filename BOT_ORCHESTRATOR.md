# Bot Orchestrator Documentation

## Overview

The Bot Orchestrator is the autonomous core of the algorithmic trading system. It manages strategy execution, position monitoring, risk management, and error recovery in a fully automated manner.

## Architecture

### Core Components

1. **TradingBot Class** - Main orchestrator managing the entire trading lifecycle
2. **Strategy Execution Engine** - Runs strategies periodically and executes trades
3. **Position Monitor** - Continuously checks stop-loss/take-profit conditions
4. **Error Recovery System** - Circuit breakers, retry logic, and health monitoring
5. **Event Bus Integration** - Real-time event notifications

### Background Tasks

The orchestrator runs three main background loops:

- **Strategy Execution Loop** (60s interval) - Fetches market data, runs strategies, executes trades
- **Position Monitoring Loop** (10s interval) - Checks open positions for exit conditions
- **Portfolio Update Loop** (300s interval) - Updates portfolio statistics

## API Endpoints

### Bot Control

#### Start Bot
```bash
curl -X POST http://localhost:8000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "initial_balance": 10000.0
  }'
```

#### Stop Bot
```bash
curl -X POST http://localhost:8000/api/v1/bot/stop
```

#### Pause Bot
```bash
curl -X POST http://localhost:8000/api/v1/bot/pause
```

#### Resume Bot
```bash
curl -X POST http://localhost:8000/api/v1/bot/resume
```

### Strategy Management

#### Get Available Strategies
```bash
curl http://localhost:8000/api/v1/bot/strategies/available
```

#### Add Strategy
```bash
curl -X POST http://localhost:8000/api/v1/bot/strategy/add \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "MACrossoverStrategy",
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "params": {
      "fast_period": 10,
      "slow_period": 30
    }
  }'
```

#### Remove Strategy
```bash
curl -X DELETE http://localhost:8000/api/v1/bot/strategy/remove/MACrossoverStrategy/BTC%2FUSDT
```

### Monitoring

#### Get Bot Status
```bash
curl http://localhost:8000/api/v1/bot/status
```

Response:
```json
{
  "running": true,
  "paused": false,
  "paper_trading": true,
  "exchange": "binance",
  "active_strategies": 2,
  "strategies": [
    {
      "name": "MACrossoverStrategy",
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "is_active": true
    }
  ]
}
```

#### Get Bot Health
```bash
curl http://localhost:8000/api/v1/bot/health
```

Response:
```json
{
  "status": "healthy",
  "is_running": true,
  "is_paused": false,
  "last_successful_update": "2025-11-05T19:44:32.211986",
  "time_since_update_seconds": 32.75,
  "consecutive_errors": 0,
  "circuit_breaker_state": "closed",
  "error_counts": {}
}
```

#### Reset Error Tracking
```bash
curl -X POST http://localhost:8000/api/v1/bot/reset-errors
```

## Available Strategies

### 1. MA Crossover Strategy
Classic moving average crossover using fast and slow MAs.
- **Buy**: Fast MA crosses above Slow MA (golden cross)
- **Sell**: Fast MA crosses below Slow MA (death cross)

**Parameters:**
```json
{
  "fast_period": 10,
  "slow_period": 30
}
```

### 2. RSI Strategy
Mean reversion based on RSI indicator.
- **Buy**: RSI < 30 (oversold)
- **Sell**: RSI > 70 (overbought)

**Parameters:**
```json
{
  "rsi_period": 14,
  "oversold": 30,
  "overbought": 70
}
```

### 3. Grid Trading Strategy
Places orders at predetermined grid levels.
- **Buy**: Price hits lower grid levels
- **Sell**: Price hits upper grid levels

**Parameters:**
```json
{
  "grid_levels": 10,
  "grid_spacing_pct": 1.0
}
```

### 4. Momentum Strategy
Breakout strategy using price momentum and volume.
- **Buy**: Price breaks resistance with high volume
- **Sell**: Price breaks support with high volume

**Parameters:**
```json
{
  "lookback_period": 20,
  "volume_threshold": 1.5
}
```

### 5. MACD + Bollinger Bands Strategy
Combines MACD crossovers with Bollinger Bands.
- **Buy**: MACD crosses up AND price touches lower BB
- **Sell**: MACD crosses down AND price touches upper BB

**Parameters:**
```json
{
  "macd_fast": 12,
  "macd_slow": 26,
  "macd_signal": 9,
  "bb_period": 20,
  "bb_std": 2
}
```

## Error Recovery Features

### Circuit Breaker
Prevents cascading failures by temporarily blocking operations after repeated failures.

States:
- **CLOSED**: Normal operation
- **OPEN**: Too many failures, rejecting requests
- **HALF_OPEN**: Testing if service recovered

Configuration:
- Failure threshold: 5 failures
- Recovery timeout: 60 seconds

### Retry Policy
Automatic retry with exponential backoff for transient errors.

Configuration:
- Max attempts: 3
- Initial delay: 1 second
- Max delay: 60 seconds
- Exponential base: 2.0

### Rate Limiter
Prevents API throttling by limiting request rate.

Configuration:
- Max calls: 100 per minute
- Time window: 60 seconds

### Error Tracking
Monitors error frequency and patterns.

- Tracks errors over 1-hour rolling window
- Auto-pauses bot after 10 consecutive errors
- Provides error statistics via health endpoint

## Usage Example

### Complete Trading Session

```bash
# 1. Start the bot
curl -X POST http://localhost:8000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{"exchange": "binance", "initial_balance": 10000}'

# 2. Add strategies
curl -X POST http://localhost:8000/api/v1/bot/strategy/add \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "MACrossoverStrategy",
    "symbol": "BTC/USDT",
    "timeframe": "1h"
  }'

curl -X POST http://localhost:8000/api/v1/bot/strategy/add \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "RSIStrategy",
    "symbol": "ETH/USDT",
    "timeframe": "4h"
  }'

# 3. Monitor status
curl http://localhost:8000/api/v1/bot/status | jq .

# 4. Check health
curl http://localhost:8000/api/v1/bot/health | jq .

# 5. View portfolio
curl http://localhost:8000/api/v1/portfolio | jq .

# 6. View positions
curl http://localhost:8000/api/v1/portfolio/positions | jq .

# 7. Pause if needed
curl -X POST http://localhost:8000/api/v1/bot/pause

# 8. Resume
curl -X POST http://localhost:8000/api/v1/bot/resume

# 9. Stop when done
curl -X POST http://localhost:8000/api/v1/bot/stop
```

## Health Status Indicators

| Status | Description |
|--------|-------------|
| `healthy` | Bot running normally with recent successful updates |
| `degraded` | Bot running but experiencing 5+ consecutive errors |
| `unhealthy` | No successful update in 5+ minutes |
| `paused` | Bot is paused (monitoring continues but no new trades) |
| `stopped` | Bot is not running |

## Best Practices

1. **Start Small**: Begin with paper trading and small positions
2. **Monitor Health**: Regularly check `/bot/health` endpoint
3. **Diversify Strategies**: Use multiple strategies on different symbols
4. **Set Timeframes**: Match strategy timeframes to market conditions
5. **Review Logs**: Check Docker logs for detailed operation info
6. **Reset Errors**: Use `/bot/reset-errors` after resolving issues
7. **Gradual Scaling**: Increase position sizes gradually as strategies prove profitable

## Logging

View real-time logs:
```bash
docker-compose logs -f trading-api
```

Logs include:
- Strategy signals and executions
- Position updates and closures
- Error tracking and recovery
- Portfolio performance updates
- Health status changes

## Configuration

Key environment variables (`.env`):

```env
# Exchange
EXCHANGE_API_KEY=your_key
EXCHANGE_API_SECRET=your_secret

# Trading Mode
PAPER_TRADING=true

# Risk Management
MAX_POSITION_SIZE=1000
RISK_PER_TRADE=0.02
MAX_DRAWDOWN_PCT=10
MAX_DAILY_LOSS_PCT=5

# AI Integration
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

## Troubleshooting

### Bot won't start
- Check exchange credentials in `.env`
- Verify Docker containers are running: `docker-compose ps`
- Check logs: `docker-compose logs trading-api`

### Strategies not executing
- Verify bot is running: `GET /api/v1/bot/status`
- Check bot is not paused
- Ensure strategies are added correctly
- Check error counts in health endpoint

### Too many errors
- Check network connectivity
- Verify exchange API is accessible
- Use `/bot/reset-errors` after fixing issues
- Review error logs for specific issues

### Circuit breaker open
- Wait for recovery timeout (60s)
- Check underlying issue in logs
- Manually reset with `/bot/reset-errors`

## Security Notes

- Always use HTTPS in production
- Keep API keys in `.env` file (never commit)
- Set appropriate CORS origins in production
- Monitor unusual trading activity
- Use paper trading for testing

## Future Enhancements

- WebSocket real-time updates
- Advanced backtesting integration
- AI-powered strategy optimization
- Multi-exchange support
- Mobile push notifications
- Strategy performance analytics dashboard

