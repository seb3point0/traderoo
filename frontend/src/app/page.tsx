'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { BotControls } from '@/components/BotControls';
import { PortfolioChart } from '@/components/charts/PortfolioChart';
import { DailyPnLChart } from '@/components/charts/DailyPnLChart';
import { BotStatus, Portfolio, DailyPnL } from '@/types';
import apiClient from '@/lib/api';
import { formatCurrency, formatPercentage } from '@/lib/utils';
import { useWebSocket } from '@/hooks/useWebSocket';
import { TrendingUp, TrendingDown, Activity, Target } from 'lucide-react';
import { toast } from 'sonner';

export default function DashboardPage() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [dailyPnL, setDailyPnL] = useState<DailyPnL[]>([]);
  const [loading, setLoading] = useState(true);
  const { isConnected, subscribe } = useWebSocket();

  const fetchData = async () => {
    try {
      const [statusData, portfolioData, pnlData] = await Promise.all([
        apiClient.getBotStatus(),
        apiClient.getPortfolio(),
        apiClient.getDailyPnL(30),
      ]);

      setStatus(statusData);
      setPortfolio(portfolioData);
      setDailyPnL(pnlData.data);
    } catch (error: any) {
      console.error('Error fetching data:', error);
      if (error.response?.status !== 400) {
        toast.error('Failed to fetch dashboard data');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Subscribe to WebSocket events
  useEffect(() => {
    const unsubscribe = subscribe('all', (message) => {
      // Refresh portfolio on position/trade events
      if (
        message.type === 'POSITION_OPENED' ||
        message.type === 'POSITION_CLOSED' ||
        message.type === 'ORDER_FILLED'
      ) {
        fetchData();
      }

      // Show notifications for signals
      if (message.type === 'SIGNAL_BUY') {
        toast.success(`Buy signal: ${message.data?.symbol || 'Unknown'}`);
      } else if (message.type === 'SIGNAL_SELL') {
        toast.info(`Sell signal: ${message.data?.symbol || 'Unknown'}`);
      } else if (message.type === 'RISK_LIMIT_HIT') {
        toast.error(`Risk limit hit: ${message.data?.reason || 'Unknown'}`);
      }
    });

    return unsubscribe;
  }, [subscribe]);

  // Prepare chart data
  const portfolioChartData = dailyPnL.map((item) => ({
    time: item.date as any,
    value: (portfolio?.initial_balance || 10000) + item.pnl,
  }));

  const pnlChartData = dailyPnL.map((item) => ({
    time: item.date as any,
    value: item.pnl,
    color: item.pnl >= 0 ? '#22c55e' : '#ef4444',
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time trading bot monitoring
            {isConnected && (
              <span className="ml-2 inline-flex items-center">
                <span className="h-2 w-2 rounded-full bg-green-500 mr-1 animate-pulse" />
                Live
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Current Balance</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(portfolio?.current_balance || 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Initial: {formatCurrency(portfolio?.initial_balance || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total P&L</CardDescription>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              (portfolio?.total_pnl || 0) >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {formatCurrency(portfolio?.total_pnl || 0)}
            </div>
            <div className="flex items-center text-xs mt-1">
              {(portfolio?.total_return_pct || 0) >= 0 ? (
                <TrendingUp className="h-3 w-3 mr-1 text-green-500" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1 text-red-500" />
              )}
              <span className={
                (portfolio?.total_return_pct || 0) >= 0 ? 'text-green-500' : 'text-red-500'
              }>
                {formatPercentage(portfolio?.total_return_pct || 0)}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open Positions</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              <Activity className="h-6 w-6 mr-2 text-primary" />
              {portfolio?.open_positions || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Unrealized: {formatCurrency(portfolio?.unrealized_pnl || 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Trades</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold flex items-center">
              <Target className="h-6 w-6 mr-2 text-primary" />
              {portfolio?.total_trades || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Realized: {formatCurrency(portfolio?.realized_pnl || 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <BotControls status={status} onStatusChange={fetchData} />
        </div>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Value</CardTitle>
              <CardDescription>Balance over time (30 days)</CardDescription>
            </CardHeader>
            <CardContent>
              {portfolioChartData.length > 0 ? (
                <PortfolioChart data={portfolioChartData} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Daily P&L</CardTitle>
              <CardDescription>Profit and loss by day (30 days)</CardDescription>
            </CardHeader>
            <CardContent>
              {pnlChartData.length > 0 ? (
                <DailyPnLChart data={pnlChartData} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No data available
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

