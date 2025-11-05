# Quick Start Guide

## Bot Orchestrator Implementation Complete! 🎉

The autonomous trading bot orchestrator has been successfully implemented with the following features:

### ✅ Implemented Features

1. **TradingBot Orchestrator**
   - Autonomous strategy execution
   - Background task scheduler
   - Lifecycle management (start/stop/pause/resume)

2. **Strategy Execution Engine**
   - Periodic market data fetching
   - Signal generation and validation
   - Automated trade execution
   - Position sizing and risk management

3. **Position Monitoring System**
   - Real-time position tracking
   - Automatic stop-loss/take-profit execution
   - Portfolio updates every 5 minutes

4. **Error Recovery & Health Monitoring**
   - Circuit breaker pattern (prevents cascading failures)
   - Retry policy with exponential backoff
   - Rate limiter (prevents API throttling)
   - Error tracking and statistics
   - Auto-pause on consecutive errors
   - Health status endpoint

5. **API Integration**
   - Start/stop/pause/resume bot
   - Add/remove strategies dynamically
   - Health monitoring
   - Available strategies listing
   - Error reset functionality

### 📋 New API Endpoints

```bash
# Bot Control
POST   /api/v1/bot/start
POST   /api/v1/bot/stop
POST   /api/v1/bot/pause
POST   /api/v1/bot/resume
GET    /api/v1/bot/status
GET    /api/v1/bot/health

# Strategy Management
GET    /api/v1/bot/strategies/available
POST   /api/v1/bot/strategy/add
DELETE /api/v1/bot/strategy/remove/{strategy_name}/{symbol}

# Error Recovery
POST   /api/v1/bot/reset-errors
```

### 🎯 Available Trading Strategies

1. **MACrossoverStrategy** - Moving Average crossover (golden/death cross)
2. **RSIStrategy** - RSI mean reversion (overbought/oversold)
3. **GridTradingStrategy** - Grid trading for range-bound markets
4. **MomentumStrategy** - Breakout strategy with volume confirmation
5. **MACDBBStrategy** - MACD + Bollinger Bands confluence

### 🚀 Getting Started

#### 1. Configure Exchange API Keys

Edit `.env` file:
```env
EXCHANGE_API_KEY=your_binance_api_key
EXCHANGE_API_SECRET=your_binance_api_secret
PAPER_TRADING=true  # Set to false for live trading
```

#### 2. Start the System

```bash
docker-compose up -d
```

#### 3. Start the Bot

```bash
curl -X POST http://localhost:8000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{
    "exchange": "binance",
    "initial_balance": 10000
  }'
```

#### 4. Add a Strategy

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

#### 5. Monitor the Bot

```bash
# Check status
curl http://localhost:8000/api/v1/bot/status | jq .

# Check health
curl http://localhost:8000/api/v1/bot/health | jq .

# View logs
docker-compose logs -f trading-api
```

### 📊 How It Works

1. **Strategy Execution Loop** (runs every 60 seconds):
   - Fetches latest market data for each active strategy
   - Calculates technical indicators
   - Generates trading signals
   - Validates signals against risk limits
   - Executes trades if conditions are met

2. **Position Monitoring Loop** (runs every 10 seconds):
   - Checks all open positions
   - Monitors stop-loss and take-profit levels
   - Automatically closes positions when targets are hit
   - Updates position P&L

3. **Portfolio Update Loop** (runs every 5 minutes):
   - Calculates portfolio statistics
   - Logs current balance and P&L
   - Updates risk metrics

### 🛡️ Error Recovery

The bot includes robust error handling:

- **Circuit Breaker**: Opens after 5 failures, recovers after 60s
- **Retry Policy**: 3 attempts with exponential backoff
- **Rate Limiter**: 100 calls per minute
- **Auto-Pause**: Pauses bot after 10 consecutive errors

### 📈 Example Trading Session

```bash
# 1. Start bot
curl -X POST http://localhost:8000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{"exchange": "binance", "initial_balance": 10000}'

# 2. Add multiple strategies
curl -X POST http://localhost:8000/api/v1/bot/strategy/add \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "MACrossoverStrategy", "symbol": "BTC/USDT", "timeframe": "1h"}'

curl -X POST http://localhost:8000/api/v1/bot/strategy/add \
  -H "Content-Type: application/json" \
  -d '{"strategy_name": "RSIStrategy", "symbol": "ETH/USDT", "timeframe": "4h"}'

# 3. Monitor
watch -n 5 'curl -s http://localhost:8000/api/v1/bot/status | jq .'

# 4. Check portfolio
curl http://localhost:8000/api/v1/portfolio | jq .

# 5. Stop when done
curl -X POST http://localhost:8000/api/v1/bot/stop
```

### 🔍 Monitoring Logs

The bot provides detailed logging:

```bash
docker-compose logs -f trading-api
```

You'll see:
- Strategy execution events
- Trade signals (BUY/SELL)
- Position opens/closes
- P&L updates
- Error tracking
- Health status

### ⚠️ Important Notes

1. **Paper Trading**: Always test with `PAPER_TRADING=true` first
2. **API Keys**: Never commit API keys to git (use `.env` file)
3. **Risk Management**: Start with small positions
4. **Monitoring**: Watch logs and health status regularly
5. **Exchange Limits**: Respect exchange rate limits

### 🐛 Troubleshooting

**Bot won't start:**
```bash
# Check logs
docker-compose logs trading-api

# Restart containers
docker-compose restart

# Check exchange credentials
cat .env | grep EXCHANGE
```

**Too many errors:**
```bash
# Check health
curl http://localhost:8000/api/v1/bot/health | jq .

# Reset errors
curl -X POST http://localhost:8000/api/v1/bot/reset-errors

# Check circuit breaker state
curl http://localhost:8000/api/v1/bot/health | jq .circuit_breaker_state
```

**Strategies not executing:**
```bash
# Verify bot is running
curl http://localhost:8000/api/v1/bot/status | jq .is_running

# Check if paused
curl http://localhost:8000/api/v1/bot/status | jq .is_paused

# List active strategies
curl http://localhost:8000/api/v1/bot/status | jq .strategies
```

### 📚 Full Documentation

See `BOT_ORCHESTRATOR.md` for complete API documentation and advanced usage.

### 🎉 What's Next?

The bot orchestrator is ready to trade! Next steps:

1. **Configure Exchange**: Add your Binance API keys to `.env`
2. **Test Strategies**: Run in paper trading mode first
3. **Monitor Performance**: Track trades and P&L
4. **Optimize Parameters**: Tune strategy parameters based on results
5. **Scale Up**: Add more strategies and symbols

### 💡 Tips

- Start with 1-2 strategies to learn how the system works
- Use different timeframes for different strategies
- Monitor the health endpoint regularly
- Review logs to understand bot behavior
- Adjust risk parameters in `.env` as needed

---

**The autonomous trading bot is now live and ready to trade! 🚀**

