# Trading Bot Frontend Setup Guide

This guide walks you through setting up and running the web dashboard for the trading bot.

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

The easiest way to run both backend and frontend together:

```bash
# From the project root
docker-compose up -d
```

Services will be available at:
- Frontend Dashboard: http://localhost:3000
- Backend API: http://localhost:8000
- Redis: localhost:6379

### Option 2: Development Mode

Run the frontend in development mode with hot-reload:

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Set up environment variables
cp .env.example .env

# 3. Start development server
npm run dev
```

The dashboard will be available at http://localhost:3000

Make sure the backend is running on port 8000 before starting the frontend.

## 📋 Prerequisites

- **Node.js**: v18 or higher
- **npm**: v9 or higher
- **Backend API**: Running on port 8000
- **Redis**: Required by backend (included in docker-compose)

## 🛠️ Installation

### 1. Install Dependencies

```bash
cd frontend
npm install
```

This will install:
- Next.js 14 (React framework)
- TypeScript
- Tailwind CSS
- TradingView Lightweight Charts
- Recharts
- Axios (API client)
- Lucide React (icons)
- Sonner (toast notifications)

### 2. Configure Environment

Create a `.env` file in the `frontend/` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

For Docker deployment, these are set in `docker-compose.yml`.

### 3. Start Development Server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

## 🏗️ Building for Production

### Local Build

```bash
# Build the application
npm run build

# Start production server
npm start
```

### Docker Build

```bash
# Build Docker image
docker build -t trading-frontend ./frontend

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  -e NEXT_PUBLIC_WS_URL=ws://localhost:8000 \
  trading-frontend
```

## 📱 Dashboard Features

### Main Dashboard (`/`)
- **Bot Controls**: Start, stop, pause, resume
- **Bot Status**: Running/paused/stopped with mode indicator
- **Portfolio Overview**: Balance, P&L, returns
- **Real-time Charts**: 
  - Portfolio value over time (TradingView chart)
  - Daily P&L histogram
- **Live Updates**: WebSocket connection indicator

### Positions (`/positions`)
- **Active Positions Table**: All open positions
- **Real-time Price Updates**: Via WebSocket
- **Position Metrics**: Unrealized P&L, P&L %, duration
- **Manual Close**: Close any position with one click
- **Summary Cards**: Total unrealized P&L, winning/losing positions

### Trades (`/trades`)
- **Trade History**: Complete trade log
- **Pagination**: 20 trades per page
- **Filters**: By symbol, date, strategy
- **Export**: CSV export functionality
- **Performance Metrics**: Win rate, total P&L per page

### Strategies (`/strategies`)
- **Add Strategies**: 5 built-in strategies
  - MA Crossover
  - RSI Strategy
  - Grid Trading
  - Momentum
  - MACD + Bollinger Bands
- **Configure Parameters**: Symbol, timeframe, AI validation
- **Remove Strategies**: One-click removal
- **Strategy Cards**: Show active strategies with settings

### Analytics (`/analytics`)
- **Performance Metrics**:
  - Total trades, win rate, profit factor
  - Sharpe ratio, max drawdown
  - Average win/loss
- **Visual Analytics**:
  - Win/Loss pie chart
  - Top symbols bar chart
  - Symbol performance table
- **AI Insights**: AI validation stats (if enabled)

## 🔌 WebSocket Events

The dashboard subscribes to real-time events:

| Event | Description | UI Update |
|-------|-------------|-----------|
| `POSITION_OPENED` | New position opened | Refresh positions |
| `POSITION_CLOSED` | Position closed | Refresh positions & trades |
| `POSITION_UPDATED` | Position modified | Refresh positions |
| `ORDER_FILLED` | Order executed | Refresh positions & portfolio |
| `SIGNAL_BUY` | Buy signal generated | Toast notification |
| `SIGNAL_SELL` | Sell signal generated | Toast notification |
| `RISK_LIMIT_HIT` | Risk limit reached | Error notification |

## 🎨 UI Components

The dashboard uses custom UI components built with Tailwind CSS:

- **Button**: Primary, secondary, destructive, outline variants
- **Card**: Container for content sections
- **Badge**: Status indicators (success, warning, destructive)
- **Table**: Data tables with sorting
- **Input/Select**: Form controls
- **Switch**: Toggle switches for boolean settings

## 🐛 Troubleshooting

### WebSocket Not Connecting

**Symptom**: "Live" indicator not showing, no real-time updates

**Solutions**:
1. Check backend is running: `curl http://localhost:8000/health`
2. Verify WebSocket endpoint: `curl http://localhost:8000/ws/status`
3. Check browser console for connection errors
4. Ensure `NEXT_PUBLIC_WS_URL` is correct in `.env`

### API Requests Failing

**Symptom**: Pages show "Failed to fetch data" errors

**Solutions**:
1. Verify backend is accessible: `curl http://localhost:8000/`
2. Check CORS settings in `app/main.py`
3. Confirm `NEXT_PUBLIC_API_URL` matches backend address
4. Check browser Network tab for error details

### Build Errors

**Symptom**: Build fails with TypeScript or dependency errors

**Solutions**:
```bash
# Clear cache and rebuild
rm -rf .next node_modules
npm install
npm run build
```

### Charts Not Displaying

**Symptom**: Empty chart containers

**Solutions**:
1. Check browser console for lightweight-charts errors
2. Ensure data is available (check API responses)
3. Verify chart container has dimensions
4. Try refreshing the page

### Docker Issues

**Symptom**: Container fails to start

**Solutions**:
```bash
# Check logs
docker logs trading-frontend

# Rebuild without cache
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

## 🔧 Development Tips

### Hot Reload
Next.js dev server has hot module replacement - changes appear instantly without refresh.

### API Testing
Use the backend's Swagger UI at http://localhost:8000/docs to test API endpoints.

### TypeScript
Run type checking without building:
```bash
npm run lint
```

### Component Development
Create new UI components in `src/components/ui/` following the existing patterns.

### Debugging WebSocket
Add to `useWebSocket.ts`:
```typescript
ws.current.onmessage = (event) => {
  console.log('WebSocket message:', event.data);
  // ... existing code
};
```

## 🚦 Production Checklist

Before deploying to production:

- [ ] Update `NEXT_PUBLIC_API_URL` to production backend URL
- [ ] Update `NEXT_PUBLIC_WS_URL` to production WebSocket URL
- [ ] Configure CORS in backend to allow production frontend origin
- [ ] Test all features with production API
- [ ] Enable error tracking (Sentry, etc.)
- [ ] Set up monitoring (uptime, performance)
- [ ] Configure proper authentication if needed
- [ ] Review and update CORS to specific origins (remove "*")
- [ ] Test WebSocket over WSS (secure WebSocket) if using HTTPS
- [ ] Enable rate limiting on API endpoints

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## 🤝 Support

For issues or questions:
1. Check this guide and the main README
2. Review backend logs: `docker logs trading-api`
3. Review frontend logs: `docker logs trading-frontend`
4. Check browser console for errors

