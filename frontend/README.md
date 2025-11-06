# Trading Bot Dashboard

A modern, real-time web dashboard for monitoring and controlling the algorithmic trading bot.

## Features

- **Real-time Dashboard**: Live portfolio tracking, P&L charts, and bot status
- **Position Management**: View and close open positions with real-time updates
- **Trade History**: Comprehensive trade log with filtering and CSV export
- **Strategy Management**: Add, remove, and configure trading strategies
- **Performance Analytics**: Detailed metrics, charts, and AI validation stats
- **WebSocket Integration**: Live updates for trades, signals, and risk alerts

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: TradingView Lightweight Charts, Recharts
- **API**: Axios for REST, native WebSocket for real-time
- **Icons**: Lucide React

## Getting Started

### Development

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The dashboard will be available at `http://localhost:3000`

### Production Build

Build the Next.js app:
```bash
npm run build
npm start
```

### Docker

Build and run with Docker:
```bash
docker build -t trading-frontend .
docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://localhost:8000 -e NEXT_PUBLIC_WS_URL=ws://localhost:8000 trading-frontend
```

Or use docker-compose from the root directory:
```bash
docker-compose up -d
```

## Configuration

### Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_WS_URL`: WebSocket URL (default: `ws://localhost:8000`)

## Pages

- `/` - Main dashboard with bot controls and charts
- `/positions` - Active positions table with real-time updates
- `/trades` - Trade history with pagination and export
- `/strategies` - Strategy management interface
- `/analytics` - Performance metrics and analytics

## API Integration

The dashboard integrates with the FastAPI backend using:

- REST API endpoints (`/api/v1/*`)
- WebSocket for real-time updates (`/ws/updates`)

## Real-time Features

The dashboard subscribes to WebSocket events:
- `POSITION_OPENED` - New position opened
- `POSITION_CLOSED` - Position closed
- `ORDER_FILLED` - Order executed
- `SIGNAL_BUY` / `SIGNAL_SELL` - Trading signals
- `RISK_LIMIT_HIT` - Risk management alerts

## Development Notes

- The app uses Next.js App Router (not Pages Router)
- All pages are client components (`'use client'`)
- Charts use TradingView Lightweight Charts for professional trading UI
- Dark theme optimized for trading dashboards
- Responsive design for desktop and mobile

## Troubleshooting

**WebSocket not connecting:**
- Check that backend is running on the correct port
- Verify `NEXT_PUBLIC_WS_URL` environment variable
- Check browser console for connection errors

**API requests failing:**
- Verify `NEXT_PUBLIC_API_URL` is correct
- Check backend CORS settings allow frontend origin
- Ensure backend is running and accessible

**Build errors:**
- Clear `.next` directory: `rm -rf .next`
- Remove `node_modules` and reinstall: `rm -rf node_modules && npm install`
- Check for TypeScript errors: `npm run lint`

