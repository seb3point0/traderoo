# Algorithmic Trading Bot Backend

A professional-grade algorithmic trading bot for cryptocurrency markets with support for both spot and futures trading across multiple exchanges.

## Features

- **Multi-Exchange Support**: Connect to 100+ exchanges via CCXT
- **Trading Modes**: Spot and futures trading with leverage
- **Multiple Strategies**: MA Crossover, RSI, Grid Trading, Momentum, and more
- **AI Integration**: LLM-powered market analysis and sentiment
- **Risk Management**: Position sizing, stop-loss, daily limits
- **Paper Trading**: Test strategies without real money
- **Real-time Updates**: WebSocket support for live data
- **Backtesting**: Validate strategies on historical data
- **Data Sources**: DEX Screener, DeFi Llama, CoinGecko integration

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- Exchange API keys

### Installation

1. Clone the repository:
```bash
git clone <your-repo>
cd trading-api
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Edit `.env` with your API keys and configuration

### Running with Docker (Recommended)

```bash
docker-compose up -d
```

The API will be available at `http://localhost:8000`

### Running Locally

1. Install TA-Lib system library:
```bash
# macOS
brew install ta-lib

# Ubuntu/Debian
sudo apt-get install ta-lib

# Windows: Download from https://ta-lib.org/
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
pip install TA-Lib
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Key Endpoints

- `POST /api/v1/bot/start` - Start trading bot
- `POST /api/v1/bot/stop` - Stop trading bot
- `GET /api/v1/bot/status` - Get bot status
- `GET /api/v1/portfolio` - View portfolio
- `GET /api/v1/positions` - View open positions
- `GET /api/v1/trades` - Trade history
- `WS /ws/updates` - Real-time WebSocket updates

## Configuration

Key configuration options in `.env`:

```env
PAPER_TRADING=true          # Start in paper trading mode
MAX_POSITION_SIZE=1000      # Max USD per position
RISK_PER_TRADE=0.02        # 2% risk per trade
MAX_DAILY_LOSS=500         # Stop trading after $500 loss
```

## Trading Strategies

### Built-in Strategies

1. **MA Crossover**: Moving average trend following
2. **RSI Mean Reversion**: Oversold/overbought signals
3. **Grid Trading**: Buy low, sell high in ranges
4. **Momentum**: Breakout with volume confirmation
5. **MACD + BB**: Multi-indicator confluence

### Adding Custom Strategies

Extend the `BaseStrategy` class in `app/strategies/base.py`:

```python
from app.strategies.base import BaseStrategy

class MyStrategy(BaseStrategy):
    async def analyze(self, market_data):
        # Your logic here
        pass
```

## Safety Features

- **Paper Trading**: Test without risk
- **Circuit Breakers**: Auto-stop on large losses
- **Position Limits**: Control exposure
- **Audit Logging**: Complete trade history
- **Graceful Shutdown**: Safe position closing

## Architecture

```
├── app/                    # Main application
│   ├── api/               # FastAPI routes
│   ├── core/              # Core trading logic
│   ├── strategies/        # Trading strategies
│   ├── data/              # Data sources & indicators
│   ├── models/            # Database models
│   └── utils/             # Utilities
├── ai/                    # AI/ML models
├── tests/                 # Test suite
└── logs/                  # Log files
```

## Development

### Run Tests
```bash
pytest tests/
```

### Database Migrations
```bash
alembic upgrade head
```

### View Logs
```bash
tail -f logs/trading_bot.log
```

## Disclaimer

⚠️ **Trading cryptocurrencies carries significant risk. This software is for educational purposes. Use at your own risk. Always start with paper trading.**

## License

MIT License

## Support

For issues and questions, please open a GitHub issue.

